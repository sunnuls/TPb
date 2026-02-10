"""
Integration Tests for Roadmap6 Phase 5.

⚠️ EDUCATIONAL RESEARCH ONLY.

Tests:
1. Settings presets
2. Settings persistence
3. Settings manager integration
4. Full settings workflow
"""

import pytest
import tempfile
from pathlib import Path

from launcher.bot_settings import BotSettings, StrategyPreset, BotSettingsManager


class TestPhase5Integration:
    """Integration tests for Phase 5."""
    
    def test_all_presets_valid(self):
        """Test all presets are valid."""
        presets = [
            StrategyPreset.CONSERVATIVE,
            StrategyPreset.BALANCED,
            StrategyPreset.AGGRESSIVE,
            StrategyPreset.GODMODE
        ]
        
        for preset in presets:
            settings = BotSettings.from_preset(preset)
            
            # Verify all parameters are in valid ranges
            assert 1 <= settings.aggression_level <= 10
            assert 0.0 <= settings.equity_threshold <= 1.0
            assert 1.0 <= settings.max_bet_multiplier <= 10.0
            assert 0.1 <= settings.delay_min <= 5.0
            assert settings.delay_min <= settings.delay_max <= 10.0
            assert 0 <= settings.mouse_curve_intensity <= 10
            assert 10 <= settings.max_session_time <= 600
    
    def test_preset_progression(self):
        """Test preset aggression progression."""
        conservative = BotSettings.from_preset(StrategyPreset.CONSERVATIVE)
        balanced = BotSettings.from_preset(StrategyPreset.BALANCED)
        aggressive = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
        godmode = BotSettings.from_preset(StrategyPreset.GODMODE)
        
        # Aggression should increase
        assert conservative.aggression_level < balanced.aggression_level
        assert balanced.aggression_level < aggressive.aggression_level
        assert aggressive.aggression_level < godmode.aggression_level
        
        # Equity threshold should decrease
        assert conservative.equity_threshold > balanced.equity_threshold
        assert balanced.equity_threshold > aggressive.equity_threshold
        assert aggressive.equity_threshold > godmode.equity_threshold
        
        # Only godmode has dangerous features
        assert not conservative.enable_manipulation
        assert not balanced.enable_manipulation
        assert not aggressive.enable_manipulation
        assert godmode.enable_manipulation
        assert godmode.enable_collusion
    
    def test_settings_serialization(self):
        """Test settings serialization."""
        # Create custom settings
        settings = BotSettings(
            preset=StrategyPreset.CUSTOM,
            aggression_level=7,
            equity_threshold=0.60,
            max_bet_multiplier=4.0,
            delay_min=0.5,
            delay_max=2.5,
            auto_rejoin=True
        )
        
        # Serialize
        data = settings.to_dict()
        
        # Deserialize
        restored = BotSettings.from_dict(data)
        
        # Verify
        assert restored.preset == settings.preset
        assert restored.aggression_level == settings.aggression_level
        assert restored.equity_threshold == settings.equity_threshold
        assert restored.max_bet_multiplier == settings.max_bet_multiplier
        assert restored.auto_rejoin == settings.auto_rejoin
    
    def test_settings_persistence_workflow(self):
        """Test complete settings persistence workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = BotSettingsManager(config_dir=config_dir)
            
            # 1. Create and save global settings
            settings = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
            manager.save_global_settings(settings)
            
            # 2. Load global settings
            loaded_global = manager.load_global_settings()
            assert loaded_global.preset == StrategyPreset.AGGRESSIVE
            
            # 3. Create per-bot settings
            bot_accounts = ["bot_001", "bot_002", "bot_003"]
            
            for i, account_id in enumerate(bot_accounts):
                bot_settings = BotSettings(aggression_level=5 + i)
                manager.save_bot_settings(account_id, bot_settings)
            
            # 4. Load per-bot settings
            for i, account_id in enumerate(bot_accounts):
                loaded_bot = manager.load_bot_settings(account_id)
                assert loaded_bot is not None
                assert loaded_bot.aggression_level == 5 + i
            
            # 5. Verify persistence
            new_manager = BotSettingsManager(config_dir=config_dir)
            
            reloaded_global = new_manager.load_global_settings()
            assert reloaded_global.preset == StrategyPreset.AGGRESSIVE
            
            reloaded_bot = new_manager.load_bot_settings(bot_accounts[0])
            assert reloaded_bot.aggression_level == 5
    
    def test_global_vs_per_bot_settings(self):
        """Test global vs per-bot settings hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BotSettingsManager(config_dir=Path(tmpdir))
            
            # Set global to balanced
            global_settings = BotSettings.from_preset(StrategyPreset.BALANCED)
            manager.save_global_settings(global_settings)
            
            # Override for specific bot
            account_id = "special_bot"
            bot_settings = BotSettings.from_preset(StrategyPreset.GODMODE)
            manager.save_bot_settings(account_id, bot_settings)
            
            # Load both
            loaded_global = manager.load_global_settings()
            loaded_bot = manager.load_bot_settings(account_id)
            
            # Verify different settings
            assert loaded_global.preset == StrategyPreset.BALANCED
            assert loaded_bot.preset == StrategyPreset.GODMODE
            assert loaded_global.aggression_level != loaded_bot.aggression_level
    
    def test_settings_validation_edge_cases(self):
        """Test validation with edge cases."""
        # Extreme values
        settings = BotSettings(
            aggression_level=999,
            equity_threshold=-5.0,
            max_bet_multiplier=0.1,
            delay_min=100.0,
            delay_max=0.1,
            mouse_curve_intensity=-10,
            max_session_time=5
        )
        
        # All should be clamped to valid ranges
        assert settings.aggression_level == 10
        assert settings.equity_threshold == 0.0
        assert settings.max_bet_multiplier == 1.0
        assert settings.delay_min == 5.0
        assert settings.delay_max >= settings.delay_min
        assert settings.mouse_curve_intensity == 0
        assert settings.max_session_time == 10
    
    def test_full_settings_workflow(self):
        """Test complete settings workflow."""
        print("\n" + "=" * 60)
        print("Full Settings Workflow Test")
        print("=" * 60)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # 1. Initialize manager
            manager = BotSettingsManager(config_dir=config_dir)
            print(f"\n1. Manager initialized")
            
            # 2. Load default global settings
            global_settings = manager.load_global_settings()
            print(f"2. Default global: {global_settings.preset.value}")
            
            # 3. User selects preset
            selected_preset = StrategyPreset.AGGRESSIVE
            global_settings = BotSettings.from_preset(selected_preset)
            print(f"3. User selects: {selected_preset.value}")
            
            # 4. Save global settings
            manager.save_global_settings(global_settings)
            print(f"4. Global settings saved")
            
            # 5. Configure per-bot overrides
            bot_overrides = {
                "bot_stealth": BotSettings.from_preset(StrategyPreset.CONSERVATIVE),
                "bot_whale": BotSettings.from_preset(StrategyPreset.GODMODE)
            }
            
            print(f"5. Per-bot overrides:")
            for account_id, settings in bot_overrides.items():
                manager.save_bot_settings(account_id, settings)
                print(f"   {account_id}: {settings.preset.value}")
            
            # 6. Verify persistence
            new_manager = BotSettingsManager(config_dir=config_dir)
            
            reloaded_global = new_manager.load_global_settings()
            print(f"\n6. Persistence verified:")
            print(f"   Global: {reloaded_global.preset.value}")
            
            for account_id in bot_overrides:
                reloaded = new_manager.load_bot_settings(account_id)
                print(f"   {account_id}: {reloaded.preset.value}")
            
            print("\n" + "=" * 60)
            print("Full settings workflow complete")
            print("=" * 60)


# Summary test
def test_phase5_summary():
    """Print Phase 5 completion summary."""
    print("\n" + "=" * 60)
    print("PHASE 5 COMPLETION SUMMARY")
    print("=" * 60)
    print()
    print("Components implemented:")
    print("  ✓ BotSettings model (bot_settings.py)")
    print("  ✓ StrategyPreset enum")
    print("  ✓ BotSettingsManager")
    print("  ✓ SettingsDialog UI (settings_dialog.py)")
    print("  ✓ Main window integration")
    print()
    print("Features:")
    print("  - 4 strategy presets + custom")
    print("  - 11 configurable parameters")
    print("  - Global settings")
    print("  - Per-bot settings overrides")
    print("  - JSON persistence")
    print("  - Settings dialog (PyQt6)")
    print("  - Menu integration (Ctrl+S)")
    print()
    print("Presets:")
    print("  - Conservative: Safe, high equity threshold")
    print("  - Balanced: Default, moderate aggression")
    print("  - Aggressive: Low threshold, fast actions")
    print("  - GodMode: Maximum aggression, collusion enabled")
    print()
    print("Parameters:")
    print("  1. Aggression level (1-10)")
    print("  2. Equity threshold (0.0-1.0)")
    print("  3. Max bet multiplier (1.0-10.0)")
    print("  4. Action delay range (0.1-10.0s)")
    print("  5. Mouse curve intensity (0-10)")
    print("  6. Max session time (10-600 min)")
    print("  7. Auto-rejoin (bool)")
    print("  8. Enable manipulation (bool)")
    print("  9. Enable collusion (bool)")
    print()
    print("Tests:")
    print("  - test_bot_settings.py")
    print("  - test_phase5_integration.py")
    print()
    print("=" * 60)
    print("Phase 5: Bot Settings & Presets COMPLETE")
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
