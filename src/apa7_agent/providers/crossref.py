from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from apa7_agent.models import Metadata


def _first(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0])
    return str(value) if value else None


def _year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "issued", "created"):
        parts = item.get(field, {}).get("date-parts", [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


def _normalize_title(value: str) -> str:
    return " ".join("".join(ch.casefold() if ch.isalnum() else " " for ch in value).split())


class CrossrefProvider:
    BASE_URL = "https://api.crossref.org"

    def __init__(
        self,
        mailto: str | None = None,
        cache_path: Path | None = None,
        timeout: float = 12.0,
        retries: int = 2,
    ) -> None:
        self.mailto = mailto
        self.cache_path = cache_path
        self.timeout = timeout
        self.retries = retries
        self.cache: dict[str, Any] = {}
        if cache_path and cache_path.exists():
            try:
                self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.cache = {}

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        params = dict(params or {})
        if self.mailto:
            params["mailto"] = self.mailto
        url = f"{self.BASE_URL}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        if url in self.cache:
            return self.cache[url]

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "apa7-reference-agent/0.1 (mailto:%s)" % (self.mailto or "not-provided")},
        )
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                self.cache[url] = payload
                self._save_cache()
                return payload
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"Crossref request failed: {last_error}")

    @staticmethod
    def _to_metadata(item: dict[str, Any], method: str, score: float) -> Metadata:
        authors = []
        for author in item.get("author", []) or []:
            authors.append(
                {
                    "family": str(author.get("family", "")).strip(),
                    "given": str(author.get("given", "")).strip(),
                }
            )
        doi = item.get("DOI")
        return Metadata(
            source="Crossref",
            source_id=doi or item.get("URL"),
            doi=str(doi).lower() if doi else None,
            title=_first(item.get("title")),
            authors=authors,
            year=_year(item),
            container_title=_first(item.get("container-title")),
            volume=str(item.get("volume")) if item.get("volume") else None,
            issue=str(item.get("issue")) if item.get("issue") else None,
            pages=str(item.get("page")) if item.get("page") else None,
            publisher=item.get("publisher"),
            item_type=item.get("type"),
            url=item.get("URL"),
            score=score,
            match_method=method,
            raw=item,
        )

    def lookup_doi(self, doi: str) -> Metadata | None:
        try:
            payload = self._get("/works/" + urllib.parse.quote(doi, safe=""))
        except RuntimeError as exc:
            if "HTTP Error 404" in str(exc):
                return None
            raise
        item = payload.get("message") if isinstance(payload, dict) else None
        return self._to_metadata(item, "doi_exact", 1.0) if isinstance(item, dict) else None

    def search_title(self, title: str) -> list[Metadata]:
        payload = self._get("/works", {"query.title": title, "rows": "5", "select": "DOI,title,author,issued,published-print,published-online,container-title,volume,issue,page,publisher,type,URL"})
        items = payload.get("message", {}).get("items", []) if isinstance(payload, dict) else []
        normalized_query = _normalize_title(title)
        results = []
        for item in items:
            candidate_title = _first(item.get("title")) or ""
            similarity = SequenceMatcher(None, normalized_query, _normalize_title(candidate_title)).ratio()
            results.append(self._to_metadata(item, "title_search", round(similarity, 4)))
        return sorted(results, key=lambda item: item.score, reverse=True)

