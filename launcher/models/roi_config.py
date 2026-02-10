"""
ROI Configuration Model - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class ROIZone:
    """
    Region of Interest zone.
    
    Attributes:
        name: Zone name (e.g., "hero_card_1", "pot", "fold_button")
        x: X coordinate
        y: Y coordinate
        width: Width
        height: Height
    """
    name: str
    x: int
    y: int
    width: int
    height: int
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ROIZone':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height']
        )


@dataclass
class ROIConfig:
    """
    Complete ROI configuration for account.
    
    Attributes:
        account_id: Associated account ID
        resolution: Window resolution (width, height)
        zones: Dict of zone_name -> ROIZone
        configured_at: Configuration timestamp
    
    Standard zones:
    - hero_card_1, hero_card_2: Hero hole cards
    - board_card_1 to board_card_5: Community cards
    - pot: Pot amount
    - stack_1 to stack_9: Player stacks
    - fold_button, check_button, call_button: Action buttons
    - raise_button, bet_input: Bet/raise controls
    """
    account_id: str
    resolution: Tuple[int, int] = (1920, 1080)
    zones: Dict[str, ROIZone] = field(default_factory=dict)
    configured_at: Optional[float] = None
    
    def add_zone(self, zone: ROIZone) -> None:
        """
        Add ROI zone.
        
        Args:
            zone: ROI zone to add
        """
        self.zones[zone.name] = zone
    
    def get_zone(self, name: str) -> Optional[ROIZone]:
        """
        Get ROI zone by name.
        
        Args:
            name: Zone name
        
        Returns:
            ROIZone if found
        """
        return self.zones.get(name)
    
    def has_required_zones(self) -> bool:
        """
        Check if all required zones are configured.
        
        Returns:
            True if complete
        """
        required = [
            'hero_card_1',
            'hero_card_2',
            'pot',
            'fold_button',
            'call_button'
        ]
        
        return all(name in self.zones for name in required)
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'account_id': self.account_id,
            'resolution': self.resolution,
            'zones': {
                name: zone.to_dict()
                for name, zone in self.zones.items()
            },
            'configured_at': self.configured_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ROIConfig':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
        
        Returns:
            ROIConfig instance
        """
        zones_data = data.get('zones', {})
        zones = {
            name: ROIZone.from_dict(zone_data)
            for name, zone_data in zones_data.items()
        }
        
        return cls(
            account_id=data['account_id'],
            resolution=tuple(data.get('resolution', (1920, 1080))),
            zones=zones,
            configured_at=data.get('configured_at')
        )


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("ROI Config Model - Educational Research")
    print("=" * 60)
    print()
    
    # Create config
    config = ROIConfig(
        account_id="test_account_001",
        resolution=(1920, 1080)
    )
    
    print(f"ROI Config created:")
    print(f"  Account: {config.account_id}")
    print(f"  Resolution: {config.resolution}")
    print(f"  Zones: {len(config.zones)}")
    print()
    
    # Add zones
    config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    config.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
    config.add_zone(ROIZone("pot", 500, 100, 100, 30))
    config.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
    config.add_zone(ROIZone("call_button", 490, 800, 80, 40))
    
    print(f"After adding zones:")
    print(f"  Zones: {len(config.zones)}")
    print(f"  Has required zones: {config.has_required_zones()}")
    print()
    
    # List zones
    print("Configured zones:")
    for name, zone in config.zones.items():
        print(f"  {name}: ({zone.x}, {zone.y}, {zone.width}, {zone.height})")
    print()
    
    # Convert to dict
    data = config.to_dict()
    print(f"Config as dict: {len(data)} fields, {len(data['zones'])} zones")
    print()
    
    print("=" * 60)
    print("ROI config demonstration complete")
    print("=" * 60)
