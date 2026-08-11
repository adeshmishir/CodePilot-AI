import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db
from app.models.repository import RepositoryModel
from app.services.github.git_service import git_service
from app.services.repository.clone_progress import (
    CloneCancelledError,
    clone_progress,
)
from app.services.repository.repository_service import repository_service
from app.schemas.repository import (
    CloneJobStatusResponse,
    CloneRepositoryRequest,
    CloneRepositoryResponse,
    RepositoryListItem,
    RepositoryListResponse,
)

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"]
)


def _friendly_clone_error(error: Exception) -> str:
    message = getattr(error, "message", None) or str(error)
    detail = getattr(error, "detail", None)
    if detail:
        return f"{message} {detail}".strip()
    return message or "Repository clone failed."


def _run_clone_job(
    job_id: str,
    url: str,
    session_factory=None,
) -> None:
    """Clone and index a repository in a background thread, reporting
    progress through the shared store."""
    db = (session_factory or SessionLocal)()

    repository = None
    clone_succeeded = False

    try:
        clone_progress.update(
            job_id,
            phase="cloning",
            message="Cloning repository...",
        )

        result = git_service.clone_repository(url)
        clone_succeeded = True

        if clone_progress.is_cancelled(job_id):
            raise CloneCancelledError()

        owner = result["owner"]
        repository_name = result["repository"]

        clone_progress.update(
            job_id,
            phase="cloning",
            message=f"Cloned {owner}/{repository_name}. Preparing to index...",
        )

        repository = (
            db.query(RepositoryModel)
            .filter(
                RepositoryModel.owner == owner,
                RepositoryModel.name == repository_name,
            )
            .first()
        )

        existed = repository is not None

        if repository is None:
            repository = RepositoryModel(
                owner=owner,
                name=repository_name,
                clone_url=url,
                local_path=result["local_path"],
            )
            db.add(repository)
            db.commit()
            db.refresh(repository)
            needs_index = True
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
            clone_progress.update(
                job_id,
                phase="indexing",
                message="Indexing repository code...",
            )

            def _report(done: int, total: int) -> None:
                if clone_progress.is_cancelled(job_id):
                    raise CloneCancelledError()
                clone_progress.update(
                    job_id,
                    files_done=done,
                    files_total=total,
                )

            index_result = repository_service.index_repository(
                repository_id=repository.id,
                repository_path=repository.local_path,
                db=db,
                progress=_report,
            )

            if existed:
                message = (
                    f"Repository recovered and re-indexed "
                    f"{index_result['files_discovered']} files into "
                    f"{index_result['chunks_created']} chunks and "
                    f"{index_result['vectors_indexed']} vectors."
                )
            else:
                message = (
                    f"Cloned and indexed {index_result['files_discovered']} "
                    f"files into {index_result['chunks_created']} chunks and "
                    f"{index_result['vectors_indexed']} vectors."
                )
        else:
            message = "Repository already exists and is up to date."

        clone_progress.update(
            job_id,
            status="done",
            phase="indexing",
            message=message,
            repository_id=repository.id,
        )
    except CloneCancelledError:
        db.rollback()

        if repository is not None:
            try:
                repository_service.cleanup_repository(
                    db,
                    repository,
                    remove_checkout=True,
                )
            except Exception as cleanup_error:
                print(
                    f"Failed cleaning up cancelled clone job {job_id}: "
                    f"{cleanup_error}"
                )

        clone_progress.update(
            job_id,
            status="cancelled",
            error="",
            message="Clone cancelled.",
        )
    except Exception as error:
        db.rollback()

        if repository is not None and clone_succeeded:
            try:
                repository_service.cleanup_repository(
                    db,
                    repository,
                    remove_checkout=True,
                )
            except Exception as cleanup_error:
                print(
                    f"Failed cleaning up failed clone job {job_id}: "
                    f"{cleanup_error}"
                )

        clone_progress.update(
            job_id,
            status="error",
            error=_friendly_clone_error(error),
        )
    finally:
        db.close()


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


@router.get(
    "/clone/status/{job_id:path}",
    response_model=CloneJobStatusResponse,
)
def clone_status(job_id: str):
    job = clone_progress.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Clone job not found",
        )

    return job


@router.post("/clone/cancel/{job_id:path}")
def cancel_clone(job_id: str):
    cancelled = clone_progress.cancel(job_id)

    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail="No active clone job found",
        )

    return {
        "success": True,
        "message": "Clone cancelled.",
    }


@router.post(
    "/clone",
    response_model=CloneRepositoryResponse
)
def clone_repository(
    request: CloneRepositoryRequest,
    db: Session = Depends(get_db)
):
    owner, repository_name = git_service._extract_repository_info(
        str(request.url)
    )

    job_id = f"{owner}/{repository_name}"

    existing = (
        db.query(RepositoryModel)
        .filter(
            RepositoryModel.owner == owner,
            RepositoryModel.name == repository_name,
        )
        .first()
    )

    healthy = (
        existing is not None
        and repository_service.count_chunks(
            repository_id=existing.id,
            db=db,
        ) > 0
        and repository_service.count_vectors(
            repository_id=existing.id,
        ) > 0
    )

    if healthy:
        return {
            "success": True,
            "id": existing.id,
            "repository": existing.name,
            "owner": existing.owner,
            "local_path": existing.local_path,
            "message": "Repository already exists and is up to date.",
        }

    if clone_progress.is_running(job_id):
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "job_id": job_id,
                "status": "running",
                "repository": repository_name,
                "owner": owner,
                "message": "Clone already in progress.",
            },
        )

    clone_progress.start(job_id)

    threading.Thread(
        target=_run_clone_job,
        args=(job_id, str(request.url)),
        daemon=True,
    ).start()

    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "job_id": job_id,
            "status": "running",
            "repository": repository_name,
            "owner": owner,
            "message": "Clone started.",
        },
    )


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
