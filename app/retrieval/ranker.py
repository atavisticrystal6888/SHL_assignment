"""Deterministic catalog ranking."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.metrics.pairwise import cosine_similarity

from app.catalog.models import CatalogAssessment
from app.catalog.repository import ASSESSMENT_ALIASES, normalize_name
from app.conversation.extractor import UserGoalProfile, summarize_user_goal
from app.llm.client import LLMClient
from app.llm.prompts import build_rerank_prompt
from app.retrieval.index import CatalogIndex, normalize_retrieval_text

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


def matches_focus(record: CatalogAssessment, focus: str) -> bool:
    category = CATEGORY_BY_FOCUS.get(focus)
    if category and category in record.categories:
        return True
    if focus == "personality" and record.test_type == "P":
        return True
    return False


def required_terms_boost(record: CatalogAssessment, required_terms: list[str]) -> float:
    boost = 0.0
    name_haystack = normalize_name(record.name)
    content_haystack = normalize_name(" ".join([record.name, record.description, " ".join(record.categories)]))
    for term in required_terms:
        normalized_term = normalize_name(term)
        if not normalized_term:
            continue
        if normalized_term in name_haystack:
            boost += 1.1
        elif normalized_term in content_haystack:
            boost += 0.4
    return boost


def language_boost(record: CatalogAssessment, language_signals: list[str], locale_signal: str | None) -> float:
    boost = 0.0
    haystack = normalize_name(" ".join(record.languages + [record.name, record.description]))
    for language in language_signals:
        normalized_language = normalize_name(language)
        if normalized_language and normalized_language in haystack:
            boost += 0.4
    if locale_signal:
        locale_lookup = {
            "US": ["us", "usa", "american"],
            "UK": ["uk", "british"],
            "Australian": ["australia", "australian"],
            "Indian": ["india", "indian"],
            "Canada": ["canada", "canadian"],
        }
        if any(token in haystack for token in locale_lookup.get(locale_signal, [normalize_name(locale_signal)])):
            boost += 0.7
    return boost


def focus_penalty(record: CatalogAssessment, preferred_categories: list[str]) -> float:
    if not preferred_categories:
        return 0.0
    if any(matches_focus(record, focus) for focus in preferred_categories):
        return 0.0
    return -0.35 if len(preferred_categories) > 1 else -0.15


def job_level_boost(record: CatalogAssessment, job_level_signals: list[str]) -> float:
    if not job_level_signals:
        return 0.0
    haystack = normalize_name(" ".join(record.job_levels + [record.name, record.description]))
    return sum(0.4 for signal in job_level_signals if normalize_name(signal) and normalize_name(signal) in haystack)


def query_reference_boost(record: CatalogAssessment, query: str) -> float:
    normalized_query = normalize_name(query)
    if not normalized_query:
        return 0.0
    normalized_name = normalize_name(record.name)
    if normalized_name and normalized_name in normalized_query:
        return 2.2

    query_tokens = {token for token in normalized_query.split() if len(token) > 1}
    name_tokens = {token for token in normalized_name.split() if len(token) > 1}
    overlap = len(query_tokens & name_tokens)
    if overlap >= 3:
        return 1.4
    if overlap == 2:
        return 0.8
    if overlap == 1 and any(token in normalized_name for token in query_tokens if len(token) > 3):
        return 0.2
    return 0.0


def alias_reference_boost(record: CatalogAssessment, query: str) -> float:
    normalized_query = normalize_name(query)
    normalized_record_name = normalize_name(record.name)
    if not normalized_query or not normalized_record_name:
        return 0.0
    for alias, canonical_name in ASSESSMENT_ALIASES.items():
        if normalize_name(alias) in normalized_query and normalize_name(canonical_name) == normalized_record_name:
            return 3.0
    return 0.0


def select_focus_coverage(matches: list[CatalogMatch], preferred_categories: list[str], *, limit: int) -> list[CatalogMatch]:
    focuses = list(dict.fromkeys(focus for focus in preferred_categories if focus in CATEGORY_BY_FOCUS))
    if len(focuses) < 2:
        return matches[:limit]

    # Ensure proportional representation across focus areas.
    # Reserve at least 2 slots (or 1 if limit is small) per focus, then fill with best scores.
    slots_per_focus = max(1, limit // len(focuses))
    selected: list[CatalogMatch] = []
    seen: set[str] = set()
    for focus in focuses:
        count = 0
        for match in matches:
            if match.assessment.entity_id in seen:
                continue
            if matches_focus(match.assessment, focus):
                selected.append(match)
                seen.add(match.assessment.entity_id)
                count += 1
                if count >= slots_per_focus:
                    break

    for match in matches:
        if match.assessment.entity_id in seen:
            continue
        selected.append(match)
        seen.add(match.assessment.entity_id)
        if len(selected) >= limit:
            break
    return selected[:limit]


def rank_catalog(
    index: CatalogIndex,
    query: str,
    *,
    limit: int = 10,
    eligible_only: bool = True,
    preferred_categories: list[str] | None = None,
    required_terms: list[str] | None = None,
    job_level_signals: list[str] | None = None,
    language_signals: list[str] | None = None,
    locale_signal: str | None = None,
    excluded_terms: list[str] | None = None,
    constraints: list[str] | None = None,
) -> list[CatalogMatch]:
    query = normalize_retrieval_text(query.strip())
    if not query or not index.records:
        return []
    preferred_categories = preferred_categories or []
    required_terms = required_terms or []
    job_level_signals = job_level_signals or []
    language_signals = language_signals or []
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
        total_score = float(score)
        total_score += category_boost(record, preferred_categories)
        total_score += required_terms_boost(record, required_terms)
        total_score += job_level_boost(record, job_level_signals)
        total_score += language_boost(record, language_signals, locale_signal)
        total_score += focus_penalty(record, preferred_categories)
        total_score += query_reference_boost(record, query)
        total_score += alias_reference_boost(record, query)
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
    selected = select_focus_coverage(matches, preferred_categories, limit=limit)
    # Drop low-scoring padding: keep only results scoring at least 25% of the top score,
    # but only when a single focus is active. With multiple focuses the coverage selector
    # already ensures balance so the threshold would remove needed diversity.
    if selected and len(set(preferred_categories) & set(CATEGORY_BY_FOCUS.keys())) < 2:
        top_score = selected[0].score
        threshold = top_score * 0.25
        selected = [m for m in selected if m.score >= threshold]
    return selected


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
    llm_timeout_seconds: float | None = None,
) -> RerankResult:
    if not matches or not llm_client.enabled:
        status = "no_candidates" if not matches else "llm_disabled"
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status=status)
    if llm_timeout_seconds is not None and llm_timeout_seconds <= 0:
        result_matches = matches[:limit] if limit is not None else matches
        return RerankResult(matches=result_matches, llm_status="skipped_deadline")

    prompt = build_rerank_prompt(
        summarize_user_goal(goal),
        "\n".join(render_rerank_candidate(match) for match in matches),
    )
    llm_result = llm_client.complete_json(prompt, timeout_seconds=llm_timeout_seconds)
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
    llm_timeout_seconds: float | None = None,
) -> list[CatalogMatch]:
    return rerank_catalog_with_llm_result(
        matches,
        goal,
        llm_client,
        limit=limit,
        llm_timeout_seconds=llm_timeout_seconds,
    ).matches
