from fastapi.testclient import TestClient

from app.evaluation.metrics import recall_at_k
from app.evaluation.replay import discover_trace_fixtures, parse_trace_fixture, replay_trace
from app.main import app
from app.settings import settings


def test_public_trace_parser_extracts_turns_and_expected_shortlists():
    fixtures = discover_trace_fixtures(settings.trace_fixtures_dir)

    assert len(fixtures) == 10
    parsed = parse_trace_fixture(next(fixture for fixture in fixtures if fixture.trace_id == "C2"))
    assert parsed.trace_id == "C2"
    assert parsed.user_turns
    assert any("Rust engineer" in turn.content for turn in parsed.user_turns)
    assert any(item.name == "SHL Verify Interactive G+" for item in parsed.expected_shortlist)
    assert all(item.url.startswith("https://www.shl.com/products/product-catalog/view/") for item in parsed.expected_shortlist)


def test_public_trace_replay_returns_schema_safe_metadata_for_first_trace():
    fixtures = discover_trace_fixtures(settings.trace_fixtures_dir)
    client = TestClient(app)

    result = replay_trace(client, parse_trace_fixture(fixtures[0]), max_user_turns=2)

    assert result.trace_id == fixtures[0].trace_id
    assert result.schema_pass is True
    assert result.turn_cap_pass is True
    assert result.timeout_pass is True
    assert result.responses
    assert all(set(response.keys()) == {"reply", "recommendations", "end_of_conversation"} for response in result.responses)
    assert result.recall_at_10 is None or 0.0 <= result.recall_at_10 <= 1.0


def test_replay_expected_shortlist_supports_recall_at_10_measurement():
    fixtures = discover_trace_fixtures(settings.trace_fixtures_dir)
    parsed = parse_trace_fixture(next(fixture for fixture in fixtures if fixture.trace_id == "C10"))
    expected = [item.url for item in parsed.expected_shortlist]
    actual = expected[:2]

    assert recall_at_k(expected, actual, k=10) == 2 / len(expected)


def test_public_trace_parser_uses_last_shortlist_table_for_c10():
    fixtures = discover_trace_fixtures(settings.trace_fixtures_dir)
    parsed = parse_trace_fixture(next(fixture for fixture in fixtures if fixture.trace_id == "C10"))

    assert [item.name for item in parsed.expected_shortlist] == ["SHL Verify Interactive G+", "Graduate Scenarios"]
