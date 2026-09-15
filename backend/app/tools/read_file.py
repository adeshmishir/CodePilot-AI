from sqlalchemy.orm import Session

from app.services.repository.manifest_service import MAX_READ_CHARS
from app.services.repository.manifest_service import (
    RepositoryManifestService,
)
from app.tools.base import AgentTool, ToolError


class ReadFileTool(AgentTool):
    name = "read_file"
    description = (
        "Read the actual contents of a file from the repository checkout. "
        "Pass the repository-relative path in 'file_path'. Use this to "
        "inspect the real source behind a file from the manifest instead "
        "of guessing from embeddings. Optionally pass 'start_line' and "
        "'end_line' to read only a slice."
    )

    def __init__(self, db: Session):
        self.db = db

    def execute(self, **kwargs) -> dict:
        repository_id = kwargs.get("repository_id")
        file_path = kwargs.get("file_path")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        max_chars = kwargs.get("max_chars", MAX_READ_CHARS)

        if not isinstance(repository_id, int):
            raise ToolError(
                "read_file requires an integer 'repository_id' argument."
            )

        if not isinstance(file_path, str) or not file_path.strip():
            raise ToolError(
                "read_file requires a non-empty 'file_path' argument."
            )

        for arg_name in ("start_line", "end_line", "max_chars"):
            value = kwargs.get(arg_name)

            if value is not None and not isinstance(value, int):
                raise ToolError(
                    f"read_file '{arg_name}' must be an integer."
                )

        manifest = RepositoryManifestService(self.db)

        try:
            result = manifest.read_file(
                repository_id=repository_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                max_chars=max_chars,
            )
        except Exception as error:
            return {
                "found": False,
                "file_path": file_path,
                "error": str(error),
            }

        if result is None:
            return {
                "found": False,
                "file_path": file_path,
                "error": (
                    "File not found in the repository checkout, or "
                    "path outside the repository was rejected."
                ),
            }

        return {
            "found": True,
            **result,
        }