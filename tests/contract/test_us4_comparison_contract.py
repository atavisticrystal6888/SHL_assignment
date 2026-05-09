from fastapi.testclient import TestClient

from app.main import app


def test_comparison_response_has_exact_contract_shape_without_recommendations():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "What is the difference between OPQ and GSA?"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
    assert "Occupational Personality Questionnaire OPQ32r" in body["reply"]
    assert "Global Skills Assessment" in body["reply"]
