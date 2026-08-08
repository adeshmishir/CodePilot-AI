from pydantic import BaseModel, HttpUrl


class CloneRepositoryRequest(BaseModel):
    url: HttpUrl


class CloneRepositoryResponse(BaseModel):
    success: bool
    id: int
    repository: str
    owner: str
    local_path: str
    message: str


class RepositoryListItem(BaseModel):
    id: int
    owner: str
    name: str
    clone_url: str
    local_path: str


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryListItem]
