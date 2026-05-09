from fastapi.testclient import TestClient

from app.main import app


def test_vague_request_returns_empty_recommendations_contract():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "I need an assessment"}]})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
    assert any(term in body["reply"].lower() for term in ["role", "skills", "seniority", "job"])


def test_malformed_input_returns_chat_response_contract():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": []})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
