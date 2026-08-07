from pathlib import Path


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
    }

    SUPPORTED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".cs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
    }

    def get_repository_files(
        self,
        repository_path: Path,
    ) -> list[Path]:
        files: list[Path] = []

        for file_path in repository_path.rglob("*"):
            if any(
                ignored in file_path.parts
                for ignored in self.IGNORED_DIRECTORIES
            ):
                continue

            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ):
                files.append(file_path)

        return files


repository_parser = RepositoryParser()
