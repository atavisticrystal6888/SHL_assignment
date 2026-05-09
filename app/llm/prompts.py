"""Grounded prompt templates for optional LLM assistance."""

from __future__ import annotations

from app.api.schemas import ConversationMessage

CATALOG_GROUNDING_RULES = """
Use only supplied catalog facts. Do not invent product names, URLs, durations,
languages, test types, availability, or compliance interpretations.
""".strip()

JSON_ONLY_RULES = """
Return valid JSON only. Do not wrap the JSON in markdown code fences.
Use empty arrays or null when the conversation does not support a field.
""".strip()


def format_conversation(messages: list[ConversationMessage]) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def build_grounded_reply_prompt(user_goal: str, catalog_context: str) -> str:
    return (
        f"{CATALOG_GROUNDING_RULES}\n\n"
        f"User goal:\n{user_goal.strip()}\n\n"
        f"Catalog context:\n{catalog_context.strip()}\n\n"
        "Return concise wording only; application code controls JSON shape."
    )


def build_intent_extraction_prompt(messages: list[ConversationMessage], current_summary: str) -> str:
    return (
        f"{CATALOG_GROUNDING_RULES}\n\n"
        f"{JSON_ONLY_RULES}\n\n"
        "Extract only explicit or strongly implied hiring intent from the conversation. "
        "Return a JSON object with keys role_titles, skills, seniority, assessment_focus, constraints, comparison_targets, languages, and locale. "
        "assessment_focus values must be chosen from: skills, ability, personality, situational judgment, simulation.\n\n"
        f"Current extracted summary:\n{current_summary.strip()}\n\n"
        f"Conversation history:\n{format_conversation(messages)}"
    )


def build_rerank_prompt(user_goal: str, catalog_candidates: str) -> str:
    return (
        f"{CATALOG_GROUNDING_RULES}\n\n"
        f"{JSON_ONLY_RULES}\n\n"
        "Reorder the provided candidate assessments by relevance to the hiring need. "
        "Do not invent new candidates. Return a JSON object with key ordered_entity_ids containing the candidate entity_id values in best-first order.\n\n"
        f"User goal:\n{user_goal.strip()}\n\n"
        f"Catalog candidates:\n{catalog_candidates.strip()}"
    )
