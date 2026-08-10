from app.config.settings import settings


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
