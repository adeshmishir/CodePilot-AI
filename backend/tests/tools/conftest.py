import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.code_chunk import CodeChunkModel


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    session.add_all(
        [
            CodeChunkModel(
                repository_id=1,
                file_path="frontend/lib/hooks/useWebSocket.ts",
                symbol_name="useWebSocket",
                symbol_type="function",
                start_line=5,
                end_line=52,
                content="export function useWebSocket() {}",
            ),
            CodeChunkModel(
                repository_id=1,
                file_path="frontend/lib/hooks/useWebSocket.ts",
                symbol_name="connect",
                symbol_type="function",
                start_line=10,
                end_line=38,
                content="const connect = () => {}",
            ),
            CodeChunkModel(
                repository_id=2,
                file_path="backend/main.py",
                symbol_name="main",
                symbol_type="function",
                start_line=1,
                end_line=10,
                content="def main():\n    pass",
            ),
        ]
    )
    session.commit()

    yield session
    session.close()
