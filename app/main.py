"""FastAPI entry point for the stateless SHL assessment recommender."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Body, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ChatResponse
from app.api.validators import malformed_chat_response, parse_chat_request, validate_chat_response, validate_refusal_response
from app.catalog.repository import CatalogRepository
from app.conversation.extractor import extract_user_goal_result
from app.conversation.policy import decide_next_action
from app.conversation.renderer import (
    maybe_rewrite_reply,
    render_catalog_facts,
    render_clarification,
    render_comparison,
    render_recommendations,
    render_refinement,
    render_refusal,
)
from app.llm.client import LLMClient
from app.retrieval.index import build_catalog_index
from app.retrieval.query import build_retrieval_query
from app.retrieval.ranker import rank_catalog, rerank_catalog_with_llm_result
from app.settings import settings

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
DEBUG_HEADER = "x-debug-llm"


def debug_requested(request: Request) -> bool:
    return request.headers.get(DEBUG_HEADER, "").strip().lower() in {"1", "true", "yes", "on"}


def set_debug_headers(response: Response, request: Request, *, intent_status: str, rerank_status: str) -> None:
    if not debug_requested(request):
        return
    response.headers["X-LLM-Intent-Extraction"] = intent_status
    response.headers["X-LLM-Reranking"] = rerank_status


@lru_cache(maxsize=1)
def catalog_repository() -> CatalogRepository:
    return CatalogRepository.from_path(settings.catalog_path)


@lru_cache(maxsize=1)
def llm_client() -> LLMClient:
    return LLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    response = malformed_chat_response()
    return JSONResponse(status_code=200, content=response.model_dump())


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "shl-assessment-recommender",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(http_request: Request, http_response: Response, payload: Any = Body(default=None)) -> ChatResponse:
    chat_request, malformed = parse_chat_request(payload)
    if malformed is not None:
        set_debug_headers(http_response, http_request, intent_status="not_applicable", rerank_status="not_applicable")
        return validate_chat_response(malformed, recommendations_allowed=False)
    assert chat_request is not None
    client = llm_client()
    extraction = extract_user_goal_result(
        chat_request.messages,
        llm_client=client,
        enable_llm=settings.llm_enable_intent_extraction,
    )
    goal = extraction.goal
    decision = decide_next_action(goal)
    if decision.action == "refuse":
        set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
        response = render_refusal(decision)
        return validate_refusal_response(response)
    if decision.action == "compare":
        catalog = catalog_repository()
        resolutions = [catalog.resolve_assessment_reference(target) for target in goal.comparison_targets]
        set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
        response = render_comparison(goal, resolutions)
        return validate_chat_response(response, recommendations_allowed=False)
    if decision.action in {"recommend", "refine"}:
        catalog = catalog_repository()
        retrieval_query = build_retrieval_query(goal)
        index = build_catalog_index(catalog.eligible_records)
        matches = rank_catalog(
            index,
            retrieval_query.query_text,
            limit=10,
            preferred_categories=retrieval_query.preferred_categories,
            excluded_terms=retrieval_query.excluded_terms,
            constraints=retrieval_query.constraints,
        )
        rerank_status = "disabled_by_config"
        if settings.llm_enable_reranking:
            rerank_result = rerank_catalog_with_llm_result(matches, goal, client, limit=10)
            matches = rerank_result.matches
            rerank_status = rerank_result.llm_status
        if matches:
            set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status=rerank_status)
            response = render_refinement(goal, matches) if decision.action == "refine" else render_recommendations(goal, matches)
            response = maybe_rewrite_reply(
                response,
                goal,
                client,
                catalog_context=[render_catalog_facts(match.assessment) for match in matches[:5]],
            )
            return validate_chat_response(response, catalog=catalog, recommendations_allowed=True)
    response = render_clarification(goal, decision)
    set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
    response = maybe_rewrite_reply(response, goal, client)
    return validate_chat_response(response, recommendations_allowed=False)
