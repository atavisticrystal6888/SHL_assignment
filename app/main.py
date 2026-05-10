"""FastAPI entry point for the stateless SHL assessment recommender."""

from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from fastapi import Body, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.chat_page_router import router as chat_page_router
from app.api.health_router import router as health_router
from app.api.landing_router import router as landing_router
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
from app.retrieval.ranker import CatalogMatch, rank_catalog, rerank_catalog_with_llm_result
from app.settings import settings

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(landing_router)
app.include_router(health_router)
app.include_router(chat_page_router)
DEBUG_HEADER = "x-debug-llm"
REQUEST_BUDGET_SECONDS = 27.5
LLM_INTENT_RESERVE_SECONDS = 8.0
LLM_RERANK_RESERVE_SECONDS = 3.5
LLM_REWRITE_RESERVE_SECONDS = 1.0


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
def catalog_index() -> Any:
    return build_catalog_index(catalog_repository().eligible_records)


@lru_cache(maxsize=1)
def llm_client() -> LLMClient:
    return LLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )


def request_deadline() -> float:
    return time.perf_counter() + REQUEST_BUDGET_SECONDS


def remaining_budget_seconds(deadline: float) -> float:
    return max(0.0, deadline - time.perf_counter())


def llm_timeout_seconds(
    deadline: float,
    client: LLMClient,
    *,
    reserve_seconds: float,
    cap_seconds: float,
) -> float | None:
    remaining = remaining_budget_seconds(deadline) - reserve_seconds
    if remaining < 1.0:
        return None
    return min(client.timeout_seconds, cap_seconds, remaining)


def resolve_prior_shortlist_matches(goal, catalog: CatalogRepository) -> list[CatalogMatch]:
    matches: list[CatalogMatch] = []
    seen: set[str] = set()
    for hint in goal.prior_shortlist_hints:
        resolution = catalog.resolve_assessment_reference(hint)
        record = resolution.record
        if record is None or not record.eligible_for_recommendation or record.entity_id in seen:
            continue
        matches.append(
            CatalogMatch(
                assessment=record,
                score=10.0,
                matched_fields=["prior_shortlist"],
                rationale_facts=[record.name],
                warnings=[],
            )
        )
        seen.add(record.entity_id)
    return matches


def carry_forward_matches(goal, prior_matches: list[CatalogMatch], matches: list[CatalogMatch]) -> list[CatalogMatch]:
    if not prior_matches:
        return matches
    excluded_terms = {term.lower() for term in goal.excluded_terms}
    retained_prior: list[CatalogMatch] = []
    for match in prior_matches:
        haystack = " ".join([match.assessment.name, match.assessment.description, match.assessment.url]).lower()
        if any(term in haystack for term in excluded_terms):
            continue
        retained_prior.append(match)
    if goal.latest_intent == "compare":
        return retained_prior
    if goal.latest_intent not in {"recommend", "refine"}:
        return matches
    merged: list[CatalogMatch] = []
    seen: set[str] = set()
    for match in retained_prior + matches:
        if match.assessment.entity_id in seen:
            continue
        merged.append(match)
        seen.add(match.assessment.entity_id)
        if len(merged) >= 10:
            break
    return merged


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    response = malformed_chat_response()
    return JSONResponse(status_code=200, content=response.model_dump())


@app.post("/chat", response_model=ChatResponse)
def chat(http_request: Request, http_response: Response, payload: Any = Body(default=None)) -> ChatResponse:
    chat_request, malformed = parse_chat_request(payload)
    if malformed is not None:
        set_debug_headers(http_response, http_request, intent_status="not_applicable", rerank_status="not_applicable")
        return validate_chat_response(malformed, recommendations_allowed=False)
    assert chat_request is not None
    deadline = request_deadline()
    client = llm_client()
    intent_timeout = llm_timeout_seconds(
        deadline,
        client,
        reserve_seconds=LLM_INTENT_RESERVE_SECONDS,
        cap_seconds=4.0,
    )
    extraction = extract_user_goal_result(
        chat_request.messages,
        llm_client=client,
        enable_llm=settings.llm_enable_intent_extraction,
        llm_timeout_seconds=intent_timeout if intent_timeout is not None else 0.0,
    )
    goal = extraction.goal
    decision = decide_next_action(goal)
    catalog = catalog_repository()
    prior_matches = resolve_prior_shortlist_matches(goal, catalog)
    if decision.action == "refuse":
        set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
        response = render_refusal(decision)
        return validate_refusal_response(response)
    if decision.action == "compare":
        resolutions = [catalog.resolve_assessment_reference(target) for target in goal.comparison_targets]
        set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
        response = render_comparison(goal, resolutions, prior_matches=prior_matches)
        return validate_chat_response(response, catalog=catalog, recommendations_allowed=bool(response.recommendations))
    if decision.action in {"recommend", "refine"}:
        retrieval_query = build_retrieval_query(goal)
        matches = rank_catalog(
            catalog_index(),
            retrieval_query.query_text,
            limit=10,
            preferred_categories=retrieval_query.preferred_categories,
            required_terms=retrieval_query.required_terms,
            seed_assessment_names=retrieval_query.seed_assessment_names,
            job_level_signals=retrieval_query.job_level_signals,
            language_signals=retrieval_query.language_signals,
            locale_signal=retrieval_query.locale_signal,
            excluded_terms=retrieval_query.excluded_terms,
            constraints=retrieval_query.constraints,
        )
        rerank_status = "disabled_by_config"
        rerank_timeout = llm_timeout_seconds(
            deadline,
            client,
            reserve_seconds=LLM_RERANK_RESERVE_SECONDS,
            cap_seconds=3.0,
        )
        if settings.llm_enable_reranking:
            rerank_result = rerank_catalog_with_llm_result(
                matches,
                goal,
                client,
                limit=10,
                llm_timeout_seconds=rerank_timeout if rerank_timeout is not None else 0.0,
            )
            matches = rerank_result.matches
            rerank_status = rerank_result.llm_status
        matches = carry_forward_matches(goal, prior_matches, matches)
        if matches:
            set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status=rerank_status)
            response = render_refinement(goal, matches) if decision.action == "refine" else render_recommendations(goal, matches)
            rewrite_timeout = llm_timeout_seconds(
                deadline,
                client,
                reserve_seconds=LLM_REWRITE_RESERVE_SECONDS,
                cap_seconds=2.0,
            )
            response = maybe_rewrite_reply(
                response,
                goal,
                client,
                catalog_context=[render_catalog_facts(match.assessment) for match in matches[:5]],
                timeout_seconds=rewrite_timeout if rewrite_timeout is not None else 0.0,
            )
            return validate_chat_response(response, catalog=catalog, recommendations_allowed=True)
    response = render_clarification(goal, decision)
    set_debug_headers(http_response, http_request, intent_status=extraction.llm_status, rerank_status="not_applicable")
    rewrite_timeout = llm_timeout_seconds(
        deadline,
        client,
        reserve_seconds=LLM_REWRITE_RESERVE_SECONDS,
        cap_seconds=2.0,
    )
    response = maybe_rewrite_reply(
        response,
        goal,
        client,
        timeout_seconds=rewrite_timeout if rewrite_timeout is not None else 0.0,
    )
    return validate_chat_response(response, recommendations_allowed=False)
