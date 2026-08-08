from sentence_transformers import SentenceTransformer

from app.config.settings import settings


class EmbeddingService:
    """Generate local vector embeddings for CodePilot."""

    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()
