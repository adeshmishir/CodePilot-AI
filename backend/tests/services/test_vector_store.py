from qdrant_client.models import PointStruct

import pytest

from app.services.vector.vector_store import (
    COLLECTION_NAME,
    VECTOR_SIZE,
    VectorStore,
)


def make_vector(value: float = 0.5) -> list[float]:
    return [value] * VECTOR_SIZE


def test_create_collection(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    names = {
        collection.name
        for collection in store.client.get_collections().collections
    }

    assert COLLECTION_NAME in names
    assert store.health_check() is True


def test_refuses_inmemory_when_debug_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.DEBUG",
        False,
    )
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        ":memory:",
    )

    with pytest.raises(RuntimeError):
        VectorStore()


def test_refuses_empty_url_when_debug_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.DEBUG",
        False,
    )
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        "",
    )

    with pytest.raises(RuntimeError):
        VectorStore()


def test_allows_inmemory_when_debug_enabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.DEBUG",
        True,
    )
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        ":memory:",
    )

    store = VectorStore()

    assert store.health_check() is True


def test_disk_path_allowed_when_debug_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.DEBUG",
        False,
    )
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()

    assert store.health_check() is True


def test_search_creates_collection_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()

    points = store.search(
        vector=make_vector(),
        limit=5,
        repository_id=1,
    )

    assert points == []

    names = {
        collection.name
        for collection in store.client.get_collections().collections
    }

    assert COLLECTION_NAME in names


def test_delete_repository_points_creates_collection_when_missing(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()

    store.delete_repository_points(1)

    names = {
        collection.name
        for collection in store.client.get_collections().collections
    }

    assert COLLECTION_NAME in names


def test_upsert_and_search(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    store.upsert_embedding(
        point_id=1,
        vector=make_vector(),
        payload={
            "repository_id": 1,
            "file_path": "src/a.py",
            "symbol_name": "foo",
            "symbol_type": "function",
            "start_line": 1,
            "end_line": 5,
            "content": "def foo(): ...",
        },
    )

    points = store.search(
        vector=make_vector(),
        limit=5,
        repository_id=1,
    )

    assert len(points) == 1
    assert points[0].id == 1
    assert points[0].payload["symbol_name"] == "foo"


def test_search_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    for point_id in range(1, 6):
        store.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=make_vector(),
                    payload={"repository_id": 1},
                )
            ],
        )

    points = store.search(
        vector=make_vector(),
        limit=2,
        repository_id=1,
    )

    assert len(points) == 2


def test_search_filters_by_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    store.upsert_embedding(
        point_id=1,
        vector=make_vector(),
        payload={"repository_id": 1},
    )
    store.upsert_embedding(
        point_id=2,
        vector=make_vector(),
        payload={"repository_id": 2},
    )

    repo_one = store.search(
        vector=make_vector(),
        limit=5,
        repository_id=1,
    )

    repo_two = store.search(
        vector=make_vector(),
        limit=5,
        repository_id=2,
    )

    assert [point.id for point in repo_one] == [1]
    assert [point.id for point in repo_two] == [2]


def test_delete_repository_points(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    store = VectorStore()
    store.create_collection()

    store.upsert_embedding(
        point_id=1,
        vector=make_vector(),
        payload={"repository_id": 1},
    )
    store.upsert_embedding(
        point_id=2,
        vector=make_vector(),
        payload={"repository_id": 1},
    )
    store.upsert_embedding(
        point_id=3,
        vector=make_vector(),
        payload={"repository_id": 2},
    )

    store.delete_repository_points(1)

    repo_one = store.search(
        vector=make_vector(),
        limit=10,
        repository_id=1,
    )
    repo_two = store.search(
        vector=make_vector(),
        limit=10,
        repository_id=2,
    )

    assert [point.id for point in repo_one] == []
    assert [point.id for point in repo_two] == [3]
