"""
Tests for TableState (Roadmap3 Phase 2).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from sim_engine.state.table_state import (
    TableState,
    PlayerState,
    Position,
    Street
)


class TestPlayerState:
    """Test PlayerState dataclass."""
    
    def test_player_state_creation(self):
        """Test basic player state creation."""
        player = PlayerState(
            player_id="hero",
            position=Position.BTN,
            stack=1000.0,
            current_bet=50.0,
            is_hero=True,
            hole_cards=["As", "Kh"]
        )
        
        assert player.player_id == "hero"
        assert player.position == Position.BTN
        assert player.stack == 1000.0
        assert player.current_bet == 50.0
        assert player.is_hero is True
        assert player.is_active is True
        assert player.hole_cards == ["As", "Kh"]
    
    def test_player_state_defaults(self):
        """Test player state default values."""
        player = PlayerState(player_id="villain")
        
        assert player.position == Position.UNKNOWN
        assert player.stack == 0.0
        assert player.current_bet == 0.0
        assert player.is_hero is False
        assert player.is_active is True
        assert player.hole_cards == []


class TestTableState:
    """Test TableState core functionality."""
    
    def test_table_state_creation(self):
        """Test basic table state creation."""
        state = TableState(
            table_id="table_001",
            table_type="cash",
            max_seats=6,
            street=Street.FLOP,
            board=["Qd", "Jc", "9s"],
            pot=150.0
        )
        
        assert state.table_id == "table_001"
        assert state.table_type == "cash"
        assert state.max_seats == 6
        assert state.street == Street.FLOP
        assert state.board == ["Qd", "Jc", "9s"]
        assert state.pot == 150.0
    
    def test_get_hero(self):
        """Test get_hero method."""
        hero = PlayerState(
            player_id="hero",
            is_hero=True,
            hole_cards=["As", "Kh"]
        )
        
        state = TableState(
            table_id="table_001",
            players={"hero": hero},
            hero_id="hero"
        )
        
        retrieved_hero = state.get_hero()
        assert retrieved_hero is not None
        assert retrieved_hero.player_id == "hero"
        assert retrieved_hero.is_hero is True
    
    def test_get_hero_none(self):
        """Test get_hero when no hero exists."""
        state = TableState(table_id="table_001")
        
        hero = state.get_hero()
        assert hero is None
    
    def test_get_hero_cards(self):
        """Test get_hero_cards method."""
        hero = PlayerState(
            player_id="hero",
            is_hero=True,
            hole_cards=["As", "Kh"]
        )
        
        state = TableState(
            table_id="table_001",
            players={"hero": hero},
            hero_id="hero"
        )
        
        cards = state.get_hero_cards()
        assert cards == ["As", "Kh"]
    
    def test_get_hero_cards_empty(self):
        """Test get_hero_cards when no hero."""
        state = TableState(table_id="table_001")
        
        cards = state.get_hero_cards()
        assert cards == []
    
    def test_get_active_players(self):
        """Test get_active_players method."""
        hero = PlayerState(player_id="hero", is_hero=True, is_active=True)
        villain1 = PlayerState(player_id="v1", is_active=True)
        villain2 = PlayerState(player_id="v2", is_active=False)
        
        state = TableState(
            table_id="table_001",
            players={"hero": hero, "v1": villain1, "v2": villain2},
            hero_id="hero"
        )
        
        active = state.get_active_players()
        assert len(active) == 2
        assert all(p.is_active for p in active)
    
    def test_get_opponent_count(self):
        """Test get_opponent_count method."""
        hero = PlayerState(player_id="hero", is_hero=True, is_active=True)
        villain1 = PlayerState(player_id="v1", is_active=True)
        villain2 = PlayerState(player_id="v2", is_active=True)
        
        state = TableState(
            table_id="table_001",
            players={"hero": hero, "v1": villain1, "v2": villain2},
            hero_id="hero"
        )
        
        opponent_count = state.get_opponent_count()
        assert opponent_count == 2
    
    def test_get_opponent_count_no_hero(self):
        """Test get_opponent_count when no hero."""
        villain1 = PlayerState(player_id="v1", is_active=True)
        villain2 = PlayerState(player_id="v2", is_active=True)
        
        state = TableState(
            table_id="table_001",
            players={"v1": villain1, "v2": villain2}
        )
        
        opponent_count = state.get_opponent_count()
        assert opponent_count == 2
    
    def test_to_collective_state(self):
        """Test conversion to CollectiveState."""
        hero = PlayerState(
            player_id="hero",
            is_hero=True,
            stack=1000.0,
            hole_cards=["As", "Kh"]
        )
        villain = PlayerState(player_id="v1", stack=950.0)
        
        state = TableState(
            table_id="table_001",
            street=Street.FLOP,
            board=["Qd", "Jc", "9s"],
            pot=150.0,
            players={"hero": hero, "v1": villain},
            hero_id="hero"
        )
        
        collective = state.to_collective_state()
        
        assert collective.collective_cards == ["As", "Kh"]
        assert collective.pot_size == 150.0
        assert collective.board == ["Qd", "Jc", "9s"]
        assert "hero" in collective.stack_sizes
        assert "v1" in collective.stack_sizes
        assert collective.stack_sizes["hero"] == 1000.0
    
    def test_as_dict(self):
        """Test as_dict serialization."""
        hero = PlayerState(
            player_id="hero",
            position=Position.BTN,
            stack=1000.0,
            is_hero=True,
            hole_cards=["As", "Kh"]
        )
        
        state = TableState(
            table_id="table_001",
            table_type="cash",
            street=Street.FLOP,
            board=["Qd", "Jc", "9s"],
            pot=150.0,
            players={"hero": hero},
            hero_id="hero"
        )
        
        data = state.as_dict()
        
        assert data['table_id'] == "table_001"
        assert data['table_type'] == "cash"
        assert data['street'] == "flop"
        assert data['board'] == ["Qd", "Jc", "9s"]
        assert data['pot'] == 150.0
        assert data['hero_id'] == "hero"
        assert 'hero' in data['players']
        assert data['players']['hero']['position'] == 'button'
        assert data['players']['hero']['stack'] == 1000.0


class TestEnums:
    """Test enum values."""
    
    def test_street_enum(self):
        """Test Street enum values."""
        assert Street.PREFLOP.value == "preflop"
        assert Street.FLOP.value == "flop"
        assert Street.TURN.value == "turn"
        assert Street.RIVER.value == "river"
    
    def test_position_enum(self):
        """Test Position enum values."""
        assert Position.BTN.value == "button"
        assert Position.SB.value == "small_blind"
        assert Position.BB.value == "big_blind"
        assert Position.UTG.value == "utg"
        assert Position.MP.value == "middle_position"
        assert Position.CO.value == "cutoff"
        assert Position.UNKNOWN.value == "unknown"


class TestIntegration:
    """Integration tests for table state."""
    
    def test_full_table_state_workflow(self):
        """Test complete table state creation and usage."""
        # Create players
        hero = PlayerState(
            player_id="hero",
            position=Position.BTN,
            stack=1000.0,
            current_bet=50.0,
            is_hero=True,
            hole_cards=["As", "Kh"]
        )
        
        villain1 = PlayerState(
            player_id="villain1",
            position=Position.SB,
            stack=950.0,
            current_bet=25.0
        )
        
        villain2 = PlayerState(
            player_id="villain2",
            position=Position.BB,
            stack=1100.0,
            current_bet=50.0
        )
        
        # Create table state
        state = TableState(
            table_id="table_001",
            table_type="cash",
            max_seats=6,
            street=Street.FLOP,
            board=["Qd", "Jc", "9s"],
            pot=125.0,
            players={
                "hero": hero,
                "villain1": villain1,
                "villain2": villain2
            },
            hero_id="hero",
            current_bet=50.0,
            min_raise=100.0,
            extraction_method="simulated",
            confidence=1.0
        )
        
        # Validate state
        assert state.get_hero() is not None
        assert state.get_hero_cards() == ["As", "Kh"]
        assert len(state.get_active_players()) == 3
        assert state.get_opponent_count() == 2
        
        # Test conversion to CollectiveState
        collective = state.to_collective_state()
        assert collective.collective_cards == ["As", "Kh"]
        assert collective.pot_size == 125.0
        assert len(collective.stack_sizes) == 3
        
        # Test serialization
        data = state.as_dict()
        assert data['table_id'] == "table_001"
        assert len(data['players']) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
