"""
HIVE Agent Module.

Educational Use Only: Research agent for studying multi-agent coordination
patterns in simulated game theory environments.

Roadmap2 - Phase 1: Agent with auto-join capability
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sim_engine.table_selection import VirtualTable


class AgentState(str, Enum):
    """Agent operational states."""
    IDLE = "idle"
    SCANNING = "scanning"
    JOINING = "joining"
    SEATED = "seated"
    IN_HAND = "in_hand"
    LEAVING = "leaving"


@dataclass
class HiveAgent:
    """
    Research agent for HIVE coordination studies.
    
    Educational Note:
        This agent is designed exclusively for academic research into
        multi-agent coordination and collective decision-making patterns.
        Not intended for real gaming or commercial use.
    """
    agent_id: str
    hive_group_id: Optional[str] = None  # Group of 3 coordinated agents
    state: AgentState = AgentState.IDLE
    current_table: Optional[VirtualTable] = None
    environment_id: Optional[str] = None
    
    # Statistics for research tracking
    tables_joined: int = 0
    hands_played: int = 0
    coordination_events: int = 0
    join_timestamp: Optional[float] = None
    
    def join_environment(self, environment_id: str, table: VirtualTable) -> bool:
        """
        Join a virtual environment (table).
        
        Args:
            environment_id: Unique environment identifier
            table: VirtualTable to join
        
        Returns:
            True if join successful, False otherwise
            
        Educational Note:
            Environment joining simulates the process of agents entering
            a coordinated research scenario for game theory studies.
        """
        # Validate table has space
        if table.seats_available < 1:
            return False
        
        # Update agent state
        self.state = AgentState.JOINING
        self.environment_id = environment_id
        self.current_table = table
        self.join_timestamp = time.time()
        
        # Simulate join latency (realistic timing for research)
        # In real implementation, this would be async WebSocket connection
        
        # Mark as seated
        self.state = AgentState.SEATED
        self.tables_joined += 1
        
        # Update table agent count
        table.agent_count += 1
        
        return True
    
    def leave_environment(self) -> bool:
        """
        Leave current environment.
        
        Returns:
            True if leave successful
        """
        if not self.current_table:
            return False
        
        # Update table
        self.current_table.agent_count -= 1
        
        # Reset agent state
        self.state = AgentState.IDLE
        self.current_table = None
        self.environment_id = None
        
        return True
    
    def can_join_table(self, table: VirtualTable) -> bool:
        """
        Check if agent can join table.
        
        Args:
            table: Table to check
        
        Returns:
            True if agent can join
        """
        # Must be idle
        if self.state not in [AgentState.IDLE, AgentState.SCANNING]:
            return False
        
        # Table must have space
        if table.seats_available < 1:
            return False
        
        return True
    
    def get_session_duration(self) -> float:
        """Get duration at current table (seconds)."""
        if not self.join_timestamp:
            return 0.0
        return time.time() - self.join_timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'agent_id': self.agent_id,
            'hive_group_id': self.hive_group_id,
            'state': self.state,
            'environment_id': self.environment_id,
            'tables_joined': self.tables_joined,
            'hands_played': self.hands_played,
            'coordination_events': self.coordination_events,
            'session_duration': self.get_session_duration()
        }


@dataclass
class HiveGroup:
    """
    Group of 3 coordinated agents for research.
    
    Educational Note:
        HIVE groups study emergent cooperation patterns when
        multiple agents share information and coordinate decisions.
    """
    group_id: str
    agents: List[HiveAgent] = field(default_factory=list)
    target_table: Optional[VirtualTable] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if group has exactly 3 agents."""
        return len(self.agents) == 3
    
    @property
    def all_seated(self) -> bool:
        """Check if all agents are seated at target table."""
        if not self.is_complete or not self.target_table:
            return False
        
        return all(
            agent.state == AgentState.SEATED and
            agent.environment_id == self.target_table.table_id
            for agent in self.agents
        )
    
    def add_agent(self, agent: HiveAgent) -> bool:
        """Add agent to group."""
        if len(self.agents) >= 3:
            return False
        
        agent.hive_group_id = self.group_id
        self.agents.append(agent)
        return True
    
    def coordinate_join(self, table: VirtualTable) -> bool:
        """
        Coordinate all 3 agents to join same table.
        
        Args:
            table: Target table for coordination
        
        Returns:
            True if all agents successfully joined
            
        Educational Note:
            Coordinated joining is a key research element, studying
            how multiple agents synchronize actions for collective goals.
        """
        if not self.is_complete:
            return False
        
        if table.seats_available < 3:
            return False
        
        self.target_table = table
        
        # All agents join
        success_count = 0
        for agent in self.agents:
            if agent.join_environment(table.table_id, table):
                success_count += 1
        
        return success_count == 3


# Example usage for research
if __name__ == "__main__":
    print("=" * 60)
    print("HIVE Agent - Research Module")
    print("Educational Use Only: Multi-Agent Coordination Study")
    print("=" * 60)
    print()
    
    # Create 3 agents
    agents = [
        HiveAgent(agent_id=f"hive_agent_{i}")
        for i in range(3)
    ]
    
    # Form HIVE group
    group = HiveGroup(group_id="hive_alpha")
    for agent in agents:
        group.add_agent(agent)
    
    print(f"HIVE Group: {group.group_id}")
    print(f"  Agents: {len(group.agents)}")
    print(f"  Complete: {group.is_complete}")
    print()
    
    # Create test table
    from sim_engine.table_selection import TableType
    test_table = VirtualTable(
        table_id="test_001",
        table_type=TableType.CASH_GAME,
        max_seats=6,
        human_count=1,
        stakes="1/2"
    )
    
    print(f"Target Table: {test_table.table_id}")
    print(f"  Humans: {test_table.human_count}")
    print(f"  Available seats: {test_table.seats_available}")
    print()
    
    # Coordinate join
    if group.coordinate_join(test_table):
        print("✓ All agents successfully joined!")
        print(f"  Table now has: {test_table.total_players} players")
        print(f"  All seated: {group.all_seated}")
    else:
        print("✗ Failed to coordinate join")
