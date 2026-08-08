import pytest
from fastapi.testclient import TestClient

from app.api.endpoints import search as search_module
from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.services.retrieval.retrieval_service import get_retrieval_service


class FakeRepository:
    id = 1


class FakeQuery:
    def __init__(self, repository_id: int):
        self._repository_id = repository_id

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self._repository_id == FakeRepository.id:
            return FakeRepository()
        return None


class FakeDB:
    def __init__(self, repository_id: int = 1):
        self.repository_id = repository_id

    def query(self, model):
        assert model is RepositoryModel
        return FakeQuery(self.repository_id)


class FakeRetrievalService:
    def search(self, query: str, repository_id: int, limit: int = 5):
        return [
            {
                "score": 0.82,
                "repository_id": repository_id,
                "file_path": "src/auth/service.js",
                "symbol_name": "authenticateUser",
                "symbol_type": "function",
                "start_line": 42,
                "end_line": 71,
                "content": "async function authenticateUser() {}",
            }
        ]


@pytest.fixture
def client():
    fake_db = FakeDB()
    fake_retrieval = FakeRetrievalService()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_retrieval_service] = (
        lambda: fake_retrieval
    )

    with TestClient(app) as test_client:
        test_client.fake_db = fake_db
        test_client.fake_retrieval = fake_retrieval
        yield test_client

    app.dependency_overrides.clear()


def test_search_success(client):
    response = client.post(
        "/api/repositories/1/search",
        json={"query": "Where is authentication handled?", "limit": 5},
    )

    assert response.status_code == 200

    body = response.json()

    assert "results" in body
    assert len(body["results"]) == 1

    result = body["results"][0]

    assert result["score"] == 0.82
    assert result["repository_id"] == 1
    assert result["file_path"] == "src/auth/service.js"
    assert result["symbol_name"] == "authenticateUser"
    assert result["symbol_type"] == "function"
    assert result["start_line"] == 42
    assert result["end_line"] == 71
    assert result["content"] == "async function authenticateUser() {}"


def test_empty_query_rejected(client):
    response = client.post(
        "/api/repositories/1/search",
        json={"query": "", "limit": 5},
    )

    assert response.status_code == 422


def test_limit_validation(client):
    for limit in (0, -1, 21):
        response = client.post(
            "/api/repositories/1/search",
            json={"query": "authentication", "limit": limit},
        )
        assert response.status_code == 422

    response = client.post(
        "/api/repositories/1/search",
        json={"query": "authentication", "limit": 10},
    )
    assert response.status_code == 200


def test_invalid_repository_returns_404(client):
    client.fake_db.repository_id = 9999

    response = client.post(
        "/api/repositories/9999/search",
        json={"query": "authentication", "limit": 5},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}


def test_missing_query_rejected(client):
    response = client.post(
        "/api/repositories/1/search",
        json={"limit": 5},
    )

    assert response.status_code == 422
