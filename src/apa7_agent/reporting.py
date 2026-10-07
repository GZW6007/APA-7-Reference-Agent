from __future__ import annotations

import json
from pathlib import Path

from apa7_agent.models import AnalysisReport


def write_json(report: AnalysisReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def render_markdown(report: AnalysisReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# APA 7 Reference Audit",
        "",
        f"- Input: `{report.input_file}`",
        f"- Total references: {summary['total']}",
        f"- Verified: {summary['verified']}",
        f"- Needs review: {summary['needs_review']}",
        f"- Unverifiable: {summary['unverifiable']}",
        "",
        "> Scope note: plain-text extraction cannot reliably verify italics, hanging indents, or all source-specific APA rules.",
        "",
    ]
    for result in report.results:
        lines.extend(
            [
                f"## {result.index}. {result.status.value}",
                "",
                f"**Original:** {result.original}",
                "",
                f"**Verification:** {result.verification_reason or 'No explanation available.'}",
                "",
            ]
        )
        if result.corrected:
            label = "Auto-corrected" if result.correction_applied else "Suggested (not applied)"
            lines.extend([f"**{label}:** {result.corrected}", ""])
        if result.issues:
            lines.append("**APA checks:**")
            lines.append("")
            lines.extend(f"- `{issue.severity.value}` `{issue.code}` — {issue.message}" for issue in result.issues)
            lines.append("")
        if result.metadata:
            lines.extend(
                [
                    f"**Metadata:** {result.metadata.source}; method={result.metadata.match_method}; confidence={result.metadata.score:.2f}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_markdown(report: AnalysisReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")


def render_corrected_references(report: AnalysisReport) -> str:
    lines = []
    for result in report.results:
        if result.correction_applied and result.corrected:
            lines.append(result.corrected)
        else:
            lines.append(result.original)
    return "\n\n".join(lines) + ("\n" if lines else "")


def write_corrected_references(report: AnalysisReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_corrected_references(report), encoding="utf-8")
