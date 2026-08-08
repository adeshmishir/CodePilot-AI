from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.tools.base import AgentTool, ToolError


class RepositoryFilesTool(AgentTool):
    name = "list_repository_files"
    description = (
        "List the file paths of indexed code in a repository. "
        "Useful to understand the repository structure before "
        "searching deeper."
    )

    def __init__(self, db: Session):
        self.db = db

    def execute(self, **kwargs) -> dict:
        repository_id = kwargs.get("repository_id")

        if not isinstance(repository_id, int):
            raise ToolError(
                "list_repository_files requires an integer "
                "'repository_id' argument."
            )

        file_rows = (
            self.db.query(CodeChunkModel.file_path)
            .filter(CodeChunkModel.repository_id == repository_id)
            .distinct()
            .order_by(CodeChunkModel.file_path)
            .all()
        )

        return {
            "files": [row[0] for row in file_rows]
        }
