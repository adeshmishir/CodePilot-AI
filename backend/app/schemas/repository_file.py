from pydantic import BaseModel, Field


class RepositoryFileEntry(BaseModel):
    file_path: str
    size_bytes: int
    index_status: str
    skip_reason: str | None = None
    indexed_at: str | None = None
    updated_at: str | None = None


class FileListResponse(BaseModel):
    repository_id: int
    files: list[RepositoryFileEntry]
    total: int
    offset: int
    limit: int


class FileReadResponse(BaseModel):
    file_path: str
    content: str
    start_line: int
    end_line: int
    total_lines: int
    truncated: bool


class FileReadNotFound(BaseModel):
    detail: str