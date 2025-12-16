from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class Suit(str, Enum):
    s = "s"
    h = "h"
    d = "d"
    c = "c"


RANKS = "23456789TJQKA"


class Card(BaseModel):
    rank: str = Field(..., pattern=f"^[{RANKS}]$")
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank}{self.suit.value}"

    @classmethod
    def from_str(cls, s: str) -> "Card":
        s = s.strip()
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s!r}")
        return cls(rank=s[0].upper(), suit=Suit(s[1].lower()))


class Confidence(BaseModel):
    """Confidence about a parsed observation (0..1)."""

    value: float = Field(..., ge=0.0, le=1.0)
    source: Literal["hand_history", "vision", "user", "engine"] = "engine"
    notes: list[str] = Field(default_factory=list)


class DecisionBase(BaseModel):
    action: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_facts: dict[str, Any] = Field(default_factory=dict)


class ExplainableResult(BaseModel):
    decision: DecisionBase
    explanation: str


