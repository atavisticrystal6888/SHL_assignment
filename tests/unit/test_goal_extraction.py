import httpx

from app.api.schemas import ConversationMessage
from app.conversation.extractor import extract_comparison_targets, extract_user_goal, extract_user_goal_result
from app.llm.client import LLMClient


def test_extracts_role_and_missing_factors_from_partial_request():
    goal = extract_user_goal([ConversationMessage(role="user", content="I am hiring a Java developer")])

    assert "Java developer" in goal.role_titles
    assert "Java" in goal.skills
    assert "seniority" in goal.missing_decision_factors
    assert "assessment_focus" in goal.missing_decision_factors


def test_no_preference_removes_missing_seniority_question():
    goal = extract_user_goal(
        [
            ConversationMessage(role="user", content="I am hiring a Java developer"),
            ConversationMessage(role="assistant", content="What seniority should I use?"),
            ConversationMessage(role="user", content="No preference on seniority, just Java skills."),
        ]
    )

    assert "seniority" not in goal.missing_decision_factors
    assert "Java" in goal.skills


def test_llm_intent_hints_fill_missing_role_focus_and_seniority():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"role_titles": ["Backend engineer"], "skills": ["Python"], "seniority": "mid-level", "assessment_focus": ["skills"], "constraints": [], "comparison_targets": []}'
                        }
                    }
                ]
            },
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="llama-3.3-70b-versatile",
        transport=httpx.MockTransport(handler),
    )

    goal = extract_user_goal(
        [ConversationMessage(role="user", content="Need something for backend APIs and stakeholder conversations.")],
        llm_client=client,
        enable_llm=True,
    )

    assert "Backend engineer" in goal.role_titles
    assert goal.seniority == "mid-level"
    assert goal.assessment_focus == ["skills"]
    assert goal.missing_decision_factors == []
    assert goal.latest_intent == "recommend"


def test_goal_extraction_result_reports_llm_status():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"role_titles": ["Backend engineer"], "skills": [], "seniority": null, "assessment_focus": ["skills"], "constraints": [], "comparison_targets": []}'
                        }
                    }
                ]
            },
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="llama-3.3-70b-versatile",
        transport=httpx.MockTransport(handler),
    )

    result = extract_user_goal_result(
        [ConversationMessage(role="user", content="Need something for backend APIs.")],
        llm_client=client,
        enable_llm=True,
    )

    assert result.llm_status == "llm_success"
    assert "Backend engineer" in result.goal.role_titles


def test_executive_leadership_follow_up_becomes_actionable():
    goal = extract_user_goal(
        [
            ConversationMessage(role="user", content="We need a solution for senior leadership."),
            ConversationMessage(role="assistant", content="Who is this meant for?"),
            ConversationMessage(
                role="user",
                content="The pool consists of CXOs, director-level positions; people with more than 15 years of experience.",
            ),
            ConversationMessage(role="assistant", content="Is this for selection or development?"),
            ConversationMessage(role="user", content="Selection - comparing candidates against a leadership benchmark."),
        ]
    )

    assert any("CXOs" in role or "director-level" in role for role in goal.role_titles)
    assert "personality" in goal.assessment_focus
    assert goal.missing_decision_factors == []
    assert goal.latest_intent == "recommend"


def test_confirmation_after_prior_shortlist_keeps_context_actionable():
    goal = extract_user_goal(
        [
            ConversationMessage(role="user", content="Hiring graduate trainees for a full battery."),
            ConversationMessage(role="assistant", content="Here is a shortlist with Verify G+ and Graduate Scenarios."),
            ConversationMessage(role="user", content="Keep the shortlist as-is. Locking it in."),
        ]
    )

    assert goal.missing_decision_factors == []
    assert goal.latest_intent == "recommend"


def test_screening_prompt_extracts_role_and_skills_focus():
    goal = extract_user_goal(
        [
            ConversationMessage(
                role="user",
                content="I need to quickly screen admin assistants for Excel and Word daily.",
            )
        ]
    )

    assert "Admin assistants" in goal.role_titles
    assert "skills" in goal.assessment_focus


def test_comparison_targets_support_different_from_questions():
    targets = extract_comparison_targets(
        "Is the Contact Center Call Simulation different from the Customer Service Phone Simulation?"
    )

    assert targets == ["Contact Center Call Simulation", "Customer Service Phone Simulation"]


def test_refinement_intent_wins_over_confirmation_language():
    goal = extract_user_goal(
        [
            ConversationMessage(role="user", content="We run a graduate management trainee scheme."),
            ConversationMessage(role="assistant", content="Shortlist includes Verify G+, OPQ32r, and Graduate Scenarios."),
            ConversationMessage(role="user", content="Drop the OPQ. Final list: Verify G+ and Graduate Scenarios."),
        ]
    )

    assert "OPQ" in goal.excluded_terms
    assert goal.latest_intent == "refine"


def test_dependability_text_does_not_imply_ability_focus():
    goal = extract_user_goal(
        [
            ConversationMessage(
                role="user",
                content="We're hiring plant operators. Safety is top priority with reliability and dependability.",
            )
        ]
    )

    assert "personality" in goal.assessment_focus
    assert "ability" not in goal.assessment_focus
