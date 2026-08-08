from app.services.retrieval.retrieval_service import RetrievalService
from app.tools.base import AgentTool, ToolError


class SearchRepositoryTool(AgentTool):
    name = "search_repository"
    description = (
        "Semantically search indexed code chunks in a repository. "
        "Returns the most relevant symbols with file paths, line ranges, "
        "similarity scores, and code content."
    )

    def __init__(self, retrieval_service: RetrievalService):
        self.retrieval_service = retrieval_service

    def execute(self, **kwargs) -> dict:
        query = kwargs.get("query")
        repository_id = kwargs.get("repository_id")
        limit = kwargs.get("limit", 5)

        if not isinstance(query, str) or not query.strip():
            raise ToolError(
                "search_repository requires a non-empty 'query' argument."
            )

        if not isinstance(repository_id, int):
            raise ToolError(
                "search_repository requires an integer 'repository_id' "
                "argument."
            )

        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        return {"results": results}
