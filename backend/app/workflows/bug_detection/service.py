import json
import re
import threading

from app.services.llm.groq_service import GroqService
from app.services.rag.context_builder import ContextBuilder
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)
from app.workflows.bug_detection.prompts import (
    BUG_ANALYSIS_PROMPT,
    bug_analysis_user_prompt,
)


class BugDetectionError(Exception):
    pass


VALID_SEVERITIES = {"low", "medium", "high", "critical"}

REQUIRED_FINDING_FIELDS = [
    "title",
    "severity",
    "description",
    "file_path",
    "start_line",
    "end_line",
    "evidence",
    "recommendation",
]


class BugDetectionService:
    """Retrieve repository code and analyze it for potential bugs."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilder,
        groq_service: GroqService,
    ):
        self.retrieval_service = retrieval_service
        self.context_builder = context_builder
        self.groq_service = groq_service

    def analyze(
        self,
        query: str,
        repository_id: int,
        limit: int = 8,
    ) -> dict:
        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        sources = [
            {
                "file_path": result.get("file_path"),
                "symbol_name": result.get("symbol_name"),
                "start_line": result.get("start_line"),
                "end_line": result.get("end_line"),
                "score": result.get("score"),
            }
            for result in results
        ]

        if not results:
            return {
                "findings": [],
                "sources": sources,
            }

        context = self.context_builder.build(results)

        raw = self.groq_service.generate(
            system_prompt=BUG_ANALYSIS_PROMPT,
            user_prompt=bug_analysis_user_prompt(query, context),
        )

        source_paths = {
            result.get("file_path")
            for result in results
            if result.get("file_path")
        }

        findings = self._parse_findings(raw, source_paths)

        return {
            "findings": findings,
            "sources": sources,
        }

    def _parse_findings(
        self,
        raw: str,
        source_paths: set[str],
    ) -> list[dict]:
        data = self._parse_json(raw)

        if not isinstance(data, dict):
            raise BugDetectionError(
                "Bug analysis produced an invalid response shape."
            )

        raw_findings = data.get("findings")

        if not isinstance(raw_findings, list):
            raise BugDetectionError(
                "Bug analysis produced an invalid findings list."
            )

        findings = []

        for item in raw_findings:
            finding = self._coerce_finding(item)

            if finding is None:
                continue

            if finding["file_path"] not in source_paths:
                continue

            findings.append(finding)

        return findings

    def _parse_json(self, raw: str):
        text = raw.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise BugDetectionError(
                "Bug analysis produced malformed output."
            ) from error

    def _coerce_finding(self, item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        if any(field not in item for field in REQUIRED_FINDING_FIELDS):
            return None

        severity = item.get("severity")

        if (
            not isinstance(severity, str)
            or severity.lower() not in VALID_SEVERITIES
        ):
            return None

        start_line = item.get("start_line")
        end_line = item.get("end_line")

        if not isinstance(start_line, int) or not isinstance(end_line, int):
            return None

        return {
            "title": item.get("title"),
            "severity": severity.lower(),
            "description": item.get("description"),
            "file_path": item.get("file_path"),
            "start_line": start_line,
            "end_line": end_line,
            "evidence": item.get("evidence"),
            "recommendation": item.get("recommendation"),
        }


bug_detection_service: BugDetectionService | None = None
bug_detection_service_lock = threading.Lock()


def get_bug_detection_service() -> BugDetectionService:
    global bug_detection_service

    if bug_detection_service is None:
        with bug_detection_service_lock:
            if bug_detection_service is None:
                bug_detection_service = BugDetectionService(
                    retrieval_service=get_retrieval_service(),
                    context_builder=ContextBuilder(),
                    groq_service=GroqService(),
                )

    return bug_detection_service
