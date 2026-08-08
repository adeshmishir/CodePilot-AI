from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BugDetectionRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "Area of the repository to analyze for potential bugs."
        ),
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=20,
        description=(
            "Number of repository code chunks to retrieve and analyze."
        ),
    )


class BugFinding(BaseModel):
    title: str
    severity: Severity
    description: str
    file_path: str
    start_line: int
    end_line: int
    evidence: str
    recommendation: str


class BugDetectionSource(BaseModel):
    file_path: str
    symbol_name: str
    start_line: int
    end_line: int
    score: float


class BugDetectionResponse(BaseModel):
    findings: list[BugFinding]
    sources: list[BugDetectionSource]
