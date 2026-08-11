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

    owner = result["owner"]
    repository_name = result["repository"]

    repository = (
        db.query(RepositoryModel)
        .filter(
            RepositoryModel.owner == owner,
            RepositoryModel.name == repository_name
        )
        .first()
    )

    if repository is None:
        repository = RepositoryModel(
            owner=owner,
            name=repository_name,
            clone_url=str(request.url),
            local_path=result["local_path"]
        )

        db.add(repository)
        db.commit()
        db.refresh(repository)

        try:
            index_result = repository_service.index_repository(
                repository_id=repository.id,
                repository_path=repository.local_path,
                db=db
            )
        except Exception:
            repository_service.cleanup_repository(
                db,
                repository,
                remove_checkout=True,
            )
            raise

        message = (
            f"Cloned and indexed {index_result['files_discovered']} files "
            f"into {index_result['chunks_created']} chunks and "
            f"{index_result['vectors_indexed']} vectors."
        )
    else:
        needs_index = not (
            repository_service.count_chunks(
                repository_id=repository.id,
                db=db,
            ) > 0
            and repository_service.count_vectors(
                repository_id=repository.id,
            ) > 0
        )

        if needs_index:
            index_result = repository_service.index_repository(
                repository_id=repository.id,
                repository_path=repository.local_path,
                db=db
            )

            message = (
                f"Repository recovered and re-indexed "
                f"{index_result['files_discovered']} files into "
                f"{index_result['chunks_created']} chunks and "
                f"{index_result['vectors_indexed']} vectors."
            )
        else:
            message = "Repository already exists and is up to date."

    return {
        "success": True,
        "id": repository.id,
        "repository": repository.name,
        "owner": repository.owner,
        "local_path": repository.local_path,
        "message": message,
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


@router.delete(
    "/{repository_id}",
)
def delete_repository(
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

    repository_service.cleanup_repository(
        db,
        repository,
        remove_checkout=True,
    )

    return {
        "success": True,
        "message": "Repository deleted.",
    }
