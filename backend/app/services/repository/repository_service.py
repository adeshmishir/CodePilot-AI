from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryIndexError
from app.models.code_chunk import CodeChunkModel
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.paths import (
    backend_root,
    normalize_local_path,
    relative_local_path,
)

NO_SUPPORTED_FILES_MESSAGE = (
    "This repository was cloned, but no supported source files were found, "
    "so CodePilot could not index it."
)

NO_CHUNKS_MESSAGE = (
    "No code chunks could be created for repository "
    "'{repository}'. Nothing to index."
)

NO_VECTORS_MESSAGE = (
    "No vectors could be indexed into the vector store for repository "
    "'{repository}'."
)


class RepositoryService:

    def __init__(self):
        self._indexer = None

    @property
    def indexer(self):
        if self._indexer is None:
            from app.services.indexing.repository_indexer import (
                RepositoryIndexer,
            )

            self._indexer = RepositoryIndexer()

        return self._indexer

    def index_repository(
        self,
        repository_id: int,
        repository_path: str,
        db: Session
    ):
        from app.services.indexing.vector_indexer import VectorIndexer
        from app.services.parser.repository_parser import repository_parser

        repository = (
            db.query(RepositoryModel)
            .filter(RepositoryModel.id == repository_id)
            .first()
        )

        if repository is None:
            raise RepositoryIndexError(
                "Repository not found in the database."
            )

        path = self._ensure_clone(repository, repository_path)

        self._sync_local_path(repository, path, db)

        files = repository_parser.get_repository_files(
            self._app_relative(path)
        )

        if not files:
            raise RepositoryIndexError(
                NO_SUPPORTED_FILES_MESSAGE
            )

        chunks = self.indexer.build_chunks(files)

        if not chunks:
            raise RepositoryIndexError(
                NO_CHUNKS_MESSAGE.format(repository=repository.name)
            )

        vectors_indexed = VectorIndexer().index_chunks(
            db=db,
            repository_id=repository_id,
            chunks=chunks,
        )

        if vectors_indexed == 0:
            raise RepositoryIndexError(
                NO_VECTORS_MESSAGE.format(repository=repository.name)
            )

        self.indexer.replace_chunks(
            chunks=chunks,
            repository_id=repository_id,
            db=db,
        )

        return {
            "files_discovered": len(files),
            "chunks_created": len(chunks),
            "vectors_indexed": vectors_indexed,
        }

    def count_chunks(self, repository_id: int, db: Session) -> int:
        return (
            db.query(CodeChunkModel)
            .filter(CodeChunkModel.repository_id == repository_id)
            .count()
        )

    def count_vectors(self, repository_id: int) -> int:
        from app.services.vector.vector_store import get_vector_store

        return get_vector_store().count_repository_points(repository_id)

    def cleanup_repository(
        self,
        db: Session,
        repository: RepositoryModel,
        remove_checkout: bool = True,
    ) -> None:
        """Remove every trace of a repository after a failed clone or delete.

        Vector points and the checkout are cleaned up best-effort, while the
        chunk rows and repository row are always removed.
        """
        from app.services.vector.vector_store import get_vector_store

        try:
            get_vector_store().delete_repository_points(repository.id)
        except Exception as error:
            print(
                f"Failed removing vectors for repository "
                f"{repository.id}: {error}"
            )

        if remove_checkout and repository.local_path:
            try:
                git_service.remove_repository(
                    normalize_local_path(repository.local_path)
                )
            except Exception as error:
                print(
                    f"Failed removing checkout for repository "
                    f"{repository.id}: {error}"
                )

        db.query(CodeChunkModel).filter(
            CodeChunkModel.repository_id == repository.id
        ).delete(synchronize_session=False)

        db.delete(repository)
        db.commit()

    def _ensure_clone(
        self,
        repository: RepositoryModel,
        repository_path: str,
    ) -> Path:
        path = normalize_local_path(repository_path)

        if git_service.is_valid_repository(path):
            return path

        if not repository.clone_url:
            raise RepositoryIndexError(
                "The repository clone is missing on disk and "
                "clone_url is not set, so it cannot be recovered."
            )

        result = git_service.recover_repository(repository.clone_url)

        return normalize_local_path(result["local_path"])

    def _sync_local_path(
        self,
        repository: RepositoryModel,
        path: Path,
        db: Session,
    ) -> None:
        canonical = relative_local_path(path)

        if repository.local_path != canonical:
            repository.local_path = canonical
            db.commit()

    def _app_relative(self, path: Path) -> Path:
        """Return the path relative to the backend root for parsing.

        Keeping chunk file paths app-root-relative makes them portable
        and avoids leaking absolute machine paths into the index.
        """
        try:
            return path.relative_to(backend_root())
        except ValueError:
            return path


repository_service: RepositoryService | None = None


def get_repository_service() -> RepositoryService:
    global repository_service

    if repository_service is None:
        repository_service = RepositoryService()

    return repository_service


repository_service = get_repository_service()
