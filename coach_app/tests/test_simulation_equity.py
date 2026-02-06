"""
Unit tests for simulation equity calculator.

Tests validation, error handling, and equity calculations
for multi-agent game theory simulations.

Educational Use Only: For research and testing purposes.
"""

from __future__ import annotations

import pytest

from coach_app.engine import (
    calculate_monte_carlo_equity,
    calculate_equity_vs_specific_hand,
    EquityResult,
    Range,
)


class TestSimulationEquityValidation:
    """Test input validation for simulation equity calculator."""
    
    def test_valid_basic_input(self):
        """Test that valid inputs are accepted."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={"QQ": 1.0, "JJ": 0.9})
        board = ["Ad", "7c", "2s"]
        
        # Should not raise
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100
        )
        
        assert isinstance(result, EquityResult)
        assert 0.0 <= result.equity <= 1.0
    
    def test_reject_invalid_card_format(self):
        """Test rejection of invalid card format."""
        hero = ["Ah", "Zz"]  # Invalid rank 'Z'
        opp_range = Range(hands={"AA": 1.0})
        board = ["Ad", "7c", "2s"]
        
        with pytest.raises(ValueError, match="Invalid rank"):
            calculate_monte_carlo_equity(hero, opp_range, board, num_simulations=10)
    
    def test_reject_invalid_suit(self):
        """Test rejection of invalid suit."""
        hero = ["Ah", "Kx"]  # Invalid suit 'x'
        opp_range = Range(hands={"AA": 1.0})
        board = ["Ad", "7c", "2s"]
        
        with pytest.raises(ValueError, match="Invalid suit"):
            calculate_monte_carlo_equity(hero, opp_range, board, num_simulations=10)
    
    def test_reject_duplicate_cards(self):
        """Test rejection of duplicate cards."""
        hero = ["Ah", "As"]
        opp_range = Range(hands={"AA": 1.0})
        board = ["Ah", "7c", "2s"]  # Ah already in hero hand
        
        with pytest.raises(ValueError, match="Duplicate cards"):
            calculate_monte_carlo_equity(hero, opp_range, board, num_simulations=10)
    
    def test_reject_wrong_number_of_hole_cards(self):
        """Test rejection of wrong number of hole cards."""
        # Too few
        with pytest.raises(ValueError, match="exactly 2 cards"):
            calculate_monte_carlo_equity(
                ["Ah"],  # Only 1 card
                Range(hands={"AA": 1.0}),
                ["Ad", "7c", "2s"],
                num_simulations=10
            )
        
        # Too many
        with pytest.raises(ValueError, match="exactly 2 cards"):
            calculate_monte_carlo_equity(
                ["Ah", "Ks", "Qd"],  # 3 cards
                Range(hands={"AA": 1.0}),
                ["Ad", "7c", "2s"],
                num_simulations=10
            )
    
    def test_reject_too_many_board_cards(self):
        """Test rejection of too many board cards."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={"AA": 1.0})
        board = ["Ad", "7c", "2s", "Jh", "9d", "8c"]  # 6 cards (max is 5)
        
        with pytest.raises(ValueError, match="0-5 cards"):
            calculate_monte_carlo_equity(hero, opp_range, board, num_simulations=10)
    
    def test_reject_empty_opponent_range(self):
        """Test rejection of empty opponent range."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={})  # Empty
        board = ["Ad", "7c", "2s"]
        
        with pytest.raises(ValueError, match="empty"):
            calculate_monte_carlo_equity(hero, opp_range, board, num_simulations=10)
    
    def test_reject_identical_hole_cards(self):
        """Test rejection of identical hole cards."""
        with pytest.raises(ValueError, match="Duplicate cards"):
            calculate_monte_carlo_equity(
                ["Ah", "Ah"],  # Same card twice
                Range(hands={"AA": 1.0}),
                ["Ad", "7c", "2s"],
                num_simulations=10
            )
    
    def test_reject_invalid_card_length(self):
        """Test rejection of cards with wrong length."""
        with pytest.raises(ValueError, match="2 chars"):
            calculate_monte_carlo_equity(
                ["A", "Ks"],  # 'A' is only 1 char
                Range(hands={"AA": 1.0}),
                ["Ad", "7c", "2s"],
                num_simulations=10
            )


class TestSimulationEquityScenarios:
    """Test equity calculations for 5 simulation scenarios."""
    
    def test_scenario_1_premium_pair_vs_range(self):
        """
        Scenario 1: Agent with pocket Aces vs typical preflop calling range.
        
        Expected: High equity (75-85%)
        """
        hero = ["As", "Ad"]  # Pocket Aces
        opp_range = Range(hands={
            "KK": 1.0,
            "QQ": 1.0,
            "JJ": 1.0,
            "AKs": 0.9,
            "AKo": 0.8,
        })
        board = []  # Preflop
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=500,
            random_seed=42  # For reproducibility
        )
        
        assert 0.75 <= result.equity <= 0.95
        assert result.total_simulations > 0
        assert result.win_count + result.tie_count + result.lose_count == result.total_simulations
    
    def test_scenario_2_top_pair_vs_range(self):
        """
        Scenario 2: Agent with top pair top kicker on flop vs opponent range.
        
        Expected: Moderate-high equity (55-75%)
        """
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={
            "AA": 0.5,  # Lower weight (unlikely with Ace on board)
            "KK": 0.8,
            "QQ": 1.0,
            "JJ": 1.0,
            "AQs": 0.9,
            "AJs": 0.8,
            "KQs": 0.7,
        })
        board = ["Ad", "7c", "2s"]  # Hero has top pair Aces
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=500,
            random_seed=42
        )
        
        assert 0.50 <= result.equity <= 0.80
        assert result.confidence >= 0.9  # High confidence with 500 sims
    
    def test_scenario_3_flush_draw_vs_made_hand(self):
        """
        Scenario 3: Agent with flush draw vs opponent with likely pair.
        
        Expected: Moderate equity (30-40%)
        """
        hero = ["Kh", "Qh"]
        opp_range = Range(hands={
            "AA": 0.7,
            "77": 1.0,  # Pair of sevens
            "22": 1.0,  # Pair of deuces
            "A7s": 0.9,
            "A2s": 0.8,
        })
        board = ["Ah", "7h", "2c"]  # Hero has flush draw
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=500,
            random_seed=42
        )
        
        # Flush draw typically ~35% equity
        assert 0.25 <= result.equity <= 0.50
    
    def test_scenario_4_underpair_vs_overcards(self):
        """
        Scenario 4: Agent with pocket pair vs two overcards.
        
        Expected: Close to 50-50 (coin flip scenario)
        """
        hero = ["Jh", "Jc"]  # Pocket Jacks
        villain = ["As", "Kd"]  # AK (two overcards)
        board = []  # Preflop
        
        result = calculate_equity_vs_specific_hand(
            hero,
            villain,
            board,
            num_simulations=500
        )
        
        # Classic coin flip: ~55% for pair, ~45% for overcards
        assert 0.48 <= result.equity <= 0.60
    
    def test_scenario_5_dominated_hand(self):
        """
        Scenario 5: Agent with dominated hand (same rank, worse kicker).
        
        Expected: Low equity (20-30%)
        """
        hero = ["Ah", "Tc"]  # A-10 offsuit
        opp_range = Range(hands={
            "AKs": 1.0,
            "AKo": 1.0,
            "AQs": 0.9,
            "AQo": 0.9,
            "AJs": 0.8,
        })
        board = ["Ad", "7c", "2s"]  # Both have pair of Aces, but opponent has better kicker
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=500,
            random_seed=42
        )
        
        # Dominated hand has poor equity
        assert 0.10 <= result.equity <= 0.40


class TestSimulationEquityResults:
    """Test equity result object and calculations."""
    
    def test_equity_result_validation(self):
        """Test EquityResult validates its fields."""
        # Valid result
        result = EquityResult(
            equity=0.65,
            win_count=650,
            tie_count=0,
            lose_count=350,
            total_simulations=1000,
            confidence=1.0
        )
        assert result.equity == 0.65
        
        # Invalid equity (out of range)
        with pytest.raises(ValueError, match="Equity must be"):
            EquityResult(
                equity=1.5,  # > 1.0
                win_count=100,
                tie_count=0,
                lose_count=0,
                total_simulations=100,
                confidence=1.0
            )
        
        # Invalid counts (don't sum to total)
        with pytest.raises(ValueError, match="don't sum"):
            EquityResult(
                equity=0.5,
                win_count=100,
                tie_count=0,
                lose_count=50,  # Only 150, but total is 200
                total_simulations=200,
                confidence=1.0
            )
    
    def test_equity_calculation_accuracy(self):
        """Test equity calculation matches win/tie/lose counts."""
        hero = ["As", "Ad"]
        villain = ["Ks", "Kd"]
        board = []
        
        result = calculate_equity_vs_specific_hand(
            hero,
            villain,
            board,
            num_simulations=1000
        )
        
        # Manually calculate equity
        expected_equity = (result.win_count + result.tie_count * 0.5) / result.total_simulations
        
        assert abs(result.equity - expected_equity) < 0.001  # Within rounding error
    
    def test_confidence_scales_with_simulations(self):
        """Test confidence increases with more simulations."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={"QQ": 1.0, "JJ": 1.0})
        board = ["Ad", "7c", "2s"]
        
        # Few simulations
        result_few = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=10
        )
        
        # Many simulations
        result_many = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=1000
        )
        
        # More simulations should have higher confidence
        assert result_many.confidence >= result_few.confidence
    
    def test_deterministic_with_seed(self):
        """Test results are deterministic when using random seed."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={"QQ": 1.0, "JJ": 1.0})
        board = ["Ad", "7c", "2s"]
        
        result1 = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100,
            random_seed=12345
        )
        
        result2 = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100,
            random_seed=12345
        )
        
        # Same seed should give same results
        assert result1.equity == result2.equity
        assert result1.win_count == result2.win_count
        assert result1.tie_count == result2.tie_count
        assert result1.lose_count == result2.lose_count


class TestSimulationEquityEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_river_equity_deterministic(self):
        """Test equity on river is deterministic (no runouts)."""
        hero = ["Ah", "Ks"]
        villain = ["Qd", "Jd"]
        board = ["Kc", "7h", "2h", "9d", "3s"]  # Complete board (river)
        
        result = calculate_equity_vs_specific_hand(
            hero,
            villain,
            board,
            num_simulations=1  # Only need 1 sim on river
        )
        
        # Hero has pair of Kings, villain has high card Queen
        # Hero should win 100%
        assert result.equity == 1.0
        assert result.win_count == 1
        assert result.lose_count == 0
    
    def test_preflop_no_board(self):
        """Test equity calculation works with empty board."""
        hero = ["As", "Ad"]
        opp_range = Range(hands={"KK": 1.0})
        board = []  # Preflop
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100
        )
        
        # AA vs KK preflop: ~80% equity for AA
        assert 0.75 <= result.equity <= 0.90
    
    def test_range_with_mixed_frequencies(self):
        """Test equity calculation with mixed frequency ranges."""
        hero = ["Ah", "Ks"]
        opp_range = Range(hands={
            "AA": 0.5,  # 50% frequency
            "KK": 1.0,  # 100% frequency
            "QQ": 0.7,  # 70% frequency
        })
        board = ["Ad", "7c", "2s"]
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=500
        )
        
        # Should weight AA less (only 50% of the time)
        assert 0.40 <= result.equity <= 0.80
    
    def test_all_outs_available(self):
        """Test simulation handles cases where all cards are available."""
        hero = ["2h", "2d"]  # Pocket deuces (low pair)
        opp_range = Range(hands={"AKs": 1.0})
        board = ["3c", "4s", "5h"]  # No cards overlap with hero/range
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100
        )
        
        # Pair should have slight edge over AK high
        assert 0.40 <= result.equity <= 0.70
    
    def test_narrow_range_sampling(self):
        """Test equity with very narrow opponent range."""
        hero = ["Ah", "Kh"]
        opp_range = Range(hands={"AA": 1.0})  # Only AA
        board = ["Kc", "7h", "2s"]
        
        result = calculate_monte_carlo_equity(
            hero,
            opp_range,
            board,
            num_simulations=100
        )
        
        # Hero has pair of Kings, opponent has Aces
        # Hero should lose most of the time
        assert result.equity < 0.30


@pytest.mark.parametrize("hero_hand,villain_hand,expected_range", [
    (["As", "Ad"], ["Ks", "Kd"], (0.80, 0.85)),  # AA vs KK preflop
    (["Ah", "Kh"], ["Ad", "Kc"], (0.10, 0.30)),  # Dominated (same ranks, worse suits)
    (["Jh", "Jc"], ["Ah", "Kd"], (0.53, 0.57)),  # Pocket pair vs overcards (classic flip)
])
def test_parametrized_equity_scenarios(hero_hand, villain_hand, expected_range):
    """Parametrized test for common equity scenarios."""
    result = calculate_equity_vs_specific_hand(
        hero_hand,
        villain_hand,
        board=[],
        num_simulations=500
    )
    
    assert expected_range[0] <= result.equity <= expected_range[1]
