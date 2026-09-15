from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural language question about the repository."
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of retrieved code chunks to use."
    )


class ChatSource(BaseModel):
    file_path: str
    symbol_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
