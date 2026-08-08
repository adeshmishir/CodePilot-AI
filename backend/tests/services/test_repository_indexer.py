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
