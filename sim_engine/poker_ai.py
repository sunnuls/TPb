"""
PokerAI — Strong single-player decision engine (Phase 4 of PS roadmap).

Implements a GTO-inspired decision framework:
- Preflop hand ranges by position (EP/MP/CO/BTN/SB/BB)
- Postflop: SPR-aware aggression, board texture adjustments
- Pot-based bet sizing (33% / 50% / 75% / pot)
- Bluff frequency by position
- Pot odds + implied odds for calls

EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------

class PokerAction(str, Enum):
    FOLD  = "fold"
    CHECK = "check"
    CALL  = "call"
    BET   = "bet"
    RAISE = "raise"


class Position(str, Enum):
    """Seat positions at the table."""
    EP  = "ep"   # Early position (UTG, UTG+1)
    MP  = "mp"   # Middle position
    CO  = "co"   # Cut-off
    BTN = "btn"  # Button
    SB  = "sb"   # Small blind
    BB  = "bb"   # Big blind


# ---------------------------------------------------------------------------
# Preflop hand-range tables
# ---------------------------------------------------------------------------

# Ranges expressed as sets of rank pairs / suited combos (simplified notation)
# Key: rank pair string (higher rank first), e.g. "AK", "QQ", "T9s"
# Positions open from (EP tightest → BTN widest)

def _build_preflop_open_ranges() -> Dict[Position, set]:
    """Build GTO-inspired open-raising ranges per position."""
    # Premium hands all positions open
    premium = {
        "AA", "KK", "QQ", "JJ", "TT", "99",
        "AKs", "AQs", "AJs", "ATs", "AKo", "AQo",
    }
    ep_add = {
        "88", "77", "KQs", "KJs", "QJs",
    }
    mp_add = {
        "66", "55", "AJo", "ATo", "KQo", "KTs", "QTs", "JTs",
    }
    co_add = {
        "44", "33", "22", "KJo", "QJo", "J9s", "T9s", "98s", "87s",
        "A9s", "A8s", "A7s", "K9s",
    }
    btn_add = {
        "K8s", "K7s", "K6s", "Q9s", "Q8s", "J8s", "T8s", "97s",
        "86s", "76s", "65s", "54s", "A6s", "A5s", "A4s", "A3s", "A2s",
        "Q9o", "J9o", "T9o", "98o",
    }
    sb_add = {
        "K5s", "K4s", "85s", "75s", "64s", "53s", "43s", "32s",
    }

    ep  = premium | ep_add
    mp  = ep  | mp_add
    co  = mp  | co_add
    btn = co  | btn_add
    sb  = btn | sb_add
    bb  = set()  # BB defends vs open (handled separately)

    return {
        Position.EP:  ep,
        Position.MP:  mp,
        Position.CO:  co,
        Position.BTN: btn,
        Position.SB:  sb,
        Position.BB:  bb,
    }


_OPEN_RANGES: Dict[Position, set] = _build_preflop_open_ranges()


def hand_in_range(cards: List[str], position: Position) -> bool:
    """Return True if this 2-card hand is in the open-raise range for position."""
    if len(cards) < 2:
        return False
    rng = _OPEN_RANGES.get(position, set())
    c1, c2 = cards[0], cards[1]
    r1, r2 = c1[0] if c1 else "?", c2[0] if c2 else "?"
    s1, s2 = c1[1] if len(c1) > 1 else "?", c2[1] if len(c2) > 1 else "?"

    # Rank order
    rank_order = "AKQJT98765432"
    idx1 = rank_order.index(r1) if r1 in rank_order else 13
    idx2 = rank_order.index(r2) if r2 in rank_order else 13
    if idx1 > idx2:
        r1, r2, s1, s2 = r2, r1, s2, s1

    suited   = "s" if s1 == s2 else "o"
    pair_str = f"{r1}{r2}"
    suited_str = f"{r1}{r2}{suited}"
    return (pair_str in rng or suited_str in rng or
            f"{r1}{r2}s" in rng or f"{r1}{r2}o" in rng)


# ---------------------------------------------------------------------------
# Board texture analysis
# ---------------------------------------------------------------------------

@dataclass
class BoardTexture:
    """Analysis of community cards texture."""
    is_wet: bool      = False  # many draws possible
    is_paired: bool   = False  # pair on board
    is_monotone: bool = False  # all same suit
    has_straight_draw: bool = False
    has_flush_draw: bool    = False
    wetness_score: float = 0.0  # 0 = dry, 1 = very wet


def analyze_board(board: List[str]) -> BoardTexture:
    """Analyze community cards texture."""
    if not board:
        return BoardTexture()

    rank_order = "AKQJT98765432"
    ranks = []
    suits = []
    for card in board:
        if len(card) >= 2:
            ranks.append(card[0])
            suits.append(card[1])

    # Paired board
    is_paired = len(ranks) != len(set(ranks))

    # Monotone (all same suit)
    is_monotone = len(set(suits)) == 1 and len(suits) >= 2

    # Flush draw possible (2+ same suit with < 5 cards)
    suit_counts = {s: suits.count(s) for s in set(suits)}
    has_flush_draw = max(suit_counts.values(), default=0) >= 2

    # Straight draw possible (3 connected ranks)
    rank_vals = sorted(set(rank_order.index(r) for r in ranks if r in rank_order))
    has_straight_draw = False
    if len(rank_vals) >= 2:
        for i in range(len(rank_vals) - 1):
            if rank_vals[i + 1] - rank_vals[i] <= 2:
                has_straight_draw = True
                break

    is_wet = has_flush_draw or has_straight_draw or is_monotone

    wetness = 0.0
    if is_monotone:
        wetness += 0.5
    if has_flush_draw:
        wetness += 0.25
    if has_straight_draw:
        wetness += 0.2
    if is_paired:
        wetness -= 0.1
    wetness = max(0.0, min(1.0, wetness))

    return BoardTexture(
        is_wet=is_wet,
        is_paired=is_paired,
        is_monotone=is_monotone,
        has_straight_draw=has_straight_draw,
        has_flush_draw=has_flush_draw,
        wetness_score=wetness,
    )


# ---------------------------------------------------------------------------
# Simple equity estimator (no Monte Carlo — fast heuristic)
# ---------------------------------------------------------------------------

def estimate_equity(hero_cards: List[str], board: List[str]) -> float:
    """Fast heuristic equity estimate (0.0 – 1.0).

    For a real implementation this would use Monte Carlo simulation.
    Here we use a simple rank-based heuristic:
    - Pair or better → 65–80%
    - Two overcards → 48%
    - High card with nut draw → 40%
    - Weak / trash → 30%
    """
    if len(hero_cards) < 2:
        return 0.35

    rank_order = "AKQJT98765432"
    r1 = hero_cards[0][0] if hero_cards[0] else "2"
    r2 = hero_cards[1][0] if len(hero_cards) > 1 and hero_cards[1] else "2"
    s1 = hero_cards[0][1] if len(hero_cards[0]) > 1 else "?"
    s2 = hero_cards[1][1] if len(hero_cards) > 1 and len(hero_cards[1]) > 1 else "?"

    # Pocket pair
    if r1 == r2:
        idx = rank_order.index(r1) if r1 in rank_order else 12
        if idx <= 2:    # AA, KK, QQ
            return 0.82
        elif idx <= 5:  # JJ–99
            return 0.72
        else:           # 88–22
            return 0.60

    # Suited broadway
    broadway = set("AKQJT")
    suited = s1 == s2
    both_broadway = r1 in broadway and r2 in broadway
    if both_broadway and suited:
        return 0.63
    if both_broadway:
        return 0.58

    # Ace-x suited
    if "A" in (r1, r2) and suited:
        return 0.56
    if "A" in (r1, r2):
        return 0.52

    # Two high cards (K/Q)
    high = {"K", "Q", "J"}
    if r1 in high and r2 in high:
        return 0.50

    # Connected suited
    if suited:
        i1 = rank_order.index(r1) if r1 in rank_order else 12
        i2 = rank_order.index(r2) if r2 in rank_order else 12
        gap = abs(i1 - i2)
        if gap <= 1:
            return 0.48
        elif gap <= 3:
            return 0.44

    return 0.38


# ---------------------------------------------------------------------------
# Bet sizing
# ---------------------------------------------------------------------------

class BetSize(str, Enum):
    SMALL  = "small"   # 33% pot
    MEDIUM = "medium"  # 50% pot
    LARGE  = "large"   # 75% pot
    POT    = "pot"     # 100% pot
    OVERBET = "overbet" # 150% pot


def compute_bet_amount(
    pot: float,
    stack: float,
    size: BetSize,
) -> float:
    """Compute actual chip amount for a bet size relative to pot."""
    ratios = {
        BetSize.SMALL:   0.33,
        BetSize.MEDIUM:  0.50,
        BetSize.LARGE:   0.75,
        BetSize.POT:     1.00,
        BetSize.OVERBET: 1.50,
    }
    amount = pot * ratios.get(size, 0.5)
    return min(round(amount), round(stack))


# ---------------------------------------------------------------------------
# Main AI decision class
# ---------------------------------------------------------------------------

@dataclass
class AIDecision:
    """Output of PokerAI.decide()."""
    action:   PokerAction
    amount:   float = 0.0          # bet/raise amount in chips (0 for fold/check/call)
    reasoning: str = ""
    confidence: float = 0.5


class PokerAI:
    """
    GTO-inspired single-player decision engine for PokerStars.

    Usage::

        ai = PokerAI()
        decision = ai.decide(
            hero_cards=["As", "Kh"],
            board=["Qd", "Jc", "9s"],
            pot=1200,
            hero_stack=8000,
            to_call=400,
            position=Position.BTN,
            street="flop",
            legal_actions=["fold", "call", "raise"],
        )
        print(decision.action, decision.amount)
    """

    def __init__(self, bluff_frequency: float = 0.25):
        """
        Args:
            bluff_frequency: Base probability of bluffing (0–1).
        """
        self.bluff_frequency = bluff_frequency

    def decide(
        self,
        hero_cards: List[str],
        board: List[str],
        pot: float,
        hero_stack: float,
        to_call: float = 0.0,
        position: Position = Position.BTN,
        street: str = "preflop",
        legal_actions: Optional[List[str]] = None,
        villain_stack: float = 0.0,
    ) -> AIDecision:
        """
        Make a poker decision given the current game state.

        Args:
            hero_cards:    Bot's hole cards, e.g. ["As", "Kh"]
            board:         Community cards, e.g. ["Qd", "Jc", "9s"]
            pot:           Current pot in chips
            hero_stack:    Bot's remaining stack
            to_call:       Amount needed to call (0 if checking option)
            position:      Seat position enum
            street:        "preflop"/"flop"/"turn"/"river"
            legal_actions: List of legal action strings
            villain_stack: Largest opponent stack

        Returns:
            AIDecision with action + amount + reasoning
        """
        if legal_actions is None:
            legal_actions = ["fold", "check", "call", "bet", "raise"]
        legal = set(a.lower() for a in legal_actions)

        if street == "preflop":
            return self._decide_preflop(
                hero_cards, pot, hero_stack, to_call, position, legal
            )
        else:
            return self._decide_postflop(
                hero_cards, board, pot, hero_stack, to_call,
                position, street, legal, villain_stack
            )

    # ── Preflop ──────────────────────────────────────────────────────────────

    def _decide_preflop(
        self,
        hero_cards: List[str],
        pot: float,
        stack: float,
        to_call: float,
        position: Position,
        legal: set,
    ) -> AIDecision:
        in_range = hand_in_range(hero_cards, position)
        equity = estimate_equity(hero_cards, [])

        if to_call == 0:
            # We have the option to check or open-raise
            if in_range and ("raise" in legal or "bet" in legal):
                # Open raise 3BB
                big_blind = max(pot / 1.5, 1)
                amount = round(big_blind * 3)
                amount = min(amount, stack)
                action = PokerAction.RAISE if "raise" in legal else PokerAction.BET
                return AIDecision(
                    action=action, amount=amount,
                    reasoning=f"Preflop open {position.value}: {hero_cards}",
                    confidence=0.8,
                )
            if "check" in legal:
                return AIDecision(action=PokerAction.CHECK, reasoning="Preflop check OOP")
            return AIDecision(action=PokerAction.FOLD, reasoning="Preflop fold (not in range)")

        # Facing a raise
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0
        if equity >= pot_odds + 0.05 and in_range:
            # 3-bet strong hands
            if equity > 0.70 and ("raise" in legal):
                big_blind = max(to_call / 3, 1)
                amount = round(to_call * 3)
                amount = min(amount, stack)
                return AIDecision(
                    action=PokerAction.RAISE, amount=amount,
                    reasoning=f"3-bet: equity={equity:.0%} pos={position.value}",
                    confidence=0.85,
                )
            # Call with decent equity
            if "call" in legal:
                return AIDecision(
                    action=PokerAction.CALL,
                    reasoning=f"Call: equity={equity:.0%} > pot_odds={pot_odds:.0%}",
                    confidence=0.7,
                )
        # Fold weak hands
        if "fold" in legal:
            return AIDecision(
                action=PokerAction.FOLD,
                reasoning=f"Fold preflop: equity={equity:.0%} < pot_odds={pot_odds:.0%}",
                confidence=0.75,
            )
        return AIDecision(action=PokerAction.CHECK if "check" in legal else PokerAction.FOLD)

    # ── Postflop ─────────────────────────────────────────────────────────────

    def _decide_postflop(
        self,
        hero_cards: List[str],
        board: List[str],
        pot: float,
        stack: float,
        to_call: float,
        position: Position,
        street: str,
        legal: set,
        villain_stack: float,
    ) -> AIDecision:
        equity   = estimate_equity(hero_cards, board)
        texture  = analyze_board(board)
        eff_stack = min(stack, villain_stack) if villain_stack > 0 else stack
        spr      = eff_stack / pot if pot > 0 else 10.0

        in_position = position in (Position.BTN, Position.CO)
        is_bluff_spot = (
            in_position
            and random.random() < self.bluff_frequency
            and equity < 0.45
            and (texture.has_flush_draw or texture.has_straight_draw)
        )

        # ── No bet facing us ─────────────────────────────────────────────────
        if to_call == 0:
            if equity >= 0.65:
                # Strong hand: bet for value
                size = self._pick_size(texture, street, "value")
                amount = compute_bet_amount(pot, stack, size)
                return AIDecision(
                    action=PokerAction.BET if "bet" in legal else PokerAction.RAISE,
                    amount=amount,
                    reasoning=(
                        f"Value bet {size.value}: equity={equity:.0%} "
                        f"SPR={spr:.1f} texture={texture.wetness_score:.2f}"
                    ),
                    confidence=0.85,
                )
            if equity >= 0.50 and spr < 3:
                # Low SPR → bet / shove
                amount = min(round(pot), round(stack))
                action = PokerAction.BET if "bet" in legal else PokerAction.RAISE
                return AIDecision(
                    action=action, amount=amount,
                    reasoning=f"Low SPR={spr:.1f}, semi-commit",
                    confidence=0.75,
                )
            if is_bluff_spot and "bet" in legal:
                size = BetSize.SMALL if texture.wetness_score < 0.4 else BetSize.MEDIUM
                amount = compute_bet_amount(pot, stack, size)
                return AIDecision(
                    action=PokerAction.BET, amount=amount,
                    reasoning=f"Positional bluff: texture={texture.wetness_score:.2f}",
                    confidence=0.55,
                )
            if "check" in legal:
                return AIDecision(
                    action=PokerAction.CHECK,
                    reasoning=f"Check: equity={equity:.0%} SPR={spr:.1f}",
                    confidence=0.65,
                )

        # ── Facing a bet ─────────────────────────────────────────────────────
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 1.0
        implied  = min(eff_stack / to_call, 10) * 0.03 if to_call > 0 else 0.0

        if equity + implied >= pot_odds:
            # Raise strong hands; call medium
            if equity >= 0.75 and ("raise" in legal):
                size = BetSize.LARGE if spr > 5 else BetSize.POT
                amount = compute_bet_amount(pot + to_call, stack, size)
                return AIDecision(
                    action=PokerAction.RAISE, amount=amount,
                    reasoning=f"Raise for value: equity={equity:.0%}",
                    confidence=0.88,
                )
            if "call" in legal:
                return AIDecision(
                    action=PokerAction.CALL,
                    reasoning=(
                        f"Call: eq={equity:.0%}+impl={implied:.0%}"
                        f" >= pot_odds={pot_odds:.0%}"
                    ),
                    confidence=0.70,
                )

        # Fold unprofitable calls
        if "fold" in legal:
            return AIDecision(
                action=PokerAction.FOLD,
                reasoning=f"Fold: eq={equity:.0%} < pot_odds={pot_odds:.0%}",
                confidence=0.72,
            )
        return AIDecision(action=PokerAction.CHECK if "check" in legal else PokerAction.FOLD)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _pick_size(self, texture: BoardTexture, street: str, bet_type: str) -> BetSize:
        """Choose bet size based on board texture and bet purpose."""
        if bet_type == "value":
            if texture.wetness_score >= 0.5:
                return BetSize.LARGE   # 75% pot on wet boards
            if street in ("turn", "river"):
                return BetSize.LARGE
            return BetSize.MEDIUM      # 50% pot dry flop
        else:  # bluff / semi-bluff
            if texture.wetness_score >= 0.4:
                return BetSize.MEDIUM
            return BetSize.SMALL

    @staticmethod
    def from_table_state(table_state: object) -> Tuple[List[str], List[str], float, float, float, str, Position]:
        """Extract arguments for decide() from a TableState object.

        Returns:
            (hero_cards, board, pot, hero_stack, to_call, street, position)
        """
        hero_cards: List[str] = []
        board:      List[str] = []
        pot:        float     = 0.0
        hero_stack: float     = 0.0
        to_call:    float     = 0.0
        street:     str       = "preflop"
        position:   Position  = Position.BTN

        try:
            board = list(getattr(table_state, "board", []) or [])
            pot   = float(getattr(table_state, "pot",  0) or 0)

            # Find hero player
            for p in getattr(table_state, "players", []):
                if getattr(p, "is_hero", False):
                    hero_cards  = list(getattr(p, "hole_cards", []) or [])
                    hero_stack  = float(getattr(p, "stack", 0) or 0)
                    to_call     = float(getattr(p, "to_call", 0) or 0)
                    pos_val     = getattr(p, "position", None)
                    if pos_val is not None:
                        try:
                            position = Position(str(pos_val).lower().split(".")[-1])
                        except ValueError:
                            position = Position.BTN
                    break

            # Street
            street_obj = getattr(table_state, "street", None)
            if street_obj is not None:
                s = str(street_obj).lower().split(".")[-1]
                street = s if s in ("preflop", "flop", "turn", "river") else "preflop"

        except Exception as exc:
            logger.debug("from_table_state parse error: %s", exc)

        return hero_cards, board, pot, hero_stack, to_call, street, position
