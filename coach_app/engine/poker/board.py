from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from coach_app.schemas.common import Card, RANKS


StraightConnectivity = Literal["low", "medium", "high"]
Dryness = Literal["dry", "semi-wet", "wet"]

RANK_TO_V = {r: i + 2 for i, r in enumerate(RANKS)}


@dataclass(frozen=True)
class BoardTexture:
    is_paired: bool
    is_monotone: bool
    is_two_tone: bool
    straight_connectivity: StraightConnectivity
    dryness: Dryness

    def to_dict(self) -> dict:
        return asdict(self)


def classify_board(board_cards: list[Card]) -> BoardTexture:
    """Deterministic board texture classification (v1)."""
    flop = board_cards[:3] if len(board_cards) >= 3 else board_cards

    if len(flop) < 3:
        return BoardTexture(
            is_paired=False,
            is_monotone=False,
            is_two_tone=False,
            straight_connectivity="low",
            dryness="dry",
        )

    ranks = [c.rank for c in flop]
    suits = [c.suit.value for c in flop]

    is_paired = len(set(ranks)) != len(ranks)

    suit_counts = {s: suits.count(s) for s in set(suits)}
    is_monotone = max(suit_counts.values(), default=0) == 3
    is_two_tone = max(suit_counts.values(), default=0) == 2

    sc = _straight_connectivity(flop)
    dry = _dryness(is_paired=is_paired, is_monotone=is_monotone, is_two_tone=is_two_tone, sc=sc)

    return BoardTexture(
        is_paired=is_paired,
        is_monotone=is_monotone,
        is_two_tone=is_two_tone,
        straight_connectivity=sc,
        dryness=dry,
    )


def _straight_connectivity(cards: list[Card]) -> StraightConnectivity:
    vals = [RANK_TO_V[c.rank] for c in cards]
    uniq = sorted(set(vals))

    best_span = (max(uniq) - min(uniq)) if uniq else 99
    if 14 in uniq:
        uniq_low = sorted(set([1 if v == 14 else v for v in uniq]))
        best_span = min(best_span, max(uniq_low) - min(uniq_low))

    if best_span <= 4:
        return "high"
    if best_span <= 5:
        return "medium"
    return "low"


def _dryness(*, is_paired: bool, is_monotone: bool, is_two_tone: bool, sc: StraightConnectivity) -> Dryness:
    if is_monotone or sc == "high":
        return "wet"
    if is_two_tone or sc == "medium" or is_paired:
        return "semi-wet"
    return "dry"
