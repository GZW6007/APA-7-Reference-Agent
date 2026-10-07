from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apa7_agent.pipeline import ReferenceAgent
from apa7_agent.providers import CrossrefProvider
from apa7_agent.reporting import write_corrected_references, write_json, write_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apa7-ref", description="Extract, verify, and audit APA 7 references.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Analyze one academic document or reference-list file.")
    check.add_argument("input", type=Path, help="Input .txt, .md, .pdf, or .docx file")
    check.add_argument("--output-dir", type=Path, default=Path("apa7-report"))
    check.add_argument("--offline", action="store_true", help="Skip external metadata verification")
    check.add_argument("--no-auto-fix", action="store_true", help="Report suggestions without applying them")
    check.add_argument("--mailto", help="Contact email sent to Crossref (recommended by Crossref etiquette)")
    check.add_argument("--title-threshold", type=float, default=0.92, help="Minimum 0-1 title similarity for a candidate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "check":
        return 2
    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2
    if not 0.0 <= args.title_threshold <= 1.0:
        print("error: --title-threshold must be between 0 and 1", file=sys.stderr)
        return 2

    provider = None
    if not args.offline:
        provider = CrossrefProvider(mailto=args.mailto, cache_path=args.output_dir / ".apa7-cache.json")
    agent = ReferenceAgent(provider=provider, auto_fix=not args.no_auto_fix, title_threshold=args.title_threshold)
    try:
        report = agent.analyze(args.input)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(report, args.output_dir / "report.json")
    write_markdown(report, args.output_dir / "report.md")
    write_corrected_references(report, args.output_dir / "corrected_references.txt")
    summary = report.to_dict()["summary"]
    print(
        f"Analyzed {summary['total']} references: {summary['verified']} verified, "
        f"{summary['needs_review']} need review, {summary['unverifiable']} unverifiable."
    )
    print(f"Reports written to: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

