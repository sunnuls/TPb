"""
Action Translator Module (Roadmap3 Phase 5.1).

Translates CollectiveDecision from decision engine into ActionCommand
that can be executed (or simulated) by action layer.

Key Features:
- CollectiveDecision -> ActionCommand translation
- Bet sizing normalization (bb -> chips)
- Action validation (legal action checking)
- Position-aware action mapping

EDUCATIONAL USE ONLY: For HCI research prototype.
Real actions prohibited without --unsafe flag.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from bridge.safety import SafetyFramework

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Poker actions (matches sim_engine/collective_decision.py)."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


class UIElement(str, Enum):
    """UI elements for action execution."""
    FOLD_BUTTON = "fold_button"
    CHECK_BUTTON = "check_button"
    CALL_BUTTON = "call_button"
    BET_BUTTON = "bet_button"
    RAISE_BUTTON = "raise_button"
    BET_SLIDER = "bet_slider"
    BET_INPUT = "bet_input"
    CONFIRM_BUTTON = "confirm_button"


@dataclass
class ActionCommand:
    """
    Command for executing a poker action.
    
    Attributes:
        action_type: Type of action to execute
        amount: Bet/raise amount (if applicable, in chips)
        ui_element: UI element to interact with
        normalized_amount: Amount in BB (for logging)
        description: Human-readable description
        legal: Whether action is legal in current state
        priority: Execution priority (higher = more important)
    """
    action_type: ActionType
    amount: float = 0.0
    ui_element: Optional[UIElement] = None
    normalized_amount: float = 0.0
    description: str = ""
    legal: bool = True
    priority: int = 100


@dataclass
class ActionContext:
    """
    Context needed for action translation.
    
    Attributes:
        pot_size: Current pot (in bb)
        hero_stack: Hero's stack (in bb)
        current_bet: Current bet to call (in bb)
        min_raise: Minimum raise size (in bb)
        legal_actions: List of legal action types
        bb_size: Big blind size (for chip conversion)
    """
    pot_size: float
    hero_stack: float
    current_bet: float = 0.0
    min_raise: float = 0.0
    legal_actions: List[str] = None
    bb_size: float = 1.0
    
    def __post_init__(self):
        if self.legal_actions is None:
            self.legal_actions = []


class ActionTranslator:
    """
    Translates CollectiveDecision into executable ActionCommand.
    
    Translation Process:
    1. Extract action + amount from CollectiveDecision
    2. Validate action is legal in current context
    3. Normalize bet sizing (bb -> chips)
    4. Map to UI elements
    5. Generate ActionCommand with execution details
    
    EDUCATIONAL NOTE:
        This creates the bridge between decision engine output
        and UI interaction layer (even in dry-run mode).
    """
    
    def __init__(
        self,
        safety: Optional[SafetyFramework] = None
    ):
        """
        Initialize action translator.
        
        Args:
            safety: Safety framework instance
        """
        self.safety = safety or SafetyFramework.get_instance()
        
        # Translation statistics
        self.translations_count = 0
        self.illegal_actions_count = 0
        
        logger.info("ActionTranslator initialized")
    
    def translate(
        self,
        decision: dict,
        context: ActionContext
    ) -> ActionCommand:
        """
        Translate CollectiveDecision to ActionCommand.
        
        Args:
            decision: CollectiveDecision dict with 'action' and 'amount' keys
            context: Current game context for validation
        
        Returns:
            ActionCommand ready for execution (or simulation)
        
        EDUCATIONAL NOTE:
            Decision format from sim_engine/collective_decision.py:
            {
                'action': 'fold'|'check'|'call'|'bet'|'raise'|'all_in',
                'amount': <bet_size_in_bb>,
                'line_type': 'aggressive'|'protective'|'passive',
                'collective_equity': <float>,
                'agent_count': <int>
            }
        """
        self.translations_count += 1
        
        # Extract action and amount
        action_str = decision.get('action', 'fold')
        amount_bb = decision.get('amount', 0.0)
        
        # Parse action type
        try:
            action_type = ActionType(action_str.lower())
        except ValueError:
            logger.error(f"Invalid action type: {action_str}, defaulting to FOLD")
            action_type = ActionType.FOLD
        
        # Validate action is legal
        if not self._is_legal(action_type, context):
            logger.warning(
                f"Illegal action: {action_type.value}, "
                f"legal actions: {context.legal_actions}"
            )
            self.illegal_actions_count += 1
            # Fallback to legal action
            action_type = self._get_fallback_action(context)
        
        # Convert amount from BB to chips
        amount_chips = amount_bb * context.bb_size
        
        # Map to UI element
        ui_element = self._map_ui_element(action_type, amount_bb, context)
        
        # Generate description
        description = self._generate_description(action_type, amount_bb, context)
        
        # Determine priority (fold < check/call < bet/raise < all-in)
        priority = self._calculate_priority(action_type)
        
        # Create command
        command = ActionCommand(
            action_type=action_type,
            amount=amount_chips,
            ui_element=ui_element,
            normalized_amount=amount_bb,
            description=description,
            legal=True,
            priority=priority
        )
        
        # Log decision
        self.safety.log_decision({
            'action': 'translate_action',
            'decision_action': action_type.value,
            'amount_bb': amount_bb,
            'amount_chips': amount_chips,
            'ui_element': ui_element.value if ui_element else None,
            'allowed': True
        })
        
        logger.info(
            f"Translated: {action_type.value} ${amount_bb:.1f}bb -> "
            f"UI:{ui_element.value if ui_element else 'none'}"
        )
        
        return command
    
    def _is_legal(self, action_type: ActionType, context: ActionContext) -> bool:
        """
        Check if action is legal in current context.
        
        Args:
            action_type: Action to validate
            context: Current game context
        
        Returns:
            True if action is legal
        """
        if not context.legal_actions:
            # No restrictions specified - assume all legal
            return True
        
        return action_type.value in context.legal_actions
    
    def _get_fallback_action(self, context: ActionContext) -> ActionType:
        """
        Get fallback action when primary action is illegal.
        
        Args:
            context: Current game context
        
        Returns:
            Safe fallback action
        
        EDUCATIONAL NOTE:
            Fallback priority: check > call > fold
        """
        legal = context.legal_actions
        
        if 'check' in legal:
            return ActionType.CHECK
        elif 'call' in legal:
            return ActionType.CALL
        else:
            return ActionType.FOLD
    
    def _map_ui_element(
        self,
        action_type: ActionType,
        amount_bb: float,
        context: ActionContext
    ) -> Optional[UIElement]:
        """
        Map action type to UI element.
        
        Args:
            action_type: Action to execute
            amount_bb: Bet amount in BB
            context: Game context
        
        Returns:
            UI element to interact with
        """
        mapping = {
            ActionType.FOLD: UIElement.FOLD_BUTTON,
            ActionType.CHECK: UIElement.CHECK_BUTTON,
            ActionType.CALL: UIElement.CALL_BUTTON,
            ActionType.BET: UIElement.BET_BUTTON,
            ActionType.RAISE: UIElement.RAISE_BUTTON,
            ActionType.ALL_IN: UIElement.RAISE_BUTTON  # Usually same as raise
        }
        
        return mapping.get(action_type)
    
    def _generate_description(
        self,
        action_type: ActionType,
        amount_bb: float,
        context: ActionContext
    ) -> str:
        """
        Generate human-readable action description.
        
        Args:
            action_type: Action type
            amount_bb: Amount in BB
            context: Game context
        
        Returns:
            Description string
        """
        if action_type == ActionType.FOLD:
            return "Fold"
        elif action_type == ActionType.CHECK:
            return "Check"
        elif action_type == ActionType.CALL:
            return f"Call {context.current_bet:.1f}bb"
        elif action_type == ActionType.BET:
            return f"Bet {amount_bb:.1f}bb (pot: {context.pot_size:.1f}bb)"
        elif action_type == ActionType.RAISE:
            return f"Raise to {amount_bb:.1f}bb"
        elif action_type == ActionType.ALL_IN:
            return f"All-in {context.hero_stack:.1f}bb"
        else:
            return f"{action_type.value}"
    
    def _calculate_priority(self, action_type: ActionType) -> int:
        """
        Calculate execution priority for action.
        
        Args:
            action_type: Action type
        
        Returns:
            Priority value (higher = more important)
        
        EDUCATIONAL NOTE:
            Priority affects error handling - high priority actions
            (all-in) require more confirmation than low priority (fold).
        """
        priority_map = {
            ActionType.FOLD: 50,
            ActionType.CHECK: 75,
            ActionType.CALL: 80,
            ActionType.BET: 90,
            ActionType.RAISE: 95,
            ActionType.ALL_IN: 100
        }
        
        return priority_map.get(action_type, 100)
    
    def get_statistics(self) -> dict:
        """Get translator statistics."""
        return {
            'total_translations': self.translations_count,
            'illegal_actions': self.illegal_actions_count,
            'illegal_rate': (
                self.illegal_actions_count / self.translations_count
                if self.translations_count > 0 else 0.0
            )
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Action Translator - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Create translator
    translator = ActionTranslator()
    
    # Example context (flop, facing bet)
    context = ActionContext(
        pot_size=30.0,
        hero_stack=100.0,
        current_bet=10.0,
        min_raise=20.0,
        legal_actions=['fold', 'call', 'raise'],
        bb_size=1.0
    )
    
    # Example decisions to translate
    decisions = [
        {
            'action': 'fold',
            'amount': 0.0,
            'line_type': 'passive'
        },
        {
            'action': 'call',
            'amount': 10.0,
            'line_type': 'protective'
        },
        {
            'action': 'raise',
            'amount': 30.0,
            'line_type': 'aggressive'
        }
    ]
    
    print("Translating CollectiveDecisions:")
    print("-" * 60)
    
    for i, decision in enumerate(decisions, 1):
        print(f"\n{i}. Decision: {decision['action']} {decision['amount']:.1f}bb")
        
        command = translator.translate(decision, context)
        
        print(f"   > Command: {command.description}")
        print(f"   > UI Element: {command.ui_element.value if command.ui_element else 'none'}")
        print(f"   > Amount (chips): {command.amount:.1f}")
        print(f"   > Priority: {command.priority}")
        print(f"   > Legal: {command.legal}")
    
    print()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    stats = translator.get_statistics()
    print(f"Total translations: {stats['total_translations']}")
    print(f"Illegal actions: {stats['illegal_actions']}")
    print(f"Illegal rate: {stats['illegal_rate']:.1%}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
    print("[NOTE] Actions translated but NOT executed")
