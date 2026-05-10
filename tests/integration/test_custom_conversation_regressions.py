import pytest
from fastapi.testclient import TestClient

from app.main import app


CASES = [
    {
        "case_id": "healthcare_hybrid",
        "turns": [
            "We're hiring bilingual clinic coordinators in Texas for patient-record handling. Spanish delivery is important, but HIPAA and medical terminology still matter. A hybrid English/Spanish setup is acceptable. What SHL assessments fit?",
        ],
        "must_include": [
            "Medical Terminology (New)",
            "HIPAA (Security)",
            "Occupational Personality Questionnaire OPQ32r",
            "Dependability and Safety Instrument (DSI)",
        ],
        "must_exclude": ["Workplace Health and Safety (New)"],
    },
    {
        "case_id": "contact_center_uk",
        "turns": [
            "We're hiring entry-level U.K. contact-centre agents for customer calls. I need a phone simulation, a spoken-English screen, and a retail/customer-service fit measure. Which SHL assessments fit?",
        ],
        "must_include": [
            "Contact Center Call Simulation (New)",
            "Customer Service Phone Simulation",
            "Entry Level Customer Serv-Retail & Contact Center",
            "SVAR - Spoken English (U.K.)",
        ],
        "must_exclude": ["SVAR - Spoken English (US) (New)"],
    },
    {
        "case_id": "industrial_safety",
        "turns": [
            "We're hiring plant operators for a petrochemical facility. Safety, reliability, and not cutting corners matter most, and we're an industrial site. Which SHL assessments fit?",
        ],
        "must_include": [
            "Manufac. & Indust. - Safety & Dependability 8.0",
            "Dependability and Safety Instrument (DSI)",
            "Workplace Health and Safety (New)",
        ],
        "must_exclude": [],
    },
    {
        "case_id": "graduate_battery_trim",
        "turns": [
            "We run a graduate management trainee intake and need cognitive, personality, and situational judgment coverage for recent graduates. What should the battery include?",
            "Remove OPQ32r and confirm the remaining shortlist.",
        ],
        "must_include": ["SHL Verify Interactive G+", "Graduate Scenarios"],
        "must_exclude": ["Occupational Personality Questionnaire OPQ32r"],
    },
    {
        "case_id": "admin_office_sim",
        "turns": [
            "I need to quickly screen admin assistants for Excel and Word daily.",
            "Actually add a simulation so we can capture the capabilities.",
        ],
        "must_include": [
            "Microsoft Excel 365 (New)",
            "Microsoft Word 365 (New)",
            "MS Excel (New)",
            "MS Word (New)",
        ],
        "must_exclude": [],
    },
]


@pytest.mark.parametrize("case", CASES, ids=[case["case_id"] for case in CASES])
def test_custom_conversation_regressions(case):
    client = TestClient(app)
    messages = []
    final_body = None

    for turn in case["turns"]:
        messages.append({"role": "user", "content": turn})
        final_body = client.post("/chat", json={"messages": messages}).json()
        messages.append({"role": "assistant", "content": final_body["reply"]})

    assert final_body is not None
    final_names = [item["name"] for item in final_body["recommendations"]]
    assert all(name in final_names for name in case["must_include"])
    assert all(name not in final_names for name in case["must_exclude"])