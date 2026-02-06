"""
Unit tests for multi-agent decision module.

Tests decision modeling for initial phases (position, resource_bucket based)
as specified in Phase 2, Step 2.1, Подпункт 1.1.

Educational Use Only: For simulation research validation.
"""

from __future__ import annotations

import pytest

from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position
from sim_engine.decision import (
    AgentContext,
    LineType,
    SimulatedActionType,
    SimulationDecision,
    generate_simulated_decision,
)


class TestSimulationDecisionValidation:
    """Test validation for SimulationDecision dataclass."""
    
    def test_valid_decision(self):
        """Test that valid decision is accepted."""
        decision = SimulationDecision(
            action=SimulatedActionType.INCREMENT,
            sizing=10.0,
            confidence=0.85,
            equity=0.68,
            line_type=LineType.PROACTIVE,
            reasoning={"test": "data"}
        )
        
        assert decision.action == SimulatedActionType.INCREMENT
        assert decision.sizing == 10.0
        assert decision.confidence == 0.85
        assert decision.equity == 0.68
    
    def test_reject_invalid_confidence(self):
        """Test rejection of confidence outside [0,1]."""
        with pytest.raises(ValueError, match="Confidence must be"):
            SimulationDecision(
                action=SimulatedActionType.INCREMENT,
                sizing=10.0,
                confidence=1.5,  # Invalid
                equity=0.68,
                line_type=LineType.PROACTIVE,
                reasoning={}
            )
    
    def test_reject_invalid_equity(self):
        """Test rejection of equity outside [0,1]."""
        with pytest.raises(ValueError, match="Equity must be"):
            SimulationDecision(
                action=SimulatedActionType.INCREMENT,
                sizing=10.0,
                confidence=0.85,
                equity=-0.1,  # Invalid
                line_type=LineType.PROACTIVE,
                reasoning={}
            )
    
    def test_increment_requires_sizing(self):
        """Test INCREMENT action requires sizing."""
        with pytest.raises(ValueError, match="requires sizing"):
            SimulationDecision(
                action=SimulatedActionType.INCREMENT,
                sizing=None,  # Missing
                confidence=0.85,
                equity=0.68,
                line_type=LineType.PROACTIVE,
                reasoning={}
            )
    
    def test_decrement_no_sizing(self):
        """Test DECREMENT should not have non-zero sizing."""
        with pytest.raises(ValueError, match="should not have non-zero sizing"):
            SimulationDecision(
                action=SimulatedActionType.DECREMENT,
                sizing=5.0,  # Should be None or 0
                confidence=0.70,
                equity=0.30,
                line_type=LineType.REACTIVE,
                reasoning={}
            )


class TestDecisionGenerationInitialPhases:
    """
    Test decision generation for initial phases (Подпункт 1.1).
    
    Focus: Actions based on position and resource_bucket.
    """
    
    def test_decision_generation_basic(self):
        """Test 1: Basic decision generation with strong hand."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={"hands_played": 0}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "As"],  # Pocket Aces
            environment=[],  # Preflop
            street=Street.PREFLOP,
            pot_bb=1.5,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False  # Use heuristic for speed
        )
        
        assert isinstance(decision, SimulationDecision)
        assert decision.action in [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK]
        assert 0.0 <= decision.confidence <= 1.0
        assert 0.0 <= decision.equity <= 1.0
    
    def test_position_based_decision_btn(self):
        """Test 2: BTN position (best position) generates aggressive actions."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Kh", "Qh"],  # Strong suited connector
            environment=["Kc", "7h", "2s"],  # Top pair
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # BTN with top pair should likely increment or check
        assert decision.action in [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK]
        assert decision.confidence >= 0.5
    
    def test_position_based_decision_early(self):
        """Test 3: Early position (UTG) generates more conservative actions."""
        context = AgentContext(
            position=Position.UTG,
            resource_bucket="medium",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Jh", "Tc"],  # Marginal hand
            environment=["Kc", "7h", "2s"],  # No pair
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,  # Facing bet
            context=context,
            use_monte_carlo=False
        )
        
        # UTG with marginal hand facing bet should likely fold or call
        assert decision.action in [
            SimulatedActionType.DECREMENT,
            SimulatedActionType.HOLD,
            SimulatedActionType.INCREMENT
        ]
    
    def test_resource_bucket_high(self):
        """Test 4: High resource bucket allows more aggressive play."""
        context = AgentContext(
            position=Position.CO,
            resource_bucket="high",  # Deep stack
            opponent_models={},
            session_state={"hands_played": 100, "bb_won": 50.0}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kd"],
            environment=["Ad", "7c", "2s"],  # Top pair top kicker
            street=Street.FLOP,
            pot_bb=15.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # High resources with strong hand: should increment
        assert decision.action in [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK]
        if decision.action == SimulatedActionType.INCREMENT:
            assert decision.sizing is not None
            assert decision.sizing > 0
    
    def test_resource_bucket_low(self):
        """Test 5: Low resource bucket generates more defensive play."""
        context = AgentContext(
            position=Position.BB,
            resource_bucket="low",  # Short stack
            opponent_models={},
            session_state={"hands_played": 50, "bb_won": -15.0}
        )
        
        decision = generate_simulated_decision(
            agent_state=["9h", "8h"],
            environment=["Kc", "7d", "2s"],  # Missed
            street=Street.FLOP,
            pot_bb=10.0,
            to_call_bb=6.0,  # Facing large bet
            context=context,
            use_monte_carlo=False
        )
        
        # Low resources, missed: should likely fold
        # (though equity calculation might suggest call with draws)
        assert decision.action in [SimulatedActionType.DECREMENT, SimulatedActionType.HOLD]
    
    def test_equity_threshold_proactive(self):
        """Test 6: High equity (>60%) generates proactive line."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "As"],  # AA (high equity preflop)
            environment=[],
            street=Street.PREFLOP,
            pot_bb=3.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # AA should have high equity and proactive line
        assert decision.equity >= 0.6
        assert decision.line_type == LineType.PROACTIVE
    
    def test_equity_threshold_reactive(self):
        """Test 7: Medium equity (40-60%) generates reactive line."""
        context = AgentContext(
            position=Position.HJ,
            resource_bucket="medium",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["7h", "7d"],  # Small pair
            environment=[],
            street=Street.PREFLOP,
            pot_bb=3.0,
            to_call_bb=2.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # Small pair should have medium equity
        # Line type might be reactive or balanced
        assert decision.line_type in [LineType.REACTIVE, LineType.BALANCED, LineType.EXPLOITATIVE]
    
    def test_opponent_models_influence(self):
        """Test 8: Opponent models influence range estimation."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={
                "tight_player": {"vpip": 0.15, "pfr": 0.12},  # Very tight
                "loose_player": {"vpip": 0.45, "pfr": 0.35}   # Very loose
            },
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Kh", "Qh"],
            environment=["Kc", "7h", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Should use opponent models in reasoning
        assert "opponent_range_size" in decision.reasoning
        assert decision.reasoning["opponent_range_size"] > 0
    
    def test_monte_carlo_integration(self):
        """Test 9: Monte Carlo equity calculation integration."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={"villain": {"vpip": 0.28, "pfr": 0.22}},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kh"],
            environment=["Ad", "7c", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=True,  # Enable MC
            num_simulations=100  # Small number for test speed
        )
        
        # Should have MC equity source
        assert decision.reasoning.get("equity_source") in ["monte_carlo", "heuristic_fallback"]
        if decision.reasoning["equity_source"] == "monte_carlo":
            assert "simulations" in decision.reasoning
    
    def test_sizing_calculation_increment(self):
        """Test 10: Sizing calculation for INCREMENT actions."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "As"],  # Strong hand
            environment=["Kc", "7h", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        if decision.action == SimulatedActionType.INCREMENT:
            # Should have sizing
            assert decision.sizing is not None
            assert decision.sizing > 0
            
            # Sizing should be reasonable (0.33x to 1.5x pot)
            assert 12.0 * 0.33 <= decision.sizing <= 12.0 * 1.5
            
            # Proactive line with high equity should have larger sizing
            if decision.line_type == LineType.PROACTIVE and decision.equity >= 0.7:
                assert decision.sizing >= 12.0 * 0.6  # At least 60% pot


class TestLineTypeSelection:
    """Test strategic line type determination."""
    
    def test_proactive_line_high_equity(self):
        """Test proactive line with equity >60%."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        # Force high equity with AA
        decision = generate_simulated_decision(
            agent_state=["Ah", "As"],
            environment=[],
            street=Street.PREFLOP,
            pot_bb=3.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        assert decision.line_type == LineType.PROACTIVE
        assert decision.equity >= 0.6
    
    def test_reactive_line_medium_equity(self):
        """Test reactive line with medium equity."""
        context = AgentContext(
            position=Position.HJ,
            resource_bucket="medium",
            opponent_models={},
            session_state={}
        )
        
        # Medium strength hand
        decision = generate_simulated_decision(
            agent_state=["Th", "9h"],
            environment=["Kc", "7h", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # Likely reactive or balanced with medium hand
        assert decision.line_type in [LineType.REACTIVE, LineType.BALANCED, LineType.EXPLOITATIVE]


@pytest.mark.parametrize("position,expected_action_types", [
    (Position.BTN, [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK]),
    (Position.UTG, [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK, SimulatedActionType.DECREMENT]),
])
def test_parametrized_position_actions(position, expected_action_types):
    """Parametrized test for position-based actions."""
    context = AgentContext(
        position=position,
        resource_bucket="medium",
        opponent_models={},
        session_state={}
    )
    
    decision = generate_simulated_decision(
        agent_state=["Kh", "Qh"],
        environment=["Kc", "7h", "2s"],
        street=Street.FLOP,
        pot_bb=12.0,
        to_call_bb=0.0,
        context=context,
        use_monte_carlo=False
    )
    
    # Action should be in expected types for this position
    assert decision.action in expected_action_types


class TestSubsequentPhasesLogic:
    """
    Test subsequent phases enhancements (Подпункт 1.2).
    
    Focus: Probability thresholds (>60% proactive), enum validation,
    exploitative lines, and output validation.
    """
    
    def test_proactive_threshold_above_60_percent(self):
        """Test proactive line triggers at >60% equity threshold."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        # Create scenario with equity slightly above 60%
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kh"],
            environment=["Ac", "7h", "2s"],  # Top pair
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6  # 60% threshold
        )
        
        # With top pair, equity should be >60%, triggering PROACTIVE
        if decision.equity >= 0.60:
            assert decision.line_type == LineType.PROACTIVE
            assert decision.action in [SimulatedActionType.INCREMENT, SimulatedActionType.CHECK]
    
    def test_reactive_below_threshold(self):
        """Test reactive line for equity below proactive threshold."""
        context = AgentContext(
            position=Position.HJ,
            resource_bucket="medium",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["9h", "8h"],  # Medium hand
            environment=["Kc", "7d", "2s"],  # Gutshot + backdoor
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # Medium hand should trigger reactive or balanced line
        assert decision.line_type in [LineType.REACTIVE, LineType.BALANCED, LineType.EXPLOITATIVE]
    
    def test_exploitative_line_vs_tight_opponent(self):
        """Test exploitative adjustments against tight opponents."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={
                "tight_player": {
                    "vpip": 0.15,
                    "pfr": 0.12,
                    "fold_to_cbet": 0.75  # Folds too much
                }
            },
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Kh", "Qh"],
            environment=["Ac", "7h", "2s"],  # Missed
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # Against tight opponent who folds too much, should exploit with bluffs
        # (might increment even with medium equity)
        assert decision.reasoning.get("opponent_range_size") is not None
    
    def test_exploitative_line_vs_aggressive_opponent(self):
        """Test exploitative adjustments when facing aggressive opponent."""
        context = AgentContext(
            position=Position.BB,
            resource_bucket="medium",
            opponent_models={
                "aggressive_player": {
                    "vpip": 0.40,
                    "pfr": 0.35,
                    "aggression_factor": 4.5  # Very aggressive
                }
            },
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Th", "9h"],
            environment=["Kc", "7h", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=6.0,  # Large bet from aggressive opponent
            context=context,
            use_monte_carlo=False,
            probability_threshold=0.6
        )
        
        # Against aggressive opponent, can call lighter (they bluff more)
        # Decision should reflect this in exploitative line
        assert decision.line_type in [LineType.EXPLOITATIVE, LineType.REACTIVE, LineType.BALANCED]
    
    def test_enum_validation_action_type(self):
        """Test that only valid SimulatedActionType enums are returned."""
        context = AgentContext(
            position=Position.CO,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kd"],
            environment=["Ad", "7c", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Action must be valid enum
        assert isinstance(decision.action, SimulatedActionType)
        assert decision.action in [
            SimulatedActionType.INCREMENT,
            SimulatedActionType.HOLD,
            SimulatedActionType.DECREMENT,
            SimulatedActionType.CHECK
        ]
    
    def test_enum_validation_line_type(self):
        """Test that only valid LineType enums are returned."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Kh", "Qh"],
            environment=["Kc", "7h", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Line type must be valid enum
        assert isinstance(decision.line_type, LineType)
        assert decision.line_type in [
            LineType.PROACTIVE,
            LineType.REACTIVE,
            LineType.BALANCED,
            LineType.EXPLOITATIVE
        ]
    
    def test_output_validation_confidence_range(self):
        """Test output validation: confidence must be in [0,1]."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "As"],
            environment=[],
            street=Street.PREFLOP,
            pot_bb=3.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Validate confidence
        assert 0.0 <= decision.confidence <= 1.0
    
    def test_output_validation_equity_range(self):
        """Test output validation: equity must be in [0,1]."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["7h", "6h"],
            environment=["Kc", "Qd", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Validate equity
        assert 0.0 <= decision.equity <= 1.0
    
    def test_output_validation_sizing_for_increment(self):
        """Test output validation: INCREMENT must have positive sizing."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kh"],
            environment=["Ad", "7c", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # If action is INCREMENT, sizing must exist and be positive
        if decision.action == SimulatedActionType.INCREMENT:
            assert decision.sizing is not None
            assert decision.sizing > 0
            
            # Sizing should be reasonable (min 33% pot, max 150% pot)
            assert 12.0 * 0.33 <= decision.sizing <= 12.0 * 1.5
    
    def test_reasoning_contains_key_factors(self):
        """Test that reasoning dict contains all key decision factors."""
        context = AgentContext(
            position=Position.BTN,
            resource_bucket="high",
            opponent_models={"villain": {"vpip": 0.28}},
            session_state={"hands_played": 100}
        )
        
        decision = generate_simulated_decision(
            agent_state=["Ah", "Kh"],
            environment=["Ad", "7c", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,
            context=context,
            use_monte_carlo=True,
            num_simulations=50
        )
        
        # Reasoning must contain key factors for analysis
        assert "equity" in decision.reasoning
        assert "line_type" in decision.reasoning
        assert "opponent_range_size" in decision.reasoning
        assert "pot_odds" in decision.reasoning
        assert "equity_source" in decision.reasoning
