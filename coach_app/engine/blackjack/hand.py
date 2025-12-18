from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


HandType = Literal["hard", "soft", "pair"]


@dataclass(frozen=True)
class HandInfo:
    hand_type: HandType
    total: int
    is_blackjack: bool
    is_bust: bool
    is_pair: bool
    soft: bool


def _rank(token: str) -> str:
    return str(token)[0].upper()


def _value(rank: str) -> int:
    if rank in ("T", "J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    try:
        return int(rank)
    except Exception:
        return 0


def hand_total(hand_cards: list[str]) -> int:
    # Best total <= 21 if possible.
    ranks = [_rank(c) for c in hand_cards]
    values = [_value(r) for r in ranks]
    total = sum(values)
    aces = sum(1 for r in ranks if r == "A")

    # Convert A from 11 to 1 until <= 21
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def _is_soft(hand_cards: list[str]) -> bool:
    # Soft if at least one Ace can be counted as 11 without busting.
    ranks = [_rank(c) for c in hand_cards]
    non_ace_total = sum(_value(r) for r in ranks if r != "A")
    ace_count = sum(1 for r in ranks if r == "A")
    if ace_count == 0:
        return False

    # Count one Ace as 11 and others as 1.
    total = non_ace_total + 11 + (ace_count - 1)
    return total <= 21


def is_blackjack(hand_cards: list[str]) -> bool:
    if len(hand_cards) != 2:
        return False
    ranks = {_rank(c) for c in hand_cards}
    if "A" not in ranks:
        return False
    other = (ranks - {"A"}).pop() if len(ranks) == 2 else None
    return other in ("T", "J", "Q", "K")


def is_bust(hand_cards: list[str]) -> bool:
    # Bust if even minimal Ace-as-1 total exceeds 21
    ranks = [_rank(c) for c in hand_cards]
    total = 0
    for r in ranks:
        if r == "A":
            total += 1
        else:
            total += _value(r)
    return total > 21


def classify_hand(hand_cards: list[str]) -> HandInfo:
    pair = len(hand_cards) == 2 and _rank(hand_cards[0]) == _rank(hand_cards[1])
    bj = is_blackjack(hand_cards)
    bust = is_bust(hand_cards)
    total = hand_total(hand_cards)
    soft = _is_soft(hand_cards)
    if pair:
        ht: HandType = "pair"
    else:
        ht = "soft" if soft else "hard"

    return HandInfo(hand_type=ht, total=total, is_blackjack=bj, is_bust=bust, is_pair=pair, soft=soft)


def classify_split_hands(split_hands: list[list[str]]) -> list[HandInfo]:
    return [classify_hand(h) for h in split_hands]
