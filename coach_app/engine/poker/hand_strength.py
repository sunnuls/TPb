from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from coach_app.schemas.common import Card


RANKS = "23456789TJQKA"
RANK_TO_I = {r: i for i, r in enumerate(RANKS, start=2)}


@dataclass(frozen=True)
class HandCategory:
    category: str
    is_flush_draw: bool
    is_straight_draw: str | None  # "open_ender" | "gutshot" | None


def categorize(hero_hole: list[Card], board: list[Card]) -> HandCategory:
    """
    Deterministic simplified evaluator:
    - category: best made hand category among available cards
    - draw detection: flush draw and straight draw (OE/gutshot) when board has at least 3 cards.

    Not solver-grade; good enough for stable MVP coaching.
    """
    cards = hero_hole + board
    if len(cards) < 2:
        return HandCategory(category="unknown", is_flush_draw=False, is_straight_draw=None)

    # Best 5-card made hand category among combos (if we have >=5 cards)
    made = _best_made_category(cards)
    flush_draw = _has_flush_draw(hero_hole, board)
    straight_draw = _straight_draw_type(hero_hole, board)
    return HandCategory(category=made, is_flush_draw=flush_draw, is_straight_draw=straight_draw)


def _best_made_category(cards: list[Card]) -> str:
    if len(cards) < 5:
        # With <5 cards, categorize by pair-ish only
        ranks = [c.rank for c in cards]
        counts = sorted([ranks.count(r) for r in set(ranks)], reverse=True)
        if counts and counts[0] == 4:
            return "quads"
        if len(counts) >= 2 and counts[0] == 3 and counts[1] == 2:
            return "full_house"
        if counts and counts[0] == 3:
            return "trips"
        if len(counts) >= 2 and counts[0] == 2 and counts[1] == 2:
            return "two_pair"
        if counts and counts[0] == 2:
            return "pair"
        return "high_card"

    best_rank = None
    best_name = "high_card"
    for five in combinations(cards, 5):
        name, rank = _rank_five(list(five))
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_name = name
    return best_name


def _rank_five(cards: list[Card]) -> tuple[str, tuple]:
    ranks = sorted([RANK_TO_I[c.rank] for c in cards], reverse=True)
    suits = [c.suit.value for c in cards]
    is_flush = len(set(suits)) == 1
    is_straight, top = _is_straight(ranks)

    # counts
    counts: dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    groups = sorted(((cnt, r) for r, cnt in counts.items()), reverse=True)  # by cnt then rank
    cnts = sorted(counts.values(), reverse=True)

    if is_flush and is_straight:
        return "straight_flush", (8, top)
    if cnts[0] == 4:
        quad = groups[0][1]
        kicker = max(r for r in ranks if r != quad)
        return "quads", (7, quad, kicker)
    if cnts[0] == 3 and cnts[1] == 2:
        trips = groups[0][1]
        pair = groups[1][1]
        return "full_house", (6, trips, pair)
    if is_flush:
        return "flush", (5, ranks)
    if is_straight:
        return "straight", (4, top)
    if cnts[0] == 3:
        trips = groups[0][1]
        kickers = sorted([r for r in ranks if r != trips], reverse=True)
        return "trips", (3, trips, kickers)
    if cnts[0] == 2 and cnts[1] == 2:
        pair_hi = groups[0][1]
        pair_lo = groups[1][1]
        kicker = max(r for r in ranks if r not in (pair_hi, pair_lo))
        return "two_pair", (2, pair_hi, pair_lo, kicker)
    if cnts[0] == 2:
        pair = groups[0][1]
        kickers = sorted([r for r in ranks if r != pair], reverse=True)
        return "pair", (1, pair, kickers)
    return "high_card", (0, ranks)


def _is_straight(ranks_desc: list[int]) -> tuple[bool, int]:
    uniq = sorted(set(ranks_desc), reverse=True)
    # wheel A-5
    if set([14, 5, 4, 3, 2]).issubset(set(uniq)):
        return True, 5
    for i in range(len(uniq) - 4):
        window = uniq[i : i + 5]
        if window[0] - window[4] == 4 and len(window) == 5:
            return True, window[0]
    return False, 0


def _has_flush_draw(hero_hole: list[Card], board: list[Card]) -> bool:
    if len(board) < 3 or len(hero_hole) != 2:
        return False
    suits = [c.suit.value for c in hero_hole + board]
    # flush draw => 4 of same suit among available cards, but not already flush (5)
    for s in set(suits):
        cnt = suits.count(s)
        if cnt == 4:
            return True
    return False


def _straight_draw_type(hero_hole: list[Card], board: list[Card]) -> str | None:
    if len(board) < 3:
        return None
    ranks = sorted(set([RANK_TO_I[c.rank] for c in hero_hole + board]))
    # include wheel ace as 1 for draw detection convenience
    if 14 in ranks:
        ranks = sorted(set(ranks + [1]))

    best = None
    for start in range(1, 11):  # possible 5-card straights start at A(1) to T(10)
        target = set(range(start, start + 5))
        have = target.intersection(ranks)
        missing = target.difference(ranks)
        if len(missing) == 1:
            miss = next(iter(missing))
            # open-ender if missing is at either end
            if miss in (start, start + 4):
                best = "open_ender"
            else:
                best = best or "gutshot"
    return best


# Secondary (legacy) strength helper used by older MVP module.
RANK_TO_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}  # 2..14


@dataclass(frozen=True)
class HandStrength:
    category: str
    is_draw: bool
    notes: list[str]


def _values(cards: list[Card]) -> list[int]:
    return sorted((RANK_TO_VALUE[c.rank] for c in cards), reverse=True)


def _is_straight_bool(values: list[int]) -> bool:
    # values: unique sorted desc
    if not values:
        return False
    uniq = sorted(set(values), reverse=True)
    # wheel: A2345
    if 14 in uniq:
        uniq.append(1)
    run = 1
    for i in range(1, len(uniq)):
        if uniq[i] == uniq[i - 1] - 1:
            run += 1
            if run >= 5:
                return True
        elif uniq[i] != uniq[i - 1]:
            run = 1
    return False


def _has_straight_draw(values: list[int]) -> bool:
    uniq = sorted(set(values))
    if 14 in uniq:
        uniq = uniq + [1]
    uniq = sorted(set(uniq))
    # For each possible 5-card straight window, check if we have 4 of them.
    for start in range(1, 11):  # 1..10
        window = set(range(start, start + 5))
        have = len(window.intersection(set(uniq)))
        if have == 4:
            return True
    return False


def compute_hand_strength(hero_hole: list[Card], board: list[Card]) -> HandStrength:
    """
    Simplified strength categorizer for coaching:
    - made hands: quads/full_house/flush/straight/set/two_pair/overpair/top_pair/pair/high_card
    - draws: flush_draw/straight_draw (flagged via is_draw)
    """
    notes: list[str] = []
    all_cards = hero_hole + board
    if len(hero_hole) != 2 or len(board) < 3:
        return HandStrength(category="unknown", is_draw=False, notes=["Недостаточно карт для оценки категории"])

    # Counts
    rank_counts: dict[str, int] = {}
    suit_counts: dict[str, int] = {}
    for c in all_cards:
        rank_counts[c.rank] = rank_counts.get(c.rank, 0) + 1
        suit_counts[c.suit.value] = suit_counts.get(c.suit.value, 0) + 1

    counts = sorted(rank_counts.values(), reverse=True)
    vals = _values(all_cards)
    board_vals = _values(board)
    hero_vals = _values(hero_hole)

    is_flush = max(suit_counts.values() or [0]) >= 5
    is_straight = _is_straight_bool(vals)

    # Draw detection (only if not already made)
    is_flush_draw = (not is_flush) and max(suit_counts.values() or [0]) == 4
    is_straight_draw = (not is_straight) and _has_straight_draw(vals)

    if 4 in counts:
        return HandStrength(category="quads", is_draw=False, notes=notes)
    if 3 in counts and 2 in counts:
        return HandStrength(category="full_house", is_draw=False, notes=notes)
    if is_flush:
        return HandStrength(category="flush", is_draw=False, notes=notes)
    if is_straight:
        return HandStrength(category="straight", is_draw=False, notes=notes)
    if 3 in counts:
        return HandStrength(category="set", is_draw=False, notes=notes)
    if counts.count(2) >= 2:
        return HandStrength(category="two_pair", is_draw=False, notes=notes)

    # One pair logic
    if 2 in counts:
        # Determine if pocket pair
        pocket_pair = hero_hole[0].rank == hero_hole[1].rank
        top_board = max(board_vals) if board_vals else 0
        if pocket_pair and hero_vals[0] > top_board:
            return HandStrength(category="overpair", is_draw=False, notes=notes)

        # Find paired rank and if it's top pair
        paired_ranks = {r for r, c in rank_counts.items() if c == 2}
        # If hero contributes to the pair and pair rank equals top board rank => top pair
        hero_ranks = {c.rank for c in hero_hole}
        top_board_rank_val = top_board
        top_board_ranks = {c.rank for c in board if RANK_TO_VALUE[c.rank] == top_board_rank_val}
        if paired_ranks.intersection(hero_ranks) and paired_ranks.intersection(top_board_ranks):
            return HandStrength(category="top_pair", is_draw=False, notes=notes)
        return HandStrength(category="pair", is_draw=False, notes=notes)

    # Draws (if no pair+)
    if is_flush_draw:
        return HandStrength(category="flush_draw", is_draw=True, notes=["Флеш-дро"])
    if is_straight_draw:
        return HandStrength(category="straight_draw", is_draw=True, notes=["Стрит-дро"])

    return HandStrength(category="high_card", is_draw=False, notes=notes)



