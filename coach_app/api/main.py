from __future__ import annotations

from fastapi import FastAPI

from coach_app.api.routes_poker import router as poker_router
from coach_app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.api_title, version=settings.api_version)
    app.include_router(poker_router)
    return app


app = create_app()
