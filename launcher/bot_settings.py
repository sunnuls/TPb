"""
Bot Settings - Launcher Application (Roadmap6 Phase 5).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Global and per-bot configuration
- Strategy presets
- Behavioral parameters
- Session limits
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
from pathlib import Path


class StrategyPreset(str, Enum):
    """Strategy presets."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    GODMODE = "godmode"
    CUSTOM = "custom"


@dataclass
class BotSettings:
    """
    Bot configuration settings.
    
    Attributes:
        preset: Strategy preset
        aggression_level: Aggression level (1-10)
        equity_threshold: Equity threshold for aggression (0.0-1.0)
        max_bet_multiplier: Maximum bet size multiplier
        delay_min: Minimum action delay (seconds)
        delay_max: Maximum action delay (seconds)
        mouse_curve_intensity: Mouse movement curve intensity (0-10)
        max_session_time: Maximum session time (minutes)
        auto_rejoin: Auto-rejoin after disconnect
        enable_manipulation: Enable 3vs1 manipulation
        enable_collusion: Enable card sharing
    
    ⚠️ EDUCATIONAL NOTE:
        Configuration for coordinated bot behavior.
    """
    preset: StrategyPreset = StrategyPreset.BALANCED
    aggression_level: int = 5
    equity_threshold: float = 0.65
    max_bet_multiplier: float = 3.0
    delay_min: float = 0.4
    delay_max: float = 3.5
    mouse_curve_intensity: int = 5
    max_session_time: int = 120
    auto_rejoin: bool = False
    enable_manipulation: bool = False
    enable_collusion: bool = False
    
    def __post_init__(self):
        """Validate settings."""
        # Validate ranges
        self.aggression_level = max(1, min(10, self.aggression_level))
        self.equity_threshold = max(0.0, min(1.0, self.equity_threshold))
        self.max_bet_multiplier = max(1.0, min(10.0, self.max_bet_multiplier))
        self.delay_min = max(0.1, min(5.0, self.delay_min))
        self.delay_max = max(self.delay_min, min(10.0, self.delay_max))
        self.mouse_curve_intensity = max(0, min(10, self.mouse_curve_intensity))
        self.max_session_time = max(10, min(600, self.max_session_time))
    
    @classmethod
    def from_preset(cls, preset: StrategyPreset) -> 'BotSettings':
        """
        Create settings from preset.
        
        Args:
            preset: Strategy preset
        
        Returns:
            Bot settings configured for preset
        """
        if preset == StrategyPreset.CONSERVATIVE:
            return cls(
                preset=preset,
                aggression_level=3,
                equity_threshold=0.75,
                max_bet_multiplier=2.0,
                delay_min=1.0,
                delay_max=4.0,
                mouse_curve_intensity=7,
                max_session_time=90,
                auto_rejoin=False,
                enable_manipulation=False,
                enable_collusion=False
            )
        
        elif preset == StrategyPreset.BALANCED:
            return cls(
                preset=preset,
                aggression_level=5,
                equity_threshold=0.65,
                max_bet_multiplier=3.0,
                delay_min=0.4,
                delay_max=3.5,
                mouse_curve_intensity=5,
                max_session_time=120,
                auto_rejoin=True,
                enable_manipulation=False,
                enable_collusion=False
            )
        
        elif preset == StrategyPreset.AGGRESSIVE:
            return cls(
                preset=preset,
                aggression_level=8,
                equity_threshold=0.55,
                max_bet_multiplier=5.0,
                delay_min=0.2,
                delay_max=2.0,
                mouse_curve_intensity=3,
                max_session_time=150,
                auto_rejoin=True,
                enable_manipulation=False,
                enable_collusion=False
            )
        
        elif preset == StrategyPreset.GODMODE:
            return cls(
                preset=preset,
                aggression_level=10,
                equity_threshold=0.50,
                max_bet_multiplier=10.0,
                delay_min=0.1,
                delay_max=1.0,
                mouse_curve_intensity=1,
                max_session_time=180,
                auto_rejoin=True,
                enable_manipulation=True,
                enable_collusion=True
            )
        
        else:  # CUSTOM
            return cls(preset=preset)
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'preset': self.preset.value,
            'aggression_level': self.aggression_level,
            'equity_threshold': self.equity_threshold,
            'max_bet_multiplier': self.max_bet_multiplier,
            'delay_min': self.delay_min,
            'delay_max': self.delay_max,
            'mouse_curve_intensity': self.mouse_curve_intensity,
            'max_session_time': self.max_session_time,
            'auto_rejoin': self.auto_rejoin,
            'enable_manipulation': self.enable_manipulation,
            'enable_collusion': self.enable_collusion
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BotSettings':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
        
        Returns:
            Bot settings instance
        """
        return cls(
            preset=StrategyPreset(data.get('preset', 'balanced')),
            aggression_level=data.get('aggression_level', 5),
            equity_threshold=data.get('equity_threshold', 0.65),
            max_bet_multiplier=data.get('max_bet_multiplier', 3.0),
            delay_min=data.get('delay_min', 0.4),
            delay_max=data.get('delay_max', 3.5),
            mouse_curve_intensity=data.get('mouse_curve_intensity', 5),
            max_session_time=data.get('max_session_time', 120),
            auto_rejoin=data.get('auto_rejoin', False),
            enable_manipulation=data.get('enable_manipulation', False),
            enable_collusion=data.get('enable_collusion', False)
        )


class BotSettingsManager:
    """
    Manages bot settings persistence.
    
    Features:
    - Save/load global settings
    - Save/load per-bot settings
    - Preset management
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize settings manager.
        
        Args:
            config_dir: Configuration directory
        """
        if config_dir is None:
            config_dir = Path("config")
        
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "bot_settings.json"
        self.bot_settings_dir = self.config_dir / "bot_settings"
        
        # Create directories
        self.config_dir.mkdir(exist_ok=True)
        self.bot_settings_dir.mkdir(exist_ok=True)
        
        # Global settings
        self.global_settings = BotSettings()
    
    def save_global_settings(self, settings: BotSettings) -> bool:
        """
        Save global settings.
        
        Args:
            settings: Bot settings
        
        Returns:
            True if successful
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings.to_dict(), f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Failed to save global settings: {e}")
            return False
    
    def load_global_settings(self) -> BotSettings:
        """
        Load global settings.
        
        Returns:
            Bot settings (default if not found)
        """
        if not self.settings_file.exists():
            return BotSettings()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return BotSettings.from_dict(data)
        
        except Exception as e:
            print(f"Failed to load global settings: {e}")
            return BotSettings()
    
    def save_bot_settings(self, account_id: str, settings: BotSettings) -> bool:
        """
        Save per-bot settings.
        
        Args:
            account_id: Account ID
            settings: Bot settings
        
        Returns:
            True if successful
        """
        try:
            settings_file = self.bot_settings_dir / f"settings_{account_id}.json"
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings.to_dict(), f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Failed to save bot settings: {e}")
            return False
    
    def load_bot_settings(self, account_id: str) -> Optional[BotSettings]:
        """
        Load per-bot settings.
        
        Args:
            account_id: Account ID
        
        Returns:
            Bot settings if found
        """
        settings_file = self.bot_settings_dir / f"settings_{account_id}.json"
        
        if not settings_file.exists():
            return None
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return BotSettings.from_dict(data)
        
        except Exception as e:
            print(f"Failed to load bot settings: {e}")
            return None


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Bot Settings - Educational Research")
    print("=" * 60)
    print()
    
    # Demonstrate presets
    print("Strategy Presets:")
    print()
    
    for preset in [StrategyPreset.CONSERVATIVE, StrategyPreset.BALANCED, 
                   StrategyPreset.AGGRESSIVE, StrategyPreset.GODMODE]:
        settings = BotSettings.from_preset(preset)
        print(f"{preset.value.upper()}:")
        print(f"  Aggression: {settings.aggression_level}/10")
        print(f"  Equity threshold: {settings.equity_threshold:.0%}")
        print(f"  Max bet: {settings.max_bet_multiplier}x")
        print(f"  Delay: {settings.delay_min:.1f}s - {settings.delay_max:.1f}s")
        print(f"  Mouse curve: {settings.mouse_curve_intensity}/10")
        print(f"  Max session: {settings.max_session_time} min")
        print(f"  Auto-rejoin: {settings.auto_rejoin}")
        print(f"  Manipulation: {settings.enable_manipulation}")
        print(f"  Collusion: {settings.enable_collusion}")
        print()
    
    # Settings manager
    manager = BotSettingsManager(Path("config_test"))
    
    print("Settings Manager:")
    print(f"  Config dir: {manager.config_dir}")
    print(f"  Settings file: {manager.settings_file}")
    print()
    
    # Save and load
    test_settings = BotSettings.from_preset(StrategyPreset.AGGRESSIVE)
    manager.save_global_settings(test_settings)
    
    loaded = manager.load_global_settings()
    print(f"Loaded settings: {loaded.preset.value}, aggression={loaded.aggression_level}")
    print()
    
    # Cleanup
    manager.settings_file.unlink(missing_ok=True)
    manager.bot_settings_dir.rmdir()
    manager.config_dir.rmdir()
    
    print("=" * 60)
    print("Bot settings demonstration complete")
    print("=" * 60)
