import json

import pytest

from app.workflows.bug_detection.service import (
    BugDetectionError,
    BugDetectionService,
)


CHUNKS = [
    {
        "score": 0.9,
        "repository_id": 1,
        "file_path": "frontend/lib/hooks/useWebSocket.ts",
        "symbol_name": "connect",
        "symbol_type": "function",
        "start_line": 10,
        "end_line": 38,
        "content": "const connect = () => {\n  ws = new WebSocket(url)\n}",
    }
]

VALID_FINDING = {
    "title": "Missing URL validation",
    "severity": "medium",
    "description": "The WebSocket URL is built without validation.",
    "file_path": "frontend/lib/hooks/useWebSocket.ts",
    "start_line": 10,
    "end_line": 38,
    "evidence": "ws = new WebSocket(url)",
    "recommendation": "Validate the URL before opening the socket.",
}


class FakeRetrievalService:
    def __init__(self, results=None):
        self.results = results
        self.calls = []

    def search(self, query, repository_id, limit=8):
        self.calls.append((query, repository_id, limit))
        return self.results if self.results is not None else CHUNKS


class FakeContextBuilder:
    def __init__(self):
        self.calls = []

    def build(self, results):
        self.calls.append(results)
        return "--- FILE: frontend/lib/hooks/useWebSocket.ts ---\ncode"


class FakeGroqService:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


def make_service(response=None, results=None):
    retrieval = FakeRetrievalService(results)
    context = FakeContextBuilder()
    groq = FakeGroqService(
        response if response is not None else json.dumps(
            {"findings": []}
        )
    )

    service = BugDetectionService(
        retrieval_service=retrieval,
        context_builder=context,
        groq_service=groq,
    )

    return service, retrieval, context, groq


def test_retrieval_receives_query_repository_and_limit():
    service, retrieval, _, groq = make_service()

    service.analyze(query="websocket bugs", repository_id=1, limit=6)

    assert retrieval.calls == [("websocket bugs", 1, 6)]


def test_findings_are_converted_to_schema():
    response = json.dumps({"findings": [VALID_FINDING]})
    service, _, _, _ = make_service(response)

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert len(result["findings"]) == 1

    finding = result["findings"][0]

    assert finding["title"] == "Missing URL validation"
    assert finding["severity"] == "medium"
    assert finding["file_path"] == "frontend/lib/hooks/useWebSocket.ts"
    assert finding["start_line"] == 10
    assert finding["end_line"] == 38


def test_empty_findings_are_valid():
    service, _, _, _ = make_service(json.dumps({"findings": []}))

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert result["findings"] == []


def test_malformed_json_raises_controlled_error():
    service, _, _, _ = make_service("this is not json")

    with pytest.raises(BugDetectionError):
        service.analyze(query="websocket bugs", repository_id=1, limit=8)


def test_invalid_response_shape_raises_controlled_error():
    service, _, _, _ = make_service('{"results": []}')

    with pytest.raises(BugDetectionError):
        service.analyze(query="websocket bugs", repository_id=1, limit=8)


def test_findings_not_referencing_retrieved_files_are_dropped():
    hallucinated = dict(VALID_FINDING)
    hallucinated["file_path"] = "src/fabricated.py"

    response = json.dumps(
        {"findings": [VALID_FINDING, hallucinated]}
    )
    service, _, _, _ = make_service(response)

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert len(result["findings"]) == 1
    assert (
        result["findings"][0]["file_path"]
        == "frontend/lib/hooks/useWebSocket.ts"
    )


def test_findings_with_invalid_severity_are_dropped():
    invalid = dict(VALID_FINDING)
    invalid["severity"] = "severe"

    response = json.dumps({"findings": [invalid]})
    service, _, _, _ = make_service(response)

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert result["findings"] == []


def test_findings_with_missing_fields_are_dropped():
    incomplete = dict(VALID_FINDING)
    del incomplete["recommendation"]

    response = json.dumps({"findings": [incomplete]})
    service, _, _, _ = make_service(response)

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert result["findings"] == []


def test_markdown_fenced_json_is_parsed():
    response = f"```json\n{json.dumps({'findings': [VALID_FINDING]})}\n```"
    service, _, _, _ = make_service(response)

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert len(result["findings"]) == 1


def test_context_is_built_from_retrieved_chunks():
    service, _, context, groq = make_service()

    service.analyze(query="websocket bugs", repository_id=1, limit=8)

    assert context.calls == [CHUNKS]
    assert "websocket bugs" in groq.calls[0][1]
    assert "useWebSocket.ts" in groq.calls[0][1]


def test_empty_retrieval_returns_empty_findings_without_llm_call():
    service, _, _, groq = make_service(results=[])

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    assert result["findings"] == []
    assert result["sources"] == []
    assert groq.calls == []


def test_sources_preserve_retrieval_metadata():
    service, _, _, _ = make_service()

    result = service.analyze(
        query="websocket bugs",
        repository_id=1,
        limit=8,
    )

    source = result["sources"][0]

    assert source["file_path"] == "frontend/lib/hooks/useWebSocket.ts"
    assert source["symbol_name"] == "connect"
    assert source["start_line"] == 10
    assert source["end_line"] == 38
    assert source["score"] == 0.9
