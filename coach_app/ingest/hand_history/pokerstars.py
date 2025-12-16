from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from coach_app.schemas.common import Card, Street
from coach_app.schemas.ingest import ParseReport
from coach_app.schemas.poker import (
    PlayerSeat,
    PokerGameState,
    PokerGameType,
    Position,
)


_RE_SEAT = re.compile(r"^Seat\s+(?P<seat>\d+):\s+(?P<name>.+?)\s+\((?P<stack>[\d\.]+)\s+in\s+chips\)")
_RE_BUTTON = re.compile(r"Seat\s+#(?P<seat>\d+)\s+is\s+the\s+button")
_RE_DEALT = re.compile(r"^Dealt\s+to\s+(?P<hero>.+?)\s+\[(?P<c1>.{2})\s+(?P<c2>.{2})\]")
_RE_FLOP = re.compile(r"^\*\*\*\s+FLOP\s+\*\*\*\s+\[(?P<b1>.{2})\s+(?P<b2>.{2})\s+(?P<b3>.{2})\]")
_RE_TURN = re.compile(r"^\*\*\*\s+TURN\s+\*\*\*\s+\[.+\]\s+\[(?P<bt>.{2})\]")
_RE_RIVER = re.compile(r"^\*\*\*\s+RIVER\s+\*\*\*\s+\[.+\]\s+\[(?P<br>.{2})\]")
_RE_TOTAL_POT = re.compile(r"^Total\s+pot\s+(?P<amt>[\d\.]+)", re.IGNORECASE)

_AMT = r"[\$€£]?(?P<amt>[\d]+(?:\.[\d]+)?)"
_RE_POSTS_SB = re.compile(rf"^(?P<name>.+?):\s+posts\s+small\s+blind\s+{_AMT}$")
_RE_POSTS_BB = re.compile(rf"^(?P<name>.+?):\s+posts\s+big\s+blind\s+{_AMT}$")
_RE_POSTS_ANTE = re.compile(rf"^(?P<name>.+?):\s+posts\s+the\s+ante\s+{_AMT}$")

_RE_BETS = re.compile(rf"^(?P<name>.+?):\s+bets\s+[\$€£]?(?P<amt>[\d]+(?:\.[\d]+)?)")
_RE_CALLS = re.compile(rf"^(?P<name>.+?):\s+calls\s+[\$€£]?(?P<amt>[\d]+(?:\.[\d]+)?)")
_RE_RAISES = re.compile(
    rf"^(?P<name>.+?):\s+raises\s+[\$€£]?(?P<from>[\d]+(?:\.[\d]+)?)\s+to\s+[\$€£]?(?P<to>[\d]+(?:\.[\d]+)?)"
)
_RE_CHECKS = re.compile(r"^(?P<name>.+?):\s+checks$")
_RE_FOLDS = re.compile(r"^(?P<name>.+?):\s+folds$")


@dataclass
class _ActionEvent:
    street: Street
    actor: str
    kind: str
    amount: float | None = None
    to_amount: float | None = None


def _detect_game_type(text: str) -> PokerGameType:
    t = text.lower()
    if "tournament" in t or "level" in t or "ante" in t:
        return PokerGameType.NLHE_MTT
    return PokerGameType.NLHE_6MAX_CASH


def _assign_positions(players: list[PlayerSeat], button_seat: int | None) -> None:
    # Only meaningful for up to 6 players in this MVP.
    if button_seat is None:
        return
    seat_to_player = {p.seat_no: p for p in players}
    seats_sorted = sorted(seat_to_player.keys())
    if button_seat not in seat_to_player:
        return

    # Build clockwise order starting from BTN.
    start_idx = seats_sorted.index(button_seat)
    order = seats_sorted[start_idx:] + seats_sorted[:start_idx]

    # 6-max mapping in clockwise order starting at BTN.
    mapping = [Position.BTN, Position.SB, Position.BB, Position.UTG, Position.HJ, Position.CO]
    for i, seat in enumerate(order[: len(mapping)]):
        seat_to_player[seat].position = mapping[i]


def _parse_cards(*cards: str) -> list[Card]:
    out: list[Card] = []
    for c in cards:
        out.append(Card.from_str(c))
    return out


class PokerStarsHandHistoryParser:
    room = "pokerstars"

    def parse(self, hand_history_text: str) -> tuple[PokerGameState, ParseReport]:
        warnings: list[str] = []
        missing: list[str] = []

        game_type = _detect_game_type(hand_history_text)

        # Parse seats and button.
        players: list[PlayerSeat] = []
        button_seat: int | None = None
        hero_name: str | None = None
        hero_hole: list[Card] = []
        board: list[Card] = []

        sb = bb = ante = 0.0
        total_pot_line: float | None = None

        # Action parsing: we compute pot/to_call at hero's first decision on the latest street where hero acts.
        street = Street.PREFLOP
        actions: list[_ActionEvent] = []

        for raw in hand_history_text.splitlines():
            line = raw.strip()
            if not line:
                continue

            m = _RE_BUTTON.search(line)
            if m:
                button_seat = int(m.group("seat"))
                continue

            m = _RE_SEAT.match(line)
            if m:
                players.append(
                    PlayerSeat(
                        seat_no=int(m.group("seat")),
                        name=m.group("name"),
                        stack=float(m.group("stack")),
                    )
                )
                continue

            m = _RE_DEALT.match(line)
            if m:
                hero_name = m.group("hero").strip()
                hero_hole = _parse_cards(m.group("c1"), m.group("c2"))
                continue

            if line.startswith("*** FLOP ***"):
                street = Street.FLOP
                m = _RE_FLOP.match(line)
                if m:
                    board = _parse_cards(m.group("b1"), m.group("b2"), m.group("b3"))
                continue
            if line.startswith("*** TURN ***"):
                street = Street.TURN
                m = _RE_TURN.match(line)
                if m:
                    if len(board) >= 3:
                        board = board[:3] + _parse_cards(m.group("bt"))
                continue
            if line.startswith("*** RIVER ***"):
                street = Street.RIVER
                m = _RE_RIVER.match(line)
                if m:
                    if len(board) >= 4:
                        board = board[:4] + _parse_cards(m.group("br"))
                continue

            m = _RE_TOTAL_POT.match(line)
            if m:
                try:
                    total_pot_line = float(m.group("amt"))
                except Exception:
                    warnings.append(f"Не удалось распарсить Total pot из строки: {line!r}")
                continue

            # Posts
            m = _RE_POSTS_SB.match(line)
            if m:
                sb = float(m.group("amt"))
                actions.append(_ActionEvent(Street.PREFLOP, m.group("name"), "post_sb", amount=sb))
                continue
            m = _RE_POSTS_BB.match(line)
            if m:
                bb = float(m.group("amt"))
                actions.append(_ActionEvent(Street.PREFLOP, m.group("name"), "post_bb", amount=bb))
                continue
            m = _RE_POSTS_ANTE.match(line)
            if m:
                ante = float(m.group("amt"))
                actions.append(_ActionEvent(Street.PREFLOP, m.group("name"), "post_ante", amount=ante))
                continue

            # Actions
            m = _RE_FOLDS.match(line)
            if m:
                actions.append(_ActionEvent(street, m.group("name"), "fold"))
                continue
            m = _RE_CHECKS.match(line)
            if m:
                actions.append(_ActionEvent(street, m.group("name"), "check"))
                continue
            m = _RE_CALLS.match(line)
            if m:
                actions.append(_ActionEvent(street, m.group("name"), "call", amount=float(m.group("amt"))))
                continue
            m = _RE_BETS.match(line)
            if m:
                actions.append(_ActionEvent(street, m.group("name"), "bet", amount=float(m.group("amt"))))
                continue
            m = _RE_RAISES.match(line)
            if m:
                actions.append(
                    _ActionEvent(
                        street,
                        m.group("name"),
                        "raise",
                        amount=float(m.group("from")),
                        to_amount=float(m.group("to")),
                    )
                )
                continue

        if not players:
            missing.append("players")
        if hero_name is None:
            missing.append("hero_name")
        if len(hero_hole) != 2:
            missing.append("hero_hole")
        if bb <= 0:
            missing.append("big_blind")
        if sb <= 0:
            missing.append("small_blind")

        # Mark hero in players if known.
        hero_seat: int | None = None
        if hero_name:
            for p in players:
                if p.name == hero_name:
                    p.is_hero = True
                    hero_seat = p.seat_no
                    break
        if hero_seat is None and players:
            # Fallback: first seat is hero (low confidence).
            players[0].is_hero = True
            hero_seat = players[0].seat_no
            warnings.append("Hero name not matched to seats; assumed Seat 1 is hero")

        _assign_positions(players, button_seat)

        # Compute pot and to_call at hero's first action on the latest street where hero acts.
        pot_at_hero: float | None = None
        to_call_at_hero: float | None = None
        decision_street: Street = Street.PREFLOP

        if hero_name:
            pot_at_hero, to_call_at_hero, decision_street = _compute_pot_and_to_call(
                actions, hero_name, fallback_street=street
            )
        else:
            # Still compute pot from all forced bets if any.
            pot_at_hero = _sum_forced(actions)
            to_call_at_hero = None
            decision_street = street
            warnings.append("Hero name unknown; cannot compute to_call")

        # Confidence: start at 0.9 and subtract for missing key fields.
        conf = 0.9
        conf -= 0.25 if "hero_hole" in missing else 0.0
        conf -= 0.15 if "players" in missing else 0.0
        conf -= 0.15 if "big_blind" in missing else 0.0
        conf = max(0.0, min(1.0, conf))

        # State.pot must be >=0; if unknown, store 0 with missing flag.
        pot_for_state = float(pot_at_hero) if pot_at_hero is not None else 0.0
        if pot_at_hero is None:
            missing.append("pot")

        state = PokerGameState(
            game_type=game_type,
            street=decision_street,
            players=players,
            small_blind=sb if sb > 0 else 0.0,
            big_blind=bb if bb > 0 else 0.0,
            ante=ante if ante > 0 else 0.0,
            pot=pot_for_state,
            hero_hole=hero_hole,
            board=board,
            to_act_seat_no=hero_seat,
            last_aggressive_action="raise" if any(a.kind in ("bet", "raise") for a in actions if a.street == decision_street) else "none",
            confidence={"value": conf, "source": "hand_history", "notes": warnings},
        )

        report = ParseReport(
            parser="PokerStarsHandHistoryParser",
            room="pokerstars",
            game_type_detected=game_type.value if game_type else "unknown",
            confidence=conf,
            missing_fields=sorted(set(missing)),
            warnings=warnings,
            parsed={
                "hero_name": hero_name,
                "hero_hand": [str(c) for c in hero_hole],
                "board": [str(c) for c in board],
                "street": decision_street.value,
                "pot": pot_at_hero,
                "total_pot": total_pot_line,
                "to_call": to_call_at_hero,
                "button_seat": button_seat,
            },
        )
        return state, report


def _sum_forced(actions: Iterable[_ActionEvent]) -> float:
    pot = 0.0
    for a in actions:
        if a.kind in ("post_sb", "post_bb", "post_ante") and a.amount is not None:
            pot += float(a.amount)
    return pot


def _compute_pot_and_to_call(
    actions: list[_ActionEvent], hero_name: str, *, fallback_street: Street
) -> tuple[float | None, float | None, Street]:
    """
    Walk actions and compute:
    - pot size (sum of contributions) right before hero's first action on the latest street where hero acts
    - to_call at that moment
    """
    # Identify the latest street where hero appears.
    hero_streets = [
        a.street for a in actions if a.actor == hero_name and a.kind in ("fold", "check", "call", "bet", "raise")
    ]
    decision_street = hero_streets[-1] if hero_streets else fallback_street

    invested: dict[str, float] = {}
    current_bet = 0.0
    pot = 0.0
    street = Street.PREFLOP

    def reset_street():
        nonlocal invested, current_bet
        invested = {}
        current_bet = 0.0

    reset_street()

    for a in actions:
        if a.street != street:
            street = a.street
            reset_street()

        # If this is hero's first action on decision_street, snapshot before applying.
        if a.street == decision_street and a.actor == hero_name and a.kind in ("fold", "check", "call", "bet", "raise"):
            to_call = max(0.0, current_bet - invested.get(hero_name, 0.0))
            return pot, to_call, decision_street

        # Apply action to pot/invested
        actor = a.actor
        invested.setdefault(actor, 0.0)

        if a.kind in ("post_sb", "post_bb", "post_ante"):
            if a.amount is None:
                continue
            invested[actor] += float(a.amount)
            pot += float(a.amount)
            if a.kind == "post_bb":
                current_bet = max(current_bet, invested[actor])
            continue

        if a.kind == "call":
            if a.amount is None:
                continue
            invested[actor] += float(a.amount)
            pot += float(a.amount)
            continue

        if a.kind == "bet":
            if a.amount is None:
                continue
            # bet sets the street bet size to amount
            add = float(a.amount) - invested[actor]
            if add < 0:
                add = 0.0
            invested[actor] += add
            pot += add
            current_bet = max(current_bet, invested[actor])
            continue

        if a.kind == "raise":
            if a.to_amount is None:
                continue
            target = float(a.to_amount)
            add = target - invested[actor]
            if add < 0:
                add = 0.0
            invested[actor] = target
            pot += add
            current_bet = max(current_bet, target)
            continue

        # check/fold add nothing

    # If hero never acted, return pot and unknown to_call at fallback street.
    return pot if pot > 0 else None, None, decision_street


