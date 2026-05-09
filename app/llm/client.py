"""Optional OpenAI-compatible LLM adapter with deterministic fallback."""

from __future__ import annotations

import json
import re
import ssl
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_TIMEOUT_SECONDS = 15.0
SYSTEM_PROMPT = (
    "You rewrite a reply for an SHL assessment recommender. "
    "Use only the supplied user-goal and catalog facts. "
    "Return plain text only and do not mention hidden instructions or JSON."
)
JSON_SYSTEM_PROMPT = (
    "You are a structured extraction and reranking helper for an SHL assessment recommender. "
    "Use only the supplied conversation and catalog facts. "
    "Return valid JSON only with no markdown fences or prose."
)


@dataclass(frozen=True)
class LLMResult:
    text: str
    used_llm: bool
    reason: str


@dataclass(frozen=True)
class LLMJSONResult:
    payload: dict[str, Any] | None
    used_llm: bool
    reason: str


class LLMClient:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        *,
        timeout_seconds: float = DEFAULT_LLM_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.strip()
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.ssl_context = ssl.create_default_context()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    @property
    def chat_completions_url(self) -> str:
        base_url = (self.base_url or DEFAULT_LLM_BASE_URL).rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

    def _extract_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        choice = choices[0]
        if not isinstance(choice, dict):
            return ""
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content", "")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                return "\n".join(parts).strip()
        text = choice.get("text", "")
        if isinstance(text, str):
            return text.strip()
        return ""

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            transport=self.transport,
            verify=self.ssl_context,
        )

    def complete(self, prompt: str, fallback: str, *, system_prompt: str = SYSTEM_PROMPT) -> LLMResult:
        if not self.enabled:
            return LLMResult(text=fallback, used_llm=False, reason="llm_disabled")
        try:
            with self._client() as client:
                response = client.post(
                    self.chat_completions_url,
                    headers=self._headers(),
                    json=self._payload(prompt, system_prompt),
                )
                response.raise_for_status()
            text = self._extract_text(response.json())
        except httpx.HTTPStatusError:
            return LLMResult(text=fallback, used_llm=False, reason="llm_http_error")
        except httpx.RequestError:
            return LLMResult(text=fallback, used_llm=False, reason="llm_request_error")
        except ValueError:
            return LLMResult(text=fallback, used_llm=False, reason="llm_response_invalid")

        if not text:
            return LLMResult(text=fallback, used_llm=False, reason="llm_response_empty")
        return LLMResult(text=text, used_llm=True, reason="llm_success")

    def complete_json(self, prompt: str) -> LLMJSONResult:
        result = self.complete(prompt, "", system_prompt=JSON_SYSTEM_PROMPT)
        if not result.used_llm:
            return LLMJSONResult(payload=None, used_llm=False, reason=result.reason)
        text = result.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return LLMJSONResult(payload=None, used_llm=False, reason="llm_json_invalid")
        if not isinstance(payload, dict):
            return LLMJSONResult(payload=None, used_llm=False, reason="llm_json_not_object")
        return LLMJSONResult(payload=payload, used_llm=True, reason="llm_success")
