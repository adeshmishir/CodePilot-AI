from app.services.rag.context_builder import ContextBuilder


RESULT_A = {
    "score": 0.82,
    "repository_id": 1,
    "file_path": "src/auth/service.py",
    "symbol_name": "authenticate",
    "symbol_type": "function",
    "start_line": 42,
    "end_line": 45,
    "content": "def authenticate():\n    return True\n",
}

RESULT_B = {
    "score": 0.71,
    "repository_id": 1,
    "file_path": "src/db.py",
    "symbol_name": "connect",
    "symbol_type": "function",
    "start_line": 1,
    "end_line": 3,
    "content": "def connect():\n    pass\n",
}


def test_build_formats_chunks_with_metadata():
    builder = ContextBuilder(max_chars=100000)

    context = builder.build([RESULT_A])

    assert "--- FILE: src/auth/service.py ---" in context
    assert "Symbol: authenticate" in context
    assert "Type: function" in context
    assert "Lines: 42-45" in context
    assert "def authenticate():" in context


def test_build_preserves_chunk_order():
    builder = ContextBuilder(max_chars=100000)

    context = builder.build([RESULT_A, RESULT_B])

    assert context.index("src/auth/service.py") < context.index("src/db.py")


def test_build_separates_chunks():
    builder = ContextBuilder(max_chars=100000)

    context = builder.build([RESULT_A, RESULT_B])

    assert context.count("--- FILE:") == 2


def test_build_respects_context_size_limit():
    builder = ContextBuilder(max_chars=len(RESULT_A["content"]))

    context = builder.build([RESULT_A, RESULT_B])

    assert len(context) <= builder.max_chars
    assert "src/db.py" not in context


def test_build_keeps_highest_ranked_first_when_limited():
    small_budget = len(
        f"{builder_header(RESULT_A)}\n{RESULT_A['content']}"
    ) + 5

    builder = ContextBuilder(max_chars=small_budget)

    context = builder.build([RESULT_A, RESULT_B])

    assert "src/auth/service.py" in context
    assert "src/db.py" not in context


def builder_header(result: dict) -> str:
    return (
        f"--- FILE: {result['file_path']} ---\n"
        f"Symbol: {result['symbol_name']}\n"
        f"Type: {result['symbol_type']}\n"
        f"Lines: {result['start_line']}-{result['end_line']}"
    )


def test_build_is_deterministic():
    builder = ContextBuilder(max_chars=100000)

    first = builder.build([RESULT_A, RESULT_B])
    second = builder.build([RESULT_A, RESULT_B])

    assert first == second
