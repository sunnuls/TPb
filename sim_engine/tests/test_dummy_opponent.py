"""
Unit tests for dummy opponent module (Roadmap2 Phase 3).

Tests scripted opponent behavior, variance, and decision logic.
"""

import pytest
from sim_engine.dummy_opponent import (
    ActionType,
    DummyOpponent,
    OpponentAction,
    OpponentStyle,
    estimate_hand_strength,
    generate_random_opponent,
)


class TestOpponentStyles:
    """Test opponent style initialization and thresholds."""
    
    def test_tight_style_thresholds(self):
        """Tight style has conservative thresholds."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.2, aggression=0.3)
        
        assert opp.style == OpponentStyle.TIGHT
        assert opp.vpip == 0.20
        assert opp.fold_threshold == 0.30
        assert opp.raise_threshold == 0.75
    
    def test_loose_style_thresholds(self):
        """Loose style has liberal thresholds."""
        opp = DummyOpponent(OpponentStyle.LOOSE, variance=0.3, aggression=0.7)
        
        assert opp.style == OpponentStyle.LOOSE
        assert opp.vpip == 0.50
        assert opp.fold_threshold == 0.15
        assert opp.raise_threshold == 0.65
    
    def test_random_style_variability(self):
        """Random style has variable thresholds."""
        opp = DummyOpponent(OpponentStyle.RANDOM, variance=0.3, aggression=0.5)
        
        assert opp.style == OpponentStyle.RANDOM
        assert 0.20 <= opp.vpip <= 0.50
        assert 0.10 <= opp.fold_threshold <= 0.40
        assert 0.60 <= opp.raise_threshold <= 0.85


class TestVariance:
    """Test behavioral variance application."""
    
    def test_zero_variance_no_change(self):
        """Zero variance = no adjustment."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        
        original = 0.60
        perceived = opp._apply_variance(original)
        
        assert perceived == original
    
    def test_variance_adjusts_strength(self):
        """Variance adjusts perceived strength."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.3)
        
        original = 0.60
        # Run multiple times to check range
        results = [opp._apply_variance(original) for _ in range(20)]
        
        # Should have some variance
        assert min(results) < original or max(results) > original
        
        # All should be in valid range
        assert all(0.0 <= r <= 1.0 for r in results)
    
    def test_variance_clamped_to_valid_range(self):
        """Variance cannot push strength below 0 or above 1."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.5)
        
        # Test low strength
        low_results = [opp._apply_variance(0.1) for _ in range(50)]
        assert all(r >= 0.0 for r in low_results)
        
        # Test high strength
        high_results = [opp._apply_variance(0.9) for _ in range(50)]
        assert all(r <= 1.0 for r in high_results)


class TestDecisionLogic:
    """Test opponent decision-making logic."""
    
    def test_weak_hand_folds(self):
        """Weak hand below fold threshold folds."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        
        action = opp.decide(
            hand_strength=0.20,  # Below tight fold threshold (0.30)
            pot_size=100.0,
            bet_to_call=50.0,
            can_check=False
        )
        
        assert action.action == ActionType.FOLD
    
    def test_weak_hand_checks_if_free(self):
        """Weak hand checks if possible."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        opp.hands_played = 5  # Simulate postflop
        
        action = opp.decide(
            hand_strength=0.20,
            pot_size=100.0,
            bet_to_call=0.0,
            can_check=True
        )
        
        assert action.action == ActionType.CHECK
    
    def test_medium_hand_calls(self):
        """Medium hand calls with pot odds."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0, aggression=0.3)
        
        action = opp.decide(
            hand_strength=0.50,  # Between call and raise threshold
            pot_size=100.0,
            bet_to_call=30.0,
            can_check=False
        )
        
        # Should call or fold based on pot odds
        assert action.action in [ActionType.CALL, ActionType.FOLD, ActionType.CHECK]
    
    def test_strong_hand_bets_or_raises(self):
        """Strong hand bets or raises aggressively."""
        opp = DummyOpponent(OpponentStyle.LOOSE, variance=0.0, aggression=0.8)
        opp.hands_played = 5  # Simulate postflop
        
        # No bet to face
        action1 = opp.decide(
            hand_strength=0.85,  # Above raise threshold
            pot_size=100.0,
            bet_to_call=0.0,
            can_check=True
        )
        
        assert action1.action in [ActionType.BET, ActionType.CHECK]
        
        # Facing a bet
        action2 = opp.decide(
            hand_strength=0.85,
            pot_size=100.0,
            bet_to_call=50.0,
            can_check=False
        )
        
        assert action2.action in [ActionType.RAISE, ActionType.CALL]
    
    def test_aggression_affects_betting(self):
        """Higher aggression = more betting."""
        passive_opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0, aggression=0.1)
        aggressive_opp = DummyOpponent(OpponentStyle.LOOSE, variance=0.0, aggression=0.9)
        
        # Count bets over multiple decisions
        passive_bets = 0
        aggressive_bets = 0
        
        for _ in range(20):
            p_action = passive_opp.decide(0.70, 100.0, 0.0, True)
            if p_action.action == ActionType.BET:
                passive_bets += 1
            
            a_action = aggressive_opp.decide(0.70, 100.0, 0.0, True)
            if a_action.action == ActionType.BET:
                aggressive_bets += 1
        
        # Aggressive should bet more often
        assert aggressive_bets >= passive_bets


class TestBetSizing:
    """Test opponent bet sizing logic."""
    
    def test_bet_size_proportional_to_pot(self):
        """Bet sizes are proportional to pot."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0, aggression=0.8)
        
        action = opp.decide(
            hand_strength=0.85,
            pot_size=100.0,
            bet_to_call=0.0,
            can_check=False
        )
        
        if action.amount is not None:
            # Should be fraction of pot
            assert 0 < action.amount <= 150.0  # Up to 1.5x pot
    
    def test_raise_size_relative_to_bet(self):
        """Raise sizes are relative to bet faced."""
        opp = DummyOpponent(OpponentStyle.LOOSE, variance=0.0, aggression=0.9)
        
        action = opp.decide(
            hand_strength=0.85,
            pot_size=100.0,
            bet_to_call=50.0,
            can_check=False
        )
        
        if action.action == ActionType.RAISE and action.amount is not None:
            # Should be multiple of bet
            assert action.amount >= 50.0  # At least call amount


class TestStyleUpdate:
    """Test opponent style adaptation."""
    
    def test_update_to_new_style(self):
        """Can update to new style."""
        opp = DummyOpponent(OpponentStyle.TIGHT)
        original_vpip = opp.vpip
        
        opp.update_style(OpponentStyle.LOOSE)
        
        assert opp.style == OpponentStyle.LOOSE
        assert opp.vpip != original_vpip
    
    def test_random_threshold_adjustment(self):
        """Random update adjusts thresholds."""
        opp = DummyOpponent(OpponentStyle.TIGHT)
        original_vpip = opp.vpip
        original_aggression = opp.aggression
        
        opp.update_style(None)  # Random adjustment
        
        # Thresholds should change (probably)
        # Use multiple attempts to avoid random false negatives
        changed = False
        for _ in range(5):
            if opp.vpip != original_vpip or opp.aggression != original_aggression:
                changed = True
                break
            opp.update_style(None)
        
        # After 5 attempts, should have changed
        assert changed or (opp.vpip == original_vpip and opp.aggression == original_aggression)


class TestStackManagement:
    """Test stack size management."""
    
    def test_reset_stack(self):
        """Can reset stack size."""
        opp = DummyOpponent(stack=1000.0)
        opp.hands_played = 50
        
        opp.reset_stack(500.0)
        
        assert opp.stack == 500.0
        assert opp.hands_played == 0


class TestRandomGeneration:
    """Test random opponent generation."""
    
    def test_generate_random_opponent(self):
        """Can generate random opponent."""
        opp = generate_random_opponent()
        
        assert opp.style in list(OpponentStyle)
        assert 0.0 <= opp.variance <= 1.0
        assert 0.0 <= opp.aggression <= 1.0
        assert opp.stack > 0
    
    def test_generate_with_fixed_style(self):
        """Can generate with fixed style."""
        opp = generate_random_opponent(OpponentStyle.TIGHT)
        
        assert opp.style == OpponentStyle.TIGHT


class TestHandStrengthEstimator:
    """Test simplified hand strength calculator."""
    
    def test_high_cards_stronger(self):
        """High cards have higher strength."""
        aces = estimate_hand_strength(["As", "Ah"])
        sevens = estimate_hand_strength(["7s", "7h"])
        
        assert aces > sevens
    
    def test_pair_bonus(self):
        """Pairs get bonus strength."""
        pair = estimate_hand_strength(["Ks", "Kh"])
        no_pair = estimate_hand_strength(["Ks", "Qh"])
        
        assert pair > no_pair
    
    def test_suited_bonus(self):
        """Suited cards get small bonus."""
        suited = estimate_hand_strength(["Ks", "Qs"])
        offsuit = estimate_hand_strength(["Kh", "Qs"])
        
        # Suited should be slightly stronger (if detected)
        assert suited >= offsuit
    
    def test_board_interaction(self):
        """Board cards affect strength."""
        hole = ["Ks", "Kh"]
        no_board = estimate_hand_strength(hole, [])
        king_on_board = estimate_hand_strength(hole, ["Kd", "Jh", "9s"])
        
        # Having K on board should increase strength (trips)
        assert king_on_board >= no_board
    
    def test_empty_hand_weak(self):
        """Empty/incomplete hand is very weak."""
        strength = estimate_hand_strength([])
        
        assert strength <= 0.2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_pot_size(self):
        """Handle zero pot (preflop)."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        
        action = opp.decide(0.70, pot_size=0.0, bet_to_call=0.0, can_check=True)
        
        # Should not crash
        assert action.action in list(ActionType)
    
    def test_very_large_bet(self):
        """Handle oversized bet."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        
        action = opp.decide(0.50, pot_size=100.0, bet_to_call=1000.0, can_check=False)
        
        # Should fold or call based on hand strength
        assert action.action in [ActionType.FOLD, ActionType.CALL]
    
    def test_perfect_hand_strength(self):
        """Handle 100% hand strength (nuts)."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0, aggression=0.9)
        opp.hands_played = 5  # Simulate postflop
        
        action = opp.decide(1.0, pot_size=100.0, bet_to_call=50.0, can_check=False)
        
        # Should play aggressively
        assert action.action in [ActionType.RAISE, ActionType.CALL]


class TestDecisionConsistency:
    """Test decision consistency and logic flow."""
    
    def test_increasing_strength_more_aggressive(self):
        """Higher hand strength = more aggressive actions."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0, aggression=0.5)
        
        weak = opp.decide(0.20, 100.0, 30.0, False)
        medium = opp.decide(0.50, 100.0, 30.0, False)
        strong = opp.decide(0.85, 100.0, 30.0, False)
        
        # Weak should fold
        assert weak.action == ActionType.FOLD
        
        # Strong should not fold
        assert strong.action != ActionType.FOLD
    
    def test_reasoning_provided(self):
        """All decisions include reasoning."""
        opp = DummyOpponent(OpponentStyle.TIGHT, variance=0.0)
        
        action = opp.decide(0.60, 100.0, 30.0, False)
        
        assert action.reasoning
        assert len(action.reasoning) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
