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
        from app.services.parser.repository_parser import repository_parser

        path = Path(repository_path)

        files = repository_parser.get_repository_files(
            path
        )

        chunks = self.indexer.index_files(
            files=files,
            repository_id=repository_id,
            db=db
        )

        return {
            "files_discovered": len(files),
            "chunks_created": len(chunks)
        }


repository_service: RepositoryService | None = None


def get_repository_service() -> RepositoryService:
    global repository_service

    if repository_service is None:
        repository_service = RepositoryService()

    return repository_service


repository_service = get_repository_service()
