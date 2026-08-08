import json
import re

from app.services.github.github_client import GitHubClient
from app.services.llm.groq_service import GroqService


ISSUE_TRIAGE_PROMPT = (
    "You are CodePilot, an issue triage assistant.\n\n"
    "Classify each supplied GitHub issue. Assign a category, a "
    "severity, and up to three concise suggested labels that fit "
    "common GitHub conventions.\n"
    "Do not invent issues that are not supplied.\n"
    "Respond ONLY with a JSON object of this shape:\n"
    "{\n"
    '  "items": [\n'
    "    {\n"
    '      "issue_number": 12,\n'
    '      "category": "bug | feature | documentation | enhancement | question | other",\n'
    '      "severity": "low | medium | high | critical",\n'
    '      "suggested_labels": ["label-a", "label-b"],\n'
    '      "summary": "one or two sentence summary of the issue and recommended action"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Do not include markdown code fences, prose, or explanations."
)


def issue_triage_user_prompt(issues: list[dict]) -> str:
    sections = ["Issues:\n"]

    for issue in issues:
        labels = ", ".join(
            label.get("name", "")
            for label in issue.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        )

        sections.append(
            f"#{issue.get('number')} [{issue.get('state')}] "
            f"{issue.get('title')}\n"
            f"Labels: {labels or '(none)'}\n"
            f"Body:\n{issue.get('body') or '(no body)'}\n"
        )

    return "\n".join(sections)


VALID_CATEGORIES = {
    "bug",
    "feature",
    "documentation",
    "enhancement",
    "question",
    "other",
}

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


class IssueTriageError(Exception):
    pass


class IssueTriageService:
    """Fetch open issues and classify them for triage."""

    def __init__(
        self,
        github_client: GitHubClient,
        groq_service: GroqService,
    ):
        self.github_client = github_client
        self.groq_service = groq_service

    def list_issues(
        self,
        owner: str,
        repository: str,
        limit: int = 20,
    ) -> list[dict]:
        issues = self.github_client.list_open_issues(
            owner=owner,
            repository=repository,
            limit=limit,
        )

        return [
            self._to_summary(issue)
            for issue in issues
        ]

    def triage(
        self,
        owner: str,
        repository: str,
        limit: int = 20,
    ) -> list[dict]:
        issues = self.github_client.list_open_issues(
            owner=owner,
            repository=repository,
            limit=limit,
        )

        if not issues:
            return []

        raw = self.groq_service.generate(
            system_prompt=ISSUE_TRIAGE_PROMPT,
            user_prompt=issue_triage_user_prompt(issues),
        )

        by_number = {issue["number"]: issue for issue in issues}

        return self._parse_triage(raw, by_number)

    def _parse_triage(
        self,
        raw: str,
        by_number: dict[int, dict],
    ) -> list[dict]:
        data = self._parse_json(raw)

        if not isinstance(data, dict):
            raise IssueTriageError(
                "Triage produced an invalid response shape."
            )

        items = data.get("items", [])

        if not isinstance(items, list):
            raise IssueTriageError(
                "Triage produced an invalid items list."
            )

        results = []

        for item in items:
            entry = self._coerce_entry(item)

            if entry is None:
                continue

            issue = by_number.get(entry["issue_number"])

            if issue is None:
                continue

            entry["title"] = issue.get("title", "")
            entry["state"] = issue.get("state", "")
            entry["author"] = (
                issue.get("user", {}).get("login", "")
                if isinstance(issue.get("user"), dict)
                else ""
            )
            entry["labels"] = [
                label.get("name", "")
                for label in issue.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            ]
            entry["created_at"] = issue.get("created_at")
            entry["url"] = issue.get("html_url")

            results.append(entry)

        return results

    def _coerce_entry(self, item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        issue_number = item.get("issue_number")

        if not isinstance(issue_number, int):
            return None

        category = item.get("category")

        if (
            not isinstance(category, str)
            or category.lower() not in VALID_CATEGORIES
        ):
            category = "other"

        severity = item.get("severity")

        if (
            not isinstance(severity, str)
            or severity.lower() not in VALID_SEVERITIES
        ):
            severity = "medium"

        suggested_labels = item.get("suggested_labels", [])

        if not isinstance(suggested_labels, list):
            suggested_labels = []

        return {
            "issue_number": issue_number,
            "category": category,
            "severity": severity,
            "suggested_labels": [
                str(label) for label in suggested_labels[:3]
            ],
            "summary": item.get("summary") or "No summary provided.",
        }

    def _parse_json(self, raw: str):
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise IssueTriageError(
                "Triage produced malformed output."
            ) from error

    def _to_summary(self, issue: dict) -> dict:
        return {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "author": (
                issue.get("user", {}).get("login", "")
                if isinstance(issue.get("user"), dict)
                else ""
            ),
            "labels": [
                label.get("name", "")
                for label in issue.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            ],
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "url": issue.get("html_url"),
        }


issue_triage_service: IssueTriageService | None = None


def get_issue_triage_service() -> IssueTriageService:
    global issue_triage_service

    if issue_triage_service is None:
        issue_triage_service = IssueTriageService(
            github_client=GitHubClient(),
            groq_service=GroqService(),
        )

    return issue_triage_service
