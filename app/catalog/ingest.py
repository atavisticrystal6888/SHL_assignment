"""Normalize the SHL product catalog into canonical recommender records."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import json5

from app.catalog.models import CatalogAssessment, CatalogCoverageSummary

SOURCE_URL = "https://www.shl.com/solutions/products/product-catalog/"
INELIGIBLE_NAME_PATTERNS = (
    "pre-packaged job solution",
    "prepackaged job solution",
    "job solution",
)
CATEGORY_TO_TEST_TYPE = {
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Simulations": "S",
    "Competencies": "C",
    "Development & 360": "D",
    "Assessment Exercises": "E",
}
REQUIRED_FIELDS = [
    "entity_id",
    "name",
    "url",
    "test_type",
    "categories",
    "description",
    "duration",
    "remote_testing",
    "adaptive_irt",
    "job_levels",
    "languages",
    "eligible_for_recommendation",
    "eligibility_source",
]


def parse_duration_minutes(duration: str, duration_raw: str = "") -> int | None:
    text = f"{duration} {duration_raw}"
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def derive_test_type(categories: list[str]) -> str:
    for category in categories:
        if category in CATEGORY_TO_TEST_TYPE:
            return CATEGORY_TO_TEST_TYPE[category]
    return "O"


def is_prepackaged_job_solution(name: str, categories: list[str], description: str) -> bool:
    haystack = " ".join([name, description, *categories]).lower()
    return any(pattern in haystack for pattern in INELIGIBLE_NAME_PATTERNS)


def eligibility_for(raw: dict[str, Any]) -> tuple[bool, str]:
    name = str(raw.get("name") or "").strip()
    link = str(raw.get("link") or raw.get("url") or "").strip()
    status = str(raw.get("status") or "").strip().lower()
    categories = [str(value).strip() for value in raw.get("keys") or raw.get("categories") or [] if str(value).strip()]
    description = str(raw.get("description") or "")

    if not name or not link or status != "ok":
        return False, "ineligible:missing_source_metadata"
    if not link.startswith("https://www.shl.com/products/product-catalog/view/"):
        return False, "ineligible:non_catalog_url"
    if is_prepackaged_job_solution(name, categories, description):
        return False, "ineligible:pre_packaged_job_solution"
    return True, "eligible:catalog_product_record"


def normalize_record(raw: dict[str, Any]) -> CatalogAssessment:
    categories = [str(value).strip() for value in raw.get("keys") or raw.get("categories") or [] if str(value).strip()]
    eligible, eligibility_source = eligibility_for(raw)
    duration = str(raw.get("duration") or "").strip()
    duration_raw = str(raw.get("duration_raw") or "").strip()
    return CatalogAssessment(
        entity_id=str(raw.get("entity_id") or raw.get("id") or "").strip(),
        name=str(raw.get("name") or "").strip(),
        url=str(raw.get("link") or raw.get("url") or "").strip(),
        test_type=derive_test_type(categories),
        categories=categories,
        description=str(raw.get("description") or "").strip(),
        duration=duration,
        duration_minutes=parse_duration_minutes(duration, duration_raw),
        remote_testing=str(raw.get("remote") or raw.get("remote_testing") or "unknown").strip() or "unknown",
        adaptive_irt=str(raw.get("adaptive") or raw.get("adaptive_irt") or "unknown").strip() or "unknown",
        job_levels=[str(value).strip() for value in raw.get("job_levels") or [] if str(value).strip()],
        languages=[str(value).strip() for value in raw.get("languages") or [] if str(value).strip()],
        status=str(raw.get("status") or "unknown").strip() or "unknown",
        eligible_for_recommendation=eligible,
        eligibility_source=eligibility_source,
        source_snapshot=str(raw.get("scraped_at") or "").strip(),
    )


def load_raw_catalog(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        return json5.loads(text)


def normalize_catalog(raw_records: list[dict[str, Any]]) -> list[CatalogAssessment]:
    return [normalize_record(record) for record in raw_records]


def build_coverage_summary(records: list[CatalogAssessment]) -> CatalogCoverageSummary:
    status_counts = Counter(record.status for record in records)
    category_counts: Counter[str] = Counter()
    job_level_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    for record in records:
        category_counts.update(record.categories)
        job_level_counts.update(record.job_levels)
        language_counts.update(record.languages)
    snapshots = [record.source_snapshot for record in records if record.source_snapshot]
    return CatalogCoverageSummary(
        source=SOURCE_URL,
        source_snapshot=max(snapshots) if snapshots else "unknown",
        total_records=len(records),
        eligible_records=sum(1 for record in records if record.eligible_for_recommendation),
        ineligible_records=sum(1 for record in records if not record.eligible_for_recommendation),
        eligibility_filter="status ok, canonical SHL product URL, explicit source metadata, not Pre-packaged Job Solution",
        required_fields=REQUIRED_FIELDS,
        status_counts=dict(status_counts),
        category_counts=dict(category_counts),
        job_level_counts=dict(job_level_counts),
        language_counts=dict(language_counts),
    )


def write_processed_catalog(raw_path: Path, catalog_path: Path, coverage_path: Path) -> tuple[list[CatalogAssessment], CatalogCoverageSummary]:
    records = normalize_catalog(load_raw_catalog(raw_path))
    coverage = build_coverage_summary(records)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps([record.model_dump() for record in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    coverage_path.write_text(json.dumps(coverage.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    return records, coverage


if __name__ == "__main__":
    from app.settings import settings

    write_processed_catalog(
        Path("data/raw/shl_product_catalog.json"),
        settings.catalog_path,
        settings.catalog_coverage_path,
    )
