"""Render schema-safe assistant replies."""

from __future__ import annotations

from app.api.schemas import ChatResponse
from app.catalog.models import CatalogAssessment
from app.catalog.repository import CatalogResolution
from app.conversation.extractor import UserGoalProfile, has_confirmation_intent, summarize_user_goal
from app.conversation.policy import AgentDecision
from app.llm.client import LLMClient
from app.llm.prompts import build_grounded_reply_prompt
from app.retrieval.ranker import CatalogMatch


def compact_list(values: list[str], *, limit: int = 4) -> str:
    if not values:
        return "not specified"
    shown = values[:limit]
    suffix = f" (+{len(values) - limit} more)" if len(values) > limit else ""
    return ", ".join(shown) + suffix


def first_sentence(value: str, *, limit: int = 220) -> str:
    text = " ".join(value.split())
    if not text:
        return "No catalog description is available."
    sentence = text.split(". ", maxsplit=1)[0].strip()
    if len(sentence) > limit:
        return sentence[: limit - 3].rstrip() + "..."
    return sentence


def render_catalog_facts(record: CatalogAssessment) -> str:
    categories = compact_list(record.categories)
    duration = record.duration or "not specified"
    job_levels = compact_list(record.job_levels)
    languages = compact_list(record.languages)
    return (
        f"{record.name}: test type {record.test_type}; categories: {categories}; "
        f"duration: {duration}; remote testing: {record.remote_testing}; adaptive/IRT: {record.adaptive_irt}; "
        f"job levels: {job_levels}; languages: {languages}. Catalog description: {first_sentence(record.description)}."
    )


def maybe_rewrite_reply(
    response: ChatResponse,
    goal: UserGoalProfile,
    llm_client: LLMClient,
    *,
    catalog_context: list[str] | None = None,
    timeout_seconds: float | None = None,
) -> ChatResponse:
    if not llm_client.enabled or (timeout_seconds is not None and timeout_seconds <= 0):
        return response

    prompt = build_grounded_reply_prompt(
        summarize_user_goal(goal),
        "\n".join(catalog_context or ["No additional catalog context."]),
    )
    result = llm_client.complete(prompt, response.reply, timeout_seconds=timeout_seconds)
    if result.text == response.reply:
        return response
    return response.model_copy(update={"reply": result.text})


def render_clarification(goal: UserGoalProfile, decision: AgentDecision) -> ChatResponse:
    missing = set(decision.missing_factors)
    if "role" in missing:
        reply = "What role or job profile should the SHL assessment support, and what skills or seniority matter most?"
    elif "language" in missing:
        reply = "What language should the SHL assessment support for the candidate interactions or spoken responses?"
    elif "locale" in missing:
        reply = "Which English variant should I target for the spoken-language screen: US, UK, Australian, or Indian?"
    elif {"seniority", "assessment_focus"}.issubset(missing):
        reply = "What seniority or experience level is this for, and should the assessment focus on skills, cognitive ability, personality, or situational judgment?"
    elif "seniority" in missing:
        reply = "What seniority or experience level should I target for this role?"
    elif "assessment_focus" in missing:
        reply = "Should the assessment focus on skills, cognitive ability, personality, situational judgment, or another SHL catalog area?"
    else:
        role = goal.role_titles[0] if goal.role_titles else "that role"
        reply = f"I can work with the context for {role}. Should I build a catalog-grounded shortlist from those details?"
    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)


def shortlist_anchor_text(matches: list[CatalogMatch], *, limit: int = 5) -> str:
    names = [match.assessment.name for match in matches[:limit]]
    return "; ".join(names) if names else "no matching assessments"


def recommendation_payload(matches: list[CatalogMatch]) -> list[dict[str, str]]:
    return [
        {
            "name": match.assessment.name,
            "url": match.assessment.url,
            "test_type": match.assessment.test_type,
        }
        for match in matches[:10]
    ]


def should_end_conversation(goal: UserGoalProfile) -> bool:
    return not goal.missing_decision_factors and has_confirmation_intent(goal.latest_user_text)


def render_recommendations(goal: UserGoalProfile, matches: list[CatalogMatch]) -> ChatResponse:
    role = goal.role_titles[0] if goal.role_titles else "the role"
    recommendations = recommendation_payload(matches)
    end = should_end_conversation(goal)
    reply = (
        f"Here is a catalog-grounded SHL shortlist for {role}, prioritized from the available catalog matches: "
        f"{shortlist_anchor_text(matches)}."
    )
    return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=end)


def render_refinement(goal: UserGoalProfile, matches: list[CatalogMatch]) -> ChatResponse:
    recommendations = recommendation_payload(matches)
    reply = (
        "Updated the SHL shortlist using the latest changes while keeping the remaining catalog-grounded context: "
        f"{shortlist_anchor_text(matches)}."
    )
    if goal.excluded_terms:
        reply += f" Removed: {', '.join(goal.excluded_terms)}."
    return ChatResponse(reply=reply, recommendations=recommendations, end_of_conversation=should_end_conversation(goal))


def render_comparison(
    goal: UserGoalProfile,
    resolutions: list[CatalogResolution],
    *,
    prior_matches: list[CatalogMatch] | None = None,
) -> ChatResponse:
    preserved_recommendations = recommendation_payload(prior_matches or [])
    if len(goal.comparison_targets) < 2:
        reply = "Which SHL catalog assessments should I compare? Please provide two assessment names or common aliases."
        return ChatResponse(reply=reply, recommendations=preserved_recommendations, end_of_conversation=False)

    ambiguous = [resolution for resolution in resolutions if resolution.status == "ambiguous"]
    if ambiguous:
        parts = []
        for resolution in ambiguous:
            candidates = ", ".join(record.name for record in resolution.matches[:5])
            parts.append(f"'{resolution.query}' could mean multiple catalog records: {candidates}")
        reply = "I found multiple SHL catalog matches. " + " ".join(parts) + " Which exact assessment should I compare?"
        return ChatResponse(reply=reply, recommendations=preserved_recommendations, end_of_conversation=False)

    not_found = [resolution.query for resolution in resolutions if resolution.status == "not_found"]
    resolved_records = [resolution.record for resolution in resolutions if resolution.record is not None]
    if not_found:
        found = ", ".join(record.name for record in resolved_records) if resolved_records else "no matching catalog assessment"
        missing = ", ".join(not_found)
        reply = f"I can compare only SHL catalog assessments. I found {found}, but could not find {missing} in the catalog."
        return ChatResponse(reply=reply, recommendations=preserved_recommendations, end_of_conversation=False)

    if len(resolved_records) < 2:
        reply = "I need two distinct SHL catalog assessments to compare. Which second assessment should I use?"
        return ChatResponse(reply=reply, recommendations=preserved_recommendations, end_of_conversation=False)

    facts = " ".join(render_catalog_facts(record) for record in resolved_records[:3])
    reply = f"Catalog-grounded comparison: {facts} These differences come from stored SHL catalog fields, not inferred product claims."
    return ChatResponse(reply=reply, recommendations=preserved_recommendations, end_of_conversation=False)


def render_refusal(decision: AgentDecision) -> ChatResponse:
    if decision.reason == "legal_advice":
        reply = "I can't provide legal advice. I can help select SHL assessments using catalog-backed product information."
    elif decision.reason == "general_hiring":
        reply = "I can help with SHL assessment selection, but not general hiring content such as job descriptions, hiring strategy, or interview-question generation."
    elif decision.reason == "non_shl":
        reply = "I can only recommend SHL catalog assessments, not non-SHL products."
    else:
        reply = "I can't follow instructions that bypass SHL catalog grounding. I can help select catalog-backed SHL assessments."
    return ChatResponse(reply=reply, recommendations=[], end_of_conversation=False)
