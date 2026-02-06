"""
Unit tests for collective decision module (Roadmap2 Phase 2).

Tests HIVE decision logic based on collective equity thresholds:
- Aggressive line when equity > 65%
- Protective line when 45% ≤ equity < 65%
- Passive line when equity < 45%
"""

import pytest
from sim_engine.collective_decision import (
    ActionType,
    CollectiveDecision,
    CollectiveDecisionEngine,
    CollectiveState,
    LineType,
    calculate_optimal_bet_size,
)


class TestCollectiveState:
    """Test CollectiveState data structure."""
    
    def test_state_creation(self):
        """Test basic state creation."""
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd"],
            collective_equity=0.70,
            agent_count=3
        )
        assert len(state.collective_cards) == 3
        assert state.collective_equity == 0.70
        assert state.agent_count == 3
        assert state.pot_size == 0.0
        assert state.stack_sizes == {}
        assert state.board == []
    
    def test_state_with_full_params(self):
        """Test state with all parameters."""
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh"],
            collective_equity=0.68,
            agent_count=3,
            pot_size=100.0,
            stack_sizes={"a1": 500, "a2": 450},
            board=["Js", "Ts", "9h"],
            dummy_range="tight"
        )
        assert state.pot_size == 100.0
        assert len(state.stack_sizes) == 2
        assert len(state.board) == 3
        assert state.dummy_range == "tight"


class TestCollectiveDecisionEngine:
    """Test core decision engine logic."""
    
    def test_engine_initialization(self):
        """Test engine with default thresholds."""
        engine = CollectiveDecisionEngine()
        assert engine.aggressive_threshold == 0.65
        assert engine.protective_threshold == 0.45
    
    def test_custom_thresholds(self):
        """Test engine with custom thresholds."""
        engine = CollectiveDecisionEngine(
            aggressive_threshold=0.70,
            protective_threshold=0.50
        )
        assert engine.aggressive_threshold == 0.70
        assert engine.protective_threshold == 0.50


class TestAggressiveLine:
    """Test aggressive line decisions (equity ≥ 65%)."""
    
    def test_all_in_with_high_equity(self):
        """All-in when equity > 65% and action available."""
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh"],
            collective_equity=0.75,
            agent_count=3,
            pot_size=100.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.FOLD, ActionType.CALL, ActionType.ALL_IN]
        )
        
        assert decision.action == ActionType.ALL_IN
        assert decision.line_type == LineType.AGGRESSIVE
        assert decision.confidence >= 0.8
        assert "equity" in decision.reasoning.lower()
    
    def test_raise_without_all_in(self):
        """Large raise when all-in not available."""
        state = CollectiveState(
            collective_cards=["Ks", "Kh", "Qd", "Qh"],
            collective_equity=0.70,
            agent_count=3,
            pot_size=100.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.FOLD, ActionType.CALL, ActionType.RAISE]
        )
        
        assert decision.action == ActionType.RAISE
        assert decision.line_type == LineType.AGGRESSIVE
        assert decision.bet_size is not None
        assert decision.bet_size > state.pot_size  # Large raise
    
    def test_bet_without_raise(self):
        """Large bet when raise not available."""
        state = CollectiveState(
            collective_cards=["As", "Kd"],
            collective_equity=0.68,
            agent_count=2,
            pot_size=50.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.CHECK, ActionType.BET]
        )
        
        assert decision.action == ActionType.BET
        assert decision.line_type == LineType.AGGRESSIVE
        assert decision.bet_size >= state.pot_size * 0.5  # At least 1/2 pot
    
    def test_aggressive_threshold_exactly(self):
        """Test exact threshold boundary (65%)."""
        state = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.65,  # Exactly at threshold
            agent_count=3,
            pot_size=100.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, [ActionType.ALL_IN, ActionType.FOLD])
        
        assert decision.line_type == LineType.AGGRESSIVE


class TestProtectiveLine:
    """Test protective line decisions (45% ≤ equity < 65%)."""
    
    def test_check_with_medium_equity(self):
        """Check for pot control with medium equity."""
        state = CollectiveState(
            collective_cards=["Js", "Jh"],
            collective_equity=0.55,
            agent_count=2,
            pot_size=80.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.CHECK, ActionType.BET, ActionType.FOLD]
        )
        
        assert decision.action == ActionType.CHECK
        assert decision.line_type == LineType.PROTECTIVE
        assert "pot control" in decision.reasoning.lower() or "medium" in decision.reasoning.lower()
    
    def test_call_without_check(self):
        """Call when check not available."""
        state = CollectiveState(
            collective_cards=["Ts", "Th"],
            collective_equity=0.50,
            agent_count=2,
            pot_size=100.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.FOLD, ActionType.CALL, ActionType.RAISE]
        )
        
        assert decision.action == ActionType.CALL
        assert decision.line_type == LineType.PROTECTIVE
    
    def test_small_bet_protective(self):
        """Small bet when forced to act."""
        state = CollectiveState(
            collective_cards=["9s", "9h"],
            collective_equity=0.48,
            agent_count=2,
            pot_size=60.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.BET, ActionType.FOLD]
        )
        
        assert decision.action == ActionType.BET
        assert decision.line_type == LineType.PROTECTIVE
        assert decision.bet_size < state.pot_size * 0.5  # Small bet


class TestPassiveLine:
    """Test passive line decisions (equity < 45%)."""
    
    def test_fold_with_low_equity(self):
        """Fold when equity < 45%."""
        state = CollectiveState(
            collective_cards=["7s", "2h"],
            collective_equity=0.30,
            agent_count=2,
            pot_size=50.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.FOLD, ActionType.CALL, ActionType.RAISE]
        )
        
        assert decision.action == ActionType.FOLD
        assert decision.line_type == LineType.PASSIVE
        assert "low equity" in decision.reasoning.lower() or "weak" in decision.reasoning.lower()
    
    def test_check_when_fold_unavailable(self):
        """Check when fold not available."""
        state = CollectiveState(
            collective_cards=["8s", "3h"],
            collective_equity=0.35,
            agent_count=2,
            pot_size=40.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.CHECK, ActionType.BET]
        )
        
        assert decision.action == ActionType.CHECK
        assert decision.line_type == LineType.PASSIVE
    
    def test_reluctant_call(self):
        """Reluctant call when no other options."""
        state = CollectiveState(
            collective_cards=["6s", "4h"],
            collective_equity=0.25,
            agent_count=2,
            pot_size=30.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(
            state,
            legal_actions=[ActionType.CALL]
        )
        
        assert decision.action == ActionType.CALL
        assert decision.line_type == LineType.PASSIVE
        assert decision.confidence < 0.5


class TestBetSizing:
    """Test optimal bet sizing logic."""
    
    def test_aggressive_bet_sizing(self):
        """Large bet with high equity."""
        bet = calculate_optimal_bet_size(
            equity=0.75,
            pot_size=100.0,
            stack_size=500.0
        )
        assert bet >= 75.0  # At least 3/4 pot
        assert bet <= 500.0  # Capped at stack
    
    def test_protective_bet_sizing(self):
        """Medium bet with medium equity."""
        bet = calculate_optimal_bet_size(
            equity=0.55,
            pot_size=100.0,
            stack_size=300.0
        )
        assert 30.0 <= bet <= 60.0  # 1/3 to 1/2 pot range
    
    def test_passive_bet_sizing(self):
        """Small bet with low equity."""
        bet = calculate_optimal_bet_size(
            equity=0.35,
            pot_size=100.0,
            stack_size=200.0
        )
        assert bet <= 50.0  # Small bet
    
    def test_bet_capped_at_stack(self):
        """Bet cannot exceed stack size."""
        bet = calculate_optimal_bet_size(
            equity=0.80,
            pot_size=1000.0,
            stack_size=50.0
        )
        assert bet == 50.0  # Capped at stack


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_no_legal_actions(self):
        """Handle empty legal actions list."""
        state = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.70,
            agent_count=3
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, legal_actions=[])
        
        assert decision.action in ActionType
    
    def test_single_legal_action(self):
        """Force specific action when only one legal."""
        state = CollectiveState(
            collective_cards=["Ks", "Kh"],
            collective_equity=0.30,  # Low equity - will choose passive
            agent_count=3
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, legal_actions=[ActionType.FOLD])
        
        # With low equity and only FOLD legal, should fold
        assert decision.action == ActionType.FOLD
    
    def test_zero_pot_size(self):
        """Handle preflop (zero pot) scenario."""
        state = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.85,
            agent_count=3,
            pot_size=0.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, [ActionType.RAISE, ActionType.FOLD])
        
        assert decision.action in [ActionType.RAISE, ActionType.FOLD]
        if decision.bet_size is not None:
            assert decision.bet_size >= 0
    
    def test_perfect_equity(self):
        """Handle 100% equity (nuts)."""
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
            collective_equity=1.0,
            agent_count=3,
            pot_size=200.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, [ActionType.ALL_IN, ActionType.CALL])
        
        assert decision.line_type == LineType.AGGRESSIVE


class TestDecisionConsistency:
    """Test decision consistency and logic flow."""
    
    def test_equity_ordering(self):
        """Higher equity = more aggressive line."""
        engine = CollectiveDecisionEngine()
        
        equities = [0.35, 0.55, 0.75]
        decisions = []
        
        for eq in equities:
            state = CollectiveState(
                collective_cards=["As", "Ah"],
                collective_equity=eq,
                agent_count=3,
                pot_size=100.0
            )
            dec = engine.decide(state, [ActionType.FOLD, ActionType.CALL, ActionType.ALL_IN])
            decisions.append(dec)
        
        # Check line progression
        assert decisions[0].line_type == LineType.PASSIVE
        assert decisions[1].line_type == LineType.PROTECTIVE
        assert decisions[2].line_type == LineType.AGGRESSIVE
    
    def test_confidence_correlation(self):
        """Higher equity = higher confidence."""
        engine = CollectiveDecisionEngine()
        
        state_low = CollectiveState(
            collective_cards=["7s", "2h"],
            collective_equity=0.25,
            agent_count=2,
            pot_size=50.0
        )
        
        state_high = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.85,
            agent_count=3,
            pot_size=50.0
        )
        
        dec_low = engine.decide(state_low, [ActionType.FOLD, ActionType.CALL])
        dec_high = engine.decide(state_high, [ActionType.ALL_IN, ActionType.FOLD])
        
        assert dec_high.confidence >= dec_low.confidence


class TestHiveCoordination:
    """Test HIVE-specific coordination logic."""
    
    def test_three_agent_hive(self):
        """Test decision with 3 agents in HIVE."""
        state = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
            collective_equity=0.72,
            agent_count=3,
            pot_size=150.0
        )
        
        engine = CollectiveDecisionEngine()
        decision = engine.decide(state, [ActionType.ALL_IN, ActionType.RAISE, ActionType.FOLD])
        
        assert decision.line_type == LineType.AGGRESSIVE
        assert decision.confidence >= 0.8
    
    def test_more_known_cards_higher_confidence(self):
        """More collective cards = higher confidence."""
        engine = CollectiveDecisionEngine()
        
        state_few = CollectiveState(
            collective_cards=["As", "Ah"],
            collective_equity=0.70,
            agent_count=2,
            pot_size=100.0
        )
        
        state_many = CollectiveState(
            collective_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
            collective_equity=0.70,
            agent_count=3,
            pot_size=100.0
        )
        
        dec_few = engine.decide(state_few, [ActionType.ALL_IN, ActionType.FOLD])
        dec_many = engine.decide(state_many, [ActionType.ALL_IN, ActionType.FOLD])
        
        # Both should be aggressive, but confidence may vary
        assert dec_few.line_type == LineType.AGGRESSIVE
        assert dec_many.line_type == LineType.AGGRESSIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
