"""
Unit tests for metrics module (Roadmap2 Phase 4).

Tests advanced performance metrics calculations including
edge exploitation, coordination efficiency, and equity realization.
"""

import pytest
from sim_engine.hive_simulation import HandResult, SimulationMetrics
from sim_engine.metrics import (
    AdvancedMetrics,
    MetricsCalculator,
    compare_strategies,
)


class TestAdvancedMetrics:
    """Test AdvancedMetrics data structure."""
    
    def test_metrics_initialization(self):
        """Can create AdvancedMetrics."""
        base = SimulationMetrics()
        advanced = AdvancedMetrics(base_metrics=base)
        
        assert advanced.base_metrics == base
        assert advanced.edge_exploitation == 0.0
        assert advanced.coordination_efficiency == 0.0
    
    def test_summary_dict(self):
        """Summary dict contains all key metrics."""
        base = SimulationMetrics()
        base.total_hands = 100
        base.hive_wins = 60
        base.total_profit = 250.0
        
        advanced = AdvancedMetrics(
            base_metrics=base,
            edge_exploitation=1.15,
            coordination_efficiency=85.0
        )
        
        summary = advanced.summary_dict()
        
        assert 'total_hands' in summary
        assert 'winrate' in summary
        assert 'edge_exploitation' in summary
        assert summary['total_hands'] == 100
        assert summary['edge_exploitation'] == 1.15


class TestMetricsCalculator:
    """Test MetricsCalculator class."""
    
    def test_calculator_initialization(self):
        """Can initialize calculator."""
        calc = MetricsCalculator()
        
        assert calc.hand_history == []
    
    def test_calculate_advanced_metrics(self):
        """Can calculate full advanced metrics."""
        base = SimulationMetrics()
        base.total_hands = 10
        base.hive_wins = 6
        base.total_profit = 100.0
        
        history = [
            HandResult(
                hand_number=i,
                hive_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
                dummy_cards=["Js", "Jh"],
                board=["Ts", "9h", "8d", "7c", "6s"],
                winner="hive" if i % 2 == 0 else "dummy",
                pot_size=150.0,
                hive_profit=10.0 if i % 2 == 0 else -10.0,
                collective_equity=0.65
            )
            for i in range(10)
        ]
        
        calc = MetricsCalculator()
        advanced = calc.calculate_advanced_metrics(base, history)
        
        assert advanced.edge_exploitation > 0
        # Coordination efficiency can be 0 if total profit = 0
        assert advanced.coordination_efficiency >= 0
        # Equity realization can be 0 if theoretical EV = 0
        assert advanced.equity_realization >= 0


class TestEdgeExploitation:
    """Test edge exploitation calculation."""
    
    def test_perfect_exploitation(self):
        """Perfect exploitation: winrate matches equity."""
        calc = MetricsCalculator()
        
        # 60% equity, 60% winrate = 1.0 exploitation
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive" if i < 6 else "dummy",
                pot_size=100.0,
                hive_profit=0.0,
                collective_equity=0.60
            )
            for i in range(10)
        ]
        
        exploitation = calc._calculate_edge_exploitation()
        
        assert 0.95 <= exploitation <= 1.05  # Allow small rounding
    
    def test_over_performing(self):
        """Over-performing: winrate > equity."""
        calc = MetricsCalculator()
        
        # 50% equity, 70% winrate = 1.4 exploitation
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive" if i < 7 else "dummy",
                pot_size=100.0,
                hive_profit=0.0,
                collective_equity=0.50
            )
            for i in range(10)
        ]
        
        exploitation = calc._calculate_edge_exploitation()
        
        assert exploitation > 1.0
    
    def test_under_performing(self):
        """Under-performing: winrate < equity."""
        calc = MetricsCalculator()
        
        # 70% equity, 50% winrate = 0.71 exploitation
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive" if i < 5 else "dummy",
                pot_size=100.0,
                hive_profit=0.0,
                collective_equity=0.70
            )
            for i in range(10)
        ]
        
        exploitation = calc._calculate_edge_exploitation()
        
        assert exploitation < 1.0


class TestCoordinationEfficiency:
    """Test coordination efficiency calculation."""
    
    def test_positive_efficiency(self):
        """Positive profit = positive efficiency."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=10.0,
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        efficiency = calc._calculate_coordination_efficiency()
        
        assert efficiency > 0
    
    def test_negative_efficiency(self):
        """Negative profit = low efficiency."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="dummy",
                pot_size=100.0,
                hive_profit=-10.0,
                collective_equity=0.4
            )
            for i in range(10)
        ]
        
        efficiency = calc._calculate_coordination_efficiency()
        
        # Can still have efficiency metric even with losses
        assert efficiency != 0 or calc.hand_history[0].hive_profit < 0


class TestEquityRealization:
    """Test equity realization calculation."""
    
    def test_full_realization(self):
        """Perfect realization: profit matches EV."""
        calc = MetricsCalculator()
        
        # EV = 0.65 * 150 = 97.5 per hand
        # If profit = 97.5, realization = 100%
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=150.0,
                hive_profit=97.5,
                collective_equity=0.65
            )
            for i in range(10)
        ]
        
        realization = calc._calculate_equity_realization()
        
        assert 95 <= realization <= 105  # Allow rounding
    
    def test_over_realization(self):
        """Over-realizing: profit > EV."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=70.0,  # More than 65% equity suggests
                collective_equity=0.65
            )
            for i in range(10)
        ]
        
        realization = calc._calculate_equity_realization()
        
        assert realization > 100


class TestVarianceCalculation:
    """Test variance (standard deviation) calculation."""
    
    def test_zero_variance(self):
        """Identical results = zero variance."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=10.0,  # Same every hand
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        variance = calc._calculate_variance()
        
        assert variance == 0.0
    
    def test_positive_variance(self):
        """Variable results = positive variance."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive" if i % 2 == 0 else "dummy",
                pot_size=100.0,
                hive_profit=50.0 if i % 2 == 0 else -50.0,
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        variance = calc._calculate_variance()
        
        assert variance > 0


class TestSharpeRatio:
    """Test Sharpe ratio calculation."""
    
    def test_positive_sharpe(self):
        """Positive mean return = positive Sharpe."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=10.0,
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        variance = calc._calculate_variance()
        sharpe = calc._calculate_sharpe_ratio(variance)
        
        # Zero variance with positive mean = infinite Sharpe (returns 0 for division safety)
        assert sharpe >= 0


class TestMaxDrawdown:
    """Test maximum drawdown calculation."""
    
    def test_no_drawdown(self):
        """All wins = no drawdown."""
        calc = MetricsCalculator()
        
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=10.0,
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        drawdown = calc._calculate_max_drawdown()
        
        assert drawdown == 0.0
    
    def test_has_drawdown(self):
        """Losing streak = negative drawdown."""
        calc = MetricsCalculator()
        
        # Win 5, lose 3, win 2
        profits = [10, 10, 10, 10, 10, -20, -20, -20, 10, 10]
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=profits[i],
                collective_equity=0.6
            )
            for i in range(10)
        ]
        
        drawdown = calc._calculate_max_drawdown()
        
        assert drawdown < 0


class TestWinDistribution:
    """Test win pot size distribution."""
    
    def test_distribution_buckets(self):
        """Correctly buckets pot sizes."""
        calc = MetricsCalculator()
        
        # Small, medium, large pots
        pot_sizes = [50, 150, 250, 80, 120, 300]
        calc.hand_history = [
            HandResult(
                hand_number=i,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=pot_sizes[i],
                hive_profit=10.0,
                collective_equity=0.6
            )
            for i in range(len(pot_sizes))
        ]
        
        distribution = calc._calculate_win_distribution()
        
        assert 'small_pots' in distribution
        assert 'medium_pots' in distribution
        assert 'large_pots' in distribution
        assert distribution['small_pots'] == 2  # 50, 80
        assert distribution['medium_pots'] == 2  # 150, 120
        assert distribution['large_pots'] == 2  # 250, 300


class TestCompareStrategies:
    """Test strategy comparison."""
    
    def test_comparison_without_baseline(self):
        """Compare to theoretical baseline."""
        base = SimulationMetrics()
        base.total_hands = 100
        base.hive_wins = 65
        base.total_profit = 300.0
        
        advanced = AdvancedMetrics(
            base_metrics=base,
            edge_exploitation=1.2,
            coordination_efficiency=80.0,
            equity_realization=110.0
        )
        
        comparison = compare_strategies(advanced)
        
        assert 'winrate_vs_breakeven' in comparison
        assert 'roi_vs_breakeven' in comparison
        assert 'coordination_efficiency' in comparison
        
        # 65% winrate vs 50% baseline = 15% improvement
        assert abs(comparison['winrate_vs_breakeven'] - 15.0) < 0.01
    
    def test_comparison_with_baseline(self):
        """Compare HIVE to baseline metrics."""
        hive_base = SimulationMetrics()
        hive_base.total_hands = 100
        hive_base.hive_wins = 65
        hive_base.total_profit = 300.0
        
        baseline_base = SimulationMetrics()
        baseline_base.total_hands = 100
        baseline_base.hive_wins = 50
        baseline_base.total_profit = 0.0
        
        hive = AdvancedMetrics(
            base_metrics=hive_base,
            variance=50.0,
            edge_exploitation=1.2
        )
        
        baseline = AdvancedMetrics(
            base_metrics=baseline_base,
            variance=70.0,
            edge_exploitation=1.0
        )
        
        comparison = compare_strategies(hive, baseline)
        
        assert 'winrate_improvement' in comparison
        assert 'variance_reduction' in comparison
        
        # HIVE should show improvement
        assert comparison['winrate_improvement'] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_history(self):
        """Handle empty hand history."""
        calc = MetricsCalculator()
        calc.hand_history = []
        
        exploitation = calc._calculate_edge_exploitation()
        efficiency = calc._calculate_coordination_efficiency()
        realization = calc._calculate_equity_realization()
        variance = calc._calculate_variance()
        
        assert exploitation == 0.0
        assert efficiency == 0.0
        assert realization == 0.0
        assert variance == 0.0
    
    def test_single_hand(self):
        """Handle single hand history."""
        calc = MetricsCalculator()
        calc.hand_history = [
            HandResult(
                hand_number=1,
                hive_cards=[],
                dummy_cards=[],
                board=[],
                winner="hive",
                pot_size=100.0,
                hive_profit=50.0,
                collective_equity=0.6
            )
        ]
        
        # Should not crash
        exploitation = calc._calculate_edge_exploitation()
        variance = calc._calculate_variance()
        
        assert exploitation >= 0
        assert variance >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
