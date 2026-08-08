from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query to search for."
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results to return."
    )


class SearchResult(BaseModel):
    score: float
    repository_id: int
    file_path: str
    symbol_name: str
    symbol_type: str
    start_line: int
    end_line: int
    content: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
