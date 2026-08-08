from pydantic import BaseModel, Field

from app.config.settings import settings


class AgentRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Task or question about the repository."
    )
    max_steps: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Maximum number of tool steps to execute. Clamped to the "
            f"configured maximum of {settings.AGENT_MAX_STEPS}."
        ),
    )


class AgentToolCall(BaseModel):
    tool: str
    arguments: dict
    observation: str


class AgentResponse(BaseModel):
    answer: str
    plan: list[str]
    tool_calls: list[AgentToolCall]
    observations: list[str]
