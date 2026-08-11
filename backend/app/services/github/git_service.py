import os
import shutil

from pathlib import Path

from git import Repo

from app.core.exceptions import RepositoryCloneError
from app.services.repository.paths import backend_root, relative_local_path


def _remove_tree(path: Path) -> None:
    """Remove a directory tree even if it contains read-only files."""
    if os.name == "nt":
        for root, _, files in os.walk(path):
            for name in files:
                os.chmod(os.path.join(root, name), 0o666)

    shutil.rmtree(path, ignore_errors=True)


class GitService:
    def __init__(self, repositories_dir: Path | None = None):
        if repositories_dir is None:
            repositories_dir = backend_root() / "data" / "repos"

        self.repositories_dir = repositories_dir
        self.repositories_dir.mkdir(parents=True, exist_ok=True)

    def _extract_repository_info(self, url: str):
        path = url.rstrip("/").split("/")

        owner = path[-2]
        repository = path[-1].replace(".git", "")

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

    def _clone_repository(self, url: str, destination: Path) -> None:
        try:
            Repo.clone_from(url, destination)
        except Exception as error:
            raise RepositoryCloneError(
                "Unable to clone repository"
            ) from error


git_service = GitService()
