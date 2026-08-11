import json

import pytest
from fastapi.testclient import TestClient
from git import Repo

from app.config.settings import settings
from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.repository_service import repository_service
from app.core.exceptions import RepositoryCloneError, RepositoryIndexError


class FakeQuery:
    def __init__(self, repositories):
        self._repositories = repositories
        self._filters = {}

    def filter(self, *args, **kwargs):
        self._filters.update(kwargs)

        for expression in args:
            left = getattr(expression, "left", None)
            right = getattr(expression, "right", None)
            key = getattr(left, "key", None)
            value = getattr(right, "effective_value", right)
            if key is not None:
                self._filters[key] = value

        return self

    def first(self):
        for repository in self._repositories:
            matches = all(
                getattr(repository, key, None) == value
                for key, value in self._filters.items()
            )
            if matches:
                return repository
        return None

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._repositories


class FakeDB:
    def __init__(self, repositories):
        self.repositories = repositories
        self.added = None

    def query(self, model):
        assert model is RepositoryModel
        return FakeQuery(self.repositories)

    def add(self, instance):
        self.added = instance
        self.repositories.append(instance)

    def delete(self, instance):
        if instance in self.repositories:
            self.repositories.remove(instance)

    def commit(self):
        pass

    def refresh(self, instance):
        instance.id = 1


class FakeGitService:
    def clone_repository(self, url):
        path = url.rstrip("/").split("/")

        return {
            "success": True,
            "repository": path[-1].replace(".git", ""),
            "owner": path[-2],
            "local_path": f"data/repos/{path[-2]}/{path[-1].replace('.git', '')}",
            "message": "Repository cloned successfully",
        }


class FakeRepositoryService:
    def __init__(self):
        self.calls = []

    def index_repository(self, repository_id, repository_path, db):
        self.calls.append(
            {
                "repository_id": repository_id,
                "repository_path": repository_path,
            }
        )

        return {
            "files_discovered": 3,
            "chunks_created": 5,
            "vectors_indexed": 5,
        }

    def count_chunks(self, repository_id, db):
        return 3

    def count_vectors(self, repository_id):
        return 5

    def cleanup_repository(self, db, repository, remove_checkout=True):
        db.delete(repository)
        db.commit()


def make_repository(id):
    repository = RepositoryModel(
        id=id,
        owner="adeshmishir",
        name="CoinOracle",
        clone_url="https://github.com/adeshmishir/CoinOracle",
        local_path="data/repos/adeshmishir/CoinOracle",
    )
    return repository


@pytest.fixture
def client(monkeypatch):
    repositories = [
        make_repository(1),
        make_repository(2),
    ]

    fake_db = FakeDB(repositories)

    fake_git = FakeGitService()

    fake_indexer = FakeRepositoryService()

    monkeypatch.setattr(
        git_service.__class__,
        "clone_repository",
        fake_git.clone_repository,
    )

    monkeypatch.setattr(
        repository_service.__class__,
        "index_repository",
        fake_indexer.index_repository,
    )

    monkeypatch.setattr(
        repository_service.__class__,
        "count_chunks",
        fake_indexer.count_chunks,
    )

    monkeypatch.setattr(
        repository_service.__class__,
        "count_vectors",
        fake_indexer.count_vectors,
    )

    monkeypatch.setattr(
        repository_service.__class__,
        "cleanup_repository",
        fake_indexer.cleanup_repository,
    )

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        test_client.fake_db = fake_db
        test_client.fake_git = fake_git
        test_client.fake_indexer = fake_indexer
        yield test_client

    app.dependency_overrides.clear()


def test_list_repositories(client):
    response = client.get("/repositories")

    assert response.status_code == 200

    body = response.json()

    assert len(body["repositories"]) == 2

    first = body["repositories"][0]

    assert first["id"] == 1
    assert first["owner"] == "adeshmishir"
    assert first["name"] == "CoinOracle"
    assert first["clone_url"] == "https://github.com/adeshmishir/CoinOracle"
    assert first["local_path"] == "data/repos/adeshmishir/CoinOracle"


def test_list_repositories_empty(client):
    client.fake_db.repositories.clear()

    response = client.get("/repositories")

    assert response.status_code == 200

    body = response.json()

    assert body["repositories"] == []


def test_clone_new_repository(client):
    response = client.post(
        "/repositories/clone",
        json={
            "url": "https://github.com/adeshmishir/NewProject",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["id"] == 1
    assert body["repository"] == "NewProject"
    assert body["owner"] == "adeshmishir"
    assert body["message"] == (
        "Cloned and indexed 3 files into 5 chunks and 5 vectors."
    )

    assert client.fake_indexer.calls == [
        {
            "repository_id": 1,
            "repository_path": "data/repos/adeshmishir/NewProject",
        }
    ]


def test_clone_existing_healthy_repository_skips_indexing(client):
    response = client.post(
        "/repositories/clone",
        json={
            "url": "https://github.com/adeshmishir/CoinOracle",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == 1
    assert body["message"] == "Repository already exists and is up to date."

    assert client.fake_indexer.calls == []


def test_clone_existing_broken_repository_is_reindexed(
    client,
    monkeypatch,
):
    class BrokenRepositoryService:
        def count_chunks(self, repository_id, db):
            return 0

        def count_vectors(self, repository_id):
            return 5

    broken = BrokenRepositoryService()

    monkeypatch.setattr(
        repository_service.__class__,
        "count_chunks",
        broken.count_chunks,
    )
    monkeypatch.setattr(
        repository_service.__class__,
        "count_vectors",
        broken.count_vectors,
    )

    response = client.post(
        "/repositories/clone",
        json={
            "url": "https://github.com/adeshmishir/CoinOracle",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == 1
    assert body["message"] == (
        "Repository recovered and re-indexed 3 files into 5 chunks and "
        "5 vectors."
    )

    assert client.fake_indexer.calls == [
        {
            "repository_id": 1,
            "repository_path": "data/repos/adeshmishir/CoinOracle",
        }
    ]


def test_reindex_repository(client):
    response = client.post("/repositories/1/reindex")

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["id"] == 1
    assert body["repository"] == "CoinOracle"
    assert body["owner"] == "adeshmishir"
    assert body["message"] == (
        "Reindexed 3 files into 5 chunks and 5 vectors."
    )

    assert client.fake_indexer.calls == [
        {
            "repository_id": 1,
            "repository_path": "data/repos/adeshmishir/CoinOracle",
        }
    ]


def test_reindex_missing_repository_returns_404(client):
    response = client.post("/repositories/9999/reindex")

    assert response.status_code == 404
    assert client.fake_indexer.calls == []


def test_reindex_returns_error_when_indexing_fails(
    client,
    monkeypatch,
):
    class FailingRepositoryService:
        def index_repository(self, repository_id, repository_path, db):
            raise RepositoryIndexError(
                "No supported source files were found. Nothing to index."
            )

    monkeypatch.setattr(
        repository_service.__class__,
        "index_repository",
        FailingRepositoryService().index_repository,
    )

    response = client.post("/repositories/1/reindex")

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "message": "No supported source files were found. Nothing to index.",
    }


def test_clone_rolls_back_row_when_indexing_fails(
    client,
    monkeypatch,
):
    before = len(client.fake_db.repositories)

    class FailingRepositoryService:
        def index_repository(self, repository_id, repository_path, db):
            raise RepositoryIndexError(
                "No supported source files were found. Nothing to index."
            )

    monkeypatch.setattr(
        repository_service.__class__,
        "index_repository",
        FailingRepositoryService().index_repository,
    )

    response = client.post(
        "/repositories/clone",
        json={
            "url": "https://github.com/adeshmishir/UnindexableProject",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "message": "No supported source files were found. Nothing to index.",
    }
    assert len(client.fake_db.repositories) == before


def test_clone_returns_clone_error_detail(client, monkeypatch):
    class FailingGitService:
        def clone_repository(self, url):
            raise RepositoryCloneError(
                "Repository could not be cloned. Please check the GitHub URL "
                "and repository access.",
                detail="repository not found",
            )

    monkeypatch.setattr(
        git_service.__class__,
        "clone_repository",
        FailingGitService().clone_repository,
    )

    response = client.post(
        "/repositories/clone",
        json={
            "url": "https://github.com/adeshmishir/Secret",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "message": (
            "Repository could not be cloned. Please check the GitHub URL and "
            "repository access."
        ),
        "detail": "repository not found",
    }


def test_clone_auth_failure_is_sanitized_and_never_leaks_token(
    monkeypatch,
    tmp_path,
):
    token = "ghp_secret_api_token"

    monkeypatch.setattr(settings, "GITHUB_TOKEN", token)
    monkeypatch.setattr(git_service, "repositories_dir", tmp_path)

    def failing_clone(url, to_path, **kwargs):
        raise Exception(
            "Cmd('git') failed due to: exit code(128)\n"
            "cmdline: git clone -v -- "
            f"'https://x-access-token:{token}@github.com/"
            "adeshmishir/Secret.git'\n"
            "stderr: fatal: Authentication failed for "
            f"'https://x-access-token:{token}@github.com/"
            "adeshmishir/Secret.git/'"
        )

    monkeypatch.setattr(Repo, "clone_from", staticmethod(failing_clone))

    class _NullDB:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    def override_get_db():
        yield _NullDB()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/repositories/clone",
                json={
                    "url": "https://github.com/adeshmishir/Secret",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400

    body = response.json()

    assert body["success"] is False
    assert "authentication is missing or invalid" in body["message"]
    assert token not in json.dumps(body)
    assert "x-access-token:***" in body["detail"]


def test_delete_repository(client):
    response = client.delete("/repositories/1")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Repository deleted.",
    }

    remaining = [repository.id for repository in client.fake_db.repositories]

    assert remaining == [2]


def test_delete_missing_repository_returns_404(client):
    response = client.delete("/repositories/9999")

    assert response.status_code == 404
