"""Shared answer-presentation guidelines for CodePilot.

These rules shape how model responses are structured so they render as
clean, professional Markdown in the chat UI. They are presentation-only:
they never change retrieval, indexing, or tool behavior.
"""

ANSWER_FORMATTING_GUIDELINES = (
    "Response formatting guidelines:\n"
    "- Present the answer as clean, professional Markdown.\n"
    "- Start substantial answers with a single '#' title that captures "
    "the answer, not the question type.\n"
    "- Use '##' section headings and '###' subheadings only where they "
    "help scanning. Pick headings that fit the specific question (for "
    "example an overview, a component breakdown, a flow, a root cause, "
    "or a recommendation).\n"
    "- Never use filler headings such as 'Introduction', 'Details', or "
    "'Conclusion', and never repeat the same heading multiple times.\n"
    "- Use bullet lists for features, files, and technical points. Use "
    "numbered lists for flows, step-by-step procedures, or priority "
    "order.\n"
    "- Wrap every file path, function name, package, endpoint, and "
    "command in inline code using backticks.\n"
    "- Put real code in fenced code blocks with a language tag. Never "
    "place multi-line code inside a paragraph.\n"
    "- When a file-tree style answer fits the question, present the tree "
    "inside a single code block without prose before it.\n"
    "- Use tables only when they genuinely clarify a comparison or "
    "mapping.\n"
    "- Highlight key concepts with bold text and use a blockquote only "
    "for short notes or conclusions.\n"
    "- Match answer length to the complexity of the question.\n"
    "- Keep technical facts exact: formatting must never change the "
    "meaning of the answer.\n"
    "- Never expose internal mechanics such as retrieval, context "
    "windows, or chunking."
)