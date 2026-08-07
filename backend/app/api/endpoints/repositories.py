from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.repository_service import repository_service
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
    request: CloneRepositoryRequest,
    db: Session = Depends(get_db)
):
    result = git_service.clone_repository(
        str(request.url)
    )

    repository = (
        db.query(RepositoryModel)
        .filter(
            RepositoryModel.owner == result["owner"],
            RepositoryModel.name == result["repository"]
        )
        .first()
    )

    if repository is None:
        repository = RepositoryModel(
            owner=result["owner"],
            name=result["repository"],
            clone_url=str(request.url),
            local_path=result["local_path"]
        )

        db.add(repository)
        db.commit()
        db.refresh(repository)

        repository_service.index_repository(
            repository_id=repository.id,
            repository_path=repository.local_path,
            db=db
        )

    return result
