from app.services.embedding.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)
import threading

from app.services.embedding.embedding_service import (
    EmbeddingService,
    get_embedding_service,
)
from app.services.vector.vector_store import VectorStore, get_vector_store


class RetrievalService:
    """Orchestrate query embedding and vector search for retrieval."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        repository_id: int,
        limit: int = 5,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed(query)

        points = self.vector_store.search(
            vector=query_vector,
            limit=limit,
            repository_id=repository_id,
        )

        results = []

        for point in points:
            payload = point.payload or {}

            results.append(
                {
                    "score": point.score,
                    "repository_id": payload.get("repository_id"),
                    "file_path": payload.get("file_path"),
                    "symbol_name": payload.get("symbol_name"),
                    "symbol_type": payload.get("symbol_type"),
                    "start_line": payload.get("start_line"),
                    "end_line": payload.get("end_line"),
                    "content": payload.get("content"),
                }
            )

        return results


retrieval_service: RetrievalService | None = None
retrieval_service_lock = threading.Lock()


def get_retrieval_service() -> RetrievalService:
    global retrieval_service

    if retrieval_service is None:
        with retrieval_service_lock:
            if retrieval_service is None:
                retrieval_service = RetrievalService(
                    embedding_service=get_embedding_service(),
                    vector_store=get_vector_store(),
                )

    return retrieval_service
