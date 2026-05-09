"""Canonical catalog data models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CatalogAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    name: str
    url: str
    test_type: str
    categories: list[str] = Field(default_factory=list)
    description: str = ""
    duration: str = ""
    duration_minutes: int | None = None
    remote_testing: str = "unknown"
    adaptive_irt: str = "unknown"
    job_levels: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    status: str = "unknown"
    eligible_for_recommendation: bool = False
    eligibility_source: str = "ineligible:no_evidence"
    source_snapshot: str = ""

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be blank")
        return value


class CatalogCoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    source_snapshot: str
    total_records: int
    eligible_records: int
    ineligible_records: int
    eligibility_filter: str
    required_fields: list[str]
    status_counts: dict[str, int]
    category_counts: dict[str, int]
    job_level_counts: dict[str, int]
    language_counts: dict[str, int]
