"""
Tests for HIVE Table Selection.

Educational Use Only: Validates table selection logic for
multi-agent coordination research (Roadmap2, Phase 1).
"""

import pytest
from sim_engine.table_selection import (
    VirtualTable,
    VirtualLobby,
    HiveOpportunity,
    TableType,
    find_hive_opportunities,
    select_best_hive_table,
    filter_optimal_3vs1
)


class TestVirtualTable:
    """Test VirtualTable dataclass."""
    
    def test_table_creation(self):
        """Test creating virtual table."""
        table = VirtualTable(
            table_id="test_001",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        assert table.table_id == "test_001"
        assert table.max_seats == 6
        assert table.human_count == 2
    
    def test_seats_available_calculation(self):
        """Test available seats calculation."""
        table = VirtualTable(
            table_id="test_002",
            table_type=TableType.CASH_GAME,
            max_seats=9,
            human_count=3,
            agent_count=2
        )
        
        # 9 max - 3 humans - 2 agents = 4 available
        assert table.seats_available == 4
    
    def test_total_players(self):
        """Test total players calculation."""
        table = VirtualTable(
            table_id="test_003",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2,
            agent_count=3
        )
        
        assert table.total_players == 5
    
    def test_is_hive_opportunity_true(self):
        """Test HIVE opportunity detection - positive case."""
        table = VirtualTable(
            table_id="test_004",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1  # 1 human, 5 seats available
        )
        
        # Perfect 3vs1 setup
        assert table.is_hive_opportunity is True
    
    def test_is_hive_opportunity_false_no_space(self):
        """Test HIVE opportunity detection - no space."""
        table = VirtualTable(
            table_id="test_005",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1,
            agent_count=3  # Already 3 agents, only 2 seats left
        )
        
        assert table.is_hive_opportunity is False
    
    def test_is_hive_opportunity_false_no_humans(self):
        """Test HIVE opportunity detection - no humans."""
        table = VirtualTable(
            table_id="test_006",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=0  # Empty table
        )
        
        assert table.is_hive_opportunity is False
    
    def test_table_to_dict(self):
        """Test table serialization."""
        table = VirtualTable(
            table_id="test_007",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        data = table.to_dict()
        
        assert data['table_id'] == "test_007"
        assert data['human_count'] == 2
        assert data['seats_available'] == 4


class TestVirtualLobby:
    """Test VirtualLobby class."""
    
    def test_lobby_creation(self):
        """Test creating virtual lobby with 200 tables."""
        lobby = VirtualLobby(num_tables=200)
        
        assert len(lobby.tables) == 200
    
    def test_lobby_tables_have_valid_data(self):
        """Test generated tables have valid data."""
        lobby = VirtualLobby(num_tables=50)
        
        for table in lobby.tables:
            assert table.table_id
            assert table.max_seats in [6, 9]
            assert 0 <= table.human_count <= 6
            assert table.seats_available >= 0
    
    def test_get_table_by_id(self):
        """Test retrieving table by ID."""
        lobby = VirtualLobby(num_tables=10)
        
        # Get first table
        first_table = lobby.tables[0]
        retrieved = lobby.get_table(first_table.table_id)
        
        assert retrieved is not None
        assert retrieved.table_id == first_table.table_id
    
    def test_get_table_not_found(self):
        """Test retrieving non-existent table."""
        lobby = VirtualLobby(num_tables=10)
        
        result = lobby.get_table("non_existent")
        
        assert result is None
    
    def test_lobby_stats(self):
        """Test lobby statistics calculation."""
        lobby = VirtualLobby(num_tables=100)
        
        stats = lobby.get_stats()
        
        assert 'total_tables' in stats
        assert stats['total_tables'] == 100
        assert 'hive_opportunities' in stats
        assert 'avg_players_per_table' in stats


class TestFindHiveOpportunities:
    """Test find_hive_opportunities function."""
    
    def test_find_opportunities_in_lobby(self):
        """Test finding HIVE opportunities."""
        lobby = VirtualLobby(num_tables=200)
        
        opportunities = find_hive_opportunities(lobby)
        
        # Should find at least some opportunities
        assert isinstance(opportunities, list)
    
    def test_opportunities_sorted_by_priority(self):
        """Test opportunities are sorted by priority (best first)."""
        lobby = VirtualLobby(num_tables=200)
        
        opportunities = find_hive_opportunities(lobby)
        
        if len(opportunities) > 1:
            # Priority should be descending
            for i in range(len(opportunities) - 1):
                assert opportunities[i].priority_score >= opportunities[i + 1].priority_score
    
    def test_perfect_3vs1_gets_highest_priority(self):
        """Test that perfect 3vs1 setup gets priority 100+."""
        lobby = VirtualLobby(num_tables=0)  # Empty
        
        # Add perfect table: 1 human, 6-max, 5 seats available
        perfect_table = VirtualTable(
            table_id="perfect",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        )
        lobby.tables.append(perfect_table)
        
        opportunities = find_hive_opportunities(lobby)
        
        assert len(opportunities) == 1
        assert opportunities[0].priority_score >= 100
        assert opportunities[0].optimal_for_3vs1 is True
    
    def test_filter_by_human_count(self):
        """Test filtering by human count."""
        lobby = VirtualLobby(num_tables=0)
        
        # Add tables with different human counts
        for i in range(5):
            lobby.tables.append(VirtualTable(
                table_id=f"t_{i}",
                table_type=TableType.CASH_GAME,
                max_seats=9,
                human_count=i
            ))
        
        # Find opportunities (default: 1-3 humans)
        opportunities = find_hive_opportunities(lobby)
        
        # Should only include tables with 1-3 humans AND 3+ seats
        for opp in opportunities:
            assert 1 <= opp.table.human_count <= 3
            assert opp.table.seats_available >= 3
    
    def test_requires_3_seats_available(self):
        """Test that opportunities require 3+ seats."""
        lobby = VirtualLobby(num_tables=0)
        
        # Table with 1 human but only 1 seat available
        lobby.tables.append(VirtualTable(
            table_id="t_full",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1,
            agent_count=4  # 6 - 1 - 4 = 1 seat
        ))
        
        opportunities = find_hive_opportunities(lobby)
        
        # Should not be included (need 3 seats)
        assert len(opportunities) == 0


class TestSelectBestHiveTable:
    """Test select_best_hive_table function."""
    
    def test_select_best_returns_highest_priority(self):
        """Test selecting best table."""
        lobby = VirtualLobby(num_tables=0)
        
        # Add mediocre table
        lobby.tables.append(VirtualTable(
            table_id="mediocre",
            table_type=TableType.TOURNAMENT,
            max_seats=9,
            human_count=3
        ))
        
        # Add perfect table
        lobby.tables.append(VirtualTable(
            table_id="perfect",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        ))
        
        best = select_best_hive_table(lobby)
        
        assert best is not None
        assert best.table_id == "perfect"
    
    def test_select_best_returns_none_if_no_opportunities(self):
        """Test returns None when no suitable tables."""
        lobby = VirtualLobby(num_tables=0)
        
        # Add only unsuitable tables
        lobby.tables.append(VirtualTable(
            table_id="full",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=6  # Full table
        ))
        
        best = select_best_hive_table(lobby)
        
        assert best is None


class TestFilterFunctions:
    """Test filter utility functions."""
    
    def test_filter_optimal_3vs1(self):
        """Test filtering to optimal 3vs1 scenarios."""
        lobby = VirtualLobby(num_tables=0)
        
        # Add mix of tables
        lobby.tables.append(VirtualTable(
            table_id="optimal",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        ))
        
        lobby.tables.append(VirtualTable(
            table_id="not_optimal",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=3
        ))
        
        opportunities = find_hive_opportunities(lobby)
        optimal = filter_optimal_3vs1(opportunities)
        
        # Only 3vs1 scenarios
        assert len(optimal) == 1
        assert optimal[0].table.human_count == 1


class TestHiveOpportunity:
    """Test HiveOpportunity dataclass."""
    
    def test_opportunity_creation(self):
        """Test creating HIVE opportunity."""
        table = VirtualTable(
            table_id="test",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        )
        
        opp = HiveOpportunity(
            table=table,
            priority_score=100.0,
            reason="Perfect 3vs1",
            optimal_for_3vs1=True
        )
        
        assert opp.table.table_id == "test"
        assert opp.priority_score == 100.0
        assert opp.optimal_for_3vs1 is True
    
    def test_opportunity_comparison(self):
        """Test opportunity sorting by priority."""
        table1 = VirtualTable(
            table_id="t1",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=1
        )
        
        table2 = VirtualTable(
            table_id="t2",
            table_type=TableType.CASH_GAME,
            max_seats=6,
            human_count=2
        )
        
        opp1 = HiveOpportunity(table=table1, priority_score=100.0, reason="Best")
        opp2 = HiveOpportunity(table=table2, priority_score=60.0, reason="Good")
        
        opportunities = [opp2, opp1]
        opportunities.sort(reverse=True)
        
        # opp1 should be first (higher priority)
        assert opportunities[0].priority_score == 100.0


class TestIntegration:
    """Test full table selection workflow."""
    
    def test_full_workflow_find_and_select(self):
        """Test complete workflow: lobby → find → select."""
        # Create lobby
        lobby = VirtualLobby(num_tables=200)
        
        # Find opportunities
        opportunities = find_hive_opportunities(lobby)
        
        # Should find at least some
        assert len(opportunities) > 0
        
        # Select best
        best = select_best_hive_table(lobby)
        
        assert best is not None
        assert best.is_hive_opportunity is True
        assert best.seats_available >= 3
