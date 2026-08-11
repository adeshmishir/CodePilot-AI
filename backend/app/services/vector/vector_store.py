from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.config.settings import settings


VECTOR_SIZE = 384

COLLECTION_NAME = "code_chunks"


_vector_store: "VectorStore | None" = None


def get_vector_store() -> "VectorStore":
    """Return the shared VectorStore instance.

    Local Qdrant storage can only be opened by one QdrantClient per
    process, so every component must reuse a single instance instead of
    constructing new ones per request.
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store


class VectorStore:
    """Handle vector storage and retrieval using Qdrant."""

    def __init__(self):
        url = (settings.QDRANT_URL or "").strip()

        if url.startswith(("http://", "https://")):
            self.client = QdrantClient(
                url=url,
                api_key=settings.QDRANT_API_KEY or None,
            )
            return

        if not url or url == ":memory:":
            if not settings.DEBUG:
                raise RuntimeError(
                    "QDRANT_URL is not configured to a persistent Qdrant "
                    "instance. In-memory storage is only allowed when "
                    "DEBUG=True; refusing to fall back to :memory: in "
                    "production."
                )

            self.client = QdrantClient(path=":memory:")
            return

        self.client = QdrantClient(path=url)

    def health_check(self) -> bool:
        """Check whether the Qdrant client is reachable."""
        self.client.get_collections()
        return True

    def create_collection(self) -> None:
        from qdrant_client.models import (
            HnswConfigDiff,
            PayloadSchemaType,
            VectorParams,
        )

        collections = self.client.get_collections().collections
        existing_names = {collection.name for collection in collections}

        if COLLECTION_NAME not in existing_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance="Cosine",
                    on_disk=True,
                ),
                # Keep the vector index and payload on disk so peak memory
                # does not grow with the number of indexed chunks, which is
                # what OOMs the small free-tier instance on larger repos.
                hnsw_config=HnswConfigDiff(on_disk=True),
                on_disk_payload=True,
            )

        try:
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="repository_id",
                field_schema=PayloadSchemaType.INTEGER,
            )
        except Exception:
            pass

    def ensure_collection(self) -> None:
        """Create the collection and its payload index if needed."""
        self.create_collection()

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

    def upsert_embeddings(self, points: list[PointStruct]) -> None:
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

    def count_repository_points(self, repository_id: int) -> int:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        self.ensure_collection()

        result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="repository_id",
                        match=MatchValue(value=repository_id),
                    )
                ]
            ),
            exact=True,
        )

        return result.count

    def list_repository_point_ids(self, repository_id: int) -> list[int]:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        self.ensure_collection()

        point_ids: list[int] = []
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="repository_id",
                            match=MatchValue(value=repository_id),
                        )
                    ]
                ),
                limit=1000,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            point_ids.extend(point.id for point in points)

            if offset is None:
                return point_ids

    def delete_points_by_ids(self, point_ids: list[int]) -> None:
        from qdrant_client.models import PointIdsList

        self.ensure_collection()

        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=PointIdsList(points=point_ids),
        )

    def search(
        self,
        vector: list[float],
        limit: int = 5,
        repository_id: int | None = None,
    ):
        self.ensure_collection()

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

        self.ensure_collection()

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
