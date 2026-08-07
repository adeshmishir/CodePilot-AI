from pathlib import Path

from app.services.parser.code_parser import CodeParser
from app.schemas.code_chunk import CodeChunk


class RepositoryIndexer:

    def __init__(self):
        self.parser = CodeParser()

    def index_files(self, files: list[Path]) -> list[CodeChunk]:
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
