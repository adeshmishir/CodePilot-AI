from app.config.settings import settings


_embedding_service: "EmbeddingService | None" = None


def get_embedding_service() -> "EmbeddingService":
    """Return the shared EmbeddingService instance.

    Loading the ONNX embedding model is expensive and memory-heavy, so
    every component must reuse a single instance per process instead of
    constructing new ones per request.
    """
    global _embedding_service

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

    def embed(self, text: str) -> list[float]:
        embedding = next(self.model.embed([text]))
        return embedding.tolist()

    def embed_batch(self, texts: list[str]):
        """Yield embeddings for a batch of texts one at a time."""
        for embedding in self.model.embed(texts):
            yield embedding.tolist()
