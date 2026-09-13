from pathlib import Path

from app.config.settings import settings


class RepositoryParser:
    IGNORED_DIRECTORIES = {
        ".git",
        ".github",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        ".tox",
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        "coverage",
    }

    BINARY_SNIFF_BYTES = 1024

    SUPPORTED_EXTENSIONS = {
        # Python
        ".py",
        ".pyw",
        ".pyi",
        # JavaScript / TypeScript
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        # Web
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".vue",
        ".svelte",
        # Config / data
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        # JVM
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".groovy",
        ".gradle",
        # C family
        ".c",
        ".h",
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".hh",
        ".hxx",
        ".cs",
        ".m",
        ".mm",
        # Go / Rust
        ".go",
        ".rs",
        # Server-side
        ".php",
        ".rb",
        ".swift",
        ".dart",
        # Shell
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        # SQL / functional
        ".sql",
        ".ex",
        ".exs",
        ".erl",
        ".hrl",
        ".hs",
        ".lhs",
        ".lua",
        ".r",
        ".ml",
        ".mli",
        ".pl",
        ".pm",
        ".clj",
        ".cljs",
        # Docs
        ".md",
        ".mdx",
        ".rst",
        ".txt",
        ".tex",
    }

    # Machine-generated files that are large and rarely useful for
    # answering questions. Indexing them burns memory and storage.
    IGNORED_FILES = {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "uv.lock",
        "cargo.lock",
        "gemfile.lock",
        "composer.lock",
        "go.sum",
        "flake.lock",
        "pipfile.lock",
        "requirements.lock",
    }

    MINIFIED_SUFFIXES = (".min.js", ".min.css")

    def _is_binary(self, file_path: Path) -> bool:
        """Heuristic: files containing a NUL byte in the first bytes are
        treated as binary and never indexed."""
        try:
            with file_path.open("rb") as handle:
                return b"\x00" in handle.read(self.BINARY_SNIFF_BYTES)
        except OSError:
            return True

    def _classify_file(
        self,
        file_path: Path,
        max_bytes: int | None = None,
    ) -> str | None:
        """Decide whether a path is indexable.

        Returns ``None`` when the path is a source file CodePilot should
        index, otherwise a short reason string explaining why it is
        skipped. Skipping reasons are used to report an "Indexed X /
        Skipped Y (reason...)" breakdown without crashing on a single
        problematic file.
        """
        if any(
            ignored in file_path.parts
            for ignored in self.IGNORED_DIRECTORIES
        ):
            return "ignored_directory"

        # Directories (and unreadable entries) are not files and are never
        # indexed. They are excluded from the skip counters below so a
        # "Skipped Y" summary counts actual files, not every directory.
        try:
            if not file_path.is_file():
                return "not_a_file"
        except OSError:
            return "not_a_file"

        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return "unsupported_extension"

        name = file_path.name.lower()

        if name in self.IGNORED_FILES:
            return "ignored_filename"

        if name.endswith(self.MINIFIED_SUFFIXES):
            return "minified"

        if max_bytes is None:
            max_bytes = settings.max_file_size_bytes()

        try:
            if file_path.stat().st_size > max_bytes:
                return "too_large"
        except OSError:
            return "unreadable"

        if self._is_binary(file_path):
            return "binary"

        return None

    def scan_repository(
        self,
        repository_path: Path,
    ) -> dict:
        """Count indexable files and skipped entries without holding paths.

        Walks the repository once, storing nothing but counters, so even a
        repository with tens of thousands of entries never accumulates a
        list of every file path in memory. Returns::

            {
                "files": int,       # files that will be indexed (post-cap)
                "eligible": int,    # all indexable files before the cap
                "skipped": {...},   # reason -> count (files only)
            }
        """
        skipped: dict[str, int] = {}
        eligible = 0
        max_files = settings.MAX_INDEX_FILES

        for file_path in repository_path.rglob("*"):
            reason = self._classify_file(file_path)

            if reason is None:
                eligible += 1
                continue

            if reason == "not_a_file":
                continue

            skipped[reason] = skipped.get(reason, 0) + 1

        selected = eligible

        if max_files > 0 and eligible > max_files:
            overflow = eligible - max_files
            skipped["max_index_files"] = (
                skipped.get("max_index_files", 0) + overflow
            )
            selected = max_files

        return {
            "files": selected,
            "eligible": eligible,
            "skipped": skipped,
        }

    def iter_repository_files(
        self,
        repository_path: Path,
    ):
        """Yield indexable source files one at a time.

        Only a single path object is alive at any moment and iteration
        stops once ``MAX_INDEX_FILES`` files have been produced, so the
        full repository is never materialized as a list of paths.
        """
        max_files = settings.MAX_INDEX_FILES
        yielded = 0

        for file_path in repository_path.rglob("*"):
            if self._classify_file(file_path) is not None:
                continue

            if max_files > 0 and yielded >= max_files:
                return

            yielded += 1
            yield file_path

    def get_repository_files(
        self,
        repository_path: Path,
    ) -> list[Path]:
        return list(self.iter_repository_files(repository_path))


repository_parser = RepositoryParser()