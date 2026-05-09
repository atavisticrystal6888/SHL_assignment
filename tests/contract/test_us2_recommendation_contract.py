from fastapi.testclient import TestClient

from app.main import app


def test_committed_shortlist_has_exact_contract_shape():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a mid-level Java developer to assess technical skills. What SHL assessments should I use?",
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert 1 <= len(body["recommendations"]) <= 10
    for recommendation in body["recommendations"]:
        assert set(recommendation.keys()) == {"name", "url", "test_type"}
        assert recommendation["url"].startswith("https://www.shl.com/products/product-catalog/view/")
        assert recommendation["name"]
        assert recommendation["test_type"]
