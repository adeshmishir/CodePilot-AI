import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.services.rag.rag_service import get_rag_service


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


class FakeRAGService:
    def __init__(self):
        self.calls = []

    def answer(self, query: str, repository_id: int, limit: int = 5):
        self.calls.append(
            {
                "query": query,
                "repository_id": repository_id,
                "limit": limit,
            }
        )

        return {
            "answer": (
                "Authentication is handled in src/auth/service.js"
            ),
            "sources": [
                {
                    "file_path": "src/auth/service.js",
                    "symbol_name": "authenticateUser",
                    "start_line": 42,
                    "end_line": 71,
                    "score": 0.82,
                }
            ],
        }


class ExplodingRAGService:
    def answer(self, query: str, repository_id: int, limit: int = 5):
        raise RuntimeError("groq is down")


@pytest.fixture
def client():
    fake_db = FakeDB()
    fake_rag = FakeRAGService()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_service] = lambda: fake_rag

    with TestClient(app) as test_client:
        test_client.fake_db = fake_db
        test_client.fake_rag = fake_rag
        yield test_client

    app.dependency_overrides.clear()


def test_chat_success(client):
    response = client.post(
        "/api/repositories/1/chat",
        json={"query": "Where is authentication handled?", "limit": 5},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["answer"] == (
        "Authentication is handled in src/auth/service.js"
    )
    assert len(body["sources"]) == 1

    source = body["sources"][0]

    assert source["file_path"] == "src/auth/service.js"
    assert source["symbol_name"] == "authenticateUser"
    assert source["start_line"] == 42
    assert source["end_line"] == 71
    assert source["score"] == 0.82


def test_chat_forwards_request_to_service(client):
    response = client.post(
        "/api/repositories/1/chat",
        json={"query": "how does auth work?", "limit": 3},
    )

    assert response.status_code == 200

    assert client.fake_rag.calls == [
        {
            "query": "how does auth work?",
            "repository_id": 1,
            "limit": 3,
        }
    ]


def test_empty_query_rejected(client):
    response = client.post(
        "/api/repositories/1/chat",
        json={"query": "", "limit": 5},
    )

    assert response.status_code == 422


def test_limit_validation(client):
    for limit in (0, -1, 11):
        response = client.post(
            "/api/repositories/1/chat",
            json={"query": "authentication", "limit": limit},
        )
        assert response.status_code == 422

    response = client.post(
        "/api/repositories/1/chat",
        json={"query": "authentication", "limit": 10},
    )
    assert response.status_code == 200


def test_invalid_repository_returns_404(client):
    client.fake_db.repository_id = 9999

    response = client.post(
        "/api/repositories/9999/chat",
        json={"query": "authentication", "limit": 5},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}


def test_missing_query_rejected(client):
    response = client.post(
        "/api/repositories/1/chat",
        json={"limit": 5},
    )

    assert response.status_code == 422


def test_service_failure_returns_500(monkeypatch):
    app.dependency_overrides[get_rag_service] = (
        lambda: ExplodingRAGService()
    )

    fake_db = FakeDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/repositories/1/chat",
                json={"query": "authentication", "limit": 5},
            )

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Unable to generate an answer at this time."
        }
    finally:
        app.dependency_overrides.clear()
