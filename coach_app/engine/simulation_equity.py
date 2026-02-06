"""
Simulation Equity Calculator for Multi-Agent Game Theory Research.

This module provides probability-based equity calculation for educational
simulation purposes. Uses Monte Carlo methods to estimate win rates and
expected values in strategic decision-making scenarios.

Educational Use Only: Designed for game theory research and educational
simulations in controlled virtual environments.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import Any

from coach_app.engine.poker.ranges.range import Range


@dataclass
class EquityResult:
    """
    Result of equity calculation for simulation analysis.
    
    Attributes:
        equity: Win probability for hero (0.0-1.0)
        win_count: Number of simulations where hero won
        tie_count: Number of simulations that tied
        lose_count: Number of simulations where hero lost
        total_simulations: Total number of Monte Carlo runs
        confidence: Statistical confidence in result (0.0-1.0)
        breakdown: Optional detailed breakdown by opponent hand
    """
    equity: float
    win_count: int
    tie_count: int
    lose_count: int
    total_simulations: int
    confidence: float
    breakdown: dict[str, Any] | None = None
    
    def __post_init__(self):
        """Validate equity result."""
        if not 0.0 <= self.equity <= 1.0:
            raise ValueError(f"Equity must be in [0,1], got {self.equity}")
        
        total = self.win_count + self.tie_count + self.lose_count
        if total != self.total_simulations:
            raise ValueError(
                f"Counts don't sum to total: {total} != {self.total_simulations}"
            )


def calculate_monte_carlo_equity(
    hero_hand: list[str],
    opponent_range: Range,
    board: list[str],
    num_simulations: int = 1000,
    random_seed: int | None = None
) -> EquityResult:
    """
    Calculate hero's equity using Monte Carlo simulation.
    
    This is a deterministic heuristic for educational simulations.
    For production use, integrate with libraries like `treys` or `pokerkit`.
    
    Algorithm:
    1. Sample opponent hand from range (weighted by hand frequency)
    2. Complete board runout if not on river
    3. Evaluate final hands using heuristic hand strength
    4. Repeat N times and calculate win rate
    
    Args:
        hero_hand: Hero's two hole cards, e.g., ["Ah", "Ks"]
        opponent_range: Opponent's estimated range (Range Model v0)
        board: Community cards, e.g., ["Ad", "7c", "2s"] (0-5 cards)
        num_simulations: Number of Monte Carlo runs (default 1000)
        random_seed: Optional seed for reproducibility in tests
    
    Returns:
        EquityResult with win/tie/lose counts and equity percentage
    
    Raises:
        ValueError: If inputs are invalid (wrong card count, duplicate cards, etc.)
    
    Example:
        >>> hero = ["Ah", "Ks"]
        >>> villain_range = Range(hands={"QQ": 1.0, "AQs": 0.9, "KJs": 0.7})
        >>> board = ["Ad", "7c", "2s"]
        >>> result = calculate_monte_carlo_equity(hero, villain_range, board, num_simulations=1000)
        >>> print(f"Equity: {result.equity:.1%}")
        Equity: 68.5%
    """
    # Validate inputs
    _validate_equity_input(hero_hand, board)
    
    if random_seed is not None:
        random.seed(random_seed)
    
    # Normalize opponent range
    opp_range = opponent_range.normalize()
    
    if len(opp_range.hands) == 0:
        raise ValueError("Opponent range is empty after normalization")
    
    # Build deck (remove known cards)
    deck = _build_deck()
    known_cards = set(hero_hand + board)
    available_deck = [c for c in deck if c not in known_cards]
    
    wins = 0
    ties = 0
    losses = 0
    
    for _ in range(num_simulations):
        # Sample opponent hand from range
        opp_hand = _sample_hand_from_range(opp_range, known_cards, available_deck)
        
        if opp_hand is None:
            # Couldn't sample valid hand, skip this simulation
            continue
        
        # Complete board (if not river)
        cards_needed = 5 - len(board)
        if cards_needed > 0:
            # Remove opponent cards from available deck
            sim_deck = [c for c in available_deck if c not in opp_hand]
            if len(sim_deck) < cards_needed:
                continue  # Not enough cards, skip
            
            runout = random.sample(sim_deck, cards_needed)
            final_board = board + runout
        else:
            final_board = board
        
        # Evaluate hands using deterministic heuristic
        hero_strength = _evaluate_hand_strength(hero_hand, final_board)
        opp_strength = _evaluate_hand_strength(opp_hand, final_board)
        
        if hero_strength > opp_strength:
            wins += 1
        elif hero_strength == opp_strength:
            ties += 1
        else:
            losses += 1
    
    # Calculate equity
    actual_sims = wins + ties + losses
    if actual_sims == 0:
        raise ValueError("No valid simulations completed")
    
    equity = (wins + ties * 0.5) / actual_sims
    
    # Confidence based on sample size (simple heuristic)
    confidence = min(1.0, actual_sims / num_simulations)
    
    return EquityResult(
        equity=equity,
        win_count=wins,
        tie_count=ties,
        lose_count=losses,
        total_simulations=actual_sims,
        confidence=confidence
    )


def calculate_equity_vs_specific_hand(
    hero_hand: list[str],
    opponent_hand: list[str],
    board: list[str],
    num_simulations: int = 1000
) -> EquityResult:
    """
    Calculate equity vs a specific opponent hand (not a range).
    
    Useful for analyzing showdown scenarios or testing specific matchups.
    
    Args:
        hero_hand: Hero's hole cards
        opponent_hand: Opponent's known hole cards
        board: Community cards (0-5 cards)
        num_simulations: Number of runouts to simulate
    
    Returns:
        EquityResult with equity calculation
    
    Example:
        >>> hero = ["Ah", "Kh"]
        >>> villain = ["Qd", "Jd"]
        >>> board = ["Kc", "7h", "2h"]  # Hero has pair + flush draw
        >>> result = calculate_equity_vs_specific_hand(hero, villain, board)
        >>> print(f"Equity: {result.equity:.1%}")
    """
    _validate_equity_input(hero_hand, board)
    _validate_hand(opponent_hand)
    
    # Check for duplicate cards
    all_cards = hero_hand + opponent_hand + board
    if len(all_cards) != len(set(all_cards)):
        raise ValueError("Duplicate cards detected")
    
    # Build deck
    deck = _build_deck()
    known_cards = set(all_cards)
    available_deck = [c for c in deck if c not in known_cards]
    
    wins = 0
    ties = 0
    losses = 0
    
    # If river, no runouts needed
    if len(board) == 5:
        hero_strength = _evaluate_hand_strength(hero_hand, board)
        opp_strength = _evaluate_hand_strength(opponent_hand, board)
        
        if hero_strength > opp_strength:
            return EquityResult(1.0, 1, 0, 0, 1, 1.0)
        elif hero_strength == opp_strength:
            return EquityResult(0.5, 0, 1, 0, 1, 1.0)
        else:
            return EquityResult(0.0, 0, 0, 1, 1, 1.0)
    
    # Simulate runouts
    cards_needed = 5 - len(board)
    
    for _ in range(num_simulations):
        runout = random.sample(available_deck, cards_needed)
        final_board = board + runout
        
        hero_strength = _evaluate_hand_strength(hero_hand, final_board)
        opp_strength = _evaluate_hand_strength(opponent_hand, final_board)
        
        if hero_strength > opp_strength:
            wins += 1
        elif hero_strength == opp_strength:
            ties += 1
        else:
            losses += 1
    
    equity = (wins + ties * 0.5) / num_simulations
    
    return EquityResult(
        equity=equity,
        win_count=wins,
        tie_count=ties,
        lose_count=losses,
        total_simulations=num_simulations,
        confidence=1.0
    )


def _validate_equity_input(hero_hand: list[str], board: list[str]) -> None:
    """
    Validate equity calculation inputs.
    
    Raises:
        ValueError: If inputs are invalid
    """
    _validate_hand(hero_hand)
    
    if not 0 <= len(board) <= 5:
        raise ValueError(f"Board must have 0-5 cards, got {len(board)}")
    
    _validate_cards(board)
    
    # Check for duplicates
    all_cards = hero_hand + board
    if len(all_cards) != len(set(all_cards)):
        raise ValueError("Duplicate cards in hero hand and board")


def _validate_hand(hand: list[str]) -> None:
    """Validate hole cards."""
    if len(hand) != 2:
        raise ValueError(f"Hand must have exactly 2 cards, got {len(hand)}")
    
    _validate_cards(hand)
    
    if hand[0] == hand[1]:
        raise ValueError(f"Duplicate cards in hand: {hand}")


def _validate_cards(cards: list[str]) -> None:
    """Validate card format."""
    valid_ranks = "23456789TJQKA"
    valid_suits = "shdc"
    
    for card in cards:
        if len(card) != 2:
            raise ValueError(f"Invalid card format: {card}. Must be 2 chars (rank+suit)")
        
        rank, suit = card[0], card[1]
        
        if rank not in valid_ranks:
            raise ValueError(f"Invalid rank: {rank}")
        
        if suit not in valid_suits:
            raise ValueError(f"Invalid suit: {suit}")


def _build_deck() -> list[str]:
    """Build standard 52-card deck."""
    ranks = "23456789TJQKA"
    suits = "shdc"
    return [r + s for r in ranks for s in suits]


def _sample_hand_from_range(
    range_obj: Range,
    known_cards: set[str],
    available_deck: list[str]
) -> list[str] | None:
    """
    Sample a hand from opponent range using weighted random selection.
    
    Args:
        range_obj: Normalized Range object
        known_cards: Cards already dealt (hero hand + board)
        available_deck: Cards available to sample from
    
    Returns:
        Two-card hand or None if sampling failed
    """
    # Get hands from range with their weights
    hands_with_weights = list(range_obj.hands.items())
    
    # Filter out hands that contain known cards
    valid_hands = []
    valid_weights = []
    
    for hand_notation, weight in hands_with_weights:
        # Convert notation to actual cards
        possible_combos = _notation_to_card_combos(hand_notation, available_deck)
        
        if possible_combos:
            valid_hands.append(hand_notation)
            valid_weights.append(weight)
    
    if not valid_hands:
        return None
    
    # Weighted random selection
    hand_notation = random.choices(valid_hands, weights=valid_weights, k=1)[0]
    
    # Get actual cards for this notation
    possible_combos = _notation_to_card_combos(hand_notation, available_deck)
    
    if not possible_combos:
        return None
    
    return random.choice(possible_combos)


def _notation_to_card_combos(hand_notation: str, available_deck: list[str]) -> list[list[str]]:
    """
    Convert hand notation (e.g., "AKs", "QQ") to actual card combinations.
    
    Args:
        hand_notation: Hand in standard notation
        available_deck: Cards available
    
    Returns:
        List of [card1, card2] combinations
    """
    if len(hand_notation) < 2:
        return []
    
    rank1 = hand_notation[0]
    rank2 = hand_notation[1]
    
    # Pair (e.g., "AA", "KK")
    if rank1 == rank2:
        combos = [
            [c1, c2]
            for c1 in available_deck
            for c2 in available_deck
            if c1[0] == rank1 and c2[0] == rank2 and c1 != c2
        ]
        return combos
    
    # Suited (e.g., "AKs")
    if len(hand_notation) == 3 and hand_notation[2] == 's':
        combos = [
            [c1, c2]
            for c1 in available_deck
            for c2 in available_deck
            if c1[0] == rank1 and c2[0] == rank2 and c1[1] == c2[1] and c1 != c2
        ]
        return combos
    
    # Offsuit (e.g., "AKo")
    if len(hand_notation) == 3 and hand_notation[2] == 'o':
        combos = [
            [c1, c2]
            for c1 in available_deck
            for c2 in available_deck
            if c1[0] == rank1 and c2[0] == rank2 and c1[1] != c2[1] and c1 != c2
        ]
        return combos
    
    return []


def _evaluate_hand_strength(hole_cards: list[str], board: list[str]) -> float:
    """
    Deterministic heuristic for hand strength evaluation.
    
    This is a simplified evaluator for educational simulations.
    For production, use proper poker evaluators like `treys` or `pokerkit`.
    
    Returns:
        Strength score (higher = better). Scale: 0.0-9.0+
        - 9.0+: Straight flush
        - 8.0-8.9: Quads
        - 7.0-7.9: Full house
        - 6.0-6.9: Flush
        - 5.0-5.9: Straight
        - 4.0-4.9: Trips
        - 3.0-3.9: Two pair
        - 2.0-2.9: Pair
        - 1.0-1.9: High card
    
    Educational Note:
        This heuristic is intentionally simplified for simulation research.
        It does NOT accurately model complex hand rankings like kicker
        comparison or tie-breaking. Use proper evaluators for real applications.
    """
    all_cards = hole_cards + board
    
    if len(all_cards) != 7:
        raise ValueError(f"Must have exactly 7 cards (2 hole + 5 board), got {len(all_cards)}")
    
    # Extract ranks and suits
    ranks = [c[0] for c in all_cards]
    suits = [c[1] for c in all_cards]
    
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)
    
    # Check for flush
    has_flush = any(count >= 5 for count in suit_counts.values())
    
    # Check for straight (simplified)
    unique_ranks = sorted(set(rank_values[r] for r in ranks))
    has_straight = False
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i:i+5] == list(range(unique_ranks[i], unique_ranks[i]+5)):
            has_straight = True
            break
    
    # Check for A-2-3-4-5 wheel straight
    if set([14, 2, 3, 4, 5]).issubset(set(unique_ranks)):
        has_straight = True
    
    # Check for straight flush (simplified)
    if has_flush and has_straight:
        return 9.0 + max(unique_ranks) / 100.0
    
    # Quads
    if 4 in rank_counts.values():
        quad_rank = [r for r, cnt in rank_counts.items() if cnt == 4][0]
        return 8.0 + rank_values[quad_rank] / 100.0
    
    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        trip_rank = [r for r, cnt in rank_counts.items() if cnt == 3][0]
        return 7.0 + rank_values[trip_rank] / 100.0
    
    # Flush
    if has_flush:
        flush_suit = [s for s, cnt in suit_counts.items() if cnt >= 5][0]
        flush_ranks = [rank_values[c[0]] for c in all_cards if c[1] == flush_suit]
        return 6.0 + max(flush_ranks) / 100.0
    
    # Straight
    if has_straight:
        return 5.0 + max(unique_ranks) / 100.0
    
    # Trips
    if 3 in rank_counts.values():
        trip_rank = [r for r, cnt in rank_counts.items() if cnt == 3][0]
        return 4.0 + rank_values[trip_rank] / 100.0
    
    # Two pair
    pairs = [r for r, cnt in rank_counts.items() if cnt == 2]
    if len(pairs) >= 2:
        top_pair_rank = max(rank_values[r] for r in pairs)
        return 3.0 + top_pair_rank / 100.0
    
    # Pair
    if len(pairs) == 1:
        pair_rank = rank_values[pairs[0]]
        return 2.0 + pair_rank / 100.0
    
    # High card
    high_card = max(rank_values[r] for r in ranks)
    return 1.0 + high_card / 100.0
