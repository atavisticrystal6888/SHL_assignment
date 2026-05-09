# Deployment

## Public API Surface

The service is designed for a Render Web Service deployment. The evaluator-required API surface is:

- `GET /health`
- `POST /chat`

The root path `/` also returns a lightweight service descriptor so opening the base deployment URL in a browser confirms the service is live and shows the primary endpoints. Default FastAPI documentation routes remain disabled, so `/docs`, `/redoc`, and `/openapi.json` return 404 in local contract tests.

## Render Configuration

`render.yaml` declares a Python web service named `shl-assessment-recommender` with:

- Build command: `pip install -e .`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Python version: `3.11.9`
- Catalog and trace fixture paths supplied through environment variables

## Local Validation

The deployment contract test verifies that `/health` returns `{"status": "ok"}`, `/chat` keeps the exact response schema for malformed input, and default docs routes are not exposed.

Current local validation status:

- `/health`: validated by `tests/contract/test_us6_health_and_deployment_contract.py`
- `/chat`: validated for strict malformed-input response shape by `tests/contract/test_us6_health_and_deployment_contract.py`
- `/docs`, `/redoc`, `/openapi.json`: validated as 404 by `tests/contract/test_us6_health_and_deployment_contract.py`
- Steady-state replay/probe timeout: latest local replay run passed the 30-second timeout flag for all public traces

## Public Deployment Evidence

- Public URL: pending actual Render deployment
- First cold-start `/health` timing: pending actual Render deployment
- Public `/chat` validation: pending actual Render deployment
- Public default-docs route validation: pending actual Render deployment

The expected cold-start gate is under 2 minutes for the first health check and under 30 seconds for steady-state chat calls.