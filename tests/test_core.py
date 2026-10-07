from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apa7_agent.apa import inspect_reference, normalize_doi_only
from apa7_agent.cli import main
from apa7_agent.extractors import extract_references_section
from apa7_agent.models import Metadata, VerificationStatus
from apa7_agent.pipeline import ReferenceAgent
from apa7_agent.references import extract_doi, split_references


class FakeProvider:
    def lookup_doi(self, doi: str) -> Metadata | None:
        if doi != "10.1234/example.1":
            return None
        return Metadata(
            source="fixture",
            source_id=doi,
            doi=doi,
            title="A useful article",
            authors=[{"family": "Smith", "given": "John A"}, {"family": "Doe", "given": "Rita"}],
            year=2020,
            container_title="Testing Journal",
            volume="5",
            issue="2",
            pages="10–20",
            item_type="journal-article",
            score=1.0,
            match_method="doi_exact",
        )

    def search_title(self, title: str) -> list[Metadata]:
        if "book" in title.casefold():
            return [Metadata(source="fixture", title=title, score=0.95, match_method="title_search")]
        return []


class CoreTests(unittest.TestCase):
    def test_heading_and_split(self) -> None:
        text = Path("tests/fixtures/sample.txt").read_text(encoding="utf-8")
        extraction = extract_references_section(text)
        self.assertTrue(extraction.heading_found)
        self.assertEqual(2, len(split_references(extraction.text)))

    def test_doi_normalization_and_rules(self) -> None:
        ref = "Smith, J. (2020). Title. Journal, 1, 1-2. doi:10.1234/ABC.1."
        self.assertEqual("10.1234/abc.1", extract_doi(ref))
        fixed = normalize_doi_only(ref)
        self.assertTrue(fixed.endswith("https://doi.org/10.1234/abc.1"))
        codes = {issue.code for issue in inspect_reference(ref)}
        self.assertIn("doi_not_url", codes)
        self.assertIn("terminal_period_after_doi", codes)

    def test_pipeline_confidence_policy(self) -> None:
        report = ReferenceAgent(FakeProvider()).analyze(Path("tests/fixtures/sample.txt"))
        self.assertEqual(VerificationStatus.VERIFIED, report.results[0].status)
        self.assertTrue(report.results[0].correction_applied)
        self.assertEqual(VerificationStatus.NEEDS_REVIEW, report.results[1].status)
        self.assertFalse(report.results[1].correction_applied)

    def test_exact_metadata_mismatch_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "refs.txt"
            path.write_text(
                "References\n\nSmith, J. (2018). The wrong title. Testing Journal, 5, 1-2. https://doi.org/10.1234/example.1",
                encoding="utf-8",
            )
            result = ReferenceAgent(FakeProvider()).analyze(path).results[0]
            codes = {issue.code for issue in result.issues}
            self.assertIn("metadata_year_mismatch", codes)
            self.assertIn("metadata_title_mismatch", codes)

    def test_offline_cli_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code = main(["check", "tests/fixtures/sample.txt", "--offline", "--output-dir", directory])
            self.assertEqual(0, code)
            payload = json.loads((Path(directory) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(2, payload["summary"]["total"])
            self.assertEqual(2, payload["summary"]["unverifiable"])
            self.assertTrue((Path(directory) / "report.md").exists())
            self.assertTrue((Path(directory) / "corrected_references.txt").exists())


if __name__ == "__main__":
    unittest.main()
