import hashlib

from sqlalchemy.orm import Session

from qdrant_client.models import PointStruct

from app.config.settings import settings
from app.models.code_chunk import CodeChunkModel
from app.schemas.code_chunk import CodeChunk
from app.services.embedding.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)
from app.services.vector.vector_store import (
    VectorStore,
    get_vector_store,
)


def point_id(repository_id: int, chunk: CodeChunk | CodeChunkModel) -> int:
    """Derive a stable, deterministic Qdrant point id for a chunk.

    The id is computed from repository + file + symbol + line span rather
    than the database primary key so that reindexing a repository always
    overwrites the same points and stale points can be removed by id.
    """
    key = "|".join(
        [
            str(repository_id),
            chunk.file_path,
            chunk.symbol_name or "",
            str(chunk.start_line),
            str(chunk.end_line),
        ]
    )

    digest = hashlib.sha1(key.encode("utf-8")).digest()

    return int.from_bytes(digest[:8], "big")


class VectorIndexer:
    """Index code chunks into Qdrant."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()

    def _chunk_to_point(
        self,
        chunk: CodeChunk | CodeChunkModel,
        repository_id: int,
        vector: list[float],
    ) -> PointStruct:
        return PointStruct(
            id=point_id(repository_id, chunk),
            vector=vector,
            payload={
                "repository_id": repository_id,
                "file_path": chunk.file_path,
                "symbol_name": chunk.symbol_name,
                "symbol_type": chunk.symbol_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
            },
        )

    def upsert_chunks(
        self,
        repository_id: int,
        chunks: list[CodeChunk | CodeChunkModel],
    ) -> tuple[int, set[int]]:
        """Embed and upsert a single file's chunks in bounded batches.

        Chunks are embedded in batches of ``INDEX_BATCH_SIZE`` so peak
        memory stays flat, and only the resulting point ids are returned.
        Returns ``(count, point_ids)``.
        """
        batch_size = settings.INDEX_BATCH_SIZE

        count = 0
        point_ids: set[int] = set()

        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset:offset + batch_size]

            vectors = list(
                self.embedding_service.embed_batch(
                    [chunk.content for chunk in batch]
                )
            )

            points = [
                self._chunk_to_point(chunk, repository_id, vector)
                for chunk, vector in zip(batch, vectors)
            ]

            self.vector_store.upsert_embeddings(points)

            count += len(batch)
            point_ids.update(
                point_id(repository_id, chunk) for chunk in batch
            )

        return count, point_ids

    def remove_stale_points(
        self,
        repository_id: int,
        new_point_ids: set[int],
    ) -> None:
        """Remove Qdrant points for the repository not in new_point_ids."""
        existing_ids = self.vector_store.list_repository_point_ids(repository_id)

        stale_ids = [
            existing_id
            for existing_id in existing_ids
            if existing_id not in new_point_ids
        ]

        if stale_ids:
            self.vector_store.delete_points_by_ids(stale_ids)

    def index_chunks(
        self,
        db: Session,
        repository_id: int,
        chunks: list[CodeChunk | CodeChunkModel],
    ) -> int:
        """Upsert vectors for the given chunks, then drop stale points.

        Vectors are written in bounded batches to keep peak memory flat
        during embedding, and stale points for the repository are only
        removed after all new vectors have been upserted successfully.
        """
        self.vector_store.create_collection()

        count, new_ids = self.upsert_chunks(repository_id, chunks)

        self.remove_stale_points(repository_id, new_ids)

        return count

    def index_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> int:
        chunks = (
            db.query(CodeChunkModel)
            .filter(CodeChunkModel.repository_id == repository_id)
            .all()
        )

        self.index_chunks(
            db=db,
            repository_id=repository_id,
            chunks=chunks,
        )

        return len(chunks)
