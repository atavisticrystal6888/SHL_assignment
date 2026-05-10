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
    seed_assessment_names: list[str] = field(default_factory=list)
    job_level_signals: list[str] = field(default_factory=list)
    language_signals: list[str] = field(default_factory=list)
    locale_signal: str | None = None
    constraints: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)


ROLE_SIGNAL_STOPWORDS = {"a", "an", "and", "for", "level", "mid", "of", "role", "roles", "senior", "the"}
LEADERSHIP_HINTS = {"cxo", "director", "executive", "leader", "leadership"}
GRADUATE_HINTS = {"graduate", "trainee", "intern", "campus"}
SALES_HINTS = {"sales", "account executive", "business development"}
SAFETY_HINTS = {"safety", "dependability", "reliability", "cutting corners", "hazard"}
CONTACT_CENTER_HINTS = {"contact center", "contact centre", "customer service", "inbound calls", "phone simulation"}
HEALTHCARE_ADMIN_HINTS = {"healthcare admin", "patient records", "medical admin", "hipaa", "bilingual"}
AUDIT_DEVELOPMENT_HINTS = {"talent audit", "re-skill", "reskill", "restructuring", "development", "audit stack"}
RUST_INFRA_HINTS = {"rust", "networking", "infrastructure", "linux", "systems"}
INDUSTRIAL_HINTS = {"industrial", "manufacturing", "chemical", "plant operator", "plant operators", "facility"}
TECHNICAL_VERIFY_G_HINTS = {"architecture", "architectural", "cognitive", "high performance", "high-performance", "infrastructure", "microservice", "microservices"}
TECHNICAL_VERIFY_G_SKILLS = {"AWS", "Angular", "Docker", "Java", "JavaScript", "Linux", "Networking", "Python", "REST", "Rust", "SQL", "Spring"}
CUSTOMER_SERVICE_SEED_NAMES = [
    "Contact Center Call Simulation (New)",
    "Customer Service Phone Simulation",
    "Entry Level Customer Serv-Retail & Contact Center",
]
HEALTHCARE_ADMIN_SEED_NAMES = [
    "HIPAA (Security)",
    "Medical Terminology (New)",
    "Microsoft Word 365 - Essentials (New)",
    "Dependability and Safety Instrument (DSI)",
]
SALES_AUDIT_SEED_NAMES = [
    "Global Skills Assessment",
    "Global Skills Development Report",
    "OPQ MQ Sales Report",
    "Sales Transformation 2.0 - Individual Contributor",
]
SAFETY_SEED_NAMES = [
    "Dependability and Safety Instrument (DSI)",
    "Workplace Health and Safety (New)",
]
RUST_INFRA_SEED_NAMES = [
    "Smart Interview Live Coding",
    "Linux Programming (General)",
    "Networking and Implementation (New)",
]
SKILL_ASSESSMENT_SEEDS = {
    "Angular": ["Angular 6 (New)"],
    "AWS": ["Amazon Web Services (AWS) Development (New)"],
    "Docker": ["Docker (New)"],
    "Financial Accounting": ["Financial Accounting (New)"],
    "HIPAA": ["HIPAA (Security)"],
    "Linux": ["Linux Programming (General)"],
    "Medical Terminology": ["Medical Terminology (New)"],
    "Networking": ["Networking and Implementation (New)"],
    "Numerical Reasoning": ["SHL Verify Interactive – Numerical Reasoning"],
    "REST": ["RESTful Web Services (New)"],
    "Spring": ["Spring (New)"],
    "SQL": ["SQL (New)"],
    "Statistics": ["Basic Statistics (New)"],
}


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


def build_seed_assessment_names(goal: UserGoalProfile) -> list[str]:
    role_context = normalize_retrieval_text(
        " ".join(goal.role_titles + goal.skills + [goal.latest_user_text, goal.conversation_text])
    )
    excluded_terms = {term.lower() for term in goal.excluded_terms}
    focus = set(goal.assessment_focus)
    seeds: list[str] = []
    technical_skills = TECHNICAL_VERIFY_G_SKILLS.intersection(goal.skills)

    if "opq" not in excluded_terms and goal.role_titles and not any(hint in role_context for hint in SAFETY_HINTS):
        seeds.append("Occupational Personality Questionnaire OPQ32r")

    if technical_skills and (
        "ability" in focus
        or goal.seniority in {"senior", "manager", "director", "executive"}
        or any("senior" in normalize_retrieval_text(role) for role in goal.role_titles)
        or any(hint in role_context for hint in TECHNICAL_VERIFY_G_HINTS)
    ):
        seeds.append("SHL Verify Interactive G+")

    if any(hint in role_context for hint in LEADERSHIP_HINTS):
        seeds.append("OPQ Leadership Report")
        if any(term in role_context for term in {"selection", "benchmark"}):
            seeds.append("OPQ Universal Competency Report 2.0")

    if any(hint in role_context for hint in GRADUATE_HINTS):
        if "ability" in focus or not focus:
            seeds.append("SHL Verify Interactive G+")
        if "situational judgment" in focus or "full battery" in role_context or not focus:
            seeds.append("Graduate Scenarios")

    if any(hint in role_context for hint in SALES_HINTS) and "opq" not in excluded_terms:
        seeds.append("OPQ MQ Sales Report")

    if any(hint in role_context for hint in SAFETY_HINTS):
        seeds.extend(SAFETY_SEED_NAMES)
        if any(hint in role_context for hint in INDUSTRIAL_HINTS):
            seeds.append("Manufac. & Indust. - Safety & Dependability 8.0")

    for skill, assessment_names in SKILL_ASSESSMENT_SEEDS.items():
        if skill in goal.skills:
            seeds.extend(assessment_names)

    if "Java" in goal.skills:
        if goal.seniority in {"senior", "manager", "director", "executive"} or any(
            hint in role_context for hint in {"backend", "full stack", "full-stack", "microservice", "architecture", "design"}
        ):
            seeds.append("Core Java (Advanced Level) (New)")
        else:
            seeds.append("Java 8 (New)")

    if any(hint in role_context for hint in CONTACT_CENTER_HINTS):
        seeds.extend(CUSTOMER_SERVICE_SEED_NAMES)
        svar_by_locale = {
            "US": "SVAR Spoken English (US) (New)",
            "UK": "SVAR - Spoken English (U.K.)",
            "Australian": "SVAR - Spoken English (AUS)",
            "Indian": "SVAR - Spoken English (Indian Accent) (New)",
        }
        if goal.locale and "English" in goal.languages and goal.locale in svar_by_locale:
            seeds.append(svar_by_locale[goal.locale])

    if any(hint in role_context for hint in HEALTHCARE_ADMIN_HINTS):
        seeds.extend(HEALTHCARE_ADMIN_SEED_NAMES)

    if "simulation" in focus:
        if "Excel" in goal.skills:
            if "prefer_short" in goal.constraints:
                seeds.append("Microsoft Excel 365 - Essentials (New)")
            else:
                seeds.append("Microsoft Excel 365 (New)")
        if "Word" in goal.skills:
            if "prefer_short" in goal.constraints:
                seeds.append("Microsoft Word 365 - Essentials (New)")
            else:
                seeds.append("Microsoft Word 365 (New)")

    if any(hint in role_context for hint in SALES_HINTS) and any(hint in role_context for hint in AUDIT_DEVELOPMENT_HINTS):
        seeds.extend(SALES_AUDIT_SEED_NAMES)

    if "Rust" in goal.skills and any(hint in role_context for hint in RUST_INFRA_HINTS):
        seeds.extend(RUST_INFRA_SEED_NAMES)

    if any(term in role_context for term in {"financial analyst", "finance knowledge", "numerical reasoning"}):
        seeds.extend(["SHL Verify Interactive – Numerical Reasoning", "Financial Accounting (New)", "Basic Statistics (New)"])

    return dedupe(seeds)


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
    required_terms = dedupe(goal.skills + goal.languages)
    if not goal.skills:
        required_terms = dedupe(required_terms + role_signal_terms(goal.role_titles))
    if goal.locale:
        required_terms.append(goal.locale)
    return RetrievalQuery(
        query_text=query_text,
        required_terms=dedupe(required_terms),
        preferred_categories=goal.assessment_focus,
        seed_assessment_names=build_seed_assessment_names(goal),
        job_level_signals=[goal.seniority] if goal.seniority else [],
        language_signals=goal.languages,
        locale_signal=goal.locale,
        constraints=goal.constraints,
        excluded_terms=goal.excluded_terms,
    )
