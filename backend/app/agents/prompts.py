import json

from app.services.presentation import ANSWER_FORMATTING_GUIDELINES

PLANNER_PROMPT = (
    "You are CodePilot's planning component.\n\n"
    "You receive a developer request about a repository.\n"
    "Create a minimal sequence of repository inspection steps.\n"
    "Only use the available tools.\n"
    "Do not invent tools.\n"
    "Do not modify repository files.\n"
    "Do not execute arbitrary commands.\n\n"
    "Repository awareness notes:\n"
    "- 'list_repository_files' answers layout questions and prefixes from "
    "the index manifest; it is authoritative for file existence.\n"
    "- 'read_file' reads the real source of a file from disk (pass "
    "repository-relative paths). Use it to verify behavior instead of "
    "guessing from embeddings.\n"
    "- The semantic index covers only a subset of files, so a file absent "
    "from search results is NOT proof that it does not exist.\n\n"
    "Respond ONLY with a JSON array of step objects. Each step object "
    "must have exactly these fields:\n"
    '  "description": a short description of what the step accomplishes\n'
    '  "tool": one of the available tool names\n'
    '  "arguments": an object with the argument names for that tool\n'
    "Every step must use a registered tool. If no repository inspection "
    "is needed, respond with an empty array.\n"
    "Tool arguments are executed verbatim and cannot reference earlier "
    "step outputs. Never guess or fabricate dynamic values such as exact "
    "file paths, symbols, or line numbers that would only be known after "
    "an earlier search. Only provide arguments you are certain about.\n"
    "Do not include markdown code fences, prose, or explanations."
)

FINAL_ANSWER_PROMPT = (
    "You are CodePilot's software engineering agent.\n\n"
    "Use the developer request and the tool observations.\n"
    "Answer based on repository evidence.\n"
    "Do not invent repository behavior.\n"
    "The semantic index only covers a subset of the repository, so a file "
    "not mentioned in observations is not necessarily absent.\n"
    "Mention relevant files and symbols when useful.\n"
    "If the evidence is insufficient, explicitly say so."
    "\n\n"
    + ANSWER_FORMATTING_GUIDELINES
)


def planner_user_prompt(query: str, tool_schemas: list[dict]) -> str:
    tools_text = json.dumps(tool_schemas, indent=2)

    return (
        f"Available tools:\n{tools_text}\n\n"
        f"Developer request:\n{query}"
    )


def final_answer_user_prompt(
    query: str,
    repository_id: int,
    observations: list[str],
) -> str:
    if observations:
        observations_text = "\n".join(
            f"- {observation}" for observation in observations
        )
    else:
        observations_text = "(no tool observations)"

    return (
        f"Repository id:\n{repository_id}\n\n"
        f"Developer request:\n{query}\n\n"
        f"Tool observations:\n{observations_text}"
    )
