"""Run local evaluator-style replay and behavior probes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.evaluation.probes import run_behavior_probes
from app.evaluation.replay import replay_fixtures
from app.main import app
from app.settings import settings


def main() -> int:
    client = TestClient(app)
    trace_results = replay_fixtures(client, settings.trace_fixtures_dir, max_user_turns=4)
    probe_results = run_behavior_probes(client)
    payload = {
        "schema_pass": all(result.schema_pass for result in trace_results),
        "turn_cap_pass": all(result.turn_cap_pass for result in trace_results),
        "timeout_pass": all(result.timeout_pass for result in trace_results),
        "trace_results": [
            {
                "trace_id": result.trace_id,
                "schema_pass": result.schema_pass,
                "turn_cap_pass": result.turn_cap_pass,
                "timeout_pass": result.timeout_pass,
                "recall_at_10": result.recall_at_10,
                "failures": result.failures,
            }
            for result in trace_results
        ],
        "probe_results": [result.__dict__ for result in probe_results],
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["schema_pass"] and payload["turn_cap_pass"] and payload["timeout_pass"] and all(result.passed for result in probe_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())