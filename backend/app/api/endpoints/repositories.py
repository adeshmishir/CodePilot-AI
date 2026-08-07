from fastapi import APIRouter

from app.services.github.git_service import git_service
from app.schemas.repository import (
    CloneRepositoryRequest,
    CloneRepositoryResponse,
)


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"]
)


@router.post(
    "/clone",
    response_model=CloneRepositoryResponse
)
async def clone_repository(
    request: CloneRepositoryRequest
):
    result = git_service.clone_repository(
        str(request.url)
    )

    return result
