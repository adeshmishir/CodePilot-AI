import pytest

from app.tools.base import ToolError
from app.tools.repository_files import RepositoryFilesTool


def test_lists_distinct_files_for_repository(db):
    tool = RepositoryFilesTool(db)

    result = tool.execute(repository_id=1)

    assert result["files"] == [
        "frontend/lib/hooks/useWebSocket.ts"
    ]


def test_files_are_isolated_by_repository(db):
    tool = RepositoryFilesTool(db)

    repo_one = tool.execute(repository_id=1)["files"]
    repo_two = tool.execute(repository_id=2)["files"]

    assert repo_one == ["frontend/lib/hooks/useWebSocket.ts"]
    assert repo_two == ["backend/main.py"]
    assert set(repo_one).isdisjoint(set(repo_two))


def test_unknown_repository_returns_empty_list(db):
    tool = RepositoryFilesTool(db)

    assert tool.execute(repository_id=9999)["files"] == []


def test_requires_integer_repository_id(db):
    tool = RepositoryFilesTool(db)

    with pytest.raises(ToolError):
        tool.execute(repository_id="1")
