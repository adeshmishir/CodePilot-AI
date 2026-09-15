from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.repository_file import (
    FileListResponse,
    FileReadNotFound,
    FileReadResponse,
    RepositoryFileEntry,
)
from app.services.repository.manifest_service import (
    RepositoryManifestService,
)


router = APIRouter(
    prefix="/api/repositories/{repository_id}",
    tags=["Files"]
)


def _get_repository(db: Session, repository_id: int) -> RepositoryModel:
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

    return repository


def _manifest(db: Session) -> RepositoryManifestService:
    return RepositoryManifestService(db)


@router.get("/files", response_model=FileListResponse)
def list_repository_files(
    repository_id: int,
    path_prefix: str | None = Query(
        default=None,
        description="Only list files under this repository-relative directory.",
    ),
    extension: str | None = Query(
        default=None,
        description="Only list files with this extension (without the dot).",
    ),
    status: str | None = Query(
        default=None,
        description="Only list files with this index status.",
    ),
    limit: int = Query(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of rows to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination.",
    ),
    db: Session = Depends(get_db),
):
    _get_repository(db, repository_id)

    return _manifest(db).list_files(
        repository_id=repository_id,
        path_prefix=path_prefix,
        extension=extension,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/files/{path:path}",
    response_model=FileReadResponse,
    responses={404: {"model": FileReadNotFound}},
)
def read_repository_file(
    repository_id: int,
    path: str,
    start_line: int | None = Query(
        default=None,
        ge=1,
        description="Read from this line (1-based).",
    ),
    end_line: int | None = Query(
        default=None,
        ge=1,
        description="Read up to this line (inclusive).",
    ),
    db: Session = Depends(get_db),
):
    _get_repository(db, repository_id)

    if start_line is not None and end_line is not None and end_line < start_line:
        raise HTTPException(
            status_code=400,
            detail="end_line must be greater than or equal to start_line",
        )

    result = _manifest(db).read_file(
        repository_id=repository_id,
        file_path=path,
        start_line=start_line,
        end_line=end_line,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="File not found in the repository checkout.",
        )

    return FileReadResponse(**result)