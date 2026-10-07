from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apa7_agent.web.app import app


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_index_and_health(self) -> None:
        index = self.client.get("/")
        self.assertEqual(200, index.status_code)
        self.assertIn("APA 7 Reference Agent", index.text)
        health = self.client.get("/api/health")
        self.assertEqual({"status": "ok", "version": "0.2.0"}, health.json())

    def test_offline_analysis(self) -> None:
        fixture = Path("tests/fixtures/sample.txt")
        with fixture.open("rb") as handle:
            response = self.client.post(
                "/api/analyze",
                files={"file": (fixture.name, handle, "text/plain")},
                data={"offline": "true", "auto_fix": "true", "title_threshold": "0.92"},
            )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(2, payload["summary"]["total"])
        self.assertEqual("sample.txt", payload["upload"]["filename"])
        self.assertIn("markdown", payload["exports"])
        self.assertIn("corrected_references", payload["exports"])

    def test_rejects_unsupported_upload(self) -> None:
        response = self.client.post(
            "/api/analyze",
            files={"file": ("malware.exe", b"not really", "application/octet-stream")},
            data={"offline": "true"},
        )
        self.assertEqual(415, response.status_code)


if __name__ == "__main__":
    unittest.main()
