from pathlib import Path


EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
}


def get_language_from_path(
    file_path: Path
) -> str | None:
    return EXTENSION_TO_LANGUAGE.get(
        file_path.suffix.lower()
    )
