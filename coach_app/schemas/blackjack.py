from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BlackjackAction(str, Enum):
    hit = "hit"
    stand = "stand"
    double = "double"
    split = "split"
    surrender = "surrender"


class BlackjackRules(BaseModel):
    decks: int = Field(default=6, ge=1, le=8)
    hit_soft_17: bool = Field(default=False, description="False means S17 (dealer stands on soft 17).")
    das: bool = Field(default=True, description="Double after split allowed.")
    surrender: bool = Field(default=True, description="Late surrender allowed.")
    peek: bool = Field(default=True, description="Dealer peeks for blackjack (typical).")


Rank = Literal["A", "2", "3", "4", "5", "6", "7", "8", "9", "T"]


class BlackjackState(BaseModel):
    player_hand: list[Rank] = Field(..., min_length=2, max_length=11)
    dealer_upcard: Rank
    can_split: bool = True
    can_double: bool = True
    can_surrender: bool = True
    running_count: int | None = None
    true_count: float | None = None
    rules: BlackjackRules = Field(default_factory=BlackjackRules)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_counts(self) -> "BlackjackState":
        if self.true_count is not None and self.running_count is None:
            raise ValueError("true_count provided without running_count")
        return self


class BlackjackDecision(BaseModel):
    action: BlackjackAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_facts: dict = Field(default_factory=dict)


class BlackjackAnalyzeRequest(BaseModel):
    player_hand: list[Rank]
    dealer_upcard: Rank
    rules: BlackjackRules = Field(default_factory=BlackjackRules)
    running_count: int | None = None
    true_count: float | None = None
    can_split: bool = True
    can_double: bool = True
    can_surrender: bool = True


class BlackjackTrainRequest(BlackjackAnalyzeRequest):
    mode: Literal["review", "trainer"] = "review"


