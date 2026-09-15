from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.services.repository.manifest_service import RepositoryManifestService
from app.tools.base import AgentTool, ToolError


class RepositoryFilesTool(AgentTool):
    name = "list_repository_files"
    description = (
        "List the repository-relative file paths in a repository, derived "
        "from the index manifest. Use this to understand the repository "
        "layout. Optionally pass 'path_prefix' (a directory) and "
        "'extension' (without the dot, e.g. 'py') to narrow the listing."
    )

    def __init__(self, db: Session):
        self.db = db
        self._manifest = None

    @property
    def manifest(self) -> RepositoryManifestService:
        if self._manifest is None:
            self._manifest = RepositoryManifestService(self.db)

        return self._manifest

    def execute(self, **kwargs) -> dict:
        repository_id = kwargs.get("repository_id")
        path_prefix = kwargs.get("path_prefix")
        extension = kwargs.get("extension")
        limit = kwargs.get("limit")
        offset = kwargs.get("offset", 0)

        if not isinstance(repository_id, int):
            raise ToolError(
                "list_repository_files requires an integer "
                "'repository_id' argument."
            )

        if limit is not None and not isinstance(limit, int):
            raise ToolError(
                "list_repository_files 'limit' must be an integer."
            )

        listing = self.manifest.list_files(
            repository_id=repository_id,
            path_prefix=path_prefix,
            extension=extension,
            limit=limit or 1000,
            offset=offset,
        )

        files = [entry["file_path"] for entry in listing["files"]]

        total = listing["total"]

        # Legacy fallback: no manifest rows exist yet for this repository,
        # so fall back to the distinct indexed chunk paths.
        if total == 0:
            fallback_rows = (
                self.db.query(CodeChunkModel.file_path)
                .filter(CodeChunkModel.repository_id == repository_id)
                .distinct()
                .order_by(CodeChunkModel.file_path)
                .limit(limit or 1000)
                .all()
            )

            files = [row[0] for row in fallback_rows]
            total = len(files)

        return {
            "files": files,
            "total": total,
            "truncated": len(files) and total > len(files),
        }