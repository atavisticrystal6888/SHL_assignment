from fastapi.testclient import TestClient

from app.main import app


def test_latest_correction_overrides_earlier_skill_probe():
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
                    "content": "Here is a shortlist with Java assessments.",
                },
                {
                    "role": "user",
                    "content": "Correction: this is a senior Python developer, not Java. Update the shortlist.",
                },
            ]
        },
    )

    body = response.json()
    names = [item["name"].lower() for item in body["recommendations"]]
    assert names
    assert any("python" in name for name in names)
    assert all("java" not in name for name in names)
    assert "updated" in body["reply"].lower()
