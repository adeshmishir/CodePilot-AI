import os
import subprocess

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.core.exceptions import RepositoryIndexError
from app.database.base import Base
from app.models.repository import RepositoryModel
from app.models.repository_manifest import RepositoryManifestModel
from app.services.github.git_service import git_service
from app.services.repository.repository_service import (
    MANIFEST_BATCH_SIZE,
    RepositoryService,
)


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def make_git_repo(path, files):
    path.mkdir(parents=True, exist_ok=True)

    for relative, content in files.items():
        file_path = path / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content)

    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)

    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
        env=GIT_ENV,
    )


class FakeEmbeddingService:
    def embed(self, text):
        return [0.5] * 384

    def embed_batch(self, texts):
        for _ in texts:
            yield [0.5] * 384


class FakeVectorStore:
    def __init__(self):
        self.upserted = []

    def create_collection(self):
        pass

    def delete_repository_points(self, repository_id):
        pass

    def upsert_embeddings(self, points):
        self.upserted.extend(
            {
                "point_id": point.id,
                "payload": point.payload,
            }
            for point in points
        )

    def list_repository_point_ids(self, repository_id):
        return []

    def delete_points_by_ids(self, point_ids):
        pass

    def count_repository_points(self, repository_id):
        return len(self.upserted)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    yield session
    session.close()


@pytest.fixture
def clone_root(tmp_path, monkeypatch):
    import app.services.embedding.embedding_service as embedding_module

    embedding_module._embedding_service = None

    monkeypatch.setattr(
        "app.services.embedding.embedding_service.EmbeddingService",
        FakeEmbeddingService,
    )

    monkeypatch.setattr(
        "app.services.vector.vector_store.VectorStore",
        FakeVectorStore,
    )

    monkeypatch.setattr(
        "app.services.vector.vector_store.get_vector_store",
        lambda: FakeVectorStore(),
    )

    root = tmp_path / "clone_root"

    monkeypatch.setattr(git_service, "repositories_dir", root)

    yield root

    embedding_module._embedding_service = None


def build_repository(db, source):
    repository = RepositoryModel(
        owner="someowner",
        name="somename",
        clone_url=source.as_posix(),
        local_path="data/repos/someowner/somename",
    )

    db.add(repository)
    db.commit()
    db.refresh(repository)

    return repository


def manifest_rows(db, repository_id):
    return (
        db.query(RepositoryManifestModel)
        .filter(RepositoryManifestModel.repository_id == repository_id)
        .all()
    )


def row_for(db, repository_id, relative_path):
    suffix = Path(relative_path).as_posix()

    for row in manifest_rows(db, repository_id):
        if Path(row.file_path).as_posix().endswith(suffix):
            return row
    return None


MIXED_FILES = {
    "src/app.py": "def hello(name):\n    return f'Hello, {name}'\n",
    "src/utils.py": "def add(a, b):\n    return a + b\n",
    "backend/server.js": (
        "function handleRequest(req, res) {\n"
        "    return res.send('ok');\n"
        "}\n"
    ),
    "notes.xyz": "# not supported\n",
    "static/vendor.min.js": "var a=1;",
    "README.md": "# Project\n\nDocs.\n",
}


@pytest.fixture
def mixed_source(tmp_path):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(source, dict(MIXED_FILES))
    return source


def index(db, source, progress=None):
    repository = build_repository(db, source)

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
        progress=progress,
    )

    return repository, result


def test_index_persists_manifest_for_indexed_files(
    tmp_path,
    db,
    clone_root,
    mixed_source,
):
    repository, result = index(db, mixed_source)

    assert result["files_indexed"] == 4

    for relative in (
        "src/app.py",
        "src/utils.py",
        "backend/server.js",
        "README.md",
    ):
        row = row_for(db, repository.id, relative)

        assert row is not None
        assert row.index_status == "indexed"
        assert row.skip_reason is None
        assert row.indexed_at is not None
        assert row.size_bytes > 0


def test_index_persists_manifest_for_scan_skips(
    tmp_path,
    db,
    clone_root,
    mixed_source,
):
    repository, result = index(db, mixed_source)

    unsupported = row_for(db, repository.id, "notes.xyz")

    assert unsupported is not None
    assert unsupported.index_status == "skipped"
    assert unsupported.skip_reason == "unsupported_extension"
    assert unsupported.indexed_at is None

    minified = row_for(db, repository.id, "vendor.min.js")

    assert minified is not None
    assert minified.index_status == "skipped"
    assert minified.skip_reason == "minified"

    assert result["skipped_reasons"]["unsupported_extension"] == 1
    assert result["skipped_reasons"]["minified"] == 1


def test_ignored_directory_internals_not_in_manifest(
    tmp_path,
    db,
    clone_root,
    mixed_source,
):
    repository, _ = index(db, mixed_source)

    for row in manifest_rows(db, repository.id):
        assert ".git" not in row.file_path


def test_index_persists_manifest_for_ignored_filename(
    tmp_path,
    db,
    clone_root,
):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "package-lock.json": "{}",
            "src/ok.py": "def ok():\n    pass\n",
        },
    )

    repository, result = index(db, source)

    row = row_for(db, repository.id, "package-lock.json")

    assert row is not None
    assert row.index_status == "skipped"
    assert row.skip_reason == "ignored_filename"

    assert result["skipped_reasons"]["ignored_filename"] == 1


def test_index_persists_manifest_for_too_large(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    monkeypatch.setattr(settings, "MAX_INDEX_FILE_SIZE_MB", 0.001)

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "big.py": "x" * 2048,
            "src/small.py": "def small():\n    pass\n",
        },
    )

    repository, result = index(db, source)

    row = row_for(db, repository.id, "big.py")

    assert row is not None
    assert row.index_status == "skipped"
    assert row.skip_reason == "too_large"

    assert result["skipped_reasons"]["too_large"] == 1
    assert result["files_indexed"] == 1


def test_index_persists_manifest_for_binary(
    tmp_path,
    db,
    clone_root,
):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "generated.py": b"\x00\x01\x02" + b"not really source code",
            "src/text.py": "def text():\n    pass\n",
        },
    )

    repository, result = index(db, source)

    row = row_for(db, repository.id, "generated.py")

    assert row is not None
    assert row.index_status == "skipped"
    assert row.skip_reason == "binary"

    assert result["skipped_reasons"]["binary"] == 1


def test_index_persists_manifest_for_max_index_files(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    monkeypatch.setattr(settings, "MAX_INDEX_FILES", 2)

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "a.py": "def a():\n    pass\n",
            "b.py": "def b():\n    pass\n",
            "c.py": "def c():\n    pass\n",
        },
    )

    repository, result = index(db, source)

    rows = manifest_rows(db, repository.id)

    indexed = [row for row in rows if row.index_status == "indexed"]
    capped = [row for row in rows if row.skip_reason == "max_index_files"]

    assert len(indexed) == 2
    assert len(capped) == 1
    assert capped[0].index_status == "skipped"

    assert result["files_discovered"] == 2
    assert result["skipped_reasons"]["max_index_files"] == 1


def test_index_persists_manifest_for_no_code_symbols(
    tmp_path,
    db,
    clone_root,
):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "src/empty.py": "# comment only, no symbols\n",
            "src/real.py": "def real():\n    pass\n",
        },
    )

    repository, result = index(db, source)

    assert result["files_skipped"] == 1

    row = row_for(db, repository.id, "empty.py")

    assert row is not None
    assert row.index_status == "skipped"
    assert row.skip_reason == "no_code_symbols"
    assert row.indexed_at is None


def test_index_persists_manifest_for_parse_failed(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    from app.services.indexing.repository_indexer import RepositoryIndexer

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(source, {"src/bad.py": "def broken(:)\n"})

    repository = build_repository(db, source)

    def failing_build_chunks(self, files):
        raise RuntimeError("cannot parse")

    monkeypatch.setattr(
        RepositoryIndexer,
        "build_chunks",
        failing_build_chunks,
    )

    with pytest.raises(RepositoryIndexError):
        RepositoryService().index_repository(
            repository_id=repository.id,
            repository_path=repository.local_path,
            db=db,
        )

    row = row_for(db, repository.id, "bad.py")

    assert row is not None
    assert row.index_status == "failed"
    assert row.skip_reason == "parse_failed"
    assert row.indexed_at is None


def test_index_persists_manifest_for_index_failed(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    from app.services.indexing.vector_indexer import VectorIndexer

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(source, {"src/good.py": "def a():\n    pass\n"})

    repository = build_repository(db, source)

    def failing_upsert_chunks(self, repository_id, chunks):
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(
        VectorIndexer,
        "upsert_chunks",
        failing_upsert_chunks,
    )

    with pytest.raises(RepositoryIndexError):
        RepositoryService().index_repository(
            repository_id=repository.id,
            repository_path=repository.local_path,
            db=db,
        )

    row = row_for(db, repository.id, "good.py")

    assert row is not None
    assert row.index_status == "failed"
    assert row.skip_reason == "index_failed"
    assert row.indexed_at is None


def test_summary_reports_failed_reasons_and_manifest(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    from app.services.indexing.repository_indexer import RepositoryIndexer
    from app.services.indexing.vector_indexer import VectorIndexer

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "src/good.py": "def good():\n    pass\n",
            "src/parse_bad.py": "def broken(:)\n",
            "src/index_bad.py": "def broken():\n",
            "src/empty.py": "# no symbols here\n",
            "notes.xyz": "# not supported\n",
            "README.md": "# Project\n\nDocs.\n",
        },
    )

    repository = build_repository(db, source)

    original_build_chunks = RepositoryIndexer.build_chunks
    original_upsert_chunks = VectorIndexer.upsert_chunks

    def build_chunks_with_failure(self, files):
        if files[0].name == "parse_bad.py":
            raise RuntimeError("boom")
        return original_build_chunks(self, files)

    def upsert_chunks_with_failure(self, repository_id, chunks):
        if Path(chunks[0].file_path).name == "index_bad.py":
            raise RuntimeError("vector boom")
        return original_upsert_chunks(self, repository_id, chunks)

    monkeypatch.setattr(
        RepositoryIndexer,
        "build_chunks",
        build_chunks_with_failure,
    )
    monkeypatch.setattr(
        VectorIndexer,
        "upsert_chunks",
        upsert_chunks_with_failure,
    )

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert result["files_discovered"] == 5
    assert result["files_indexed"] == 2
    assert result["files_failed"] == 2
    assert result["files_skipped"] == 1

    assert result["failed_reasons"] == {
        "parse_failed": 1,
        "index_failed": 1,
    }

    assert "parse_failed" not in result["skipped_reasons"]
    assert "index_failed" not in result["skipped_reasons"]
    assert result["skipped_reasons"]["no_code_symbols"] == 1
    assert result["skipped_reasons"]["unsupported_extension"] == 1

    parse_row = row_for(db, repository.id, "parse_bad.py")
    index_row = row_for(db, repository.id, "index_bad.py")

    assert parse_row.index_status == "failed"
    assert parse_row.skip_reason == "parse_failed"

    assert index_row.index_status == "failed"
    assert index_row.skip_reason == "index_failed"

    assert len(manifest_rows(db, repository.id)) == 6


def test_progress_advances_for_index_failed(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    from app.services.indexing.vector_indexer import VectorIndexer

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "src/one.py": "def one():\n    pass\n",
            "src/two.py": "def two():\n    pass\n",
        },
    )

    repository = build_repository(db, source)

    original_upsert_chunks = VectorIndexer.upsert_chunks

    def upsert_chunks_with_failure(self, repository_id, chunks):
        if Path(chunks[0].file_path).name == "two.py":
            raise RuntimeError("vector boom")
        return original_upsert_chunks(self, repository_id, chunks)

    monkeypatch.setattr(
        VectorIndexer,
        "upsert_chunks",
        upsert_chunks_with_failure,
    )

    progress_updates = []

    result = RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
        progress=lambda done, total: progress_updates.append((done, total)),
    )

    assert result["files_indexed"] == 1
    assert result["files_failed"] == 1
    assert result["failed_reasons"] == {"index_failed": 1}
    assert progress_updates == [(1, 2), (2, 2)]


def test_reindex_does_not_duplicate_manifest_rows(
    tmp_path,
    db,
    clone_root,
    mixed_source,
):
    repository, _ = index(db, mixed_source)

    first_rows = manifest_rows(db, repository.id)

    RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    second_rows = manifest_rows(db, repository.id)

    assert len(second_rows) == len(first_rows)
    assert len(second_rows) == len(
        {row.file_path for row in second_rows}
    )


def test_reindex_removes_stale_manifest_entries(
    tmp_path,
    db,
    clone_root,
):
    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(
        source,
        {
            "src/a.py": "def a():\n    pass\n",
            "src/b.py": "def b():\n    pass\n",
        },
    )

    repository, _ = index(db, source)

    assert row_for(db, repository.id, "b.py") is not None

    clone = clone_root / "someowner" / "somename"
    (clone / "src" / "b.py").unlink()

    subprocess.run(["git", "-C", str(clone), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(clone), "commit", "-q", "-m", "remove b"],
        check=True,
        env=GIT_ENV,
    )

    RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert row_for(db, repository.id, "b.py") is None
    assert row_for(db, repository.id, "a.py") is not None


def test_scan_skip_reconciliation_is_batched(
    tmp_path,
    db,
    clone_root,
    monkeypatch,
):
    files = {"src/ok.py": "def ok():\n    pass\n"}

    for i in range(210):
        files[f"notes_{i}.xyz"] = "# not supported\n"

    source = tmp_path / "repos" / "someowner" / "somename"
    make_git_repo(source, files)

    repository = build_repository(db, source)

    batch_sizes = []
    original_bulk = db.bulk_insert_mappings

    def tracking_bulk(model, mappings, *args, **kwargs):
        batch_sizes.append(len(mappings))
        return original_bulk(model, mappings, *args, **kwargs)

    monkeypatch.setattr(db, "bulk_insert_mappings", tracking_bulk)

    RepositoryService().index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db,
    )

    assert batch_sizes, "reconciliation must flush manifest rows in batches"
    assert max(batch_sizes) <= MANIFEST_BATCH_SIZE

    rows = manifest_rows(db, repository.id)

    assert len(rows) == 211
    assert len({row.file_path for row in rows}) == 211