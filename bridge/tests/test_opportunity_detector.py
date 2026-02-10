"""
Tests for OpportunityDetector (Roadmap3 Phase 3.2).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from bridge.opportunity_detector import (
    OpportunityDetector,
    HiveOpportunity,
    OpportunityReport,
    OpportunityScore
)
from bridge.lobby_scanner import LobbyScanner, LobbyTable, TableType


class TestHiveOpportunity:
    """Test HiveOpportunity dataclass."""
    
    def test_hive_opportunity_creation(self):
        """Test basic opportunity creation."""
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=1
        )
        
        opp = HiveOpportunity(
            table=table,
            score=OpportunityScore.PERFECT,
            priority=100.0,
            required_agents=3,
            reason="Perfect 3vs1 scenario"
        )
        
        assert opp.table == table
        assert opp.score == OpportunityScore.PERFECT
        assert opp.priority == 100.0
        assert opp.required_agents == 3
        assert opp.current_opponents == 1  # Auto-calculated
        assert opp.expected_opponents == 1  # Auto-calculated
    
    def test_hive_opportunity_auto_calculation(self):
        """Test auto-calculation of opponent counts."""
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=2
        )
        
        opp = HiveOpportunity(
            table=table,
            score=OpportunityScore.EXCELLENT,
            priority=80.0
        )
        
        # Should auto-calculate from table.occupied_seats
        assert opp.current_opponents == 2
        assert opp.expected_opponents == 2


class TestOpportunityReport:
    """Test OpportunityReport dataclass."""
    
    def test_opportunity_report_creation(self):
        """Test basic report creation."""
        from bridge.lobby_scanner import LobbySnapshot
        
        snapshot = LobbySnapshot(timestamp=0.0)
        
        table1 = LobbyTable(table_id="t1", max_seats=6, occupied_seats=1)
        table2 = LobbyTable(table_id="t2", max_seats=6, occupied_seats=2)
        
        opp1 = HiveOpportunity(
            table=table1,
            score=OpportunityScore.PERFECT,
            priority=100.0
        )
        opp2 = HiveOpportunity(
            table=table2,
            score=OpportunityScore.EXCELLENT,
            priority=80.0
        )
        
        report = OpportunityReport(
            snapshot=snapshot,
            opportunities=[opp1, opp2]
        )
        
        assert len(report.opportunities) == 2
        assert report.perfect_count == 1
        assert report.excellent_count == 1
        assert report.good_count == 0
        assert report.best_opportunity == opp1  # Highest priority


class TestOpportunityDetector:
    """Test OpportunityDetector core functionality."""
    
    def test_init(self):
        """Test initialization."""
        detector = OpportunityDetector(min_priority=50.0)
        
        assert detector.min_priority == 50.0
        assert detector.detections_count == 0
        assert detector.last_report is None
    
    def test_detect_opportunities_dry_run(self):
        """Test opportunity detection in dry-run mode."""
        detector = OpportunityDetector(min_priority=50.0)
        
        report = detector.detect_opportunities(required_agents=3)
        
        assert report is not None
        assert len(report.opportunities) >= 0
        assert detector.detections_count == 1
    
    def test_detect_opportunities_finds_tables(self):
        """Test detection finds opportunities."""
        detector = OpportunityDetector(min_priority=0.0)  # Accept all
        
        report = detector.detect_opportunities(required_agents=3)
        
        # Should find some opportunities in simulated lobby
        assert len(report.opportunities) > 0
    
    def test_detect_opportunities_priority_scoring(self):
        """Test priority scoring matches HIVE logic."""
        detector = OpportunityDetector(min_priority=0.0)
        
        report = detector.detect_opportunities(required_agents=3)
        
        # Check that opportunities are sorted by priority
        priorities = [opp.priority for opp in report.opportunities]
        assert priorities == sorted(priorities, reverse=True)
        
        # Check that perfect opportunities have highest priority
        perfect_opps = [
            opp for opp in report.opportunities 
            if opp.score == OpportunityScore.PERFECT
        ]
        if perfect_opps:
            assert all(opp.priority == 100.0 for opp in perfect_opps)
    
    def test_detect_opportunities_with_threshold(self):
        """Test priority threshold filtering."""
        # High threshold - should get fewer opportunities
        detector_high = OpportunityDetector(min_priority=80.0)
        report_high = detector_high.detect_opportunities()
        
        # Low threshold - should get more opportunities
        detector_low = OpportunityDetector(min_priority=40.0)
        report_low = detector_low.detect_opportunities()
        
        # All high-priority opportunities should have priority >= 80
        for opp in report_high.opportunities:
            assert opp.priority >= 80.0
        
        # Low threshold should return more opportunities
        assert len(report_low.opportunities) >= len(report_high.opportunities)
    
    def test_evaluate_table_perfect_3vs1(self):
        """Test evaluation of perfect 3vs1 scenario."""
        detector = OpportunityDetector()
        
        # Table with 1 opponent, 5 seats left (perfect for 3 agents)
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=1
        )
        
        opp = detector._evaluate_table(table, required_agents=3)
        
        assert opp is not None
        assert opp.score == OpportunityScore.PERFECT
        assert opp.priority == 100.0
        assert opp.expected_opponents == 1
    
    def test_evaluate_table_excellent_3vs2(self):
        """Test evaluation of excellent 3vs2 scenario."""
        detector = OpportunityDetector()
        
        # Table with 2 opponents, 4 seats left
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=2
        )
        
        opp = detector._evaluate_table(table, required_agents=3)
        
        assert opp is not None
        assert opp.score == OpportunityScore.EXCELLENT
        assert opp.priority == 80.0
        assert opp.expected_opponents == 2
    
    def test_evaluate_table_good_3vs3(self):
        """Test evaluation of good 3vs3 scenario."""
        detector = OpportunityDetector()
        
        # Table with 3 opponents, 3 seats left
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=3
        )
        
        opp = detector._evaluate_table(table, required_agents=3)
        
        assert opp is not None
        assert opp.score == OpportunityScore.GOOD
        assert opp.priority == 60.0
        assert opp.expected_opponents == 3
    
    def test_evaluate_table_insufficient_seats(self):
        """Test evaluation rejects table with insufficient seats."""
        detector = OpportunityDetector()
        
        # Table with only 2 seats left (need 3)
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=4
        )
        
        opp = detector._evaluate_table(table, required_agents=3)
        
        # Should return None - not enough seats
        assert opp is None
    
    def test_get_best_opportunity(self):
        """Test getting best opportunity."""
        detector = OpportunityDetector(min_priority=0.0)
        
        # Detect opportunities
        report = detector.detect_opportunities()
        
        # Get best opportunity
        best = detector.get_best_opportunity()
        
        if report.opportunities:
            assert best is not None
            assert best == report.best_opportunity
            # Should be highest priority
            assert best.priority == max(opp.priority for opp in report.opportunities)
        else:
            assert best is None
    
    def test_get_statistics(self):
        """Test statistics collection."""
        detector = OpportunityDetector(min_priority=50.0)
        
        detector.detect_opportunities()
        detector.detect_opportunities()
        
        stats = detector.get_statistics()
        
        assert stats['total_detections'] == 2
        assert stats['min_priority'] == 50.0
        assert stats['last_report'] is not None


class TestOpportunityIntegration:
    """Integration tests for opportunity detector."""
    
    def test_full_detection_workflow(self):
        """Test complete opportunity detection workflow."""
        # Create scanner and detector
        scanner = LobbyScanner(dry_run=True)
        detector = OpportunityDetector(lobby_scanner=scanner, min_priority=50.0)
        
        # Detect opportunities
        report = detector.detect_opportunities(required_agents=3, max_seats_filter=6)
        
        # Validate report
        assert report is not None
        assert report.snapshot is not None
        
        # Should have some opportunities
        if report.opportunities:
            # Check best opportunity
            best = report.best_opportunity
            assert best is not None
            assert best.priority >= 50.0
            assert best.table.seats_left >= 3
            
            # Verify priority ordering
            for i in range(len(report.opportunities) - 1):
                assert report.opportunities[i].priority >= report.opportunities[i+1].priority
    
    def test_detection_with_custom_scanner(self):
        """Test detection with custom lobby scanner."""
        scanner = LobbyScanner(dry_run=True)
        detector = OpportunityDetector(lobby_scanner=scanner)
        
        # Both should be using same scanner
        assert detector.lobby_scanner == scanner
        
        report = detector.detect_opportunities()
        assert report is not None
    
    def test_opportunity_counts(self):
        """Test opportunity count categorization."""
        detector = OpportunityDetector(min_priority=0.0)
        
        report = detector.detect_opportunities()
        
        # Count totals should match
        total_counted = (
            report.perfect_count + 
            report.excellent_count + 
            report.good_count
        )
        
        # At most total_counted should be <= total opportunities
        # (some may be marginal/poor)
        assert total_counted <= len(report.opportunities)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
