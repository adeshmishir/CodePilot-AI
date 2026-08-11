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
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".java",
        ".cpp",
        ".cc",
        ".cxx",
        ".c",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".cs",
        ".php",
        ".swift",
        ".kt",
        ".md",
    }

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

        for file_path in repository_path.rglob("*"):
            if any(
                ignored in file_path.parts
                for ignored in self.IGNORED_DIRECTORIES
            ):
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
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

        return files


repository_parser = RepositoryParser()
