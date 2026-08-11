from pathlib import Path


def backend_root() -> Path:
    """Absolute path to the backend package root (contains app/ and data/)."""
    return Path(__file__).resolve().parents[3]


def normalize_local_path(local_path: str | Path) -> Path:
    """Resolve a stored local_path into an absolute Path.

    Handles POSIX and Windows separators as well as absolute and
    app-root-relative paths so database rows remain portable between
    development machines and production containers.
    """
    normalized = str(local_path).replace("\\", "/")

    path = Path(normalized)

    if path.is_absolute():
        return path.resolve()

    return (backend_root() / path).resolve()


def relative_local_path(path: Path) -> str:
    """Convert a path into an app-root-relative POSIX string for storage."""
    resolved = path.resolve()

    try:
        return resolved.relative_to(backend_root()).as_posix()
    except ValueError:
        return resolved.as_posix()
