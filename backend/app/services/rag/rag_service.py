import threading

from sqlalchemy.orm import Session

from app.services.llm.groq_service import GroqService
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.query_classifier import (
    QueryClassifier,
    QueryIntent,
)
from app.services.repository.manifest_service import RepositoryManifestService
from app.services.repository.paths import posix_path, repo_relative_path
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)
from app.models.repository import RepositoryModel


# ── prompts ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are CodePilot, an AI software engineering assistant.\n\n"
    "Answer the developer's question about a repository using the "
    "provided repository context.\n\n"
    "Context sections:\n"
    "- REPOSITORY METADATA: completeness information and what is indexed "
    "(not the full repository).\n"
    "- REPOSITORY STRUCTURE: a compact file tree from the manifest "
    "(authoritative layout).\n"
    "- RELEVANT FILES: repository-relative paths most related to the "
    "question.\n"
    "- RETRIEVED CODE: a small subset of relevant code chunks. Treat this "
    "as partial evidence, not the whole repository.\n"
    "- IMPORTANT: explicit reminders about the subset nature of the "
    "retrieved code.\n\n"
    "Rules:\n"
    "1. File existence, naming, and layout must come from the manifest "
    "sections (REPOSITORY STRUCTURE / RELEVANT FILES), NOT from the "
    "RETRIEVED CODE section alone.\n"
    "2. If you claim a file does not exist, base that on the manifest "
    "sections. Never assume absence of a file just because it is missing "
    "from RETRIEVED CODE.\n"
    "3. When describing architecture, language mix, or project layout, use "
    "the top-level directories listed in the REPOSITORY STRUCTURE / "
    "RELEVANT FILES sections.\n"
    "4. Only make statements about behavior when supported by the "
    "RETRIEVED CODE section. If the relevant code is not present, say so "
    "explicitly.\n"
    "5. When useful, include file paths and line ranges in the answer.\n"
    "6. If you need the actual contents of a file not shown in the "
    "RETRIEVED CODE section, say you need to call read_file.\n"
    "7. Keep answers clear and concise."
)

GENERAL_SYSTEM_PROMPT = (
    "You are CodePilot, an AI software engineering assistant.\n\n"
    "Answer the user's question directly and concisely.\n"
    "If they ask for code, provide a clear, working example."
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_source(
    file_path: str,
    *,
    score: float | None = None,
    symbol_name: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    return {
        "file_path": file_path,
        "symbol_name": symbol_name,
        "start_line": start_line,
        "end_line": end_line,
        "score": score,
    }
    return {"file_path": file_path, "score": score}


# ── service ──────────────────────────────────────────────────────────────────

class RAGService:
    """Orchestrate retrieval, context construction, and LLM generation.

    When ``db`` is passed, structure/file/project intents are answered from
    the PostgreSQL manifest instead of asking the LLM to reconstruct the
    repository from a few embedding results. Without ``db`` the old
    semantic-only path is used, so existing tests without a database
    continue to work.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilder,
        groq_service: GroqService,
        query_classifier: QueryClassifier | None = None,
    ):
        self.retrieval_service = retrieval_service
        self.context_builder = context_builder
        self.groq_service = groq_service
        self.query_classifier = query_classifier or QueryClassifier()

    # ── public API ───────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        repository_id: int,
        limit: int = 5,
        db: Session | None = None,
    ) -> dict:
        intent = self.query_classifier.classify(query)

        if intent == QueryIntent.GENERAL:
            return self._general_answer(query)

        manifest = self._manifest(db)

        if manifest is not None:
            return self._answered_by_manifest(
                manifest,
                query=query,
                repository_id=repository_id,
                intent=intent,
                limit=limit,
            )

        return self._semantic_answer(query, repository_id, limit)

    def answer_stream(
        self,
        query: str,
        repository_id: int,
        limit: int = 5,
        db: Session | None = None,
    ):
        """Yield SSE-style events for a streaming chat response.

        Events:
          {"type": "sources", "sources": [...]}
          {"type": "delta", "text": str}
          {"type": "done", "message": str}
        """
        intent = self.query_classifier.classify(query)

        if intent == QueryIntent.GENERAL:
            yield {"type": "sources", "sources": []}

            for delta in self.groq_service.generate_stream(
                system_prompt=GENERAL_SYSTEM_PROMPT,
                user_prompt=query,
            ):
                yield {"type": "delta", "text": delta}

            yield {"type": "done", "message": ""}
            return

        manifest = self._manifest(db)

        if manifest is not None:
            result = self._answered_by_manifest(
                manifest,
                query=query,
                repository_id=repository_id,
                intent=intent,
                limit=limit,
            )

            yield {"type": "sources", "sources": result.get("sources", [])}

            for delta in self.groq_service.generate_stream(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=result.get("user_prompt", query),
            ):
                yield {"type": "delta", "text": delta}

            yield {"type": "done", "message": ""}
            return

        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        context = self.context_builder.build(results)

        sources = [
            _make_source(
                result.get("file_path"),
                score=result.get("score"),
                symbol_name=result.get("symbol_name"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
            )
            for result in results
        ]

        yield {"type": "sources", "sources": sources}

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        for delta in self.groq_service.generate_stream(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        ):
            yield {"type": "delta", "text": delta}

        yield {"type": "done", "message": ""}

    # ── internal routing ──────────────────────────────────────────────────

    def _manifest(self, db: Session | None) -> RepositoryManifestService | None:
        if db is None:
            return None

        return RepositoryManifestService(db)

    def _answered_by_manifest(
        self,
        manifest: RepositoryManifestService,
        *,
        query: str,
        repository_id: int,
        intent: QueryIntent,
        limit: int,
    ) -> dict:
        if intent == QueryIntent.STRUCTURE_QUERY:
            return self._structure_answer(manifest, repository_id, query)

        if intent == QueryIntent.FILE_LOOKUP_QUERY:
            return self._file_lookup_answer(
                manifest, repository_id, query, limit
            )

        if intent == QueryIntent.GENERAL_PROJECT_QUERY:
            return self._project_answer(
                manifest, repository_id, query, limit
            )

        if intent == QueryIntent.CROSS_FILE_QUERY:
            return self._cross_file_answer(
                manifest, repository_id, query, limit
            )

        # SEMANTIC_CODE_QUERY: retrieval wrapped with metadata + structure.
        return self._semantic_manifest_answer(
            manifest, repository_id, query, limit
        )

    # ── intent answers ────────────────────────────────────────────────────

    def _structure_answer(
        self,
        manifest: RepositoryManifestService,
        repository_id: int,
        query: str,
    ) -> dict:
        """STRUCTURE_QUERY: answer entirely from the manifest.

        Never calls embeddings – structure is deterministic.
        """
        structure = manifest.build_structure(repository_id)
        metadata = manifest.get_summary(repository_id)

        context = self.context_builder.build_repository_context(
            query=query,
            metadata=metadata,
            structure=structure,
        )

        sources = [
            _make_source(dir_name)
            for dir_name in structure.get("top_level_directories", [])
        ]

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "user_prompt": user_prompt,
        }

    def _file_lookup_answer(
        self,
        manifest: RepositoryManifestService,
        repository_id: int,
        query: str,
        limit: int,
    ) -> dict:
        """FILE_LOOKUP_QUERY: manifest entry + code chunks for the named file,
        with semantic fallback when the file has no chunks."""
        file_path = self.query_classifier.extract_file_path(query) or ""
        entry = manifest.get_entry(repository_id, file_path) if file_path else None

        chunks = []
        if file_path:
            chunks = manifest.file_chunks(repository_id, file_path)

        # Fall back to semantic search when the file is named but has no
        # chunks (e.g. skipped for "no_code_symbols" or "too_large").
        if not chunks:
            return self._semantic_manifest_answer(
                manifest, repository_id, query, limit
            )

        root = self._repository_root(manifest, repository_id)

        chunks = [
            {
                "file_path": _to_repo_relative(root, chunk.get("file_path", "")),
                "symbol_name": chunk.get("symbol_name", ""),
                "symbol_type": chunk.get("symbol_type", ""),
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
                "content": chunk.get("content", ""),
                "score": None,
            }
            for chunk in chunks
        ]

        metadata = manifest.get_summary(repository_id)

        context = self.context_builder.build_repository_context(
            query=query,
            metadata=metadata,
            manifest_entries=[entry] if entry else [],
            retrieved=chunks,
        )

        sources = [
            _make_source(
                _to_repo_relative(root, chunk.get("file_path", "")),
                score=None,
                symbol_name=chunk.get("symbol_name"),
                start_line=chunk.get("start_line"),
                end_line=chunk.get("end_line"),
            )
            for chunk in chunks
        ]

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "user_prompt": user_prompt,
        }

    def _project_answer(
        self,
        manifest: RepositoryManifestService,
        repository_id: int,
        query: str,
        limit: int,
    ) -> dict:
        """GENERAL_PROJECT_QUERY: summary + config files + targeted retrieval."""
        metadata = manifest.get_summary(repository_id)
        configs = manifest.config_files(repository_id)

        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        context = self.context_builder.build_repository_context(
            query=query,
            metadata=metadata,
            manifest_entries=configs,
            retrieved=results,
        )

        sources = [
            _make_source(
                result.get("file_path"),
                score=result.get("score"),
                symbol_name=result.get("symbol_name"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
            )
            for result in results
        ]

        # Also surface config-file paths so the agent can read them.
        for entry in configs:
            path = entry.get("file_path")
            if path and not any(s["file_path"] == path for s in sources):
                sources.append(_make_source(path, score=None))

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "user_prompt": user_prompt,
        }

    def _cross_file_answer(
        self,
        manifest: RepositoryManifestService,
        repository_id: int,
        query: str,
        limit: int,
    ) -> dict:
        """CROSS_FILE_QUERY: manifest discovery of mentioned subdirs +
        targeted retrieval."""
        structure = manifest.build_structure(repository_id)
        metadata = manifest.get_summary(repository_id)

        # Surface top-level dirs and let the retrieval do the rest.
        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        manifest_entries = []

        for dir_name in structure.get("top_level_directories", []):
            dir_entry = manifest.get_entry(repository_id, dir_name)
            if dir_entry:
                manifest_entries.append(dir_entry)

        context = self.context_builder.build_repository_context(
            query=query,
            metadata=metadata,
            structure=structure,
            manifest_entries=manifest_entries,
            retrieved=results,
        )

        sources = [
            _make_source(
                result.get("file_path"),
                score=result.get("score"),
                symbol_name=result.get("symbol_name"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
            )
            for result in results
        ]

        for dir_name in structure.get("top_level_directories", []):
            if not any(s["file_path"] == dir_name for s in sources):
                sources.append(_make_source(dir_name, score=None))

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "user_prompt": user_prompt,
        }

    def _semantic_manifest_answer(
        self,
        manifest: RepositoryManifestService,
        repository_id: int,
        query: str,
        limit: int,
    ) -> dict:
        """SEMANTIC_CODE_QUERY: retrieval wrapped with metadata + structure
        so the agent sees what the repository looks like, not just a few
        code chunks."""
        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        metadata = manifest.get_summary(repository_id)
        structure = manifest.build_structure(repository_id)

        context = self.context_builder.build_repository_context(
            query=query,
            metadata=metadata,
            structure=structure,
            retrieved=results,
        )

        sources = [
            _make_source(
                result.get("file_path"),
                score=result.get("score"),
                symbol_name=result.get("symbol_name"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
            )
            for result in results
        ]

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return {
            "answer": answer,
            "sources": sources,
            "user_prompt": user_prompt,
        }

    # ── fallback (no db) ──────────────────────────────────────────────────

    def _semantic_answer(self, query: str, repository_id: int, limit: int) -> dict:
        """Old semantic-only path used when db is unavailable."""
        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        context = self.context_builder.build(results)

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        sources = [
            _make_source(
                result.get("file_path"),
                score=result.get("score"),
                symbol_name=result.get("symbol_name"),
                start_line=result.get("start_line"),
                end_line=result.get("end_line"),
            )
            for result in results
        ]

        return {
            "answer": answer,
            "sources": sources,
        }

    def _general_answer(self, query: str) -> dict:
        answer = self.groq_service.generate(
            system_prompt=GENERAL_SYSTEM_PROMPT,
            user_prompt=query,
        )

        return {
            "answer": answer,
            "sources": [],
        }

    def _repository_root(
        self, manifest: RepositoryManifestService, repository_id: int
    ) -> str:
        """Return the POSIX repository root for the given repository_id."""
        repo = (
            manifest.db.query(RepositoryModel)
            .filter(RepositoryModel.id == repository_id)
            .first()
        )

        if repo is None:
            return ""

        return posix_path(repo.local_path)


def _to_repo_relative(root: str, raw_path: str) -> str:
    """Convert a stored chunk path into a repo-relative POSIX path."""
    return repo_relative_path(root, raw_path)


rag_service: RAGService | None = None
rag_service_lock = threading.Lock()


def get_rag_service() -> RAGService:
    global rag_service

    if rag_service is None:
        with rag_service_lock:
            if rag_service is None:
                rag_service = RAGService(
                    retrieval_service=get_retrieval_service(),
                    context_builder=ContextBuilder(),
                    groq_service=GroqService(),
                )

    return rag_service