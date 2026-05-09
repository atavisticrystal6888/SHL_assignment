from fastapi.testclient import TestClient

from app.main import app


def test_debug_header_opt_in_exposes_llm_status_headers_without_changing_body_shape():
    client = TestClient(app)

    response = client.post(
        "/chat",
        headers={"X-Debug-LLM": "1"},
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a mid-level Java developer who works with stakeholders. Assess Java technical skills.",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert set(response.json().keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert response.headers["X-LLM-Intent-Extraction"]
    assert response.headers["X-LLM-Reranking"]