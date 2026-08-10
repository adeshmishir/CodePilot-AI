from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.config.settings import settings


VECTOR_SIZE = 384

COLLECTION_NAME = "code_chunks"


class VectorStore:
    """Handle vector storage and retrieval using Qdrant."""

    def __init__(self):
        if settings.QDRANT_URL.startswith(("http://", "https://")):
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
        else:
            self.client = QdrantClient(path=settings.QDRANT_URL or ":memory:")

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

    def search(
        self,
        vector: list[float],
        limit: int = 5,
        repository_id: int | None = None,
    ):
        query_filter = None

        if repository_id is not None:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="repository_id",
                        match=MatchValue(value=repository_id),
                    )
                ]
            )

        return self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter=query_filter,
            limit=limit,
        ).points

    def delete_repository_points(self, repository_id: int) -> None:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            FilterSelector,
            MatchValue,
        )

        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="repository_id",
                            match=MatchValue(value=repository_id),
                        )
                    ]
                )
            ),
        )
