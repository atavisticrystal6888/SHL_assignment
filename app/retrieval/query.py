"""Build retrieval queries from extracted user goals."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.conversation.extractor import UserGoalProfile


@dataclass(frozen=True)
class RetrievalQuery:
    query_text: str
    required_terms: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    job_level_signals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)


def build_retrieval_query(goal: UserGoalProfile) -> RetrievalQuery:
    parts = [
        goal.conversation_text,
        " ".join(goal.role_titles),
        " ".join(goal.skills),
        goal.seniority or "",
        " ".join(goal.assessment_focus),
        " ".join(goal.constraints),
    ]
    query_text = " ".join(part for part in parts if part).strip()
    return RetrievalQuery(
        query_text=query_text,
        required_terms=goal.skills,
        preferred_categories=goal.assessment_focus,
        job_level_signals=[goal.seniority] if goal.seniority else [],
        constraints=goal.constraints,
        excluded_terms=goal.excluded_terms,
    )
