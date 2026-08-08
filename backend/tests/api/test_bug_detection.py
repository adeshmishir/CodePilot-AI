import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.workflows.bug_detection.service import (
    get_bug_detection_service,
)


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


class FakeBugDetectionService:
    def __init__(self):
        self.calls = []

    def analyze(self, query, repository_id, limit=8):
        self.calls.append(
            {
                "query": query,
                "repository_id": repository_id,
                "limit": limit,
            }
        )

        return {
            "findings": [
                {
                    "title": "Missing URL validation",
                    "severity": "medium",
                    "description": (
                        "The WebSocket URL is built without validation."
                    ),
                    "file_path": "frontend/lib/hooks/useWebSocket.ts",
                    "start_line": 10,
                    "end_line": 38,
                    "evidence": "ws = new WebSocket(url)",
                    "recommendation": (
                        "Validate the URL before opening the socket."
                    ),
                }
            ],
            "sources": [
                {
                    "file_path": "frontend/lib/hooks/useWebSocket.ts",
                    "symbol_name": "connect",
                    "start_line": 10,
                    "end_line": 38,
                    "score": 0.9,
                }
            ],
        }


class ExplodingBugDetectionService:
    def analyze(self, query, repository_id, limit=8):
        raise RuntimeError("groq is down")


@pytest.fixture
def client():
    fake_db = FakeDB()
    fake_service = FakeBugDetectionService()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_bug_detection_service] = (
        lambda: fake_service
    )

    with TestClient(app) as test_client:
        test_client.fake_db = fake_db
        test_client.fake_service = fake_service
        yield test_client

    app.dependency_overrides.clear()


def test_bug_detection_success(client):
    response = client.post(
        "/api/repositories/1/bugs",
        json={
            "query": "Find potential bugs in the WebSocket implementation.",
            "limit": 8,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body["findings"]) == 1
    assert len(body["sources"]) == 1

    finding = body["findings"][0]

    assert finding["title"] == "Missing URL validation"
    assert finding["severity"] == "medium"
    assert finding["description"] == (
        "The WebSocket URL is built without validation."
    )
    assert finding["file_path"] == "frontend/lib/hooks/useWebSocket.ts"
    assert finding["start_line"] == 10
    assert finding["end_line"] == 38
    assert finding["evidence"] == "ws = new WebSocket(url)"
    assert finding["recommendation"] == (
        "Validate the URL before opening the socket."
    )

    source = body["sources"][0]

    assert source["file_path"] == "frontend/lib/hooks/useWebSocket.ts"
    assert source["symbol_name"] == "connect"
    assert source["start_line"] == 10
    assert source["end_line"] == 38
    assert source["score"] == 0.9


def test_request_is_forwarded_to_service(client):
    response = client.post(
        "/api/repositories/1/bugs",
        json={"query": "auth bugs", "limit": 5},
    )

    assert response.status_code == 200

    assert client.fake_service.calls == [
        {
            "query": "auth bugs",
            "repository_id": 1,
            "limit": 5,
        }
    ]


def test_empty_query_rejected(client):
    response = client.post(
        "/api/repositories/1/bugs",
        json={"query": "", "limit": 8},
    )

    assert response.status_code == 422


def test_missing_query_rejected(client):
    response = client.post(
        "/api/repositories/1/bugs",
        json={"limit": 8},
    )

    assert response.status_code == 422


def test_limit_validation(client):
    for limit in (0, -1, 21):
        response = client.post(
            "/api/repositories/1/bugs",
            json={"query": "bugs", "limit": limit},
        )
        assert response.status_code == 422

    response = client.post(
        "/api/repositories/1/bugs",
        json={"query": "bugs", "limit": 20},
    )
    assert response.status_code == 200


def test_invalid_repository_returns_404(client):
    client.fake_db.repository_id = 9999

    response = client.post(
        "/api/repositories/9999/bugs",
        json={"query": "bugs", "limit": 8},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}


def test_service_failure_returns_safe_500(monkeypatch):
    app.dependency_overrides[get_bug_detection_service] = (
        lambda: ExplodingBugDetectionService()
    )

    fake_db = FakeDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/repositories/1/bugs",
                json={"query": "bugs", "limit": 8},
            )

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Bug analysis failed to complete."
        }
    finally:
        app.dependency_overrides.clear()
