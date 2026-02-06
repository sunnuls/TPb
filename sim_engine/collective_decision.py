"""
Collective Decision Module for HIVE Strategy (Roadmap2 Phase 2).

This module implements decision-making logic for multi-agent coordination
based on pooled hole cards and collective equity calculations.

Educational Use Only: For research into emergent cooperation patterns
in multi-agent game theory simulations. Not for production use.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ActionType(str, Enum):
    """Poker action types for collective decisions."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


class LineType(str, Enum):
    """Strategic line types based on collective edge."""
    AGGRESSIVE = "aggressive"  # Large bets, raises, all-ins
    PROTECTIVE = "protective"  # Pot control, check/call
    PASSIVE = "passive"  # Fold, minimal investment


@dataclass
class CollectiveState:
    """
    Shared state for HIVE group decision-making.
    
    Attributes:
        collective_cards: All hole cards known to the group
        collective_equity: Estimated win probability vs dummy opponent
        agent_count: Number of agents in the HIVE
        pot_size: Current pot (in bb)
        stack_sizes: Dict of agent_id -> stack (in bb)
        board: Community cards
        dummy_range: Opponent's estimated range
    """
    collective_cards: List[str]
    collective_equity: float
    agent_count: int
    pot_size: float = 0.0
    stack_sizes: Dict[str, float] = None
    board: List[str] = None
    dummy_range: str = "random"
    
    def __post_init__(self):
        if self.stack_sizes is None:
            self.stack_sizes = {}
        if self.board is None:
            self.board = []


@dataclass
class CollectiveDecision:
    """
    Decision output for HIVE group.
    
    Attributes:
        action: Recommended action type
        line_type: Strategic line (aggressive/protective/passive)
        bet_size: Bet/raise size (in bb or as fraction of pot)
        reasoning: Explanation of decision logic
        confidence: Decision confidence (0.0 to 1.0)
    """
    action: ActionType
    line_type: LineType
    bet_size: Optional[float] = None
    reasoning: str = ""
    confidence: float = 0.5


class CollectiveDecisionEngine:
    """
    Decision engine for HIVE collective strategy.
    
    Core Logic (Roadmap2 Phase 2):
    - If collective_equity > 65% → Aggressive line (large bet/raise/all-in)
    - Else → Protective/passive line (check/call/fold)
    
    Educational Note:
        This engine demonstrates how shared information enables
        coordinated aggressive strategies when collective edge is high.
        For academic study of multi-agent cooperation only.
    """
    
    def __init__(
        self,
        aggressive_threshold: float = 0.65,
        protective_threshold: float = 0.45
    ):
        """
        Initialize collective decision engine.
        
        Args:
            aggressive_threshold: Equity threshold for aggressive play
            protective_threshold: Minimum equity for protective play
        """
        self.aggressive_threshold = aggressive_threshold
        self.protective_threshold = protective_threshold
    
    def decide(
        self,
        state: CollectiveState,
        legal_actions: Optional[List[ActionType]] = None
    ) -> CollectiveDecision:
        """
        Make collective decision based on HIVE state.
        
        Args:
            state: Current collective state
            legal_actions: Available actions (default: all)
            
        Returns:
            CollectiveDecision with action, line, and reasoning
            
        Educational Note:
            This demonstrates threshold-based coordination where
            agents agree on aggressive strategy when edge is sufficient.
        """
        if legal_actions is None:
            legal_actions = list(ActionType)
        
        equity = state.collective_equity
        
        # Phase 2 Core Logic: Aggressive if equity > 65%
        if equity >= self.aggressive_threshold:
            return self._decide_aggressive(state, legal_actions)
        elif equity >= self.protective_threshold:
            return self._decide_protective(state, legal_actions)
        else:
            return self._decide_passive(state, legal_actions)
    
    def _decide_aggressive(
        self,
        state: CollectiveState,
        legal_actions: List[ActionType]
    ) -> CollectiveDecision:
        """
        Aggressive line: Large bets, raises, all-ins.
        
        Used when collective equity > 65% (HIVE has strong edge).
        """
        # Prefer all-in or large raise
        if ActionType.ALL_IN in legal_actions:
            return CollectiveDecision(
                action=ActionType.ALL_IN,
                line_type=LineType.AGGRESSIVE,
                bet_size=None,  # All-in
                reasoning=f"Collective equity {state.collective_equity:.1%} > 65% - HIVE all-in",
                confidence=0.9
            )
        
        if ActionType.RAISE in legal_actions:
            bet_size = state.pot_size * 1.5  # 1.5x pot raise
            return CollectiveDecision(
                action=ActionType.RAISE,
                line_type=LineType.AGGRESSIVE,
                bet_size=bet_size,
                reasoning=f"Collective equity {state.collective_equity:.1%} - large raise",
                confidence=0.85
            )
        
        if ActionType.BET in legal_actions:
            bet_size = state.pot_size * 0.75  # 3/4 pot bet
            return CollectiveDecision(
                action=ActionType.BET,
                line_type=LineType.AGGRESSIVE,
                bet_size=bet_size,
                reasoning=f"Collective equity {state.collective_equity:.1%} - large bet",
                confidence=0.8
            )
        
        # Fallback: call aggressively
        if ActionType.CALL in legal_actions:
            return CollectiveDecision(
                action=ActionType.CALL,
                line_type=LineType.AGGRESSIVE,
                reasoning="Call to see showdown with strong collective equity",
                confidence=0.7
            )
        
        return CollectiveDecision(
            action=ActionType.CHECK,
            line_type=LineType.AGGRESSIVE,
            reasoning="Check (no aggressive options available)",
            confidence=0.5
        )
    
    def _decide_protective(
        self,
        state: CollectiveState,
        legal_actions: List[ActionType]
    ) -> CollectiveDecision:
        """
        Protective line: Pot control, check/call.
        
        Used when 45% ≤ equity < 65% (medium strength).
        """
        if ActionType.CHECK in legal_actions:
            return CollectiveDecision(
                action=ActionType.CHECK,
                line_type=LineType.PROTECTIVE,
                reasoning=f"Medium equity {state.collective_equity:.1%} - pot control",
                confidence=0.6
            )
        
        if ActionType.CALL in legal_actions:
            return CollectiveDecision(
                action=ActionType.CALL,
                line_type=LineType.PROTECTIVE,
                reasoning=f"Equity {state.collective_equity:.1%} - call to showdown",
                confidence=0.55
            )
        
        # Small bet if forced to act
        if ActionType.BET in legal_actions:
            bet_size = state.pot_size * 0.33  # 1/3 pot
            return CollectiveDecision(
                action=ActionType.BET,
                line_type=LineType.PROTECTIVE,
                bet_size=bet_size,
                reasoning="Small probe bet with medium equity",
                confidence=0.5
            )
        
        return CollectiveDecision(
            action=ActionType.FOLD,
            line_type=LineType.PROTECTIVE,
            reasoning="Fold - no safe protective actions",
            confidence=0.4
        )
    
    def _decide_passive(
        self,
        state: CollectiveState,
        legal_actions: List[ActionType]
    ) -> CollectiveDecision:
        """
        Passive line: Fold, minimal investment.
        
        Used when equity < 45% (weak collective hand).
        """
        if ActionType.FOLD in legal_actions:
            return CollectiveDecision(
                action=ActionType.FOLD,
                line_type=LineType.PASSIVE,
                reasoning=f"Low equity {state.collective_equity:.1%} - fold",
                confidence=0.7
            )
        
        if ActionType.CHECK in legal_actions:
            return CollectiveDecision(
                action=ActionType.CHECK,
                line_type=LineType.PASSIVE,
                reasoning="Check - no investment with weak hand",
                confidence=0.6
            )
        
        # Reluctant call if no other options
        if ActionType.CALL in legal_actions:
            return CollectiveDecision(
                action=ActionType.CALL,
                line_type=LineType.PASSIVE,
                reasoning="Reluctant call - low equity but pot odds",
                confidence=0.3
            )
        
        return CollectiveDecision(
            action=ActionType.FOLD,
            line_type=LineType.PASSIVE,
            reasoning="Fold - weak collective hand",
            confidence=0.5
        )


def calculate_optimal_bet_size(
    equity: float,
    pot_size: float,
    stack_size: float
) -> float:
    """
    Calculate optimal bet size based on equity and pot.
    
    Args:
        equity: Collective equity (0.0 to 1.0)
        pot_size: Current pot (in bb)
        stack_size: Agent's available stack (in bb)
        
    Returns:
        Recommended bet size (in bb)
        
    Educational Note:
        Simple bet sizing model based on equity.
        Real implementations use game theory optimal (GTO) solvers.
    """
    if equity >= 0.65:
        # Aggressive: 0.75x to 1.5x pot
        bet = pot_size * (0.75 + equity * 0.75)
    elif equity >= 0.45:
        # Protective: 0.33x to 0.5x pot
        bet = pot_size * 0.4
    else:
        # Passive: minimal
        bet = pot_size * 0.25
    
    # Cap at stack size
    return min(bet, stack_size)


# Educational Example Usage
if __name__ == "__main__":
    # Example: 3 agents in HIVE with strong collective equity
    state = CollectiveState(
        collective_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
        collective_equity=0.72,  # 72% - above aggressive threshold
        agent_count=3,
        pot_size=100.0,
        stack_sizes={"agent1": 500, "agent2": 450, "agent3": 480},
        board=["Js", "Ts", "9h"]
    )
    
    engine = CollectiveDecisionEngine()
    decision = engine.decide(state)
    
    print(f"HIVE Decision: {decision.action.value}")
    print(f"Line Type: {decision.line_type.value}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Confidence: {decision.confidence:.1%}")
    
    if decision.bet_size:
        print(f"Bet Size: {decision.bet_size:.1f} bb")
