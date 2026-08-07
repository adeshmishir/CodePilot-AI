from pathlib import Path

from sqlalchemy.orm import Session

from app.services.indexing.repository_indexer import RepositoryIndexer
from app.services.parser.repository_parser import repository_parser


class RepositoryService:

    def __init__(self):
        self.indexer = RepositoryIndexer()

    def index_repository(
        self,
        repository_id: int,
        repository_path: str,
        db: Session
    ):
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


repository_service = RepositoryService()
