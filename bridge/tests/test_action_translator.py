"""
Tests for ActionTranslator (Roadmap3 Phase 5.1).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from bridge.action_translator import (
    ActionTranslator,
    ActionCommand,
    ActionContext,
    ActionType,
    UIElement
)


class TestActionContext:
    """Test ActionContext dataclass."""
    
    def test_action_context_creation(self):
        """Test basic context creation."""
        context = ActionContext(
            pot_size=30.0,
            hero_stack=100.0,
            current_bet=10.0,
            min_raise=20.0,
            legal_actions=['fold', 'call', 'raise'],
            bb_size=1.0
        )
        
        assert context.pot_size == 30.0
        assert context.hero_stack == 100.0
        assert context.current_bet == 10.0
        assert context.min_raise == 20.0
        assert len(context.legal_actions) == 3
        assert context.bb_size == 1.0
    
    def test_action_context_defaults(self):
        """Test default values."""
        context = ActionContext(
            pot_size=20.0,
            hero_stack=50.0
        )
        
        assert context.current_bet == 0.0
        assert context.min_raise == 0.0
        assert context.legal_actions == []
        assert context.bb_size == 1.0


class TestActionTranslator:
    """Test ActionTranslator core functionality."""
    
    def test_init(self):
        """Test translator initialization."""
        translator = ActionTranslator()
        
        assert translator.translations_count == 0
        assert translator.illegal_actions_count == 0
    
    def test_translate_fold(self):
        """Test translating fold action."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['fold', 'call', 'raise']
        )
        
        decision = {'action': 'fold', 'amount': 0.0}
        command = translator.translate(decision, context)
        
        assert command.action_type == ActionType.FOLD
        assert command.amount == 0.0
        assert command.ui_element == UIElement.FOLD_BUTTON
        assert command.legal is True
    
    def test_translate_call(self):
        """Test translating call action."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=30.0,
            hero_stack=100.0,
            current_bet=10.0,
            legal_actions=['fold', 'call', 'raise'],
            bb_size=2.0
        )
        
        decision = {'action': 'call', 'amount': 10.0}
        command = translator.translate(decision, context)
        
        assert command.action_type == ActionType.CALL
        assert command.normalized_amount == 10.0
        assert command.amount == 20.0  # 10bb * 2.0 bb_size
        assert command.ui_element == UIElement.CALL_BUTTON
    
    def test_translate_raise(self):
        """Test translating raise action."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=30.0,
            hero_stack=100.0,
            current_bet=10.0,
            min_raise=20.0,
            legal_actions=['fold', 'call', 'raise']
        )
        
        decision = {'action': 'raise', 'amount': 30.0}
        command = translator.translate(decision, context)
        
        assert command.action_type == ActionType.RAISE
        assert command.normalized_amount == 30.0
        assert command.ui_element == UIElement.RAISE_BUTTON
    
    def test_translate_illegal_action(self):
        """Test handling illegal action."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['fold', 'call']  # Raise not legal
        )
        
        decision = {'action': 'raise', 'amount': 30.0}
        command = translator.translate(decision, context)
        
        # Should fallback to legal action
        assert command.action_type in [ActionType.CALL, ActionType.FOLD]
        assert translator.illegal_actions_count == 1
    
    def test_translate_invalid_action_type(self):
        """Test handling invalid action type."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['fold', 'call', 'raise']
        )
        
        decision = {'action': 'invalid', 'amount': 0.0}
        command = translator.translate(decision, context)
        
        # Should default to FOLD
        assert command.action_type == ActionType.FOLD
    
    def test_priority_calculation(self):
        """Test action priority calculation."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['fold', 'check', 'raise']
        )
        
        decisions = [
            {'action': 'fold', 'amount': 0.0},
            {'action': 'check', 'amount': 0.0},
            {'action': 'raise', 'amount': 20.0}
        ]
        
        priorities = [
            translator.translate(d, context).priority
            for d in decisions
        ]
        
        # Priorities should increase: fold < check < raise
        assert priorities[0] < priorities[1] < priorities[2]
    
    def test_bb_to_chips_conversion(self):
        """Test BB to chips conversion."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['bet'],
            bb_size=5.0  # 5 chips per BB
        )
        
        decision = {'action': 'bet', 'amount': 10.0}  # 10bb
        command = translator.translate(decision, context)
        
        assert command.normalized_amount == 10.0  # BB
        assert command.amount == 50.0  # Chips (10 * 5)
    
    def test_get_statistics(self):
        """Test statistics collection."""
        translator = ActionTranslator()
        context = ActionContext(
            pot_size=20.0,
            hero_stack=100.0,
            legal_actions=['fold', 'call']
        )
        
        # Translate some actions
        translator.translate({'action': 'fold', 'amount': 0.0}, context)
        translator.translate({'action': 'call', 'amount': 10.0}, context)
        translator.translate({'action': 'raise', 'amount': 20.0}, context)  # Illegal
        
        stats = translator.get_statistics()
        
        assert stats['total_translations'] == 3
        assert stats['illegal_actions'] == 1
        assert stats['illegal_rate'] == pytest.approx(1/3)


class TestActionCommand:
    """Test ActionCommand dataclass."""
    
    def test_action_command_creation(self):
        """Test basic command creation."""
        command = ActionCommand(
            action_type=ActionType.RAISE,
            amount=50.0,
            ui_element=UIElement.RAISE_BUTTON,
            normalized_amount=25.0,
            description="Raise to 25bb",
            legal=True,
            priority=95
        )
        
        assert command.action_type == ActionType.RAISE
        assert command.amount == 50.0
        assert command.ui_element == UIElement.RAISE_BUTTON
        assert command.normalized_amount == 25.0
        assert command.description == "Raise to 25bb"
        assert command.legal is True
        assert command.priority == 95


class TestIntegration:
    """Integration tests for action translator."""
    
    def test_full_translation_workflow(self):
        """Test complete translation workflow."""
        translator = ActionTranslator()
        
        # Context for facing bet on flop
        context = ActionContext(
            pot_size=30.0,
            hero_stack=100.0,
            current_bet=10.0,
            min_raise=20.0,
            legal_actions=['fold', 'call', 'raise'],
            bb_size=1.0
        )
        
        # Translate various decisions
        decisions = [
            {'action': 'fold', 'amount': 0.0, 'line_type': 'passive'},
            {'action': 'call', 'amount': 10.0, 'line_type': 'protective'},
            {'action': 'raise', 'amount': 30.0, 'line_type': 'aggressive'}
        ]
        
        commands = [translator.translate(d, context) for d in decisions]
        
        # Validate all commands
        assert len(commands) == 3
        assert all(cmd.legal for cmd in commands)
        assert all(cmd.ui_element is not None for cmd in commands)
        
        # Check increasing priority
        assert commands[0].priority < commands[1].priority < commands[2].priority


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
