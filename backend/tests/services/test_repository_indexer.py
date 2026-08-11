from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.code_chunk import CodeChunkModel
from app.models.repository import RepositoryModel
from app.services.indexing.repository_indexer import RepositoryIndexer


SAMPLE_FILE = """
def hello(name):
    return f"Hello, {name}"


class Greeter:
    def greet(self):
        return hello("world")
"""


def test_index_files_is_idempotent(tmp_path):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    db_session = sessionmaker(bind=engine)()

    source = tmp_path / "greeter.py"
    source.write_text(SAMPLE_FILE)

    indexer = RepositoryIndexer()

    first = indexer.index_files(
        files=[source],
        repository_id=1,
        db=db_session,
    )
    second = indexer.index_files(
        files=[source],
        repository_id=1,
        db=db_session,
    )

    rows = (
        db_session.query(CodeChunkModel)
        .filter(CodeChunkModel.repository_id == 1)
        .all()
    )

    unique = {
        (
            row.file_path,
            row.symbol_name,
            row.start_line,
            row.end_line,
        )
        for row in rows
    }

    assert len(first) > 0
    assert len(second) == len(first)
    assert len(rows) == len(unique)


def test_iter_file_chunks_yields_chunks_per_file(tmp_path):
    indexer = RepositoryIndexer()

    files = []

    for name in ("a.py", "b.py", "c.py"):
        path = tmp_path / name
        path.write_text(SAMPLE_FILE)
        files.append(path)

    batches = list(indexer.iter_file_chunks(files))

    assert len(batches) == 3

    for batch, path in zip(batches, files):
        assert len(batch) > 0
        assert {chunk.file_path for chunk in batch} == {str(path)}

    seen_paths = {
        Path(chunk.file_path).name
        for batch in batches
        for chunk in batch
    }

    assert seen_paths == {"a.py", "b.py", "c.py"}


def test_iter_file_chunks_skips_unparseable_files(tmp_path, monkeypatch):
    from app.services.indexing.repository_indexer import RepositoryIndexer

    good = tmp_path / "good.py"
    good.write_text(SAMPLE_FILE)

    bad = tmp_path / "bad.py"
    bad.write_text(SAMPLE_FILE)

    original = RepositoryIndexer.build_chunks

    def flaky_build_chunks(self, files):
        if any(path.name == "bad.py" for path in files):
            raise RuntimeError("boom")
        return original(self, files)

    monkeypatch.setattr(
        RepositoryIndexer,
        "build_chunks",
        flaky_build_chunks,
    )

    indexer = RepositoryIndexer()

    batches = list(indexer.iter_file_chunks([good, bad]))

    assert len(batches) == 1
    assert Path(batches[0][0].file_path).name == "good.py"


def test_iter_file_chunks_skips_files_without_symbols(tmp_path):
    indexer = RepositoryIndexer()

    empty = tmp_path / "empty.py"
    empty.write_text("# no symbols here\n")

    full = tmp_path / "full.py"
    full.write_text(SAMPLE_FILE)

    batches = list(indexer.iter_file_chunks([empty, full]))

    assert len(batches) == 1
    assert Path(batches[0][0].file_path).name == "full.py"
