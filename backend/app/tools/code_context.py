from sqlalchemy.orm import Session

from app.services.repository.manifest_service import RepositoryManifestService
from app.services.repository.paths import posix_path, repo_relative_path
from app.models.repository import RepositoryModel
from app.tools.base import AgentTool, ToolError


class CodeContextTool(AgentTool):
    name = "get_code_context"
    description = (
        "Retrieve the indexed code chunks for a specific file in a "
        "repository. Optionally narrow to a single symbol via "
        "'symbol_name'. Pass the repository-relative 'file_path'."
    )

    def __init__(self, db: Session):
        self.db = db

    def execute(self, **kwargs) -> dict:
        repository_id = kwargs.get("repository_id")
        file_path = kwargs.get("file_path")
        symbol_name = kwargs.get("symbol_name")

        if not isinstance(repository_id, int):
            raise ToolError(
                "get_code_context requires an integer 'repository_id' "
                "argument."
            )

        if not isinstance(file_path, str) or not file_path.strip():
            raise ToolError(
                "get_code_context requires a non-empty 'file_path' "
                "argument."
            )

        manifest = RepositoryManifestService(self.db)

        chunks = manifest.file_chunks(
            repository_id=repository_id,
            file_path=file_path,
        )

        repository = (
            self.db.query(RepositoryModel)
            .filter(RepositoryModel.id == repository_id)
            .first()
        )

        root = posix_path(repository.local_path) if repository else ""

        result = []

        for chunk in chunks:
            if symbol_name and chunk["symbol_name"] != symbol_name:
                continue

            result.append(
                {
                    "file_path": repo_relative_path(root, chunk["file_path"]),
                    "symbol_name": chunk["symbol_name"],
                    "symbol_type": chunk["symbol_type"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "content": chunk["content"],
                }
            )

        return {
            "chunks": result,
        }