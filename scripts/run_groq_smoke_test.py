"""Run a local Groq-backed smoke test against the live FastAPI server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MESSAGE = "Hiring a mid-level backend engineer who works with stakeholders. Assess technical skills and add personality signals too."
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def local_llm_configuration_status() -> dict[str, str | bool]:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {
            "env_file_present": False,
            "llm_api_key_present": False,
            "note": "No repo-root .env file was found. Create .env from .env.example, add your Groq key, then restart the FastAPI server.",
        }

    env_text = env_path.read_text(encoding="utf-8")
    api_key_present = any(
        line.startswith(("GROQ_API_KEY=", "LLM_API_KEY=")) and bool(line.split("=", maxsplit=1)[1].strip())
        for line in env_text.splitlines()
        if not line.lstrip().startswith("#")
    )
    note = ""
    if not api_key_present:
        note = "The repo-root .env file exists, but GROQ_API_KEY is empty. Add a valid Groq key and restart the FastAPI server."
    return {
        "env_file_present": True,
        "llm_api_key_present": api_key_present,
        "note": note,
    }


def main() -> int:
    base_url = os.getenv("SMOKE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    body = {
        "messages": [
            {
                "role": "user",
                "content": os.getenv("SMOKE_USER_MESSAGE", DEFAULT_MESSAGE),
            }
        ]
    }
    headers = {"X-Debug-LLM": "1"}

    try:
        with httpx.Client(timeout=30.0) as client:
            health = client.get(f"{base_url}/health")
            health.raise_for_status()
            response = client.post(f"{base_url}/chat", json=body, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Smoke test failed to reach {base_url}: {exc}", file=sys.stderr)
        return 1

    intent_status = response.headers.get("X-LLM-Intent-Extraction", "missing")
    rerank_status = response.headers.get("X-LLM-Reranking", "missing")
    payload = response.json()
    report = {
        "base_url": base_url,
        "local_configuration": local_llm_configuration_status(),
        "health": health.json(),
        "intent_extraction_status": intent_status,
        "reranking_status": rerank_status,
        "llm_intent_used": intent_status == "llm_success",
        "llm_reranking_used": rerank_status == "llm_success",
        "response": payload,
    }
    if intent_status == "missing" or rerank_status == "missing":
        report["note"] = "LLM debug headers are missing. Restart the FastAPI server on the updated code before trusting this smoke test."
    elif intent_status == "llm_disabled" or rerank_status == "llm_disabled":
        report["note"] = (
            "The server responded from the updated code path, but LLM features are disabled in that process. "
            "Check local_configuration, then restart the FastAPI server after fixing .env."
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())