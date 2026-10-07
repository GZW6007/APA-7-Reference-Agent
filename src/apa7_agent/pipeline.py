from __future__ import annotations

from pathlib import Path

from apa7_agent.apa import compare_with_metadata, format_from_metadata, inspect_reference, normalize_doi_only
from apa7_agent.extractors import extract_references_section, read_document
from apa7_agent.models import AnalysisReport, ReferenceResult, VerificationStatus
from apa7_agent.providers.base import MetadataProvider
from apa7_agent.references import extract_doi, split_references, title_guess


class ReferenceAgent:
    def __init__(self, provider: MetadataProvider | None, auto_fix: bool = True, title_threshold: float = 0.92) -> None:
        self.provider = provider
        self.auto_fix = auto_fix
        self.title_threshold = title_threshold

    def analyze(self, input_path: Path) -> AnalysisReport:
        extraction = extract_references_section(read_document(input_path))
        references = split_references(extraction.text)
        results = [self._analyze_one(index, reference) for index, reference in enumerate(references, start=1)]
        return AnalysisReport(str(input_path), extraction.heading_found, extraction.notes, results)

    def _analyze_one(self, index: int, reference: str) -> ReferenceResult:
        issues = inspect_reference(reference)
        normalized = normalize_doi_only(reference)
        metadata = None
        reason = None
        doi = extract_doi(reference)

        if self.provider is None:
            reason = "Metadata lookup was disabled (offline mode)."
        elif doi:
            try:
                metadata = self.provider.lookup_doi(doi)
                if metadata is None:
                    reason = "The DOI was not found in the metadata provider."
            except RuntimeError as exc:
                reason = str(exc)
        else:
            guessed_title = title_guess(reference)
            if not guessed_title:
                reason = "No DOI was present and a reliable title could not be extracted."
            else:
                try:
                    candidates = self.provider.search_title(guessed_title)
                    metadata = candidates[0] if candidates and candidates[0].score >= self.title_threshold else None
                    if metadata is None:
                        best = candidates[0].score if candidates else 0.0
                        reason = f"No title match met the confidence threshold ({best:.2f} < {self.title_threshold:.2f})."
                except RuntimeError as exc:
                    reason = str(exc)

        corrected = normalized if normalized != reference else None
        correction_applied = bool(corrected and self.auto_fix)

        if metadata and metadata.match_method == "doi_exact":
            issues.extend(compare_with_metadata(reference, metadata))
            formatted = format_from_metadata(metadata)
            if formatted:
                corrected = formatted
                correction_applied = self.auto_fix and corrected != reference
            status = VerificationStatus.VERIFIED
            reason = "DOI matched an authoritative Crossref record."
        elif metadata:
            issues.extend(compare_with_metadata(reference, metadata))
            status = VerificationStatus.NEEDS_REVIEW
            reason = f"Probable title match ({metadata.score:.2f}); confirm before replacing the reference."
            suggested = format_from_metadata(metadata)
            if suggested:
                corrected = suggested
            correction_applied = False
        elif reason and ("disabled" in reason or "failed" in reason or "not found" in reason):
            status = VerificationStatus.UNVERIFIABLE
        else:
            status = VerificationStatus.NEEDS_REVIEW

        if not self.auto_fix:
            correction_applied = False
        return ReferenceResult(index, reference, status, issues, metadata, corrected, correction_applied, reason)
