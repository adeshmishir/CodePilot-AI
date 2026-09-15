import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryPathError
from app.models.repository import RepositoryModel
from app.models.repository_manifest import RepositoryManifestModel
from app.services.parser.language_mapper import get_language_from_path
from app.services.repository.paths import (
    normalize_local_path,
    posix_path,
    repo_relative_path,
)

# Default upper bound on a single file read. Reading a file should stay
# memory bounded even when the user asks for a very large file without a
# line range.
MAX_READ_CHARS = 20000

# Structural listing is capped so a repository with tens of thousands of
# manifest rows never materializes a full tree into the LLM prompt.
MAX_STRUCTURE_ENTRIES = 500

# Files that most strongly describe a project for GENERAL_PROJECT_QUERY.
CONFIG_FILE_NAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "pipfile",
    "readme.md",
    "readme",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gemfile",
    "composer.json",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.mjs",
    ".env.example",
    "manage.py",
}

RE_DOUBLE_DOT = re.compile(r"(^|[/\\])\.\.([/\\]|$)")


def _suffix(rel_path: str) -> str | None:
    name = Path(rel_path).name

    if "." not in name:
        return None

    return Path(name).suffix.lower()


def _language_for(rel_path: str) -> str | None:
    language = get_language_from_path(Path(rel_path))

    if language is not None:
        return language

    suffix = _suffix(rel_path)

    if suffix is None:
        return None

    return suffix.lstrip(".")


class RepositoryManifestService:
    """Query the repository manifest from PostgreSQL.

    The manifest is the source of truth for repository structure. Structure
    questions and exact file lookups are answered from here directly, never
    by asking the vector store or the LLM to reconstruct the repository tree
    from embeddings.
    """

    def __init__(self, db: Session):
        self.db = db

    def read_file(
        self,
        repository_id: int,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_chars: int = MAX_READ_CHARS,
    ) -> dict | None:
        """Read only the requested file from the local checkout.

        Path traversal is rejected, the read is restricted to the requested
        line range, and the returned content is capped at ``max_chars`` so a
        single file read can never load the whole repository into memory.
        """
        repository = self._repository(repository_id)

        if repository is None:
            return None

        normalized = posix_path(file_path)

        if is_unsafe_relative(normalized):
            return None

        full_path = self._resolve_checkout_file(repository, normalized)

        if full_path is None:
            return None

        return self._read_lines(
            repository,
            normalized,
            full_path,
            start_line,
            end_line,
            max_chars,
        )

    def get_entry(
        self,
        repository_id: int,
        file_path: str,
    ) -> dict | None:
        """Return a single manifest entry for an exact repository-relative
        path, or ``None`` when the path is not present in the manifest."""
        repository = self._repository(repository_id)

        if repository is None or not file_path:
            return None

        normalized = posix_path(file_path)

        if not normalized or is_unsafe_relative(normalized):
            return None

        full = self._join_root(repository, normalized)

        row = (
            self.db.query(RepositoryManifestModel)
            .filter(
                RepositoryManifestModel.repository_id == repository_id,
                RepositoryManifestModel.file_path == full,
            )
            .first()
        )

        if row is None:
            return None

        return self._to_entry(row)

    def list_files(
        self,
        repository_id: int,
        path_prefix: str | None = None,
        extension: str | None = None,
        status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """Manifest-backed file listing with optional prefix, extension and
        status filters.

        Filtering of the repository root prefix happens in SQL so only a
        bounded page of rows is ever pulled into memory. Returns a
        deterministic, ordered listing plus totals.
        """
        repository = self._repository(repository_id)

        if repository is None:
            return {
                "repository_id": repository_id,
                "files": [],
                "total": 0,
                "offset": 0,
                "limit": limit,
            }

        query = self.db.query(RepositoryManifestModel).filter(
            RepositoryManifestModel.repository_id == repository_id,
        )

        clean_prefix = _clean_path_prefix(path_prefix)

        if clean_prefix:
            full_prefix = self._join_root(repository, clean_prefix) + "/"
            query = query.filter(
                RepositoryManifestModel.file_path.like(full_prefix + "%")
            )

        if status:
            query = query.filter(
                RepositoryManifestModel.index_status == status
            )

        if extension:
            suffix = extension.strip().lower().lstrip(".")
            query = query.filter(
                func.lower(RepositoryManifestModel.file_path).like(
                    f"%.{suffix}"
                )
            )

        total = query.count()

        rows = (
            query.order_by(RepositoryManifestModel.file_path)
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "repository_id": repository_id,
            "files": [self._to_entry(row) for row in rows],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def file_chunks(
        self,
        repository_id: int,
        file_path: str,
        limit: int = 200,
    ) -> list[dict]:
        """Return indexed chunks belonging to an exact file, for retrieving
        the code of a file the user already named instead of fuzzy
        semantic retrieval.

        Chunk rows are stored with the checkout prefix too, so we match
        both POSIX and native separators by normalizing the stored column
        comparison.
        """
        repository = self._repository(repository_id)

        if not file_path:
            return []

        normalized = posix_path(file_path)

        if is_unsafe_relative(normalized):
            return []

        full = self._join_root(repository, normalized) if repository else normalized
        full_win = full.replace("/", "\\")

        from app.models.code_chunk import CodeChunkModel

        rows = (
            self.db.query(CodeChunkModel)
            .filter(
                CodeChunkModel.repository_id == repository_id,
                (
                    (CodeChunkModel.file_path == full)
                    | (CodeChunkModel.file_path == full_win)
                    | (CodeChunkModel.file_path.like(full + "/%"))
                    | (CodeChunkModel.file_path.like(full_win + "\\%"))
                ),
            )
            .order_by(CodeChunkModel.start_line)
            .limit(limit)
            .all()
        )

        return [
            {
                "file_path": code_chunk.file_path,
                "symbol_name": code_chunk.symbol_name,
                "symbol_type": code_chunk.symbol_type,
                "start_line": code_chunk.start_line,
                "end_line": code_chunk.end_line,
                "content": code_chunk.content,
            }
            for code_chunk in rows
        ]

    def get_summary(self, repository_id: int) -> dict | None:
        """Repository completeness information derived from the manifest:
        total/indexed/skipped/failed files, languages, top-level dirs and an
        explicit completeness flag."""
        repository = self._repository(repository_id)

        if repository is None:
            return None

        root = posix_path(repository.local_path)

        rows = self._all_paths(repository_id)

        indexed = 0
        skipped = 0
        failed = 0
        languages: dict[str, int] = {}
        language_order: list[str] = []
        top_level: set[str] = set()
        has_root_files = False
        skipped_reasons: dict[str, int] = {}

        for row in rows:
            rel = repo_relative_path(root, row.file_path)

            if row.index_status == "indexed":
                indexed += 1
                language = _language_for(rel)

                if language is not None:
                    if language not in languages:
                        languages[language] = 0
                        language_order.append(language)
                    languages[language] += 1
            elif row.index_status == "skipped":
                skipped += 1
                reason = row.skip_reason or "unknown"
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
            elif row.index_status == "failed":
                failed += 1

            head, separator, rest = rel.partition("/")

            if separator:
                top_level.add(head)
            else:
                has_root_files = True

        top_level_dirs = sorted(top_level)

        if has_root_files:
            top_level_dirs.append("(root files)")

        total = indexed + skipped + failed

        partial = failed > 0 or bool(skipped_reasons.get("max_index_files"))

        return {
            "repository_id": repository_id,
            "total_files": total,
            "indexed_files": indexed,
            "skipped_files": skipped,
            "failed_files": failed,
            "skipped_reasons": skipped_reasons,
            "languages": [
                {"language": name, "count": languages[name]}
                for name in language_order
            ],
            "top_level_directories": top_level_dirs,
            "partial": partial,
        }

    def build_structure(
        self,
        repository_id: int,
        path_prefix: str | None = None,
        max_entries: int = MAX_STRUCTURE_ENTRIES,
    ) -> dict:
        """Build a deterministic, compact file tree from the manifest.

        Returns a text tree plus top-level directories. Only paths (not file
        contents) are materialized and the output is capped so the prompt
        stays bounded.
        """
        repository = self._repository(repository_id)

        if repository is None:
            return {
                "tree": "",
                "top_level_directories": [],
                "truncated": False,
            }

        root = posix_path(repository.local_path)

        rows = self._all_paths(repository_id)

        clean_prefix = _clean_path_prefix(path_prefix)

        included = 0
        truncated = False
        tree: dict = {}

        for row in rows:
            rel = repo_relative_path(root, row.file_path)

            if clean_prefix and not (
                rel == clean_prefix or rel.startswith(clean_prefix + "/")
            ):
                continue

            if included >= max_entries:
                truncated = True
                break

            _insert_path(tree, rel, row.index_status)
            included += 1

        return {
            "tree": _render_tree(tree, truncated, max_entries),
            "top_level_directories": _top_level_dirs(tree),
            "truncated": truncated,
        }

    def config_files(
        self,
        repository_id: int,
        limit: int = 8,
    ) -> list[dict]:
        """Return manifest entries for files that describe the project
        (package.json, requirements.txt, README, Docker files, configs...)."""
        repository = self._repository(repository_id)

        if repository is None:
            return []

        found: list[dict] = []
        seen = set()

        for row in self._all_paths(repository_id):
            if len(found) >= limit:
                break

            name = Path(row.file_path).name.lower()

            if name in CONFIG_FILE_NAMES:
                found.append(self._to_entry(row))
                seen.add(row.file_path)

        if len(found) < limit:
            for row in self._all_paths(repository_id):
                if len(found) >= limit:
                    break

                if row.file_path.lower().endswith(
                    (".toml", ".yaml", ".yml", ".json")
                ) and row.file_path not in seen:
                    found.append(self._to_entry(row))
                    seen.add(row.file_path)

        return found

    # -- internals -----------------------------------------------------

    def _repository(self, repository_id: int) -> RepositoryModel | None:
        return (
            self.db.query(RepositoryModel)
            .filter(RepositoryModel.id == repository_id)
            .first()
        )

    def _root(self, repository: RepositoryModel) -> str:
        return posix_path(repository.local_path)

    def _join_root(self, repository: RepositoryModel, rel: str) -> str:
        root = self._root(repository)

        if not root:
            return rel

        return f"{root}/{rel}"

    def _resolve_checkout_file(
        self,
        repository: RepositoryModel,
        normalized: str,
    ) -> Path | None:
        checkout_root = normalize_local_path(repository.local_path).resolve()

        candidate = (checkout_root / normalized).resolve()

        if not candidate.is_relative_to(checkout_root):
            return None

        if not candidate.is_file():
            return None

        return candidate

    def _read_lines(
        self,
        repository: RepositoryModel,
        rel_path: str,
        full_path: Path,
        start_line: int | None,
        end_line: int | None,
        max_chars: int,
    ) -> dict:
        root = self._root(repository)
        rel = repo_relative_path(root, rel_path)

        try:
            data = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            raise RepositoryPathError(f"Cannot read {rel}: {error}")

        lines = data.splitlines()

        total_lines = len(lines)

        if start_line is None:
            start_line = 1

        if end_line is None or end_line > total_lines:
            end_line = total_lines

        if start_line < 1:
            start_line = 1

        if end_line < start_line:
            end_line = start_line

        selected = lines[start_line - 1:end_line]

        content = "\n".join(selected)
        truncated = len(content) > max_chars

        if truncated:
            content = content[:max_chars]

        return {
            "file_path": rel,
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "truncated": truncated,
        }

    def _all_paths(self, repository_id: int):
        return (
            self.db.query(RepositoryManifestModel)
            .filter(RepositoryManifestModel.repository_id == repository_id)
            .order_by(RepositoryManifestModel.file_path)
            .all()
        )

    def _to_entry(self, row: RepositoryManifestModel) -> dict:
        root = posix_path(self._entry_root(row))

        return {
            "file_path": repo_relative_path(root, row.file_path),
            "size_bytes": row.size_bytes,
            "index_status": row.index_status,
            "skip_reason": row.skip_reason,
            "indexed_at": _iso_or_none(row.indexed_at),
            "updated_at": _iso_or_none(row.updated_at),
        }

    def _entry_root(self, row: RepositoryManifestModel) -> str:
        repository = (
            self.db.query(RepositoryModel)
            .filter(RepositoryModel.id == row.repository_id)
            .first()
        )

        if repository is None:
            return ""

        return self._root(repository)


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _clean_path_prefix(value: str | None) -> str:
    if not value:
        return ""

    cleaned = posix_path(value)

    if is_unsafe_relative(cleaned):
        return ""

    return cleaned


def is_unsafe_relative(path: str) -> bool:
    """Reject absolute paths and ``..`` traversal segments."""
    if not path:
        return True

    if path.startswith("/"):
        return True

    if RE_DOUBLE_DOT.search(path):
        return True

    return False


def _insert_path(tree: dict, rel: str, status: str) -> None:
    node = tree

    parts = rel.split("/")

    for part in parts[:-1]:
        dirs = node.setdefault("__dirs__", {})
        node = dirs.setdefault(part, {"__dirs__": {}, "__files__": []})

    node.setdefault("__files__", []).append((parts[-1], status))


def _top_level_dirs(tree: dict) -> list[str]:
    return sorted((tree.get("__dirs__") or {}).keys())


def _render_tree(tree: dict, truncated: bool, max_entries: int) -> str:
    lines: list[str] = []

    def add(line: str) -> None:
        if len(lines) < max_entries:
            lines.append(line)

    def walk(node: dict, prefix: str, name: str, last: bool) -> None:
        marker = "└── " if last else "├── "

        if name:
            add(f"{prefix}{marker}{name}/")

        child_prefix = prefix + ("    " if last else "│   ") if name else prefix

        child_dirs = sorted((node.get("__dirs__") or {}).keys())
        files = sorted(node.get("__files__") or [])

        dir_count = len(child_dirs)

        for index, child_name in enumerate(child_dirs):
            child_node = (node["__dirs__"] or {})[child_name]
            is_last = (index == dir_count - 1) and not files
            walk(child_node, child_prefix, child_name, is_last)

        for index, (file_name, status) in enumerate(files):
            is_last = index == len(files) - 1
            marker = "└── " if is_last else "├── "
            suffix = "" if status == "indexed" else f" [{status}]"
            add(f"{child_prefix}{marker}{file_name}{suffix}")

    walk(tree, "", "", True)

    if truncated:
        lines.append("... (listing truncated)")

    return "\n".join(lines)