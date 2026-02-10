"""
ROI (Region of Interest) Manager for HCI Research (Roadmap3 Phase 1).

EDUCATIONAL USE ONLY: This module manages dynamic ROI loading for screen
capture regions in external desktop application research.

DRY-RUN MODE: All operations are simulated by default.

WARNING: This is a research prototype. Real-world use is PROHIBITED.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from bridge.safety import get_safety

logger = logging.getLogger(__name__)


@dataclass
class ROI:
    """
    Region of Interest definition.
    
    Attributes:
        name: ROI identifier (e.g., "hero_cards", "pot")
        x: X coordinate (pixels)
        y: Y coordinate (pixels)
        width: Width (pixels)
        height: Height (pixels)
        description: Optional description
    """
    name: str
    x: int
    y: int
    width: int
    height: int
    description: str = ""
    
    def as_tuple(self) -> Tuple[int, int, int, int]:
        """Return as (x, y, width, height) tuple."""
        return (self.x, self.y, self.width, self.height)
    
    def as_dict(self) -> Dict:
        """Return as dictionary."""
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'description': self.description
        }


class ROIManager:
    """
    Dynamic ROI manager for HCI research.
    
    Features:
    - Load ROI presets from YAML/JSON
    - Per-room and per-resolution configurations
    - Runtime ROI adjustment
    - DRY-RUN mode support
    
    EDUCATIONAL NOTE:
        This class manages screen regions for capturing specific UI elements
        from external applications. Used for HCI research only.
    """
    
    def __init__(self, config_path: str = "bridge/config/live_config.yaml"):
        """
        Initialize ROI manager.
        
        Args:
            config_path: Path to configuration file with ROI presets
        """
        self.config_path = Path(config_path)
        self.roi_presets: Dict[str, Dict] = {}
        self.current_room: Optional[str] = None
        self.current_resolution: Optional[str] = None
        self.current_rois: Dict[str, ROI] = {}
        
        # Load configuration
        self._load_config()
        
        logger.info(f"ROIManager initialized (DRY-RUN: {get_safety().is_dry_run()})")
    
    def _load_config(self) -> None:
        """Load ROI configuration from file."""
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Extract ROI presets
            if 'roi_presets' in config:
                self.roi_presets = config['roi_presets']
                logger.info(f"Loaded ROI presets for {len(self.roi_presets)} rooms")
            else:
                logger.warning("No ROI presets found in configuration")
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def list_available_rooms(self) -> List[str]:
        """
        List available room configurations.
        
        Returns:
            List of room names
        """
        return list(self.roi_presets.keys())
    
    def list_available_resolutions(self, room: str) -> List[str]:
        """
        List available resolutions for a room.
        
        Args:
            room: Room name
            
        Returns:
            List of resolution strings (e.g., "1920x1080")
        """
        if room not in self.roi_presets:
            logger.warning(f"Room not found: {room}")
            return []
        
        return list(self.roi_presets[room].keys())
    
    def load_roi_set(self, room: str, resolution: str) -> bool:
        """
        Load ROI set for specific room and resolution.
        
        Args:
            room: Room name (e.g., "pokerstars_6max")
            resolution: Resolution string (e.g., "1920x1080")
            
        Returns:
            True if successful, False otherwise
            
        EDUCATIONAL NOTE:
            Loads pre-configured screen regions for specific game room layout.
        """
        # Check if room exists
        if room not in self.roi_presets:
            logger.error(f"Room configuration not found: {room}")
            logger.info(f"Available rooms: {self.list_available_rooms()}")
            return False
        
        # Check if resolution exists
        if resolution not in self.roi_presets[room]:
            logger.error(f"Resolution not found for {room}: {resolution}")
            logger.info(f"Available resolutions: {self.list_available_resolutions(room)}")
            return False
        
        # Load ROIs
        roi_config = self.roi_presets[room][resolution]
        self.current_rois = {}
        
        # Parse ROI configurations
        for key, value in roi_config.items():
            if isinstance(value, dict) and all(k in value for k in ['x', 'y', 'width', 'height']):
                # Single ROI
                roi = ROI(
                    name=key,
                    x=value['x'],
                    y=value['y'],
                    width=value['width'],
                    height=value['height'],
                    description=value.get('name', key)
                )
                self.current_rois[key] = roi
            
            elif isinstance(value, list):
                # Multiple ROIs (e.g., stacks, buttons)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        roi_name = f"{key}_{i}"
                        if 'name' in item:
                            roi_name = item['name']
                        
                        roi = ROI(
                            name=roi_name,
                            x=item['x'],
                            y=item['y'],
                            width=item['width'],
                            height=item['height'],
                            description=f"{key} {i+1}"
                        )
                        self.current_rois[roi_name] = roi
        
        self.current_room = room
        self.current_resolution = resolution
        
        logger.info(f"Loaded {len(self.current_rois)} ROIs for {room} @ {resolution}")
        
        return True
    
    def get_roi(self, name: str) -> Optional[ROI]:
        """
        Get specific ROI by name.
        
        Args:
            name: ROI name (e.g., "hero_cards", "pot")
            
        Returns:
            ROI object or None if not found
        """
        if name not in self.current_rois:
            logger.warning(f"ROI not found: {name}")
            logger.debug(f"Available ROIs: {list(self.current_rois.keys())}")
            return None
        
        return self.current_rois[name]
    
    def get_all_rois(self) -> Dict[str, ROI]:
        """
        Get all loaded ROIs.
        
        Returns:
            Dictionary of ROI name -> ROI object
        """
        return self.current_rois.copy()
    
    def get_roi_tuple(self, name: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Get ROI as (x, y, width, height) tuple.
        
        Args:
            name: ROI name
            
        Returns:
            Tuple or None if not found
        """
        roi = self.get_roi(name)
        return roi.as_tuple() if roi else None
    
    def add_custom_roi(self, name: str, x: int, y: int, width: int, height: int) -> None:
        """
        Add custom ROI at runtime.
        
        Args:
            name: ROI name
            x: X coordinate
            y: Y coordinate
            width: Width
            height: Height
        """
        roi = ROI(name=name, x=x, y=y, width=width, height=height)
        self.current_rois[name] = roi
        
        logger.info(f"Added custom ROI: {name} @ ({x}, {y}, {width}, {height})")
    
    def save_custom_rois(self, output_path: str) -> bool:
        """
        Save current ROI set to JSON file.
        
        Args:
            output_path: Output file path
            
        Returns:
            True if successful
            
        EDUCATIONAL NOTE:
            Allows researchers to save custom ROI configurations.
        """
        try:
            # Convert ROIs to dict
            rois_dict = {
                'room': self.current_room,
                'resolution': self.current_resolution,
                'rois': {name: roi.as_dict() for name, roi in self.current_rois.items()}
            }
            
            # Save to JSON
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(rois_dict, f, indent=2)
            
            logger.info(f"Saved {len(self.current_rois)} ROIs to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save ROIs: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """
        Get ROI manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'current_room': self.current_room,
            'current_resolution': self.current_resolution,
            'loaded_rois': len(self.current_rois),
            'available_rooms': len(self.roi_presets),
            'dry_run': get_safety().is_dry_run()
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("HCI Research - ROI Manager Demo (DRY-RUN)")
    print("=" * 60)
    print()
    
    # Initialize in dry-run mode
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
    SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    
    # Create ROI manager
    manager = ROIManager()
    
    # List available rooms
    print("Available rooms:")
    for room in manager.list_available_rooms():
        resolutions = manager.list_available_resolutions(room)
        print(f"  {room}: {resolutions}")
    print()
    
    # Load ROI set
    print("Loading ROI set for pokerstars_6max @ 1920x1080...")
    success = manager.load_roi_set("pokerstars_6max", "1920x1080")
    print(f"  Success: {success}")
    print()
    
    # List loaded ROIs
    print("Loaded ROIs:")
    for name, roi in manager.get_all_rois().items():
        print(f"  {name}: ({roi.x}, {roi.y}, {roi.width}, {roi.height})")
    print()
    
    # Get specific ROI
    print("Getting 'hero_cards' ROI:")
    hero_roi = manager.get_roi("hero_cards")
    if hero_roi:
        print(f"  {hero_roi.name}: {hero_roi.as_tuple()}")
    print()
    
    # Statistics
    stats = manager.get_statistics()
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode active")
    print("=" * 60)
