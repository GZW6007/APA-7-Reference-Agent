from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


REFERENCE_HEADINGS = {
    "references",
    "reference",
    "bibliography",
    "works cited",
    "參考文獻",
    "参考文献",
    "引用文獻",
}


@dataclass(slots=True)
class ExtractionResult:
    text: str
    heading_found: bool
    notes: list[str]


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires: pip install 'apa7-reference-agent[documents]'") from exc
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("DOCX support requires: pip install 'apa7-reference-agent[documents]'") from exc
    doc = Document(str(path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8-sig")
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}. Use .txt, .md, .pdf, or .docx")


def extract_references_section(text: str) -> ExtractionResult:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    heading_index: int | None = None
    for index, line in enumerate(lines):
        normalized = re.sub(r"^[#\s\d.、()（）]+|[:：\s]+$", "", line).strip().casefold()
        if normalized in REFERENCE_HEADINGS:
            heading_index = index

    notes: list[str] = []
    if heading_index is None:
        notes.append("No references heading was found; the whole document was treated as a reference list.")
        section = "\n".join(lines)
        found = False
    else:
        section = "\n".join(lines[heading_index + 1 :])
        found = True

    if not section.strip():
        notes.append("The extracted references section is empty.")
    return ExtractionResult(section.strip(), found, notes)

