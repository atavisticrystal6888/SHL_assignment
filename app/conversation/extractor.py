"""Stateless user-goal extraction from submitted chat history."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.api.schemas import ConversationMessage
from app.llm.client import LLMClient
from app.llm.prompts import build_intent_extraction_prompt

SKILL_TERMS = [
    "Java",
    "Python",
    "JavaScript",
    "Rust",
    "Linux",
    "Networking",
    "SQL",
    "Sales",
    "Leadership",
    "Angular",
    "AWS",
    "Customer Service",
    "Docker",
    "Excel",
    "HIPAA",
    "Medical Terminology",
    "REST",
    "Spring",
    "Word",
]
EXCLUSION_TERMS = {
    "Java": ("java",),
    "Python": ("python",),
    "JavaScript": ("javascript",),
    "Rust": ("rust",),
    "Linux": ("linux",),
    "Networking": ("networking",),
    "SQL": ("sql",),
    "OPQ": ("opq", "occupational personality questionnaire"),
}
REFINEMENT_TERMS = (
    "actually",
    "add",
    "drop",
    "remove",
    "exclude",
    "replace",
    "instead",
    "correction",
    "update",
)
CONFIRMATION_TERMS = (
    "confirmed",
    "confirm",
    "final list",
    "final shortlist",
    "keep as-is",
    "keep the shortlist",
    "keep verify",
    "locking it in",
    "lock it in",
    "perfect",
    "that covers it",
    "that works",
    "that's good",
    "that's what we need",
    "understood",
)
COMPARISON_TERMS = (
    "compare",
    "comparison",
    "difference",
    "different from",
    "different between",
    " vs ",
    " versus ",
    "which is better",
)
KNOWN_COMPARISON_REFERENCES = [
    ("OPQ report", ("opq report", "opq reports")),
    ("OPQ MQ Sales Report", ("opq mq sales report",)),
    (
        "Occupational Personality Questionnaire OPQ32r",
        ("occupational personality questionnaire opq32r", "occupational personality questionnaire", "opq32r", "opq"),
    ),
    ("Global Skills Development Report", ("global skills development report",)),
    ("Global Skills Assessment", ("global skills assessment", "gsa")),
    (
        "SHL Verify Interactive G+",
        ("shl verify interactive g+", "verify interactive g+", "verify g+"),
    ),
    ("Dependability and Safety Instrument (DSI)", ("dependability and safety instrument", "dsi")),
]
SENIORITY_TERMS = {
    "entry": "entry-level",
    "graduate": "graduate",
    "junior": "junior",
    "mid": "mid-level",
    "senior": "senior",
    "manager": "manager",
    "director": "director",
    "executive": "executive",
    "cxo": "executive",
}
FOCUS_TERMS = {
    "skill": "skills",
    "knowledge": "skills",
    "coding": "skills",
    "cognitive": "ability",
    "ability": "ability",
    "aptitude": "ability",
    "personality": "personality",
    "behavior": "personality",
    "situational": "situational judgment",
    "judgement": "situational judgment",
    "judgment": "situational judgment",
    "simulation": "simulation",
}
CANONICAL_FOCUS_VALUES = {"skills", "ability", "personality", "situational judgment", "simulation"}
CANONICAL_SENIORITY_VALUES = {
    "entry-level",
    "graduate",
    "junior",
    "mid-level",
    "senior",
    "manager",
    "director",
    "executive",
    "experience specified",
    "no preference",
}
ROLE_STOPWORDS = {"assessment", "assessments", "solution", "solutions", "stack", "battery"}
SKILLS_FOCUS_HINTS = (
    "assess technical",
    "day-one priorities",
    "daily",
    "excel",
    "hipaa",
    "knowledge test",
    "knowledge tests",
    "medical terminology",
    "priorities",
    "priority",
    "re-skill",
    "reskill",
    "screen",
    "screening",
    "technical skills",
    "word",
)
PERSONALITY_FOCUS_HINTS = (
    "audit",
    "benchmark",
    "behavior",
    "behaviour",
    "compliance",
    "dependability",
    "fit",
    "never cutting corners",
    "personality",
    "reliability",
    "safety",
)
SIMULATION_FOCUS_HINTS = (
    "call simulation",
    "inbound calls",
    "simulation",
    "simulations",
    "spoken english",
    "spoken language",
    "volume screening",
)


@dataclass(frozen=True)
class UserGoalProfile:
    latest_user_text: str = ""
    conversation_text: str = ""
    role_titles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    seniority: str | None = None
    assessment_focus: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)
    comparison_targets: list[str] = field(default_factory=list)
    has_prior_recommendation: bool = False
    missing_decision_factors: list[str] = field(default_factory=list)
    latest_intent: str = "clarify"


@dataclass(frozen=True)
class GoalExtractionResult:
    goal: UserGoalProfile
    llm_status: str


def latest_user_message(messages: list[ConversationMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def user_text(messages: list[ConversationMessage]) -> str:
    return "\n".join(message.content for message in messages if message.role == "user")


def dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = " ".join(item.split())
        if cleaned:
            normalized.append(cleaned)
    return dedupe(normalized)


def normalize_focus_hints(value: Any) -> list[str]:
    hints = normalize_string_list(value)
    normalized: list[str] = []
    for hint in hints:
        lowered = hint.lower()
        if lowered in CANONICAL_FOCUS_VALUES:
            normalized.append(lowered)
            continue
        mapped = FOCUS_TERMS.get(lowered)
        if mapped:
            normalized.append(mapped)
    return dedupe(normalized)


def normalize_seniority_hint(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = " ".join(value.split()).lower()
    if not candidate:
        return None
    if candidate in CANONICAL_SENIORITY_VALUES:
        return candidate
    return SENIORITY_TERMS.get(candidate, value.strip())


def has_confirmation_intent(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return any(term in lowered for term in CONFIRMATION_TERMS)


def text_contains(text: str, term: str) -> bool:
    pattern = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!\w){pattern}(?!\w)", text, flags=re.IGNORECASE) is not None


def compute_missing_factors(
    role_titles: list[str],
    seniority: str | None,
    assessment_focus: list[str],
    *,
    skills: list[str] | None = None,
    has_prior_recommendation: bool = False,
    latest_text: str = "",
) -> list[str]:
    if has_prior_recommendation and has_confirmation_intent(latest_text):
        return []
    if role_titles and assessment_focus:
        return []

    missing: list[str] = []
    if not role_titles:
        missing.append("role")
    if seniority is None:
        missing.append("seniority")
    if not assessment_focus:
        missing.append("assessment_focus")
    return missing


def determine_latest_intent(
    latest_text: str,
    *,
    comparison_targets: list[str],
    has_prior_recommendation: bool,
    missing_decision_factors: list[str],
) -> str:
    if comparison_targets or has_comparison_intent(latest_text):
        return "compare"
    if has_refinement_intent(latest_text) and has_prior_recommendation and not missing_decision_factors:
        return "refine"
    if has_confirmation_intent(latest_text) and has_prior_recommendation and not missing_decision_factors:
        return "recommend"
    return "clarify" if missing_decision_factors else "recommend"


def summarize_user_goal(goal: UserGoalProfile) -> str:
    lines = [f"Latest user request: {goal.latest_user_text}"]
    if goal.conversation_text:
        lines.append(f"Conversation context: {goal.conversation_text}")
    if goal.role_titles:
        lines.append(f"Role titles: {', '.join(goal.role_titles)}")
    if goal.skills:
        lines.append(f"Skills: {', '.join(goal.skills)}")
    if goal.seniority:
        lines.append(f"Seniority: {goal.seniority}")
    if goal.assessment_focus:
        lines.append(f"Assessment focus: {', '.join(goal.assessment_focus)}")
    if goal.constraints:
        lines.append(f"Constraints: {', '.join(goal.constraints)}")
    if goal.excluded_terms:
        lines.append(f"Excluded terms: {', '.join(goal.excluded_terms)}")
    if goal.comparison_targets:
        lines.append(f"Comparison targets: {', '.join(goal.comparison_targets)}")
    if goal.missing_decision_factors:
        lines.append(f"Missing decision factors: {', '.join(goal.missing_decision_factors)}")
    return "\n".join(lines)


def merge_goal_with_llm_hints(
    goal: UserGoalProfile,
    payload: dict[str, Any],
    *,
    prior_recommendation: bool,
) -> UserGoalProfile:
    role_titles = dedupe(goal.role_titles + normalize_string_list(payload.get("role_titles")))
    skills = dedupe(goal.skills + normalize_string_list(payload.get("skills")))
    excluded_lookup = {term.lower() for term in goal.excluded_terms}
    skills = [skill for skill in skills if skill.lower() not in excluded_lookup]
    seniority = goal.seniority or normalize_seniority_hint(payload.get("seniority"))
    assessment_focus = dedupe(goal.assessment_focus + normalize_focus_hints(payload.get("assessment_focus")))
    constraints = dedupe(goal.constraints + normalize_string_list(payload.get("constraints")))
    comparison_targets = dedupe(goal.comparison_targets + normalize_string_list(payload.get("comparison_targets")))
    missing = compute_missing_factors(
        role_titles,
        seniority,
        assessment_focus,
        skills=skills,
        has_prior_recommendation=prior_recommendation,
        latest_text=goal.latest_user_text,
    )
    latest_intent = determine_latest_intent(
        goal.latest_user_text,
        comparison_targets=comparison_targets,
        has_prior_recommendation=prior_recommendation,
        missing_decision_factors=missing,
    )
    return UserGoalProfile(
        latest_user_text=goal.latest_user_text,
        conversation_text=goal.conversation_text,
        role_titles=role_titles,
        skills=skills,
        seniority=seniority,
        assessment_focus=assessment_focus,
        constraints=constraints,
        corrections=goal.corrections,
        excluded_terms=goal.excluded_terms,
        comparison_targets=comparison_targets,
        has_prior_recommendation=goal.has_prior_recommendation,
        missing_decision_factors=missing,
        latest_intent=latest_intent,
    )


def _clean_role_title(value: str) -> str:
    value = re.sub(r"^\d+\+?\s+", "", value)
    value = re.sub(r"\bpeople\s+with\b.*$", "", value, flags=re.IGNORECASE)
    value = re.split(r"\b(?:with|who|that|and|for|to)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
    value = re.sub(r"\bpositions?\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bscheme\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,-—")


def extract_role_titles(text: str) -> list[str]:
    roles: list[str] = []
    roles.extend(re.findall(r'"([^"\n]+?)\s*[—-]\s*[^"\n]+"', text))

    patterns = [
        r"hiring\s+(?:a|an|for\s+a|for\s+an)?\s*([^.,;?]+)",
        r"need\s+(?:a|an)?\s*assessment\s+for\s+([^.,;?]+)",
        r"(?:this\s+is|it\s+is|it's|role\s+is|this\s+role\s+is)\s+(?:for\s+)?(?:a|an)?\s*([^.,;?]+)",
        r"pool\s+consists\s+of\s+([^.;?]+)",
        r"screen(?:ing)?\s+(?:\d+\s+)?([^.;?]+?)(?:\s+for\b|[.;?]|$)",
        r"re-?skill\s+our\s+([^.;?]+)",
        r"run\s+(?:a|an)\s+([^.;?]+?scheme)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            role = _clean_role_title(match.group(1))
            if role and role.lower() not in ROLE_STOPWORDS:
                roles.append(role[:1].upper() + role[1:])
    return dedupe(roles)


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    for term in SKILL_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
            found.append(term)
    return dedupe(found)


def has_refinement_intent(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in REFINEMENT_TERMS)


def has_comparison_intent(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(term in lowered for term in COMPARISON_TERMS)


def _spans_overlap(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < existing[1] and existing[0] < span[1] for existing in spans)


def _clean_comparison_target(value: str) -> str:
    value = value.strip(" .?!,;:\"'")
    value = re.sub(r"^(?:the|a|an)\s+", "", value, flags=re.IGNORECASE)
    value = re.split(
        r"\b(?:and include|include its|including its|for a|for an|for the|for|using|based on|from the catalog)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return value.strip(" .?!,;:\"'")


def extract_comparison_targets(text: str) -> list[str]:
    if not has_comparison_intent(text):
        return []
    targets: list[str] = []
    matched_spans: list[tuple[int, int]] = []
    aliases: list[tuple[str, str]] = []
    for canonical, canonical_aliases in KNOWN_COMPARISON_REFERENCES:
        aliases.extend((canonical, alias) for alias in canonical_aliases)
    for canonical, alias in sorted(aliases, key=lambda item: len(item[1]), reverse=True):
        for match in re.finditer(re.escape(alias), text, flags=re.IGNORECASE):
            span = match.span()
            if not _spans_overlap(span, matched_spans):
                targets.append(canonical)
                matched_spans.append(span)

    generic_patterns = [
        r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:[?.]|$)",
        r"\bcompare\s+(.+?)\s+(?:with|and|vs\.?|versus)\s+(.+?)(?:[?.]|$)",
        r"\bis\s+(.+?)\s+different\s+from\s+(.+?)(?:[?.]|$)",
        r"\b(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:[?.]|$)",
    ]
    for pattern in generic_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            targets.extend(_clean_comparison_target(group) for group in match.groups())
            break
    return dedupe(targets)


def has_prior_recommendation(messages: list[ConversationMessage]) -> bool:
    return any(
        message.role == "assistant"
        and any(term in message.content.lower() for term in ("shortlist", "recommend", "assessment"))
        for message in messages
    )


def extract_excluded_terms(text: str) -> list[str]:
    lowered = text.lower()
    exclusions: list[str] = []
    exclusion_verbs = r"drop|remove|exclude|without|not|no"
    for canonical, aliases in EXCLUSION_TERMS.items():
        for alias in aliases:
            escaped = re.escape(alias)
            if re.search(rf"\b(?:{exclusion_verbs})\s+(?:the\s+)?{escaped}\b", lowered):
                exclusions.append(canonical)
            elif re.search(rf"\b{escaped}\b.*\b(?:out|removed|excluded)\b", lowered):
                exclusions.append(canonical)
    return dedupe(exclusions)


def extract_constraints(text: str) -> list[str]:
    lowered = text.lower()
    constraints: list[str] = []
    duration_match = re.search(r"\b(?:under|less than|max(?:imum)?)\s+(\d+)\s*(?:minutes|mins?)\b", lowered)
    if duration_match:
        constraints.append(f"max_duration:{duration_match.group(1)}")
    if any(term in lowered for term in ("shorter", "quick", "fast", "brief")):
        constraints.append("prefer_short")
    return constraints


def extract_seniority(text: str) -> str | None:
    lowered = text.lower()
    if "no preference" in lowered and "seniority" in lowered:
        return "no preference"
    for term, value in SENIORITY_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            return value
    if re.search(r"\b\d+\s*(?:\+\s*)?(?:years|yrs)\b", lowered):
        return "experience specified"
    return None


def extract_focus(text: str) -> list[str]:
    lowered = text.lower()
    focus: list[str] = []
    for term, value in FOCUS_TERMS.items():
        if text_contains(lowered, term):
            focus.append(value)
    if any(text_contains(lowered, term) for term in SKILLS_FOCUS_HINTS):
        focus.append("skills")
    if any(text_contains(lowered, term) for term in PERSONALITY_FOCUS_HINTS):
        focus.append("personality")
    if any(text_contains(lowered, term) for term in SIMULATION_FOCUS_HINTS):
        focus.append("simulation")
    if extract_skills(text) and re.search(r"\bwhat\s+(?:shl\s+)?assessments?\b", lowered):
        focus.append("skills")
    if "assess" in lowered and "skills" in lowered:
        focus.append("skills")
    return dedupe(focus)


def extract_user_goal_result(
    messages: list[ConversationMessage],
    *,
    llm_client: LLMClient | None = None,
    enable_llm: bool = False,
) -> GoalExtractionResult:
    text = user_text(messages)
    latest_text = latest_user_message(messages)
    comparison_targets = extract_comparison_targets(latest_text)
    latest_is_refinement = has_refinement_intent(latest_text)
    prior_recommendation = has_prior_recommendation(messages)
    conversation_text = text
    if prior_recommendation and has_confirmation_intent(latest_text):
        conversation_text = "\n".join(message.content for message in messages)
    exclusions = extract_excluded_terms(latest_text)
    latest_roles = extract_role_titles(latest_text)
    roles = latest_roles if latest_is_refinement and latest_roles else extract_role_titles(text)
    skills = extract_skills(text)
    latest_skills = extract_skills(latest_text)
    if latest_is_refinement and latest_skills:
        skills.extend(latest_skills)
    excluded_lookup = {term.lower() for term in exclusions}
    skills = [skill for skill in dedupe(skills) if skill.lower() not in excluded_lookup]
    latest_seniority = extract_seniority(latest_text)
    seniority = latest_seniority if latest_is_refinement and latest_seniority else extract_seniority(text)
    focus = extract_focus(text)
    constraints = extract_constraints(text)
    missing = compute_missing_factors(
        roles,
        seniority,
        focus,
        skills=skills,
        has_prior_recommendation=prior_recommendation,
        latest_text=latest_text,
    )
    latest_intent = determine_latest_intent(
        latest_text,
        comparison_targets=comparison_targets,
        has_prior_recommendation=prior_recommendation,
        missing_decision_factors=missing,
    )
    goal = UserGoalProfile(
        latest_user_text=latest_text,
        conversation_text=conversation_text,
        role_titles=roles,
        skills=skills,
        seniority=seniority,
        assessment_focus=focus,
        constraints=constraints,
        corrections=exclusions,
        excluded_terms=exclusions,
        comparison_targets=comparison_targets,
        has_prior_recommendation=prior_recommendation,
        missing_decision_factors=missing,
        latest_intent=latest_intent,
    )
    if not enable_llm or llm_client is None or not llm_client.enabled:
        status = "disabled_by_config" if not enable_llm else "llm_disabled"
        return GoalExtractionResult(goal=goal, llm_status=status)
    llm_result = llm_client.complete_json(build_intent_extraction_prompt(messages, summarize_user_goal(goal)))
    if llm_result.payload is None:
        return GoalExtractionResult(goal=goal, llm_status=llm_result.reason)
    merged_goal = merge_goal_with_llm_hints(goal, llm_result.payload, prior_recommendation=prior_recommendation)
    return GoalExtractionResult(goal=merged_goal, llm_status=llm_result.reason)


def extract_user_goal(
    messages: list[ConversationMessage],
    *,
    llm_client: LLMClient | None = None,
    enable_llm: bool = False,
) -> UserGoalProfile:
    return extract_user_goal_result(
        messages,
        llm_client=llm_client,
        enable_llm=enable_llm,
    ).goal
