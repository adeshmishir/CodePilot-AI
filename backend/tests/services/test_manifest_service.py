from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.code_chunk import CodeChunkModel
from app.models.repository import RepositoryModel
from app.models.repository_manifest import RepositoryManifestModel
from app.services.repository.manifest_service import (
    RepositoryManifestService,
    is_unsafe_relative,
)

ROOT = "data/repos/owner/name"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    session.add(
        RepositoryModel(
            id=1,
            owner="owner",
            name="name",
            clone_url="https://github.com/owner/name.git",
            local_path=ROOT,
        )
    )

    rows = [
        (ROOT, "backend/app/main.py", 100, "indexed", None),
        (ROOT, "backend/app/services/leetcode_service.py", 200, "indexed", None),
        (ROOT, "backend/requirements.txt", 50, "indexed", None),
        (ROOT, "frontend/src/pages/Dashboard.jsx", 300, "indexed", None),
        (ROOT, "frontend/src/components/Icons.jsx", 40, "indexed", None),
        (ROOT, "backend/big.py", 999, "skipped", "too_large"),
        (ROOT, "README.md", 10, "indexed", None),
        (ROOT, "package-lock.json", 5, "skipped", "ignored_filename"),
        (ROOT, "backend/broken.py", 20, "failed", "parse_failed"),
    ]

    for prefix, rel, size, status, reason in rows:
        session.add(
            RepositoryManifestModel(
                repository_id=1,
                file_path=f"{prefix}/{rel}",
                size_bytes=size,
                index_status=status,
                skip_reason=reason,
            )
        )

    session.add(
        CodeChunkModel(
            repository_id=1,
            file_path=f"{ROOT}/backend/app/main.py",
            symbol_name="main",
            symbol_type="function",
            start_line=1,
            end_line=10,
            content="def main():\n    run()",
        )
    )

    session.commit()

    yield session
    session.close()


@pytest.fixture
def service(db):
    return RepositoryManifestService(db)


def test_list_files_returns_repo_relative_paths_with_prefix(db, service):
    result = service.list_files(repository_id=1, path_prefix="backend")

    assert [entry["file_path"] for entry in result["files"]] == [
        "backend/app/main.py",
        "backend/app/services/leetcode_service.py",
        "backend/big.py",
        "backend/broken.py",
        "backend/requirements.txt",
    ]
    assert result["total"] == 5


def test_list_files_filters_by_status(db, service):
    result = service.list_files(repository_id=1, status="failed")

    assert [entry["file_path"] for entry in result["files"]] == [
        "backend/broken.py"
    ]


def test_list_files_filters_by_extension(db, service):
    result = service.list_files(repository_id=1, extension="jsx")

    assert [entry["file_path"] for entry in result["files"]] == [
        "frontend/src/components/Icons.jsx",
        "frontend/src/pages/Dashboard.jsx",
    ]


def test_list_files_paginates(db, service):
    page_one = service.list_files(repository_id=1, limit=2, offset=0)
    page_two = service.list_files(repository_id=1, limit=2, offset=2)

    assert page_one["total"] == 9
    assert len(page_one["files"]) == 2
    assert len(page_two["files"]) == 2
    assert page_one["files"][0]["file_path"] != page_two["files"][0]["file_path"]


def test_get_entry_exact(db, service):
    entry = service.get_entry(1, "backend/app/services/leetcode_service.py")

    assert entry is not None
    assert entry["file_path"] == "backend/app/services/leetcode_service.py"
    assert entry["index_status"] == "indexed"


def test_get_entry_missing_returns_none(db, service):
    assert service.get_entry(1, "backend/missing.py") is None


def test_summary_counts(db, service):
    summary = service.get_summary(1)

    assert summary is not None
    assert summary["total_files"] == 9
    assert summary["indexed_files"] == 6
    assert summary["skipped_files"] == 2
    assert summary["failed_files"] == 1
    assert summary["partial"] is True
    assert summary["top_level_directories"] == [
        "backend",
        "frontend",
        "(root files)",
    ]


def test_summary_languages(db, service):
    summary = service.get_summary(1)

    by_language = {item["language"]: item["count"] for item in summary["languages"]}

    assert by_language["python"] == 2
    assert by_language["jsx"] == 2


def test_build_structure_renders_tree(db, service):
    structure = service.build_structure(1)

    assert "backend/" in structure["tree"]
    assert "README.md" in structure["tree"]
    assert "big.py [skipped]" in structure["tree"]
    assert structure["truncated"] is False


def test_build_structure_prefix(db, service):
    structure = service.build_structure(1, path_prefix="frontend")

    assert "frontend/" in structure["tree"]
    assert "backend" not in structure["tree"]


def test_build_structure_truncates(db, service):
    structure = service.build_structure(1, max_entries=3)

    assert structure["truncated"] is True
    assert "listing truncated" in structure["tree"]


def test_config_files_returns_project_descriptors(db, service):
    paths = [entry["file_path"] for entry in service.config_files(1)]

    assert "README.md" in paths
    assert "backend/requirements.txt" in paths


def test_file_chunks_returns_indexed_chunks_for_file(db, service):
    chunks = service.file_chunks(1, "backend/app/main.py")

    assert len(chunks) == 1
    assert chunks[0]["symbol_name"] == "main"
    assert chunks[0]["content"] == "def main():\n    run()"


def test_is_unsafe_relative_rejects_traversal():
    assert is_unsafe_relative("../etc/passwd")
    assert is_unsafe_relative("a/../../b")
    assert is_unsafe_relative("/abs/path")
    assert is_unsafe_relative("..")
    assert is_unsafe_relative("..\\escape")
    assert not is_unsafe_relative("backend/app/main.py")


def test_read_file_reads_requested_file(db, service, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "backend").mkdir(parents=True)

    (checkout / "backend" / "main.py").write_text(
        "line1\nline2\nline3\nline4\n",
        encoding="utf-8",
    )

    repo = db.query(RepositoryModel).filter_by(id=1).first()
    repo.local_path = str(checkout)
    db.commit()

    result = service.read_file(1, "backend/main.py")

    assert result is not None
    assert result["content"] == "line1\nline2\nline3\nline4"
    assert result["total_lines"] == 4
    assert result["truncated"] is False


def test_read_file_line_range(db, service, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "backend").mkdir(parents=True)
    (checkout / "backend" / "main.py").write_text(
        "line1\nline2\nline3\nline4\n",
        encoding="utf-8",
    )

    repo = db.query(RepositoryModel).filter_by(id=1).first()
    repo.local_path = str(checkout)
    db.commit()

    result = service.read_file(1, "backend/main.py", start_line=2, end_line=3)

    assert result["content"] == "line2\nline3"
    assert result["start_line"] == 2
    assert result["end_line"] == 3


def test_read_file_rejects_traversal(db, service, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()

    repo = db.query(RepositoryModel).filter_by(id=1).first()
    repo.local_path = str(checkout)
    db.commit()

    assert service.read_file(1, "../outside.txt") is None


def test_read_file_missing_returns_none(db, service, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()

    repo = db.query(RepositoryModel).filter_by(id=1).first()
    repo.local_path = str(checkout)
    db.commit()

    assert service.read_file(1, "nope.py") is None


@pytest.mark.skipif(
    __import__("sys").platform == "win32",
    reason="Creating symlinks requires elevated privileges on Windows",
)
def test_read_file_resolve_escape_via_symlink(db, service, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (checkout / "link.py").symlink_to(secret)

    repo = db.query(RepositoryModel).filter_by(id=1).first()
    repo.local_path = str(checkout)
    db.commit()

    result = service.read_file(1, "link.py")

    assert result is None