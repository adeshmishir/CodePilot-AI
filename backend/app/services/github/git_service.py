import os
import re
import shutil

from pathlib import Path
from urllib.parse import quote, urlparse

from git import Repo

from app.config.settings import settings
from app.core.exceptions import RepositoryCloneError
from app.services.repository.paths import backend_root, relative_local_path

CLONE_FAILED_MESSAGE = (
    "Repository could not be cloned. Please check the GitHub URL and "
    "repository access."
)

AUTH_FAILED_MESSAGE = (
    "Repository could not be cloned. GitHub authentication is missing or "
    "invalid, or the token does not have access to this repository."
)

NOT_FOUND_MESSAGE = (
    "Repository could not be cloned. GitHub reports that this repository "
    "does not exist, was renamed, or is not publicly accessible."
)

NETWORK_FAILED_MESSAGE = (
    "Repository could not be cloned. Could not connect to GitHub. Check "
    "your network connection and try again."
)

INVALID_URL_MESSAGE = (
    "Invalid repository URL. Please provide a full GitHub URL such as "
    "https://github.com/owner/repository."
)

GITHUB_HOST = "github.com"

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

        try:
            self._clone_repository(url, repository_path)
        except Exception:
            _remove_tree(repository_path)
            raise

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
            or "not granted" in message
            or "write access" in message
            or "403" in message
            or "401" in message
        ):
            return AUTH_FAILED_MESSAGE

        if (
            "not found" in message
            or "does not appear" in message
            or "could not read from remote repository" in message
        ):
            return NOT_FOUND_MESSAGE

        if (
            "could not resolve host" in message
            or "unable to access" in message
            or "network" in message
            or "timed out" in message
            or "temporary failure" in message
        ):
            return NETWORK_FAILED_MESSAGE

        return CLONE_FAILED_MESSAGE

    def _redact_error(self, error: Exception) -> str:
        message = str(error)

        token = settings.GITHUB_TOKEN.strip()

        if token:
            message = message.replace(token, "***")

        return _redact_credentials(message)[:MAX_DETAIL_LENGTH]

    def _build_clone_url(self, url: str) -> str:
        """Return a clone URL, injecting the server-side GitHub token only
        for github.com hosts. The credentials are transient and never stored.
        """
        token = settings.GITHUB_TOKEN.strip()

        if not token:
            return url

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or parsed.hostname is None:
            return url

        if parsed.hostname.lower() != GITHUB_HOST:
            return url

        owner, repository = self._extract_repository_info(url)

        encoded_token = quote(token, safe="")

        return (
            f"https://x-access-token:{encoded_token}@github.com/"
            f"{owner}/{repository}.git"
        )

    def _clone_repository(self, url: str, destination: Path) -> None:
        clone_url = self._build_clone_url(url)

        parsed = urlparse(clone_url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        is_github = hostname == GITHUB_HOST

        try:
            Repo.clone_from(
                clone_url,
                destination,
                depth=1 if is_github else None,
                env={"GIT_TERMINAL_PROMPT": "0"},
            )
        except Exception as error:
            raise RepositoryCloneError(
                self._describe_clone_error(error),
                detail=self._redact_error(error),
            ) from error


git_service = GitService()
