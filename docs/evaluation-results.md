# Evaluation Results

## Local Regression

Latest scoped SHL feature regression command: selected unit, contract, and integration tests for catalog normalization, schema validation, goal extraction, ranking, all six user stories, replay, behavior probes, and non-happy paths.

Result: 49 passed in 16.78 seconds.

The new Phase 9 robustness coverage in `tests/integration/test_non_happy_paths.py` verifies malformed message history normalization, declined seniority preference handling, and later contradictory skill correction.

## Replay And Probe Run

Latest replay command: `scripts/run_replay.py`.

- Schema pass: true
- Turn-cap pass: true
- Timeout pass: true
- Public traces replayed: C1 through C10
- Trace failures: none
- Behavior probes: 6 passed, 0 failed

Behavior probes cover vague clarification, legal/off-topic refusal, user-edit refinement, grounded comparison, hallucination resistance, and conversational coherence after a declined seniority preference.

## Recall@10

Current labeled public-trace Recall@10 values:

| Trace | Recall@10 |
|-------|-----------|
| C2 | 0.20 |
| C4 | 0.40 |

Mean Recall@10 across labeled public traces with non-null expected shortlists is 0.30. The remaining public traces currently have no recoverable expected shortlist in the replay parser output, so Recall@10 is recorded as unavailable for those traces.

Baseline comparison status: unavailable. No earlier persisted Recall@10 baseline exists in the repository; this Phase 9 run is the recorded baseline for future ranking or prompt changes.

## Broader Repository Suite Note

An upstream-wide `pytest tests -q` run was attempted. It collected 2,945 tests and confirmed all SHL feature tests passed before moving into unrelated Spec Kit integration coverage. It was stopped after more than ten minutes because the remaining upstream suite was outside the SHL feature release gate. The transient `tests/integrations/test_cli.py` marker from that broad run did not reproduce: `tests/integrations/test_cli.py` passes in isolation with 67 passed and 1 skipped.

## Deployment Checks

Local contract coverage verifies `GET /health`, strict malformed `/chat` responses, and disabled default FastAPI docs routes. Public Render URL and cold-start timing remain pending until a Render deployment is created.