"""
Dummy Human Opponent Simulation (Roadmap2 Phase 3).

This module implements a scripted opponent player with:
- Tight/loose random behavior with variance
- Simple decision logic based on hand strength
- Realistic variability to simulate human unpredictability

Educational Use Only: For research into multi-agent strategies
against simulated human-like opponents. Not for production use.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class OpponentStyle(str, Enum):
    """Opponent playing style."""
    TIGHT = "tight"  # Only plays strong hands
    LOOSE = "loose"  # Plays many hands
    RANDOM = "random"  # Unpredictable mix


class ActionType(str, Enum):
    """Poker action types."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"


@dataclass
class OpponentAction:
    """
    Dummy opponent's action result.
    
    Attributes:
        action: Action type (fold/check/call/bet/raise)
        amount: Bet/raise amount (None for fold/check/call)
        reasoning: Why the dummy made this decision
    """
    action: ActionType
    amount: Optional[float] = None
    reasoning: str = ""


class DummyOpponent:
    """
    Scripted dummy opponent for HIVE simulation.
    
    This opponent uses simple hand strength thresholds and variance
    to simulate human-like decision-making. It is intentionally weak
    to demonstrate HIVE coordination advantages.
    
    Features:
    - Tight/loose/random playing styles
    - Hand strength-based decisions
    - Behavioral variance (unpredictability)
    - Pot odds awareness (simplified)
    
    Educational Note:
        This is a research tool to study multi-agent coordination
        against a baseline opponent, not a realistic poker AI.
    """
    
    def __init__(
        self,
        style: OpponentStyle = OpponentStyle.RANDOM,
        variance: float = 0.3,
        aggression: float = 0.5,
        stack: float = 1000.0
    ):
        """
        Initialize dummy opponent.
        
        Args:
            style: Playing style (tight/loose/random)
            variance: Behavioral unpredictability (0.0 to 1.0)
            aggression: Betting frequency (0.0 = passive, 1.0 = aggressive)
            stack: Starting stack size (in bb)
        """
        self.style = style
        self.variance = variance
        self.aggression = aggression
        self.stack = stack
        self.hands_played = 0
        
        # Style-specific thresholds
        self._set_thresholds()
    
    def _set_thresholds(self) -> None:
        """Set hand strength thresholds based on style."""
        if self.style == OpponentStyle.TIGHT:
            self.vpip = 0.20  # Voluntarily Put money In Pot 20%
            self.fold_threshold = 0.30
            self.call_threshold = 0.60
            self.raise_threshold = 0.75
        elif self.style == OpponentStyle.LOOSE:
            self.vpip = 0.50  # 50% VPIP
            self.fold_threshold = 0.15
            self.call_threshold = 0.40
            self.raise_threshold = 0.65
        else:  # RANDOM
            self.vpip = random.uniform(0.25, 0.45)
            self.fold_threshold = random.uniform(0.15, 0.35)
            self.call_threshold = random.uniform(0.40, 0.65)
            self.raise_threshold = random.uniform(0.65, 0.80)
    
    def decide(
        self,
        hand_strength: float,
        pot_size: float,
        bet_to_call: float = 0.0,
        can_check: bool = False
    ) -> OpponentAction:
        """
        Make decision based on hand strength and pot odds.
        
        Args:
            hand_strength: Estimated hand strength (0.0 to 1.0)
            pot_size: Current pot size (in bb)
            bet_to_call: Amount to call (0 if can check)
            can_check: Whether checking is legal
            
        Returns:
            OpponentAction with action type and amount
            
        Educational Note:
            This uses simple thresholds with variance to simulate
            human-like unpredictability and suboptimal play.
        """
        self.hands_played += 1
        
        # Apply variance: randomly adjust hand strength perception
        perceived_strength = self._apply_variance(hand_strength)
        
        # Preflop: VPIP check (but don't fold strong hands)
        if self.hands_played <= 1:  # Simplified preflop detection
            if perceived_strength < 0.50 and random.random() > self.vpip:
                return OpponentAction(
                    action=ActionType.FOLD,
                    reasoning=f"Preflop fold ({self.style.value} VPIP={self.vpip:.0%})"
                )
        
        # Decision tree based on perceived strength
        if perceived_strength < self.fold_threshold:
            # Weak hand - likely fold (unless can check free)
            if can_check and bet_to_call == 0:
                return OpponentAction(
                    action=ActionType.CHECK,
                    reasoning=f"Weak hand ({perceived_strength:.1%}) - free card"
                )
            else:
                return OpponentAction(
                    action=ActionType.FOLD,
                    reasoning=f"Weak hand ({perceived_strength:.1%}) below fold threshold"
                )
        
        elif perceived_strength < self.call_threshold:
            # Medium-weak hand - check or call
            if can_check and random.random() > self.aggression:
                return OpponentAction(
                    action=ActionType.CHECK,
                    reasoning=f"Medium-weak ({perceived_strength:.1%}) - pot control"
                )
            else:
                # Check pot odds
                if bet_to_call > 0:
                    pot_odds = bet_to_call / (pot_size + bet_to_call)
                    if perceived_strength > pot_odds * 1.5:  # Simplified odds
                        return OpponentAction(
                            action=ActionType.CALL,
                            reasoning=f"Call with pot odds ({perceived_strength:.1%} vs {pot_odds:.1%})"
                        )
                    else:
                        return OpponentAction(
                            action=ActionType.FOLD,
                            reasoning="Bad pot odds"
                        )
                else:
                    return OpponentAction(
                        action=ActionType.CHECK,
                        reasoning="Check behind"
                    )
        
        elif perceived_strength < self.raise_threshold:
            # Medium-strong hand - call or bet
            if bet_to_call > 0:
                return OpponentAction(
                    action=ActionType.CALL,
                    reasoning=f"Medium-strong ({perceived_strength:.1%}) - call"
                )
            else:
                # Bet if aggressive enough
                if random.random() < self.aggression:
                    bet_amount = pot_size * random.uniform(0.5, 0.75)
                    return OpponentAction(
                        action=ActionType.BET,
                        amount=bet_amount,
                        reasoning=f"Medium-strong bet ({bet_amount:.1f}bb)"
                    )
                else:
                    return OpponentAction(
                        action=ActionType.CHECK,
                        reasoning="Pot control with medium hand"
                    )
        
        else:
            # Strong hand - bet or raise
            if bet_to_call > 0:
                # Facing a bet - raise or call
                if random.random() < self.aggression:
                    raise_amount = bet_to_call * random.uniform(2.0, 3.5)
                    return OpponentAction(
                        action=ActionType.RAISE,
                        amount=raise_amount,
                        reasoning=f"Strong hand raise ({perceived_strength:.1%})"
                    )
                else:
                    return OpponentAction(
                        action=ActionType.CALL,
                        reasoning=f"Slowplay strong hand ({perceived_strength:.1%})"
                    )
            else:
                # No bet to face - bet big
                bet_amount = pot_size * random.uniform(0.66, 1.0)
                return OpponentAction(
                    action=ActionType.BET,
                    amount=bet_amount,
                    reasoning=f"Strong hand value bet ({perceived_strength:.1%})"
                )
    
    def _apply_variance(self, hand_strength: float) -> float:
        """
        Apply behavioral variance to hand strength perception.
        
        Simulates human error and unpredictability by randomly
        adjusting perceived hand strength.
        
        Args:
            hand_strength: True hand strength (0.0 to 1.0)
            
        Returns:
            Perceived hand strength with variance applied
        """
        if self.variance == 0:
            return hand_strength
        
        # Random adjustment within ±variance range
        adjustment = random.uniform(-self.variance, self.variance)
        perceived = hand_strength + adjustment
        
        # Clamp to valid range
        return max(0.0, min(1.0, perceived))
    
    def update_style(self, new_style: Optional[OpponentStyle] = None) -> None:
        """
        Update opponent's playing style (simulates adaptation).
        
        Args:
            new_style: New style, or None to randomize thresholds
        """
        if new_style:
            self.style = new_style
        else:
            # Randomize thresholds slightly (simulate tilt/adaptation)
            self.vpip = max(0.1, min(0.6, self.vpip + random.uniform(-0.1, 0.1)))
            self.aggression = max(0.2, min(0.8, self.aggression + random.uniform(-0.15, 0.15)))
        
        self._set_thresholds()
    
    def reset_stack(self, new_stack: float) -> None:
        """Reset stack size (new session)."""
        self.stack = new_stack
        self.hands_played = 0


def generate_random_opponent(
    style: Optional[OpponentStyle] = None
) -> DummyOpponent:
    """
    Generate a random dummy opponent for simulation.
    
    Args:
        style: Fixed style, or None for random selection
        
    Returns:
        DummyOpponent with randomized parameters
        
    Educational Note:
        Creates diverse opponents to test HIVE robustness
        against various human playing styles.
    """
    if style is None:
        style = random.choice(list(OpponentStyle))
    
    variance = random.uniform(0.2, 0.4)
    aggression = random.uniform(0.3, 0.7)
    stack = random.uniform(800.0, 1200.0)
    
    return DummyOpponent(
        style=style,
        variance=variance,
        aggression=aggression,
        stack=stack
    )


def estimate_hand_strength(hole_cards: List[str], board: List[str] = None) -> float:
    """
    Simplified hand strength estimator for dummy opponent.
    
    This is an intentionally basic heuristic for research purposes.
    Real poker AI would use Monte Carlo simulation or lookup tables.
    
    Args:
        hole_cards: Two hole cards (e.g., ["As", "Kh"])
        board: Community cards (0-5 cards)
        
    Returns:
        Hand strength estimate (0.0 to 1.0)
        
    Educational Note:
        Simplified for computational efficiency in large simulations.
        Not intended as realistic equity calculator.
    """
    if board is None:
        board = []
    
    # Card rank values
    rank_values = {
        'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
        '9': 9, '8': 8, '7': 7, '6': 6, '5': 5,
        '4': 4, '3': 3, '2': 2
    }
    
    # Parse hole cards
    if len(hole_cards) < 2:
        return 0.1  # Very weak if not full hand
    
    rank1 = rank_values.get(hole_cards[0][0], 2)
    rank2 = rank_values.get(hole_cards[1][0], 2)
    
    # Base strength from high card
    max_rank = max(rank1, rank2)
    base_strength = max_rank / 14.0  # Normalize to 0-1
    
    # Pair bonus
    if rank1 == rank2:
        pair_bonus = 0.2 + (rank1 / 14.0) * 0.15
        base_strength = min(1.0, base_strength + pair_bonus)
    
    # Suited bonus (simplified)
    if len(hole_cards[0]) > 1 and len(hole_cards[1]) > 1:
        if hole_cards[0][1] == hole_cards[1][1]:
            base_strength = min(1.0, base_strength + 0.05)
    
    # Connectivity bonus (simplified)
    if abs(rank1 - rank2) <= 4:
        base_strength = min(1.0, base_strength + 0.03)
    
    # Board interaction (very simplified)
    if board:
        board_ranks = [rank_values.get(card[0], 2) for card in board if card]
        # Check for top pair
        if max_rank in board_ranks:
            base_strength = min(1.0, base_strength + 0.15)
    
    return base_strength


# Educational Example Usage
if __name__ == "__main__":
    # Create dummy opponents with different styles
    tight_opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.2, aggression=0.3)
    loose_opp = DummyOpponent(OpponentStyle.LOOSE, variance=0.4, aggression=0.7)
    random_opp = generate_random_opponent()
    
    # Simulate decisions with different hand strengths
    test_strengths = [0.25, 0.50, 0.75, 0.90]
    pot = 100.0
    
    print("Dummy Opponent Decision Examples:\n")
    
    for strength in test_strengths:
        print(f"Hand Strength: {strength:.0%}")
        
        # Tight opponent
        action = tight_opp.decide(strength, pot, bet_to_call=30.0)
        print(f"  Tight: {action.action.value} - {action.reasoning}")
        
        # Loose opponent
        action = loose_opp.decide(strength, pot, bet_to_call=30.0)
        print(f"  Loose: {action.action.value} - {action.reasoning}")
        
        # Random opponent
        action = random_opp.decide(strength, pot, bet_to_call=30.0)
        print(f"  Random: {action.action.value} - {action.reasoning}")
        
        print()
    
    # Test hand strength estimator
    print("Hand Strength Estimates:")
    test_hands = [
        (["As", "Ah"], [], "Pocket Aces"),
        (["Ks", "Qh"], [], "King-Queen offsuit"),
        (["7s", "2h"], [], "Seven-deuce offsuit"),
        (["Ts", "9s"], [], "Ten-nine suited")
    ]
    
    for hole, board, desc in test_hands:
        strength = estimate_hand_strength(hole, board)
        print(f"  {desc}: {strength:.1%}")
