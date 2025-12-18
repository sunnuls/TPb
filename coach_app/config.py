from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterConfigRef(BaseModel):
    """Reference to an adapter config file (YAML/JSON) for vision/screenshot ingestion."""

    name: str
    path: Path


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COACH_", env_file=".env", extra="ignore")

    env: Literal["dev", "prod", "test"] = "dev"
    api_title: str = "AI Poker + Blackjack Coach"
    api_version: str = "0.1.0"
    language: Literal["ru", "en"] = "ru"

    # Poker defaults
    poker_equity_samples: int = Field(default=20_000, ge=1000, le=500_000)

    # Vision adapters directory
    adapters_dir: Path = Field(default=Path("coach_app/configs/adapters"))
    vision_adapters_dir: Path = Field(default=Path("coach_app/configs/vision_adapters"))

    # Telegram
    telegram_bot_token: str | None = None


settings = AppSettings()


