import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.github import (
    GitHubIssue,
    GitHubPullRequest,
    IssueListResponse,
    IssueTriageEntry,
    IssueTriageResponse,
    PullRequestListResponse,
    PullRequestReview,
    ReviewComment,
)
from app.services.github.github_client import (
    GitHubApiError,
    GitHubAuthError,
    GitHubNotFoundError,
)
from app.services.github.issue_triage_service import (
    IssueTriageService,
    get_issue_triage_service,
)
from app.services.github.pr_review_service import (
    PullRequestReviewService,
    get_pull_request_review_service,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/repositories/{repository_id}/github",
    tags=["GitHub"]
)


def _needs_token() -> bool:
    return not bool(settings.GITHUB_TOKEN)


def _resolve_repository(
    db: Session,
    repository_id: int,
) -> RepositoryModel:
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


def _handle_github_error(error: Exception) -> None:
    if isinstance(error, GitHubAuthError):
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if isinstance(error, GitHubNotFoundError):
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    if isinstance(error, GitHubApiError):
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    logger.error("GitHub operation failed: %s", error)
    raise HTTPException(
        status_code=500,
        detail="The GitHub operation failed.",
    ) from error


@router.get(
    "/prs",
    response_model=PullRequestListResponse
)
def list_pull_requests(
    repository_id: int,
    db: Session = Depends(get_db),
):
    repository = _resolve_repository(db, repository_id)

    if _needs_token():
        return PullRequestListResponse(
            pull_requests=[],
            needs_github_token=True,
        )

    try:
        prs = GitHubClient().list_open_pull_requests(
            owner=repository.owner,
            repository=repository.name,
        )
    except GitHubApiError as error:
        _handle_github_error(error)

    return PullRequestListResponse(
        pull_requests=[
            GitHubPullRequest(
                number=pr.get("number"),
                title=pr.get("title"),
                author=(
                    pr.get("user", {}).get("login", "")
                    if isinstance(pr.get("user"), dict)
                    else ""
                ),
                state=pr.get("state"),
                created_at=pr.get("created_at"),
                updated_at=pr.get("updated_at"),
                additions=pr.get("additions", 0),
                deletions=pr.get("deletions", 0),
                changed_files=pr.get("changed_files", 0),
                head_branch=(
                    pr.get("head", {}).get("ref")
                    if isinstance(pr.get("head"), dict)
                    else None
                ),
                base_branch=(
                    pr.get("base", {}).get("ref")
                    if isinstance(pr.get("base"), dict)
                    else None
                ),
                url=pr.get("html_url"),
            )
            for pr in prs
        ],
    )


@router.post(
    "/prs/{pull_number}/review",
    response_model=PullRequestReview
)
def review_pull_request(
    repository_id: int,
    pull_number: int,
    db: Session = Depends(get_db),
    service: PullRequestReviewService = Depends(
        get_pull_request_review_service
    ),
):
    repository = _resolve_repository(db, repository_id)

    if _needs_token():
        raise HTTPException(
            status_code=400,
            detail=(
                "GITHUB_TOKEN is not configured. Add a GitHub personal "
                "access token to the .env file to review pull requests."
            ),
        )

    try:
        result = service.review(
            owner=repository.owner,
            repository=repository.name,
            pull_number=pull_number,
        )
    except GitHubApiError as error:
        _handle_github_error(error)
        raise HTTPException(status_code=500)

    return PullRequestReview(
        pull_request_number=result["pull_request_number"],
        title=result["title"],
        summary=result["summary"],
        comments=[
            ReviewComment(**comment)
            for comment in result["comments"]
        ],
    )


@router.get(
    "/issues",
    response_model=IssueListResponse
)
def list_issues(
    repository_id: int,
    db: Session = Depends(get_db),
    service: IssueTriageService = Depends(get_issue_triage_service),
):
    repository = _resolve_repository(db, repository_id)

    if _needs_token():
        return IssueListResponse(
            issues=[],
            needs_github_token=True,
        )

    try:
        issues = service.list_issues(
            owner=repository.owner,
            repository=repository.name,
        )
    except GitHubApiError as error:
        _handle_github_error(error)

    return IssueListResponse(
        issues=[
            GitHubIssue(**issue)
            for issue in issues
        ],
    )


@router.post(
    "/issues/triage",
    response_model=IssueTriageResponse
)
def triage_issues(
    repository_id: int,
    db: Session = Depends(get_db),
    service: IssueTriageService = Depends(get_issue_triage_service),
):
    repository = _resolve_repository(db, repository_id)

    if _needs_token():
        return IssueTriageResponse(
            issues=[],
            needs_github_token=True,
        )

    try:
        issues = service.triage(
            owner=repository.owner,
            repository=repository.name,
        )
    except GitHubApiError as error:
        _handle_github_error(error)

    return IssueTriageResponse(
        issues=[
            IssueTriageEntry(**issue)
            for issue in issues
        ],
    )
