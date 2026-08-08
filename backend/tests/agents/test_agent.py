import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.agent import AgentService
from app.config.settings import settings
from app.database.base import Base
from app.models.code_chunk import CodeChunkModel


THREE_STEP_PLAN = json.dumps(
    [
        {
            "description": "List repository files",
            "tool": "list_repository_files",
            "arguments": {},
        },
        {
            "description": "Search WebSocket code",
            "tool": "search_repository",
            "arguments": {"query": "WebSocket price updates"},
        },
        {
            "description": "Inspect the hook",
            "tool": "get_code_context",
            "arguments": {
                "file_path": "frontend/lib/hooks/useWebSocket.ts"
            },
        },
    ]
)

SIX_STEP_PLAN = json.dumps(
    [
        {
            "description": f"Step {index}",
            "tool": "list_repository_files",
            "arguments": {},
        }
        for index in range(6)
    ]
)

UNKNOWN_TOOL_PLAN = json.dumps(
    [
        {
            "description": "Run shell",
            "tool": "shell",
            "arguments": {},
        }
    ]
)

MISSING_QUERY_PLAN = json.dumps(
    [
        {
            "description": "Search with no query",
            "tool": "search_repository",
            "arguments": {},
        }
    ]
)


class FakeRetrievalService:
    def search(self, query, repository_id, limit=5):
        return [
            {
                "score": 0.9,
                "repository_id": repository_id,
                "file_path": "frontend/lib/hooks/useWebSocket.ts",
                "symbol_name": "connect",
                "symbol_type": "function",
                "start_line": 10,
                "end_line": 38,
                "content": "const connect = () => {}",
            }
        ]


class FakeGroqService:
    def __init__(self, plan=THREE_STEP_PLAN, answer="Final answer"):
        self.plan = plan
        self.answer = answer
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))

        if len(self.calls) == 1:
            return self.plan

        return self.answer


def make_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    session.add(
        CodeChunkModel(
            repository_id=1,
            file_path="frontend/lib/hooks/useWebSocket.ts",
            symbol_name="connect",
            symbol_type="function",
            start_line=10,
            end_line=38,
            content="const connect = () => {}",
        )
    )
    session.commit()

    return session


def make_service(groq: FakeGroqService | None = None):
    return AgentService(
        groq_service=groq or FakeGroqService(),
        retrieval_service=FakeRetrievalService(),
    )


def run(db, service, **kwargs):
    return service.run(
        db=db,
        repository_id=1,
        query="Explain how WebSocket price updates work",
        **kwargs,
    )


def test_plan_generated_and_tools_executed():
    db = make_db()
    service = make_service()

    result = run(db, service)

    assert result["answer"] == "Final answer"

    assert result["plan"] == [
        "List repository files",
        "Search WebSocket code",
        "Inspect the hook",
    ]

    assert len(result["tool_calls"]) == 3

    names = [call["tool"] for call in result["tool_calls"]]

    assert names == [
        "list_repository_files",
        "search_repository",
        "get_code_context",
    ]


def test_tool_calls_record_arguments_repository_and_observation():
    db = make_db()
    service = make_service()

    result = run(db, service)

    search_call = result["tool_calls"][1]

    assert search_call["arguments"]["query"] == "WebSocket price updates"
    assert search_call["arguments"]["repository_id"] == 1
    assert search_call["observation"]


def test_observations_are_recorded():
    db = make_db()
    service = make_service()

    result = run(db, service)

    assert len(result["observations"]) >= len(result["tool_calls"])
    assert any(
        "useWebSocket.ts" in observation
        for observation in result["observations"]
    )


def test_max_steps_is_respected():
    db = make_db()
    service = make_service(FakeGroqService(plan=SIX_STEP_PLAN))

    result = run(db, service, max_steps=2)

    assert len(result["tool_calls"]) == 2


def test_requested_max_steps_is_clamped_to_configuration():
    db = make_db()
    service = make_service(FakeGroqService(plan=SIX_STEP_PLAN))

    result = run(db, service, max_steps=100)

    assert len(result["tool_calls"]) == settings.AGENT_MAX_STEPS


def test_unknown_tool_is_rejected():
    db = make_db()
    service = make_service(FakeGroqService(plan=UNKNOWN_TOOL_PLAN))

    result = run(db, service)

    assert result["tool_calls"] == []
    assert any("unknown" in obs.lower() for obs in result["observations"])
    assert "shell" in " ".join(result["observations"])
    assert result["answer"] == "Final answer"


def test_invalid_planner_output_is_safe():
    db = make_db()
    service = make_service(FakeGroqService(plan="not json"))

    result = run(db, service)

    assert result["tool_calls"] == []
    assert any("json" in obs.lower() for obs in result["observations"])
    assert result["answer"] == "Final answer"


def test_tool_failure_is_handled():
    db = make_db()
    service = make_service(FakeGroqService(plan=MISSING_QUERY_PLAN))

    result = run(db, service)

    assert result["tool_calls"] == []
    assert any(
        "search_repository" in obs and "failed" in obs
        for obs in result["observations"]
    )
    assert result["answer"] == "Final answer"


def test_all_tool_calls_target_the_requested_repository():
    db = make_db()
    service = make_service(FakeGroqService(plan=SIX_STEP_PLAN))

    result = run(db, service)

    assert result["tool_calls"]
    assert all(
        call["arguments"]["repository_id"] == 1
        for call in result["tool_calls"]
    )


GUESSED_PATH_PLAN = json.dumps(
    [
        {
            "description": "Inspect a guessed file",
            "tool": "get_code_context",
            "arguments": {
                "file_path": "path/to/guessed/file.ts"
            },
        }
    ]
)


def test_guessed_code_context_path_is_skipped():
    db = make_db()
    service = make_service(FakeGroqService(plan=GUESSED_PATH_PLAN))

    result = run(db, service)

    assert result["tool_calls"] == []
    assert any(
        "not found" in obs and "guessed" in obs
        for obs in result["observations"]
    )
    assert result["answer"] == "Final answer"


def test_real_code_context_path_is_executed():
    db = make_db()
    service = make_service(FakeGroqService(plan=THREE_STEP_PLAN))

    result = run(db, service)

    names = [call["tool"] for call in result["tool_calls"]]

    assert names == [
        "list_repository_files",
        "search_repository",
        "get_code_context",
    ]
