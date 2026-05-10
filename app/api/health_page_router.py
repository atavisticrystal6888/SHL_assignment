"""Dev-only browser route for the health status page."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.page_support import template_response

router = APIRouter()


@router.get("/health/ui", include_in_schema=False, response_model=None)
def health_page() -> FileResponse:
    return template_response("health.html")