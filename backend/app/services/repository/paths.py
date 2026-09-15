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


def posix_path(value: str | Path) -> str:
    """Normalize any stored path to a POSIX string without leading/trailing
    slashes, so that manifest and chunk paths compare consistently across
    Windows and Linux."""
    raw = str(value).replace("\\", "/").strip()
    return raw.strip("/")


def repo_relative_path(local_path: str, file_path: str) -> str:
    """Convert a stored manifest/chunk path into a repository-relative
    POSIX path.

    Manifest and chunk paths are stored with the local checkout prefix
    (e.g. ``data/repos/owner/name/backend/app.py``). The repository's
    ``local_path`` records that same prefix (either app-root-relative or
    absolute), so stripping it yields a portable, LLM-friendly path such as
    ``backend/app.py``.
    """
    root = posix_path(local_path)
    value = posix_path(file_path)

    if not root:
        return value

    marker = root + "/"

    if value.startswith(marker):
        return value[len(marker):]

    if value == root:
        return ""

    return value
