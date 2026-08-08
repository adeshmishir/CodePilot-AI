import pytest

from app.tools.base import ToolError
from app.tools.repository_search import SearchRepositoryTool


class FakeRetrievalService:
    def __init__(self):
        self.calls = []

    def search(self, query, repository_id, limit=5):
        self.calls.append((query, repository_id, limit))

        return [
            {
                "score": 0.82,
                "repository_id": repository_id,
                "file_path": "frontend/lib/hooks/useWebSocket.ts",
                "symbol_name": "connect",
                "symbol_type": "function",
                "start_line": 10,
                "end_line": 38,
                "content": "const connect = () => {}",
            }
        ]


def test_search_executes_with_correct_arguments():
    fake = FakeRetrievalService()
    tool = SearchRepositoryTool(fake)

    result = tool.execute(
        query="websocket",
        repository_id=1,
        limit=3,
    )

    assert fake.calls == [("websocket", 1, 3)]

    assert result["results"][0]["repository_id"] == 1
    assert (
        result["results"][0]["file_path"]
        == "frontend/lib/hooks/useWebSocket.ts"
    )


def test_search_defaults_limit_to_five():
    fake = FakeRetrievalService()
    tool = SearchRepositoryTool(fake)

    tool.execute(query="websocket", repository_id=1)

    assert fake.calls == [("websocket", 1, 5)]


def test_search_forward_repository_id_for_isolation():
    fake = FakeRetrievalService()
    tool = SearchRepositoryTool(fake)

    tool.execute(query="websocket", repository_id=2)

    assert fake.calls == [("websocket", 2, 5)]


def test_search_requires_non_empty_query():
    tool = SearchRepositoryTool(FakeRetrievalService())

    with pytest.raises(ToolError):
        tool.execute(query="", repository_id=1)


def test_search_requires_integer_repository_id():
    tool = SearchRepositoryTool(FakeRetrievalService())

    with pytest.raises(ToolError):
        tool.execute(query="websocket", repository_id="1")


def test_schema_exposes_name_and_description():
    tool = SearchRepositoryTool(FakeRetrievalService())

    schema = tool.schema()

    assert schema["name"] == "search_repository"
    assert schema["description"]
