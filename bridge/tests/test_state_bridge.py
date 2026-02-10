"""
Tests for StateBridge (Roadmap3 Phase 2.4).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from bridge.state_bridge import StateBridge
from sim_engine.state.table_state import TableState, Street, Position


class TestStateBridge:
    """Test StateBridge core functionality."""
    
    def test_init_dry_run(self):
        """Test initialization in dry-run mode."""
        bridge = StateBridge(dry_run=True)
        
        assert bridge.dry_run is True
        assert bridge.screen_capture is not None
        assert bridge.roi_manager is not None
        assert bridge.card_extractor is not None
        assert bridge.numeric_parser is not None
        assert bridge.metadata_extractor is not None
        assert bridge.extractions_count == 0
    
    def test_get_live_table_state_dry_run(self):
        """Test table state extraction in dry-run mode."""
        bridge = StateBridge(dry_run=True)
        
        state = bridge.get_live_table_state(
            table_id="test_table",
            room="pokerstars_6max",
            resolution="1920x1080"
        )
        
        assert state is not None
        assert isinstance(state, TableState)
        assert state.table_id == "test_table"
        assert bridge.extractions_count == 1
    
    def test_extracted_state_structure(self):
        """Test extracted state has correct structure."""
        bridge = StateBridge(dry_run=True)
        
        state = bridge.get_live_table_state()
        
        # Validate basic table info
        assert state.table_id is not None
        assert isinstance(state.street, Street)
        assert state.pot >= 0
        
        # Validate players
        assert len(state.players) > 0
        assert state.hero_id in state.players
        
        # Validate hero
        hero = state.get_hero()
        assert hero is not None
        assert hero.is_hero is True
        assert len(hero.hole_cards) == 2
    
    def test_extracted_state_has_board(self):
        """Test extracted state includes board cards."""
        bridge = StateBridge(dry_run=True)
        
        state = bridge.get_live_table_state()
        
        # Board should be present (simulated data includes flop)
        assert state.board is not None
        assert isinstance(state.board, list)
        assert len(state.board) >= 0
        assert len(state.board) <= 5
    
    def test_extracted_state_conversion_to_collective(self):
        """Test extracted state can convert to CollectiveState."""
        bridge = StateBridge(dry_run=True)
        
        state = bridge.get_live_table_state()
        collective = state.to_collective_state()
        
        # Validate conversion
        assert collective is not None
        assert collective.pot_size == state.pot
        assert collective.board == state.board
        assert len(collective.stack_sizes) == len(state.players)
    
    def test_multiple_extractions(self):
        """Test multiple extractions work correctly."""
        bridge = StateBridge(dry_run=True)
        
        state1 = bridge.get_live_table_state(table_id="table_1")
        state2 = bridge.get_live_table_state(table_id="table_2")
        state3 = bridge.get_live_table_state(table_id="table_3")
        
        assert state1 is not None
        assert state2 is not None
        assert state3 is not None
        assert bridge.extractions_count == 3
        assert bridge.last_state is state3
    
    def test_map_position(self):
        """Test _map_position helper."""
        bridge = StateBridge(dry_run=True)
        
        assert bridge._map_position('BTN') == Position.BTN
        assert bridge._map_position('btn') == Position.BTN
        assert bridge._map_position('SB') == Position.SB
        assert bridge._map_position('BB') == Position.BB
        assert bridge._map_position('UTG') == Position.UTG
        assert bridge._map_position('MP') == Position.MP
        assert bridge._map_position('CO') == Position.CO
        assert bridge._map_position('UNKNOWN') == Position.UNKNOWN
        assert bridge._map_position('invalid') == Position.UNKNOWN
    
    def test_get_statistics(self):
        """Test statistics collection."""
        bridge = StateBridge(dry_run=True)
        
        bridge.get_live_table_state()
        bridge.get_live_table_state()
        
        stats = bridge.get_statistics()
        
        assert stats['total_extractions'] == 2
        assert stats['last_extraction_time'] >= 0  # Can be very small in dry-run
        assert stats['dry_run'] is True
        assert 'components' in stats
        assert 'cards' in stats['components']
        assert 'numeric' in stats['components']
        assert 'metadata' in stats['components']


class TestStateBridgeWithConfig:
    """Test StateBridge with configuration."""
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = {
            'screen_capture': {'window_title': 'PokerStars'},
            'roi': {'default_room': 'pokerstars_6max'}
        }
        
        bridge = StateBridge(dry_run=True, config=config)
        
        assert bridge.config == config
        assert bridge.dry_run is True
    
    def test_extraction_with_different_rooms(self):
        """Test extraction with different room configurations."""
        bridge = StateBridge(dry_run=True)
        
        # Test with different rooms
        state1 = bridge.get_live_table_state(room="pokerstars_6max")
        state2 = bridge.get_live_table_state(room="partypoker_6max")
        
        assert state1 is not None
        assert state2 is not None
        assert bridge.extractions_count == 2
    
    def test_extraction_with_different_resolutions(self):
        """Test extraction with different resolutions."""
        bridge = StateBridge(dry_run=True)
        
        # Test with different resolutions
        state1 = bridge.get_live_table_state(resolution="1920x1080")
        state2 = bridge.get_live_table_state(resolution="1280x720")
        
        assert state1 is not None
        assert state2 is not None


class TestStateBridgeIntegration:
    """Integration tests for full state bridge pipeline."""
    
    def test_full_extraction_pipeline(self):
        """Test complete extraction pipeline."""
        bridge = StateBridge(dry_run=True)
        
        # Extract complete table state
        state = bridge.get_live_table_state(
            table_id="integration_test",
            room="pokerstars_6max",
            resolution="1920x1080"
        )
        
        # Validate complete state
        assert state is not None
        
        # Validate extraction metadata
        assert state.extraction_method == "simulated"
        assert state.confidence == 1.0
        
        # Validate table structure
        assert state.table_id == "integration_test"
        assert state.max_seats == 6
        
        # Validate hero
        hero = state.get_hero()
        assert hero is not None
        assert len(hero.hole_cards) == 2
        
        # Validate opponents
        opponent_count = state.get_opponent_count()
        assert opponent_count > 0
        
        # Validate conversion to CollectiveState
        collective = state.to_collective_state()
        assert collective.collective_cards == hero.hole_cards
        assert collective.pot_size == state.pot
        
        # Validate serialization
        data = state.as_dict()
        assert data['table_id'] == "integration_test"
        assert data['extraction_method'] == "simulated"
    
    def test_extraction_timing(self):
        """Test extraction timing is reasonable."""
        bridge = StateBridge(dry_run=True)
        
        state = bridge.get_live_table_state()
        
        assert state is not None
        assert bridge.last_extraction_time >= 0  # Can be very small in dry-run
        # In dry-run mode, extraction should be very fast
        assert bridge.last_extraction_time < 1.0  # Less than 1 second
    
    def test_component_statistics(self):
        """Test all components track statistics correctly."""
        bridge = StateBridge(dry_run=True)
        
        # Perform multiple extractions
        for i in range(3):
            bridge.get_live_table_state(table_id=f"table_{i}")
        
        # Get statistics
        stats = bridge.get_statistics()
        
        # Validate main bridge stats
        assert stats['total_extractions'] == 3
        
        # Validate component stats
        assert stats['components']['cards']['total_extractions'] == 6  # 2 per extraction (hero+board)
        assert stats['components']['numeric']['total_extractions'] == 3
        assert stats['components']['metadata']['total_extractions'] == 3
        
        # All should have 100% success rate in dry-run
        assert stats['components']['cards']['success_rate'] == 1.0
        assert stats['components']['numeric']['success_rate'] == 1.0
        assert stats['components']['metadata']['success_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
