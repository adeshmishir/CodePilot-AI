import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.code_chunk import CodeChunkModel
from app.services.embedding.embedding_service import EmbeddingService
from app.services.indexing.vector_indexer import VectorIndexer
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)
from app.services.vector.vector_store import VECTOR_SIZE, VectorStore


class FakeFastEmbed:
    def __init__(self, model_name=None):
        self.model_name = model_name

    @classmethod
    def list_supported_models(cls):
        return [
            {
                "model": "BAAI/bge-small-en-v1.5",
                "dim": VECTOR_SIZE,
                "description": "Fake test model",
                "size_in_GB": 0.0,
                "sources": {"hf": "BAAI/bge-small-en-v1.5"},
                "model_file": "onnx/model.onnx",
            }
        ]

    def embed(self, texts):
        for _ in texts:
            yield np.ones(VECTOR_SIZE, dtype=np.float32)


@pytest.fixture
def fake_fastembed(monkeypatch):
    import fastembed
    from qdrant_client.fastembed_common import FastEmbedMisc

    monkeypatch.setattr(fastembed, "TextEmbedding", FakeFastEmbed)
    monkeypatch.setattr(FastEmbedMisc, "IS_INSTALLED", False)

    return FakeFastEmbed


def make_chunk() -> CodeChunkModel:
    return CodeChunkModel(
        repository_id=1,
        file_path="src/auth/service.js",
        symbol_name="authenticateUser",
        symbol_type="function",
        start_line=42,
        end_line=71,
        content="async function authenticateUser() {}",
    )


def test_embedding_dimension(fake_fastembed):
    embedding = EmbeddingService().embed("What is authentication?")

    assert len(embedding) == VECTOR_SIZE


def test_embedding_output_is_list_of_floats(fake_fastembed):
    embedding = EmbeddingService().embed("hello world")

    assert isinstance(embedding, list)
    assert all(isinstance(value, float) for value in embedding)


def test_embedding_service_initializes_model(fake_fastembed):
    service = EmbeddingService()

    assert isinstance(service.model, FakeFastEmbed)


def test_module_import_does_not_load_fastembed():
    backend = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys;"
                "import app.services.embedding.embedding_service;"
                "print('fastembed' in sys.modules)"
            ),
        ],
        cwd=backend,
        env={
            **os.environ,
            "PYTHONPATH": str(backend),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_torch_and_sentence_transformers_are_not_installed():
    assert importlib.util.find_spec("torch") is None
    assert importlib.util.find_spec("sentence_transformers") is None


@pytest.fixture
def vector_store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    return VectorStore()


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    yield session
    session.close()


def test_index_and_query_embeddings_are_compatible(
    fake_fastembed,
    vector_store,
    db_session,
):
    db_session.add(make_chunk())
    db_session.commit()

    VectorIndexer(
        embedding_service=EmbeddingService(),
        vector_store=vector_store,
    ).index_repository(db=db_session, repository_id=1)

    results = RetrievalService(
        embedding_service=EmbeddingService(),
        vector_store=vector_store,
    ).search(query="authentication", repository_id=1, limit=5)

    assert len(results) == 1
    assert results[0]["symbol_name"] == "authenticateUser"


def test_get_retrieval_service_is_singleton(
    fake_fastembed,
    tmp_path,
    monkeypatch,
):
    import app.services.retrieval.retrieval_service as module

    monkeypatch.setattr(
        "app.services.vector.vector_store.settings.QDRANT_URL",
        str(tmp_path),
    )

    module.retrieval_service = None

    try:
        first = get_retrieval_service()
        second = get_retrieval_service()

        assert first is second
        assert first.embedding_service is second.embedding_service
    finally:
        module.retrieval_service = None
