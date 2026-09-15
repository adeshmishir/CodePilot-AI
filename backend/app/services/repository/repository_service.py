import gc
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryIndexError
from app.core.memory import log_memory
from app.models.code_chunk import CodeChunkModel
from app.models.repository import RepositoryModel
from app.models.repository_manifest import RepositoryManifestModel
from app.services.github.git_service import git_service
from app.services.repository.paths import (
    backend_root,
    normalize_local_path,
    posix_path,
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

# Manifest rows are persisted in bounded batches during the scan-skip
# reconciliation walk so a repository with many non-indexable files never
# accumulates a repository-wide list (or a single huge transaction) in
# memory.
MANIFEST_BATCH_SIZE = 200


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
        and manifest rows are committed per file, so peak memory is bounded
        to a single file (plus a small embedding batch) instead of the
        whole repository. A file that fails to index is recorded in the
        manifest as failed (``parse_failed``/``index_failed``) so one bad
        file cannot stop the whole repository from being indexed.

        The returned summary reports how many files were indexed, skipped
        and failed and why, so the UI can show "Indexed X, Skipped Y"
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
        indexed_files = 0
        failed_files = 0
        processed_files = 0
        total_files = scan["files"]
        skipped_reasons = dict(scan["skipped"])
        failed_reasons: dict[str, int] = {}

        def _count_skip(reason: str) -> None:
            skipped_reasons[reason] = (
                skipped_reasons.get(reason, 0) + 1
            )

        def _count_failed(reason: str) -> None:
            failed_reasons[reason] = (
                failed_reasons.get(reason, 0) + 1
            )

        def _file_size(file_path: Path) -> int:
            try:
                return file_path.stat().st_size
            except OSError:
                return 0

        def _stage_manifest(
            file_path: str,
            size_bytes: int,
            index_status: str,
            skip_reason: str | None = None,
        ) -> None:
            """Stage a manifest row for the current file in the session.

            Inserted through the Core API so the row never enters the ORM
            identity map.  On a re-index the previous rows are deleted with
            ``synchronize_session=False`` and SQLite can reuse their ids;
            a Core insert avoids the resulting identity-map key collision
            and keeps the session free of stale manifest objects.
            """
            db.execute(
                insert(RepositoryManifestModel).values(
                    repository_id=repository_id,
                    file_path=posix_path(file_path),
                    size_bytes=size_bytes,
                    index_status=index_status,
                    skip_reason=skip_reason,
                    indexed_at=(
                        datetime.utcnow()
                        if index_status == "indexed"
                        else None
                    ),
                ),
            )

        def _persist_manifest(
            file_path: str,
            size_bytes: int,
            index_status: str,
            skip_reason: str | None = None,
            commit: bool = True,
        ) -> None:
            """Insert one manifest row for the current file.

            Defaults to an immediate commit so the row survives any
            subsequent rollback of the chunk transaction (e.g. on a parse
            or index failure). The successful-index path passes
            ``commit=False`` so the row is flushed together with the file's
            chunk rows instead of doubling the per-file transactions.
            """
            _stage_manifest(
                file_path=file_path,
                size_bytes=size_bytes,
                index_status=index_status,
                skip_reason=skip_reason,
            )

            if commit:
                db.commit()

        def _persist_scan_skips(root: Path) -> None:
            """Record scan-level skip reasons as manifest rows.

            Files that were skipped before the streaming loop in
            ``repository_parser.scan_repository`` (unsupported extension,
            too large, binary, lockfile, cap overflow, ...) have no rows
            yet because the loop only ever sees indexable files. This
            reconciliation walk fills them in, writing a bounded batch per
            transaction and clearing it, so a repository with thousands of
            non-indexable files never builds a full list in Python memory.

            Files skipped only because of an ignored directory (.git,
            node_modules, dist, ...) and directories themselves are not
            repository source files, so they are intentionally left out of
            the manifest. Eligible files that were already recorded by the
            loop are recognized by counting eligible files in the same
            deterministic walk order that ``iter_repository_files`` used;
            any eligible file beyond that count was cut off by
            ``MAX_INDEX_FILES`` and is recorded as a cap skip.
            """
            batch: list[dict] = []

            def _flush() -> None:
                if batch:
                    db.bulk_insert_mappings(
                        RepositoryManifestModel,
                        batch,
                    )
                    db.commit()
                    batch.clear()

            eligible_seen = 0

            for file_path in root.rglob("*"):
                reason = repository_parser._classify_file(file_path)

                if reason is None:
                    eligible_seen += 1

                    if eligible_seen <= processed_files:
                        continue

                    batch.append({
                        "repository_id": repository_id,
                        "file_path": posix_path(file_path),
                        "size_bytes": _file_size(file_path),
                        "index_status": "skipped",
                        "skip_reason": "max_index_files",
                    })
                elif reason in ("not_a_file", "ignored_directory"):
                    continue
                else:
                    batch.append({
                        "repository_id": repository_id,
                        "file_path": posix_path(file_path),
                        "size_bytes": _file_size(file_path),
                        "index_status": "skipped",
                        "skip_reason": reason,
                    })

                if len(batch) >= MANIFEST_BATCH_SIZE:
                    _flush()

            _flush()

        # Delete stale manifest and chunk rows from any prior indexing
        # pass so re-indexing starts clean and does not leak rows for
        # files that were deleted from the repository.  Each is a single
        # bounded operation before the streaming loop begins.
        db.query(RepositoryManifestModel).filter(
            RepositoryManifestModel.repository_id == repository_id,
        ).delete(synchronize_session=False)

        db.query(CodeChunkModel).filter(
            CodeChunkModel.repository_id == repository_id,
        ).delete(synchronize_session=False)

        db.commit()

        for file_path in repository_parser.iter_repository_files(root):
            try:
                file_chunks = self.indexer.build_chunks([file_path])
            except Exception as error:
                db.rollback()
                _persist_manifest(
                    file_path=str(file_path),
                    size_bytes=_file_size(file_path),
                    index_status="failed",
                    skip_reason="parse_failed",
                )
                failed_files += 1
                _count_failed("parse_failed")
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
                    _persist_manifest(
                        file_path=str(file_path),
                        size_bytes=_file_size(file_path),
                        index_status="skipped",
                        skip_reason="no_code_symbols",
                    )
                    processed_files += 1

                    if progress is not None:
                        progress(processed_files, total_files)

                    continue

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

                _persist_manifest(
                    file_path=str(file_path),
                    size_bytes=_file_size(file_path),
                    index_status="indexed",
                    commit=False,
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
                _persist_manifest(
                    file_path=str(file_path),
                    size_bytes=_file_size(file_path),
                    index_status="failed",
                    skip_reason="index_failed",
                )
                failed_files += 1
                _count_failed("index_failed")
                print(
                    f"Failed indexing a file for repository "
                    f"{repository_id}: {error}"
                )
                processed_files += 1

                if progress is not None:
                    progress(processed_files, total_files)
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

        # Fill in manifest rows for the files the streaming loop never saw
        # because the scan classified them as unsupported/oversized/binary
        # or cut them off by MAX_INDEX_FILES.  Bounded batches, not a
        # repository-wide list.
        _persist_scan_skips(root)

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

        skipped_files = total_files - indexed_files - failed_files

        return {
            "files_discovered": total_files,
            "files_indexed": indexed_files,
            "files_skipped": skipped_files,
            "files_failed": failed_files,
            "skipped_reasons": skipped_reasons,
            "failed_reasons": failed_reasons,
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

        db.query(RepositoryManifestModel).filter(
            RepositoryManifestModel.repository_id == repository.id
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
