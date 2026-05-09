"""Evaluator-style metrics and validation summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import ValidationError

from app.api.schemas import ChatResponse
from app.catalog.repository import CatalogRepository


@dataclass(frozen=True)
class EvaluationRun:
    run_id: str
    schema_pass: bool
    catalog_only_pass: bool
    turn_cap_pass: bool
    timeout_pass: bool
    recall_at_10: float | None = None
    probe_results: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_identifier(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/")
    return " ".join(value.split())


def recall_at_k(expected: list[str], actual: list[str], *, k: int = 10) -> float | None:
    expected_set = {normalize_identifier(item) for item in expected if item}
    if not expected_set:
        return None
    actual_set = {normalize_identifier(item) for item in actual[:k] if item}
    return len(expected_set & actual_set) / len(expected_set)


def evaluate_chat_response(
    response: dict[str, Any],
    *,
    catalog: CatalogRepository,
    expected_urls: list[str] | None = None,
    turn_count: int = 0,
    elapsed_seconds: float = 0.0,
) -> EvaluationRun:
    failures: list[str] = []
    try:
        parsed = ChatResponse.model_validate(response)
        schema_pass = set(response.keys()) == {"reply", "recommendations", "end_of_conversation"}
    except (ValidationError, AttributeError):
        parsed = None
        schema_pass = False
    if not schema_pass:
        failures.append("schema")

    catalog_only_pass = True
    actual_urls: list[str] = []
    if parsed is not None:
        actual_urls = [recommendation.url for recommendation in parsed.recommendations]
        for url in actual_urls:
            if not catalog.contains_url(url, eligible_only=True):
                catalog_only_pass = False
                failures.append("catalog_only")
                break
    turn_cap_pass = turn_count <= 8
    timeout_pass = elapsed_seconds <= 30
    if not turn_cap_pass:
        failures.append("turn_cap")
    if not timeout_pass:
        failures.append("timeout")
    return EvaluationRun(
        run_id="chat-response",
        schema_pass=schema_pass,
        catalog_only_pass=catalog_only_pass,
        turn_cap_pass=turn_cap_pass,
        timeout_pass=timeout_pass,
        recall_at_10=recall_at_k(expected_urls or [], actual_urls, k=10),
        failures=failures,
    )


def compare_recall_baseline(*, current: float | None, baseline: float | None) -> dict[str, float | str | None]:
    if current is None or baseline is None:
        return {"status": "unavailable", "current": current, "baseline": baseline, "delta": None}
    delta = current - baseline
    if delta > 0:
        status = "improved"
    elif delta < 0:
        status = "regressed"
    else:
        status = "stable"
    return {"status": status, "current": current, "baseline": baseline, "delta": delta}