from datetime import datetime

from pydantic import BaseModel


class ManifestEntry(BaseModel):
    file_path: str
    size_bytes: int
    index_status: str
    skip_reason: str | None = None
    indexed_at: datetime | None = None


class RepositoryManifestResponse(BaseModel):
    repository_id: int
    entries: list[ManifestEntry]


class ManifestSkipSummary(BaseModel):
    indexed: int
    skipped: int
    failed: int
    skipped_reasons: dict[str, int]
    failed_reasons: dict[str, int]
