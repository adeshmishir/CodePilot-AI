import os
import re
import shutil

from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from app.core.exceptions import RepositoryCloneError
from app.services.repository.paths import backend_root, relative_local_path

CLONE_FAILED_MESSAGE = (
    "Repository could not be cloned. Please check the GitHub URL and "
    "repository access."
)

INVALID_URL_MESSAGE = (
    "Invalid repository URL. Please provide a full GitHub URL such as "
    "https://github.com/owner/repository."
)

MAX_DETAIL_LENGTH = 400


def _remove_tree(path: Path) -> None:
    """Remove a directory tree even if it contains read-only files."""
    if os.name == "nt":
        for root, _, files in os.walk(path):
            for name in files:
                os.chmod(os.path.join(root, name), 0o666)

    shutil.rmtree(path, ignore_errors=True)


def _redact_credentials(text: str) -> str:
    """Mask credentials embedded in URLs inside arbitrary text."""
    return re.sub(
        r"(?<=://)([^/@:\s]+):([^/@\s]+)@",
        r"\1:***@",
        text,
    )


class GitService:
    def __init__(self, repositories_dir: Path | None = None):
        if repositories_dir is None:
            repositories_dir = backend_root() / "data" / "repos"

        self.repositories_dir = repositories_dir
        self.repositories_dir.mkdir(parents=True, exist_ok=True)

    def _extract_repository_info(self, url: str):
        value = url.strip()

        if "://" in value:
            parsed = urlparse(value)

            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise RepositoryCloneError(INVALID_URL_MESSAGE)

            path = parsed.path
        else:
            path = value

        parts = [part for part in path.replace("\\", "/").split("/") if part]

        if len(parts) < 2:
            raise RepositoryCloneError(INVALID_URL_MESSAGE)

        owner = parts[-2]
        repository = parts[-1].replace(".git", "")

        if not owner or not repository:
            raise RepositoryCloneError(INVALID_URL_MESSAGE)

        return owner, repository

    def _destination(self, owner: str, repository: str) -> Path:
        return self.repositories_dir / owner / repository

    def _local_path(self, repository_path: Path) -> str:
        return relative_local_path(repository_path)

    def is_valid_repository(self, path: Path) -> bool:
        return (
            path.is_dir()
            and (path / ".git").is_dir()
        )

    def clone_repository(self, url: str):
        owner, repository = self._extract_repository_info(url)

        repository_path = self._destination(owner, repository)

        if self.is_valid_repository(repository_path):
            return {
                "success": True,
                "owner": owner,
                "repository": repository,
                "local_path": self._local_path(repository_path),
                "message": "Repository already exists",
            }

        return self._clone(
            url,
            repository_path,
            owner,
            repository,
        )

    def recover_repository(self, clone_url: str):
        """Ensure a valid clone exists, repairing or re-cloning if needed."""
        owner, repository = self._extract_repository_info(clone_url)

        repository_path = self._destination(owner, repository)

        if self.is_valid_repository(repository_path):
            return {
                "success": True,
                "owner": owner,
                "repository": repository,
                "local_path": self._local_path(repository_path),
                "message": "Repository already exists",
            }

        return self._clone(
            clone_url,
            repository_path,
            owner,
            repository,
        )

    def remove_repository(self, local_path: Path) -> None:
        """Best-effort removal of a repository checkout."""
        _remove_tree(local_path)

    def _clone(
        self,
        url: str,
        repository_path: Path,
        owner: str,
        repository: str,
    ):
        if repository_path.exists():
            _remove_tree(repository_path)

        repository_path.parent.mkdir(parents=True, exist_ok=True)

        self._clone_repository(url, repository_path)

        return {
            "success": True,
            "owner": owner,
            "repository": repository,
            "local_path": self._local_path(repository_path),
            "message": "Repository cloned successfully",
        }

    def _describe_clone_error(self, error: Exception) -> str:
        message = str(error).lower()

        if (
            "could not read username" in message
            or "authentication" in message
            or "access denied" in message
            or "permission denied" in message
            or "403" in message
            or "401" in message
        ):
            return (
                "GitHub rejected the clone because authentication is missing "
                "or invalid. Private repositories require access credentials."
            )

        if (
            "not found" in message
            or "does not appear" in message
            or "could not read from remote repository" in message
        ):
            return (
                "GitHub reports that this repository does not exist, was "
                "renamed, or is not publicly accessible."
            )

        if (
            "could not resolve host" in message
            or "unable to access" in message
            or "network" in message
            or "timed out" in message
            or "temporary failure" in message
        ):
            return (
                "Could not connect to GitHub. Check your network connection "
                "and try again."
            )

        return CLONE_FAILED_MESSAGE

    def _redact_error(self, error: Exception) -> str:
        return _redact_credentials(str(error))[:MAX_DETAIL_LENGTH]

    def _clone_repository(self, url: str, destination: Path) -> None:
        try:
            Repo.clone_from(url, destination)
        except Exception as error:
            raise RepositoryCloneError(
                self._describe_clone_error(error),
                detail=self._redact_error(error),
            ) from error


git_service = GitService()
