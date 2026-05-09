from fastapi.testclient import TestClient

from app.main import app


def test_role_without_seniority_or_focus_asks_targeted_followup():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "I am hiring a Java developer"}]})

    body = response.json()
    reply = body["reply"].lower()
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
    assert "seniority" in reply or "level" in reply or "experience" in reply
    assert "focus" in reply or "skills" in reply or "assessment" in reply


def test_declined_preference_does_not_repeat_same_question():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "I am hiring a Java developer"},
                {"role": "assistant", "content": "What seniority and assessment focus should I use?"},
                {"role": "user", "content": "No preference on seniority, just assess Java skills."},
            ]
        },
    )

    body = response.json()
    assert "seniority" not in body["reply"].lower() or "no preference" in body["reply"].lower()
