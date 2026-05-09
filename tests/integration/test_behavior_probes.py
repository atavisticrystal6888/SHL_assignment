from fastapi.testclient import TestClient

from app.evaluation.probes import default_behavior_probes, run_behavior_probes
from app.main import app


def test_behavior_probe_suite_covers_required_agent_paths():
    probe_ids = {probe.probe_id for probe in default_behavior_probes()}

    assert {
        "vague_clarification",
        "off_topic_refusal",
        "user_edit_refinement",
        "grounded_comparison",
        "hallucination_resistance",
        "conversational_incoherence",
    }.issubset(probe_ids)


def test_default_behavior_probes_pass_against_local_app():
    results = run_behavior_probes(TestClient(app), default_behavior_probes())

    assert results
    assert all(result.passed for result in results), [result.failure for result in results if not result.passed]
