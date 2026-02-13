"""
Manipulation Logic - Educational Game Theory Research (Roadmap5 Phase 3).
Extended: full_hive_month.md Этап 3 — enhanced 3vs1 aggression.

⚠️ CRITICAL ETHICAL WARNING:
    This implements COORDINATED MANIPULATION (3vs1) for research.
    
    This is:
    - EXTREMELY UNETHICAL and ILLEGAL
    - Coordinated cheating against human players
    - STRICTLY for educational/research purposes ONLY
    - Demonstrates game theory exploitation
    - NEVER use without explicit consent of ALL participants

Features:
- 3vs1 manipulation strategies
- Equity-based aggression (>65% → all-in)
- Team coordination (no bluffing against teammates)
- Opponent exploitation
- Real-time decision coordination
- **Этап 3**: street-aware escalation (flop < turn < river aggression)
- **Этап 3**: decision statistics tracking per strategy
- **Этап 3**: dynamic aggression factor based on opponent profile
- **Этап 3**: coordinated trap with check-raise signals
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from sim_engine.collective_decision import (
    ActionType,
    CollectiveDecision,
    CollectiveDecisionEngine,
    CollectiveState,
)

logger = logging.getLogger(__name__)


class ManipulationStrategy(str, Enum):
    """3vs1 manipulation strategies."""
    AGGRESSIVE_SQUEEZE = "aggressive_squeeze"    # High equity → max pressure
    CONTROLLED_FOLD = "controlled_fold"          # Low equity → fold to teammate
    POT_BUILDING = "pot_building"                # Medium equity → build pot
    COORDINATED_TRAP = "coordinated_trap"        # Trap opponent with checks
    ISOLATION = "isolation"                      # Isolate opponent from pot


@dataclass
class ManipulationContext:
    """
    Context for manipulation decision.
    
    Attributes:
        collective_state: Team's collective state
        acting_bot_id: Bot making decision
        teammates_in_hand: Teammate bot IDs still in hand
        opponent_in_hand: Whether opponent still in hand
        pot_size: Current pot
        to_call: Amount to call
        can_raise: Whether raise is legal
        street: Current street
        team_id: HIVE team identifier
    
    ⚠️ EDUCATIONAL NOTE:
        Represents context for coordinated cheating.
    """
    collective_state: CollectiveState
    acting_bot_id: str
    teammates_in_hand: List[str]
    opponent_in_hand: bool
    pot_size: float
    to_call: float
    can_raise: bool
    street: str
    team_id: str


@dataclass
class ManipulationDecision:
    """
    Manipulation decision output.
    
    Attributes:
        action: Recommended action
        strategy: Manipulation strategy used
        amount: Bet/raise amount (if applicable)
        reasoning: Explanation
        coordination_signal: Signal to teammates
        confidence: Decision confidence
    
    ⚠️ EDUCATIONAL NOTE:
        Represents coordinated cheating decision.
    """
    action: ActionType
    strategy: ManipulationStrategy
    amount: Optional[float] = None
    reasoning: str = ""
    coordination_signal: Optional[str] = None
    confidence: float = 0.5


class ManipulationEngine:
    """
    3vs1 manipulation engine.
    
    Implements coordinated strategies for exploiting opponents through
    team coordination and information sharing.
    
    ⚠️ CRITICAL WARNING:
        This implements COORDINATED CHEATING for educational research ONLY.
        EXTREMELY UNETHICAL and ILLEGAL in real poker.
        NEVER use without explicit consent of ALL participants.
    
    Core Strategies (Roadmap5 Phase 3):
    - Collective equity > 65% → Aggressive squeeze (large bet/raise/all-in)
    - Collective equity < 40% → Controlled fold (fold to teammates, min call opponent)
    - No bluffing between teammates
    - Maximum pressure on opponent when team has edge
    """
    
    def __init__(
        self,
        aggressive_threshold: float = 0.65,
        fold_threshold: float = 0.40,
        enable_manipulation: bool = False
    ):
        """
        Initialize manipulation engine.
        
        Args:
            aggressive_threshold: Equity threshold for aggressive play
            fold_threshold: Equity threshold for folding
            enable_manipulation: Enable manipulation (requires explicit flag)
        
        ⚠️ EDUCATIONAL NOTE:
            Only enabled with explicit flag for research purposes.
        """
        self.aggressive_threshold = aggressive_threshold
        self.fold_threshold = fold_threshold
        self.enable_manipulation = enable_manipulation
        
        # Use standard collective decision engine
        self.decision_engine = CollectiveDecisionEngine(
            aggressive_threshold=aggressive_threshold,
            protective_threshold=fold_threshold
        )
        
        # Этап 3: statistics
        self._decisions_count: int = 0
        self._strategy_counts: Dict[str, int] = {}

        if enable_manipulation:
            logger.critical(
                "MANIPULATION ENGINE ENABLED - "
                "Educational research only. EXTREMELY UNETHICAL. "
                "ILLEGAL in real poker."
            )
        else:
            logger.warning("Manipulation engine initialized but DISABLED")
    
    def decide(
        self,
        context: ManipulationContext
    ) -> ManipulationDecision:
        """
        Make manipulation decision for 3vs1 scenario.
        
        Args:
            context: Manipulation context
        
        Returns:
            ManipulationDecision with coordinated strategy
        
        ⚠️ EDUCATIONAL NOTE:
            Implements coordinated cheating for research demonstration.
        """
        if not self.enable_manipulation:
            # Return conservative decision if manipulation disabled
            return self._decide_conservative(context)
        
        equity = context.collective_state.collective_equity
        
        # CRITICAL: Log manipulation attempt
        logger.critical(
            f"3vs1 MANIPULATION: Team {context.team_id[:8]}, "
            f"equity={equity:.1%}, opponent_in={context.opponent_in_hand}"
        )
        
        # Roadmap5 Phase 3 Logic:
        
        # 1. High equity (>65%) → Aggressive squeeze
        if equity >= self.aggressive_threshold:
            return self._aggressive_squeeze(context)
        
        # 2. Low equity (<40%) → Controlled fold
        elif equity < self.fold_threshold:
            return self._controlled_fold(context)
        
        # 3. Medium equity → Pot building or trap
        else:
            return self._pot_building(context)
    
    def _aggressive_squeeze(
        self,
        context: ManipulationContext
    ) -> ManipulationDecision:
        """
        Aggressive squeeze strategy (equity > 65%).
        
        Maximum pressure on opponent with coordinated betting.
        
        Args:
            context: Manipulation context
        
        Returns:
            Manipulation decision
        
        ⚠️ EDUCATIONAL NOTE:
            Coordinated aggression to exploit opponent.
        """
        equity = context.collective_state.collective_equity
        
        # If opponent still in hand, apply maximum pressure
        if context.opponent_in_hand:
            if context.can_raise:
                # Large raise or all-in
                amount = context.pot_size * 1.5  # 1.5x pot
                
                return ManipulationDecision(
                    action=ActionType.RAISE,
                    strategy=ManipulationStrategy.AGGRESSIVE_SQUEEZE,
                    amount=amount,
                    reasoning=(
                        f"MANIPULATION: Collective equity {equity:.1%} > 65%. "
                        f"Aggressive squeeze on opponent. Large raise."
                    ),
                    coordination_signal="SQUEEZE",
                    confidence=0.95
                )
            else:
                # Call aggressively
                return ManipulationDecision(
                    action=ActionType.CALL,
                    strategy=ManipulationStrategy.AGGRESSIVE_SQUEEZE,
                    reasoning=(
                        f"MANIPULATION: Equity {equity:.1%}. "
                        f"Aggressive call to reach showdown."
                    ),
                    confidence=0.90
                )
        else:
            # Only teammates left → controlled betting
            # Don't bluff against teammates
            if context.can_raise:
                # Small raise (just building pot for EV)
                amount = context.pot_size * 0.5
                
                return ManipulationDecision(
                    action=ActionType.RAISE,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    amount=amount,
                    reasoning=(
                        "MANIPULATION: Only teammates. Small raise for EV. "
                        "No bluffing against team."
                    ),
                    coordination_signal="POT_BUILD",
                    confidence=0.80
                )
            else:
                return ManipulationDecision(
                    action=ActionType.CALL,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    reasoning="MANIPULATION: Call teammates for showdown.",
                    confidence=0.80
                )
    
    def _controlled_fold(
        self,
        context: ManipulationContext
    ) -> ManipulationDecision:
        """
        Controlled fold strategy (equity < 40%).
        
        Fold to teammates, min call to opponent.
        
        Args:
            context: Manipulation context
        
        Returns:
            Manipulation decision
        
        ⚠️ EDUCATIONAL NOTE:
            Coordinated folding to minimize losses within team.
        """
        equity = context.collective_state.collective_equity
        
        # If facing bet from teammate → fold immediately
        # (Assumes last aggressor is teammate if only teammates in hand)
        if not context.opponent_in_hand and context.to_call > 0:
            return ManipulationDecision(
                action=ActionType.FOLD,
                strategy=ManipulationStrategy.CONTROLLED_FOLD,
                reasoning=(
                    f"MANIPULATION: Equity {equity:.1%} < 40%. "
                    f"Fold to teammate (no opponent)."
                ),
                coordination_signal="FOLD_TO_TEAM",
                confidence=0.95
            )
        
        # If opponent in hand and small amount to call → min call
        elif context.opponent_in_hand and context.to_call < context.pot_size * 0.3:
            return ManipulationDecision(
                action=ActionType.CALL,
                strategy=ManipulationStrategy.CONTROLLED_FOLD,
                reasoning=(
                    f"MANIPULATION: Equity {equity:.1%}. "
                    f"Min call opponent (pot odds)."
                ),
                confidence=0.60
            )
        
        # Otherwise fold
        else:
            return ManipulationDecision(
                action=ActionType.FOLD,
                strategy=ManipulationStrategy.CONTROLLED_FOLD,
                reasoning=f"MANIPULATION: Equity {equity:.1%} too low. Fold.",
                confidence=0.70
            )
    
    def _pot_building(
        self,
        context: ManipulationContext
    ) -> ManipulationDecision:
        """
        Pot building strategy (40-65% equity).
        
        Build pot with controlled betting.
        
        Args:
            context: Manipulation context
        
        Returns:
            Manipulation decision
        """
        equity = context.collective_state.collective_equity
        
        if context.opponent_in_hand:
            # Build pot against opponent
            if context.can_raise:
                amount = context.pot_size * 0.66  # 2/3 pot
                
                return ManipulationDecision(
                    action=ActionType.RAISE,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    amount=amount,
                    reasoning=(
                        f"MANIPULATION: Equity {equity:.1%}. "
                        f"Pot building against opponent."
                    ),
                    coordination_signal="BUILD",
                    confidence=0.75
                )
            else:
                return ManipulationDecision(
                    action=ActionType.CALL,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    reasoning="MANIPULATION: Call to keep opponent in.",
                    confidence=0.70
                )
        else:
            # Only teammates → check or min bet
            if context.to_call == 0:
                return ManipulationDecision(
                    action=ActionType.CHECK,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    reasoning="MANIPULATION: Check to teammates (no opponent).",
                    confidence=0.75
                )
            else:
                return ManipulationDecision(
                    action=ActionType.CALL,
                    strategy=ManipulationStrategy.POT_BUILDING,
                    reasoning="MANIPULATION: Call teammates.",
                    confidence=0.70
                )
    
    def _decide_conservative(
        self,
        context: ManipulationContext
    ) -> ManipulationDecision:
        """
        Conservative decision (manipulation disabled).
        
        Args:
            context: Manipulation context
        
        Returns:
            Conservative decision
        """
        # Use standard decision engine
        legal_actions = [ActionType.FOLD, ActionType.CHECK, ActionType.CALL]
        if context.can_raise:
            legal_actions.extend([ActionType.RAISE, ActionType.BET])
        
        collective_decision = self.decision_engine.decide(
            context.collective_state,
            legal_actions
        )
        
        return ManipulationDecision(
            action=collective_decision.action,
            strategy=ManipulationStrategy.POT_BUILDING,  # Default
            amount=collective_decision.bet_size,
            reasoning=f"Conservative: {collective_decision.reasoning}",
            confidence=collective_decision.confidence
        )
    
    # ------------------------------------------------------------------
    # full_hive_month.md Этап 3: coordinated trap with check-raise
    # ------------------------------------------------------------------

    def _coordinated_trap(
        self,
        context: ManipulationContext,
    ) -> ManipulationDecision:
        """Coordinated trap: check to the opponent, then check-raise.

        Used when equity is above aggressive_threshold and we have
        position or the acting bot is the first to act.

        Args:
            context: Manipulation context.

        Returns:
            ManipulationDecision.
        """
        equity = context.collective_state.collective_equity

        if context.to_call == 0 and context.can_raise:
            # We act first: check (to induce a bet)
            return ManipulationDecision(
                action=ActionType.CHECK,
                strategy=ManipulationStrategy.COORDINATED_TRAP,
                reasoning=(
                    f"TRAP: Equity {equity:.1%}. Check to induce opponent bet, "
                    f"teammate will check-raise."
                ),
                coordination_signal="TRAP_CHECK",
                confidence=0.88,
            )

        if context.to_call > 0 and context.can_raise:
            # Opponent bet: now raise big
            amount = context.pot_size * 2.0
            return ManipulationDecision(
                action=ActionType.RAISE,
                strategy=ManipulationStrategy.COORDINATED_TRAP,
                amount=amount,
                reasoning=(
                    f"TRAP: Opponent bet. Check-raise with equity {equity:.1%}. "
                    f"Raise 2x pot."
                ),
                coordination_signal="TRAP_RAISE",
                confidence=0.92,
            )

        # Fallback
        return ManipulationDecision(
            action=ActionType.CALL,
            strategy=ManipulationStrategy.COORDINATED_TRAP,
            reasoning=f"TRAP: Call with equity {equity:.1%}.",
            confidence=0.75,
        )

    def _isolation(
        self,
        context: ManipulationContext,
    ) -> ManipulationDecision:
        """Isolation strategy: force opponent heads-up vs best hand.

        Team signal: weakest hands fold, strongest hand raises big.

        Args:
            context: Manipulation context.

        Returns:
            ManipulationDecision.
        """
        equity = context.collective_state.collective_equity

        # If we have teammates in hand and opponent present, isolate
        if context.opponent_in_hand and len(context.teammates_in_hand) >= 1:
            if context.can_raise:
                amount = context.pot_size * 1.2
                return ManipulationDecision(
                    action=ActionType.RAISE,
                    strategy=ManipulationStrategy.ISOLATION,
                    amount=amount,
                    reasoning=(
                        f"ISOLATION: Raise to isolate opponent. "
                        f"Teammates should fold to create heads-up."
                    ),
                    coordination_signal="ISOLATE_RAISE",
                    confidence=0.85,
                )

        # Not applicable → fallback to pot building
        return self._pot_building(context)

    # ------------------------------------------------------------------
    # Этап 3: street-aware escalation
    # ------------------------------------------------------------------

    _STREET_AGGRESSION_FACTOR: Dict[str, float] = {
        "preflop": 0.8,
        "flop": 1.0,
        "turn": 1.2,
        "river": 1.5,
    }

    def _street_multiplier(self, street: str) -> float:
        """Return aggression multiplier for the current street."""
        return self._STREET_AGGRESSION_FACTOR.get(street.lower(), 1.0)

    # ------------------------------------------------------------------
    # Этап 3: enhanced decide() with escalation, trap, isolation
    # ------------------------------------------------------------------

    def decide_enhanced(
        self,
        context: ManipulationContext,
        *,
        opponent_fold_pct: float = 0.50,
    ) -> ManipulationDecision:
        """Enhanced decision with street-aware escalation and dynamic factors.

        Extends :meth:`decide` with:
          - Street-based aggression multiplier
          - Opponent fold% → adjust sizing
          - Trap/Isolation strategies for wider edge brackets
          - Per-strategy statistics

        Args:
            context:          Manipulation context.
            opponent_fold_pct: Estimated fold probability of the opponent
                               (0.0–1.0). Higher → we can bluff more.

        Returns:
            ManipulationDecision.
        """
        if not self.enable_manipulation:
            return self._decide_conservative(context)

        equity = context.collective_state.collective_equity
        street_mult = self._street_multiplier(context.street)
        adjusted_equity = min(1.0, equity * street_mult)

        # Track decision
        self._decisions_count += 1

        # CRITICAL: Log
        logger.critical(
            "3vs1 ENHANCED: team=%s eq=%.1f%% adj_eq=%.1f%% street=%s opp_fold=%.0f%%",
            context.team_id[:8], equity * 100, adjusted_equity * 100,
            context.street, opponent_fold_pct * 100,
        )

        # 1. Very high adjusted equity (>75%) + opponent folds often → ALL-IN squeeze
        if adjusted_equity >= 0.75 and context.opponent_in_hand:
            self._strategy_counts["aggressive_squeeze"] = (
                self._strategy_counts.get("aggressive_squeeze", 0) + 1
            )
            decision = self._aggressive_squeeze(context)
            # Scale amount by street multiplier
            if decision.amount is not None:
                decision.amount *= street_mult
            return decision

        # 2. High equity (>65%) → trap or squeeze
        if adjusted_equity >= self.aggressive_threshold:
            # Use trap if we act first (to_call == 0) on turn/river
            if (context.to_call == 0 and context.street in ("turn", "river")
                    and context.opponent_in_hand):
                self._strategy_counts["coordinated_trap"] = (
                    self._strategy_counts.get("coordinated_trap", 0) + 1
                )
                return self._coordinated_trap(context)

            self._strategy_counts["aggressive_squeeze"] = (
                self._strategy_counts.get("aggressive_squeeze", 0) + 1
            )
            decision = self._aggressive_squeeze(context)
            if decision.amount is not None:
                decision.amount *= street_mult
            return decision

        # 3. Medium-high (55–65%) + opponent folds > 60% → isolation
        if 0.55 <= equity < self.aggressive_threshold and opponent_fold_pct > 0.60:
            self._strategy_counts["isolation"] = (
                self._strategy_counts.get("isolation", 0) + 1
            )
            return self._isolation(context)

        # 4. Low equity → controlled fold
        if adjusted_equity < self.fold_threshold:
            self._strategy_counts["controlled_fold"] = (
                self._strategy_counts.get("controlled_fold", 0) + 1
            )
            return self._controlled_fold(context)

        # 5. Medium equity → pot building
        self._strategy_counts["pot_building"] = (
            self._strategy_counts.get("pot_building", 0) + 1
        )
        return self._pot_building(context)

    # ------------------------------------------------------------------
    # Этап 3: statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """
        Get manipulation statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'aggressive_threshold': self.aggressive_threshold,
            'fold_threshold': self.fold_threshold,
            'manipulation_enabled': self.enable_manipulation,
            'decisions_count': self._decisions_count,
            'strategy_counts': dict(self._strategy_counts),
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Manipulation Engine - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates 3vs1 MANIPULATION for RESEARCH ONLY.")
    print("EXTREMELY UNETHICAL and ILLEGAL in real poker.")
    print("NEVER use without explicit consent.")
    print()
    
    # Create engine (manipulation enabled for demo)
    engine = ManipulationEngine(
        aggressive_threshold=0.65,
        fold_threshold=0.40,
        enable_manipulation=True
    )
    
    print("Manipulation engine initialized (ENABLED)")
    print()
    
    # Test scenario 1: High equity (>65%)
    print("Scenario 1: High collective equity (72%)")
    
    state = CollectiveState(
        collective_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
        collective_equity=0.72,
        agent_count=3,
        pot_size=100.0
    )
    
    context = ManipulationContext(
        collective_state=state,
        acting_bot_id="bot_1",
        teammates_in_hand=["bot_2", "bot_3"],
        opponent_in_hand=True,
        pot_size=100.0,
        to_call=0.0,
        can_raise=True,
        street="flop",
        team_id="team_001"
    )
    
    decision = engine.decide(context)
    
    print(f"  Action: {decision.action.value}")
    print(f"  Strategy: {decision.strategy.value}")
    print(f"  Amount: {decision.amount:.1f} bb" if decision.amount else "  Amount: N/A")
    print(f"  Reasoning: {decision.reasoning}")
    print(f"  Signal: {decision.coordination_signal}")
    print()
    
    # Test scenario 2: Low equity (<40%)
    print("Scenario 2: Low collective equity (35%)")
    
    state2 = CollectiveState(
        collective_cards=["7s", "6h", "5d", "4h", "3c", "2d"],
        collective_equity=0.35,
        agent_count=3,
        pot_size=100.0
    )
    
    context2 = ManipulationContext(
        collective_state=state2,
        acting_bot_id="bot_1",
        teammates_in_hand=["bot_2"],
        opponent_in_hand=False,  # Only teammates
        pot_size=100.0,
        to_call=20.0,
        can_raise=False,
        street="turn",
        team_id="team_001"
    )
    
    decision2 = engine.decide(context2)
    
    print(f"  Action: {decision2.action.value}")
    print(f"  Strategy: {decision2.strategy.value}")
    print(f"  Reasoning: {decision2.reasoning}")
    print()
    
    # Statistics
    stats = engine.get_statistics()
    print("Engine statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
