"""
Opportunity Detector Module (Roadmap3 Phase 3.2).

Adapts HIVE table selection logic from sim_engine/table_selection.py
for real lobby data. Detects optimal tables for 3-agent coordination.

Core logic from sim_engine/table_selection.py:
- Priority scoring for 3vs1 scenarios
- Seats available validation
- Opponent count assessment

In DRY-RUN mode: logs opportunities without actions.
In UNSAFE mode: can trigger join requests (Phase 4+).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from bridge.lobby_scanner import LobbyScanner, LobbyTable, LobbySnapshot, TableType
from bridge.safety import SafetyFramework

logger = logging.getLogger(__name__)


class OpportunityScore(str, Enum):
    """Opportunity quality scoring."""
    PERFECT = "perfect"      # 3 agents vs 1 opponent (ideal HIVE)
    EXCELLENT = "excellent"  # 3 agents vs 2 opponents
    GOOD = "good"            # 3 agents vs 3 opponents
    MARGINAL = "marginal"    # Non-ideal but playable
    POOR = "poor"            # Not recommended


@dataclass
class HiveOpportunity:
    """
    HIVE opportunity detected in live lobby.
    
    Adapted from sim_engine/table_selection.py HiveOpportunity.
    
    Attributes:
        table: The lobby table with opportunity
        score: Opportunity quality score
        priority: Numeric priority (higher = better)
        required_agents: Number of agents needed
        current_opponents: Current opponent count
        expected_opponents: Expected opponents after join
        reason: Human-readable explanation
    """
    table: LobbyTable
    score: OpportunityScore
    priority: float
    required_agents: int = 3
    current_opponents: int = 0
    expected_opponents: int = 0
    reason: str = ""
    
    def __post_init__(self):
        """Calculate current and expected opponents."""
        if self.current_opponents == 0:
            self.current_opponents = self.table.occupied_seats
        if self.expected_opponents == 0:
            self.expected_opponents = self.current_opponents


@dataclass
class OpportunityReport:
    """
    Report of all detected opportunities in lobby.
    
    Attributes:
        snapshot: Original lobby snapshot
        opportunities: List of detected HIVE opportunities
        perfect_count: Number of perfect opportunities
        excellent_count: Number of excellent opportunities
        good_count: Number of good opportunities
        best_opportunity: Highest priority opportunity
        timestamp: When report was generated
    """
    snapshot: LobbySnapshot
    opportunities: List[HiveOpportunity] = field(default_factory=list)
    perfect_count: int = 0
    excellent_count: int = 0
    good_count: int = 0
    best_opportunity: Optional[HiveOpportunity] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Calculate counts and find best opportunity."""
        self.perfect_count = sum(
            1 for opp in self.opportunities 
            if opp.score == OpportunityScore.PERFECT
        )
        self.excellent_count = sum(
            1 for opp in self.opportunities 
            if opp.score == OpportunityScore.EXCELLENT
        )
        self.good_count = sum(
            1 for opp in self.opportunities 
            if opp.score == OpportunityScore.GOOD
        )
        
        if self.opportunities:
            self.best_opportunity = max(
                self.opportunities, 
                key=lambda opp: opp.priority
            )


class OpportunityDetector:
    """
    Detects HIVE opportunities in live poker lobby.
    
    Core Algorithm (from sim_engine/table_selection.py):
    1. Scan lobby for tables with 3+ seats available
    2. Calculate priority for each table:
       - PERFECT (priority=100): 1 opponent after join (3vs1)
       - EXCELLENT (priority=80): 2 opponents after join (3vs2)
       - GOOD (priority=60): 3 opponents after join (3vs3)
       - MARGINAL (priority=40): 4+ opponents
    3. Filter by minimum priority threshold
    4. Return sorted list of opportunities
    
    EDUCATIONAL NOTE:
        This implements the same HIVE selection logic as simulation,
        but operates on real lobby data from OpportunityDetector.
    """
    
    def __init__(
        self,
        lobby_scanner: Optional[LobbyScanner] = None,
        min_priority: float = 50.0,
        safety: Optional[SafetyFramework] = None
    ):
        """
        Initialize opportunity detector.
        
        Args:
            lobby_scanner: LobbyScanner instance (creates new if None)
            min_priority: Minimum priority threshold for opportunities
            safety: SafetyFramework instance
        """
        self.lobby_scanner = lobby_scanner or LobbyScanner(dry_run=True)
        self.min_priority = min_priority
        self.safety = safety or SafetyFramework.get_instance()
        
        # Statistics
        self.detections_count = 0
        self.last_report: Optional[OpportunityReport] = None
        
        logger.info(
            f"OpportunityDetector initialized (min_priority={min_priority})"
        )
    
    def detect_opportunities(
        self,
        required_agents: int = 3,
        max_seats_filter: int = 6
    ) -> OpportunityReport:
        """
        Scan lobby and detect all HIVE opportunities.
        
        Args:
            required_agents: Number of agents in HIVE (default 3)
            max_seats_filter: Table size filter (6-max recommended)
        
        Returns:
            OpportunityReport with all detected opportunities
        
        EDUCATIONAL NOTE:
            Implements HIVE detection logic from sim_engine/table_selection.py.
            Priority scoring:
            - 3vs1: 100 (perfect)
            - 3vs2: 80 (excellent)
            - 3vs3: 60 (good)
            - 3vs4+: 40 (marginal)
        """
        self.detections_count += 1
        
        # Log decision
        self.safety.log_decision({
            'action': 'detect_opportunities',
            'reason': f"Detecting HIVE opportunities (dry_run={self.lobby_scanner.dry_run})",
            'allowed': True
        })
        
        # Scan lobby
        snapshot = self.lobby_scanner.scan_lobby(
            table_type_filter=TableType.CASH,
            min_seats_left=required_agents,
            max_seats_filter=max_seats_filter
        )
        
        if not snapshot or not snapshot.tables:
            logger.warning("No tables found in lobby scan")
            return OpportunityReport(
                snapshot=snapshot or LobbySnapshot(timestamp=0.0),
                timestamp=snapshot.timestamp if snapshot else 0.0
            )
        
        # Detect opportunities in each table
        opportunities = []
        for table in snapshot.tables:
            opportunity = self._evaluate_table(table, required_agents)
            if opportunity and opportunity.priority >= self.min_priority:
                opportunities.append(opportunity)
        
        # Sort by priority (highest first)
        opportunities.sort(key=lambda opp: opp.priority, reverse=True)
        
        # Create report
        report = OpportunityReport(
            snapshot=snapshot,
            opportunities=opportunities,
            timestamp=snapshot.timestamp
        )
        
        self.last_report = report
        
        logger.info(
            f"Detected {len(opportunities)} HIVE opportunities: "
            f"perfect={report.perfect_count}, excellent={report.excellent_count}, "
            f"good={report.good_count}"
        )
        
        return report
    
    def _evaluate_table(
        self,
        table: LobbyTable,
        required_agents: int
    ) -> Optional[HiveOpportunity]:
        """
        Evaluate a single table for HIVE opportunity.
        
        Args:
            table: LobbyTable to evaluate
            required_agents: Number of agents needed
        
        Returns:
            HiveOpportunity if table is suitable, None otherwise
        
        EDUCATIONAL NOTE:
            Core HIVE logic from sim_engine/table_selection.py:
            - Must have seats for all agents
            - Priority based on expected opponent count
        """
        # Check if table has enough seats
        if table.seats_left < required_agents:
            return None
        
        # Calculate expected state after agents join
        current_opponents = table.occupied_seats
        expected_opponents = current_opponents  # Opponents already present
        
        # Calculate priority and score based on opponent count
        # (from sim_engine/table_selection.py priority scoring)
        if expected_opponents == 1:
            # PERFECT: 3vs1 scenario (ideal HIVE)
            score = OpportunityScore.PERFECT
            priority = 100.0
            reason = "Perfect 3vs1 scenario - single opponent"
            
        elif expected_opponents == 2:
            # EXCELLENT: 3vs2 scenario
            score = OpportunityScore.EXCELLENT
            priority = 80.0
            reason = "Excellent 3vs2 scenario - two opponents"
            
        elif expected_opponents == 3:
            # GOOD: 3vs3 scenario (balanced)
            score = OpportunityScore.GOOD
            priority = 60.0
            reason = "Good 3vs3 scenario - balanced opponents"
            
        elif expected_opponents == 4:
            # MARGINAL: 3vs4+ scenario
            score = OpportunityScore.MARGINAL
            priority = 40.0
            reason = "Marginal 3vs4+ scenario - many opponents"
            
        else:
            # POOR: Not recommended (0 opponents or 5+)
            score = OpportunityScore.POOR
            priority = 20.0
            if expected_opponents == 0:
                reason = "Empty table - no opponents"
            else:
                reason = f"Too many opponents ({expected_opponents})"
        
        return HiveOpportunity(
            table=table,
            score=score,
            priority=priority,
            required_agents=required_agents,
            current_opponents=current_opponents,
            expected_opponents=expected_opponents,
            reason=reason
        )
    
    def get_best_opportunity(self) -> Optional[HiveOpportunity]:
        """
        Get the best (highest priority) opportunity from last detection.
        
        Returns:
            Best HiveOpportunity or None
        
        EDUCATIONAL NOTE:
            Equivalent to select_best_hive_table() in sim_engine/table_selection.py
        """
        if not self.last_report:
            logger.warning("No opportunities detected yet - run detect_opportunities first")
            return None
        
        return self.last_report.best_opportunity
    
    def get_statistics(self) -> dict:
        """Get opportunity detector statistics."""
        return {
            'total_detections': self.detections_count,
            'min_priority': self.min_priority,
            'last_report': {
                'total_opportunities': len(self.last_report.opportunities) if self.last_report else 0,
                'perfect_count': self.last_report.perfect_count if self.last_report else 0,
                'excellent_count': self.last_report.excellent_count if self.last_report else 0,
                'good_count': self.last_report.good_count if self.last_report else 0,
                'best_priority': self.last_report.best_opportunity.priority if self.last_report and self.last_report.best_opportunity else 0.0
            } if self.last_report else None
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Opportunity Detector - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Initialize detector in DRY-RUN mode (safe)
    detector = OpportunityDetector(min_priority=50.0)
    
    # Detect opportunities
    print("Detecting HIVE opportunities...")
    report = detector.detect_opportunities(required_agents=3, max_seats_filter=6)
    
    print()
    print("=" * 60)
    print("Opportunity Report:")
    print("=" * 60)
    print()
    
    print(f"Total tables scanned: {report.snapshot.total_tables}")
    print(f"Total opportunities: {len(report.opportunities)}")
    print(f"  Perfect (3vs1): {report.perfect_count}")
    print(f"  Excellent (3vs2): {report.excellent_count}")
    print(f"  Good (3vs3): {report.good_count}")
    print()
    
    if report.opportunities:
        print("Top 5 Opportunities:")
        print("-" * 60)
        for i, opp in enumerate(report.opportunities[:5], 1):
            print(
                f"{i}. [{opp.score.value.upper()}] {opp.table.table_name} "
                f"(priority={opp.priority:.0f})"
            )
            print(f"   {opp.reason}")
            print(
                f"   Current: {opp.current_opponents} opponents, "
                f"{opp.table.seats_left} seats left"
            )
            print()
        
        # Best opportunity
        if report.best_opportunity:
            best = report.best_opportunity
            print("=" * 60)
            print("BEST OPPORTUNITY:")
            print("=" * 60)
            print(f"Table: {best.table.table_name} ({best.table.table_id})")
            print(f"Score: {best.score.value.upper()} (priority={best.priority:.0f})")
            print(f"Reason: {best.reason}")
            print(f"Stakes: {best.table.stakes}")
            print(f"Current opponents: {best.current_opponents}")
            print(f"Seats available: {best.table.seats_left}")
            print()
    else:
        print("[NO OPPORTUNITIES] No suitable tables found")
        print()
    
    # Statistics
    stats = detector.get_statistics()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    print(f"Total detections: {stats['total_detections']}")
    print(f"Min priority threshold: {stats['min_priority']}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
