import logging

import httpx

from app.config.settings import settings


logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"


class GitHubAuthError(Exception):
    pass


class GitHubApiError(Exception):
    pass


class GitHubNotFoundError(GitHubApiError):
    pass


class GitHubClient:
    """Thin REST client for the GitHub API."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN

    def list_open_pull_requests(
        self,
        owner: str,
        repository: str,
        limit: int = 20,
    ) -> list[dict]:
        data = self._get(
            f"/repos/{owner}/{repository}/pulls",
            params={
                "state": "open",
                "per_page": limit,
                "sort": "updated",
                "direction": "desc",
            },
        )
        return data if isinstance(data, list) else []

    def get_pull_request(
        self,
        owner: str,
        repository: str,
        pull_number: int,
    ) -> dict:
        data = self._get(
            f"/repos/{owner}/{repository}/pulls/{pull_number}"
        )

        if not isinstance(data, dict):
            raise GitHubApiError(
                "GitHub returned an invalid pull request response."
            )

        return data

    def get_pull_request_files(
        self,
        owner: str,
        repository: str,
        pull_number: int,
        limit: int = 50,
    ) -> list[dict]:
        data = self._get(
            f"/repos/{owner}/{repository}/pulls/{pull_number}/files",
            params={"per_page": limit},
        )
        return data if isinstance(data, list) else []

    def list_open_issues(
        self,
        owner: str,
        repository: str,
        limit: int = 20,
    ) -> list[dict]:
        data = self._get(
            f"/repos/{owner}/{repository}/issues",
            params={
                "state": "open",
                "per_page": limit,
                "sort": "updated",
                "direction": "desc",
            },
        )

        issues = data if isinstance(data, list) else []

        return [
            issue
            for issue in issues
            if "pull_request" not in issue
        ]

    def _get(
        self,
        path: str,
        params: dict | None = None,
    ):
        if not self.token:
            raise GitHubAuthError(
                "GITHUB_TOKEN is not configured. Add a GitHub personal "
                "access token to the .env file to use GitHub features."
            )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            response = httpx.get(
                f"{GITHUB_API_BASE_URL}{path}",
                params=params,
                headers=headers,
                timeout=30,
            )
        except httpx.HTTPError as error:
            logger.error("GitHub request to %s failed: %s", path, error)
            raise GitHubApiError(
                "Unable to reach the GitHub API."
            ) from error

        if response.status_code == 404:
            raise GitHubNotFoundError(
                "The repository, pull request, or issue was not found "
                "on GitHub."
            )

        if response.status_code in (401, 403):
            raise GitHubAuthError(
                "GitHub rejected the token. Verify GITHUB_TOKEN is "
                "valid and has the required permissions."
            )

        if response.status_code >= 400:
            raise GitHubApiError(
                f"GitHub API returned status {response.status_code}."
            )

        try:
            return response.json()
        except ValueError as error:
            raise GitHubApiError(
                "GitHub API returned an unreadable response."
            ) from error
