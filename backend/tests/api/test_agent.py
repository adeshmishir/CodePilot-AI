import pytest
from fastapi.testclient import TestClient

from app.agents.agent import get_agent_service
from app.database.session import get_db
from app.main import app
from app.models.repository import RepositoryModel
from app.workflows.multi_agent.orchestrator import (
    get_multi_agent_orchestrator,
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


class FakeAgentService:
    def __init__(self):
        self.calls = []

    def run(self, db, repository_id, query, max_steps=None):
        self.calls.append(
            {
                "repository_id": repository_id,
                "query": query,
                "max_steps": max_steps,
            }
        )

        return {
            "answer": (
                "WebSocket updates flow through useWebSocket.ts"
            ),
            "plan": ["Search WebSocket code"],
            "tool_calls": [
                {
                    "tool": "search_repository",
                    "arguments": {
                        "query": "WebSocket",
                        "repository_id": 1,
                    },
                    "observation": '{"results": []}',
                }
            ],
            "observations": ["Executed search_repository"],
        }


class ExplodingAgentService:
    def run(self, db, repository_id, query, max_steps=None):
        raise RuntimeError("groq is down")


class UnusedMultiAgentOrchestrator:
    def run(self, *args, **kwargs):
        raise AssertionError(
            "Multi-agent orchestrator should not run in single mode tests."
        )


@pytest.fixture
def client():
    fake_db = FakeDB()
    fake_agent = FakeAgentService()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    app.dependency_overrides[get_multi_agent_orchestrator] = (
        lambda: UnusedMultiAgentOrchestrator()
    )

    with TestClient(app) as test_client:
        test_client.fake_db = fake_db
        test_client.fake_agent = fake_agent
        yield test_client

    app.dependency_overrides.clear()


def test_agent_success(client):
    response = client.post(
        "/api/repositories/1/agent",
        json={
            "query": "Explain how WebSocket price updates work.",
            "max_steps": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["answer"] == "WebSocket updates flow through useWebSocket.ts"
    assert body["plan"] == ["Search WebSocket code"]
    assert body["observations"] == ["Executed search_repository"]

    tool_call = body["tool_calls"][0]

    assert tool_call["tool"] == "search_repository"
    assert tool_call["arguments"] == {
        "query": "WebSocket",
        "repository_id": 1,
    }
    assert tool_call["observation"] == '{"results": []}'


def test_agent_forwards_request_to_service(client):
    response = client.post(
        "/api/repositories/1/agent",
        json={
            "query": "how does auth work?",
            "max_steps": 3,
        },
    )

    assert response.status_code == 200

    assert client.fake_agent.calls == [
        {
            "repository_id": 1,
            "query": "how does auth work?",
            "max_steps": 3,
        }
    ]


def test_empty_query_rejected(client):
    response = client.post(
        "/api/repositories/1/agent",
        json={"query": "", "max_steps": 5},
    )

    assert response.status_code == 422


def test_missing_query_rejected(client):
    response = client.post(
        "/api/repositories/1/agent",
        json={"max_steps": 5},
    )

    assert response.status_code == 422


def test_invalid_max_steps_rejected(client):
    for max_steps in (0, -1):
        response = client.post(
            "/api/repositories/1/agent",
            json={"query": "authentication", "max_steps": max_steps},
        )
        assert response.status_code == 422


def test_invalid_repository_returns_404(client):
    client.fake_db.repository_id = 9999

    response = client.post(
        "/api/repositories/9999/agent",
        json={"query": "authentication", "max_steps": 5},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Repository not found"}


def test_agent_failure_returns_500(monkeypatch):
    app.dependency_overrides[get_agent_service] = (
        lambda: ExplodingAgentService()
    )
    app.dependency_overrides[get_multi_agent_orchestrator] = (
        lambda: UnusedMultiAgentOrchestrator()
    )

    fake_db = FakeDB()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/repositories/1/agent",
                json={"query": "authentication", "max_steps": 5},
            )

        assert response.status_code == 500
        assert response.json() == {
            "detail": "The agent failed to complete the request."
        }
    finally:
        app.dependency_overrides.clear()
