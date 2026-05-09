"""Browser route for the chat workspace."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.page_support import template_response

router = APIRouter()


@router.get("/chat", include_in_schema=False, response_model=None)
def chat_page() -> FileResponse:
    return template_response("chat.html")