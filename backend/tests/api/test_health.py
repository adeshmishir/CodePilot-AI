import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_engine(monkeypatch):
    import app.api.endpoints.health as health_module

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


def test_health_passes_when_shared_vector_store_healthy(
    client,
    monkeypatch,
    fake_engine,
):
    import app.api.endpoints.health as health_module

    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_URL",
        "https://qdrant.example.invalid",
    )

    class FakeStore:
        def health_check(self):
            return True

    monkeypatch.setattr(
        "app.services.vector.vector_store.get_vector_store",
        lambda: FakeStore(),
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["checks"]["vector_store"] is True


def test_health_treats_qdrant_failure_as_unhealthy(
    client,
    monkeypatch,
    fake_engine,
):
    import app.api.endpoints.health as health_module

    monkeypatch.setattr(
        health_module.settings,
        "QDRANT_URL",
        "https://qdrant.example.invalid",
    )

    class FakeStore:
        def health_check(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(
        "app.services.vector.vector_store.get_vector_store",
        lambda: FakeStore(),
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["checks"]["vector_store"] is False
