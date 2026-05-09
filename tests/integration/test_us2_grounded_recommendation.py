from fastapi.testclient import TestClient

from app.main import app


def test_complete_java_developer_need_returns_catalog_backed_skill_assessment():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a mid-level Java developer who works with stakeholders. Assess Java technical skills.",
                }
            ]
        },
    )

    body = response.json()
    names = [item["name"].lower() for item in body["recommendations"]]
    assert body["recommendations"]
    assert any("java" in name for name in names)
    assert body["end_of_conversation"] is False
