"""
Multi-Agent Decision Module for Simulation Research.

This module provides decision modeling capabilities for multi-agent game theory
simulations. Built on top of Range Model v0 and Postflop Line Logic v2, it
generates simulated actions with sizing for educational research purposes.

Educational Use Only: Designed for controlled virtual environments and academic
study of strategic decision-making in multi-agent systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from coach_app.engine import (
    Range,
    calculate_monte_carlo_equity,
    recommend_postflop,
    recommend_preflop,
)
from coach_app.schemas.common import Street
from coach_app.schemas.poker import PokerActionType, Position


class SimulatedActionType(Enum):
    """
    Action types for multi-agent simulations.
    
    Uses abstract terminology (increment/hold/decrement) for research purposes
    rather than poker-specific terms.
    
    Educational Note:
        These action types are generalized for game theory research and can
        map to various strategic scenarios beyond poker. In poker context:
        - INCREMENT: bet/raise (increase pot/commitment)
        - HOLD: call (maintain current commitment)
        - DECREMENT: fold (reduce commitment to zero)
        - CHECK: check (neutral action, no change)
    """
    INCREMENT = "increment"  # Aggressive action: bet/raise
    HOLD = "hold"  # Neutral/defensive: call
    DECREMENT = "decrement"  # Exit action: fold
    CHECK = "check"  # Passive neutral: check


class LineType(Enum):
    """
    Strategic line types for multi-agent decision modeling.
    
    Educational Note:
        Line types represent meta-strategies in game theory simulations.
        They help model different behavioral patterns and strategic approaches
        that agents might take in competitive scenarios.
    """
    PROACTIVE = "proactive"  # Aggressive, initiative-taking
    REACTIVE = "reactive"  # Defensive, responsive to opponents
    BALANCED = "balanced"  # Mixed strategy
    EXPLOITATIVE = "exploitative"  # Opponent-specific adaptation


@dataclass
class SimulationDecision:
    """
    Decision output for multi-agent simulation.
    
    Attributes:
        action: Simulated action type (increment/hold/decrement/check)
        sizing: Action sizing in base units (e.g., BB for poker)
        confidence: Decision confidence level (0.0-1.0)
        equity: Estimated equity/win probability (0.0-1.0)
        line_type: Strategic line being pursued
        reasoning: Key decision factors for analysis
        
    Educational Note:
        This structured decision format enables systematic analysis of
        multi-agent strategic interactions in research scenarios.
    """
    action: SimulatedActionType
    sizing: float | None
    confidence: float
    equity: float
    line_type: LineType
    reasoning: dict[str, Any]
    
    def __post_init__(self):
        """Validate decision fields."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0,1], got {self.confidence}")
        
        if not 0.0 <= self.equity <= 1.0:
            raise ValueError(f"Equity must be in [0,1], got {self.equity}")
        
        if self.sizing is not None and self.sizing < 0:
            raise ValueError(f"Sizing cannot be negative, got {self.sizing}")
        
        # Validate sizing requirements
        if self.action == SimulatedActionType.INCREMENT and self.sizing is None:
            raise ValueError("INCREMENT action requires sizing")
        
        if self.action in [SimulatedActionType.DECREMENT, SimulatedActionType.CHECK]:
            if self.sizing is not None and self.sizing != 0:
                raise ValueError(f"{self.action.value} should not have non-zero sizing")


@dataclass
class AgentContext:
    """
    Context information for agent decision-making.
    
    Attributes:
        position: Agent's position in the scenario
        resource_bucket: Resource level category (e.g., "high", "medium", "low")
        opponent_models: Dict of opponent_id -> behavioral statistics
        session_state: Current session metrics (hands played, performance, etc.)
        
    Educational Note:
        Context provides the environmental and historical information that
        agents use to make informed decisions in simulations.
    """
    position: Position | str
    resource_bucket: str
    opponent_models: dict[str, dict[str, float]]
    session_state: dict[str, Any]


def generate_simulated_decision(
    agent_state: list[str],
    environment: list[str],
    street: Street,
    pot_bb: float,
    to_call_bb: float,
    context: AgentContext,
    *,
    use_monte_carlo: bool = True,
    num_simulations: int = 1000,
    probability_threshold: float = 0.6,
) -> SimulationDecision:
    """
    Generate decision for multi-agent simulation using Range Model v0 and
    Postflop Line Logic v2 as foundation.
    
    Algorithm:
    1. Estimate opponent range based on context
    2. Calculate equity (Monte Carlo if enabled, heuristic otherwise)
    3. Determine strategic line (proactive/reactive/balanced)
    4. Generate action based on equity and line type
    5. Calculate appropriate sizing
    
    Args:
        agent_state: Agent's hole cards, e.g., ["Ah", "Ks"]
        environment: Community cards (board), e.g., ["Ad", "7c", "2s"]
        street: Current street (preflop/flop/turn/river)
        pot_bb: Current pot size in big blinds
        to_call_bb: Amount to call in big blinds
        context: Agent context (position, resources, opponents)
        use_monte_carlo: Enable Monte Carlo equity calculation
        num_simulations: Number of MC simulations (if enabled)
        probability_threshold: Threshold for proactive vs reactive (default 0.6)
    
    Returns:
        SimulationDecision with action, sizing, confidence, and reasoning
    
    Educational Note:
        This function models strategic decision-making in multi-agent scenarios
        for research purposes. It combines deterministic heuristics (Range Model v0,
        Postflop Logic v2) with probabilistic modeling (Monte Carlo) to simulate
        realistic agent behavior in controlled environments.
    
    Example:
        >>> context = AgentContext(
        ...     position=Position.BTN,
        ...     resource_bucket="high",
        ...     opponent_models={"villain1": {"vpip": 0.28, "pfr": 0.22}},
        ...     session_state={"hands_played": 50, "bb_won": 15.5}
        ... )
        >>> decision = generate_simulated_decision(
        ...     agent_state=["Ah", "Ks"],
        ...     environment=["Ad", "7c", "2s"],
        ...     street=Street.FLOP,
        ...     pot_bb=12.0,
        ...     to_call_bb=0.0,
        ...     context=context
        ... )
        >>> print(decision.action)  # SimulatedActionType.INCREMENT
    """
    reasoning: dict[str, Any] = {}
    
    # Step 1: Estimate opponent range
    opponent_range = _estimate_opponent_range(
        street=street,
        context=context,
        pot_bb=pot_bb,
        to_call_bb=to_call_bb
    )
    reasoning["opponent_range_size"] = len(opponent_range.hands)
    
    # Step 2: Calculate equity
    if use_monte_carlo and len(opponent_range.hands) > 0:
        try:
            equity_result = calculate_monte_carlo_equity(
                hero_hand=agent_state,
                opponent_range=opponent_range,
                board=environment,
                num_simulations=num_simulations
            )
            equity = equity_result.equity
            reasoning["equity_source"] = "monte_carlo"
            reasoning["simulations"] = equity_result.total_simulations
        except Exception as e:
            # Fallback to heuristic
            equity = _heuristic_equity(agent_state, environment, street)
            reasoning["equity_source"] = "heuristic_fallback"
            reasoning["monte_carlo_error"] = str(e)
    else:
        equity = _heuristic_equity(agent_state, environment, street)
        reasoning["equity_source"] = "heuristic"
    
    reasoning["equity"] = equity
    
    # Step 3: Determine strategic line
    line_type = _determine_line_type(
        equity=equity,
        context=context,
        probability_threshold=probability_threshold
    )
    reasoning["line_type"] = line_type.value
    
    # Step 4: Generate action based on equity and line
    pot_odds = to_call_bb / (pot_bb + to_call_bb) if (pot_bb + to_call_bb) > 0 else 0
    reasoning["pot_odds"] = pot_odds
    
    action, confidence = _select_action(
        equity=equity,
        pot_odds=pot_odds,
        line_type=line_type,
        to_call_bb=to_call_bb,
        context=context
    )
    
    # Step 5: Calculate sizing
    sizing = _calculate_sizing(
        action=action,
        pot_bb=pot_bb,
        equity=equity,
        line_type=line_type,
        street=street
    )
    
    return SimulationDecision(
        action=action,
        sizing=sizing,
        confidence=confidence,
        equity=equity,
        line_type=line_type,
        reasoning=reasoning
    )


def _estimate_opponent_range(
    street: Street,
    context: AgentContext,
    pot_bb: float,
    to_call_bb: float
) -> Range:
    """
    Estimate opponent range based on context and game state.
    
    Uses opponent modeling statistics and position to construct
    likely range for educational simulations.
    
    Educational Note:
        Range estimation is a critical component of multi-agent modeling.
        This heuristic approach provides reasonable estimates for research
        purposes but should not be used for production applications.
    """
    # Default ranges based on position and aggression
    default_ranges = {
        "tight": {"AA": 1.0, "KK": 1.0, "QQ": 1.0, "AKs": 0.95, "AKo": 0.85},
        "normal": {
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 0.9, "TT": 0.8,
            "AKs": 0.95, "AKo": 0.85, "AQs": 0.9, "AQo": 0.75, "KQs": 0.7
        },
        "loose": {
            "AA": 1.0, "KK": 1.0, "QQ": 1.0, "JJ": 0.95, "TT": 0.9,
            "99": 0.85, "88": 0.75,
            "AKs": 1.0, "AKo": 0.9, "AQs": 0.95, "AQo": 0.85,
            "AJs": 0.85, "AJo": 0.75, "KQs": 0.8, "KQo": 0.65,
            "JTs": 0.7, "T9s": 0.6
        }
    }
    
    # Estimate opponent tightness from models
    if context.opponent_models:
        # Average VPIP/PFR from all opponents
        avg_vpip = sum(
            model.get("vpip", 0.25) 
            for model in context.opponent_models.values()
        ) / len(context.opponent_models)
        
        if avg_vpip < 0.20:
            range_type = "tight"
        elif avg_vpip > 0.35:
            range_type = "loose"
        else:
            range_type = "normal"
    else:
        range_type = "normal"
    
    hands = default_ranges[range_type].copy()
    
    return Range(
        hands=hands,
        metadata={
            "estimated_type": range_type,
            "street": street.value,
            "pot_bb": pot_bb
        }
    )


def _heuristic_equity(
    agent_state: list[str],
    environment: list[str],
    street: Street
) -> float:
    """
    Simple heuristic for equity estimation when Monte Carlo unavailable.
    
    Educational Note:
        This is an intentionally simplified heuristic for simulation purposes.
        Real applications should use proper equity calculators.
    """
    # Very rough heuristics based on street and hand strength indicators
    if street == Street.PREFLOP:
        # Check for premium hands
        ranks = [c[0] for c in agent_state]
        if ranks[0] == ranks[1]:  # Pocket pair
            if ranks[0] in "AKQ":
                return 0.80  # Premium pair
            elif ranks[0] in "JT9":
                return 0.60  # Medium pair
            else:
                return 0.50  # Small pair
        elif 'A' in ranks and 'K' in ranks:
            return 0.65  # AK
        elif 'A' in ranks:
            return 0.55  # Ace-high
        else:
            return 0.45  # Random hand
    
    # Postflop: assume 50% if we have any equity
    return 0.50


def _determine_line_type(
    equity: float,
    context: AgentContext,
    probability_threshold: float
) -> LineType:
    """
    Determine strategic line based on equity and context.
    
    Educational Note:
        Line selection models meta-strategy in multi-agent systems.
        Threshold-based selection (>60% for proactive) represents
        a simplified decision boundary for research purposes.
    """
    # Proactive if equity exceeds threshold
    if equity >= probability_threshold:
        return LineType.PROACTIVE
    
    # Reactive if equity is marginal
    if equity >= probability_threshold * 0.7:  # e.g., 42% if threshold is 60%
        return LineType.REACTIVE
    
    # Exploitative if we have opponent models
    if context.opponent_models and 0.3 <= equity < probability_threshold * 0.7:
        return LineType.EXPLOITATIVE
    
    # Balanced otherwise
    return LineType.BALANCED


def _select_action(
    equity: float,
    pot_odds: float,
    line_type: LineType,
    to_call_bb: float,
    context: AgentContext
) -> tuple[SimulatedActionType, float]:
    """
    Select action based on equity, pot odds, and strategic line.
    
    Subsequent Phases Enhancement (Подпункт 1.2):
    - Expanded line logic with probability thresholds
    - Proactive line: >60% equity triggers aggressive actions
    - Reactive line: defensive with pot odds + buffer
    - Exploitative line: opponent-specific adaptations
    - Uses enums for type safety
    - Validates all outputs
    
    Returns:
        (action, confidence) tuple
    
    Educational Note:
        Action selection combines equity-based decision theory with
        strategic line modeling for educational simulations. Subsequent
        phases add nuanced probability thresholds (>60% for proactive)
        and opponent-specific exploitation strategies.
    """
    confidence = 0.5  # Base confidence
    
    # No amount to call: check or increment
    if to_call_bb == 0:
        # Subsequent phases: refined thresholds for initial phases
        if line_type == LineType.PROACTIVE:
            if equity >= 0.70:
                # Very strong: definitely increment
                return SimulatedActionType.INCREMENT, min(0.95, equity + 0.05)
            elif equity >= 0.60:
                # Strong: increment with medium confidence
                return SimulatedActionType.INCREMENT, min(0.85, equity)
            elif equity >= 0.50:
                # Medium: check (pot control)
                return SimulatedActionType.CHECK, 0.75
            else:
                # Weak: check
                return SimulatedActionType.CHECK, 0.60
        
        elif line_type == LineType.REACTIVE:
            # Reactive: prefer checking over betting
            if equity >= 0.65:
                # Strong enough to bet
                return SimulatedActionType.INCREMENT, min(0.80, equity)
            else:
                # Check otherwise
                return SimulatedActionType.CHECK, 0.70
        
        elif line_type == LineType.EXPLOITATIVE:
            # Exploitative: adjust based on opponent tendencies
            exploit_action = _exploitative_action_no_bet(equity, context)
            return exploit_action
        
        else:  # BALANCED
            if equity >= 0.55:
                return SimulatedActionType.CHECK, 0.70  # Balanced: check mostly
            else:
                return SimulatedActionType.CHECK, 0.65
    
    # Facing a bet: compare equity to pot odds
    equity_advantage = equity - pot_odds
    
    if line_type == LineType.PROACTIVE:
        # Subsequent phases: >60% equity threshold for aggressive play
        if equity >= 0.70 and equity_advantage > 0.15:
            # Very strong advantage: increment (raise)
            return SimulatedActionType.INCREMENT, min(0.95, equity + 0.1)
        elif equity >= 0.60 and equity_advantage > 0.05:
            # Strong advantage (>60% threshold): increment
            return SimulatedActionType.INCREMENT, min(0.90, equity + 0.05)
        elif equity_advantage > 0:
            # Slight advantage: hold (call)
            return SimulatedActionType.HOLD, min(0.80, equity)
        else:
            # No advantage: decrement (fold)
            return SimulatedActionType.DECREMENT, 0.70
    
    elif line_type == LineType.REACTIVE:
        # Reactive: needs extra buffer on pot odds
        buffer = 0.05  # 5% equity buffer for defensive play
        
        if equity > pot_odds + buffer + 0.10:
            # Strong equity advantage: consider raise
            return SimulatedActionType.INCREMENT, min(0.85, equity)
        elif equity > pot_odds + buffer:
            # Good equity: call
            return SimulatedActionType.HOLD, min(0.75, equity)
        elif equity > pot_odds - 0.03:
            # Marginal: call with low confidence
            return SimulatedActionType.HOLD, 0.60
        else:
            # Fold otherwise
            return SimulatedActionType.DECREMENT, 0.65
    
    elif line_type == LineType.EXPLOITATIVE:
        # Exploitative: adjust based on opponent patterns
        exploit_action = _exploitative_action_facing_bet(
            equity, pot_odds, equity_advantage, context
        )
        return exploit_action
    
    else:  # BALANCED
        if equity > pot_odds + 0.03:
            # Slight edge: call
            return SimulatedActionType.HOLD, min(0.70, equity)
        elif equity > pot_odds - 0.02:
            # Very marginal: fold
            return SimulatedActionType.DECREMENT, 0.60
        else:
            return SimulatedActionType.DECREMENT, 0.65


def _exploitative_action_no_bet(
    equity: float,
    context: AgentContext
) -> tuple[SimulatedActionType, float]:
    """
    Exploitative action when not facing a bet.
    
    Subsequent Phases: Adapts to opponent tendencies for educational research.
    """
    if not context.opponent_models:
        # No data: default to check
        return SimulatedActionType.CHECK, 0.65
    
    # Average opponent fold-to-bet tendency (estimated)
    avg_fold = sum(
        model.get("fold_to_cbet", 0.5)
        for model in context.opponent_models.values()
    ) / len(context.opponent_models)
    
    # If opponents fold too much, bluff more
    if avg_fold > 0.65:
        # Opponents fold often: bet even with medium equity
        if equity >= 0.40:
            return SimulatedActionType.INCREMENT, 0.75
        else:
            return SimulatedActionType.CHECK, 0.60
    
    # If opponents don't fold much, bet for value only
    if avg_fold < 0.45:
        if equity >= 0.65:
            return SimulatedActionType.INCREMENT, 0.80
        else:
            return SimulatedActionType.CHECK, 0.70
    
    # Balanced approach
    if equity >= 0.55:
        return SimulatedActionType.INCREMENT, 0.70
    else:
        return SimulatedActionType.CHECK, 0.65


def _exploitative_action_facing_bet(
    equity: float,
    pot_odds: float,
    equity_advantage: float,
    context: AgentContext
) -> tuple[SimulatedActionType, float]:
    """
    Exploitative action when facing a bet.
    
    Subsequent Phases: Opponent-specific adaptations for research.
    """
    if not context.opponent_models:
        # No data: use equity vs pot odds
        if equity > pot_odds:
            return SimulatedActionType.HOLD, min(0.70, equity)
        else:
            return SimulatedActionType.DECREMENT, 0.65
    
    # Average opponent aggression
    avg_aggression = sum(
        model.get("aggression_factor", 2.0)
        for model in context.opponent_models.values()
    ) / len(context.opponent_models)
    
    # Against aggressive opponents (bluff more): can call lighter
    if avg_aggression > 3.0:
        # Aggressive opponent: call with slightly worse pot odds
        if equity > pot_odds - 0.05:
            return SimulatedActionType.HOLD, min(0.75, equity)
        else:
            return SimulatedActionType.DECREMENT, 0.65
    
    # Against passive opponents: need better pot odds
    if avg_aggression < 1.5:
        # Passive opponent (value heavy): fold more
        if equity > pot_odds + 0.08:
            return SimulatedActionType.HOLD, min(0.75, equity)
        else:
            return SimulatedActionType.DECREMENT, 0.70
    
    # Balanced
    if equity > pot_odds:
        return SimulatedActionType.HOLD, min(0.70, equity)
    else:
        return SimulatedActionType.DECREMENT, 0.65


def _calculate_sizing(
    action: SimulatedActionType,
    pot_bb: float,
    equity: float,
    line_type: LineType,
    street: Street
) -> float | None:
    """
    Calculate appropriate sizing for increment actions.
    
    Educational Note:
        Sizing models the magnitude of strategic commitments in
        competitive scenarios. Varies by line type and game state.
    """
    if action != SimulatedActionType.INCREMENT:
        return None if action in [SimulatedActionType.CHECK, SimulatedActionType.DECREMENT] else 0.0
    
    # Base sizing on line type and equity
    if line_type == LineType.PROACTIVE:
        # Aggressive sizing
        if equity >= 0.75:
            # Very strong: large sizing (80-100% pot)
            multiplier = 0.85 + (equity - 0.75) * 0.6
        else:
            # Strong: standard sizing (60-75% pot)
            multiplier = 0.60 + (equity - 0.60) * 0.5
    
    elif line_type == LineType.REACTIVE:
        # Conservative sizing (40-60% pot)
        multiplier = 0.40 + equity * 0.3
    
    elif line_type == LineType.EXPLOITATIVE:
        # Variable sizing based on opponent
        multiplier = 0.50 + equity * 0.4
    
    else:  # BALANCED
        # Standard sizing (50-70% pot)
        multiplier = 0.50 + equity * 0.3
    
    # Adjust by street (later streets: larger sizing)
    street_multipliers = {
        Street.PREFLOP: 1.0,
        Street.FLOP: 1.0,
        Street.TURN: 1.15,
        Street.RIVER: 1.25
    }
    
    multiplier *= street_multipliers.get(street, 1.0)
    
    sizing = pot_bb * multiplier
    
    # Minimum sizing: 0.33 pot (33% pot)
    # Maximum sizing: 1.5 pot (150% pot, overbet)
    sizing = max(pot_bb * 0.33, min(pot_bb * 1.5, sizing))
    
    return round(sizing, 2)
