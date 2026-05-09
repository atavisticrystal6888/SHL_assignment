from fastapi.testclient import TestClient

from app.main import app


def post_message(text: str) -> dict:
    client = TestClient(app)
    return client.post("/chat", json={"messages": [{"role": "user", "content": text}]}).json()


def test_refuses_legal_advice_request():
    body = post_message("Can you give me legal advice about whether this assessment is compliant?")

    assert body["recommendations"] == []
    assert "legal" in body["reply"].lower()
    assert "shl" in body["reply"].lower()


def test_redirects_general_hiring_strategy_request():
    body = post_message("Give me general interview questions and hiring strategy for managers.")

    assert body["recommendations"] == []
    assert "shl" in body["reply"].lower()


def test_refuses_non_shl_product_recommendation():
    body = post_message("Recommend a non-SHL assessment like HackerRank instead.")

    assert body["recommendations"] == []
    assert "shl" in body["reply"].lower()


def test_refuses_job_description_authoring_request():
    body = post_message("Write a job description for a senior data engineer.")

    assert body["recommendations"] == []
    assert "shl" in body["reply"].lower()
    assert "job descriptions" in body["reply"].lower() or "hiring" in body["reply"].lower()
