from sqlalchemy.orm import Session

from app.services.retrieval.retrieval_service import RetrievalService
from app.tools.base import AgentTool
from app.tools.code_context import CodeContextTool
from app.tools.repository_files import RepositoryFilesTool
from app.tools.repository_search import SearchRepositoryTool


class ToolRegistry:
    """Central registry of tools the agent may execute."""

    def __init__(self, tools: list[AgentTool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> list[dict]:
        return [tool.schema() for tool in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def build_tool_registry(
    db: Session,
    retrieval_service: RetrievalService,
) -> ToolRegistry:
    return ToolRegistry(
        [
            SearchRepositoryTool(retrieval_service),
            RepositoryFilesTool(db),
            CodeContextTool(db),
        ]
    )
