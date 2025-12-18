from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, field_validator


class Meta(BaseModel):
    model_config = {"extra": "ignore"}

    _allowed_sources: ClassVar[set[str]] = {"poker_room", "simulator", "home_game", "play_money", "unknown"}
    _allowed_triggers: ClassVar[set[str]] = {"ui_change", "hotkey", "hand_complete", "unknown"}

    source: str = "unknown"
    is_realtime: bool = False
    hand_complete: bool | None = None
    client_tag: str | None = None

    post_action: bool = False
    trigger: Literal["ui_change", "hotkey", "hand_complete", "unknown"] = "unknown"
    frame_id: str | None = None
    session_id: str | None = None

    @field_validator("source", mode="before")
    @classmethod
    def _normalize_source(cls, v: object) -> str:
        if v is None:
            return "unknown"
        s = str(v)
        if s in cls._allowed_sources:
            return s
        return "unknown"

    @field_validator("trigger", mode="before")
    @classmethod
    def _normalize_trigger(cls, v: object) -> str:
        if v is None:
            return "unknown"
        s = str(v)
        if s in cls._allowed_triggers:
            return s
        return "unknown"
