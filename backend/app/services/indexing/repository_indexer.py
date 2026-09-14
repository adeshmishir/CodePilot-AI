from pathlib import Path

from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunkModel
from app.services.parser.code_parser import CodeParser
from app.schemas.code_chunk import CodeChunk


class RepositoryIndexer:

    def __init__(self):
        self.parser = CodeParser()

    def build_chunks(self, files: list[Path]) -> list[CodeChunk]:
        """Parse source files into chunks without touching the database."""
        chunks = []

        for file in files:
            try:
                file_chunks = self.parser.create_chunks(file)
                chunks.extend(file_chunks)

            except Exception as error:
                print(
                    f"Failed parsing {file}: {error}"
                )

        return chunks

    def iter_file_chunks(self, files: list[Path]):
        """Yield chunks one file at a time.

        Callers iterate over this generator so that only a single file's
        chunks are held in memory at once, instead of accumulating the
        entire repository's chunks in one list.
        """
        for file in files:
            try:
                file_chunks = self.build_chunks([file])
            except Exception as error:
                print(
                    f"Failed parsing {file}: {error}"
                )
                continue

            if file_chunks:
                yield file_chunks

    def replace_chunks(
        self,
        chunks: list[CodeChunk],
        repository_id: int,
        db: Session
    ) -> None:
        """Replace persisted chunk rows for a repository."""
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

    def replace_file_chunks(
        self,
        chunks: list[CodeChunk],
        repository_id: int,
        db: Session
    ) -> None:
        """Replace the persisted chunk rows for a single file.

        Only the rows belonging to ``chunks[0].file_path`` are removed, so
        this is safe to call once per file while streaming a repository:
        it never touches (or re-inserts) any other file's rows.
        """
        if not chunks:
            return

        file_path = chunks[0].file_path

        db.query(CodeChunkModel).filter(
            CodeChunkModel.repository_id == repository_id,
            CodeChunkModel.file_path == file_path,
        ).delete(synchronize_session=False)

        for chunk in chunks:
            db.add(CodeChunkModel(
                repository_id=repository_id,
                file_path=chunk.file_path,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
            ))

        db.commit()

    def index_files(
        self,
        files: list[Path],
        repository_id: int,
        db: Session
    ) -> list[CodeChunk]:
        """Index files, streaming one file's chunks at a time.

        Persistence is committed per file via ``replace_file_chunks`` so
        peak memory is bounded to a single file instead of holding the
        whole repository's chunk list (and a matching transaction) in
        memory. ``build_chunks`` remains for lower-level single-file uses.
        """
        chunks: list[CodeChunk] = []

        for file_chunks in self.iter_file_chunks(files):
            if not file_chunks:
                continue

            self.replace_file_chunks(
                chunks=file_chunks,
                repository_id=repository_id,
                db=db,
            )

            chunks.extend(file_chunks)

        return chunks
