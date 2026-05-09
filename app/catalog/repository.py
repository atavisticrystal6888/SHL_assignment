"""Read-only access to the processed SHL catalog."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.catalog.models import CatalogAssessment

ASSESSMENT_ALIASES = {
    "opq": "Occupational Personality Questionnaire OPQ32r",
    "opq32r": "Occupational Personality Questionnaire OPQ32r",
    "occupational personality questionnaire": "Occupational Personality Questionnaire OPQ32r",
    "occupational personality questionnaire opq32r": "Occupational Personality Questionnaire OPQ32r",
    "gsa": "Global Skills Assessment",
    "global skills assessment": "Global Skills Assessment",
    "global skills development report": "Global Skills Development Report",
    "verify g": "SHL Verify Interactive G+",
    "verify g+": "SHL Verify Interactive G+",
    "verify interactive g": "SHL Verify Interactive G+",
    "verify interactive g+": "SHL Verify Interactive G+",
    "shl verify interactive g": "SHL Verify Interactive G+",
    "shl verify interactive g+": "SHL Verify Interactive G+",
    "dsi": "Dependability and Safety Instrument (DSI)",
    "dependability and safety instrument": "Dependability and Safety Instrument (DSI)",
}
STOPWORDS = {"assessment", "assessments", "test", "tests", "the", "a", "an"}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass(frozen=True)
class CatalogResolution:
    query: str
    status: str
    matches: list[CatalogAssessment]

    @property
    def record(self) -> CatalogAssessment | None:
        if self.status == "resolved" and self.matches:
            return self.matches[0]
        return None


class CatalogRepository:
    def __init__(self, records: list[CatalogAssessment]) -> None:
        self.records = records
        self.eligible_records = [record for record in records if record.eligible_for_recommendation]
        self.urls = {record.url for record in records}
        self.eligible_urls = {record.url for record in self.eligible_records}
        self._by_name = {normalize_name(record.name): record for record in records}
        self._aliases = {normalize_name(alias): name for alias, name in ASSESSMENT_ALIASES.items()}

    @classmethod
    def from_path(cls, path: Path) -> "CatalogRepository":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls([CatalogAssessment.model_validate(item) for item in data])

    def contains_url(self, url: str, *, eligible_only: bool = False) -> bool:
        return url in (self.eligible_urls if eligible_only else self.urls)

    def by_name(self, name: str) -> CatalogAssessment | None:
        return self._by_name.get(normalize_name(name))

    def search_name(self, query: str, *, limit: int = 10) -> list[CatalogAssessment]:
        normalized_query = normalize_name(query)
        if not normalized_query:
            return []
        matches = [record for record in self.records if normalized_query in normalize_name(record.name)]
        return sorted(matches, key=lambda record: record.name.lower())[:limit]

    def resolve_assessment_reference(self, query: str, *, limit: int = 5) -> CatalogResolution:
        normalized_query = normalize_name(query)
        if not normalized_query:
            return CatalogResolution(query=query, status="not_found", matches=[])

        alias_target = self._aliases.get(normalized_query)
        if alias_target:
            record = self.by_name(alias_target)
            if record is not None:
                return CatalogResolution(query=query, status="resolved", matches=[record])

        exact = self.by_name(query)
        if exact is not None:
            return CatalogResolution(query=query, status="resolved", matches=[exact])

        matches = self.search_name(query, limit=limit + 1)
        if not matches:
            tokens = [token for token in normalized_query.split() if token not in STOPWORDS and len(token) > 1]
            matches = [
                record
                for record in self.records
                if tokens and all(token in normalize_name(record.name) for token in tokens)
            ]
            matches = sorted(matches, key=lambda record: record.name.lower())[: limit + 1]
        if len(matches) == 1:
            return CatalogResolution(query=query, status="resolved", matches=matches)
        if len(matches) > 1:
            return CatalogResolution(query=query, status="ambiguous", matches=matches[:limit])
        return CatalogResolution(query=query, status="not_found", matches=[])
