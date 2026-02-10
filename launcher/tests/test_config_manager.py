"""
Tests for ConfigManager - Phase 1.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import tempfile
from pathlib import Path

from launcher.config_manager import ConfigManager
from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig, ROIZone


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create config manager with temp directory."""
    return ConfigManager(config_dir=temp_config_dir)


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_initialization(self, config_manager, temp_config_dir):
        """Test config manager initialization."""
        assert config_manager.config_dir == temp_config_dir
        assert config_manager.config_dir.exists()
        assert config_manager.roi_dir.exists()
    
    def test_save_and_load_accounts(self, config_manager):
        """Test saving and loading accounts."""
        # Create accounts
        accounts = [
            Account(nickname="Bot001", room="pokerstars"),
            Account(nickname="Bot002", room="ignition")
        ]
        
        # Save
        success = config_manager.save_accounts(accounts)
        assert success
        assert config_manager.accounts_file.exists()
        
        # Load
        loaded = config_manager.load_accounts()
        assert len(loaded) == 2
        assert loaded[0].nickname == "Bot001"
        assert loaded[1].nickname == "Bot002"
    
    def test_load_accounts_no_file(self, config_manager):
        """Test loading accounts when file doesn't exist."""
        loaded = config_manager.load_accounts()
        assert len(loaded) == 0
    
    def test_save_and_load_roi_config(self, config_manager):
        """Test saving and loading ROI config."""
        account_id = "test-account-123"
        
        # Create ROI config
        roi_config = ROIConfig(account_id=account_id)
        roi_config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
        
        # Save
        success = config_manager.save_roi_config(account_id, roi_config)
        assert success
        
        roi_file = config_manager.roi_dir / f"roi_{account_id}.json"
        assert roi_file.exists()
        
        # Load
        loaded = config_manager.load_roi_config(account_id)
        assert loaded is not None
        assert loaded.account_id == account_id
        assert len(loaded.zones) == 2
        assert "hero_card_1" in loaded.zones
        assert "pot" in loaded.zones
    
    def test_load_roi_config_no_file(self, config_manager):
        """Test loading ROI config when file doesn't exist."""
        loaded = config_manager.load_roi_config("nonexistent")
        assert loaded is None
    
    def test_delete_roi_config(self, config_manager):
        """Test deleting ROI config."""
        account_id = "test-account-123"
        
        # Create and save
        roi_config = ROIConfig(account_id=account_id)
        config_manager.save_roi_config(account_id, roi_config)
        
        # Verify exists
        roi_file = config_manager.roi_dir / f"roi_{account_id}.json"
        assert roi_file.exists()
        
        # Delete
        success = config_manager.delete_roi_config(account_id)
        assert success
        assert not roi_file.exists()
    
    def test_delete_roi_config_no_file(self, config_manager):
        """Test deleting nonexistent ROI config."""
        success = config_manager.delete_roi_config("nonexistent")
        assert success
    
    def test_get_all_roi_configs(self, config_manager):
        """Test getting all ROI configs."""
        # Create multiple configs
        accounts = ["acc1", "acc2", "acc3"]
        
        for acc_id in accounts:
            roi_config = ROIConfig(account_id=acc_id)
            roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
            config_manager.save_roi_config(acc_id, roi_config)
        
        # Get all
        all_configs = config_manager.get_all_roi_configs()
        
        assert len(all_configs) == 3
        assert "acc1" in all_configs
        assert "acc2" in all_configs
        assert "acc3" in all_configs
    
    def test_persistence(self, config_manager):
        """Test data persistence across manager instances."""
        # Create and save account
        account = Account(nickname="PersistBot", room="pokerstars")
        config_manager.save_accounts([account])
        
        # Create new manager with same directory
        new_manager = ConfigManager(config_dir=config_manager.config_dir)
        
        # Load account
        loaded = new_manager.load_accounts()
        assert len(loaded) == 1
        assert loaded[0].nickname == "PersistBot"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
