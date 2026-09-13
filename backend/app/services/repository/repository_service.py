import gc
import threading
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryIndexError
from app.core.memory import log_memory
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
        db: Session,
        progress=None,
    ):
        """Index a repository, reporting progress through ``progress(done, total)``.

        Files are discovered and parsed one at a time and each file's chunk
        rows are committed in their own transaction, so peak memory is
        bounded to a single file (plus a small embedding batch) instead of
        the whole repository. A file that fails to index is skipped so one
        bad file cannot stop the whole repository from being indexed.

        The returned summary reports how many files were indexed and why
        the rest were skipped, so the UI can show "Indexed X, Skipped Y"
        without silently pretending a repository is fully covered.
        """
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

        root = self._app_relative(path)

        scan = repository_parser.scan_repository(root)

        if scan["files"] == 0:
            raise RepositoryIndexError(
                NO_SUPPORTED_FILES_MESSAGE
            )

        indexer = VectorIndexer()

        indexer.vector_store.create_collection()

        total_chunks = 0
        total_vectors = 0
        new_point_ids: set[int] = set()
        rows_replaced = False
        indexed_files = 0
        failed_files = 0
        processed_files = 0
        total_files = scan["files"]
        skipped_reasons = dict(scan["skipped"])

        def _count_skip(reason: str) -> None:
            skipped_reasons[reason] = (
                skipped_reasons.get(reason, 0) + 1
            )

        for file_path in repository_parser.iter_repository_files(root):
            try:
                file_chunks = self.indexer.build_chunks([file_path])
            except Exception as error:
                db.rollback()
                failed_files += 1
                _count_skip("parse_failed")
                print(
                    f"Failed parsing {file_path}: {error}"
                )
                processed_files += 1

                if progress is not None:
                    progress(processed_files, total_files)

                continue

            try:
                if not file_chunks:
                    _count_skip("no_code_symbols")
                    processed_files += 1

                    if progress is not None:
                        progress(processed_files, total_files)

                    continue

                if not rows_replaced:
                    db.query(CodeChunkModel).filter(
                        CodeChunkModel.repository_id == repository_id
                    ).delete(synchronize_session=False)
                    rows_replaced = True

                vectors, point_ids = indexer.upsert_chunks(
                    repository_id=repository_id,
                    chunks=file_chunks,
                )

                db.bulk_insert_mappings(
                    CodeChunkModel,
                    [
                        {
                            "repository_id": repository_id,
                            "file_path": chunk.file_path,
                            "symbol_name": chunk.symbol_name,
                            "symbol_type": chunk.symbol_type,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "content": chunk.content,
                        }
                        for chunk in file_chunks
                    ],
                )

                # Bound session buffering and persist each file's rows in
                # its own transaction so a crash mid-index does not lose
                # the work already done.
                db.flush()
                db.commit()

                total_chunks += len(file_chunks)
                total_vectors += vectors
                new_point_ids.update(point_ids)

                indexed_files += 1
                processed_files += 1

                if progress is not None:
                    progress(processed_files, total_files)
            except Exception as error:
                db.rollback()
                failed_files += 1
                _count_skip("index_failed")
                print(
                    f"Failed indexing a file for repository "
                    f"{repository_id}: {error}"
                )
            finally:
                # Release this file's chunk list before the loop rebinds it,
                # and periodically run the GC + log RSS so steady-state
                # memory on the free tier stays bounded and observable.
                del file_chunks

                if processed_files % 50 == 0:
                    gc.collect()
                    log_memory(
                        f"index_repository {repository_id} "
                        f"({processed_files}/{total_files} files)"
                    )

        if total_chunks == 0:
            raise RepositoryIndexError(
                NO_CHUNKS_MESSAGE.format(repository=repository.name)
            )

        if total_vectors == 0:
            raise RepositoryIndexError(
                NO_VECTORS_MESSAGE.format(repository=repository.name)
            )

        indexer.remove_stale_points(repository_id, new_point_ids)

        db.commit()

        skipped_files = total_files - indexed_files

        return {
            "files_discovered": total_files,
            "files_indexed": indexed_files,
            "files_skipped": skipped_files,
            "files_failed": failed_files,
            "skipped_reasons": skipped_reasons,
            "chunks_created": total_chunks,
            "vectors_indexed": total_vectors,
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
repository_service_lock = threading.Lock()


def get_repository_service() -> RepositoryService:
    global repository_service

    if repository_service is None:
        with repository_service_lock:
            if repository_service is None:
                repository_service = RepositoryService()

    return repository_service


repository_service = get_repository_service()
