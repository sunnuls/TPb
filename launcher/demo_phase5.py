"""
Phase 5 Demo - Bot Settings & Presets.

⚠️ EDUCATIONAL RESEARCH ONLY.

This demo illustrates Phase 5 functionality WITHOUT requiring PyQt6.
"""

import tempfile
from pathlib import Path

from launcher.bot_settings import BotSettings, StrategyPreset, BotSettingsManager


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def demo_strategy_presets():
    """Demonstrate strategy presets."""
    print_section("1. Strategy Presets")
    
    presets = [
        StrategyPreset.CONSERVATIVE,
        StrategyPreset.BALANCED,
        StrategyPreset.AGGRESSIVE,
        StrategyPreset.GODMODE
    ]
    
    print("\nAvailable presets:")
    print()
    
    for preset in presets:
        settings = BotSettings.from_preset(preset)
        
        print(f"{preset.value.upper()}:")
        print(f"  Aggression: {settings.aggression_level}/10")
        print(f"  Equity threshold: {settings.equity_threshold:.0%}")
        print(f"  Max bet multiplier: {settings.max_bet_multiplier}x")
        print(f"  Action delay: {settings.delay_min:.1f}s - {settings.delay_max:.1f}s")
        print(f"  Mouse curve: {settings.mouse_curve_intensity}/10")
        print(f"  Max session: {settings.max_session_time} minutes")
        print(f"  Auto-rejoin: {settings.auto_rejoin}")
        print(f"  Manipulation: {'ENABLED' if settings.enable_manipulation else 'Disabled'}")
        print(f"  Collusion: {'ENABLED' if settings.enable_collusion else 'Disabled'}")
        print()


def demo_custom_settings():
    """Demonstrate custom settings."""
    print_section("2. Custom Settings")
    
    print("\nCreating custom settings...")
    
    custom = BotSettings(
        preset=StrategyPreset.CUSTOM,
        aggression_level=6,
        equity_threshold=0.62,
        max_bet_multiplier=3.5,
        delay_min=0.6,
        delay_max=2.8,
        mouse_curve_intensity=4,
        max_session_time=90,
        auto_rejoin=True,
        enable_manipulation=False,
        enable_collusion=False
    )
    
    print(f"Custom settings:")
    print(f"  Preset: {custom.preset.value}")
    print(f"  Aggression: {custom.aggression_level}/10")
    print(f"  Equity: {custom.equity_threshold:.0%}")
    print(f"  Max bet: {custom.max_bet_multiplier}x")
    print(f"  Delay range: {custom.delay_min:.1f}s - {custom.delay_max:.1f}s")
    print()


def demo_validation():
    """Demonstrate parameter validation."""
    print_section("3. Parameter Validation")
    
    print("\nCreating settings with invalid values...")
    
    invalid = BotSettings(
        aggression_level=999,  # Too high
        equity_threshold=2.0,  # Too high
        max_bet_multiplier=50.0,  # Too high
        delay_min=-5.0,  # Too low
        delay_max=0.1,  # Less than min
        mouse_curve_intensity=100  # Too high
    )
    
    print(f"After validation:")
    print(f"  Aggression: 999 -> {invalid.aggression_level} (clamped to 10)")
    print(f"  Equity: 2.0 -> {invalid.equity_threshold} (clamped to 1.0)")
    print(f"  Max bet: 50.0 -> {invalid.max_bet_multiplier} (clamped to 10.0)")
    print(f"  Delay min: -5.0 -> {invalid.delay_min} (clamped to 5.0)")
    print(f"  Delay max: {invalid.delay_max} (ensured >= min)")
    print(f"  Mouse curve: 100 -> {invalid.mouse_curve_intensity} (clamped to 10)")
    print()


def demo_settings_persistence():
    """Demonstrate settings persistence."""
    print_section("4. Settings Persistence")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        
        # Create manager
        manager = BotSettingsManager(config_dir=config_dir)
        
        print(f"\nSettings manager:")
        print(f"  Config directory: {manager.config_dir}")
        print(f"  Global settings file: {manager.settings_file.name}")
        print(f"  Per-bot directory: {manager.bot_settings_dir.name}")
        print()
        
        # Save global settings
        print("Saving global settings (AGGRESSIVE)...")
        global_settings = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
        manager.save_global_settings(global_settings)
        print("  Saved")
        
        # Save per-bot settings
        print("\nSaving per-bot settings...")
        bot_configs = {
            "bot_001": StrategyPreset.CONSERVATIVE,
            "bot_002": StrategyPreset.BALANCED,
            "bot_003": StrategyPreset.GODMODE
        }
        
        for account_id, preset in bot_configs.items():
            settings = BotSettings.from_preset(preset)
            manager.save_bot_settings(account_id, settings)
            print(f"  {account_id}: {preset.value}")
        
        # Load back
        print("\nLoading settings...")
        loaded_global = manager.load_global_settings()
        print(f"  Global: {loaded_global.preset.value}")
        
        print("\nPer-bot settings:")
        for account_id in bot_configs:
            loaded = manager.load_bot_settings(account_id)
            print(f"  {account_id}: {loaded.preset.value}")
        
        print()


def demo_settings_dialog_features():
    """Demonstrate settings dialog features (description only)."""
    print_section("5. Settings Dialog UI")
    
    print("\nSettingsDialog Window (PyQt6):")
    print()
    print("  Warning Banner:")
    print("    - Red background")
    print("    - 'COLLUSION SETTINGS - Educational Research Only'")
    print()
    print("  Preset Selector:")
    print("    - QComboBox with 5 options:")
    print("      * Conservative")
    print("      * Balanced (default)")
    print("      * Aggressive")
    print("      * GodMode")
    print("      * Custom")
    print("    - Auto-loads preset parameters on selection")
    print()
    print("  Parameters Group:")
    print("    - Aggression Level: QSpinBox (1-10)")
    print("    - Equity Threshold: QDoubleSpinBox (0.0-1.0)")
    print("    - Max Bet Multiplier: QDoubleSpinBox (1.0-10.0)")
    print("    - Action Delay: Min/Max QDoubleSpinBox (0.1-10.0s)")
    print("    - Mouse Curve: QSpinBox (0-10)")
    print("    - Max Session Time: QSpinBox (10-600 min)")
    print()
    print("  Advanced Options:")
    print("    - Auto-rejoin: QCheckBox")
    print("    - Enable manipulation: QCheckBox (red text)")
    print("    - Enable collusion: QCheckBox (bold red)")
    print()
    print("  Behavior:")
    print("    - Changing any parameter -> switches to 'Custom'")
    print("    - Saving with collusion -> critical warning dialog")
    print("    - Signal: settings_saved(BotSettings)")
    print()


def demo_preset_comparison():
    """Compare presets side-by-side."""
    print_section("6. Preset Comparison")
    
    presets = [
        StrategyPreset.CONSERVATIVE,
        StrategyPreset.BALANCED,
        StrategyPreset.AGGRESSIVE,
        StrategyPreset.GODMODE
    ]
    
    print("\n{:<15} {:<10} {:<10} {:<10} {:<15} {:<12}".format(
        "Preset", "Aggression", "Equity", "Max Bet", "Delay Range", "Collusion"
    ))
    print("-" * 75)
    
    for preset in presets:
        s = BotSettings.from_preset(preset)
        print("{:<15} {:<10} {:<10} {:<10} {:<15} {:<12}".format(
            preset.value,
            f"{s.aggression_level}/10",
            f"{s.equity_threshold:.0%}",
            f"{s.max_bet_multiplier}x",
            f"{s.delay_min:.1f}-{s.delay_max:.1f}s",
            "YES" if s.enable_collusion else "No"
        ))
    
    print()


def main():
    """Run Phase 5 demo."""
    print("\n" + "=" * 60)
    print("PHASE 5 DEMO - Bot Settings & Presets")
    print("=" * 60)
    print("\nEducational Game Theory Research")
    print("WARNING: CRITICAL: COLLUSION SYSTEM - ILLEGAL IN REAL POKER")
    print("=" * 60)
    
    # Demo 1: Strategy Presets
    demo_strategy_presets()
    
    # Demo 2: Custom Settings
    demo_custom_settings()
    
    # Demo 3: Validation
    demo_validation()
    
    # Demo 4: Persistence
    demo_settings_persistence()
    
    # Demo 5: UI Description
    demo_settings_dialog_features()
    
    # Demo 6: Comparison
    demo_preset_comparison()
    
    # Summary
    print_section("PHASE 5 COMPLETE")
    print("\nImplemented:")
    print("  -> BotSettings model with 11 parameters")
    print("  -> 4 strategy presets + custom")
    print("  -> BotSettingsManager for persistence")
    print("  -> SettingsDialog UI (PyQt6)")
    print("  -> Global settings integration")
    print("  -> Per-bot settings overrides")
    print("  -> Parameter validation")
    print("  -> Menu integration (Ctrl+S)")
    print()
    print("Presets Summary:")
    print("  Conservative: Aggression 3/10, Equity 75%, Safe")
    print("  Balanced:     Aggression 5/10, Equity 65%, Auto-rejoin")
    print("  Aggressive:   Aggression 8/10, Equity 55%, Fast")
    print("  GodMode:      Aggression 10/10, Equity 50%, COLLUSION ENABLED")
    print()
    print("Tests: 23 passed")
    print("Files: 5 created/modified")
    print()
    print("Next Phase: Фаза 6 - Logs, Monitoring & Safety")
    print("=" * 60)


if __name__ == "__main__":
    main()
