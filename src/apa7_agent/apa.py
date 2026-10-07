from __future__ import annotations

import re
from difflib import SequenceMatcher

from apa7_agent.models import Issue, Metadata, Severity
from apa7_agent.references import DOI_PATTERN, YEAR_PATTERN, extract_doi, title_guess


def inspect_reference(reference: str) -> list[Issue]:
    issues: list[Issue] = []
    doi = extract_doi(reference)
    if not YEAR_PATTERN.search(reference):
        issues.append(Issue("missing_year", "No four-digit publication year in parentheses was detected.", Severity.ERROR))
    if doi:
        canonical = f"https://doi.org/{doi}"
        matched = DOI_PATTERN.search(reference)
        shown = matched.group(0) if matched else ""
        if not shown.lower().startswith("https://doi.org/"):
            issues.append(Issue("doi_not_url", f"DOI should use the URL form: {canonical}", Severity.ERROR, True))
        if reference.rstrip().rstrip(".").lower().endswith(doi) and reference.rstrip().endswith("."):
            issues.append(Issue("terminal_period_after_doi", "APA 7 does not place a period after a DOI URL.", Severity.ERROR, True))
    if "retrieved from" in reference.casefold():
        issues.append(Issue("retrieved_from", "'Retrieved from' is usually omitted unless a retrieval date is required.", Severity.WARNING))
    if re.search(r"\b(?:vol\.|volume)\s*\d", reference, re.I):
        issues.append(Issue("volume_label", "Journal volume normally appears without 'Vol.' or 'Volume'.", Severity.WARNING))
    if re.match(r"^\s*(?:and|&)\s", reference, re.I):
        issues.append(Issue("missing_author", "The reference appears to start without an author or group author.", Severity.ERROR))
    return issues


def compare_with_metadata(reference: str, metadata: Metadata) -> list[Issue]:
    """Report field-level discrepancies without treating fuzzy parsing as fact."""
    issues: list[Issue] = []
    year_match = YEAR_PATTERN.search(reference)
    if year_match and metadata.year:
        cited_year = int(re.search(r"\d{4}", year_match.group(0)).group(0))
        if cited_year != metadata.year:
            issues.append(
                Issue(
                    "metadata_year_mismatch",
                    f"Cited year {cited_year} differs from provider year {metadata.year}.",
                    Severity.ERROR,
                    metadata.match_method == "doi_exact",
                )
            )
    cited_title = title_guess(reference)
    if cited_title and metadata.title:
        normalize = lambda value: " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())
        similarity = SequenceMatcher(None, normalize(cited_title), normalize(metadata.title)).ratio()
        if similarity < 0.88:
            issues.append(
                Issue(
                    "metadata_title_mismatch",
                    f"Cited title differs from provider title (similarity {similarity:.2f}).",
                    Severity.WARNING,
                    metadata.match_method == "doi_exact",
                )
            )
    if metadata.doi and not extract_doi(reference):
        issues.append(
            Issue(
                "doi_missing",
                f"The matched metadata includes DOI https://doi.org/{metadata.doi}.",
                Severity.WARNING,
                False,
            )
        )
    return issues


def normalize_doi_only(reference: str) -> str:
    doi = extract_doi(reference)
    if not doi:
        return reference
    canonical = f"https://doi.org/{doi}"
    fixed = DOI_PATTERN.sub(canonical, reference, count=1)
    if fixed.rstrip().endswith(canonical + "."):
        fixed = fixed.rstrip()[:-1]
    return fixed


def _initials(given: str) -> str:
    words = [word for word in given.strip().split() if word]
    return " ".join("-".join(f"{part[0].upper()}." for part in word.split("-") if part) for word in words)


def format_authors(authors: list[dict[str, str]]) -> str:
    rendered = []
    for author in authors:
        family = author.get("family", "").strip()
        given = _initials(author.get("given", ""))
        rendered.append(", ".join(part for part in (family, given) if part))
    if not rendered:
        return ""
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) <= 20:
        return ", ".join(rendered[:-1]) + ", & " + rendered[-1]
    return ", ".join(rendered[:19]) + ", … " + rendered[-1]


def format_from_metadata(metadata: Metadata) -> str | None:
    """Format common Crossref records. Returns None when fields are insufficient."""
    authors = format_authors(metadata.authors)
    if not authors or not metadata.year or not metadata.title:
        return None
    title = metadata.title.rstrip(". ") + "."
    doi = f" https://doi.org/{metadata.doi}" if metadata.doi else ""
    if metadata.item_type in {"journal-article", "proceedings-article"} and metadata.container_title:
        source = f"{metadata.container_title}"
        if metadata.volume:
            source += f", {metadata.volume}"
            if metadata.issue:
                source += f"({metadata.issue})"
        if metadata.pages:
            source += f", {metadata.pages}"
        return f"{authors} ({metadata.year}). {title} {source}.{doi}".strip()
    if metadata.item_type in {"book", "monograph", "reference-book"} and metadata.publisher:
        return f"{authors} ({metadata.year}). {title} {metadata.publisher}.{doi}".strip()
    return None
