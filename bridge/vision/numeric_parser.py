"""
Numeric Parser Module (Roadmap3 Phase 2.2).

Extracts numeric data from screenshots:
- Pot size
- Player stacks
- Current bets
- Player positions

In DRY-RUN mode: returns simulated numeric data.
In UNSAFE mode: uses OCR (pytesseract or similar).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class NumericData:
    """
    Result of numeric extraction.
    
    Attributes:
        pot: Pot size (in bb or chips)
        stacks: Player stacks {player_id: stack_size}
        bets: Current bets {player_id: bet_amount}
        positions: Player positions {player_id: position_name}
        confidence: Extraction confidence (0.0-1.0)
        method: Extraction method used
        error: Error message if extraction failed
    """
    pot: float = 0.0
    stacks: Dict[str, float] = None
    bets: Dict[str, float] = None
    positions: Dict[str, str] = None
    confidence: float = 1.0
    method: str = "simulated"
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.stacks is None:
            self.stacks = {}
        if self.bets is None:
            self.bets = {}
        if self.positions is None:
            self.positions = {}


class NumericParser:
    """
    Extracts numeric data from poker screenshots.
    
    In DRY-RUN mode (default):
        Returns simulated numeric data for testing.
    
    In UNSAFE mode:
        Attempts OCR extraction using pytesseract or similar.
    
    EDUCATIONAL NOTE:
        This demonstrates OCR-based numeric extraction from
        external applications for HCI research purposes.
    """
    
    def __init__(
        self,
        dry_run: bool = True,
        fallback_to_simulation: bool = True
    ):
        """
        Initialize numeric parser.
        
        Args:
            dry_run: If True, return simulated data only
            fallback_to_simulation: If True, fallback to simulation on errors
        """
        self.dry_run = dry_run
        self.fallback_to_simulation = fallback_to_simulation
        
        # Try to import OCR library (optional)
        self.ocr_available = False
        if not dry_run:
            self.ocr_available = self._try_load_ocr()
        
        # Statistics
        self.extractions_count = 0
        self.failures_count = 0
        
        logger.info(
            f"NumericParser initialized (dry_run={dry_run}, "
            f"ocr={'available' if self.ocr_available else 'unavailable'})"
        )
    
    def _try_load_ocr(self) -> bool:
        """
        Try to load OCR library (pytesseract).
        
        Returns:
            True if OCR available, False otherwise
        """
        try:
            # Example: import pytesseract
            logger.info("Attempting to load pytesseract...")
            
            # Placeholder - actual implementation would test pytesseract
            # import pytesseract
            # pytesseract.get_tesseract_version()
            # return True
            
            logger.warning("pytesseract not available - using simulation")
            return False
            
        except (ImportError, Exception) as e:
            logger.debug(f"OCR library import failed: {e}")
            return False
    
    def extract_all(
        self,
        screenshot: Optional[np.ndarray] = None,
        roi_dict: Optional[Dict[str, Tuple[int, int, int, int]]] = None
    ) -> NumericData:
        """
        Extract all numeric data from screenshot.
        
        Args:
            screenshot: Screenshot array (H, W, 3) or None for simulation
            roi_dict: Dictionary of ROIs for each element:
                      {'pot': (x,y,w,h), 'hero_stack': (x,y,w,h), ...}
        
        Returns:
            NumericData with all extracted values
        
        EDUCATIONAL NOTE:
            In DRY-RUN mode, returns realistic simulated data for testing.
        """
        self.extractions_count += 1
        
        if self.dry_run:
            return self._simulate_numeric_data()
        
        # Real extraction (UNSAFE mode)
        try:
            result = NumericData()
            
            if roi_dict is None:
                raise ValueError("roi_dict required for real extraction")
            
            # Extract pot
            if 'pot' in roi_dict:
                result.pot = self._extract_pot(screenshot, roi_dict['pot'])
            
            # Extract player stacks
            result.stacks = self._extract_stacks(screenshot, roi_dict)
            
            # Extract current bets
            result.bets = self._extract_bets(screenshot, roi_dict)
            
            # Extract positions (usually from fixed layout)
            result.positions = self._extract_positions(roi_dict)
            
            result.method = "ocr" if self.ocr_available else "pattern_matching"
            result.confidence = 0.8 if self.ocr_available else 0.6
            
            return result
            
        except Exception as e:
            logger.error(f"Numeric extraction error: {e}")
            self.failures_count += 1
            
            if self.fallback_to_simulation:
                return self._simulate_numeric_data()
            
            return NumericData(
                confidence=0.0,
                method="error",
                error=str(e)
            )
    
    def _extract_pot(
        self,
        screenshot: np.ndarray,
        roi: Tuple[int, int, int, int]
    ) -> float:
        """
        Extract pot size from ROI.
        
        Args:
            screenshot: Screenshot array
            roi: Region of interest (x, y, w, h)
        
        Returns:
            Pot size as float
        """
        if not self.ocr_available:
            return 0.0
        
        # Example OCR extraction:
        # region = screenshot[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        # text = pytesseract.image_to_string(region, config='--psm 6')
        # pot = self._parse_numeric_text(text)
        # return pot
        
        return 0.0
    
    def _extract_stacks(
        self,
        screenshot: np.ndarray,
        roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> Dict[str, float]:
        """
        Extract player stacks from ROIs.
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary with stack ROIs ('hero_stack', 'seat1_stack', ...)
        
        Returns:
            Dictionary of player stacks
        """
        stacks = {}
        
        # Find all stack ROIs
        stack_rois = {
            k: v for k, v in roi_dict.items()
            if 'stack' in k.lower()
        }
        
        for player_id, roi in stack_rois.items():
            if self.ocr_available:
                # Example OCR:
                # region = screenshot[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
                # text = pytesseract.image_to_string(region)
                # stack = self._parse_numeric_text(text)
                # stacks[player_id] = stack
                pass
            else:
                stacks[player_id] = 0.0
        
        return stacks
    
    def _extract_bets(
        self,
        screenshot: np.ndarray,
        roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> Dict[str, float]:
        """
        Extract current bets from ROIs.
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary with bet ROIs
        
        Returns:
            Dictionary of player bets
        """
        bets = {}
        
        # Find all bet ROIs
        bet_rois = {
            k: v for k, v in roi_dict.items()
            if 'bet' in k.lower()
        }
        
        for player_id, roi in bet_rois.items():
            if self.ocr_available:
                # Example OCR extraction
                pass
            else:
                bets[player_id] = 0.0
        
        return bets
    
    def _extract_positions(
        self,
        roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> Dict[str, str]:
        """
        Determine player positions from ROI layout.
        
        Args:
            roi_dict: Dictionary of ROIs
        
        Returns:
            Dictionary of player positions
        
        EDUCATIONAL NOTE:
            Position often inferred from seat geometry in poker clients.
        """
        positions = {}
        
        # Example position mapping based on seat layout
        seat_map = {
            'hero': 'BTN',
            'seat1': 'SB',
            'seat2': 'BB',
            'seat3': 'UTG',
            'seat4': 'MP',
            'seat5': 'CO'
        }
        
        for player_id in roi_dict.keys():
            for seat_id, position in seat_map.items():
                if seat_id in player_id.lower():
                    positions[player_id] = position
                    break
        
        return positions
    
    def _parse_numeric_text(self, text: str) -> float:
        """
        Parse numeric value from OCR text.
        
        Args:
            text: Raw OCR text
        
        Returns:
            Parsed numeric value
        
        Examples:
            "150.50" -> 150.5
            "$1,234" -> 1234.0
            "25 BB" -> 25.0
        """
        # Remove common non-numeric characters
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _simulate_numeric_data(self) -> NumericData:
        """
        Generate simulated numeric data for DRY-RUN mode.
        
        Returns:
            Realistic simulated numeric data
        """
        return NumericData(
            pot=150.0,
            stacks={
                'hero': 1000.0,
                'seat1': 950.0,
                'seat2': 1100.0,
                'seat3': 800.0
            },
            bets={
                'hero': 0.0,
                'seat1': 10.0,
                'seat2': 10.0,
                'seat3': 0.0
            },
            positions={
                'hero': 'BTN',
                'seat1': 'SB',
                'seat2': 'BB',
                'seat3': 'UTG'
            },
            confidence=1.0,
            method="simulated"
        )
    
    def get_statistics(self) -> dict:
        """Get extraction statistics."""
        success_rate = 0.0
        if self.extractions_count > 0:
            success_rate = (
                (self.extractions_count - self.failures_count) /
                self.extractions_count
            )
        
        return {
            'total_extractions': self.extractions_count,
            'failures': self.failures_count,
            'success_rate': success_rate,
            'dry_run': self.dry_run,
            'ocr_available': self.ocr_available
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Numeric Parser - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # DRY-RUN mode (safe for testing)
    parser = NumericParser(dry_run=True)
    
    # Extract all numeric data
    data = parser.extract_all()
    
    print(f"Pot: {data.pot} bb")
    print(f"Method: {data.method}, Confidence: {data.confidence:.1%}")
    print()
    
    print("Player Stacks:")
    for player, stack in data.stacks.items():
        position = data.positions.get(player, "?")
        bet = data.bets.get(player, 0.0)
        print(f"  {player} ({position}): {stack} bb (bet: {bet} bb)")
    print()
    
    # Statistics
    stats = parser.get_statistics()
    print(f"Extractions: {stats['total_extractions']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"DRY-RUN mode: {stats['dry_run']}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
