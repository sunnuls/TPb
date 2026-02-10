"""
Table Scanner - Educational Game Theory Research.

⚠️ ETHICAL WARNING:
    This implements automated table selection for RESEARCH ONLY.
    Demonstrates opportunity detection in multi-agent systems.
    NEVER use without explicit participant consent.

Scans lobby for suitable tables:
- Human player count
- Available seats
- Table dynamics (stakes, speed)
- Prioritization for HIVE team deployment
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from bridge.lobby_scanner import LobbyScanner
from bridge.opportunity_detector import OpportunityDetector

logger = logging.getLogger(__name__)


class TablePriority(str, Enum):
    """Table priority for HIVE deployment."""
    CRITICAL = "critical"    # 1 human, 3+ seats
    HIGH = "high"            # 2 humans, 3+ seats
    MEDIUM = "medium"        # 3 humans, 3 seats
    LOW = "low"              # Not suitable
    BLOCKED = "blocked"      # Already has HIVE team


@dataclass
class HiveOpportunity:
    """
    HIVE-specific table opportunity.
    
    Attributes:
        table_id: Table identifier
        human_count: Number of human players
        seats_available: Available seats
        priority: Deployment priority
        score: Opportunity score (higher = better)
        detected_at: Detection timestamp
        metadata: Additional table info
    
    EDUCATIONAL NOTE:
        Represents opportunity for coordinated agent deployment.
    """
    table_id: str
    human_count: int
    seats_available: int
    priority: TablePriority
    score: float
    detected_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    
    def is_suitable_for_hive(self) -> bool:
        """
        Check if table is suitable for HIVE deployment.
        
        Returns:
            True if suitable (1-3 humans, ≥3 seats)
        """
        return (
            1 <= self.human_count <= 3 and
            self.seats_available >= 3 and
            self.priority != TablePriority.BLOCKED
        )
    
    def get_age(self) -> float:
        """
        Get opportunity age.
        
        Returns:
            Age in seconds
        """
        return time.time() - self.detected_at


class TableScanner:
    """
    Table scanner for HIVE deployment.
    
    Extends lobby scanning for coordinated agent placement.
    
    Features:
    - Automated lobby scanning
    - Opportunity prioritization
    - Human player detection
    - HIVE suitability assessment
    
    ⚠️ EDUCATIONAL USE ONLY:
        Demonstrates automated opportunity detection for research.
        NOT for use in real games.
    """
    
    def __init__(
        self,
        room: str = "pokerstars",
        scan_interval: float = 5.0,
        dry_run: bool = True
    ):
        """
        Initialize table scanner.
        
        Args:
            room: Poker room identifier
            scan_interval: Scan interval in seconds
            dry_run: If True, simulation mode
        """
        self.room = room
        self.scan_interval = scan_interval
        self.dry_run = dry_run
        
        # Components
        self.lobby_scanner = LobbyScanner(dry_run=dry_run)
        self.opportunity_detector = OpportunityDetector()
        
        # Opportunities
        self.opportunities: Dict[str, HiveOpportunity] = {}
        
        # Statistics
        self.scans_performed = 0
        self.opportunities_found = 0
        self.last_scan_time: Optional[float] = None
        
        logger.info(
            f"TableScanner initialized for {room} "
            f"(interval: {scan_interval}s, dry_run: {dry_run})"
        )
    
    def scan_lobby(self) -> List[HiveOpportunity]:
        """
        Scan lobby for HIVE opportunities.
        
        Returns:
            List of suitable opportunities
        
        EDUCATIONAL NOTE:
            Simulates lobby scanning for research purposes.
        """
        self.scans_performed += 1
        self.last_scan_time = time.time()
        
        # Scan lobby (dry-run returns simulated data)
        snapshot = self.lobby_scanner.scan_lobby()
        
        if not snapshot or not snapshot.tables:
            logger.debug("No tables found in lobby")
            return []
        
        # Convert to HiveOpportunities
        opportunities = []
        
        for table in snapshot.tables:
            # Calculate human count (in dry-run, simulate)
            human_count = self._estimate_human_count(table)
            
            # Calculate available seats
            seats_available = table.seats_left
            
            # Prioritize
            priority = self._calculate_priority(human_count, seats_available)
            
            # Score
            score = self._calculate_score(human_count, seats_available, table)
            
            opportunity = HiveOpportunity(
                table_id=table.table_id,
                human_count=human_count,
                seats_available=seats_available,
                priority=priority,
                score=score,
                metadata=table
            )
            
            # Store if suitable
            if opportunity.is_suitable_for_hive():
                self.opportunities[opportunity.table_id] = opportunity
                opportunities.append(opportunity)
                self.opportunities_found += 1
        
        logger.info(
            f"Scan #{self.scans_performed}: "
            f"{len(opportunities)} HIVE opportunities found"
        )
        
        return opportunities
    
    def _estimate_human_count(self, table) -> int:
        """
        Estimate human player count.
        
        Args:
            table: LobbyTable object
        
        Returns:
            Estimated human count
        
        EDUCATIONAL NOTE:
            In production, would use bot detection heuristics.
            In dry-run, simulates realistic distribution.
        """
        if self.dry_run:
            # Simulate: mostly 1-3 humans per table
            import random
            return random.choices(
                [0, 1, 2, 3, 4, 5, 6],
                weights=[5, 30, 25, 20, 10, 5, 5]
            )[0]
        
        # Real implementation would analyze:
        # - Player names patterns
        # - Action timing patterns
        # - Betting patterns
        # - VPIP/PFR statistics
        
        # For now, assume all are human
        return table.occupied_seats
    
    def _calculate_priority(
        self,
        human_count: int,
        seats_available: int
    ) -> TablePriority:
        """
        Calculate deployment priority.
        
        Args:
            human_count: Number of humans
            seats_available: Available seats
        
        Returns:
            TablePriority
        """
        # Blocked if already has team (would check in real system)
        # For now, just prioritize by humans
        
        if seats_available < 3:
            return TablePriority.LOW
        
        if human_count == 1 and seats_available >= 3:
            return TablePriority.CRITICAL
        
        if human_count == 2 and seats_available >= 3:
            return TablePriority.HIGH
        
        if human_count == 3 and seats_available >= 3:
            return TablePriority.MEDIUM
        
        return TablePriority.LOW
    
    def _calculate_score(
        self,
        human_count: int,
        seats_available: int,
        table
    ) -> float:
        """
        Calculate opportunity score.
        
        Args:
            human_count: Number of humans
            seats_available: Available seats
            table: LobbyTable object
        
        Returns:
            Score (0-100, higher is better)
        """
        score = 0.0
        
        # Prefer fewer humans (easier 3vs1)
        if human_count == 1:
            score += 50.0
        elif human_count == 2:
            score += 35.0
        elif human_count == 3:
            score += 20.0
        else:
            score += 5.0
        
        # Prefer more available seats
        score += min(seats_available * 5, 25.0)
        
        # Prefer higher stakes (in research context, for realistic simulation)
        stakes = None
        if hasattr(table, 'stakes'):
            stakes = table.stakes
        elif isinstance(table, dict):
            stakes = table.get('stakes', '')
        
        if stakes and ('100' in str(stakes) or '200' in str(stakes)):
            score += 15.0
        elif stakes and '50' in str(stakes):
            score += 10.0
        
        # Prefer active tables (recent hands)
        hands_per_hour = 0
        if hasattr(table, 'hands_per_hour'):
            hands_per_hour = table.hands_per_hour
        elif isinstance(table, dict):
            hands_per_hour = table.get('hands_per_hour', 0)
        
        if hands_per_hour > 50:
            score += 10.0
        
        return min(score, 100.0)
    
    def get_best_opportunities(
        self,
        count: int = 5,
        max_age: float = 60.0
    ) -> List[HiveOpportunity]:
        """
        Get best opportunities for HIVE deployment.
        
        Args:
            count: Maximum number to return
            max_age: Maximum age in seconds
        
        Returns:
            List of opportunities, sorted by score
        """
        # Filter by age and suitability
        valid = [
            opp for opp in self.opportunities.values()
            if opp.get_age() < max_age and opp.is_suitable_for_hive()
        ]
        
        # Sort by score
        sorted_opps = sorted(valid, key=lambda x: x.score, reverse=True)
        
        return sorted_opps[:count]
    
    def mark_table_occupied(self, table_id: str) -> None:
        """
        Mark table as occupied by HIVE team.
        
        Args:
            table_id: Table identifier
        """
        if table_id in self.opportunities:
            self.opportunities[table_id].priority = TablePriority.BLOCKED
            logger.info(f"Table {table_id} marked as occupied")
    
    def remove_opportunity(self, table_id: str) -> bool:
        """
        Remove opportunity from tracking.
        
        Args:
            table_id: Table identifier
        
        Returns:
            True if removed
        """
        if table_id in self.opportunities:
            del self.opportunities[table_id]
            logger.debug(f"Opportunity {table_id} removed")
            return True
        
        return False
    
    def clear_stale_opportunities(self, max_age: float = 120.0) -> int:
        """
        Remove stale opportunities.
        
        Args:
            max_age: Maximum age in seconds
        
        Returns:
            Number of opportunities removed
        """
        stale_ids = [
            table_id for table_id, opp in self.opportunities.items()
            if opp.get_age() > max_age
        ]
        
        for table_id in stale_ids:
            del self.opportunities[table_id]
        
        if stale_ids:
            logger.info(f"Cleared {len(stale_ids)} stale opportunities")
        
        return len(stale_ids)
    
    def get_statistics(self) -> dict:
        """
        Get scanner statistics.
        
        Returns:
            Statistics dictionary
        """
        priority_counts = {}
        for priority in TablePriority:
            priority_counts[priority.value] = sum(
                1 for opp in self.opportunities.values()
                if opp.priority == priority
            )
        
        suitable_count = sum(
            1 for opp in self.opportunities.values()
            if opp.is_suitable_for_hive()
        )
        
        return {
            'scans_performed': self.scans_performed,
            'opportunities_found': self.opportunities_found,
            'current_opportunities': len(self.opportunities),
            'suitable_opportunities': suitable_count,
            'priority_distribution': priority_counts,
            'last_scan_time': self.last_scan_time,
            'room': self.room,
            'dry_run': self.dry_run
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Table Scanner - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates automated table selection for RESEARCH ONLY.")
    print("NEVER use in real games without explicit consent.")
    print()
    
    # Create scanner
    scanner = TableScanner(
        room="pokerstars",
        scan_interval=5.0,
        dry_run=True
    )
    
    print("Scanner initialized:")
    print(f"  Room: {scanner.room}")
    print(f"  Scan interval: {scanner.scan_interval}s")
    print(f"  Dry-run: {scanner.dry_run}")
    print()
    
    # Scan lobby
    print("Scanning lobby...")
    opportunities = scanner.scan_lobby()
    
    print(f"\nFound {len(opportunities)} opportunities:")
    for opp in opportunities[:5]:
        print(f"  {opp.table_id}: {opp.human_count} humans, "
              f"{opp.seats_available} seats, "
              f"priority={opp.priority.value}, "
              f"score={opp.score:.1f}")
    print()
    
    # Get best
    best = scanner.get_best_opportunities(count=3)
    print(f"Top 3 opportunities:")
    for opp in best:
        print(f"  {opp.table_id}: score={opp.score:.1f}")
    print()
    
    # Statistics
    stats = scanner.get_statistics()
    print("Scanner statistics:")
    for key, value in stats.items():
        if key != 'priority_distribution':
            print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
