from pathlib import Path
from app.core.exceptions import RepositoryCloneError
from git import Repo


class GitService:
    def __init__(self):
        self.repositories_dir = Path("data/repos")
        self.repositories_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def _extract_repository_info(self, url: str):
        path = url.rstrip("/").split("/")

        owner = path[-2]
        repository = path[-1].replace(".git", "")

        return owner, repository

    def _repository_exists(
        self,
        owner: str,
        repository: str
    ) -> bool:
        repository_path = (
            self.repositories_dir
            / owner
            / repository
        )

        return repository_path.exists()

    def _clone_repository(
        self,
        url: str,
        destination: Path
    ) -> None:
        try:
            Repo.clone_from(
                url,
                destination
            )

        except Exception as error:
            raise RepositoryCloneError(
                "Unable to clone repository"
            ) from error

    def clone_repository(self, url: str):
        owner, repository = self._extract_repository_info(url)

        repository_path = (
            self.repositories_dir
            / owner
            / repository
        )

        if self._repository_exists(owner, repository):
            return {
                "owner": owner,
                "repository": repository,
                "path": str(repository_path),
                "message": "Repository already exists"
            }

        repository_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._clone_repository(
            url,
            repository_path
        )

        return {
            "owner": owner,
            "repository": repository,
            "path": str(repository_path),
            "message": "Repository cloned successfully"
        }


git_service = GitService()