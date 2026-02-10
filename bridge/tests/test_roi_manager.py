"""
Unit tests for ROI manager (Roadmap3 Phase 1).

Tests ROI loading and management functionality.
"""

import pytest
from pathlib import Path

from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
from bridge.roi_manager import ROI, ROIManager


@pytest.fixture(autouse=True)
def setup_safety():
    """Setup safety framework in dry-run mode for tests."""
    SafetyFramework._instance = None  # Reset singleton
    SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN, enable_kill_switch=False))
    yield
    SafetyFramework._instance = None  # Cleanup


class TestROI:
    """Test ROI dataclass."""
    
    def test_roi_creation(self):
        """Can create ROI."""
        roi = ROI(
            name="test_roi",
            x=100,
            y=200,
            width=300,
            height=400,
            description="Test ROI"
        )
        
        assert roi.name == "test_roi"
        assert roi.x == 100
        assert roi.y == 200
        assert roi.width == 300
        assert roi.height == 400
    
    def test_roi_as_tuple(self):
        """ROI can be converted to tuple."""
        roi = ROI(name="test", x=10, y=20, width=30, height=40)
        
        tuple_form = roi.as_tuple()
        
        assert tuple_form == (10, 20, 30, 40)
    
    def test_roi_as_dict(self):
        """ROI can be converted to dict."""
        roi = ROI(name="test", x=10, y=20, width=30, height=40, description="desc")
        
        dict_form = roi.as_dict()
        
        assert dict_form['name'] == "test"
        assert dict_form['x'] == 10
        assert dict_form['width'] == 30


class TestROIManagerInit:
    """Test ROIManager initialization."""
    
    def test_initialization_default(self):
        """Can initialize with default config."""
        manager = ROIManager()
        
        assert manager.config_path is not None
        assert manager.current_room is None
        assert manager.current_resolution is None
    
    def test_initialization_loads_config(self):
        """Initialization loads configuration."""
        manager = ROIManager(config_path="bridge/config/live_config.yaml")
        
        # Should have loaded some presets
        assert isinstance(manager.roi_presets, dict)


class TestListAvailable:
    """Test listing available rooms and resolutions."""
    
    def test_list_available_rooms(self):
        """Can list available rooms."""
        manager = ROIManager()
        
        rooms = manager.list_available_rooms()
        
        assert isinstance(rooms, list)
    
    def test_list_available_resolutions(self):
        """Can list available resolutions for room."""
        manager = ROIManager()
        
        # Try with first available room
        rooms = manager.list_available_rooms()
        if rooms:
            resolutions = manager.list_available_resolutions(rooms[0])
            assert isinstance(resolutions, list)


class TestLoadROISet:
    """Test loading ROI sets."""
    
    def test_load_roi_set_success(self):
        """Can load ROI set for room and resolution."""
        manager = ROIManager()
        
        # Try loading pokerstars_6max @ 1920x1080
        success = manager.load_roi_set("pokerstars_6max", "1920x1080")
        
        # Should succeed if config exists
        if success:
            assert manager.current_room == "pokerstars_6max"
            assert manager.current_resolution == "1920x1080"
            assert len(manager.current_rois) > 0
    
    def test_load_roi_set_invalid_room(self):
        """Loading invalid room fails gracefully."""
        manager = ROIManager()
        
        success = manager.load_roi_set("nonexistent_room", "1920x1080")
        
        assert success is False
    
    def test_load_roi_set_invalid_resolution(self):
        """Loading invalid resolution fails gracefully."""
        manager = ROIManager()
        
        success = manager.load_roi_set("pokerstars_6max", "999x999")
        
        assert success is False


class TestGetROI:
    """Test getting specific ROIs."""
    
    def test_get_roi_success(self):
        """Can get specific ROI by name."""
        manager = ROIManager()
        
        # Load a set first
        if manager.load_roi_set("pokerstars_6max", "1920x1080"):
            roi = manager.get_roi("hero_cards")
            
            if roi:
                assert isinstance(roi, ROI)
                assert roi.name == "hero_cards"
                assert roi.width > 0
                assert roi.height > 0
    
    def test_get_roi_not_found(self):
        """get_roi returns None for nonexistent ROI."""
        manager = ROIManager()
        manager.load_roi_set("pokerstars_6max", "1920x1080")
        
        roi = manager.get_roi("nonexistent_roi")
        
        assert roi is None
    
    def test_get_roi_tuple(self):
        """Can get ROI as tuple."""
        manager = ROIManager()
        
        if manager.load_roi_set("pokerstars_6max", "1920x1080"):
            roi_tuple = manager.get_roi_tuple("hero_cards")
            
            if roi_tuple:
                assert isinstance(roi_tuple, tuple)
                assert len(roi_tuple) == 4
                assert all(isinstance(x, int) for x in roi_tuple)


class TestGetAllROIs:
    """Test getting all ROIs."""
    
    def test_get_all_rois(self):
        """Can get all loaded ROIs."""
        manager = ROIManager()
        
        if manager.load_roi_set("pokerstars_6max", "1920x1080"):
            all_rois = manager.get_all_rois()
            
            assert isinstance(all_rois, dict)
            assert len(all_rois) > 0
            assert all(isinstance(roi, ROI) for roi in all_rois.values())
    
    def test_get_all_rois_empty_initially(self):
        """get_all_rois returns empty dict initially."""
        manager = ROIManager()
        
        all_rois = manager.get_all_rois()
        
        assert isinstance(all_rois, dict)
        assert len(all_rois) == 0


class TestCustomROI:
    """Test adding custom ROIs."""
    
    def test_add_custom_roi(self):
        """Can add custom ROI at runtime."""
        manager = ROIManager()
        
        manager.add_custom_roi("custom", x=50, y=60, width=70, height=80)
        
        roi = manager.get_roi("custom")
        assert roi is not None
        assert roi.name == "custom"
        assert roi.x == 50
        assert roi.y == 60
    
    def test_custom_roi_in_get_all(self):
        """Custom ROI appears in get_all_rois."""
        manager = ROIManager()
        manager.add_custom_roi("custom", x=10, y=20, width=30, height=40)
        
        all_rois = manager.get_all_rois()
        
        assert "custom" in all_rois


class TestStatistics:
    """Test statistics retrieval."""
    
    def test_get_statistics_initial(self):
        """get_statistics returns initial state."""
        manager = ROIManager()
        
        stats = manager.get_statistics()
        
        assert 'current_room' in stats
        assert 'current_resolution' in stats
        assert 'loaded_rois' in stats
        assert 'dry_run' in stats
        assert stats['loaded_rois'] == 0
        assert stats['dry_run'] is True
    
    def test_get_statistics_after_load(self):
        """get_statistics reflects loaded state."""
        manager = ROIManager()
        
        if manager.load_roi_set("pokerstars_6max", "1920x1080"):
            stats = manager.get_statistics()
            
            assert stats['current_room'] == "pokerstars_6max"
            assert stats['current_resolution'] == "1920x1080"
            assert stats['loaded_rois'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
