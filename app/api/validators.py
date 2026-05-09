"""Validation helpers for evaluator-safe chat responses."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.api.schemas import ChatRequest, ChatResponse, Recommendation
from app.catalog.repository import CatalogRepository

MALFORMED_INPUT_REPLY = (
    "I could not use that message history. Please send a messages array with user and assistant entries "
    "that include non-empty content."
)


def malformed_chat_response() -> ChatResponse:
    return ChatResponse(reply=MALFORMED_INPUT_REPLY, recommendations=[], end_of_conversation=False)


def parse_chat_request(payload: Any) -> tuple[ChatRequest | None, ChatResponse | None]:
    try:
        return ChatRequest.model_validate(payload), None
    except ValidationError:
        return None, malformed_chat_response()


def validate_chat_response(
    response: ChatResponse,
    *,
    catalog: CatalogRepository | None = None,
    recommendations_allowed: bool,
) -> ChatResponse:
    if not recommendations_allowed and response.recommendations:
        raise ValueError("recommendations must be empty for this response path")
    if len(response.recommendations) > 10:
        raise ValueError("recommendations must contain no more than 10 items")
    if recommendations_allowed and len(response.recommendations) == 0:
        raise ValueError("committed recommendation responses must contain at least one item")
    if catalog is not None:
        for recommendation in response.recommendations:
            if not catalog.contains_url(recommendation.url, eligible_only=True):
                raise ValueError(f"recommendation URL is not eligible catalog URL: {recommendation.url}")
    return response


def validate_refusal_response(response: ChatResponse) -> ChatResponse:
    return validate_chat_response(response, recommendations_allowed=False)


def recommendation_from_catalog(name: str, url: str, test_type: str) -> Recommendation:
    return Recommendation(name=name, url=url, test_type=test_type)
