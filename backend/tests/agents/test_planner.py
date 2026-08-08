import json

import pytest

from app.agents.planner import InvalidPlanError, PlanStep, Planner


TOOL_SCHEMAS = [
    {"name": "search_repository", "description": "Search code."},
    {"name": "list_repository_files", "description": "List files."},
    {"name": "get_code_context", "description": "Get code context."},
]


VALID_PLAN = json.dumps(
    [
        {
            "description": "Inspect repository structure",
            "tool": "list_repository_files",
            "arguments": {},
        },
        {
            "description": "Search authentication code",
            "tool": "search_repository",
            "arguments": {
                "query": "authentication login JWT",
                "limit": 5,
            },
        },
        {
            "description": "Read the auth service",
            "tool": "get_code_context",
            "arguments": {
                "file_path": "frontend/lib/auth/service.ts"
            },
        },
    ]
)


class FakeGroqService:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def make_planner(response: str = VALID_PLAN):
    return Planner(
        groq_service=FakeGroqService(response),
        tool_schemas=TOOL_SCHEMAS,
    )


def test_valid_plan_parses_into_steps():
    planner = make_planner()

    plan = planner.create_plan(query="auth", max_steps=5)

    assert len(plan) == 3
    assert all(isinstance(step, PlanStep) for step in plan)

    assert plan[0].description == "Inspect repository structure"
    assert plan[0].tool == "list_repository_files"
    assert plan[0].arguments == {}

    assert plan[1].tool == "search_repository"
    assert plan[1].arguments["query"] == "authentication login JWT"
    assert plan[1].arguments["limit"] == 5


def test_plan_is_truncated_to_max_steps():
    planner = make_planner()

    plan = planner.create_plan(query="auth", max_steps=2)

    assert len(plan) == 2


def test_unknown_tool_is_rejected():
    bad_plan = json.dumps(
        [
            {
                "description": "Run a shell command",
                "tool": "shell",
                "arguments": {},
            }
        ]
    )
    planner = make_planner(bad_plan)

    with pytest.raises(InvalidPlanError):
        planner.create_plan(query="auth", max_steps=5)


def test_invalid_json_is_rejected():
    planner = make_planner("this is not json")

    with pytest.raises(InvalidPlanError):
        planner.create_plan(query="auth", max_steps=5)


def test_empty_plan_is_rejected():
    planner = make_planner("[]")

    with pytest.raises(InvalidPlanError):
        planner.create_plan(query="auth", max_steps=5)


def test_non_list_output_is_rejected():
    planner = make_planner('{"plan": "do nothing"}')

    with pytest.raises(InvalidPlanError):
        planner.create_plan(query="auth", max_steps=5)


def test_markdown_fenced_json_is_parsed():
    planner = make_planner(f"```json\n{VALID_PLAN}\n```")

    plan = planner.create_plan(query="auth", max_steps=5)

    assert len(plan) == 3


def test_step_without_tool_is_rejected():
    bad_plan = json.dumps(
        [
            {
                "description": "Just think about it",
                "arguments": {},
            }
        ]
    )
    planner = make_planner(bad_plan)

    with pytest.raises(InvalidPlanError):
        planner.create_plan(query="auth", max_steps=5)


def test_planner_sends_tool_schemas_and_query():
    fake = FakeGroqService(VALID_PLAN)
    planner = Planner(
        groq_service=fake,
        tool_schemas=TOOL_SCHEMAS,
    )

    planner.create_plan(query="auth", max_steps=5)

    assert len(fake.calls) == 1

    system_prompt, user_prompt = fake.calls[0]

    assert "planning" in system_prompt.lower()
    assert "auth" in user_prompt
    assert "search_repository" in user_prompt
    assert "list_repository_files" in user_prompt
    assert "get_code_context" in user_prompt
