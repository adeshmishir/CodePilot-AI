from pathlib import Path

from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.services.parser.code_parser import CodeParser
from app.schemas.code_chunk import CodeChunk


class RepositoryIndexer:

    def __init__(self):
        self.parser = CodeParser()

    def index_files(
        self,
        files: list[Path],
        repository_id: int,
        db: Session
    ) -> list[CodeChunk]:

        chunks = []

        for file in files:
            try:
                file_chunks = self.parser.create_chunks(file)
                chunks.extend(file_chunks)

            except Exception as error:
                print(
                    f"Failed parsing {file}: {error}"
                )

        db.query(CodeChunkModel).filter(
            CodeChunkModel.repository_id == repository_id
        ).delete(synchronize_session=False)

        for chunk in chunks:
            code_chunk = CodeChunkModel(
                repository_id=repository_id,
                file_path=chunk.file_path,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content
            )

            db.add(code_chunk)

        db.commit()

        return chunks
