"""Build retrieval queries from extracted user goals."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.conversation.extractor import UserGoalProfile
from app.retrieval.index import normalize_retrieval_text


@dataclass(frozen=True)
class RetrievalQuery:
    query_text: str
    required_terms: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    job_level_signals: list[str] = field(default_factory=list)
    language_signals: list[str] = field(default_factory=list)
    locale_signal: str | None = None
    constraints: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)


ROLE_SIGNAL_STOPWORDS = {"a", "an", "and", "for", "level", "mid", "of", "role", "roles", "senior", "the"}


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def role_signal_terms(role_titles: list[str]) -> list[str]:
    terms: list[str] = []
    for role_title in role_titles:
        normalized_role = normalize_retrieval_text(role_title)
        if normalized_role:
            terms.append(normalized_role)
        for token in re.findall(r"[a-z0-9]+", normalized_role):
            if len(token) > 3 and token not in ROLE_SIGNAL_STOPWORDS:
                terms.append(token)
    return dedupe(terms)


def build_retrieval_query(goal: UserGoalProfile) -> RetrievalQuery:
    conversation_context = "" if goal.latest_intent == "refine" else goal.conversation_text
    parts = [
        goal.latest_user_text,
        " ".join(goal.role_titles),
        " ".join(goal.skills),
        " ".join(goal.languages),
        goal.locale or "",
        goal.seniority or "",
        " ".join(goal.assessment_focus),
        " ".join(goal.constraints),
        conversation_context,
    ]
    query_text = normalize_retrieval_text(" ".join(part for part in parts if part).strip())
    required_terms = dedupe(goal.skills + role_signal_terms(goal.role_titles) + goal.languages)
    if goal.locale:
        required_terms.append(goal.locale)
    return RetrievalQuery(
        query_text=query_text,
        required_terms=dedupe(required_terms),
        preferred_categories=goal.assessment_focus,
        job_level_signals=[goal.seniority] if goal.seniority else [],
        language_signals=goal.languages,
        locale_signal=goal.locale,
        constraints=goal.constraints,
        excluded_terms=goal.excluded_terms,
    )
