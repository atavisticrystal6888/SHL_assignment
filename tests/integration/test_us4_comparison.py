from fastapi.testclient import TestClient

from app.main import app


def post_message(text: str) -> dict:
    client = TestClient(app)
    return client.post("/chat", json={"messages": [{"role": "user", "content": text}]}).json()


def test_opq_and_gsa_comparison_uses_catalog_fields():
    body = post_message("Compare OPQ and GSA for a talent audit.")
    reply = body["reply"]

    assert body["recommendations"] == []
    assert "Occupational Personality Questionnaire OPQ32r" in reply
    assert "Global Skills Assessment" in reply
    assert "Personality & Behavior" in reply
    assert "Competencies" in reply
    assert "25 minutes" in reply
    assert "16 minutes" in reply


def test_ambiguous_assessment_comparison_asks_for_catalog_choice():
    body = post_message("Compare OPQ report with OPQ.")
    reply = body["reply"].lower()

    assert body["recommendations"] == []
    assert "multiple" in reply or "which" in reply
    assert "opq" in reply
    assert "report" in reply


def test_comparison_preserves_prior_shortlist_when_following_up_on_recommendation():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "We are screening entry-level contact centre agents for English US inbound calls.",
                },
                {
                    "role": "assistant",
                    "content": "Here is a catalog-grounded SHL shortlist for contact centre agents, prioritized from the available catalog matches: SVAR Spoken English (US) (New); Contact Center Call Simulation (New); Customer Service Phone Simulation.",
                },
                {
                    "role": "user",
                    "content": "Is the Contact Center Call Simulation different from the Customer Service Phone Simulation?",
                },
            ]
        },
    )

    body = response.json()
    names = {item["name"] for item in body["recommendations"]}

    assert "Catalog-grounded comparison" in body["reply"]
    assert "Contact Center Call Simulation (New)" in names
    assert "Customer Service Phone Simulation" in names
    assert body["end_of_conversation"] is False
