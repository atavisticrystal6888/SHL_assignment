from fastapi.testclient import TestClient

from app.main import app


def test_multi_turn_refinement_preserves_exact_contract_shape():
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
                    "content": "Here is a catalog-grounded SHL shortlist for the Java developer.",
                },
                {"role": "user", "content": "Actually add personality tests too."},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert "updated" in body["reply"].lower()
    assert 1 <= len(body["recommendations"]) <= 10
    for recommendation in body["recommendations"]:
        assert set(recommendation.keys()) == {"name", "url", "test_type"}
