from pydantic import BaseModel, HttpUrl


class CloneRepositoryRequest(BaseModel):
    url: HttpUrl


class CloneRepositoryResponse(BaseModel):
    success: bool
    job_id: str | None = None
    status: str | None = None
    id: int | None = None
    repository: str | None = None
    owner: str | None = None
    local_path: str | None = None
    message: str = ""


class CloneJobStatusResponse(BaseModel):
    job_id: str
    status: str
    phase: str
    files_done: int = 0
    files_total: int = 0
    message: str = ""
    error: str = ""
    repository_id: int | None = None


class RepositoryListItem(BaseModel):
    id: int
    owner: str
    name: str
    clone_url: str
    local_path: str


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryListItem]
