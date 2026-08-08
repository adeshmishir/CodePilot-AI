from app.config.settings import settings


class ContextBuilder:
    """Format retrieved code chunks into deterministic LLM context."""

    def __init__(self, max_chars: int | None = None):
        self.max_chars = max_chars or settings.RAG_CONTEXT_MAX_CHARS

    def build(self, results: list[dict]) -> str:
        sections = []
        used = 0

        for result in results:
            block = self._format_block(result)

            if used + len(block) <= self.max_chars:
                sections.append(block)
                used += len(block)
                continue

            truncated = self._truncate_block(result, self.max_chars - used)

            if truncated is not None:
                sections.append(truncated)

            break

        return "\n".join(sections)

    def _format_block(self, result: dict) -> str:
        header = self._format_header(result)
        content = result.get("content", "")

        return f"{header}\n{content}"

    def _truncate_block(self, result: dict, budget: int) -> str | None:
        header = self._format_header(result)

        code_budget = budget - len(header)

        if code_budget <= 0:
            return None

        content = result.get("content", "")

        if len(content) > code_budget:
            content = content[:code_budget]

        return f"{header}\n{content}"

    def _format_header(self, result: dict) -> str:
        file_path = result.get("file_path", "unknown")
        symbol = result.get("symbol_name", "")
        symbol_type = result.get("symbol_type", "")
        start_line = result.get("start_line")
        end_line = result.get("end_line")

        if start_line is not None and end_line is not None:
            lines = f"{start_line}-{end_line}"
        else:
            lines = "-"

        return (
            f"--- FILE: {file_path} ---\n"
            f"Symbol: {symbol}\n"
            f"Type: {symbol_type}\n"
            f"Lines: {lines}"
        )
