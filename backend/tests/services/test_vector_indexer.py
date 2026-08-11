import pytest

from app.config.settings import settings
from app.schemas.code_chunk import CodeChunk
from app.services.indexing.vector_indexer import VectorIndexer, point_id
from app.services.vector.vector_store import VECTOR_SIZE, VectorStore


class FakeEmbeddingService:
    def embed_batch(self, texts):
        for _ in texts:
            yield [0.5] * VECTOR_SIZE


class CountingEmbeddingService(FakeEmbeddingService):
    def __init__(self):
        self.batch_sizes = []

    def embed_batch(self, texts):
        texts = list(texts)
        self.batch_sizes.append(len(texts))
        yield from super().embed_batch(texts)


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


def test_upsert_chunks_respects_batch_size(vector_store, monkeypatch):
    monkeypatch.setattr(settings, "INDEX_BATCH_SIZE", 2)

    vector_store.create_collection()

    embedding = CountingEmbeddingService()

    indexer = VectorIndexer(
        embedding_service=embedding,
        vector_store=vector_store,
    )

    chunks = [
        make_chunk(file_path=f"src/{i}.py", symbol_name=f"fn_{i}")
        for i in range(5)
    ]

    count, point_ids = indexer.upsert_chunks(
        repository_id=1,
        chunks=chunks,
    )

    assert count == 5
    assert len(point_ids) == 5
    assert embedding.batch_sizes == [2, 2, 1]

    ids = sorted(vector_store.list_repository_point_ids(1))

    assert ids == sorted(point_id(1, chunk) for chunk in chunks)


def test_index_chunks_respects_batch_size(vector_store, monkeypatch):
    monkeypatch.setattr(settings, "INDEX_BATCH_SIZE", 3)

    embedding = CountingEmbeddingService()

    indexer = VectorIndexer(
        embedding_service=embedding,
        vector_store=vector_store,
    )

    chunks = [
        make_chunk(file_path=f"src/{i}.py", symbol_name=f"fn_{i}")
        for i in range(5)
    ]

    indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=chunks,
    )

    assert embedding.batch_sizes == [3, 2]


def test_remove_stale_points_keeps_new_ids(vector_store, indexer):
    indexer.index_chunks(
        db=None,
        repository_id=1,
        chunks=[make_chunk()],
    )

    kept = make_chunk(file_path="src/kept.py")

    indexer.upsert_chunks(
        repository_id=1,
        chunks=[kept],
    )

    indexer.remove_stale_points(1, {point_id(1, kept)})

    assert vector_store.list_repository_point_ids(1) == [point_id(1, kept)]
