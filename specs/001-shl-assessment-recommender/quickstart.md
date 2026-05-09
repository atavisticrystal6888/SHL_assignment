# Quickstart: Conversational SHL Assessment Recommender

## Prerequisites

- Python 3.11+ runtime.
- SHL catalog source available at `Documents/shl_product_catalog.json` during development.
- Public trace fixtures available at `Documents/GenAI_SampleConversations/C1.md` through `C10.md`.
- Environment variables for any selected LLM provider, if an LLM adapter is enabled.

## 1. Prepare Catalog Data

1. Copy or reference the provided catalog JSON as `data/raw/shl_product_catalog.json`.
2. Run the catalog normalization workflow.
3. Confirm the processed catalog records include `entity_id`, `name`, `url`, `test_type`, `categories`, `description`, `duration`, `remote_testing`, `adaptive_irt`, `job_levels`, `languages`, `eligible_for_recommendation`, and `eligibility_source`.
4. Confirm recommendation eligibility is restricted to Individual Test Solutions and that records without eligibility evidence default to ineligible.
5. Confirm the catalog coverage summary records the current 377-item source snapshot and source URL.

## 2. Load Public Trace Fixtures

1. Copy or reference `Documents/GenAI_SampleConversations/*.md` as public replay fixtures.
2. Parse trace turns into user/assistant histories.
3. Resolve final expected shortlist names and URLs to canonical catalog records where possible.
4. Record any trace caveats, such as recommendations shown as markdown tables while the API must return JSON arrays.

## 3. Start the API Locally

Validated development command:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Check Readiness

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

If you open the base URL `/` in a browser, the service returns a small JSON descriptor identifying the app and listing `/health` and `/chat`. That root response is informational only; evaluator checks still target `/health` and `/chat`.

## 5. Test Clarification Behavior

```powershell
$body = @{
  messages = @(
    @{ role = "user"; content = "I need an assessment" }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType "application/json" -Body $body
```

Expected behavior:

- `reply` asks a targeted clarifying question.
- `recommendations` is `[]`.
- `end_of_conversation` is `false`.

## 6. Test Recommendation Behavior

```powershell
$body = @{
  messages = @(
    @{ role = "user"; content = "Hiring a mid-level Java developer who works with stakeholders. What SHL assessments should I use?" }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType "application/json" -Body $body
```

Expected behavior:

- If enough context exists, `recommendations` contains 1 to 10 catalog-backed items.
- Each item includes `name`, `url`, and `test_type`.
- Every URL appears in the processed catalog.

## 7. Test Refinement Behavior

Submit a full history where the user first receives or approaches a shortlist, then says something like `Actually, add personality tests` or `Drop the OPQ`. Expected behavior: the next response updates the shortlist from the full history, treats corrections as authoritative, and removes now-invalid recommendations.

## 8. Test Comparison Behavior

Submit a question such as `What is the difference between OPQ and GSA?`. Expected behavior: the response uses catalog-backed fields and does not invent unsupported product claims.

## 9. Test Refusal Behavior

Submit off-topic, legal, non-SHL, or prompt-injection requests. Expected behavior: concise refusal or redirect to SHL assessment selection, `recommendations` is `[]`, and the top-level schema remains exact.

## 10. Run Evaluator-Style Checks

Validated validation commands:

```powershell
python -m pytest tests/contract
python -m pytest tests/integration/test_behavior_probes.py
python -m pytest tests/integration/test_replay_public_traces.py
python -m scripts.run_replay
```

Required checks:

- Exact response schema on every response.
- Schema-safe `POST /chat` response for malformed input, without FastAPI's default validation-error body.
- No public FastAPI default documentation routes in the submitted service.
- Empty recommendations during clarification/refusal.
- Catalog-only recommendation names and URLs.
- Explicit exclusion of Pre-packaged Job Solutions and records without Individual Test Solution eligibility evidence.
- 1 to 10 recommendations after commitment.
- 8-turn cap compliance.
- 30-second request budget under replay/probe runs.
- Recall@10 measurement for labeled trace final recommendations.
- Recall@10 baseline comparison after ranking, retrieval, or prompt changes.
- Behavior probes for refusal, no early recommendation, user edits, grounded comparisons, hallucination resistance, and conversational incoherence.
- Deterministic fallback behavior when the optional LLM adapter is disabled or unavailable.

## 11. Deployment Validation

1. Deploy the FastAPI service to Render Web Service as the default submission host.
2. Confirm `GET /health` responds with `{"status":"ok"}`.
3. Confirm `POST /chat` accepts stateless histories and returns the exact schema for valid and malformed request bodies.
4. Confirm default documentation routes such as `/docs`, `/redoc`, and `/openapi.json` are not exposed in the submitted service.
5. Record the first cold-start `/health` timing and confirm it completes within 2 minutes.
6. Confirm steady-state chat responses stay within evaluator timeout.

Current local validation: contract tests cover `/health`, `/chat`, and disabled default docs routes; public URL and cold-start timing still require the actual Render deployment.

## 12. Submission Readiness

Before submission, confirm:

- Public API endpoint URL is reachable.
- `/health` and `/chat` are both reachable.
- Approach document is no more than two pages.
- Approach document covers design choices, retrieval setup, prompt design, evaluation approach, failed approaches, measured improvement, and AI-tool usage.
- Latest replay/probe results are available for technical review.
