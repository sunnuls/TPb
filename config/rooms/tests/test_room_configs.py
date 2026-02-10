"""
Tests for Room Configurations (Roadmap4 Phase 2).

Tests YAML configs for all poker rooms.
"""

from pathlib import Path

import pytest
import yaml


def load_room_config(room_name: str) -> dict:
    """Load room configuration from YAML."""
    config_path = Path(__file__).parent.parent / f"{room_name}.yaml"
    
    if not config_path.exists():
        pytest.skip(f"Config not found: {room_name}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestRoomConfigs:
    """Test room configuration files."""
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_config_exists(self, room_name):
        """Test that config file exists."""
        config_path = Path(__file__).parent.parent / f"{room_name}.yaml"
        assert config_path.exists(), f"Missing config for {room_name}"
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_config_structure(self, room_name):
        """Test config has required structure."""
        config = load_room_config(room_name)
        
        # Required top-level keys
        assert 'room_name' in config
        assert 'resolution' in config
        assert 'rois' in config
        assert 'colors' in config
        assert 'ocr' in config
        assert 'cards' in config
        assert 'metadata' in config
        
        assert config['room_name'] == room_name
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_hero_cards_rois(self, room_name):
        """Test hero card ROIs are defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        # Hero cards
        assert 'hero_card_1' in rois
        assert 'hero_card_2' in rois
        
        # Check ROI structure
        for card_key in ['hero_card_1', 'hero_card_2']:
            roi = rois[card_key]
            assert 'x' in roi
            assert 'y' in roi
            assert 'width' in roi
            assert 'height' in roi
            
            # Validate values
            assert roi['x'] >= 0
            assert roi['y'] >= 0
            assert roi['width'] > 0
            assert roi['height'] > 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_board_cards_rois(self, room_name):
        """Test board card ROIs are defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        # Board cards
        for i in range(1, 6):
            card_key = f'board_card_{i}'
            assert card_key in rois, f"Missing {card_key} in {room_name}"
            
            roi = rois[card_key]
            assert roi['x'] >= 0
            assert roi['y'] >= 0
            assert roi['width'] > 0
            assert roi['height'] > 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_pot_roi(self, room_name):
        """Test pot ROI is defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        assert 'pot' in rois
        
        roi = rois['pot']
        assert roi['x'] >= 0
        assert roi['y'] >= 0
        assert roi['width'] > 0
        assert roi['height'] > 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_stack_rois(self, room_name):
        """Test stack ROIs are defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        # Hero stack
        assert 'hero_stack' in rois
        
        # Villain stacks (at least 5 for 6-max)
        for i in range(1, 6):
            villain_key = f'villain_{i}_stack'
            assert villain_key in rois, f"Missing {villain_key} in {room_name}"
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_action_buttons(self, room_name):
        """Test action button ROIs are defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        # Action buttons
        buttons = ['fold_button', 'check_button', 'call_button', 'raise_button']
        for button in buttons:
            assert button in rois, f"Missing {button} in {room_name}"
            
            roi = rois[button]
            assert roi['x'] >= 0
            assert roi['y'] >= 0
            assert roi['width'] > 0
            assert roi['height'] > 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_bet_amount_field(self, room_name):
        """Test bet amount field ROI is defined."""
        config = load_room_config(room_name)
        rois = config['rois']
        
        assert 'bet_amount_field' in rois
        
        roi = rois['bet_amount_field']
        assert roi['x'] >= 0
        assert roi['y'] >= 0
        assert roi['width'] > 0
        assert roi['height'] > 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_colors_defined(self, room_name):
        """Test color definitions."""
        config = load_room_config(room_name)
        colors = config['colors']
        
        # Required colors
        assert 'table_felt' in colors
        assert 'card_back' in colors
        assert 'button_active' in colors
        assert 'button_inactive' in colors
        
        # Validate RGB format
        for color_key in ['table_felt', 'card_back', 'button_active', 'button_inactive']:
            rgb = colors[color_key]
            assert isinstance(rgb, list)
            assert len(rgb) == 3
            
            # Valid RGB range
            for value in rgb:
                assert 0 <= value <= 255
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_ocr_settings(self, room_name):
        """Test OCR settings."""
        config = load_room_config(room_name)
        ocr = config['ocr']
        
        # Required OCR settings
        assert 'pot_prefix' in ocr
        assert 'bet_prefix' in ocr
        assert 'stack_suffix' in ocr
        assert 'decimal_separator' in ocr
        assert 'thousands_separator' in ocr
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_card_settings(self, room_name):
        """Test card recognition settings."""
        config = load_room_config(room_name)
        cards = config['cards']
        
        # Required card settings
        assert 'rank_height' in cards
        assert 'suit_height' in cards
        assert 'rank_y_offset' in cards
        assert 'suit_y_offset' in cards
        
        # Validate values
        assert cards['rank_height'] > 0
        assert cards['suit_height'] > 0
        assert cards['rank_y_offset'] >= 0
        assert cards['suit_y_offset'] >= 0
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_metadata_indicators(self, room_name):
        """Test metadata indicator ROIs."""
        config = load_room_config(room_name)
        metadata = config['metadata']
        
        # Required indicators
        assert 'table_type_indicator' in metadata
        assert 'street_indicator' in metadata


class TestRoomConfigComparison:
    """Test consistency across room configs."""
    
    def test_all_rooms_have_same_essential_rois(self):
        """Test all rooms have essential ROIs."""
        rooms = ["pokerstars", "ignition", "ggpoker", "888poker", "partypoker"]
        
        # Essential ROIs that should be in all configs
        essential_rois = [
            'hero_card_1', 'hero_card_2',
            'board_card_1', 'board_card_2', 'board_card_3', 'board_card_4', 'board_card_5',
            'pot', 'hero_stack',
            'fold_button', 'check_button', 'call_button', 'raise_button',
            'bet_amount_field'
        ]
        
        for room in rooms:
            config = load_room_config(room)
            rois = config['rois']
            
            for roi_name in essential_rois:
                assert roi_name in rois, f"{room} missing {roi_name}"
    
    def test_resolution_consistency(self):
        """Test all configs use same resolution."""
        rooms = ["pokerstars", "ignition", "ggpoker", "888poker", "partypoker"]
        
        resolutions = set()
        for room in rooms:
            config = load_room_config(room)
            resolutions.add(config['resolution'])
        
        # All should be 1920x1080
        assert len(resolutions) == 1
        assert '1920x1080' in resolutions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
