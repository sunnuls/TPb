"""
Tests for Launcher Data Models - Phase 1.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
from launcher.models.account import (
    Account,
    AccountStatus,
    WindowInfo,
    WindowType
)
from launcher.models.roi_config import ROIConfig, ROIZone


class TestWindowInfo:
    """Tests for WindowInfo."""
    
    def test_create_empty(self):
        """Test creating empty window info."""
        window = WindowInfo()
        
        assert window.window_id is None
        assert window.window_title is None
        assert window.window_type == WindowType.UNKNOWN
        assert not window.is_captured()
    
    def test_create_with_data(self):
        """Test creating window info with data."""
        window = WindowInfo(
            window_id="12345",
            window_title="PokerStars",
            window_type=WindowType.DESKTOP_CLIENT,
            process_name="PokerStars.exe",
            position=(100, 100, 800, 600)
        )
        
        assert window.window_id == "12345"
        assert window.window_title == "PokerStars"
        assert window.window_type == WindowType.DESKTOP_CLIENT
        assert window.process_name == "PokerStars.exe"
        assert window.position == (100, 100, 800, 600)
        assert window.is_captured()


class TestAccount:
    """Tests for Account."""
    
    def test_create_default(self):
        """Test creating account with defaults."""
        account = Account()
        
        assert account.account_id
        assert account.nickname == "Unnamed"
        assert account.status == AccountStatus.IDLE
        assert not account.window_info.is_captured()
        assert not account.roi_configured
        assert not account.bot_running
        assert account.room == "pokerstars"
    
    def test_create_with_data(self):
        """Test creating account with data."""
        account = Account(
            nickname="TestBot001",
            room="ignition",
            notes="Test account"
        )
        
        assert account.nickname == "TestBot001"
        assert account.room == "ignition"
        assert account.notes == "Test account"
    
    def test_is_ready_to_run(self):
        """Test ready to run check."""
        account = Account()
        
        # Not ready - no window
        assert not account.is_ready_to_run()
        
        # Capture window
        account.window_info.window_id = "12345"
        assert not account.is_ready_to_run()  # Still need ROI
        
        # Configure ROI
        account.roi_configured = True
        assert account.is_ready_to_run()
        
        # Bot running - not ready
        account.bot_running = True
        assert not account.is_ready_to_run()
        
        # Error status - not ready
        account.bot_running = False
        account.status = AccountStatus.ERROR
        assert not account.is_ready_to_run()
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        account = Account(nickname="Test", room="pokerstars")
        data = account.to_dict()
        
        assert 'account_id' in data
        assert data['nickname'] == "Test"
        assert data['room'] == "pokerstars"
        assert 'window_info' in data
        assert 'roi_configured' in data
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'account_id': 'test-id-123',
            'nickname': 'TestBot',
            'status': 'ready',
            'window_info': {
                'window_id': '12345',
                'window_title': 'PokerStars',
                'window_type': 'desktop_client',
                'process_name': 'poker.exe',
                'position': (0, 0, 800, 600)
            },
            'roi_configured': True,
            'bot_running': False,
            'room': 'pokerstars',
            'notes': 'Test'
        }
        
        account = Account.from_dict(data)
        
        assert account.account_id == 'test-id-123'
        assert account.nickname == 'TestBot'
        assert account.status == AccountStatus.READY
        assert account.window_info.window_id == '12345'
        assert account.roi_configured is True


class TestROIZone:
    """Tests for ROIZone."""
    
    def test_create_zone(self):
        """Test creating ROI zone."""
        zone = ROIZone("hero_card_1", 100, 200, 50, 70)
        
        assert zone.name == "hero_card_1"
        assert zone.x == 100
        assert zone.y == 200
        assert zone.width == 50
        assert zone.height == 70
    
    def test_to_tuple(self):
        """Test converting to tuple."""
        zone = ROIZone("pot", 500, 100, 100, 30)
        
        assert zone.to_tuple() == (500, 100, 100, 30)
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        zone = ROIZone("fold_button", 400, 800, 80, 40)
        data = zone.to_dict()
        
        assert data['name'] == "fold_button"
        assert data['x'] == 400
        assert data['y'] == 800
        assert data['width'] == 80
        assert data['height'] == 40
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'name': 'call_button',
            'x': 490,
            'y': 800,
            'width': 80,
            'height': 40
        }
        
        zone = ROIZone.from_dict(data)
        
        assert zone.name == 'call_button'
        assert zone.x == 490
        assert zone.y == 800


class TestROIConfig:
    """Tests for ROIConfig."""
    
    def test_create_config(self):
        """Test creating ROI config."""
        config = ROIConfig(account_id="test-123")
        
        assert config.account_id == "test-123"
        assert config.resolution == (1920, 1080)
        assert len(config.zones) == 0
    
    def test_add_zone(self):
        """Test adding zones."""
        config = ROIConfig(account_id="test-123")
        
        zone1 = ROIZone("hero_card_1", 100, 200, 50, 70)
        zone2 = ROIZone("pot", 500, 100, 100, 30)
        
        config.add_zone(zone1)
        config.add_zone(zone2)
        
        assert len(config.zones) == 2
        assert "hero_card_1" in config.zones
        assert "pot" in config.zones
    
    def test_get_zone(self):
        """Test getting zone by name."""
        config = ROIConfig(account_id="test-123")
        zone = ROIZone("fold_button", 400, 800, 80, 40)
        config.add_zone(zone)
        
        retrieved = config.get_zone("fold_button")
        assert retrieved is not None
        assert retrieved.name == "fold_button"
        
        missing = config.get_zone("missing")
        assert missing is None
    
    def test_has_required_zones(self):
        """Test checking required zones."""
        config = ROIConfig(account_id="test-123")
        
        # Missing required zones
        assert not config.has_required_zones()
        
        # Add required zones
        config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        config.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        config.add_zone(ROIZone("pot", 500, 100, 100, 30))
        config.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        config.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        
        # All required zones present
        assert config.has_required_zones()
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        config = ROIConfig(account_id="test-123")
        config.add_zone(ROIZone("pot", 500, 100, 100, 30))
        
        data = config.to_dict()
        
        assert data['account_id'] == "test-123"
        assert 'resolution' in data
        assert 'zones' in data
        assert 'pot' in data['zones']
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'account_id': 'test-123',
            'resolution': [1920, 1080],
            'zones': {
                'pot': {
                    'name': 'pot',
                    'x': 500,
                    'y': 100,
                    'width': 100,
                    'height': 30
                }
            },
            'configured_at': 1234567890.0
        }
        
        config = ROIConfig.from_dict(data)
        
        assert config.account_id == 'test-123'
        assert config.resolution == (1920, 1080)
        assert len(config.zones) == 1
        assert 'pot' in config.zones


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
