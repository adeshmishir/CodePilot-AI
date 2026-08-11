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

    def get_repository_files(
        self,
        repository_path: Path,
    ) -> list[Path]:
        files: list[Path] = []

        max_bytes = int(settings.MAX_INDEX_FILE_SIZE_MB * 1024 * 1024)
        max_files = settings.MAX_INDEX_FILES

        for file_path in repository_path.rglob("*"):
            if any(
                ignored in file_path.parts
                for ignored in self.IGNORED_DIRECTORIES
            ):
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            name = file_path.name.lower()

            if name in self.IGNORED_FILES or name.endswith(
                self.MINIFIED_SUFFIXES
            ):
                continue

            try:
                if (
                    not file_path.is_file()
                    or file_path.stat().st_size > max_bytes
                ):
                    continue
            except OSError:
                continue

            if self._is_binary(file_path):
                continue

            files.append(file_path)

        if max_files and len(files) > max_files:
            print(
                f"Repository has more than {max_files} supported files; "
                f"indexing the first {max_files} to bound memory usage."
            )
            files = files[:max_files]

        return files


repository_parser = RepositoryParser()
