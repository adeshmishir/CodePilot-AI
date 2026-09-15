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

    def build_repository_context(
        self,
        *,
        query: str,
        metadata: dict | None = None,
        structure: dict | None = None,
        manifest_entries: list[dict] | None = None,
        retrieved: list[dict] | None = None,
    ) -> str:
        """Assemble a labeled, deterministic repository context.

        Sections:
          REPOSITORY METADATA   - completeness + language overview
          REPOSITORY STRUCTURE  - manifest file tree
          RELEVANT FILES        - manifest entries worth mentioning
          RETRIEVED CODE        - semantic search blocks
          IMPORTANT             - explicit subset notice

        The metadata/structure sections make the agent aware that the
        retrieved chunks are a small subset of the repository. ``build`` is
        kept untouched for the old behaviour.
        """
        sections = []

        if metadata:
            sections.append(
                f"[REPOSITORY METADATA]\n{self._format_metadata(metadata)}"
            )

        if structure and structure.get("tree"):
            parts = [f"[REPOSITORY STRUCTURE]\n{structure['tree']}"]

            if structure.get("truncated"):
                parts.append(
                    "Note: this tree is truncated to the first entries."
                )

            sections.append("\n".join(parts))

        if manifest_entries:
            lines = ["[RELEVANT FILES]"]
            for entry in manifest_entries:
                path = entry.get("file_path", "unknown")
                status = entry.get("index_status")
                notes = []

                if status == "skipped":
                    notes.append(f"not indexed ({entry.get('skip_reason') or 'skipped'})")
                elif status == "failed":
                    notes.append("indexing failed")

                line = path
                if notes:
                    line += f" [{', '.join(notes)}]"
                lines.append(line)
            sections.append("\n".join(lines))

        if retrieved:
            code = self.build(retrieved)

            if code:
                sections.append(f"[RETRIEVED CODE (subset)]\n{code}")

        warning = self._subset_warning(query, manifest_entries)
        if warning:
            sections.append(f"[IMPORTANT]\n{warning}")

        return "\n\n".join(sections)

    def _format_metadata(self, metadata: dict) -> str:
        lines = [
            "This repository provides a streaming, memory-safe index. "
            "Only a subset of files is embedded and returned to you.",
        ]

        total = metadata.get("total_files")
        indexed = metadata.get("indexed_files")
        skipped = metadata.get("skipped_files")
        failed = metadata.get("failed_files")

        if total is not None:
            lines.append(
                f"Files in manifest: {total} "
                f"(indexed: {indexed or 0}, "
                f"skipped: {skipped or 0}, "
                f"failed: {failed or 0})"
            )

        if metadata.get("partial"):
            lines.append(
                "The index is PARTIAL: the manifest lists more files than "
                "were embedded, so semantic retrieval may miss relevant "
                "code. Prefer the file paths above."
            )

        dirs = metadata.get("top_level_directories") or []
        if dirs:
            lines.append("Top-level layout: " + ", ".join(dirs))

        languages = metadata.get("languages") or []
        if languages:
            summary = [
                part for part in languages if part.get("count")
            ]
            if summary:
                lines.append(
                    "Languages: "
                    + ", ".join(
                        f"{item['language']} ({item['count']})"
                        for item in summary
                    )
                )

        return "\n".join(lines)

    def _subset_warning(
        self,
        query: str,
        manifest_entries: list[dict] | None,
    ) -> str:
        lines = [
            "The RETRIEVED CODE section above contains only a few relevant "
            "chunks, NOT the whole repository.",
        ]

        if manifest_entries:
            paths = [entry.get("file_path") for entry in manifest_entries]
            lines.append(
                "Files most likely relevant to this question: "
                + ", ".join(str(path) for path in paths if path)
            )

        lines.append(
            "If a correct answer requires the structure listed under "
            "REPOSITORY STRUCTURE, or files under RELEVANT FILES, use the "
            "listen_files / read_file tools so you can answer from the "
            "manifest-backed structure instead of guessing."
        )

        return "\n".join(lines)

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
