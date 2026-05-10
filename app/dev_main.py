"""Development entry point that adds browser pages on top of the submission API."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.chat_page_router import router as chat_page_router
from app.api.health_page_router import router as health_page_router
from app.api.landing_router import router as landing_router
from app.main import create_submission_app


def create_dev_app() -> FastAPI:
    application = create_submission_app()
    application.include_router(landing_router)
    application.include_router(health_page_router)
    application.include_router(chat_page_router)
    return application


app = create_dev_app()