from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.config.settings import settings


VECTOR_SIZE = 384

COLLECTION_NAME = "code_chunks"


class VectorStore:
    """Handle vector storage and retrieval using Qdrant."""

    def __init__(self):
        self.client = QdrantClient(path=settings.QDRANT_URL)

    def health_check(self) -> bool:
        """Check whether the Qdrant client is reachable."""
        self.client.get_collections()
        return True

    def create_collection(self) -> None:
        collections = self.client.get_collections().collections
        existing_names = {collection.name for collection in collections}

        if COLLECTION_NAME not in existing_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "size": VECTOR_SIZE,
                    "distance": "Cosine",
                },
            )

    def upsert_embedding(
        self,
        point_id: int,
        vector: list[float],
        payload: dict,
    ) -> None:
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
