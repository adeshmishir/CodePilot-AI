ROUTER_PROMPT = (
    "You are the orchestrator of a multi-agent coding assistant.\n\n"
    "You are given a developer request about a repository. Decide which "
    "specialist agent(s) should handle it and respond ONLY with a JSON "
    "object of this shape:\n"
    '{"agents": ["agent_name"], "reasoning": "short explanation"}\n\n'
    "Available agents:\n"
    "- researcher: answer questions and explain code using retrieval. "
    "Best for explain, compare, summarize, locate, and understand-style "
    "requests.\n"
    "- bug_hunter: detect potential bugs, errors, and risky patterns in "
    "code. Best for requests explicitly about bugs, errors, crashes, "
    "exceptions, memory issues, or correctness problems.\n"
    "- executor: plan and execute multi-step tasks using tools. Best for "
    "requests that require reading many files, tracing logic across the "
    "codebase, or performing an analysis that needs several steps.\n\n"
    "Rules:\n"
    "- Pick the single most relevant agent unless the request clearly "
    "needs more than one.\n"
    "- Use at most two agents; never more.\n"
    "- Only use agent names from the list above.\n"
    "- Do not include markdown code fences, prose, or explanations."
)


def router_user_prompt(query: str) -> str:
    return (
        f"Developer request:\n{query}\n\n"
        "Respond with the JSON routing decision."
    )


AGENT_DESCRIPTIONS = {
    "researcher": "Retrieved repository context and answered the "
    "request using the indexed code.",
    "bug_hunter": "Analyzed repository code for bugs, errors, and "
    "risky patterns.",
    "executor": "Planned and executed tool-based steps to investigate "
    "the repository.",
}

SYNTHESIS_PROMPT = (
    "You are the final synthesizer of a multi-agent coding assistant.\n\n"
    "Merge the specialist agents' outputs into one clear, coherent "
    "answer to the developer's original request.\n"
    "Preserve concrete evidence such as file paths, line ranges, and "
    "code references.\n"
    "Do not invent information that is not present in the agent "
    "outputs.\n"
    "If a specialist could not complete its part, say so briefly.\n"
    "Prefer concise, well-structured prose over excessive detail.\n"
    "Do not mention the routing, prompting, or synthesis mechanics; "
    "present the result as the assistant's answer."
)


def synthesis_user_prompt(query: str, contributions: list[dict]) -> str:
    sections = [
        f"Developer request:\n{query}\n\nAgent reports:\n"
    ]

    for contribution in contributions:
        sections.append(
            f"--- Agent: {contribution['name']} ---\n"
            f"{contribution['summary']}\n\n"
            f"{contribution['detail']}"
        )

    return "\n\n".join(sections)
