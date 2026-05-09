"""Deterministic catalog ranking."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.metrics.pairwise import cosine_similarity

from app.catalog.models import CatalogAssessment
from app.catalog.repository import normalize_name
from app.conversation.extractor import UserGoalProfile, summarize_user_goal
from app.llm.client import LLMClient
from app.llm.prompts import build_rerank_prompt
from app.retrieval.index import CatalogIndex

CATEGORY_BY_FOCUS = {
    "skills": "Knowledge & Skills",
    "ability": "Ability & Aptitude",
    "personality": "Personality & Behavior",
    "situational judgment": "Biodata & Situational Judgment",
    "simulation": "Simulations",
}


@dataclass(frozen=True)
class CatalogMatch:
    assessment: CatalogAssessment
    score: float
    matched_fields: list[str]
    rationale_facts: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class RerankResult:
    matches: list[CatalogMatch]
    llm_status: str


def is_excluded(record: CatalogAssessment, excluded_terms: list[str]) -> bool:
    haystack = " ".join([record.name, record.description, record.url]).lower()
    return any(term.lower() in haystack for term in excluded_terms)


def max_duration_from_constraints(constraints: list[str]) -> int | None:
    for constraint in constraints:
        if constraint.startswith("max_duration:"):
            return int(constraint.split(":", maxsplit=1)[1])
    return None


def category_boost(record: CatalogAssessment, preferred_categories: list[str]) -> float:
    boost = 0.0
    for focus in preferred_categories:
        category = CATEGORY_BY_FOCUS.get(focus)
        if category and category in record.categories:
            boost += 0.45
        if focus == "personality" and record.test_type == "P":
            boost += 0.2
    return boost


def rank_catalog(
    index: CatalogIndex,
    query: str,
    *,
    limit: int = 10,
    eligible_only: bool = True,
    preferred_categories: list[str] | None = None,
    excluded_terms: list[str] | None = None,
    constraints: list[str] | None = None,
) -> list[CatalogMatch]:
    query = query.strip()
    if not query or not index.records:
        return []
    preferred_categories = preferred_categories or []
    excluded_terms = excluded_terms or []
    constraints = constraints or []
    max_duration = max_duration_from_constraints(constraints)
    query_vector = index.vectorizer.transform([query])
    scores = cosine_similarity(query_vector, index.matrix).ravel()
    matches: list[CatalogMatch] = []
    for record, score in zip(index.records, scores, strict=True):
        if eligible_only and not record.eligible_for_recommendation:
            continue
        if is_excluded(record, excluded_terms):
            continue
        if max_duration is not None and record.duration_minutes is not None and record.duration_minutes > max_duration:
            continue
        total_score = float(score) + category_boost(record, preferred_categories)
        if "prefer_short" in constraints and record.duration_minutes is not None:
            total_score += max(0.0, (30 - record.duration_minutes) / 100)
        if total_score <= 0:
            continue
        facts = [record.name, ", ".join(record.categories)]
        if record.duration:
            facts.append(record.duration)
        matches.append(
            CatalogMatch(
                assessment=record,
                score=total_score,
                matched_fields=["name", "categories", "description", "job_levels", "languages"],
                rationale_facts=[fact for fact in facts if fact],
                warnings=[] if record.eligible_for_recommendation else ["ineligible_for_recommendation"],
            )
        )
    matches.sort(key=lambda match: (-match.score, match.assessment.name.lower()))
    return matches[:limit]


def render_rerank_candidate(match: CatalogMatch) -> str:
    record = match.assessment
    return (
        f"entity_id={record.entity_id}; name={record.name}; score={match.score:.4f}; "
        f"test_type={record.test_type}; categories={', '.join(record.categories) or 'not specified'}; "
        f"job_levels={', '.join(record.job_levels) or 'not specified'}; "
        f"description={record.description or 'not specified'}"
    )


def rerank_catalog_with_llm_result(
    matches: list[CatalogMatch],
    goal: UserGoalProfile,
    llm_client: LLMClient,
    *,
    limit: int | None = None,
) -> RerankResult:
    if not matches or not llm_client.enabled:
        status = "no_candidates" if not matches else "llm_disabled"
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status=status)

    prompt = build_rerank_prompt(
        summarize_user_goal(goal),
        "\n".join(render_rerank_candidate(match) for match in matches),
    )
    llm_result = llm_client.complete_json(prompt)
    if llm_result.payload is None:
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status=llm_result.reason)

    entity_ids = llm_result.payload.get("ordered_entity_ids")
    if not isinstance(entity_ids, list):
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status="llm_missing_ordered_entity_ids")

    ordered_ids = [str(entity_id).strip() for entity_id in entity_ids if str(entity_id).strip()]
    if not ordered_ids:
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status="llm_empty_ordered_entity_ids")

    by_entity_id = {match.assessment.entity_id: match for match in matches}
    by_name = {normalize_name(match.assessment.name): match for match in matches}
    ordered_matches: list[CatalogMatch] = []
    seen: set[str] = set()

    for entity_id in ordered_ids:
        match = by_entity_id.get(entity_id) or by_name.get(normalize_name(entity_id))
        if match is None or match.assessment.entity_id in seen:
            continue
        ordered_matches.append(match)
        seen.add(match.assessment.entity_id)

    ordered_matches.extend(match for match in matches if match.assessment.entity_id not in seen)
    result_matches = ordered_matches[:limit] if limit is not None else ordered_matches
    return RerankResult(matches=result_matches, llm_status=llm_result.reason)


def rerank_catalog_with_llm(
    matches: list[CatalogMatch],
    goal: UserGoalProfile,
    llm_client: LLMClient,
    *,
    limit: int | None = None,
) -> list[CatalogMatch]:
    return rerank_catalog_with_llm_result(matches, goal, llm_client, limit=limit).matches
