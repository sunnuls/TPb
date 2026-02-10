"""
Tests for LobbyScanner (Roadmap3 Phase 3.1).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import time

from bridge.lobby_scanner import (
    LobbyScanner,
    LobbyTable,
    LobbySnapshot,
    TableType
)


class TestLobbyTable:
    """Test LobbyTable dataclass."""
    
    def test_lobby_table_creation(self):
        """Test basic lobby table creation."""
        table = LobbyTable(
            table_id="table_001",
            table_name="Table 1",
            table_type=TableType.CASH,
            max_seats=6,
            occupied_seats=3,
            stakes="1/2"
        )
        
        assert table.table_id == "table_001"
        assert table.table_name == "Table 1"
        assert table.table_type == TableType.CASH
        assert table.max_seats == 6
        assert table.occupied_seats == 3
        assert table.seats_left == 3  # Auto-calculated
        assert table.stakes == "1/2"
    
    def test_lobby_table_seats_calculation(self):
        """Test seats_left calculation."""
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=4
        )
        
        # Should auto-calculate seats_left
        assert table.seats_left == 2
    
    def test_lobby_table_full(self):
        """Test full table."""
        table = LobbyTable(
            table_id="table_001",
            max_seats=6,
            occupied_seats=6
        )
        
        assert table.seats_left == 0


class TestLobbySnapshot:
    """Test LobbySnapshot dataclass."""
    
    def test_lobby_snapshot_creation(self):
        """Test basic snapshot creation."""
        tables = [
            LobbyTable(table_id="t1", max_seats=6, occupied_seats=3),
            LobbyTable(table_id="t2", max_seats=6, occupied_seats=5)
        ]
        
        snapshot = LobbySnapshot(
            timestamp=time.time(),
            tables=tables
        )
        
        assert len(snapshot.tables) == 2
        assert snapshot.total_tables == 2  # Auto-calculated
        assert snapshot.total_players == 8  # 3 + 5
    
    def test_lobby_snapshot_empty(self):
        """Test empty snapshot."""
        snapshot = LobbySnapshot(timestamp=time.time())
        
        assert len(snapshot.tables) == 0
        assert snapshot.total_tables == 0
        assert snapshot.total_players == 0


class TestLobbyScanner:
    """Test LobbyScanner core functionality."""
    
    def test_init_dry_run(self):
        """Test initialization in dry-run mode."""
        scanner = LobbyScanner(dry_run=True)
        
        assert scanner.dry_run is True
        assert scanner.scans_count == 0
        assert scanner.last_snapshot is None
    
    def test_scan_lobby_dry_run(self):
        """Test lobby scan in dry-run mode."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot = scanner.scan_lobby()
        
        assert snapshot is not None
        assert len(snapshot.tables) > 0
        assert snapshot.extraction_method == "simulated"
        assert snapshot.confidence == 1.0
        assert scanner.scans_count == 1
    
    def test_scan_lobby_returns_tables(self):
        """Test scan returns valid tables."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot = scanner.scan_lobby()
        
        # Validate table structure
        for table in snapshot.tables:
            assert table.table_id is not None
            assert table.max_seats > 0
            assert table.occupied_seats >= 0
            assert table.occupied_seats <= table.max_seats
            assert table.seats_left >= 0
    
    def test_scan_lobby_with_filters(self):
        """Test lobby scan with filters."""
        scanner = LobbyScanner(dry_run=True)
        
        # Filter for tables with 3+ seats
        snapshot = scanner.scan_lobby(min_seats_left=3)
        
        assert snapshot is not None
        # All returned tables should have 3+ seats
        for table in snapshot.tables:
            assert table.seats_left >= 3
    
    def test_scan_lobby_table_type_filter(self):
        """Test table type filtering."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot = scanner.scan_lobby(table_type_filter=TableType.CASH)
        
        assert snapshot is not None
        # All returned tables should be CASH type
        for table in snapshot.tables:
            assert table.table_type == TableType.CASH
    
    def test_scan_lobby_max_seats_filter(self):
        """Test max seats filtering."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot = scanner.scan_lobby(max_seats_filter=6)
        
        assert snapshot is not None
        # All returned tables should be 6-max
        for table in snapshot.tables:
            assert table.max_seats == 6
    
    def test_find_tables_with_seats(self):
        """Test finding tables with specific seats."""
        scanner = LobbyScanner(dry_run=True)
        
        tables = scanner.find_tables_with_seats(required_seats=3)
        
        assert len(tables) > 0
        # All tables should have 3+ seats
        for table in tables:
            assert table.seats_left >= 3
    
    def test_multiple_scans(self):
        """Test multiple scans increment counter."""
        scanner = LobbyScanner(dry_run=True)
        
        scanner.scan_lobby()
        scanner.scan_lobby()
        scanner.scan_lobby()
        
        assert scanner.scans_count == 3
    
    def test_last_snapshot_updated(self):
        """Test last_snapshot is updated."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot1 = scanner.scan_lobby()
        assert scanner.last_snapshot == snapshot1
        
        snapshot2 = scanner.scan_lobby()
        assert scanner.last_snapshot == snapshot2
    
    def test_get_statistics(self):
        """Test statistics collection."""
        scanner = LobbyScanner(dry_run=True)
        
        scanner.scan_lobby()
        scanner.scan_lobby()
        
        stats = scanner.get_statistics()
        
        assert stats['total_scans'] == 2
        assert stats['last_scan_time'] >= 0  # Can be very small in dry-run
        assert stats['dry_run'] is True
        assert stats['last_snapshot'] is not None
        assert stats['last_snapshot']['tables'] > 0


class TestLobbyIntegration:
    """Integration tests for lobby scanner."""
    
    def test_full_lobby_scan_workflow(self):
        """Test complete lobby scan workflow."""
        scanner = LobbyScanner(dry_run=True)
        
        # Scan lobby
        snapshot = scanner.scan_lobby()
        
        assert snapshot is not None
        assert len(snapshot.tables) > 0
        
        # Check tables have varied occupancy
        occupancies = [t.occupied_seats for t in snapshot.tables]
        assert len(set(occupancies)) > 1  # Should have variety
        
        # Find HIVE opportunities
        hive_tables = scanner.find_tables_with_seats(required_seats=3)
        assert len(hive_tables) > 0
        
        # Verify all HIVE tables have 3+ seats
        for table in hive_tables:
            assert table.seats_left >= 3
    
    def test_scan_timing(self):
        """Test scan timing is reasonable."""
        scanner = LobbyScanner(dry_run=True)
        
        snapshot = scanner.scan_lobby()
        
        assert snapshot is not None
        assert scanner.last_scan_time >= 0
        # In dry-run, scan should be very fast
        assert scanner.last_scan_time < 0.5  # Less than 500ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
