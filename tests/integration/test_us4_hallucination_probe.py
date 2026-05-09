from fastapi.testclient import TestClient

from app.main import app


def test_unknown_comparison_target_does_not_create_catalog_facts_or_recommendations():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Compare OPQ with Imaginary Quantum Assessment and include its catalog URL.",
                }
            ]
        },
    )

    body = response.json()
    reply = body["reply"].lower()
    assert body["recommendations"] == []
    assert "could not find" in reply or "catalog" in reply
    assert "imaginary-quantum" not in reply
    assert "https://www.shl.com/products/product-catalog/view/imaginary" not in reply
