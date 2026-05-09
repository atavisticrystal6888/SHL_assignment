"""Conversation decision policy."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.conversation.extractor import UserGoalProfile

LEGAL_TERMS = ("legal advice", "legally", "compliant", "compliance", "law", "regulation")
GENERAL_HIRING_TERMS = ("interview questions", "hiring strategy", "recruiting strategy", "candidate scoring")
NON_SHL_TERMS = ("non-shl", "non shl", "hackerrank", "codility", "testgorilla", "mercer")
PROMPT_INJECTION_TERMS = (
    "ignore previous",
    "ignore all previous",
    "ignore your rules",
    "hidden prompt",
    "hidden prompts",
    "reveal hidden",
    "system prompt",
    "invent",
)


@dataclass(frozen=True)
class AgentDecision:
    action: str
    reason: str
    missing_factors: list[str] = field(default_factory=list)
    recommendations_allowed: bool = False
    end_allowed: bool = False


def decide_next_action(goal: UserGoalProfile) -> AgentDecision:
    lowered = goal.latest_user_text.lower()
    if any(term in lowered for term in PROMPT_INJECTION_TERMS):
        return AgentDecision(action="refuse", reason="prompt_injection", recommendations_allowed=False, end_allowed=False)
    if any(term in lowered for term in LEGAL_TERMS):
        return AgentDecision(action="refuse", reason="legal_advice", recommendations_allowed=False, end_allowed=False)
    if any(term in lowered for term in GENERAL_HIRING_TERMS):
        return AgentDecision(action="refuse", reason="general_hiring", recommendations_allowed=False, end_allowed=False)
    if any(term in lowered for term in NON_SHL_TERMS):
        return AgentDecision(action="refuse", reason="non_shl", recommendations_allowed=False, end_allowed=False)
    if goal.latest_intent == "compare":
        return AgentDecision(
            action="compare",
            reason="comparison_requested",
            missing_factors=[],
            recommendations_allowed=False,
            end_allowed=False,
        )
    if goal.missing_decision_factors:
        return AgentDecision(
            action="clarify",
            reason="missing_decision_factors",
            missing_factors=goal.missing_decision_factors,
            recommendations_allowed=False,
            end_allowed=False,
        )
    if goal.latest_intent == "refine":
        return AgentDecision(
            action="refine",
            reason="user_updated_constraints",
            missing_factors=[],
            recommendations_allowed=True,
            end_allowed=False,
        )
    return AgentDecision(
        action="recommend",
        reason="sufficient_context",
        missing_factors=[],
        recommendations_allowed=True,
        end_allowed=False,
    )
