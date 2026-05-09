import json

import httpx

from app.llm.client import LLMClient


def test_llm_client_returns_fallback_when_disabled():
    client = LLMClient()

    result = client.complete("prompt", "fallback")

    assert result.text == "fallback"
    assert result.used_llm is False
    assert result.reason == "llm_disabled"


def test_llm_client_uses_openai_compatible_chat_completions_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "openai/gpt-oss-120b"
        assert payload["messages"][1]["content"] == "grounded prompt"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "LLM rewritten reply"}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete("grounded prompt", "fallback")

    assert result.text == "LLM rewritten reply"
    assert result.used_llm is True
    assert result.reason == "llm_success"


def test_llm_client_falls_back_on_http_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = LLMClient(
        api_key="bad-key",
        base_url="https://example.com/v1",
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete("grounded prompt", "fallback")

    assert result.text == "fallback"
    assert result.used_llm is False
    assert result.reason == "llm_http_error"


def test_llm_client_complete_json_returns_payload_and_status():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ordered_entity_ids": ["1", "2"]}'}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete_json("grounded prompt")

    assert result.payload == {"ordered_entity_ids": ["1", "2"]}
    assert result.used_llm is True
    assert result.reason == "llm_success"