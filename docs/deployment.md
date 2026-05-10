# Deployment

## Public API Surface

The service is designed for a Render Web Service deployment. The evaluator-required API surface is:

- `GET /health`
- `POST /chat`

The submission deployment intentionally does not expose a browser landing page. `GET /` returns `404`, `GET /chat` returns `405`, and default FastAPI documentation routes remain disabled.

## Render Configuration

`render.yaml` declares a Python web service named `shl-assessment-recommender` with:

- Build command: `pip install -e . && python scripts/render_preflight.py`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Python version: `3.11.9`
- Catalog and trace fixture paths supplied through environment variables
- `LLM_ENABLE_INTENT_EXTRACTION=false`
- `LLM_ENABLE_RERANKING=false`

The Render build preflight fails the deployment early if the processed catalog files, trace fixtures, or submission app health route are broken. The blueprint defaults to the deterministic evaluator-safe path; only enable LLM-backed intent extraction or reranking on Render after measuring a concrete improvement in replay quality and latency.

## Render Deployment Steps

1. Create a new Render Web Service from this repository.
2. Let Render detect `render.yaml` from the repository root.
3. Confirm the service uses the blueprint build and start commands without switching to `app.dev_main:app`.
4. Keep the default blueprint environment values for `CATALOG_PATH`, `CATALOG_COVERAGE_PATH`, and `TRACE_FIXTURES_DIR`.
5. Leave `LLM_ENABLE_INTENT_EXTRACTION` and `LLM_ENABLE_RERANKING` set to `false` for the initial deployment.
6. If you later want to test Groq-backed stages, add `GROQ_API_KEY` and `GROQ_MODEL` as Render environment variables and re-measure replay, probe, and timeout behavior before submitting.

## Local Validation

The deployment contract test verifies that `/health` returns `{"status": "ok"}`, `/chat` keeps the exact response schema for malformed input, `GET /` stays disabled, `GET /chat` is not a page route, and default docs routes are not exposed.

Current local validation status:

- `/health`: validated by `tests/contract/test_us6_health_and_deployment_contract.py`
- `/chat`: validated for strict malformed-input response shape by `tests/contract/test_us6_health_and_deployment_contract.py`
- `GET /`: validated as `404` by `tests/contract/test_us6_health_and_deployment_contract.py`
- `GET /chat`: validated as `405` by `tests/contract/test_us6_health_and_deployment_contract.py`
- `/docs`, `/redoc`, `/openapi.json`: validated as 404 by `tests/contract/test_us6_health_and_deployment_contract.py`
- Render build preflight: validated by `python scripts/render_preflight.py`
- Steady-state replay/probe timeout: latest local replay run passed the 30-second timeout flag for all public traces

## Post-Deploy Validation

After Render finishes deploying, validate the live service with:

```powershell
python scripts/validate_render_deployment.py https://your-service-name.onrender.com
```

The validator checks:

- `GET /health` returns JSON `{"status": "ok"}`
- malformed `POST /chat` preserves the exact evaluator-facing response shape
- `/docs`, `/redoc`, and `/openapi.json` return `404`
- `GET /` returns `404`
- `GET /chat` returns `405`

## Public Deployment Evidence

- Public URL: pending actual Render deployment
- First cold-start `/health` timing: pending actual Render deployment
- Public `/chat` validation: pending actual Render deployment
- Public default-docs route validation: pending actual Render deployment

The expected cold-start gate is under 2 minutes for the first health check and under 30 seconds for steady-state chat calls.