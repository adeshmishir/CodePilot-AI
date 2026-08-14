import threading

from app.config.settings import settings
from app.core.memory import log_memory


_embedding_service: "EmbeddingService | None" = None
_embedding_service_lock = threading.Lock()


def get_embedding_service() -> "EmbeddingService":
    """Return the shared EmbeddingService instance.

    Loading the ONNX embedding model is expensive and memory-heavy, so
    every component must reuse a single instance per process instead of
    constructing new ones per request. The lock is important: model
    loading is lazy and the clone/index worker runs on a separate thread,
    so a concurrent request could otherwise construct a second copy of
    the model and blow through the instance memory limit.
    """
    global _embedding_service

    if _embedding_service is None:
        with _embedding_service_lock:
            if _embedding_service is None:
                _embedding_service = EmbeddingService()

    return _embedding_service


class EmbeddingService:
    """Generate ONNX vector embeddings for CodePilot."""

    def __init__(self):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(
            model_name=settings.EMBEDDING_MODEL,
        )

        log_memory("embedding model loaded")

    def embed(self, text: str) -> list[float]:
        embedding = next(self.model.embed([text]))
        return embedding.tolist()

    def embed_batch(self, texts: list[str]):
        """Yield embeddings for a batch of texts one at a time."""
        for embedding in self.model.embed(texts):
            yield embedding.tolist()
