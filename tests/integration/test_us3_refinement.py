from fastapi.testclient import TestClient

from app.main import app


def test_adding_personality_tests_updates_shortlist_with_personality_signal():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a mid-level Java developer. Assess Java technical skills.",
                },
                {
                    "role": "assistant",
                    "content": "Here is a shortlist with Java technical assessments.",
                },
                {"role": "user", "content": "Actually add personality tests too."},
            ]
        },
    )

    body = response.json()
    assert body["recommendations"]
    assert any(item["test_type"] == "P" or "personality" in item["name"].lower() or "opq" in item["name"].lower() for item in body["recommendations"])
    assert "updated" in body["reply"].lower()


def test_drop_opq_removes_opq_from_revised_shortlist():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a senior sales manager. Assess sales leadership and personality fit.",
                },
                {
                    "role": "assistant",
                    "content": "Shortlist includes Occupational Personality Questionnaire OPQ32r and OPQ MQ Sales Report.",
                },
                {"role": "user", "content": "Drop OPQ and keep sales personality alternatives."},
            ]
        },
    )

    body = response.json()
    assert body["recommendations"]
    assert all("opq" not in item["name"].lower() for item in body["recommendations"])
    assert "updated" in body["reply"].lower()


def test_role_pivot_replaces_previous_shortlist_context():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a mid-level Java developer. Assess Java technical skills.",
                },
                {
                    "role": "assistant",
                    "content": "Shortlist includes Core Java (Advanced Level) and Spring.",
                },
                {
                    "role": "user",
                    "content": "Actually switch to a senior sales manager role and assess sales leadership and personality fit instead.",
                },
            ]
        },
    )

    body = response.json()
    names = [item["name"].lower() for item in body["recommendations"]]

    assert body["recommendations"]
    assert any("sales" in name or "opq" in name for name in names)
    assert all("java" not in name and "spring" not in name and "sql" not in name for name in names)
    assert "updated" in body["reply"].lower()
