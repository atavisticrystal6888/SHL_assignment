import httpx

from app.api.schemas import ConversationMessage
from app.conversation.extractor import extract_user_goal, extract_user_goal_result
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
        model="openai/gpt-oss-120b",
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
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    result = extract_user_goal_result(
        [ConversationMessage(role="user", content="Need something for backend APIs.")],
        llm_client=client,
        enable_llm=True,
    )

    assert result.llm_status == "llm_success"
    assert "Backend engineer" in result.goal.role_titles
