import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_passes_qdrant_api_key_when_configured(
    client,
    monkeypatch,
):
    import app.api.endpoints.health as health_module

    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_URL",
        "https://qdrant.example.invalid",
    )
    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_API_KEY",
        "secret-key",
    )

    captured = {}

    class FakeCollections:
        def __init__(self, client):
            pass

    class FakeQdrantClient:
        def __init__(self, url, api_key=None):
            captured["url"] = url
            captured["api_key"] = api_key

        def get_collections(self):
            return FakeCollections(self)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args, **kwargs):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(health_module, "engine", FakeEngine())
    monkeypatch.setattr(
        "qdrant_client.QdrantClient",
        FakeQdrantClient,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert captured["url"] == "https://qdrant.example.invalid"
    assert captured["api_key"] == "secret-key"


def test_health_treats_qdrant_failure_as_unhealthy(
    client,
    monkeypatch,
):
    import app.api.endpoints.health as health_module

    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_URL",
        "https://qdrant.example.invalid",
    )
    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_API_KEY",
        "",
    )

    class FakeQdrantClient:
        def __init__(self, url, api_key=None):
            pass

        def get_collections(self):
            raise RuntimeError("connection refused")

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args, **kwargs):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(health_module, "engine", FakeEngine())
    monkeypatch.setattr(
        "qdrant_client.QdrantClient",
        FakeQdrantClient,
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["checks"]["vector_store"] is False
