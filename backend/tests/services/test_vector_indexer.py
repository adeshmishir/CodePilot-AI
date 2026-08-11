import pytest

from app.schemas.code_chunk import CodeChunk
from app.services.indexing.vector_indexer import VectorIndexer, point_id
from app.services.vector.vector_store import VECTOR_SIZE, VectorStore


class FakeEmbeddingService:
    def embed_batch(self, texts):
        for _ in texts:
            yield [0.5] * VECTOR_SIZE


def make_chunk(file_path="src/a.py", symbol_name="foo", start=1, end=5):
    return CodeChunk(
        file_path=file_path,
        symbol_name=symbol_name,
        symbol_type="function",
        start_line=start,
        end_line=end,
        content="def foo(): ...",
    )


@pytest.fixture
def vector_store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    return VectorStore()


@pytest.fixture
def indexer(vector_store):
    return VectorIndexer(
        embedding_service=FakeEmbeddingService(),
        vector_store=vector_store,
    )


def test_point_id_is_deterministic():
    chunk = make_chunk()

    assert point_id(1, chunk) == point_id(1, chunk)


def test_point_id_distinguishes_repositories_and_chunks():
    first = point_id(1, make_chunk())
    second = point_id(2, make_chunk())
    third = point_id(1, make_chunk(start=10))

    assert first != second
    assert first != third


def test_index_chunks_upserts_vectors(vector_store, indexer):
    chunks = [
        make_chunk(),
        make_chunk(file_path="src/b.py", symbol_name="bar"),
    ]

    count = indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=chunks,
    )

    assert count == 2

    ids = sorted(vector_store.list_repository_point_ids(1))

    assert ids == sorted(point_id(1, chunk) for chunk in chunks)


def test_index_chunks_removes_stale_points(vector_store, indexer):
    indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=[make_chunk(), make_chunk(file_path="src/b.py")],
    )

    kept = make_chunk()

    indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=[kept],
    )

    assert vector_store.list_repository_point_ids(1) == [point_id(1, kept)]


def test_index_chunks_is_isolated_by_repository(vector_store, indexer):
    indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=[make_chunk()],
    )

    assert vector_store.list_repository_point_ids(2) == []
