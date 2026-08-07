from datetime import datetime

from pydantic import BaseModel


class RepositoryModel(BaseModel):
    id: int | None = None
    owner: str
    name: str
    clone_url: str
    local_path: str
    created_at: datetime
    updated_at: datetime