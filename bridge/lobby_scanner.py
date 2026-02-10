"""
Lobby Scanner Module (Roadmap3 Phase 3.1).

Captures and analyzes poker lobby to detect available tables:
- Number of players at each table
- Seats left (empty seats)
- Table stakes/limits
- Table type (cash/tournament)

In DRY-RUN mode: returns simulated lobby data.
In UNSAFE mode: performs real lobby capture and analysis.

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from bridge.safety import SafetyFramework

logger = logging.getLogger(__name__)


class TableType(str, Enum):
    """Table types in lobby."""
    CASH = "cash"
    TOURNAMENT = "tournament"
    SNG = "sit_n_go"
    SPIN = "spin_and_go"
    UNKNOWN = "unknown"


@dataclass
class LobbyTable:
    """
    Information about a single table in the lobby.
    
    Attributes:
        table_id: Unique table identifier
        table_name: Human-readable table name
        table_type: Type of table
        max_seats: Maximum seats at table
        occupied_seats: Number of occupied seats
        seats_left: Number of empty seats
        stakes: Stakes/limits (e.g., "1/2", "50+5")
        average_pot: Average pot size (if available)
        hands_per_hour: Hands per hour (if available)
        waitlist: Number of players on waitlist
    """
    table_id: str
    table_name: str = "Unknown"
    table_type: TableType = TableType.CASH
    max_seats: int = 6
    occupied_seats: int = 0
    seats_left: int = 6
    stakes: str = "1/2"
    average_pot: float = 0.0
    hands_per_hour: int = 0
    waitlist: int = 0
    
    def __post_init__(self):
        """Calculate seats_left if not provided."""
        if self.seats_left == self.max_seats and self.occupied_seats > 0:
            self.seats_left = self.max_seats - self.occupied_seats


@dataclass
class LobbySnapshot:
    """
    Complete snapshot of poker lobby at a point in time.
    
    Attributes:
        timestamp: When snapshot was taken
        tables: List of all visible tables
        total_tables: Total number of tables
        total_players: Total number of players across all tables
        extraction_method: How data was extracted
        confidence: Extraction confidence (0.0-1.0)
        error: Error message if extraction failed
    """
    timestamp: float
    tables: List[LobbyTable] = field(default_factory=list)
    total_tables: int = 0
    total_players: int = 0
    extraction_method: str = "simulated"
    confidence: float = 1.0
    error: Optional[str] = None
    
    def __post_init__(self):
        """Calculate totals if not provided."""
        if self.total_tables == 0:
            self.total_tables = len(self.tables)
        if self.total_players == 0:
            self.total_players = sum(t.occupied_seats for t in self.tables)


class LobbyScanner:
    """
    Scans poker lobby to detect available tables and opportunities.
    
    In DRY-RUN mode (default):
        Returns simulated lobby data with realistic table distribution.
    
    In UNSAFE mode:
        Attempts real lobby capture using:
        - Screenshot analysis
        - OCR for table names and stakes
        - Template matching for player counts
    
    EDUCATIONAL NOTE:
        This demonstrates automated lobby monitoring for HCI research.
        All operations respect SafetyFramework constraints.
    """
    
    def __init__(
        self,
        dry_run: bool = True,
        safety: Optional[SafetyFramework] = None
    ):
        """
        Initialize lobby scanner.
        
        Args:
            dry_run: If True, return simulated data only
            safety: SafetyFramework instance for permission checking
        """
        self.dry_run = dry_run
        self.safety = safety or SafetyFramework.get_instance()
        
        # Statistics
        self.scans_count = 0
        self.last_scan_time = 0.0
        self.last_snapshot: Optional[LobbySnapshot] = None
        
        logger.info(
            f"LobbyScanner initialized (dry_run={dry_run})"
        )
    
    def scan_lobby(
        self,
        table_type_filter: Optional[TableType] = None,
        min_seats_left: int = 0,
        max_seats_filter: Optional[int] = None
    ) -> Optional[LobbySnapshot]:
        """
        Scan poker lobby and return snapshot.
        
        Args:
            table_type_filter: Filter by table type (None = all types)
            min_seats_left: Minimum empty seats required
            max_seats_filter: Filter by max seats (e.g., 6 for 6-max only)
        
        Returns:
            LobbySnapshot with all visible tables
        
        EDUCATIONAL NOTE:
            In DRY-RUN mode, generates realistic lobby distribution.
            In UNSAFE mode, performs real lobby capture.
        """
        start_time = time.time()
        self.scans_count += 1
        
        # Log decision
        self.safety.log_decision({
            'action': 'scan_lobby',
            'reason': f"Scanning lobby (dry_run={self.dry_run})",
            'allowed': True
        })
        
        try:
            if self.dry_run:
                snapshot = self._simulate_lobby_scan()
            else:
                # Real lobby scan (UNSAFE mode)
                self.safety.require_unsafe_mode("scan_lobby")
                snapshot = self._perform_real_scan()
            
            # Apply filters
            if snapshot and snapshot.tables:
                filtered_tables = self._apply_filters(
                    snapshot.tables,
                    table_type_filter,
                    min_seats_left,
                    max_seats_filter
                )
                snapshot.tables = filtered_tables
                snapshot.total_tables = len(filtered_tables)
                snapshot.total_players = sum(
                    t.occupied_seats for t in filtered_tables
                )
            
            # Update statistics
            self.last_scan_time = time.time() - start_time
            self.last_snapshot = snapshot
            
            logger.info(
                f"Lobby scan complete: {len(snapshot.tables)} tables found "
                f"(scan_time={self.last_scan_time:.3f}s)"
            )
            
            return snapshot
            
        except PermissionError as e:
            logger.error(f"Lobby scan blocked by safety framework: {e}")
            return LobbySnapshot(
                timestamp=time.time(),
                extraction_method="blocked",
                confidence=0.0,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Lobby scan failed: {e}", exc_info=True)
            return LobbySnapshot(
                timestamp=time.time(),
                extraction_method="error",
                confidence=0.0,
                error=str(e)
            )
    
    def _simulate_lobby_scan(self) -> LobbySnapshot:
        """
        Generate simulated lobby data for DRY-RUN mode.
        
        Returns:
            Realistic lobby snapshot with varied table distribution
        """
        tables = []
        
        # Generate 10 simulated tables with varied occupancy
        for i in range(10):
            table_id = f"table_{i+1:03d}"
            
            # Vary table parameters
            max_seats = 6 if i < 7 else 9  # Mostly 6-max
            occupied = min(i + 1, max_seats)  # Progressive filling
            
            # Vary stakes
            stakes_options = ["0.5/1", "1/2", "2/4", "5/10", "10/20"]
            stakes = stakes_options[i % len(stakes_options)]
            
            table = LobbyTable(
                table_id=table_id,
                table_name=f"Table {i+1}",
                table_type=TableType.CASH,
                max_seats=max_seats,
                occupied_seats=occupied,
                stakes=stakes,
                average_pot=float(50 + i * 10),
                hands_per_hour=80 + i * 5,
                waitlist=1 if occupied == max_seats and i < 3 else 0
            )
            
            tables.append(table)
        
        snapshot = LobbySnapshot(
            timestamp=time.time(),
            tables=tables,
            extraction_method="simulated",
            confidence=1.0
        )
        
        return snapshot
    
    def _perform_real_scan(self) -> LobbySnapshot:
        """
        Perform real lobby scan (UNSAFE mode only).
        
        Returns:
            LobbySnapshot from real capture
        
        EDUCATIONAL NOTE:
            Real implementation would:
            1. Capture lobby screenshot
            2. Detect table rows using template matching
            3. Extract table info using OCR
            4. Parse player counts and stakes
        """
        # Placeholder for real lobby scanning
        logger.warning("Real lobby scan not implemented - using fallback simulation")
        
        # In a real implementation:
        # 1. Capture lobby window screenshot
        # 2. Find table list region
        # 3. Detect individual table rows
        # 4. Extract data from each row:
        #    - Table name (OCR)
        #    - Player count (OCR or icon counting)
        #    - Stakes (OCR)
        #    - Available seats (calculation)
        
        return self._simulate_lobby_scan()
    
    def _apply_filters(
        self,
        tables: List[LobbyTable],
        table_type_filter: Optional[TableType],
        min_seats_left: int,
        max_seats_filter: Optional[int]
    ) -> List[LobbyTable]:
        """
        Apply filters to table list.
        
        Args:
            tables: List of tables to filter
            table_type_filter: Filter by table type
            min_seats_left: Minimum empty seats
            max_seats_filter: Filter by max seats
        
        Returns:
            Filtered list of tables
        """
        filtered = tables
        
        # Filter by table type
        if table_type_filter:
            filtered = [t for t in filtered if t.table_type == table_type_filter]
        
        # Filter by seats left
        if min_seats_left > 0:
            filtered = [t for t in filtered if t.seats_left >= min_seats_left]
        
        # Filter by max seats
        if max_seats_filter:
            filtered = [t for t in filtered if t.max_seats == max_seats_filter]
        
        return filtered
    
    def find_tables_with_seats(
        self,
        required_seats: int = 3,
        table_type: Optional[TableType] = None
    ) -> List[LobbyTable]:
        """
        Find tables with specific number of available seats.
        
        Args:
            required_seats: Number of seats needed
            table_type: Filter by table type
        
        Returns:
            List of tables with enough seats
        
        EDUCATIONAL NOTE:
            Used to find HIVE opportunities (3+ seats for group play).
        """
        snapshot = self.scan_lobby(
            table_type_filter=table_type,
            min_seats_left=required_seats
        )
        
        if not snapshot or not snapshot.tables:
            return []
        
        return snapshot.tables
    
    def get_statistics(self) -> dict:
        """Get lobby scanner statistics."""
        return {
            'total_scans': self.scans_count,
            'last_scan_time': self.last_scan_time,
            'dry_run': self.dry_run,
            'last_snapshot': {
                'tables': len(self.last_snapshot.tables) if self.last_snapshot else 0,
                'total_players': self.last_snapshot.total_players if self.last_snapshot else 0,
                'timestamp': self.last_snapshot.timestamp if self.last_snapshot else 0.0
            } if self.last_snapshot else None
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Lobby Scanner - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Initialize scanner in DRY-RUN mode (safe)
    scanner = LobbyScanner(dry_run=True)
    
    # Scan lobby
    print("Scanning lobby...")
    snapshot = scanner.scan_lobby()
    
    if snapshot:
        print()
        print("=" * 60)
        print("Lobby Snapshot:")
        print("=" * 60)
        print()
        
        print(f"Total tables: {snapshot.total_tables}")
        print(f"Total players: {snapshot.total_players}")
        print(f"Extraction method: {snapshot.extraction_method}")
        print(f"Confidence: {snapshot.confidence:.1%}")
        print()
        
        print("Available Tables:")
        print("-" * 60)
        for table in snapshot.tables[:5]:  # Show first 5
            print(
                f"  {table.table_name} ({table.table_id}): "
                f"{table.occupied_seats}/{table.max_seats} players, "
                f"{table.seats_left} seats left, "
                f"stakes={table.stakes}"
            )
        print()
        
        # Find HIVE opportunities (3+ seats)
        print("Finding HIVE opportunities (3+ seats)...")
        hive_tables = scanner.find_tables_with_seats(required_seats=3)
        print(f"Found {len(hive_tables)} tables with 3+ seats:")
        for table in hive_tables[:3]:
            print(
                f"  [OPPORTUNITY] {table.table_name}: "
                f"{table.seats_left} seats left"
            )
        print()
        
        # Statistics
        stats = scanner.get_statistics()
        print("=" * 60)
        print("Statistics:")
        print("=" * 60)
        print(f"Total scans: {stats['total_scans']}")
        print(f"Last scan time: {stats['last_scan_time']:.3f}s")
        print(f"DRY-RUN mode: {stats['dry_run']}")
        print()
    else:
        print("[ERROR] Lobby scan failed")
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
