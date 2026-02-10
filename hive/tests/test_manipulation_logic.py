"""
Tests for Manipulation Logic (Roadmap5 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY - Tests 3vs1 MANIPULATION.
"""

import pytest

from hive.manipulation_logic import (
    ManipulationContext,
    ManipulationEngine,
    ManipulationStrategy,
)
from sim_engine.collective_decision import ActionType, CollectiveState


class TestManipulationEngine:
    """Test manipulation engine."""
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = ManipulationEngine(
            aggressive_threshold=0.65,
            fold_threshold=0.40,
            enable_manipulation=False
        )
        
        assert engine.aggressive_threshold == 0.65
        assert engine.fold_threshold == 0.40
        assert engine.enable_manipulation is False
    
    def test_manipulation_disabled(self):
        """Test conservative decision when manipulation disabled."""
        engine = ManipulationEngine(enable_manipulation=False)
        
        state = CollectiveState(
            collective_cards=["As", "Kh"],
            collective_equity=0.75,
            agent_count=3
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
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should be conservative
        assert "Conservative" in decision.reasoning
    
    def test_aggressive_squeeze_high_equity(self):
        """Test aggressive squeeze with high equity."""
        engine = ManipulationEngine(enable_manipulation=True)
        
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh"],
            collective_equity=0.72,  # > 65%
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
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should be aggressive
        assert decision.action in [ActionType.RAISE, ActionType.BET]
        assert decision.strategy == ManipulationStrategy.AGGRESSIVE_SQUEEZE
        assert "MANIPULATION" in decision.reasoning
    
    def test_controlled_fold_low_equity(self):
        """Test controlled fold with low equity."""
        engine = ManipulationEngine(enable_manipulation=True)
        
        state = CollectiveState(
            collective_cards=["7s", "6h", "5d", "4h"],
            collective_equity=0.35,  # < 40%
            agent_count=3,
            pot_size=100.0
        )
        
        context = ManipulationContext(
            collective_state=state,
            acting_bot_id="bot_1",
            teammates_in_hand=["bot_2"],
            opponent_in_hand=False,  # Only teammates
            pot_size=100.0,
            to_call=20.0,
            can_raise=False,
            street="turn",
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should fold to teammates
        assert decision.action == ActionType.FOLD
        assert decision.strategy == ManipulationStrategy.CONTROLLED_FOLD
    
    def test_pot_building_medium_equity(self):
        """Test pot building with medium equity."""
        engine = ManipulationEngine(enable_manipulation=True)
        
        state = CollectiveState(
            collective_cards=["Qs", "Qh", "Jd", "Th"],
            collective_equity=0.55,  # 40-65%
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
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should build pot
        assert decision.strategy == ManipulationStrategy.POT_BUILDING
    
    def test_no_bluff_against_teammates(self):
        """Test no bluffing against teammates."""
        engine = ManipulationEngine(enable_manipulation=True)
        
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh"],
            collective_equity=0.75,
            agent_count=3,
            pot_size=100.0
        )
        
        context = ManipulationContext(
            collective_state=state,
            acting_bot_id="bot_1",
            teammates_in_hand=["bot_2", "bot_3"],
            opponent_in_hand=False,  # Only teammates
            pot_size=100.0,
            to_call=0.0,
            can_raise=True,
            street="flop",
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should not be aggressive against teammates
        assert "teammates" in decision.reasoning.lower()
    
    def test_coordination_signals(self):
        """Test coordination signals generation."""
        engine = ManipulationEngine(enable_manipulation=True)
        
        state = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.70,
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
            team_id="team_1"
        )
        
        decision = engine.decide(context)
        
        # Should have coordination signal
        assert decision.coordination_signal is not None
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        engine = ManipulationEngine(
            aggressive_threshold=0.65,
            fold_threshold=0.40,
            enable_manipulation=True
        )
        
        stats = engine.get_statistics()
        
        assert stats['aggressive_threshold'] == 0.65
        assert stats['fold_threshold'] == 0.40
        assert stats['manipulation_enabled'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
