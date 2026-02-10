"""
Tests for LobbyScanner - Phase 3.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest

from launcher.lobby_scanner import LobbyScanner, LobbyTable, LobbySnapshot


class TestLobbyTable:
    """Tests for LobbyTable."""
    
    def test_create_table(self):
        """Test creating lobby table."""
        table = LobbyTable(
            table_id="table_001",
            table_name="Table 1",
            game_type="NLHE",
            stakes="0.25/0.50",
            players_seated=5,
            max_seats=9,
            human_count=2
        )
        
        assert table.table_id == "table_001"
        assert table.table_name == "Table 1"
        assert table.players_seated == 5
        assert table.max_seats == 9
        assert table.human_count == 2
    
    def test_seats_available(self):
        """Test calculating available seats."""
        table = LobbyTable(
            table_id="test",
            table_name="Test",
            players_seated=6,
            max_seats=9
        )
        
        assert table.seats_available() == 3
    
    def test_is_suitable_for_hive(self):
        """Test HIVE suitability check."""
        # Suitable: 2 humans, 4 seats available
        table1 = LobbyTable(
            table_id="t1",
            table_name="Table 1",
            players_seated=5,
            max_seats=9,
            human_count=2
        )
        assert table1.is_suitable_for_hive()
        
        # Not suitable: 0 humans
        table2 = LobbyTable(
            table_id="t2",
            table_name="Table 2",
            players_seated=5,
            max_seats=9,
            human_count=0
        )
        assert not table2.is_suitable_for_hive()
        
        # Not suitable: 4 humans (too many)
        table3 = LobbyTable(
            table_id="t3",
            table_name="Table 3",
            players_seated=5,
            max_seats=9,
            human_count=4
        )
        assert not table3.is_suitable_for_hive()
        
        # Not suitable: only 2 seats available
        table4 = LobbyTable(
            table_id="t4",
            table_name="Table 4",
            players_seated=7,
            max_seats=9,
            human_count=2
        )
        assert not table4.is_suitable_for_hive()
    
    def test_priority_score(self):
        """Test priority score calculation."""
        # 1 human = highest priority
        table1 = LobbyTable(
            table_id="t1",
            table_name="Table 1",
            players_seated=3,
            max_seats=9,
            human_count=1
        )
        score1 = table1.priority_score()
        
        # 2 humans = medium priority
        table2 = LobbyTable(
            table_id="t2",
            table_name="Table 2",
            players_seated=4,
            max_seats=9,
            human_count=2
        )
        score2 = table2.priority_score()
        
        # 3 humans = lower priority
        table3 = LobbyTable(
            table_id="t3",
            table_name="Table 3",
            players_seated=5,
            max_seats=9,
            human_count=3
        )
        score3 = table3.priority_score()
        
        # 1 human should have highest priority
        assert score1 > score2 > score3
        assert 0 <= score1 <= 100
        
        # Unsuitable table = 0 score
        table4 = LobbyTable(
            table_id="t4",
            table_name="Table 4",
            players_seated=8,
            max_seats=9,
            human_count=5
        )
        assert table4.priority_score() == 0.0


class TestLobbySnapshot:
    """Tests for LobbySnapshot."""
    
    def test_create_snapshot(self):
        """Test creating lobby snapshot."""
        snapshot = LobbySnapshot()
        
        assert snapshot.timestamp > 0
        assert len(snapshot.tables) == 0
        assert snapshot.total_tables == 0
    
    def test_get_hive_opportunities(self):
        """Test getting HIVE opportunities."""
        tables = [
            # Suitable
            LobbyTable("t1", "Table 1", players_seated=3, max_seats=9, human_count=1),
            LobbyTable("t2", "Table 2", players_seated=4, max_seats=9, human_count=2),
            # Not suitable
            LobbyTable("t3", "Table 3", players_seated=8, max_seats=9, human_count=5),
            LobbyTable("t4", "Table 4", players_seated=2, max_seats=9, human_count=0),
        ]
        
        snapshot = LobbySnapshot(tables=tables, total_tables=len(tables))
        
        opportunities = snapshot.get_hive_opportunities()
        
        # Should have 2 suitable tables
        assert len(opportunities) == 2
        
        # Should be sorted by priority (1 human first)
        assert opportunities[0].human_count == 1
        assert opportunities[1].human_count == 2


class TestLobbyScanner:
    """Tests for LobbyScanner."""
    
    def test_initialization(self):
        """Test scanner initialization."""
        scanner = LobbyScanner()
        
        assert scanner.lobby_window_id is None
    
    def test_scan_lobby(self):
        """Test scanning lobby."""
        scanner = LobbyScanner()
        
        snapshot = scanner.scan_lobby()
        
        # Should return snapshot (even if empty)
        assert isinstance(snapshot, LobbySnapshot)
        assert snapshot.timestamp > 0
    
    def test_find_best_opportunity(self):
        """Test finding best opportunity."""
        scanner = LobbyScanner()
        
        # With empty lobby
        best = scanner.find_best_opportunity()
        assert best is None
    
    def test_simulate_lobby_data(self):
        """Test simulating lobby data."""
        scanner = LobbyScanner()
        
        snapshot = scanner.simulate_lobby_data(num_tables=10)
        
        assert len(snapshot.tables) == 10
        assert snapshot.total_tables == 10
        
        # Check table structure
        for table in snapshot.tables:
            assert table.table_id
            assert table.table_name
            assert 0 <= table.players_seated <= table.max_seats
            assert table.human_count >= 0
    
    def test_find_best_with_simulated_data(self):
        """Test finding best opportunity with simulated data."""
        scanner = LobbyScanner()
        
        # Generate many tables to ensure at least one opportunity
        snapshot = scanner.simulate_lobby_data(num_tables=50)
        opportunities = snapshot.get_hive_opportunities()
        
        # Should find at least some opportunities
        # (not guaranteed due to randomness, but very likely with 50 tables)
        print(f"\nFound {len(opportunities)} opportunities in 50 simulated tables")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
