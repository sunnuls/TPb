from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from coach_app.product.mode import ProductMode
from coach_app.schemas.meta import Meta


class BlackjackAction(str, Enum):
    hit = "hit"
    stand = "stand"
    double = "double"
    split = "split"
    surrender = "surrender"


class SurrenderAllowed(str, Enum):
    none = "none"
    early = "early"
    late = "late"


class BlackjackRules(BaseModel):
    decks: int = Field(default=6, ge=1, le=8)
    dealer_hits_soft_17: bool = Field(default=False, description="False means S17 (dealer stands on soft 17).")
    double_after_split: bool = Field(default=True, description="DAS: double after split allowed.")
    surrender_allowed: SurrenderAllowed = Field(default=SurrenderAllowed.late)
    resplit_aces: bool = Field(default=False)
    max_splits: int = Field(default=3, ge=0, le=4)


CardToken = str
AllowedAction = Literal["hit", "stand", "double", "split", "surrender"]


class BlackjackState(BaseModel):
    player_hand: list[CardToken] = Field(..., min_length=2, max_length=11)
    dealer_upcard: CardToken
    allowed_actions: list[BlackjackAction] | None = None
    split_count: int = Field(default=0, ge=0, le=4)
    hand_doubled: bool = False
    running_count: int | None = None
    true_count: float | None = None
    rules: BlackjackRules = Field(default_factory=BlackjackRules)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_counts(self) -> "BlackjackState":
        if self.true_count is not None and self.running_count is None:
            raise ValueError("true_count provided without running_count")
        if not self.player_hand or not isinstance(self.player_hand, list):
            raise ValueError("player_hand must be a list")
        for c in self.player_hand:
            if not isinstance(c, str) or len(c) != 2:
                raise ValueError("Invalid player_hand card token")
        if not isinstance(self.dealer_upcard, str) or len(self.dealer_upcard) != 2:
            raise ValueError("Invalid dealer_upcard card token")
        return self


class BlackjackDecision(BaseModel):
    action: BlackjackAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_facts: dict = Field(default_factory=dict)


class BlackjackAnalyzeRequest(BaseModel):
    player_hand: list[CardToken]
    dealer_upcard: CardToken
    rules: BlackjackRules = Field(default_factory=BlackjackRules)
    allowed_actions: list[BlackjackAction] | None = None
    running_count: int | None = None
    true_count: float | None = None
    split_count: int = Field(default=0, ge=0, le=4)
    hand_doubled: bool = False
    mode: ProductMode = ProductMode.REVIEW
    meta: Meta = Field(default_factory=Meta)


class BlackjackTrainRequest(BaseModel):
    mode: Literal["review", "trainer"] = "review"
    scenario_index: int | None = Field(default=None, ge=0)
    chosen_action: BlackjackAction | None = None

    product_mode: ProductMode = ProductMode.REVIEW
    meta: Meta = Field(default_factory=Meta)

    # review-mode payload (same meaning as /analyze/blackjack)
    player_hand: list[CardToken] | None = None
    dealer_upcard: CardToken | None = None
    rules: BlackjackRules = Field(default_factory=BlackjackRules)
    allowed_actions: list[BlackjackAction] | None = None
    split_count: int = Field(default=0, ge=0, le=4)
    hand_doubled: bool = False

    @model_validator(mode="after")
    def _validate_by_mode(self) -> "BlackjackTrainRequest":
        if self.mode == "review":
            if not self.player_hand:
                raise ValueError("review mode requires player_hand")
            if not self.dealer_upcard:
                raise ValueError("review mode requires dealer_upcard")
        return self
