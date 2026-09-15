import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.models.repository_manifest import RepositoryManifestModel

ROOT = "data/repos/owner/name"


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    checkout = tmp_path / "checkout"
    (checkout / "backend").mkdir(parents=True)
    (checkout / "backend" / "main.py").write_text(
        "line1\nline2\nline3",
        encoding="utf-8",
    )

    session.add(
        RepositoryModel(
            id=1,
            owner="owner",
            name="name",
            clone_url="https://github.com/owner/name.git",
            local_path=str(checkout),
        )
    )

    session.add(
        RepositoryManifestModel(
            repository_id=1,
            file_path=f"{str(checkout).replace(chr(92), '/')}/backend/main.py",
            size_bytes=18,
            index_status="indexed",
            skip_reason=None,
        )
    )
    session.add(
        RepositoryManifestModel(
            repository_id=1,
            file_path=f"{str(checkout).replace(chr(92), '/')}/backend/slow.py",
            size_bytes=999,
            index_status="skipped",
            skip_reason="too_large",
        )
    )
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.session = session
        yield test_client

    app.dependency_overrides.clear()
    session.close()


def test_list_files_returns_manifest_entries(client):
    response = client.get("/api/repositories/1/files")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert {entry["file_path"] for entry in body["files"]} == {
        "backend/main.py",
        "backend/slow.py",
    }


def test_list_files_prefix_filter(client):
    response = client.get(
        "/api/repositories/1/files",
        params={"path_prefix": "backend"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_list_files_status_filter(client):
    response = client.get(
        "/api/repositories/1/files",
        params={"status": "skipped"},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 1
    assert body["files"][0]["file_path"] == "backend/slow.py"
    assert body["files"][0]["skip_reason"] == "too_large"


def test_read_file_returns_content(client):
    response = client.get("/api/repositories/1/files/backend/main.py")

    assert response.status_code == 200

    body = response.json()

    assert body["content"] == "line1\nline2\nline3"
    assert body["total_lines"] == 3
    assert body["truncated"] is False


def test_read_file_line_range(client):
    response = client.get(
        "/api/repositories/1/files/backend/main.py",
        params={"start_line": 2, "end_line": 3},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "line2\nline3"


def test_read_missing_file_returns_404(client):
    response = client.get("/api/repositories/1/files/nope.py")

    assert response.status_code == 404


def test_read_file_traversal_rejected(client):
    response = client.get("/api/repositories/1/files/../secret.py")

    assert response.status_code == 404


def test_unknown_repository_returns_404(client):
    response = client.get("/api/repositories/9999/files")

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}


def test_invalid_line_range_returns_400(client):
    response = client.get(
        "/api/repositories/1/files/backend/main.py",
        params={"start_line": 3, "end_line": 1},
    )

    assert response.status_code == 400