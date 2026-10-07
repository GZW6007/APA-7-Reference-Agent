from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    UNVERIFIABLE = "unverifiable"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class Issue:
    code: str
    message: str
    severity: Severity
    auto_fixable: bool = False


@dataclass(slots=True)
class Metadata:
    source: str
    source_id: str | None = None
    doi: str | None = None
    title: str | None = None
    authors: list[dict[str, str]] = field(default_factory=list)
    year: int | None = None
    container_title: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None
    item_type: str | None = None
    url: str | None = None
    score: float = 0.0
    match_method: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(slots=True)
class ReferenceResult:
    index: int
    original: str
    status: VerificationStatus
    issues: list[Issue] = field(default_factory=list)
    metadata: Metadata | None = None
    corrected: str | None = None
    correction_applied: bool = False
    verification_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        for issue in value["issues"]:
            issue["severity"] = issue["severity"].value
        return value


@dataclass(slots=True)
class AnalysisReport:
    input_file: str
    references_heading_found: bool
    extraction_notes: list[str]
    results: list[ReferenceResult]

    def to_dict(self) -> dict[str, Any]:
        counts = {status.value: 0 for status in VerificationStatus}
        for result in self.results:
            counts[result.status.value] += 1
        return {
            "schema_version": "1.0",
            "input_file": self.input_file,
            "references_heading_found": self.references_heading_found,
            "extraction_notes": self.extraction_notes,
            "summary": {"total": len(self.results), **counts},
            "results": [result.to_dict() for result in self.results],
        }

