from __future__ import annotations

from dataclasses import dataclass

from coach_app.engine.poker.hand_strength import compute_hand_strength
from coach_app.schemas.common import Street
from coach_app.schemas.poker import PokerActionType, PokerDecision, PokerGameState, Position


@dataclass(frozen=True)
class EngineContext:
    hero_position: Position | None
    street: Street


def _hand_code(state: PokerGameState) -> str | None:
    if len(state.hero_hole) != 2:
        return None
    c1, c2 = state.hero_hole
    ranks = [c1.rank, c2.rank]
    # order by rank value (A high)
    order = "23456789TJQKA"
    ranks_sorted = sorted(ranks, key=lambda r: order.index(r), reverse=True)
    if ranks_sorted[0] == ranks_sorted[1]:
        return f"{ranks_sorted[0]}{ranks_sorted[1]}"
    suited = c1.suit == c2.suit
    return f"{ranks_sorted[0]}{ranks_sorted[1]}{'s' if suited else 'o'}"


def _hero_position(state: PokerGameState) -> Position | None:
    for p in state.players:
        if p.is_hero:
            return p.position
    return None


def _preflop_ranges(pos: Position) -> tuple[set[str], set[str], set[str]]:
    """
    Deterministic placeholder ranges:
    - open: RFI
    - call vs open
    - 3bet vs open
    """
    premiums = {"AA", "KK", "QQ", "JJ", "AKs", "AKo"}
    strong = {"TT", "AQs", "AQo", "AJs", "KQs"}
    playable = {"99", "88", "77", "ATs", "KJs", "QJs", "JTs", "T9s", "A5s"}

    if pos in (Position.UTG, Position.HJ):
        open_ = premiums | strong | {"AJo", "KQo"} | {"66", "55", "44"} | {"KJs"}
        call_ = {"QQ", "JJ", "TT", "AQs", "AJs", "KQs", "99"}
        threebet_ = premiums | {"AQs", "AKs", "AKo"}
    elif pos in (Position.CO, Position.BTN):
        open_ = premiums | strong | playable | {"66", "55", "44", "33", "22"} | {"KQo", "QTs", "98s"}
        call_ = strong | {"99", "88", "77", "AJo", "KQo"}
        threebet_ = premiums | {"AQs", "A5s", "KQs"}
    else:  # blinds (simplified)
        open_ = premiums | strong | playable
        call_ = playable | {"AQo", "AJo", "KQo", "TT", "99"}
        threebet_ = premiums | {"AQs", "AKo", "KQs"}

    return open_, call_, threebet_


def recommend(state: PokerGameState, *, to_call: float | None = None) -> PokerDecision:
    """
    MVP deterministic poker decision:
    - preflop: simple position-based heuristics
    - postflop: pot_odds + simplified strength category

    `to_call` is the amount hero needs to call at decision point if known.
    """
    ctx = EngineContext(hero_position=_hero_position(state), street=state.street)
    hand = _hand_code(state)

    notes: list[str] = []
    conf = 0.75
    if hand is None:
        conf -= 0.35
        notes.append("Карты героя не распознаны (hero_hole).")
    if ctx.hero_position is None and state.street == Street.PREFLOP:
        conf -= 0.1
        notes.append("Позиция героя не распознана; используется консервативная логика.")

    pot = state.pot if state.pot > 0 else None
    pot_odds: float | None = None
    if pot is not None and to_call is not None and to_call > 0:
        pot_odds = float(to_call) / float(pot + to_call)
    elif to_call is None:
        notes.append("to_call неизвестен; pot_odds не рассчитывается.")
        conf -= 0.1
    elif pot is None:
        notes.append("pot неизвестен; pot_odds не рассчитывается.")
        conf -= 0.1

    # Build key facts (required set)
    key_facts: dict = {
        "street": state.street.value,
        "pot": pot,
        "to_call": to_call,
        "pot_odds": pot_odds,
        "hero_hand": [str(c) for c in state.hero_hole],
        "board": [str(c) for c in state.board],
        "hand_category": None,
        "range_summary": "Placeholder диапазоны: базовые 6-max эвристики (RFI/call/3bet).",
        "combos_summary": "Placeholder: упрощённая оценка силы руки/дро по карте стола.",
        "notes": notes,
    }

    # PRE-FLOP
    if state.street == Street.PREFLOP:
        pos = ctx.hero_position or Position.CO
        open_range, call_range, threebet_range = _preflop_ranges(pos)
        facing_raise = state.last_aggressive_action in ("bet", "raise")

        if hand is None:
            action = PokerActionType.fold
            conf = max(0.0, conf)
            return PokerDecision(action=action, sizing=None, confidence=max(0.0, min(1.0, conf)), key_facts=key_facts)

        if not facing_raise:
            if hand in open_range:
                key_facts["hand_category"] = "preflop_open"
                return PokerDecision(
                    action=PokerActionType.raise_,
                    sizing=2.5 if state.big_blind > 0 else None,
                    confidence=max(0.0, min(1.0, conf)),
                    key_facts=key_facts,
                )
            key_facts["hand_category"] = "preflop_fold"
            return PokerDecision(
                action=PokerActionType.fold,
                sizing=None,
                confidence=max(0.0, min(1.0, conf - 0.15)),
                key_facts=key_facts,
            )

        # Facing a raise: 3bet / call / fold
        if hand in threebet_range:
            key_facts["hand_category"] = "preflop_3bet"
            return PokerDecision(
                action=PokerActionType.raise_,
                sizing=8.0 if state.big_blind > 0 else None,
                confidence=max(0.0, min(1.0, conf)),
                key_facts=key_facts,
            )
        if hand in call_range:
            key_facts["hand_category"] = "preflop_call"
            return PokerDecision(
                action=PokerActionType.call,
                sizing=None,
                confidence=max(0.0, min(1.0, conf - 0.05)),
                key_facts=key_facts,
            )
        key_facts["hand_category"] = "preflop_fold_vs_raise"
        return PokerDecision(
            action=PokerActionType.fold,
            sizing=None,
            confidence=max(0.0, min(1.0, conf - 0.15)),
            key_facts=key_facts,
        )

    # POST-FLOP+
    strength = compute_hand_strength(state.hero_hole, state.board)
    key_facts["hand_category"] = strength.category
    if strength.notes:
        notes.extend(strength.notes)

    # If to_call unknown: default conservative
    if to_call is None:
        return PokerDecision(
            action=PokerActionType.check,
            sizing=None,
            confidence=max(0.0, min(1.0, conf - 0.25)),
            key_facts=key_facts,
        )

    # If facing a bet and to_call > 0
    if to_call > 0:
        if strength.category in ("two_pair", "set", "straight", "flush", "full_house", "quads", "overpair", "top_pair"):
            # Raise for value (deterministic)
            sizing = float(to_call) * 3.0
            notes.append("Сильная рука: выбираем вэлью-рейз (MVP эвристика).")
            return PokerDecision(
                action=PokerActionType.raise_,
                sizing=sizing,
                confidence=max(0.0, min(1.0, conf)),
                key_facts=key_facts,
            )
        if strength.is_draw:
            if pot_odds is not None and pot_odds <= 0.35:
                notes.append("Дро: колл при приемлемых pot_odds (MVP).")
                return PokerDecision(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=max(0.0, min(1.0, conf - 0.05)),
                    key_facts=key_facts,
                )
            notes.append("Дро: фолд при плохих pot_odds (MVP).")
            return PokerDecision(
                action=PokerActionType.fold,
                sizing=None,
                confidence=max(0.0, min(1.0, conf - 0.05)),
                key_facts=key_facts,
            )
        if strength.category in ("pair",):
            if pot_odds is not None and pot_odds <= 0.25:
                notes.append("Пара: колл при дешёвой цене (MVP).")
                return PokerDecision(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=max(0.0, min(1.0, conf - 0.15)),
                    key_facts=key_facts,
                )
            notes.append("Пара/слабее: фолд при дорогой цене (MVP).")
            return PokerDecision(
                action=PokerActionType.fold,
                sizing=None,
                confidence=max(0.0, min(1.0, conf - 0.15)),
                key_facts=key_facts,
            )

        notes.append("Слабая рука: фолд (MVP).")
        return PokerDecision(
            action=PokerActionType.fold,
            sizing=None,
            confidence=max(0.0, min(1.0, conf - 0.2)),
            key_facts=key_facts,
        )

    # No bet to call: choose bet/check based on strength
    if strength.category in ("two_pair", "set", "straight", "flush", "full_house", "quads", "overpair", "top_pair"):
        sizing = float(state.pot) * 0.66 if state.pot > 0 else None
        notes.append("Когда нет ставки противника: ставим для вэлью/защиты (MVP).")
        return PokerDecision(
            action=PokerActionType.bet,
            sizing=sizing,
            confidence=max(0.0, min(1.0, conf)),
            key_facts=key_facts,
        )
    if strength.is_draw:
        sizing = float(state.pot) * 0.5 if state.pot > 0 else None
        notes.append("Когда нет ставки противника: полублеф (MVP).")
        return PokerDecision(
            action=PokerActionType.bet,
            sizing=sizing,
            confidence=max(0.0, min(1.0, conf - 0.1)),
            key_facts=key_facts,
        )

    return PokerDecision(
        action=PokerActionType.check,
        sizing=None,
        confidence=max(0.0, min(1.0, conf - 0.1)),
        key_facts=key_facts,
    )



