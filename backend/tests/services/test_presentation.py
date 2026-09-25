from app.agents.prompts import FINAL_ANSWER_PROMPT
from app.services.presentation import ANSWER_FORMATTING_GUIDELINES
from app.services.rag.rag_service import (
    GENERAL_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from app.workflows.multi_agent.prompts import SYNTHESIS_PROMPT


def test_chat_prompts_include_formatting_guidelines():
    assert "Response formatting guidelines" in SYSTEM_PROMPT
    assert ANSWER_FORMATTING_GUIDELINES in SYSTEM_PROMPT
    assert "Response formatting guidelines" in GENERAL_SYSTEM_PROMPT
    assert ANSWER_FORMATTING_GUIDELINES in GENERAL_SYSTEM_PROMPT


def test_agent_prompts_include_formatting_guidelines():
    assert ANSWER_FORMATTING_GUIDELINES in SYNTHESIS_PROMPT
    assert ANSWER_FORMATTING_GUIDELINES in FINAL_ANSWER_PROMPT


def test_guidelines_are_presentation_only():
    assert "retrieval" in ANSWER_FORMATTING_GUIDELINES
    assert "#" in ANSWER_FORMATTING_GUIDELINES
    assert "table" in ANSWER_FORMATTING_GUIDELINES