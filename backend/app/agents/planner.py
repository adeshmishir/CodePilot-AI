import json
import re

from app.agents.prompts import PLANNER_PROMPT, planner_user_prompt
from app.services.llm.groq_service import GroqService


class PlanStep:
    def __init__(
        self,
        description: str,
        tool: str,
        arguments: dict,
    ):
        self.description = description
        self.tool = tool
        self.arguments = arguments


class InvalidPlanError(Exception):
    pass


class Planner:
    """Convert a developer request into a structured, validated plan."""

    def __init__(
        self,
        groq_service: GroqService,
        tool_schemas: list[dict],
    ):
        self.groq_service = groq_service
        self.tool_schemas = tool_schemas
        self._tool_names = {
            schema["name"] for schema in tool_schemas
        }

    def create_plan(
        self,
        query: str,
        max_steps: int,
    ) -> list[PlanStep]:
        raw = self.groq_service.generate(
            system_prompt=PLANNER_PROMPT,
            user_prompt=planner_user_prompt(query, self.tool_schemas),
        )

        steps = self._parse_steps(raw)
        self._validate_steps(steps)

        return [
            PlanStep(
                description=step["description"],
                tool=step["tool"],
                arguments=step.get("arguments", {}),
            )
            for step in steps[:max_steps]
        ]

    def _parse_steps(self, raw: str) -> list[dict]:
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidPlanError(
                "Planner returned output that is not valid JSON."
            ) from error

        if not isinstance(parsed, list) or len(parsed) == 0:
            raise InvalidPlanError(
                "Planner returned an empty or invalid plan."
            )

        return parsed

    def _validate_steps(self, steps: list[dict]) -> None:
        for step in steps:
            if not isinstance(step, dict):
                raise InvalidPlanError(
                    "Planner returned a plan step that is not an object."
                )

            description = step.get("description")
            tool = step.get("tool")
            arguments = step.get("arguments", {})

            if not isinstance(description, str) or not description.strip():
                raise InvalidPlanError(
                    "Planner returned a step without a description."
                )

            if not isinstance(tool, str) or tool not in self._tool_names:
                raise InvalidPlanError(
                    f"Planner returned an unknown or missing tool: "
                    f"{tool!r}."
                )

            if not isinstance(arguments, dict):
                raise InvalidPlanError(
                    f"Planner returned invalid arguments for tool "
                    f"'{tool}'."
                )
