from pydantic import BaseModel, Field


class GitHubPullRequest(BaseModel):
    number: int
    title: str
    author: str
    state: str
    created_at: str | None = None
    updated_at: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    head_branch: str | None = None
    base_branch: str | None = None
    url: str | None = None


class PullRequestListResponse(BaseModel):
    pull_requests: list[GitHubPullRequest]
    needs_github_token: bool = False


class ReviewComment(BaseModel):
    file_path: str
    line: int | None = None
    severity: str
    category: str
    message: str


class PullRequestReview(BaseModel):
    pull_request_number: int
    title: str
    summary: str
    comments: list[ReviewComment]


class GitHubIssue(BaseModel):
    number: int
    title: str
    author: str
    state: str
    labels: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    url: str | None = None


class IssueListResponse(BaseModel):
    issues: list[GitHubIssue]
    needs_github_token: bool = False


class IssueTriageEntry(BaseModel):
    issue_number: int
    title: str
    state: str
    author: str
    category: str
    severity: str
    suggested_labels: list[str] = Field(default_factory=list)
    summary: str
    labels: list[str] = Field(default_factory=list)
    created_at: str | None = None
    url: str | None = None


class IssueTriageResponse(BaseModel):
    issues: list[IssueTriageEntry]
    needs_github_token: bool = False
