import json
import logging
import re

from sqlalchemy.orm import Session

from app.agents.agent import AgentService, get_agent_service
from app.config.settings import settings
from app.services.llm.groq_service import GroqService
from app.services.rag.rag_service import RAGService, get_rag_service
from app.workflows.bug_detection.service import (
    BugDetectionService,
    get_bug_detection_service,
)
from app.workflows.multi_agent.prompts import (
    AGENT_DESCRIPTIONS,
    ROUTER_PROMPT,
    SYNTHESIS_PROMPT,
    router_user_prompt,
    synthesis_user_prompt,
)


logger = logging.getLogger(__name__)

VALID_AGENTS = {"researcher", "bug_hunter", "executor"}

DETAIL_MAX_CHARS = 3000


class MultiAgentError(Exception):
    pass


class MultiAgentOrchestrator:
    """Route a request to specialist agents and synthesize their output."""

    def __init__(
        self,
        groq_service: GroqService,
        rag_service: RAGService,
        bug_detection_service: BugDetectionService,
        agent_service: AgentService,
    ):
        self.groq_service = groq_service
        self.rag_service = rag_service
        self.bug_detection_service = bug_detection_service
        self.agent_service = agent_service

    def run(
        self,
        db: Session,
        repository_id: int,
        query: str,
        max_steps: int | None = None,
    ) -> dict:
        assigned = self._route(query)

        plan = []
        contributions = []
        observations: list[str] = []
        tool_calls: list[dict] = []

        for agent in assigned:
            plan.append(self._describe_assignment(agent))

            try:
                contribution = self._dispatch(
                    agent=agent,
                    db=db,
                    repository_id=repository_id,
                    query=query,
                    max_steps=max_steps,
                )
            except Exception as error:
                logger.error(
                    "Agent %s failed for repository %s: %s",
                    agent,
                    repository_id,
                    error,
                )
                observations.append(
                    f"Agent '{agent}' failed: {_safe_message(error)}"
                )
                contributions.append(
                    {
                        "name": agent,
                        "summary": "The agent failed to complete its "
                        "part.",
                        "detail": "",
                    }
                )
                continue

            contributions.append(contribution)

            observations.extend(contribution.get("observations", []))
            tool_calls.extend(contribution.get("tool_calls", []))

        answer = self._synthesize(query, contributions)

        return {
            "answer": answer,
            "plan": plan,
            "tool_calls": tool_calls,
            "observations": observations,
            "agents": [
                {
                    "name": contribution["name"],
                    "summary": contribution["summary"],
                    "detail": contribution["detail"],
                }
                for contribution in contributions
            ],
        }

    def _route(self, query: str) -> list[str]:
        raw = self.groq_service.generate(
            system_prompt=ROUTER_PROMPT,
            user_prompt=router_user_prompt(query),
        )

        try:
            data = self._parse_json(raw)
            agents = data.get("agents", [])
        except (MultiAgentError, AttributeError):
            agents = []

        valid = [
            agent
            for agent in agents
            if isinstance(agent, str) and agent in VALID_AGENTS
        ]

        if not valid:
            valid = ["researcher"]

        return valid[:2]

    def _dispatch(
        self,
        agent: str,
        db: Session,
        repository_id: int,
        query: str,
        max_steps: int | None,
    ) -> dict:
        if agent == "researcher":
            return self._run_researcher(repository_id, query)
        if agent == "bug_hunter":
            return self._run_bug_hunter(repository_id, query)
        if agent == "executor":
            return self._run_executor(db, repository_id, query, max_steps)
        raise MultiAgentError(f"Unknown agent '{agent}'.")

    def _run_researcher(
        self,
        repository_id: int,
        query: str,
    ) -> dict:
        result = self.rag_service.answer(
            query=query,
            repository_id=repository_id,
            limit=5,
        )

        detail = _truncate(result["answer"])
        sources = result.get("sources", [])

        if sources:
            referenced = ", ".join(
                f"{source.get('file_path')}:{source.get('start_line')}"
                for source in sources
                if source.get("file_path")
            )
            detail += f"\n\nReferenced files: {referenced}"

        return {
            "name": "researcher",
            "summary": "Researched the repository and produced an "
            "evidence-backed answer.",
            "detail": detail,
            "observations": [],
            "tool_calls": [],
        }

    def _run_bug_hunter(
        self,
        repository_id: int,
        query: str,
    ) -> dict:
        result = self.bug_detection_service.analyze(
            query=query,
            repository_id=repository_id,
            limit=8,
        )

        findings = result.get("findings", [])

        if not findings:
            detail = "No concrete bugs found in the analyzed code."
        else:
            lines = []
            for finding in findings:
                lines.append(
                    f"- [{finding['severity']}] {finding['title']} "
                    f"({finding['file_path']}:"
                    f"{finding['start_line']}-{finding['end_line']})"
                    f"\n  {finding['description']}"
                    f"\n  Recommendation: {finding['recommendation']}"
                )
            detail = "\n".join(lines)

        return {
            "name": "bug_hunter",
            "summary": f"Analyzed code and identified {len(findings)} "
            "potential bug(s).",
            "detail": detail,
            "observations": [],
            "tool_calls": [],
        }

    def _run_executor(
        self,
        db: Session,
        repository_id: int,
        query: str,
        max_steps: int | None,
    ) -> dict:
        result = self.agent_service.run(
            db=db,
            repository_id=repository_id,
            query=query,
            max_steps=max_steps,
        )

        return {
            "name": "executor",
            "summary": "Planned and executed tool-based investigation "
            "steps.",
            "detail": _truncate(result["answer"]),
            "observations": result["observations"],
            "tool_calls": result["tool_calls"],
        }

    def _synthesize(
        self,
        query: str,
        contributions: list[dict],
    ) -> str:
        if not contributions:
            return (
                "No specialist agent could process this request. "
                "Please try rephrasing it."
            )

        user_prompt = synthesis_user_prompt(query, contributions)

        return self.groq_service.generate(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=user_prompt,
        )

    def _describe_assignment(self, agent: str) -> str:
        description = AGENT_DESCRIPTIONS.get(agent, agent)

        return f"{agent}: {description}"

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            raise MultiAgentError(
                "Router produced invalid JSON."
            ) from error

        if not isinstance(parsed, dict):
            raise MultiAgentError(
                "Router produced a non-object response."
            )

        return parsed


def _truncate(text: str, max_chars: int = DETAIL_MAX_CHARS) -> str:
    if text is None:
        return ""

    if len(text) > max_chars:
        text = text[:max_chars] + "… (truncated)"

    return text


def _safe_message(error: Exception) -> str:
    message = str(error)

    if len(message) > 200:
        message = message[:200]

    return message or error.__class__.__name__


multi_agent_orchestrator: MultiAgentOrchestrator | None = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    global multi_agent_orchestrator

    if multi_agent_orchestrator is None:
        multi_agent_orchestrator = MultiAgentOrchestrator(
            groq_service=GroqService(),
            rag_service=get_rag_service(),
            bug_detection_service=get_bug_detection_service(),
            agent_service=get_agent_service(),
        )

    return multi_agent_orchestrator
