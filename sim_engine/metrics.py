"""
Advanced Metrics Module for HIVE Simulation (Roadmap2 Phase 4).

This module provides detailed performance metrics including:
- Winrate and ROI
- Edge exploitation (how well HIVE capitalizes on advantages)
- Coordination efficiency (benefit from multi-agent cooperation)
- Equity realization (actual profit vs theoretical equity)

Educational Use Only: For research into multi-agent performance
measurement and coordination effectiveness analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sim_engine.hive_simulation import HandResult, SimulationMetrics


@dataclass
class AdvancedMetrics:
    """
    Advanced performance metrics for HIVE simulation analysis.
    
    Attributes:
        base_metrics: Basic simulation metrics (from SimulationMetrics)
        edge_exploitation: How well HIVE converts equity advantage to profit (0.0-1.0)
        coordination_efficiency: Profit boost from coordination vs independent play (%)
        equity_realization: Actual profit / theoretical equity (%)
        variance: Standard deviation of results (bb)
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Largest peak-to-trough decline (bb)
        win_distribution: Distribution of pot sizes won
    """
    base_metrics: SimulationMetrics
    edge_exploitation: float = 0.0
    coordination_efficiency: float = 0.0
    equity_realization: float = 0.0
    variance: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_distribution: Dict[str, int] = field(default_factory=dict)
    
    def summary_dict(self) -> Dict[str, float]:
        """Return summary as dictionary for easy export."""
        return {
            'total_hands': self.base_metrics.total_hands,
            'winrate': self.base_metrics.winrate(),
            'roi': self.base_metrics.roi(),
            'bb_per_100': self.base_metrics.bb_per_100(),
            'total_profit': self.base_metrics.total_profit,
            'edge_exploitation': self.edge_exploitation,
            'coordination_efficiency': self.coordination_efficiency,
            'equity_realization': self.equity_realization,
            'variance': self.variance,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'average_equity': self.base_metrics.average_equity,
            'coordination_bonus': self.base_metrics.coordination_bonus
        }


class MetricsCalculator:
    """
    Calculator for advanced HIVE performance metrics.
    
    Educational Note:
        This class analyzes simulation results to quantify
        coordination effectiveness and edge exploitation in
        multi-agent game theory research scenarios.
    """
    
    def __init__(self):
        """Initialize metrics calculator."""
        self.hand_history: List[HandResult] = []
    
    def calculate_advanced_metrics(
        self,
        base_metrics: SimulationMetrics,
        hand_history: List[HandResult]
    ) -> AdvancedMetrics:
        """
        Calculate advanced metrics from simulation results.
        
        Args:
            base_metrics: Basic metrics from simulation
            hand_history: Full hand-by-hand results
            
        Returns:
            AdvancedMetrics with detailed performance analysis
            
        Educational Note:
            These metrics help researchers understand how effectively
            multi-agent coordination translates into measurable advantages.
        """
        self.hand_history = hand_history
        
        metrics = AdvancedMetrics(base_metrics=base_metrics)
        
        # Calculate each metric
        metrics.edge_exploitation = self._calculate_edge_exploitation()
        metrics.coordination_efficiency = self._calculate_coordination_efficiency()
        metrics.equity_realization = self._calculate_equity_realization()
        metrics.variance = self._calculate_variance()
        metrics.sharpe_ratio = self._calculate_sharpe_ratio(metrics.variance)
        metrics.max_drawdown = self._calculate_max_drawdown()
        metrics.win_distribution = self._calculate_win_distribution()
        
        return metrics
    
    def _calculate_edge_exploitation(self) -> float:
        """
        Calculate edge exploitation: how well HIVE converts equity to profit.
        
        Edge exploitation = (actual winrate) / (average equity)
        - 1.0 = perfect conversion (win exactly as often as equity suggests)
        - >1.0 = over-performing (winning more than equity suggests)
        - <1.0 = under-performing (leaving profit on table)
        
        Returns:
            Edge exploitation ratio (typically 0.7 to 1.3)
            
        Educational Note:
            Measures how effectively coordination translates theoretical
            advantage into realized profit. Research benchmark for
            multi-agent decision quality.
        """
        if not self.hand_history:
            return 0.0
        
        # Calculate actual winrate
        hive_wins = sum(1 for h in self.hand_history if h.winner == "hive")
        actual_winrate = hive_wins / len(self.hand_history)
        
        # Calculate average equity
        avg_equity = sum(h.collective_equity for h in self.hand_history) / len(self.hand_history)
        
        if avg_equity == 0:
            return 0.0
        
        # Edge exploitation ratio
        exploitation = actual_winrate / avg_equity
        
        return exploitation
    
    def _calculate_coordination_efficiency(self) -> float:
        """
        Calculate coordination efficiency: profit boost from cooperation.
        
        Coordination efficiency = (coordination_bonus / total_profit) * 100
        - Positive % = coordination adds value
        - 0% = no coordination benefit
        - Negative % = coordination is counterproductive
        
        Returns:
            Coordination efficiency percentage
            
        Educational Note:
            Quantifies the value-add of multi-agent coordination
            compared to independent play baseline. Key research
            metric for studying emergent cooperation.
        """
        if not self.hand_history:
            return 0.0
        
        total_profit = sum(h.hive_profit for h in self.hand_history)
        
        if total_profit == 0:
            return 0.0
        
        # Estimate independent baseline (50% winrate, break-even)
        # Coordination bonus is profit above this baseline
        coordination_bonus = total_profit  # Simplified: all profit attributed to coordination
        
        efficiency = (coordination_bonus / abs(total_profit)) * 100
        
        return efficiency
    
    def _calculate_equity_realization(self) -> float:
        """
        Calculate equity realization: actual profit vs theoretical EV.
        
        Equity realization = (actual profit / theoretical EV) * 100
        - 100% = perfect realization (profit matches equity)
        - >100% = over-realizing (better than expected)
        - <100% = under-realizing (leaving money on table)
        
        Returns:
            Equity realization percentage
            
        Educational Note:
            Measures decision-making quality by comparing realized
            results to theoretical expectations. Research indicator
            of how well agents execute coordination strategy.
        """
        if not self.hand_history:
            return 0.0
        
        # Actual profit
        actual_profit = sum(h.hive_profit for h in self.hand_history)
        
        # Theoretical EV (simplified: equity * pot)
        theoretical_ev = sum(h.collective_equity * h.pot_size for h in self.hand_history)
        
        if theoretical_ev == 0:
            return 0.0
        
        realization = (actual_profit / theoretical_ev) * 100
        
        return realization
    
    def _calculate_variance(self) -> float:
        """
        Calculate variance (standard deviation of results).
        
        Returns:
            Standard deviation in bb
            
        Educational Note:
            Measures result volatility. Lower variance indicates
            more consistent performance from coordination strategy.
        """
        if len(self.hand_history) < 2:
            return 0.0
        
        profits = [h.hive_profit for h in self.hand_history]
        
        # Calculate mean
        mean_profit = sum(profits) / len(profits)
        
        # Calculate variance
        squared_diffs = [(p - mean_profit) ** 2 for p in profits]
        variance = sum(squared_diffs) / (len(profits) - 1)
        
        # Standard deviation
        std_dev = variance ** 0.5
        
        return std_dev
    
    def _calculate_sharpe_ratio(self, variance: float) -> float:
        """
        Calculate Sharpe ratio: risk-adjusted return.
        
        Sharpe = (mean return) / (standard deviation)
        - Higher is better (more return per unit of risk)
        - >1.0 = good risk-adjusted performance
        - >2.0 = excellent
        
        Args:
            variance: Pre-calculated standard deviation
            
        Returns:
            Sharpe ratio
            
        Educational Note:
            Borrowed from finance, adapted for game theory research
            to measure risk-adjusted coordination effectiveness.
        """
        if not self.hand_history or variance == 0:
            return 0.0
        
        # Mean return per hand
        mean_return = sum(h.hive_profit for h in self.hand_history) / len(self.hand_history)
        
        # Sharpe ratio
        sharpe = mean_return / variance if variance > 0 else 0.0
        
        return sharpe
    
    def _calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown: largest peak-to-trough decline.
        
        Returns:
            Max drawdown in bb (negative value)
            
        Educational Note:
            Measures worst-case losing streak. Important for
            understanding coordination strategy resilience.
        """
        if not self.hand_history:
            return 0.0
        
        # Calculate cumulative profit
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for hand in self.hand_history:
            cumulative += hand.hive_profit
            
            # Update peak
            if cumulative > peak:
                peak = cumulative
            
            # Calculate drawdown
            drawdown = cumulative - peak
            
            # Track max drawdown
            if drawdown < max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_win_distribution(self) -> Dict[str, int]:
        """
        Calculate distribution of win sizes.
        
        Returns:
            Dict with pot size buckets and win counts
            
        Educational Note:
            Shows how coordination affects pot size distribution.
            Research insight into aggressive vs protective strategy mix.
        """
        if not self.hand_history:
            return {}
        
        # Bucket pot sizes
        buckets = {
            'small_pots': 0,    # < 100 bb
            'medium_pots': 0,   # 100-200 bb
            'large_pots': 0,    # > 200 bb
        }
        
        for hand in self.hand_history:
            if hand.winner == "hive":
                if hand.pot_size < 100:
                    buckets['small_pots'] += 1
                elif hand.pot_size < 200:
                    buckets['medium_pots'] += 1
                else:
                    buckets['large_pots'] += 1
        
        return buckets


def compare_strategies(
    hive_metrics: AdvancedMetrics,
    baseline_metrics: Optional[AdvancedMetrics] = None
) -> Dict[str, float]:
    """
    Compare HIVE coordination strategy to baseline (independent play).
    
    Args:
        hive_metrics: Metrics from HIVE simulation
        baseline_metrics: Metrics from independent play (optional)
        
    Returns:
        Dict with comparison metrics (improvement %)
        
    Educational Note:
        Research tool for quantifying coordination advantages.
        Compares HIVE strategy to baseline to measure emergent benefits.
    """
    comparison = {}
    
    if baseline_metrics:
        # Compare winrate
        hive_wr = hive_metrics.base_metrics.winrate()
        baseline_wr = baseline_metrics.base_metrics.winrate()
        comparison['winrate_improvement'] = ((hive_wr - baseline_wr) / baseline_wr * 100) if baseline_wr > 0 else 0.0
        
        # Compare ROI
        hive_roi = hive_metrics.base_metrics.roi()
        baseline_roi = baseline_metrics.base_metrics.roi()
        comparison['roi_improvement'] = hive_roi - baseline_roi
        
        # Compare variance
        comparison['variance_reduction'] = ((baseline_metrics.variance - hive_metrics.variance) / baseline_metrics.variance * 100) if baseline_metrics.variance > 0 else 0.0
    else:
        # Compare to theoretical baseline (50% winrate, 0 ROI)
        hive_wr = hive_metrics.base_metrics.winrate()
        comparison['winrate_vs_breakeven'] = (hive_wr - 0.50) * 100  # % above 50%
        
        comparison['roi_vs_breakeven'] = hive_metrics.base_metrics.roi()
    
    # Add coordination-specific metrics
    comparison['coordination_efficiency'] = hive_metrics.coordination_efficiency
    comparison['edge_exploitation'] = hive_metrics.edge_exploitation
    comparison['equity_realization'] = hive_metrics.equity_realization
    
    return comparison


# Educational Example Usage
if __name__ == "__main__":
    from sim_engine.hive_simulation import HiveSimulation
    
    # Run small simulation
    print("Running HIVE simulation for metrics analysis...")
    sim = HiveSimulation(
        agent_count=20,
        hands_per_session=100,
        lobby_size=100,
        log_interval=50
    )
    
    base_metrics = sim.run()
    
    # Calculate advanced metrics
    calculator = MetricsCalculator()
    advanced = calculator.calculate_advanced_metrics(base_metrics, sim.hand_history)
    
    # Display results
    print("\n" + "=" * 60)
    print("ADVANCED METRICS ANALYSIS")
    print("=" * 60)
    print(f"Winrate: {advanced.base_metrics.winrate():.1%}")
    print(f"ROI: {advanced.base_metrics.roi():.1f}%")
    print(f"bb/100: {advanced.base_metrics.bb_per_100():.2f}")
    print(f"\nEdge Exploitation: {advanced.edge_exploitation:.2f}x")
    print(f"Coordination Efficiency: {advanced.coordination_efficiency:.1f}%")
    print(f"Equity Realization: {advanced.equity_realization:.1f}%")
    print(f"\nVariance (σ): {advanced.variance:.2f}bb")
    print(f"Sharpe Ratio: {advanced.sharpe_ratio:.3f}")
    print(f"Max Drawdown: {advanced.max_drawdown:.2f}bb")
    print(f"\nWin Distribution:")
    for bucket, count in advanced.win_distribution.items():
        print(f"  {bucket}: {count} pots")
    print("=" * 60)
    
    # Compare to baseline
    comparison = compare_strategies(advanced)
    print("\nCOMPARISON vs BASELINE:")
    for metric, value in comparison.items():
        print(f"  {metric}: {value:.2f}")
    print("=" * 60)
