from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ParseReport(BaseModel):
    """Structured parse report for HH ingestion."""

    parser: str
    room: Literal["pokerstars", "gg", "generic", "unknown"] = "unknown"
    game_type_detected: Literal["NLHE_6max_cash", "NLHE_MTT", "unknown"] = "unknown"

    confidence: float = Field(..., ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    parsed: dict[str, Any] = Field(default_factory=dict, description="Small summary of parsed fields.")


class HandHistoryParseError(BaseModel):
    message: str
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    parse_report: ParseReport | None = None


