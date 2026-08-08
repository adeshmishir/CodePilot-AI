from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.services.embedding.embedding_service import EmbeddingService
from app.services.vector.vector_store import VectorStore


class VectorIndexer:
    """Index persisted code chunks into Qdrant."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

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

        self.vector_store.create_collection()

        self.vector_store.delete_repository_points(repository_id)

        for chunk in chunks:
            vector = self.embedding_service.embed(chunk.content)

            self.vector_store.upsert_embedding(
                point_id=chunk.id,
                vector=vector,
                payload={
                    "repository_id": chunk.repository_id,
                    "file_path": chunk.file_path,
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                },
            )

        return len(chunks)
