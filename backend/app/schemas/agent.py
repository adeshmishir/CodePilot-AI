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
    mode: str = Field(
        default="single",
        pattern="^(single|multi)$",
        description=(
            "Execution mode: 'single' runs the planning agent, "
            "'multi' runs the multi-agent orchestrator."
        ),
    )


class AgentToolCall(BaseModel):
    tool: str
    arguments: dict
    observation: str


class AgentContribution(BaseModel):
    name: str
    summary: str
    detail: str


class AgentResponse(BaseModel):
    answer: str
    plan: list[str]
    tool_calls: list[AgentToolCall]
    observations: list[str]
    agents: list[AgentContribution] = Field(
        default_factory=list,
        description=(
            "Specialist agent contributions. Populated when the "
            "request runs in multi-agent mode."
        ),
    )
