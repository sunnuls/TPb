"""
Decision engines for poker/blackjack with simulation support.

This module provides core decision-making logic for single-agent coaching
and multi-agent simulation research. Includes deterministic heuristics
(Range Model v0, Postflop Line Logic v2) and probabilistic equity calculations
for educational game theory simulations.

Educational Use Only: Multi-agent simulation features are designed for
controlled virtual environments and academic research purposes.
"""

from __future__ import annotations

# Core decision engines
from coach_app.engine.poker.analyze import analyze_poker_state
from coach_app.engine.blackjack.analyze import analyze_blackjack

# Simulation-specific equity calculations (for multi-agent research)
from coach_app.engine.simulation_equity import (
    calculate_monte_carlo_equity,
    calculate_equity_vs_specific_hand,
    EquityResult,
)

# Range Model v0 (deterministic heuristics)
from coach_app.engine.poker.ranges.range import Range

# Postflop Line Logic v2
from coach_app.engine.poker.postflop import recommend_postflop, PostflopPlan
from coach_app.engine.poker.preflop import recommend_preflop, PreflopPlan

__all__ = [
    # Single-agent decision engines
    "analyze_poker_state",
    "analyze_blackjack",
    
    # Simulation equity calculations
    "calculate_monte_carlo_equity",
    "calculate_equity_vs_specific_hand",
    "EquityResult",
    
    # Range Model v0
    "Range",
    
    # Postflop/Preflop logic
    "recommend_postflop",
    "PostflopPlan",
    "recommend_preflop",
    "PreflopPlan",
]

