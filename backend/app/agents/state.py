from dataclasses import dataclass, field


@dataclass
class AgentState:
    repository_id: int
    user_query: str
    plan: list = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    retrieved_context: list[dict] = field(default_factory=list)
    final_answer: str | None = None

    def record_observation(self, observation: str) -> None:
        self.observations.append(observation)

    def record_tool_call(
        self,
        tool: str,
        arguments: dict,
        observation: str,
    ) -> None:
        self.tool_calls.append(
            {
                "tool": tool,
                "arguments": arguments,
                "observation": observation,
            }
        )

    def extend_context(self, results: list[dict]) -> None:
        self.retrieved_context.extend(results)
