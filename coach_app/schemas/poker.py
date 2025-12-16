from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from coach_app.schemas.common import Card, Confidence, Street


class PokerActionType(str, Enum):
    fold = "fold"
    check = "check"
    call = "call"
    bet = "bet"
    raise_ = "raise"
    all_in = "all_in"


class Position(str, Enum):
    # 6-max
    UTG = "UTG"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class PlayerSeat(BaseModel):
    seat_no: int = Field(..., ge=1, le=10)
    name: str | None = None
    stack: float = Field(..., ge=0.0)
    position: Position | None = None
    in_hand: bool = True
    is_hero: bool = False
    confidence: Confidence = Field(default_factory=lambda: Confidence(value=1.0, source="engine"))


class PokerGameType(str, Enum):
    NLHE_6MAX_CASH = "NLHE_6max_cash"
    NLHE_MTT = "NLHE_MTT"


class PokerGameState(BaseModel):
    game_type: PokerGameType
    street: Street
    players: list[PlayerSeat]

    small_blind: float = Field(..., ge=0.0)
    big_blind: float = Field(..., ge=0.0)
    ante: float = Field(default=0.0, ge=0.0)

    pot: float = Field(..., ge=0.0)
    hero_hole: list[Card] = Field(default_factory=list, max_length=2)
    board: list[Card] = Field(default_factory=list, max_length=5)

    to_act_seat_no: int | None = Field(default=None, ge=1, le=10)
    last_aggressive_action: Literal["none", "bet", "raise"] = "none"

    confidence: Confidence = Field(default_factory=lambda: Confidence(value=1.0, source="engine"))

    @model_validator(mode="after")
    def _basic_consistency(self) -> "PokerGameState":
        # Keep this lightweight; heavier checks live in state.validate
        if self.small_blind > self.big_blind and self.big_blind > 0:
            raise ValueError("small_blind cannot exceed big_blind")
        if self.street == Street.PREFLOP and len(self.board) != 0:
            raise ValueError("board must be empty preflop")
        if self.street == Street.FLOP and len(self.board) not in (0, 3):
            raise ValueError("flop street must have 3 board cards (or 0 if unknown)")
        if self.street == Street.TURN and len(self.board) not in (0, 4):
            raise ValueError("turn street must have 4 board cards (or 0 if unknown)")
        if self.street == Street.RIVER and len(self.board) not in (0, 5):
            raise ValueError("river street must have 5 board cards (or 0 if unknown)")
        return self


class PokerDecision(BaseModel):
    action: PokerActionType
    sizing: float | None = Field(default=None, ge=0.0, description="Bet/raise size (BBs or chips per normalize)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_facts: dict = Field(default_factory=dict)


class PokerAnalyzeRequest(BaseModel):
    hand_history_text: str = Field(..., min_length=1)
    game_type: PokerGameType = PokerGameType.NLHE_6MAX_CASH


class PokerTrainRequest(BaseModel):
    # Minimal trainer stub; in real trainer you’d store sessions and difficulty.
    hand_history_text: str = Field(..., min_length=1)
    mode: Literal["review", "trainer"] = "review"
    game_type: PokerGameType = PokerGameType.NLHE_6MAX_CASH


