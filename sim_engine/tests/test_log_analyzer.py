"""
Tests for Log Analyzer.

Educational Use Only: Validates log analysis and optimization
identification for research simulations (Шаг 4.3).
"""

import pytest
from datetime import datetime
from pathlib import Path

# Import analyzer components
import sys
analysis_path = Path(__file__).parent.parent / "analysis"
sys.path.insert(0, str(analysis_path))

from log_analyzer import (
    LogEntry,
    PerformanceMetrics,
    OptimizationOpportunity,
    SimulationLogAnalyzer
)


class TestLogEntry:
    """Test LogEntry dataclass."""
    
    def test_log_entry_creation(self):
        """Test creating log entry."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            agent_id='agent_1',
            event_type='decision',
            data={'action': 'increment'}
        )
        
        assert entry.agent_id == 'agent_1'
        assert entry.event_type == 'decision'
        assert entry.data['action'] == 'increment'


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            total_decisions=1000,
            total_anomalies=50,
            average_latency_ms=45.0
        )
        
        assert metrics.total_decisions == 1000
        assert metrics.total_anomalies == 50
        assert metrics.average_latency_ms == 45.0


class TestOptimizationOpportunity:
    """Test OptimizationOpportunity dataclass."""
    
    def test_opportunity_creation(self):
        """Test creating optimization opportunity."""
        opp = OptimizationOpportunity(
            category='performance',
            severity='high',
            description='High latency detected',
            impact_estimate='+5% efficiency',
            recommendation='Cache calculations'
        )
        
        assert opp.category == 'performance'
        assert opp.severity == 'high'
        assert '+5%' in opp.impact_estimate


class TestSimulationLogAnalyzer:
    """Test SimulationLogAnalyzer main functionality."""
    
    def test_analyzer_creation(self):
        """Test creating log analyzer."""
        analyzer = SimulationLogAnalyzer()
        
        assert analyzer.log_dir == Path('logs')
        assert len(analyzer.entries) == 0
        assert analyzer.metrics is None
    
    def test_load_logs_generates_samples(self):
        """Test loading logs generates sample data."""
        analyzer = SimulationLogAnalyzer()
        
        count = analyzer.load_logs()
        
        # Should generate sample logs
        assert count > 0
        assert len(analyzer.entries) == count
    
    def test_entries_sorted_by_timestamp(self):
        """Test entries are sorted chronologically."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        if len(analyzer.entries) > 1:
            for i in range(len(analyzer.entries) - 1):
                assert analyzer.entries[i].timestamp <= analyzer.entries[i + 1].timestamp


class TestPerformanceAnalysis:
    """Test performance analysis functionality (Пункт 1)."""
    
    def test_analyze_performance_basic(self):
        """Test basic performance analysis."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        metrics = analyzer.analyze_performance()
        
        assert metrics.total_decisions >= 0
        assert metrics.total_anomalies >= 0
        assert 0 <= metrics.anomaly_rate <= 1
        assert metrics.average_latency_ms >= 0
        assert metrics.decisions_per_second >= 0
    
    def test_analyze_performance_calculates_anomaly_rate(self):
        """Test anomaly rate calculation."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        metrics = analyzer.analyze_performance()
        
        if metrics.total_decisions > 0:
            expected_rate = metrics.total_anomalies / metrics.total_decisions
            assert abs(metrics.anomaly_rate - expected_rate) < 0.001
    
    def test_analyze_performance_efficiency_score(self):
        """Test efficiency score calculation."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        metrics = analyzer.analyze_performance()
        
        # Efficiency should be 0-100
        assert 0 <= metrics.efficiency_score <= 100
    
    def test_analyze_performance_identifies_slow_operations(self):
        """Test identification of slow operations."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        metrics = analyzer.analyze_performance()
        
        # Should have slow_operations list (may be empty)
        assert isinstance(metrics.slow_operations, list)
        
        # If there are slow ops, they should be tuples
        for op in metrics.slow_operations:
            assert isinstance(op, tuple)
            assert len(op) == 2  # (agent_id, latency)
    
    def test_analyze_performance_equity_distribution(self):
        """Test equity distribution analysis."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        metrics = analyzer.analyze_performance()
        
        # Should have equity distribution buckets
        assert isinstance(metrics.equity_distribution, dict)
        
        # Valid buckets: low, medium, high
        for bucket in metrics.equity_distribution.keys():
            assert bucket in ['low', 'medium', 'high']


class TestOptimizationIdentification:
    """Test optimization identification (Пункт 1: suggest enhancements for +10% efficiency)."""
    
    def test_identify_optimizations_returns_list(self):
        """Test optimization identification returns list."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        opportunities = analyzer.identify_optimizations()
        
        assert isinstance(opportunities, list)
    
    def test_opportunities_have_required_fields(self):
        """Test opportunities have all required fields."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        opportunities = analyzer.identify_optimizations()
        
        if opportunities:
            opp = opportunities[0]
            assert hasattr(opp, 'category')
            assert hasattr(opp, 'severity')
            assert hasattr(opp, 'description')
            assert hasattr(opp, 'impact_estimate')
            assert hasattr(opp, 'recommendation')
    
    def test_high_severity_opportunities_flagged(self):
        """Test high severity issues are identified."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        opportunities = analyzer.identify_optimizations()
        
        # Should identify at least some opportunities from sample data
        assert len(opportunities) > 0
        
        # Should have severity levels
        severities = {opp.severity for opp in opportunities}
        assert severities.issubset({'high', 'medium', 'low'})
    
    def test_optimization_categories(self):
        """Test optimization categories are valid."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        opportunities = analyzer.identify_optimizations()
        
        valid_categories = {'performance', 'anomaly', 'equity', 'coordination'}
        
        for opp in opportunities:
            assert opp.category in valid_categories
    
    def test_impact_estimates_provided(self):
        """Test all opportunities have impact estimates."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        opportunities = analyzer.identify_optimizations()
        
        for opp in opportunities:
            assert opp.impact_estimate
            assert '%' in opp.impact_estimate  # Should mention percentage


class TestReportGeneration:
    """Test report generation (Подпункт 1.2: document changes)."""
    
    def test_generate_report_creates_content(self):
        """Test report generation creates content."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        assert len(report) > 0
        assert 'Optimization Analysis Report' in report
    
    def test_report_contains_metrics(self):
        """Test report contains performance metrics."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        assert 'Total Decisions' in report
        assert 'Anomaly Rate' in report
        assert 'Average Latency' in report
        assert 'Efficiency Score' in report
    
    def test_report_contains_opportunities(self):
        """Test report contains optimization opportunities."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        assert 'Optimization Opportunities' in report
        assert 'Recommendation' in report
    
    def test_report_contains_next_steps(self):
        """Test report contains actionable next steps (Подпункт 1.1)."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        assert 'Next Steps' in report
        assert 'Priority' in report
    
    def test_report_markdown_format(self):
        """Test report is valid Markdown."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        # Should have Markdown headers
        assert report.count('#') > 0
        assert report.count('##') > 0
        
        # Should have lists
        assert '-' in report
    
    def test_report_educational_context(self):
        """Test report includes educational context."""
        analyzer = SimulationLogAnalyzer()
        analyzer.load_logs()
        
        report = analyzer.generate_report('test_report.md')
        
        assert 'Educational' in report or 'Research' in report


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_analyze_empty_logs(self):
        """Test analyzing with no logs."""
        analyzer = SimulationLogAnalyzer()
        # Don't load logs
        
        metrics = analyzer.analyze_performance()
        
        assert metrics.total_decisions == 0
        assert metrics.total_anomalies == 0
        assert metrics.efficiency_score == 0.0
    
    def test_identify_optimizations_empty_logs(self):
        """Test optimization identification with no data."""
        analyzer = SimulationLogAnalyzer()
        
        opportunities = analyzer.identify_optimizations()
        
        # Should still return list (may be empty or have generic suggestions)
        assert isinstance(opportunities, list)


class TestIntegration:
    """Test full analysis workflow."""
    
    def test_full_analysis_workflow(self):
        """Test complete analysis workflow (Пункт 1)."""
        analyzer = SimulationLogAnalyzer()
        
        # Load logs
        count = analyzer.load_logs()
        assert count > 0
        
        # Analyze performance
        metrics = analyzer.analyze_performance()
        assert metrics.total_decisions > 0
        
        # Identify optimizations
        opportunities = analyzer.identify_optimizations()
        assert len(opportunities) > 0
        
        # Generate report
        report = analyzer.generate_report('test_full_report.md')
        assert len(report) > 1000  # Should be substantial
        
        # Verify +10% efficiency target
        assert '+10' in report or '+15' in report
