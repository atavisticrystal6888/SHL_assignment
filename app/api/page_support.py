"""Helpers for serving browser pages without breaking JSON API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


def wants_html(request: Request) -> bool:
    accept_header = request.headers.get("accept", "")
    return "text/html" in accept_header or "application/xhtml+xml" in accept_header


def template_response(filename: str) -> FileResponse:
    return FileResponse(TEMPLATE_DIR / filename, media_type="text/html")