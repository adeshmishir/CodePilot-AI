import pytest

from app.tools.base import ToolError
from app.tools.code_context import CodeContextTool


def test_returns_chunks_for_file_ordered_by_line(db):
    tool = CodeContextTool(db)

    result = tool.execute(
        repository_id=1,
        file_path="frontend/lib/hooks/useWebSocket.ts",
    )

    assert len(result["chunks"]) == 2
    assert [chunk["start_line"] for chunk in result["chunks"]] == [5, 10]

    first = result["chunks"][0]

    assert first["symbol_name"] == "useWebSocket"
    assert first["symbol_type"] == "function"
    assert first["end_line"] == 52
    assert first["content"] == "export function useWebSocket() {}"


def test_filters_by_symbol_name(db):
    tool = CodeContextTool(db)

    result = tool.execute(
        repository_id=1,
        file_path="frontend/lib/hooks/useWebSocket.ts",
        symbol_name="connect",
    )

    assert len(result["chunks"]) == 1
    assert result["chunks"][0]["symbol_name"] == "connect"
    assert result["chunks"][0]["start_line"] == 10


def test_chunks_are_isolated_by_repository(db):
    tool = CodeContextTool(db)

    repo_one = tool.execute(
        repository_id=1,
        file_path="frontend/lib/hooks/useWebSocket.ts",
    )
    repo_two = tool.execute(
        repository_id=2,
        file_path="frontend/lib/hooks/useWebSocket.ts",
    )

    assert len(repo_one["chunks"]) == 2
    assert repo_two["chunks"] == []


def test_missing_file_returns_empty_chunks(db):
    tool = CodeContextTool(db)

    result = tool.execute(
        repository_id=1,
        file_path="does/not/exist.py",
    )

    assert result["chunks"] == []


def test_requires_non_empty_file_path(db):
    tool = CodeContextTool(db)

    with pytest.raises(ToolError):
        tool.execute(repository_id=1, file_path="  ")


def test_requires_integer_repository_id(db):
    tool = CodeContextTool(db)

    with pytest.raises(ToolError):
        tool.execute(repository_id="1", file_path="a.py")
