from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from coach_app.schemas.common import Card, Street


def infer_current_street(state: Any) -> Street:
    if state is None:
        return Street.FLOP

    st = getattr(state, "street", None)
    if isinstance(st, Street):
        return st
    if isinstance(st, str):
        try:
            return Street(st.lower().strip())
        except Exception:
            pass

    if isinstance(state, Mapping):
        raw = state.get("street")
        if isinstance(raw, Street):
            return raw
        if isinstance(raw, str):
            try:
                return Street(raw.lower().strip())
            except Exception:
                pass
        board = state.get("board")
    else:
        board = getattr(state, "board", None)

    cards = _normalize_cards(board)
    if len(cards) >= 5:
        return Street.RIVER
    if len(cards) == 4:
        return Street.TURN
    if len(cards) == 3:
        return Street.FLOP
    return Street.PREFLOP


def previous_street_action_summary(
    state: Any,
    *,
    action_history: list[Mapping[str, Any]] | None = None,
    hero_name: str | None = None,
) -> dict[str, Any]:
    if action_history is None:
        if isinstance(state, Mapping):
            raw = state.get("action_history")
        else:
            raw = getattr(state, "action_history", None)
        action_history = raw if isinstance(raw, list) else None

    cur = infer_current_street(state)
    prev = _previous_street(cur)

    if not action_history or prev is None:
        return {
            "previous_street": prev.value if prev else None,
            "actions": 0,
            "had_aggression": None,
            "checked_through": None,
            "last_aggressor": None,
            "hero_aggressor": None,
        }

    def st(x: Any) -> str:
        return str(x).lower().strip()

    prev_actions = [a for a in action_history if st(a.get("street")) == prev.value]
    aggr = [a for a in prev_actions if st(a.get("kind")) in ("bet", "raise")]
    last_aggr = str(aggr[-1].get("actor")) if aggr else None

    hero_aggr = None
    if hero_name and aggr:
        hero_aggr = any(str(a.get("actor")) == hero_name for a in aggr)

    checked_through = bool(prev_actions) and not bool(aggr)

    return {
        "previous_street": prev.value,
        "actions": len(prev_actions),
        "had_aggression": bool(aggr),
        "checked_through": checked_through,
        "last_aggressor": last_aggr,
        "hero_aggressor": hero_aggr,
    }


def runout_change(
    *,
    board_before: list[Any] | None,
    board_after: list[Any] | None,
) -> dict[str, Any] | None:
    before = _normalize_cards(board_before)
    after = _normalize_cards(board_after)

    if len(after) <= len(before) or not after:
        return None

    new_card = after[-1]

    paired = any(c.rank == new_card.rank for c in before)

    suits_before = Counter(c.suit.value for c in before)
    suits_after = Counter(c.suit.value for c in after)
    max_before = max(suits_before.values(), default=0)
    max_after = max(suits_after.values(), default=0)

    flush_intensified = max_after > max_before

    vb = [_rank_value(c) for c in before]
    va = _rank_value(new_card)
    overcard = bool(vb) and va > max(vb)

    connects = bool(vb) and min(abs(va - v) for v in vb) <= 4

    return {
        "card": str(new_card),
        "paired": paired,
        "flush_intensified": flush_intensified,
        "overcard": overcard,
        "connects": connects,
    }


def _normalize_cards(cards: Any) -> list[Card]:
    if not isinstance(cards, list):
        return []

    out: list[Card] = []
    for c in cards:
        if isinstance(c, Card):
            out.append(c)
        elif isinstance(c, str):
            try:
                out.append(Card.from_str(c))
            except Exception:
                continue
    return out


def _previous_street(street: Street) -> Street | None:
    if street == Street.RIVER:
        return Street.TURN
    if street == Street.TURN:
        return Street.FLOP
    if street == Street.FLOP:
        return Street.PREFLOP
    return None


def _rank_value(card: Card) -> int:
    ranks = "23456789TJQKA"
    try:
        return ranks.index(card.rank) + 2
    except Exception:
        return 0
