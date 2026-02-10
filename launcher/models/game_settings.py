"""
Game Settings Model - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Game type preferences (Hold'em, PLO, etc.)
- Stake limits
- Table type preferences
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class GameType(Enum):
    """Supported game types."""
    HOLDEM = "Hold'em"
    PLO = "PLO"
    OMAHA = "Omaha"
    RUSH_AND_CASH = "Rush & Cash"
    SPIN_GOLD = "Spin Gold"
    MYSTERY_BOUNTY = "Mystery Bounty"
    EXCLUSIVE = "Exclusive"
    TOURNAMENT = "Tournament"
    FLIPNGO = "Flip&Go"
    BATTLE_ROYALE = "Battle Royale"
    APL = "APL"
    WSOP_EXPRESS = "WSOP Express"


class StakeLevel(Enum):
    """Stake level categories."""
    MICRO = "Micro"  # $0.01/$0.02 - $0.10/$0.25
    LOW = "Low"  # $0.25/$0.50 - $1/$2
    MEDIUM = "Medium"  # $2/$5 - $5/$10
    HIGH = "High"  # $10/$20+


@dataclass
class GamePreferences:
    """
    Game preferences for a bot.
    
    Attributes:
        enabled_games: List of enabled game types
        min_stake: Minimum stake (e.g., "$0.10/$0.25")
        max_stake: Maximum stake (e.g., "$5/$10")
        stake_levels: Preferred stake levels
        min_players: Minimum players at table (for auto-join)
        max_players: Maximum players at table
        preferred_table_size: Preferred table size (2, 6, 9, etc.)
        auto_join_tables: Auto join tables matching criteria
        max_tables: Maximum simultaneous tables per bot
    """
    enabled_games: List[GameType] = field(default_factory=lambda: [GameType.HOLDEM])
    min_stake: str = "$0.10/$0.25"
    max_stake: str = "$1/$2"
    stake_levels: List[StakeLevel] = field(default_factory=lambda: [StakeLevel.MICRO, StakeLevel.LOW])
    
    # Table selection criteria
    min_players: int = 1  # Prefer tables with 1-3 human players (for 3vs1 collusion)
    max_players: int = 3
    preferred_table_size: int = 6  # 6-max or 9-max
    
    # Auto-join settings
    auto_join_tables: bool = True
    max_tables: int = 1  # How many tables this bot can play simultaneously
    
    # Additional filters
    avoid_full_bot_tables: bool = True  # Don't join tables with only bots
    prefer_weak_players: bool = True  # Use player stats to find weak opponents
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'enabled_games': [game.value for game in self.enabled_games],
            'min_stake': self.min_stake,
            'max_stake': self.max_stake,
            'stake_levels': [level.value for level in self.stake_levels],
            'min_players': self.min_players,
            'max_players': self.max_players,
            'preferred_table_size': self.preferred_table_size,
            'auto_join_tables': self.auto_join_tables,
            'max_tables': self.max_tables,
            'avoid_full_bot_tables': self.avoid_full_bot_tables,
            'prefer_weak_players': self.prefer_weak_players
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GamePreferences':
        """Create from dictionary."""
        enabled_games = [GameType(g) for g in data.get('enabled_games', ['Hold\'em'])]
        stake_levels = [StakeLevel(s) for s in data.get('stake_levels', ['Micro', 'Low'])]
        
        return cls(
            enabled_games=enabled_games,
            min_stake=data.get('min_stake', '$0.10/$0.25'),
            max_stake=data.get('max_stake', '$1/$2'),
            stake_levels=stake_levels,
            min_players=data.get('min_players', 1),
            max_players=data.get('max_players', 3),
            preferred_table_size=data.get('preferred_table_size', 6),
            auto_join_tables=data.get('auto_join_tables', True),
            max_tables=data.get('max_tables', 1),
            avoid_full_bot_tables=data.get('avoid_full_bot_tables', True),
            prefer_weak_players=data.get('prefer_weak_players', True)
        )


# Predefined stake configurations
STAKE_PRESETS = {
    'Micro Stakes': {
        'min_stake': '$0.01/$0.02',
        'max_stake': '$0.10/$0.25',
        'levels': [StakeLevel.MICRO]
    },
    'Low Stakes': {
        'min_stake': '$0.25/$0.50',
        'max_stake': '$1/$2',
        'levels': [StakeLevel.LOW]
    },
    'Medium Stakes': {
        'min_stake': '$2/$5',
        'max_stake': '$5/$10',
        'levels': [StakeLevel.MEDIUM]
    },
    'Mixed (Micro + Low)': {
        'min_stake': '$0.10/$0.25',
        'max_stake': '$1/$2',
        'levels': [StakeLevel.MICRO, StakeLevel.LOW]
    }
}


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Game Settings - Educational Research")
    print("=" * 60)
    print()
    
    # Create default preferences
    prefs = GamePreferences()
    
    print("Default Game Preferences:")
    print(f"  Enabled games: {[g.value for g in prefs.enabled_games]}")
    print(f"  Stakes: {prefs.min_stake} - {prefs.max_stake}")
    print(f"  Player range: {prefs.min_players}-{prefs.max_players}")
    print(f"  Auto-join: {prefs.auto_join_tables}")
    print()
    
    # Custom configuration
    custom = GamePreferences(
        enabled_games=[GameType.HOLDEM, GameType.PLO],
        min_stake="$0.25/$0.50",
        max_stake="$2/$5",
        min_players=1,
        max_players=3,
        max_tables=2
    )
    
    print("Custom Configuration:")
    print(f"  Enabled games: {[g.value for g in custom.enabled_games]}")
    print(f"  Stakes: {custom.min_stake} - {custom.max_stake}")
    print(f"  Max tables: {custom.max_tables}")
    print()
    
    print("=" * 60)
