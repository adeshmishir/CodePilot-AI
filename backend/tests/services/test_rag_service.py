from app.services.rag.rag_service import RAGService


RETRIEVAL_RESULTS = [
    {
        "score": 0.82,
        "repository_id": 1,
        "file_path": "src/auth/service.js",
        "symbol_name": "authenticateUser",
        "symbol_type": "function",
        "start_line": 42,
        "end_line": 71,
        "content": "async function authenticateUser() {}",
    },
    {
        "score": 0.71,
        "repository_id": 1,
        "file_path": "src/db.js",
        "symbol_name": "connect",
        "symbol_type": "function",
        "start_line": 1,
        "end_line": 10,
        "content": "function connect() {}",
    },
]


class FakeRetrievalService:
    def __init__(self, results=None):
        self.results = results or RETRIEVAL_RESULTS
        self.calls = []

    def search(self, query: str, repository_id: int, limit: int = 5):
        self.calls.append(
            {
                "query": query,
                "repository_id": repository_id,
                "limit": limit,
            }
        )
        return self.results


class FakeContextBuilder:
    def __init__(self):
        self.calls = []

    def build(self, results: list[dict]) -> str:
        self.calls.append(results)
        return "--- FILE: src/auth/service.js ---\n..."


class FakeGroqService:
    def __init__(self):
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return "Authentication is handled in src/auth/service.js"


def make_service():
    retrieval = FakeRetrievalService()
    context = FakeContextBuilder()
    groq = FakeGroqService()

    service = RAGService(
        retrieval_service=retrieval,
        context_builder=context,
        groq_service=groq,
    )

    return service, retrieval, context, groq


def test_answer_returns_answer_and_sources():
    service, _, _, _ = make_service()

    result = service.answer(
        query="Where is authentication handled?",
        repository_id=1,
        limit=5,
    )

    assert result["answer"] == (
        "Authentication is handled in src/auth/service.js"
    )
    assert len(result["sources"]) == 2

    source = result["sources"][0]

    assert source["file_path"] == "src/auth/service.js"
    assert source["symbol_name"] == "authenticateUser"
    assert source["start_line"] == 42
    assert source["end_line"] == 71
    assert source["score"] == 0.82


def test_answer_forwards_query_repository_and_limit():
    service, retrieval, _, _ = make_service()

    service.answer(
        query="how does auth work?",
        repository_id=7,
        limit=3,
    )

    assert retrieval.calls == [
        {
            "query": "how does auth work?",
            "repository_id": 7,
            "limit": 3,
        }
    ]


def test_answer_feeds_context_to_groq():
    service, retrieval, _, groq = make_service()

    service.answer(query="auth", repository_id=1, limit=5)

    assert len(groq.calls) == 1

    call = groq.calls[0]

    assert "auth" in call["user_prompt"]
    assert "--- FILE: src/auth/service.js ---" in call["user_prompt"]
    assert call["system_prompt"]


def test_answer_uses_context_builder_output():
    service, _, context, groq = make_service()

    service.answer(query="auth", repository_id=1, limit=5)

    assert context.calls == [RETRIEVAL_RESULTS]
    assert groq.calls[0]["user_prompt"].endswith(
        "--- FILE: src/auth/service.js ---\n..."
    )


def test_general_question_skips_retrieval():
    service, retrieval, context, groq = make_service()

    result = service.answer(
        query="hello",
        repository_id=1,
        limit=5,
    )

    assert retrieval.calls == []
    assert context.calls == []
    assert result["sources"] == []
    assert result["answer"] == (
        "Authentication is handled in src/auth/service.js"
    )


def test_general_code_request_skips_retrieval():
    service, retrieval, _, groq = make_service()

    result = service.answer(
        query="give me a C++ sum function",
        repository_id=1,
        limit=5,
    )

    assert retrieval.calls == []
    assert result["sources"] == []
    assert groq.calls[0]["user_prompt"] == "give me a C++ sum function"


def test_identity_question_skips_retrieval():
    service, retrieval, _, _ = make_service()

    result = service.answer(
        query="who are you?",
        repository_id=1,
        limit=5,
    )

    assert retrieval.calls == []
    assert result["sources"] == []
