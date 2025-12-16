from __future__ import annotations

from dataclasses import dataclass

from coach_app.schemas.poker import PokerActionType, Position


RANKS = "23456789TJQKA"
RANK_TO_I = {r: i for i, r in enumerate(RANKS, start=2)}


def _hand_notation(c1: str, c2: str, suited: bool) -> str:
    # ranks only (e.g. "A", "K")
    r1, r2 = c1, c2
    if RANK_TO_I[r2] > RANK_TO_I[r1]:
        r1, r2 = r2, r1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{'s' if suited else 'o'}"


@dataclass(frozen=True)
class PreflopPlan:
    action: PokerActionType
    sizing_bb: float | None
    confidence: float
    notes: list[str]


def recommend_preflop(
    *,
    hero_hand: str | None,
    hero_pos: Position | None,
    has_aggression: bool,
    game_type: str,
) -> PreflopPlan:
    """
    Deterministic, minimal preflop heuristic for 6-max.
    Uses simple placeholder ranges; NOT meant to be solver-accurate.
    """
    if hero_hand is None:
        return PreflopPlan(
            action=PokerActionType.check,
            sizing_bb=None,
            confidence=0.15,
            notes=["Preflop: неизвестны карты героя -> даю нейтральную линию (check)"],
        )

    pos = hero_pos or Position.CO
    notes: list[str] = [f"Preflop heuristic for {pos.value} ({game_type})."]

    # Placeholder tiers (very simple)
    premium = {"AA", "KK", "QQ", "JJ", "AKs", "AKo"}
    strong = premium | {"TT", "AQs", "AQo", "AJs", "KQs"}
    playable = strong | {"99", "88", "77", "ATs", "KJs", "QJs", "JTs", "T9s", "A5s"}

    # Position-adjust: tighter early, looser late
    if pos in (Position.UTG, Position.HJ):
        open_range = strong
        call_vs_raise = {"AQs", "AJs", "KQs", "TT", "99"}
        threebet = premium
    elif pos == Position.CO:
        open_range = playable
        call_vs_raise = {"AJs", "AQs", "KQs", "TT", "99", "88", "ATs"}
        threebet = premium | {"AQo", "AQs", "JJ"}
    else:  # BTN/SB/BB default (BB handled elsewhere, but keep simple)
        open_range = playable | {"66", "55", "A9s", "KTs", "QTs", "98s"}
        call_vs_raise = {"AJs", "ATs", "KQs", "KJs", "QJs", "JTs", "TT", "99", "88"}
        threebet = premium | {"AQs", "AQo", "JJ", "TT"}

    if not has_aggression:
        if hero_hand in open_range:
            size = 2.2 if pos == Position.BTN else 2.5
            return PreflopPlan(
                action=PokerActionType.raise_,
                sizing_bb=size,
                confidence=0.65,
                notes=notes + [f"RFI: {hero_hand} in open_range (placeholder)."],
            )
        return PreflopPlan(
            action=PokerActionType.fold,
            sizing_bb=None,
            confidence=0.7,
            notes=notes + [f"RFI: {hero_hand} not in open_range (placeholder)."],
        )

    # Facing aggression
    if hero_hand in threebet:
        return PreflopPlan(
            action=PokerActionType.raise_,
            sizing_bb=7.5,
            confidence=0.6,
            notes=notes + [f"Vs raise: {hero_hand} in 3bet tier (placeholder)."],
        )
    if hero_hand in call_vs_raise:
        return PreflopPlan(
            action=PokerActionType.call,
            sizing_bb=None,
            confidence=0.5,
            notes=notes + [f"Vs raise: {hero_hand} in call tier (placeholder)."],
        )
    return PreflopPlan(
        action=PokerActionType.fold,
        sizing_bb=None,
        confidence=0.65,
        notes=notes + [f"Vs raise: {hero_hand} not in defend tiers (placeholder)."],
    )


def hole_cards_to_notation(rank1: str, rank2: str, suited: bool) -> str:
    return _hand_notation(rank1, rank2, suited)


