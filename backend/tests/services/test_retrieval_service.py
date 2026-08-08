import pytest

from app.services.retrieval.retrieval_service import RetrievalService
from app.services.vector.vector_store import VECTOR_SIZE, VectorStore


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        return [0.5] * VECTOR_SIZE


@pytest.fixture
def vector_store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    store.upsert_embedding(
        point_id=1,
        vector=[0.9] * VECTOR_SIZE,
        payload={
            "repository_id": 1,
            "file_path": "src/auth/service.js",
            "symbol_name": "authenticateUser",
            "symbol_type": "function",
            "start_line": 42,
            "end_line": 71,
            "content": "async function authenticateUser() {}",
        },
    )
    store.upsert_embedding(
        point_id=2,
        vector=[0.1] * VECTOR_SIZE,
        payload={
            "repository_id": 2,
            "file_path": "src/other.js",
            "symbol_name": "other",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 2,
            "content": "function other() {}",
        },
    )

    return store


@pytest.fixture
def service(vector_store):
    return RetrievalService(
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )


def test_search_returns_structured_results(service):
    results = service.search(
        query="authentication",
        repository_id=1,
        limit=5,
    )

    assert len(results) == 1

    result = results[0]

    assert result["score"] > 0
    assert result["repository_id"] == 1
    assert result["file_path"] == "src/auth/service.js"
    assert result["symbol_name"] == "authenticateUser"
    assert result["symbol_type"] == "function"
    assert result["start_line"] == 42
    assert result["end_line"] == 71
    assert result["content"] == "async function authenticateUser() {}"


def test_search_respects_limit(service):
    service.vector_store.upsert_embedding(
        point_id=3,
        vector=[0.8] * VECTOR_SIZE,
        payload={
            "repository_id": 1,
            "file_path": "src/b.js",
            "symbol_name": "bar",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 1,
            "content": "function bar() {}",
        },
    )

    results = service.search(
        query="anything",
        repository_id=1,
        limit=1,
    )

    assert len(results) == 1


def test_search_is_isolated_by_repository(service):
    repo_one = service.search(
        query="authentication",
        repository_id=1,
        limit=5,
    )
    repo_two = service.search(
        query="authentication",
        repository_id=2,
        limit=5,
    )

    assert all(result["repository_id"] == 1 for result in repo_one)
    assert all(result["repository_id"] == 2 for result in repo_two)
