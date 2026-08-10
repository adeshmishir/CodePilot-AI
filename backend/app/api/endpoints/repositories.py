from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.repository_service import repository_service
from app.schemas.repository import (
    CloneRepositoryRequest,
    CloneRepositoryResponse,
    RepositoryListItem,
    RepositoryListResponse,
)

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"]
)


@router.get(
    "",
    response_model=RepositoryListResponse
)
def list_repositories(
    db: Session = Depends(get_db)
):
    repositories = (
        db.query(RepositoryModel)
        .order_by(RepositoryModel.created_at.desc())
        .all()
    )

    return RepositoryListResponse(
        repositories=[
            RepositoryListItem(
                id=repository.id,
                owner=repository.owner,
                name=repository.name,
                clone_url=repository.clone_url,
                local_path=repository.local_path,
            )
            for repository in repositories
        ]
    )


@router.post(
    "/clone",
    response_model=CloneRepositoryResponse
)
def clone_repository(
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

    return {
        "success": result["success"],
        "id": repository.id,
        "repository": result["repository"],
        "owner": result["owner"],
        "local_path": result["local_path"],
        "message": result["message"],
    }


@router.post(
    "/{repository_id}/reindex",
    response_model=CloneRepositoryResponse
)
def reindex_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    repository = (
        db.query(RepositoryModel)
        .filter(RepositoryModel.id == repository_id)
        .first()
    )

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found"
        )

    result = repository_service.index_repository(
        repository_id=repository.id,
        repository_path=repository.local_path,
        db=db
    )

    return {
        "success": True,
        "id": repository.id,
        "repository": repository.name,
        "owner": repository.owner,
        "local_path": repository.local_path,
        "message": (
            f"Reindexed {result['files_discovered']} files into "
            f"{result['chunks_created']} chunks and "
            f"{result['vectors_indexed']} vectors."
        ),
    }
