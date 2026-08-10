from pathlib import Path

from sqlalchemy.orm import Session

class RepositoryService:

    def __init__(self):
        self._indexer = None

    @property
    def indexer(self):
        if self._indexer is None:
            from app.services.indexing.repository_indexer import (
                RepositoryIndexer,
            )

            self._indexer = RepositoryIndexer()

        return self._indexer

    def index_repository(
        self,
        repository_id: int,
        repository_path: str,
        db: Session
    ):
        from app.services.embedding.embedding_service import EmbeddingService
        from app.services.indexing.vector_indexer import VectorIndexer
        from app.services.parser.repository_parser import repository_parser
        from app.services.vector.vector_store import VectorStore

        path = Path(repository_path)

        files = repository_parser.get_repository_files(
            path
        )

        chunks = self.indexer.index_files(
            files=files,
            repository_id=repository_id,
            db=db
        )

        vectors_indexed = VectorIndexer(
            embedding_service=EmbeddingService(),
            vector_store=VectorStore(),
        ).index_repository(
            db=db,
            repository_id=repository_id,
        )

        return {
            "files_discovered": len(files),
            "chunks_created": len(chunks),
            "vectors_indexed": vectors_indexed,
        }


repository_service: RepositoryService | None = None


def get_repository_service() -> RepositoryService:
    global repository_service

    if repository_service is None:
        repository_service = RepositoryService()

    return repository_service


repository_service = get_repository_service()
