from __future__ import annotations

import re


YEAR_PATTERN = re.compile(r"\((?:18|19|20)\d{2}[a-z]?\)|（(?:18|19|20)\d{2}[a-z]?）")
DOI_PATTERN = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
START_PATTERN = re.compile(
    r"^(?:\[?\d+\]?\s*[.)、]?\s*)?(?:[A-ZÀ-ÖØ-Þ\u3400-\u9fff][^\n]{0,100}?)(?:,|。|\s)"
)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_doi(reference: str) -> str | None:
    match = DOI_PATTERN.search(reference)
    if not match:
        return None
    return match.group(1).rstrip(".,;)]}").lower()


def _looks_like_start(line: str) -> bool:
    return bool(START_PATTERN.match(line) and YEAR_PATTERN.search(line[:180]))


def split_references(section: str) -> list[str]:
    """Split a plain-text reference section using blank lines and author/year starts."""
    raw_lines = section.splitlines()
    entries: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            value = normalize_whitespace(" ".join(current))
            value = re.sub(r"^\[?\d+\]?\s*[.)、]\s*", "", value)
            if value:
                entries.append(value)
            current.clear()

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            flush()
            continue
        if current and _looks_like_start(line):
            flush()
        current.append(line)
    flush()
    return entries


def title_guess(reference: str) -> str | None:
    """Best-effort title extraction for metadata search; never used as a correction."""
    after_year = YEAR_PATTERN.split(reference, maxsplit=1)
    if len(after_year) < 2:
        return None
    remainder = after_year[1].lstrip(".。 )）")
    candidates = re.split(r"\.\s+(?=[A-ZÀ-ÖØ-Þ])|。", remainder, maxsplit=1)
    title = normalize_whitespace(candidates[0]).strip(". ")
    return title if len(title) >= 4 else None

