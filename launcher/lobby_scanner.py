"""
Lobby Scanner - Launcher Application (Roadmap6 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Scan poker lobby for tables
- OCR/ROI based table detection
- Filter by human count and seats
- Prioritize opportunities
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import time

logger = logging.getLogger(__name__)


@dataclass
class LobbyTable:
    """
    Lobby table information.
    
    Attributes:
        table_id: Unique table identifier
        table_name: Table name
        game_type: Game type (NLHE, PLO, etc.)
        stakes: Stakes (e.g., "0.25/0.50")
        players_seated: Number of players currently seated
        max_seats: Maximum seats at table
        human_count: Estimated human player count
        avg_pot: Average pot size
        hands_per_hour: Hands per hour
        waiting: Number of players waiting
    """
    table_id: str
    table_name: str
    game_type: str = "NLHE"
    stakes: str = "0.25/0.50"
    players_seated: int = 0
    max_seats: int = 9
    human_count: int = 0
    avg_pot: float = 0.0
    hands_per_hour: int = 0
    waiting: int = 0
    
    def seats_available(self) -> int:
        """Get available seats."""
        return self.max_seats - self.players_seated
    
    def is_suitable_for_hive(self) -> bool:
        """
        Check if table is suitable for HIVE deployment.
        
        Requirements:
        - 1-3 human players
        - 3+ seats available
        
        Returns:
            True if suitable
        """
        return (
            1 <= self.human_count <= 3 and
            self.seats_available() >= 3
        )
    
    def priority_score(self) -> float:
        """
        Calculate priority score for HIVE deployment.
        
        Higher score = better opportunity.
        
        Factors:
        - Fewer humans = higher priority
        - More open seats = higher priority
        - Higher stakes = higher priority
        
        Returns:
            Priority score (0-100)
        """
        if not self.is_suitable_for_hive():
            return 0.0
        
        # Base score
        score = 50.0
        
        # Fewer humans bonus (1 human is best)
        if self.human_count == 1:
            score += 30.0
        elif self.human_count == 2:
            score += 20.0
        elif self.human_count == 3:
            score += 10.0
        
        # More open seats bonus
        open_seats = self.seats_available()
        score += min(open_seats * 2.0, 20.0)
        
        return min(score, 100.0)


@dataclass
class LobbySnapshot:
    """
    Snapshot of lobby state.
    
    Attributes:
        timestamp: Snapshot timestamp
        tables: List of tables in lobby
        total_tables: Total number of tables
    """
    timestamp: float = field(default_factory=time.time)
    tables: List[LobbyTable] = field(default_factory=list)
    total_tables: int = 0
    
    def get_hive_opportunities(self) -> List[LobbyTable]:
        """
        Get tables suitable for HIVE deployment.
        
        Returns:
            List of suitable tables, sorted by priority
        """
        suitable = [t for t in self.tables if t.is_suitable_for_hive()]
        return sorted(suitable, key=lambda t: t.priority_score(), reverse=True)


class LobbyScanner:
    """
    Lobby scanner for finding table opportunities.
    
    Features:
    - Capture lobby window
    - OCR table information
    - Filter by criteria
    - Prioritize opportunities
    
    ⚠️ EDUCATIONAL NOTE:
        Scans lobby to find targets for coordinated bot deployment.
    """
    
    def __init__(self, lobby_window_id: Optional[str] = None):
        """
        Initialize lobby scanner.
        
        Args:
            lobby_window_id: Lobby window handle (for capture)
        """
        self.lobby_window_id = lobby_window_id
        
        logger.info("Lobby scanner initialized")
        logger.warning(
            "CRITICAL: Lobby scanner for COORDINATED COLLUSION. "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def scan_lobby(self) -> LobbySnapshot:
        """
        Scan lobby and return snapshot.
        
        This is a placeholder that would integrate with:
        - bridge/lobby_scanner.py for actual lobby capture
        - OCR for table information extraction
        - Vision-based table detection
        
        Returns:
            Lobby snapshot with table information
        """
        logger.info("Scanning lobby...")
        
        # PLACEHOLDER: In real implementation, this would:
        # 1. Capture lobby window screenshot
        # 2. Apply ROI for table list area
        # 3. OCR each table row
        # 4. Parse table information
        # 5. Estimate human count (heuristics)
        
        # For Phase 3, return empty snapshot
        snapshot = LobbySnapshot(tables=[], total_tables=0)
        
        logger.debug(f"Lobby scan complete: {snapshot.total_tables} tables found")
        
        return snapshot
    
    def find_best_opportunity(
        self,
        min_humans: int = 1,
        max_humans: int = 3,
        min_seats: int = 3
    ) -> Optional[LobbyTable]:
        """
        Find best table opportunity.
        
        Args:
            min_humans: Minimum human count
            max_humans: Maximum human count
            min_seats: Minimum available seats
        
        Returns:
            Best table if found
        """
        snapshot = self.scan_lobby()
        opportunities = snapshot.get_hive_opportunities()
        
        # Filter by criteria
        filtered = [
            t for t in opportunities
            if min_humans <= t.human_count <= max_humans
            and t.seats_available() >= min_seats
        ]
        
        if not filtered:
            logger.debug("No suitable opportunities found")
            return None
        
        best = filtered[0]
        logger.info(
            f"Best opportunity: {best.table_name} "
            f"({best.human_count} humans, {best.seats_available()} seats)"
        )
        
        return best
    
    def simulate_lobby_data(self, num_tables: int = 10) -> LobbySnapshot:
        """
        Simulate lobby data for testing.
        
        Args:
            num_tables: Number of tables to generate
        
        Returns:
            Simulated lobby snapshot
        """
        import random
        
        tables = []
        
        for i in range(num_tables):
            max_seats = random.choice([6, 9])
            players_seated = random.randint(2, max_seats)
            
            table = LobbyTable(
                table_id=f"table_{i+1:03d}",
                table_name=f"Table {i+1}",
                game_type=random.choice(["NLHE", "PLO"]),
                stakes=random.choice(["0.25/0.50", "0.50/1.00", "1.00/2.00"]),
                players_seated=players_seated,
                max_seats=max_seats,
                human_count=random.randint(0, min(6, players_seated)),
                avg_pot=random.uniform(5.0, 50.0),
                hands_per_hour=random.randint(50, 100)
            )
            tables.append(table)
        
        snapshot = LobbySnapshot(
            tables=tables,
            total_tables=num_tables
        )
        
        logger.info(f"Simulated {num_tables} tables")
        
        return snapshot


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Lobby Scanner - Educational Research")
    print("=" * 60)
    print()
    
    # Create scanner
    scanner = LobbyScanner()
    
    print("Lobby scanner created")
    print()
    
    # Simulate lobby data
    print("Simulating lobby data (10 tables)...")
    snapshot = scanner.simulate_lobby_data(10)
    
    print(f"Total tables: {snapshot.total_tables}")
    print()
    
    # Find opportunities
    opportunities = snapshot.get_hive_opportunities()
    
    print(f"HIVE opportunities: {len(opportunities)}")
    if opportunities:
        print("\nTop 3 opportunities:")
        for i, table in enumerate(opportunities[:3], 1):
            print(f"  {i}. {table.table_name}")
            print(f"     Humans: {table.human_count}, Seats: {table.seats_available()}")
            print(f"     Priority: {table.priority_score():.1f}")
            print(f"     Stakes: {table.stakes}")
    
    print()
    
    # Find best opportunity
    print("Finding best opportunity...")
    best = scanner.find_best_opportunity()
    
    if best:
        print(f"Best table: {best.table_name}")
        print(f"  Humans: {best.human_count}")
        print(f"  Available seats: {best.seats_available()}")
        print(f"  Priority score: {best.priority_score():.1f}")
    else:
        print("  No suitable opportunities found")
    
    print()
    print("=" * 60)
    print("Lobby scanner demonstration complete")
    print("=" * 60)
