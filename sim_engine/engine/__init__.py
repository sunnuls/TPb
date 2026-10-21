"""
Minimal engine surface restored from coach_app for sim_engine consumers.

Provides Range Model v0 + Monte Carlo equity + Street/Position enums
without depending on the deleted coach_app package.
"""

from __future__ import annotations

from enum import Enum

from sim_engine.engine.range import Range
from sim_engine.engine.simulation_equity import (
    EquityResult,
    calculate_monte_carlo_equity,
)

__all__ = [
    "Range",
    "EquityResult",
    "calculate_monte_carlo_equity",
    "Street",
    "Position",
    "PokerActionType",
]


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class Position(str, Enum):
    UTG = "UTG"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class PokerActionType(str, Enum):
    fold = "fold"
    check = "check"
    call = "call"
    bet = "bet"
    raise_ = "raise"
    all_in = "all_in"
