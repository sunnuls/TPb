from __future__ import annotations

from fastapi import FastAPI

from coach_app.api.routes_blackjack import router as blackjack_router
from coach_app.api.routes_poker import router as poker_router
from coach_app.api.routes_simulation import router as simulation_router
from coach_app.config import settings


def create_app() -> FastAPI:
    """
    Create FastAPI application with all routes.
    
    Includes:
    - Poker coaching routes
    - Blackjack coaching routes
    - Simulation research routes (educational use only)
    """
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="AI Poker & Blackjack Coach with Multi-Agent Simulation Research Support"
    )
    
    # Core coaching routes
    app.include_router(poker_router)
    app.include_router(blackjack_router)
    
    # Simulation research routes (educational only)
    app.include_router(simulation_router)
    
    return app


app = create_app()
