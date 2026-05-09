"""Browser route for the landing page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api.page_support import template_response, wants_html

router = APIRouter()


def root_payload() -> dict[str, Any]:
    return {
        "service": "shl-assessment-recommender",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
        },
    }


@router.get("/", include_in_schema=False, response_model=None)
def root(request: Request) -> FileResponse | JSONResponse:
    if wants_html(request):
        return template_response("landing.html")
    return JSONResponse(content=root_payload())