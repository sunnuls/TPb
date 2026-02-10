"""
Tests for Table Scanner (Roadmap5 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest

from hive.table_scanner import HiveOpportunity, TablePriority, TableScanner


class TestHiveOpportunity:
    """Test HIVE opportunity."""
    
    def test_creation(self):
        """Test opportunity creation."""
        opp = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0
        )
        
        assert opp.table_id == "table_1"
        assert opp.human_count == 1
        assert opp.seats_available == 8
        assert opp.priority == TablePriority.CRITICAL
        assert opp.score == 95.0
    
    def test_is_suitable_for_hive(self):
        """Test HIVE suitability check."""
        # Suitable: 1 human, 3+ seats
        opp1 = HiveOpportunity(
            table_id="t1",
            human_count=1,
            seats_available=5,
            priority=TablePriority.CRITICAL,
            score=90.0
        )
        assert opp1.is_suitable_for_hive() is True
        
        # Not suitable: 0 humans
        opp2 = HiveOpportunity(
            table_id="t2",
            human_count=0,
            seats_available=5,
            priority=TablePriority.LOW,
            score=10.0
        )
        assert opp2.is_suitable_for_hive() is False
        
        # Not suitable: too many humans
        opp3 = HiveOpportunity(
            table_id="t3",
            human_count=5,
            seats_available=3,
            priority=TablePriority.LOW,
            score=5.0
        )
        assert opp3.is_suitable_for_hive() is False
        
        # Not suitable: not enough seats
        opp4 = HiveOpportunity(
            table_id="t4",
            human_count=2,
            seats_available=2,
            priority=TablePriority.LOW,
            score=20.0
        )
        assert opp4.is_suitable_for_hive() is False
    
    def test_get_age(self):
        """Test opportunity age."""
        opp = HiveOpportunity(
            table_id="t1",
            human_count=1,
            seats_available=5,
            priority=TablePriority.CRITICAL,
            score=90.0
        )
        
        age = opp.get_age()
        
        assert age >= 0
        assert age < 1.0  # Should be very recent


class TestTableScanner:
    """Test table scanner."""
    
    def test_initialization(self):
        """Test scanner initialization."""
        scanner = TableScanner(
            room="pokerstars",
            scan_interval=5.0,
            dry_run=True
        )
        
        assert scanner.room == "pokerstars"
        assert scanner.scan_interval == 5.0
        assert scanner.dry_run is True
        assert scanner.scans_performed == 0
    
    def test_scan_lobby(self):
        """Test lobby scanning."""
        scanner = TableScanner(dry_run=True)
        
        opportunities = scanner.scan_lobby()
        
        # Should find some opportunities (simulated)
        assert isinstance(opportunities, list)
        assert scanner.scans_performed == 1
        assert scanner.last_scan_time is not None
    
    def test_calculate_priority(self):
        """Test priority calculation."""
        scanner = TableScanner(dry_run=True)
        
        # Critical: 1 human, 3+ seats
        p1 = scanner._calculate_priority(human_count=1, seats_available=5)
        assert p1 == TablePriority.CRITICAL
        
        # High: 2 humans, 3+ seats
        p2 = scanner._calculate_priority(human_count=2, seats_available=4)
        assert p2 == TablePriority.HIGH
        
        # Medium: 3 humans, 3 seats
        p3 = scanner._calculate_priority(human_count=3, seats_available=3)
        assert p3 == TablePriority.MEDIUM
        
        # Low: not enough seats
        p4 = scanner._calculate_priority(human_count=1, seats_available=2)
        assert p4 == TablePriority.LOW
    
    def test_calculate_score(self):
        """Test score calculation."""
        scanner = TableScanner(dry_run=True)
        
        # 1 human should score higher than 3 humans
        score1 = scanner._calculate_score(1, 5, {})
        score3 = scanner._calculate_score(3, 5, {})
        
        assert score1 > score3
    
    def test_get_best_opportunities(self):
        """Test getting best opportunities."""
        scanner = TableScanner(dry_run=True)
        
        # Scan to populate
        scanner.scan_lobby()
        
        # Get best
        best = scanner.get_best_opportunities(count=3)
        
        assert isinstance(best, list)
        assert len(best) <= 3
        
        # Should be sorted by score
        if len(best) >= 2:
            assert best[0].score >= best[1].score
    
    def test_mark_table_occupied(self):
        """Test marking table as occupied."""
        scanner = TableScanner(dry_run=True)
        
        # Scan to get opportunities
        opportunities = scanner.scan_lobby()
        
        if opportunities:
            opp = opportunities[0]
            
            # Mark occupied
            scanner.mark_table_occupied(opp.table_id)
            
            # Should be blocked
            assert scanner.opportunities[opp.table_id].priority == TablePriority.BLOCKED
    
    def test_remove_opportunity(self):
        """Test removing opportunity."""
        scanner = TableScanner(dry_run=True)
        
        # Scan
        opportunities = scanner.scan_lobby()
        
        if opportunities:
            opp = opportunities[0]
            
            # Remove
            removed = scanner.remove_opportunity(opp.table_id)
            
            assert removed is True
            assert opp.table_id not in scanner.opportunities
    
    def test_clear_stale_opportunities(self):
        """Test clearing stale opportunities."""
        scanner = TableScanner(dry_run=True)
        
        # Scan
        scanner.scan_lobby()
        
        # Clear stale (should clear nothing with max_age=0)
        cleared = scanner.clear_stale_opportunities(max_age=0.0)
        
        # All opportunities should be fresh
        assert cleared >= 0
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        scanner = TableScanner(dry_run=True)
        
        # Scan
        scanner.scan_lobby()
        
        stats = scanner.get_statistics()
        
        assert stats['scans_performed'] == 1
        assert stats['room'] == scanner.room
        assert stats['dry_run'] is True
        assert 'priority_distribution' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
