"""Validate a deployed Render instance against the evaluator contract."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Expected JSON response from {response.request.method} {response.request.url}: {exc}") from exc
    require(isinstance(payload, dict), f"Expected JSON object from {response.request.method} {response.request.url}")
    return payload


def validate(base_url: str, timeout_seconds: float) -> None:
    base_url = base_url.rstrip("/")
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        health = client.get(f"{base_url}/health", headers={"accept": "text/html"})
        require(health.status_code == 200, f"GET /health failed with {health.status_code}")
        require(health.headers.get("content-type", "").startswith("application/json"), "GET /health must return JSON")
        require(load_json(health) == {"status": "ok"}, "GET /health must return exactly {'status': 'ok'}")

        malformed = client.post(f"{base_url}/chat", json={"messages": []})
        require(malformed.status_code == 200, f"Malformed POST /chat failed with {malformed.status_code}")
        malformed_body = load_json(malformed)
        require(
            set(malformed_body.keys()) == {"reply", "recommendations", "end_of_conversation"},
            "Malformed POST /chat must preserve the exact top-level response shape",
        )
        require(malformed_body.get("recommendations") == [], "Malformed POST /chat must return empty recommendations")
        require("detail" not in malformed_body, "Malformed POST /chat must not return FastAPI's default error body")

        for path in ("/docs", "/redoc", "/openapi.json"):
            response = client.get(f"{base_url}{path}")
            require(response.status_code == 404, f"{path} must return 404, got {response.status_code}")

        root = client.get(f"{base_url}/")
        require(root.status_code == 404, f"GET / must return 404, got {root.status_code}")

        chat_get = client.get(f"{base_url}/chat")
        require(chat_get.status_code == 405, f"GET /chat must return 405, got {chat_get.status_code}")

    print("Render deployment validation passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a deployed Render instance against the evaluator contract.")
    parser.add_argument("base_url", help="Public base URL, for example https://your-service.onrender.com")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds for each request")
    args = parser.parse_args()
    validate(args.base_url, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())