from pydantic import BaseModel, HttpUrl


class CloneRepositoryRequest(BaseModel):
    url: HttpUrl


class CloneRepositoryResponse(BaseModel):
    success: bool
    repository: str
    owner: str
    local_path: str
    message: str