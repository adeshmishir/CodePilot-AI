import json
import re

from app.services.github.github_client import GitHubClient
from app.services.llm.groq_service import GroqService


PR_REVIEW_PROMPT = (
    "You are CodePilot, a meticulous pull request reviewer.\n\n"
    "Review the supplied diff hunks. Identify concrete issues that "
    "matter: bugs, correctness problems, security risks, performance "
    "problems, and clear style violations.\n"
    "Only reference files and line numbers that appear in the diff "
    "context.\n"
    "Prefer fewer high-confidence findings over speculative ones.\n"
    "If there is nothing worth flagging, return an empty comments list "
    "and a short summary.\n\n"
    "Respond ONLY with a JSON object of this shape:\n"
    "{\n"
    '  "summary": "short overall assessment of the change",\n'
    '  "comments": [\n'
    "    {\n"
    '      "file_path": "path from the diff",\n'
    '      "line": 42,\n'
    '      "severity": "low | medium | high | critical",\n'
    '      "category": "bug | security | performance | style | nit",\n'
    '      "message": "explanation of the issue and suggested fix"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Do not include markdown code fences, prose, or explanations."
)


def pr_review_user_prompt(
    title: str,
    description: str,
    files: list[dict],
) -> str:
    sections = [
        f"Pull request title: {title}\n\n",
        f"Pull request description:\n{description or '(none)'}\n\n",
        "Diff:\n",
    ]

    for file in files:
        file_path = file.get("filename", "unknown")
        patch = file.get("patch", "")

        sections.append(
            f"### {file_path} ({file.get('status', 'modified')}, "
            f"+{file.get('additions', 0)} -{file.get('deletions', 0)})\n"
            f"{patch or '(no patch available)'}\n"
        )

    return "".join(sections)


class PullRequestReviewService:
    """Fetch pull request diffs and produce structured reviews."""

    def __init__(
        self,
        github_client: GitHubClient,
        groq_service: GroqService,
    ):
        self.github_client = github_client
        self.groq_service = groq_service

    def review(
        self,
        owner: str,
        repository: str,
        pull_number: int,
    ) -> dict:
        files = self.github_client.get_pull_request_files(
            owner=owner,
            repository=repository,
            pull_number=pull_number,
        )

        changed_files = [
            {
                "filename": file.get("filename"),
                "status": file.get("status"),
                "additions": file.get("additions"),
                "deletions": file.get("deletions"),
                "patch": file.get("patch"),
            }
            for file in files
        ]

        title = self._describe_pull_request(owner, repository, pull_number)

        if not changed_files:
            return {
                "pull_request_number": pull_number,
                "title": title,
                "summary": "No changed files were found to review.",
                "comments": [],
            }

        user_prompt = pr_review_user_prompt(
            title=title,
            description="",
            files=changed_files,
        )

        raw = self.groq_service.generate(
            system_prompt=PR_REVIEW_PROMPT,
            user_prompt=user_prompt,
        )

        return self._parse_review(raw, pull_number, title, changed_files)

    def _describe_pull_request(
        self,
        owner: str,
        repository: str,
        pull_number: int,
    ) -> str:
        data = self.github_client.get_pull_request(
            owner=owner,
            repository=repository,
            pull_number=pull_number,
        )

        return (
            data.get("title")
            or f"Pull request #{pull_number}"
        )

    def _parse_review(
        self,
        raw: str,
        pull_number: int,
        title: str,
        changed_files: list[dict],
    ) -> dict:
        data = self._parse_json(raw)

        if not isinstance(data, dict):
            raise PullRequestReviewError(
                "Review produced an invalid response shape."
            )

        available_paths = {
            file["filename"]
            for file in changed_files
            if file.get("filename")
        }

        comments = []

        raw_comments = data.get("comments", [])

        if isinstance(raw_comments, list):
            for item in raw_comments:
                comment = self._coerce_comment(item, available_paths)

                if comment is not None:
                    comments.append(comment)

        return {
            "pull_request_number": pull_number,
            "title": title,
            "summary": data.get("summary") or "No summary provided.",
            "comments": comments,
        }

    def _coerce_comment(
        self,
        item: object,
        available_paths: set[str],
    ) -> dict | None:
        if not isinstance(item, dict):
            return None

        file_path = item.get("file_path")
        severity = item.get("severity")

        if (
            not isinstance(file_path, str)
            or file_path not in available_paths
        ):
            return None

        if (
            not isinstance(severity, str)
            or severity.lower() not in VALID_SEVERITIES
        ):
            severity = "medium"

        line = item.get("line")

        if not isinstance(line, int):
            line = None

        category = item.get("category")

        if not isinstance(category, str) or category.lower() not in VALID_CATEGORIES:
            category = "nit"

        return {
            "file_path": file_path,
            "line": line,
            "severity": severity.lower(),
            "category": category,
            "message": item.get("message") or "No message provided.",
        }

    def _parse_json(self, raw: str):
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise PullRequestReviewError(
                "Review produced malformed output."
            ) from error


VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_CATEGORIES = {"bug", "security", "performance", "style", "nit"}


class PullRequestReviewError(Exception):
    pass


pull_request_review_service: PullRequestReviewService | None = None


def get_pull_request_review_service() -> PullRequestReviewService:
    global pull_request_review_service

    if pull_request_review_service is None:
        pull_request_review_service = PullRequestReviewService(
            github_client=GitHubClient(),
            groq_service=GroqService(),
        )

    return pull_request_review_service
