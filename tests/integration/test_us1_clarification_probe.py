from fastapi.testclient import TestClient

from app.main import app


def test_no_turn_one_recommendation_for_vague_input_probe():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "Need assessment recommendations"}]})

    body = response.json()
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
    assert "?" in body["reply"]
