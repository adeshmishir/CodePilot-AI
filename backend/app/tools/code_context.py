from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.tools.base import AgentTool, ToolError


class CodeContextTool(AgentTool):
    name = "get_code_context"
    description = (
        "Retrieve the indexed code chunks for a specific file in a "
        "repository. Optionally narrow to a single symbol via "
        "'symbol_name'."
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

        query = (
            self.db.query(CodeChunkModel)
            .filter(
                CodeChunkModel.repository_id == repository_id,
                CodeChunkModel.file_path == file_path,
            )
        )

        if symbol_name:
            query = query.filter(
                CodeChunkModel.symbol_name == symbol_name
            )

        chunks = (
            query.order_by(CodeChunkModel.start_line).all()
        )

        return {
            "chunks": [
                {
                    "file_path": chunk.file_path,
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                }
                for chunk in chunks
            ]
        }
