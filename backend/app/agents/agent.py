import json
import logging
import threading

from sqlalchemy.orm import Session

from app.agents.planner import InvalidPlanError, Planner
from app.agents.prompts import FINAL_ANSWER_PROMPT, final_answer_user_prompt
from app.agents.state import AgentState
from app.config.settings import settings
from app.services.llm.groq_service import GroqService
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)
from app.tools.registry import ToolRegistry, build_tool_registry


logger = logging.getLogger(__name__)

OBSERVATION_MAX_CHARS = 2000


class AgentService:
    """Orchestrate planning, tool execution, and final reasoning."""

    def __init__(
        self,
        groq_service: GroqService,
        retrieval_service: RetrievalService,
    ):
        self.groq_service = groq_service
        self.retrieval_service = retrieval_service

    def run(
        self,
        db: Session,
        repository_id: int,
        query: str,
        max_steps: int | None = None,
    ) -> dict:
        step_limit = self._resolve_step_limit(max_steps)

        registry = build_tool_registry(
            db=db,
            retrieval_service=self.retrieval_service,
        )

        planner = Planner(
            groq_service=self.groq_service,
            tool_schemas=registry.schemas(),
        )

        state = AgentState(
            repository_id=repository_id,
            user_query=query,
        )

        try:
            plan = planner.create_plan(
                query=query,
                max_steps=step_limit,
            )
        except InvalidPlanError as error:
            state.record_observation(str(error))
            state.final_answer = self._generate_final_answer(state)
            return self._to_result(state)

        state.plan = plan

        for step in plan:
            if len(state.tool_calls) >= step_limit:
                break

            tool = registry.get(step.tool)

            if tool is None:
                state.record_observation(
                    f"Rejected unknown tool '{step.tool}'."
                )
                continue

            arguments = dict(step.arguments)
            arguments["repository_id"] = repository_id

            if step.tool == "get_code_context" and not self._file_exists(
                registry=registry,
                repository_id=repository_id,
                file_path=arguments.get("file_path"),
            ):
                state.record_observation(
                    "Skipped step: file "
                    f"{arguments.get('file_path')!r} was not found in "
                    "the repository; the planner likely guessed the path."
                )
                continue

            try:
                result = tool.execute(**arguments)
            except Exception as error:
                logger.error(
                    "Tool %s failed for repository %s: %s",
                    step.tool,
                    repository_id,
                    error,
                )
                state.record_observation(
                    f"Tool '{step.tool}' failed: {_safe_message(error)}"
                )
                break

            observation = _summarize(result)
            state.record_observation(observation)
            state.record_tool_call(
                tool=step.tool,
                arguments=arguments,
                observation=observation,
            )

            if step.tool == "search_repository":
                state.extend_context(result.get("results", []))

        state.final_answer = self._generate_final_answer(state)

        return self._to_result(state)

    def _file_exists(
        self,
        registry: ToolRegistry,
        repository_id: int,
        file_path: object,
    ) -> bool:
        if not isinstance(file_path, str) or not file_path.strip():
            return False

        files_tool = registry.get("list_repository_files")

        if files_tool is None:
            return True

        files = files_tool.execute(
            repository_id=repository_id
        ).get("files", [])

        return file_path in files

    def _resolve_step_limit(self, max_steps: int | None) -> int:
        if max_steps is None:
            return settings.AGENT_MAX_STEPS

        return min(max_steps, settings.AGENT_MAX_STEPS)

    def _generate_final_answer(self, state: AgentState) -> str:
        user_prompt = final_answer_user_prompt(
            query=state.user_query,
            repository_id=state.repository_id,
            observations=state.observations,
        )

        return self.groq_service.generate(
            system_prompt=FINAL_ANSWER_PROMPT,
            user_prompt=user_prompt,
        )

    def _to_result(self, state: AgentState) -> dict:
        return {
            "answer": state.final_answer or "",
            "plan": [step.description for step in state.plan],
            "tool_calls": state.tool_calls,
            "observations": state.observations,
        }


def _summarize(result: dict) -> str:
    text = json.dumps(result, ensure_ascii=False)

    if len(text) > OBSERVATION_MAX_CHARS:
        text = (
            text[:OBSERVATION_MAX_CHARS]
            + "... (observation truncated)"
        )

    return text


def _safe_message(error: Exception) -> str:
    message = str(error)

    if len(message) > 200:
        message = message[:200]

    return message or error.__class__.__name__


agent_service: AgentService | None = None
agent_service_lock = threading.Lock()


def get_agent_service() -> AgentService:
    global agent_service

    if agent_service is None:
        with agent_service_lock:
            if agent_service is None:
                agent_service = AgentService(
                    groq_service=GroqService(),
                    retrieval_service=get_retrieval_service(),
                )

    return agent_service
