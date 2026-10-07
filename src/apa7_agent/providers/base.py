from __future__ import annotations

from typing import Protocol

from apa7_agent.models import Metadata


class MetadataProvider(Protocol):
    def lookup_doi(self, doi: str) -> Metadata | None: ...

    def search_title(self, title: str) -> list[Metadata]: ...

