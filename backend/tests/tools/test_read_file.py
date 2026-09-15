import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.repository import RepositoryModel
from app.tools.base import ToolError
from app.tools.read_file import ReadFileTool


@pytest.fixture
def db(tmp_path):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "backend").mkdir()
    (checkout / "backend" / "main.py").write_text(
        "line1\nline2\nline3\nline4\n",
        encoding="utf-8",
    )

    session.add(
        RepositoryModel(
            id=1,
            owner="owner",
            name="name",
            clone_url="https://github.com/owner/name.git",
            local_path=str(checkout),
        )
    )
    session.commit()

    yield session
    session.close()


def test_read_file_returns_content(db):
    tool = ReadFileTool(db)

    result = tool.execute(repository_id=1, file_path="backend/main.py")

    assert result["found"] is True
    assert result["content"] == "line1\nline2\nline3\nline4"
    assert result["total_lines"] == 4
    assert result["file_path"] == "backend/main.py"


def test_read_file_line_range(db):
    tool = ReadFileTool(db)

    result = tool.execute(
        repository_id=1,
        file_path="backend/main.py",
        start_line=2,
        end_line=3,
    )

    assert result["found"] is True
    assert result["content"] == "line2\nline3"
    assert result["start_line"] == 2
    assert result["end_line"] == 3


def test_read_missing_file_returns_not_found(db):
    tool = ReadFileTool(db)

    result = tool.execute(repository_id=1, file_path="nope.py")

    assert result["found"] is False
    assert "not found" in result["error"].lower()


def test_read_traversal_rejected(db):
    tool = ReadFileTool(db)

    result = tool.execute(repository_id=1, file_path="../outside.txt")

    assert result["found"] is False


def test_requires_integer_repository_id(db):
    tool = ReadFileTool(db)

    with pytest.raises(ToolError):
        tool.execute(repository_id="1", file_path="backend/main.py")


def test_requires_non_empty_file_path(db):
    tool = ReadFileTool(db)

    with pytest.raises(ToolError):
        tool.execute(repository_id=1, file_path="  ")


def test_requires_valid_max_chars(db):
    tool = ReadFileTool(db)

    with pytest.raises(ToolError):
        tool.execute(
            repository_id=1,
            file_path="backend/main.py",
            max_chars="not_a_number",
        )