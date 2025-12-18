from __future__ import annotations

import re
from dataclasses import dataclass

from coach_app.schemas.common import Card, Street
from coach_app.schemas.ingest import ParseReport
from coach_app.schemas.poker import PlayerSeat, PokerGameState, PokerGameType


_RE_DEALT = re.compile(r"Dealt\s+to\s+(?P<hero>.+?)\s+\[(?P<c1>.{2})\s+(?P<c2>.{2})\]", re.IGNORECASE)
_RE_BOARD_FLOP = re.compile(r"FLOP.*\[(?P<b1>.{2})\s+(?P<b2>.{2})\s+(?P<b3>.{2})\]", re.IGNORECASE)
_RE_BOARD_TURN = re.compile(r"TURN.*\[(?P<bt>.{2})\]", re.IGNORECASE)
_RE_BOARD_RIVER = re.compile(r"RIVER.*\[(?P<br>.{2})\]", re.IGNORECASE)

_RE_POSTS_SB = re.compile(r"(?P<name>.+?):\s+posts\s+small\s+blind\s+(?P<amt>[\d\.]+)", re.IGNORECASE)
_RE_POSTS_BB = re.compile(r"(?P<name>.+?):\s+posts\s+big\s+blind\s+(?P<amt>[\d\.]+)", re.IGNORECASE)
_RE_POSTS_ANTE = re.compile(r"(?P<name>.+?):\s+posts\s+.*ante\s+(?P<amt>[\d\.]+)", re.IGNORECASE)

_RE_CALLS = re.compile(r"(?P<name>.+?):\s+calls\s+(?P<amt>[\d\.]+)", re.IGNORECASE)
_RE_BETS = re.compile(r"(?P<name>.+?):\s+bets\s+(?P<amt>[\d\.]+)", re.IGNORECASE)
_RE_RAISES = re.compile(r"(?P<name>.+?):\s+raises\s+(?P<from>[\d\.]+)\s+to\s+(?P<to>[\d\.]+)", re.IGNORECASE)
_RE_CHECKS = re.compile(r"(?P<name>.+?):\s+checks\s*$", re.IGNORECASE)
_RE_FOLDS = re.compile(r"(?P<name>.+?):\s+folds\s*$", re.IGNORECASE)


@dataclass
class _Action:
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


def _parse_cards(*cards: str) -> list[Card]:
    return [Card.from_str(c) for c in cards]


class GenericHandHistoryParser:
    """
    Generic fallback parser:
    attempts to parse hero hand, board, blinds/antes and basic action lines with amounts.

    This parser is conservative: it will not guess missing values silently.
    """

    room = "generic"

    def parse(self, hand_history_text: str) -> tuple[PokerGameState, ParseReport]:
        warnings: list[str] = []
        missing: list[str] = []

        game_type = _detect_game_type(hand_history_text)

        hero_name: str | None = None
        hero_hole: list[Card] = []
        board: list[Card] = []
        sb = bb = ante = 0.0

        street = Street.PREFLOP
        actions: list[_Action] = []

        names_seen: set[str] = set()

        for raw in hand_history_text.splitlines():
            line = raw.strip()
            if not line:
                continue

            m = _RE_DEALT.search(line)
            if m and not hero_hole:
                hero_name = m.group("hero").strip()
                hero_hole = _parse_cards(m.group("c1"), m.group("c2"))
                names_seen.add(hero_name)
                continue

            # Board / street
            if "FLOP" in line.upper():
                street = Street.FLOP
                m = _RE_BOARD_FLOP.search(line)
                if m:
                    board = _parse_cards(m.group("b1"), m.group("b2"), m.group("b3"))
                continue
            if "TURN" in line.upper():
                street = Street.TURN
                m = _RE_BOARD_TURN.search(line)
                if m and len(board) >= 3:
                    board = board[:3] + _parse_cards(m.group("bt"))
                continue
            if "RIVER" in line.upper():
                street = Street.RIVER
                m = _RE_BOARD_RIVER.search(line)
                if m and len(board) >= 4:
                    board = board[:4] + _parse_cards(m.group("br"))
                continue

            # forced bets
            m = _RE_POSTS_SB.search(line)
            if m:
                sb = float(m.group("amt"))
                names_seen.add(m.group("name"))
                actions.append(_Action(Street.PREFLOP, m.group("name"), "post_sb", amount=sb))
                continue
            m = _RE_POSTS_BB.search(line)
            if m:
                bb = float(m.group("amt"))
                names_seen.add(m.group("name"))
                actions.append(_Action(Street.PREFLOP, m.group("name"), "post_bb", amount=bb))
                continue
            m = _RE_POSTS_ANTE.search(line)
            if m:
                ante = float(m.group("amt"))
                names_seen.add(m.group("name"))
                actions.append(_Action(Street.PREFLOP, m.group("name"), "post_ante", amount=ante))
                continue

            # actions
            for rx, kind in (
                (_RE_FOLDS, "fold"),
                (_RE_CHECKS, "check"),
                (_RE_CALLS, "call"),
                (_RE_BETS, "bet"),
                (_RE_RAISES, "raise"),
            ):
                m = rx.search(line)
                if not m:
                    continue
                actor = m.group("name").strip()
                names_seen.add(actor)
                if kind == "call":
                    actions.append(_Action(street, actor, "call", amount=float(m.group("amt"))))
                elif kind == "bet":
                    actions.append(_Action(street, actor, "bet", amount=float(m.group("amt"))))
                elif kind == "raise":
                    actions.append(
                        _Action(
                            street,
                            actor,
                            "raise",
                            amount=float(m.group("from")),
                            to_amount=float(m.group("to")),
                        )
                    )
                else:
                    actions.append(_Action(street, actor, kind))
                break

        # minimal players list
        players: list[PlayerSeat] = []
        if hero_name:
            players.append(PlayerSeat(seat_no=1, name=hero_name, stack=0.0, is_hero=True))
        else:
            missing.append("hero_name")
            warnings.append("Не удалось надёжно извлечь имя героя (Dealt to ...)")
            players.append(PlayerSeat(seat_no=1, name="Hero", stack=0.0, is_hero=True))

        if not hero_hole:
            missing.append("hero_hole")
        if bb <= 0:
            missing.append("big_blind")
        if sb <= 0:
            missing.append("small_blind")

        # pot/to_call estimation (best-effort, conservative)
        pot = 0.0
        to_call: float | None = None
        decision_street = street
        if hero_name:
            pot, to_call, decision_street = _compute_pot_to_call_generic(actions, hero_name, fallback_street=street)
        else:
            pot = sum(a.amount or 0.0 for a in actions if a.kind in ("post_sb", "post_bb", "post_ante"))
            to_call = None

        conf = 0.65
        conf -= 0.25 if "hero_hole" in missing else 0.0
        conf -= 0.15 if "big_blind" in missing else 0.0
        conf = max(0.0, min(1.0, conf))

        if pot == 0.0:
            missing.append("pot")

        state = PokerGameState(
            game_type=game_type,
            street=decision_street,
            players=players,
            small_blind=sb if sb > 0 else 0.0,
            big_blind=bb if bb > 0 else 0.0,
            ante=ante if ante > 0 else 0.0,
            pot=pot if pot >= 0 else 0.0,
            hero_hole=hero_hole,
            board=board,
            to_act_seat_no=1,
            last_aggressive_action="raise"
            if any(a.kind in ("bet", "raise") for a in actions if a.street == decision_street)
            else "none",
            confidence={"value": conf, "source": "hand_history", "notes": warnings},
        )

        report = ParseReport(
            parser="GenericHandHistoryParser",
            room="generic",
            game_type_detected=game_type.value if game_type else "unknown",
            confidence=conf,
            missing_fields=sorted(set(missing)),
            warnings=warnings,
            parsed={
                "hero_name": hero_name,
                "hero_hand": [str(c) for c in hero_hole],
                "board": [str(c) for c in board],
                "street": decision_street.value,
                "pot": pot if pot > 0 else None,
                "to_call": to_call,
                "names_seen": sorted(names_seen),
                "action_history": [
                    {
                        "street": a.street.value,
                        "actor": a.actor,
                        "kind": a.kind,
                        "amount": a.amount,
                        "to_amount": a.to_amount,
                    }
                    for a in actions
                ],
            },
        )
        return state, report


def _compute_pot_to_call_generic(
    actions: list[_Action], hero_name: str, *, fallback_street: Street
) -> tuple[float, float | None, Street]:
    hero_streets = [
        a.street
        for a in actions
        if a.actor == hero_name and a.kind in ("fold", "check", "call", "bet", "raise")
    ]
    decision_street = hero_streets[-1] if hero_streets else fallback_street

    decision_idx: int | None = None
    for i, a in enumerate(actions):
        if a.street == decision_street and a.actor == hero_name and a.kind in ("fold", "check", "call", "bet", "raise"):
            decision_idx = i

    invested: dict[str, float] = {}
    current_bet = 0.0
    pot = 0.0
    street = Street.PREFLOP

    def reset_street():
        nonlocal invested, current_bet
        invested = {}
        current_bet = 0.0

    reset_street()

    for i, a in enumerate(actions):
        if a.street != street:
            street = a.street
            reset_street()

        if decision_idx is not None and i == decision_idx:
            to_call = max(0.0, current_bet - invested.get(hero_name, 0.0))
            return pot, to_call, decision_street

        invested.setdefault(a.actor, 0.0)
        if a.kind in ("post_sb", "post_bb", "post_ante") and a.amount is not None:
            invested[a.actor] += float(a.amount)
            pot += float(a.amount)
            if a.kind == "post_bb":
                current_bet = max(current_bet, invested[a.actor])
            continue
        if a.kind == "call" and a.amount is not None:
            invested[a.actor] += float(a.amount)
            pot += float(a.amount)
            continue
        if a.kind == "bet" and a.amount is not None:
            target = float(a.amount)
            add = max(0.0, target - invested[a.actor])
            invested[a.actor] += add
            pot += add
            current_bet = max(current_bet, invested[a.actor])
            continue
        if a.kind == "raise" and a.to_amount is not None:
            target = float(a.to_amount)
            add = max(0.0, target - invested[a.actor])
            invested[a.actor] = target
            pot += add
            current_bet = max(current_bet, target)
            continue

    return pot, None, decision_street


