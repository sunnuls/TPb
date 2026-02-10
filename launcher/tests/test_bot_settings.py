"""
Tests for BotSettings - Phase 5.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import tempfile
from pathlib import Path

from launcher.bot_settings import BotSettings, StrategyPreset, BotSettingsManager


class TestBotSettings:
    """Tests for BotSettings."""
    
    def test_create_default(self):
        """Test creating default settings."""
        settings = BotSettings()
        
        assert settings.preset == StrategyPreset.BALANCED
        assert settings.aggression_level == 5
        assert settings.equity_threshold == 0.65
        assert settings.max_bet_multiplier == 3.0
        assert settings.delay_min == 0.4
        assert settings.delay_max == 3.5
        assert settings.mouse_curve_intensity == 5
        assert settings.max_session_time == 120
        assert not settings.auto_rejoin
        assert not settings.enable_manipulation
        assert not settings.enable_collusion
    
    def test_create_custom(self):
        """Test creating custom settings."""
        settings = BotSettings(
            preset=StrategyPreset.CUSTOM,
            aggression_level=7,
            equity_threshold=0.60,
            max_bet_multiplier=4.0,
            delay_min=0.5,
            delay_max=2.5
        )
        
        assert settings.preset == StrategyPreset.CUSTOM
        assert settings.aggression_level == 7
        assert settings.equity_threshold == 0.60
    
    def test_validation(self):
        """Test parameter validation."""
        # Out of range values should be clamped
        settings = BotSettings(
            aggression_level=15,  # Too high
            equity_threshold=1.5,  # Too high
            max_bet_multiplier=20.0,  # Too high
            delay_min=-1.0,  # Too low
            delay_max=0.2,  # Less than min
            mouse_curve_intensity=15  # Too high
        )
        
        assert settings.aggression_level == 10  # Clamped
        assert settings.equity_threshold == 1.0  # Clamped
        assert settings.max_bet_multiplier == 10.0  # Clamped
        assert settings.delay_min == 0.1  # Clamped
        assert settings.delay_max >= settings.delay_min  # Fixed
        assert settings.mouse_curve_intensity == 10  # Clamped
    
    def test_conservative_preset(self):
        """Test conservative preset."""
        settings = BotSettings.from_preset(StrategyPreset.CONSERVATIVE)
        
        assert settings.preset == StrategyPreset.CONSERVATIVE
        assert settings.aggression_level == 3
        assert settings.equity_threshold == 0.75
        assert settings.max_bet_multiplier == 2.0
        assert settings.delay_min == 1.0
        assert settings.delay_max == 4.0
        assert not settings.enable_manipulation
        assert not settings.enable_collusion
    
    def test_balanced_preset(self):
        """Test balanced preset."""
        settings = BotSettings.from_preset(StrategyPreset.BALANCED)
        
        assert settings.preset == StrategyPreset.BALANCED
        assert settings.aggression_level == 5
        assert settings.equity_threshold == 0.65
        assert settings.max_bet_multiplier == 3.0
        assert settings.auto_rejoin
    
    def test_aggressive_preset(self):
        """Test aggressive preset."""
        settings = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
        
        assert settings.preset == StrategyPreset.AGGRESSIVE
        assert settings.aggression_level == 8
        assert settings.equity_threshold == 0.55
        assert settings.max_bet_multiplier == 5.0
        assert settings.delay_min == 0.2
        assert settings.delay_max == 2.0
    
    def test_godmode_preset(self):
        """Test godmode preset."""
        settings = BotSettings.from_preset(StrategyPreset.GODMODE)
        
        assert settings.preset == StrategyPreset.GODMODE
        assert settings.aggression_level == 10
        assert settings.equity_threshold == 0.50
        assert settings.max_bet_multiplier == 10.0
        assert settings.enable_manipulation  # DANGER
        assert settings.enable_collusion  # DANGER
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        settings = BotSettings(
            aggression_level=7,
            equity_threshold=0.70
        )
        
        data = settings.to_dict()
        
        assert 'preset' in data
        assert 'aggression_level' in data
        assert data['aggression_level'] == 7
        assert data['equity_threshold'] == 0.70
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'preset': 'aggressive',
            'aggression_level': 8,
            'equity_threshold': 0.55,
            'max_bet_multiplier': 5.0,
            'delay_min': 0.2,
            'delay_max': 2.0,
            'mouse_curve_intensity': 3,
            'max_session_time': 150,
            'auto_rejoin': True,
            'enable_manipulation': False,
            'enable_collusion': False
        }
        
        settings = BotSettings.from_dict(data)
        
        assert settings.preset == StrategyPreset.AGGRESSIVE
        assert settings.aggression_level == 8
        assert settings.equity_threshold == 0.55


class TestBotSettingsManager:
    """Tests for BotSettingsManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            assert manager.config_dir.exists()
            assert manager.bot_settings_dir.exists()
    
    def test_save_and_load_global(self):
        """Test saving and loading global settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            # Create settings
            settings = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
            
            # Save
            success = manager.save_global_settings(settings)
            assert success
            assert manager.settings_file.exists()
            
            # Load
            loaded = manager.load_global_settings()
            assert loaded.preset == StrategyPreset.AGGRESSIVE
            assert loaded.aggression_level == 8
    
    def test_load_global_no_file(self):
        """Test loading global settings when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            # Should return default
            loaded = manager.load_global_settings()
            assert loaded.preset == StrategyPreset.BALANCED
    
    def test_save_and_load_per_bot(self):
        """Test saving and loading per-bot settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            account_id = "test_account_123"
            settings = BotSettings(aggression_level=9)
            
            # Save
            success = manager.save_bot_settings(account_id, settings)
            assert success
            
            # Load
            loaded = manager.load_bot_settings(account_id)
            assert loaded is not None
            assert loaded.aggression_level == 9
    
    def test_load_per_bot_no_file(self):
        """Test loading per-bot settings when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            # Should return None
            loaded = manager.load_bot_settings("nonexistent")
            assert loaded is None
    
    def test_preset_comparison(self):
        """Compare all presets."""
        presets = [
            StrategyPreset.CONSERVATIVE,
            StrategyPreset.BALANCED,
            StrategyPreset.AGGRESSIVE,
            StrategyPreset.GODMODE
        ]
        
        print("\n" + "=" * 60)
        print("Preset Comparison")
        print("=" * 60)
        
        for preset in presets:
            settings = BotSettings.from_preset(preset)
            print(f"\n{preset.value.upper()}:")
            print(f"  Aggression: {settings.aggression_level}/10")
            print(f"  Equity: {settings.equity_threshold:.0%}")
            print(f"  Max bet: {settings.max_bet_multiplier}x")
            print(f"  Delay: {settings.delay_min:.1f}s - {settings.delay_max:.1f}s")
            print(f"  Manipulation: {settings.enable_manipulation}")
            print(f"  Collusion: {settings.enable_collusion}")
        
        print("=" * 60)
        
        # Verify aggression increases across presets
        conservative = BotSettings.from_preset(StrategyPreset.CONSERVATIVE)
        balanced = BotSettings.from_preset(StrategyPreset.BALANCED)
        aggressive = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
        godmode = BotSettings.from_preset(StrategyPreset.GODMODE)
        
        assert conservative.aggression_level < balanced.aggression_level
        assert balanced.aggression_level < aggressive.aggression_level
        assert aggressive.aggression_level < godmode.aggression_level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
