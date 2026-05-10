"""Submission health route."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", include_in_schema=False, response_model=None)
def health() -> JSONResponse:
    return JSONResponse(content=health_payload())