"""
Tests for HIVE Agent.

Educational Use Only: Validates agent behavior for
multi-agent coordination research (Roadmap2, Phase 1).
"""

import pytest
from sim_engine.agent import (
    HiveAgent,
    HiveGroup,
    AgentState
)
from sim_engine.table_selection import (
    VirtualTable,
    VirtualLobby,
    TableType,
    find_hive_opportunities
)


class TestHiveAgent:
    """Test HiveAgent class."""
    
    def test_agent_creation(self):
        """Test creating HIVE agent."""
        agent = HiveAgent(agent_id="test_agent_1")
        
        assert agent.agent_id == "test_agent_1"
        assert agent.state == AgentState.IDLE
        assert agent.current_table is None
    
    def test_join_environment_success(self):
        """Test successful environment join."""
        agent = HiveAgent(agent_id="agent_1")
        
        table = VirtualTable(
            table_id="table_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        result = agent.join_environment("table_001", table)
        
        assert result is True
        assert agent.state == AgentState.SEATED
        assert agent.environment_id == "table_001"
        assert agent.current_table == table
        assert agent.tables_joined == 1
        assert table.agent_count == 1
    
    def test_join_environment_no_space(self):
        """Test joining table with no space."""
        agent = HiveAgent(agent_id="agent_1")
        
        table = VirtualTable(
            table_id="table_full",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=5,
            agent_count=1  # Only 0 seats left
        )
        
        result = agent.join_environment("table_full", table)
        
        assert result is False
        assert agent.state == AgentState.IDLE
    
    def test_leave_environment(self):
        """Test leaving environment."""
        agent = HiveAgent(agent_id="agent_1")
        
        table = VirtualTable(
            table_id="table_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        # Join first
        agent.join_environment("table_001", table)
        assert table.agent_count == 1
        
        # Then leave
        result = agent.leave_environment()
        
        assert result is True
        assert agent.state == AgentState.IDLE
        assert agent.current_table is None
        assert agent.environment_id is None
        assert table.agent_count == 0
    
    def test_can_join_table_when_idle(self):
        """Test can_join_table returns True when idle."""
        agent = HiveAgent(agent_id="agent_1")
        
        table = VirtualTable(
            table_id="table_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        assert agent.can_join_table(table) is True
    
    def test_cannot_join_when_already_seated(self):
        """Test can_join_table returns False when already seated."""
        agent = HiveAgent(agent_id="agent_1")
        
        table1 = VirtualTable(
            table_id="table_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        table2 = VirtualTable(
            table_id="table_002",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        )
        
        # Join first table
        agent.join_environment("table_001", table1)
        
        # Cannot join second while seated
        assert agent.can_join_table(table2) is False
    
    def test_session_duration(self):
        """Test session duration tracking."""
        agent = HiveAgent(agent_id="agent_1")
        
        table = VirtualTable(
            table_id="table_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        agent.join_environment("table_001", table)
        
        # Should have timestamp
        assert agent.join_timestamp is not None
        duration = agent.get_session_duration()
        
        assert duration >= 0.0
    
    def test_agent_to_dict(self):
        """Test agent serialization."""
        agent = HiveAgent(agent_id="agent_1", hive_group_id="alpha")
        
        data = agent.to_dict()
        
        assert data['agent_id'] == "agent_1"
        assert data['hive_group_id'] == "alpha"
        assert data['state'] == AgentState.IDLE


class TestHiveGroup:
    """Test HiveGroup coordination."""
    
    def test_group_creation(self):
        """Test creating HIVE group."""
        group = HiveGroup(group_id="hive_alpha")
        
        assert group.group_id == "hive_alpha"
        assert len(group.agents) == 0
        assert group.is_complete is False
    
    def test_add_agents_to_group(self):
        """Test adding agents to group."""
        group = HiveGroup(group_id="hive_alpha")
        
        agents = [
            HiveAgent(agent_id=f"agent_{i}")
            for i in range(3)
        ]
        
        for agent in agents:
            result = group.add_agent(agent)
            assert result is True
        
        assert group.is_complete is True
        assert len(group.agents) == 3
    
    def test_cannot_add_4th_agent(self):
        """Test group limited to 3 agents."""
        group = HiveGroup(group_id="hive_alpha")
        
        # Add 3 agents
        for i in range(3):
            group.add_agent(HiveAgent(agent_id=f"agent_{i}"))
        
        # Try to add 4th
        result = group.add_agent(HiveAgent(agent_id="agent_extra"))
        
        assert result is False
        assert len(group.agents) == 3
    
    def test_agents_get_group_id(self):
        """Test agents receive group_id when added."""
        group = HiveGroup(group_id="hive_beta")
        agent = HiveAgent(agent_id="agent_1")
        
        group.add_agent(agent)
        
        assert agent.hive_group_id == "hive_beta"
    
    def test_coordinate_join_success(self):
        """Test coordinated join of 3 agents."""
        group = HiveGroup(group_id="hive_alpha")
        
        # Add 3 agents
        for i in range(3):
            group.add_agent(HiveAgent(agent_id=f"agent_{i}"))
        
        # Create target table
        table = VirtualTable(
            table_id="target_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        )
        
        # Coordinate join
        result = group.coordinate_join(table)
        
        assert result is True
        assert table.agent_count == 3
        assert group.all_seated is True
    
    def test_coordinate_join_insufficient_seats(self):
        """Test coordinated join fails with insufficient seats."""
        group = HiveGroup(group_id="hive_alpha")
        
        # Add 3 agents
        for i in range(3):
            group.add_agent(HiveAgent(agent_id=f"agent_{i}"))
        
        # Table with only 2 seats
        table = VirtualTable(
            table_id="target_002",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=3,
            agent_count=1  # 6 - 3 - 1 = 2 seats
        )
        
        result = group.coordinate_join(table)
        
        assert result is False
    
    def test_all_seated_check(self):
        """Test all_seated property."""
        group = HiveGroup(group_id="hive_alpha")
        
        # Add 3 agents
        for i in range(3):
            group.add_agent(HiveAgent(agent_id=f"agent_{i}"))
        
        table = VirtualTable(
            table_id="target_003",
            table_type=TableType.CASH_GAME,
            max_seats=9,
            human_count=1
        )
        
        # Before join
        assert group.all_seated is False
        
        # After coordinate join
        group.coordinate_join(table)
        assert group.all_seated is True


class TestIntegration:
    """Test full Phase 1 integration."""
    
    def test_full_phase1_workflow(self):
        """Test complete Phase 1 workflow: lobby → select → join."""
        # 1. Create lobby
        lobby = VirtualLobby(num_tables=200)
        
        # 2. Find opportunities
        opportunities = find_hive_opportunities(lobby)
        
        assert len(opportunities) > 0
        
        # 3. Select best table
        best_table = opportunities[0].table
        
        # 4. Create HIVE group
        group = HiveGroup(group_id="research_group_1")
        for i in range(3):
            group.add_agent(HiveAgent(agent_id=f"research_agent_{i}"))
        
        # 5. Coordinate join
        result = group.coordinate_join(best_table)
        
        # Verify success (should work with 200 random tables)
        if result:
            assert group.all_seated is True
            assert best_table.agent_count == 3
