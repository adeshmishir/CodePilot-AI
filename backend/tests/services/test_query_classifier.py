import pytest

from app.services.rag.query_classifier import (
    QueryClassifier,
    QueryIntent,
)


@pytest.fixture
def classifier():
    return QueryClassifier()


def test_greetings_are_general(classifier):
    for query in (
        "hello",
        "Hello",
        "hi",
        "hey",
        "hey there",
        "good morning",
        "hi, how are you?",
    ):
        assert classifier.classify(query) == QueryIntent.GENERAL, query


def test_identity_questions_are_general(classifier):
    for query in (
        "who are you?",
        "what can you do?",
        "what do you do?",
        "what is your name?",
        "are you an AI?",
        "who made you?",
        "tell me about yourself",
    ):
        assert classifier.classify(query) == QueryIntent.GENERAL, query


def test_small_talk_is_general(classifier):
    for query in (
        "thanks",
        "thank you",
        "ok",
        "thanks a lot",
        "see you later",
    ):
        assert classifier.classify(query) == QueryIntent.GENERAL, query


def test_general_code_requests_are_general(classifier):
    for query in (
        "give me a C++ sum function",
        "write a python function to compute fibonacci",
        "how do I write a merge sort in go",
        "write me a JavaScript regex for emails",
        "can you show me a SQL query for joining tables",
    ):
        assert classifier.classify(query) == QueryIntent.GENERAL, query


def test_repository_questions_require_context(classifier):
    for query in (
        "Where is authentication handled?",
        "how does auth work?",
        "auth",
        "authentication",
        "find the bug in payment.js",
        "how does the API server start in this project",
        "give me a list of files in this repo",
        "what does useWebSocket do in src/",
        "explain the module structure",
    ):
        assert classifier.classify(query) == QueryIntent.REPOSITORY, query
