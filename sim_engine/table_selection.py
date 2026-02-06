"""
HIVE Table Selection Module.

Educational Use Only: For academic study of multi-agent coordination
in simulated game theory environments. Research-focused implementation
of table selection strategies for 3-agent cooperative systems.

Roadmap2 - Phase 1: HIVE Table Selection + Auto-Join
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class TableType(str, Enum):
    """Table types in virtual lobby."""
    CASH_GAME = "cash_game"
    TOURNAMENT = "tournament"
    SIT_N_GO = "sit_n_go"


@dataclass
class VirtualTable:
    """
    Virtual poker table in simulated lobby.
    
    Educational Note:
        Represents a simulated environment for studying multi-agent
        coordination patterns in game theory research contexts.
    """
    table_id: str
    table_type: TableType
    max_seats: int  # 6 or 9
    human_count: int  # Number of human players (0-6)
    agent_count: int = 0  # Number of research agents
    stakes: str = "1/2"
    table_name: str = ""
    
    @property
    def seats_available(self) -> int:
        """Calculate available seats."""
        return self.max_seats - self.human_count - self.agent_count
    
    @property
    def total_players(self) -> int:
        """Total players at table."""
        return self.human_count + self.agent_count
    
    @property
    def is_hive_opportunity(self) -> bool:
        """
        Check if table is suitable for HIVE setup (3 agents vs 1-3 humans).
        
        Educational Note:
            HIVE opportunities are defined as tables where 3 coordinated
            agents can study collective decision-making patterns.
        """
        # Ideal: 1-3 humans, with space for 3 agents
        return (
            1 <= self.human_count <= 3 and
            self.seats_available >= 3
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'table_id': self.table_id,
            'table_type': self.table_type,
            'max_seats': self.max_seats,
            'human_count': self.human_count,
            'agent_count': self.agent_count,
            'seats_available': self.seats_available,
            'total_players': self.total_players,
            'stakes': self.stakes,
            'table_name': self.table_name,
            'is_hive_opportunity': self.is_hive_opportunity
        }


@dataclass
class HiveOpportunity:
    """
    Identified HIVE opportunity for 3-agent coordination.
    
    Educational Note:
        Represents a research-suitable environment for studying
        3-agent cooperative strategies in game theory.
    """
    table: VirtualTable
    priority_score: float  # 0-100, higher is better
    reason: str
    optimal_for_3vs1: bool = False
    
    def __lt__(self, other: HiveOpportunity) -> bool:
        """Compare by priority score for sorting."""
        return self.priority_score < other.priority_score


class VirtualLobby:
    """
    Simulated poker lobby with multiple tables.
    
    Educational Note:
        Virtual environment for studying table selection strategies
        in multi-agent research scenarios.
    """
    
    def __init__(self, num_tables: int = 200):
        """
        Initialize virtual lobby with random tables.
        
        Args:
            num_tables: Number of tables to simulate (default: 200)
        """
        self.tables: List[VirtualTable] = []
        self._generate_tables(num_tables)
    
    def _generate_tables(self, count: int):
        """Generate random tables for simulation."""
        table_types = [TableType.CASH_GAME, TableType.TOURNAMENT, TableType.SIT_N_GO]
        max_seats_options = [6, 9]
        stakes_options = ["0.5/1", "1/2", "2/5", "5/10"]
        
        for i in range(count):
            table = VirtualTable(
                table_id=f"table_{i:03d}",
                table_type=random.choice(table_types),
                max_seats=random.choice(max_seats_options),
                human_count=random.randint(0, 6),  # 0-6 humans
                stakes=random.choice(stakes_options),
                table_name=f"Virtual_{random.choice(['NL', 'PL', 'FL'])}_{i}"
            )
            self.tables.append(table)
    
    def get_table(self, table_id: str) -> Optional[VirtualTable]:
        """Get table by ID."""
        for table in self.tables:
            if table.table_id == table_id:
                return table
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get lobby statistics."""
        return {
            'total_tables': len(self.tables),
            'empty_tables': sum(1 for t in self.tables if t.total_players == 0),
            'full_tables': sum(1 for t in self.tables if t.seats_available == 0),
            'hive_opportunities': sum(1 for t in self.tables if t.is_hive_opportunity),
            'avg_players_per_table': sum(t.total_players for t in self.tables) / max(1, len(self.tables))
        }


def find_hive_opportunities(
    lobby: VirtualLobby,
    min_humans: int = 1,
    max_humans: int = 3,
    required_seats: int = 3
) -> List[HiveOpportunity]:
    """
    Find optimal tables for HIVE 3-agent coordination setup.
    
    Args:
        lobby: Virtual lobby to scan
        min_humans: Minimum human players (default: 1)
        max_humans: Maximum human players (default: 3)  
        required_seats: Seats needed for agents (default: 3)
    
    Returns:
        List of HiveOpportunity objects, sorted by priority (best first)
        
    Educational Note:
        This function identifies research-suitable environments for
        studying 3-agent cooperative decision-making patterns in
        game theory. Priority scoring favors 3vs1 scenarios (ideal
        for academic study of coordination advantages).
    
    Priority Scoring:
        - 100 points: Exactly 1 human, 5+ seats available (perfect 3vs1)
        - 80 points: 1 human, 3-4 seats available
        - 60 points: 2 humans, 3+ seats available
        - 40 points: 3 humans, 3+ seats available
        - Bonus: +10 for 6-max tables (faster gameplay for research)
    """
    opportunities: List[HiveOpportunity] = []
    
    for table in lobby.tables:
        # Basic filter: must have humans and available seats
        if not (min_humans <= table.human_count <= max_humans):
            continue
        
        if table.seats_available < required_seats:
            continue
        
        # Calculate priority score
        priority = 0.0
        reason = ""
        optimal_3vs1 = False
        
        if table.human_count == 1 and table.seats_available >= 5:
            # Perfect scenario: 1 human, plenty of room
            priority = 100.0
            reason = "Ideal 3vs1 setup: 1 human, 5+ seats available"
            optimal_3vs1 = True
            
        elif table.human_count == 1 and table.seats_available >= 3:
            # Good scenario: 1 human, enough room
            priority = 80.0
            reason = "Good 3vs1 setup: 1 human, 3-4 seats available"
            optimal_3vs1 = True
            
        elif table.human_count == 2 and table.seats_available >= 3:
            # Acceptable: 2 humans
            priority = 60.0
            reason = "3vs2 setup: 2 humans, 3+ seats available"
            
        elif table.human_count == 3 and table.seats_available >= 3:
            # Minimal: 3 humans (balanced but less coordination advantage)
            priority = 40.0
            reason = "3vs3 setup: 3 humans, 3+ seats available"
        
        # Bonus for 6-max tables (faster research iterations)
        if table.max_seats == 6:
            priority += 10.0
            reason += " | 6-max (faster)"
        
        # Bonus for cash games (easier simulation)
        if table.table_type == TableType.CASH_GAME:
            priority += 5.0
            reason += " | Cash game"
        
        opportunity = HiveOpportunity(
            table=table,
            priority_score=priority,
            reason=reason,
            optimal_for_3vs1=optimal_3vs1
        )
        opportunities.append(opportunity)
    
    # Sort by priority (highest first)
    opportunities.sort(reverse=True)
    
    return opportunities


def select_best_hive_table(lobby: VirtualLobby) -> Optional[VirtualTable]:
    """
    Select single best table for HIVE operation.
    
    Args:
        lobby: Virtual lobby to scan
    
    Returns:
        Best table for 3-agent coordination, or None if no suitable tables
        
    Educational Note:
        Convenience function for quickly identifying the optimal
        research environment for multi-agent coordination studies.
    """
    opportunities = find_hive_opportunities(lobby)
    
    if not opportunities:
        return None
    
    # Return best opportunity
    return opportunities[0].table


def filter_by_stakes(
    opportunities: List[HiveOpportunity],
    stakes: str
) -> List[HiveOpportunity]:
    """Filter opportunities by stake level."""
    return [opp for opp in opportunities if opp.table.stakes == stakes]


def filter_optimal_3vs1(
    opportunities: List[HiveOpportunity]
) -> List[HiveOpportunity]:
    """Filter to only optimal 3vs1 scenarios."""
    return [opp for opp in opportunities if opp.optimal_for_3vs1]


# Example usage for research purposes
if __name__ == "__main__":
    print("=" * 60)
    print("HIVE Table Selection - Research Simulation")
    print("Educational Use Only: Multi-Agent Game Theory Study")
    print("=" * 60)
    print()
    
    # Create virtual lobby
    lobby = VirtualLobby(num_tables=200)
    
    print(f"Lobby Statistics:")
    stats = lobby.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Find HIVE opportunities
    opportunities = find_hive_opportunities(lobby)
    
    print(f"Found {len(opportunities)} HIVE opportunities")
    print()
    
    # Show top 10
    print("Top 10 HIVE Opportunities:")
    for i, opp in enumerate(opportunities[:10], 1):
        table = opp.table
        print(f"{i}. {table.table_id} | Priority: {opp.priority_score:.0f}")
        print(f"   {table.human_count} humans, {table.seats_available} seats | {opp.reason}")
        print()
    
    # Show best 3vs1 opportunities
    optimal_3vs1 = filter_optimal_3vs1(opportunities)
    print(f"Optimal 3vs1 scenarios: {len(optimal_3vs1)}")
    
    # Select best table
    best = select_best_hive_table(lobby)
    if best:
        print(f"\nBest table selected: {best.table_id}")
        print(f"  Humans: {best.human_count}, Seats: {best.seats_available}")
