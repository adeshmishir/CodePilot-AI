import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.bug_detection import (
    BugDetectionRequest,
    BugDetectionResponse,
    BugDetectionSource,
    BugFinding,
)
from app.workflows.bug_detection.service import (
    BugDetectionService,
    get_bug_detection_service,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/repositories/{repository_id}",
    tags=["Bug Detection"]
)


@router.post(
    "/bugs",
    response_model=BugDetectionResponse
)
def detect_bugs(
    repository_id: int,
    request: BugDetectionRequest,
    db: Session = Depends(get_db),
    service: BugDetectionService = Depends(get_bug_detection_service),
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

    try:
        result = service.analyze(
            query=request.query,
            repository_id=repository_id,
            limit=request.limit,
        )
    except Exception as error:
        logger.error(
            "Bug detection failed for repository %s: %s",
            repository_id,
            error,
        )
        raise HTTPException(
            status_code=500,
            detail="Bug analysis failed to complete.",
        ) from error

    return BugDetectionResponse(
        findings=[
            BugFinding(**finding)
            for finding in result["findings"]
        ],
        sources=[
            BugDetectionSource(**source)
            for source in result["sources"]
        ],
    )
