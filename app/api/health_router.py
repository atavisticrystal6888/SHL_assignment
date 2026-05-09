"""Browser-aware health route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api.page_support import template_response, wants_html

router = APIRouter()


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", include_in_schema=False, response_model=None)
def health(request: Request) -> FileResponse | JSONResponse:
    if wants_html(request):
        return template_response("health.html")
    return JSONResponse(content=health_payload())