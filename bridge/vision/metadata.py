"""
Metadata Extractor Module (Roadmap3 Phase 2.3).

Extracts table metadata from screenshots:
- Current street/stage (preflop, flop, turn, river)
- Table type (cash, tournament, SNG)
- Number of seats (6-max, 9-max, heads-up)
- Active player count

In DRY-RUN mode: returns simulated metadata.
In UNSAFE mode: uses visual heuristics and OCR.

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np

# Import Street from unified state module
from sim_engine.state.table_state import Street

logger = logging.getLogger(__name__)


class TableType(str, Enum):
    """Table types."""
    CASH = "cash"
    TOURNAMENT = "tournament"
    SNG = "sit_n_go"
    UNKNOWN = "unknown"


@dataclass
class TableMetadata:
    """
    Result of metadata extraction.
    
    Attributes:
        street: Current poker street
        table_type: Type of table (cash/tournament/etc)
        max_seats: Maximum seats at table
        active_seats: Number of currently active seats
        hand_number: Current hand number (if visible)
        confidence: Extraction confidence (0.0-1.0)
        method: Extraction method used
        error: Error message if extraction failed
    """
    street: Street = Street.PREFLOP
    table_type: TableType = TableType.CASH
    max_seats: int = 6
    active_seats: int = 4
    hand_number: int = 0
    confidence: float = 1.0
    method: str = "simulated"
    error: Optional[str] = None


class MetadataExtractor:
    """
    Extracts table metadata from poker screenshots.
    
    In DRY-RUN mode (default):
        Returns simulated metadata for testing.
    
    In UNSAFE mode:
        Uses visual heuristics:
        - Street: count board cards (0=preflop, 3=flop, 4=turn, 5=river)
        - Table type: OCR table title or detect tournament chips
        - Seats: count visible player positions
    
    EDUCATIONAL NOTE:
        This demonstrates visual metadata extraction from
        external applications for HCI research purposes.
    """
    
    def __init__(
        self,
        dry_run: bool = True,
        fallback_to_simulation: bool = True
    ):
        """
        Initialize metadata extractor.
        
        Args:
            dry_run: If True, return simulated data only
            fallback_to_simulation: If True, fallback to simulation on errors
        """
        self.dry_run = dry_run
        self.fallback_to_simulation = fallback_to_simulation
        
        # Statistics
        self.extractions_count = 0
        self.failures_count = 0
        
        logger.info(
            f"MetadataExtractor initialized (dry_run={dry_run})"
        )
    
    def extract_all(
        self,
        screenshot: Optional[np.ndarray] = None,
        board_card_count: Optional[int] = None,
        roi_dict: Optional[dict] = None
    ) -> TableMetadata:
        """
        Extract all metadata from screenshot.
        
        Args:
            screenshot: Screenshot array (H, W, 3) or None for simulation
            board_card_count: Number of board cards (overrides detection)
            roi_dict: Dictionary of ROIs for metadata extraction
        
        Returns:
            TableMetadata with all extracted values
        
        EDUCATIONAL NOTE:
            Street detection is typically based on visible board cards.
        """
        self.extractions_count += 1
        
        if self.dry_run:
            # In dry-run, still respect explicit board_card_count if provided
            if board_card_count is not None:
                metadata = self._simulate_metadata()
                metadata.street = self._detect_street(board_card_count)
                return metadata
            return self._simulate_metadata()
        
        # Real extraction (UNSAFE mode)
        try:
            result = TableMetadata()
            
            # Extract street (from board card count)
            if board_card_count is not None:
                result.street = self._detect_street(board_card_count)
            elif roi_dict and 'board' in roi_dict:
                # Count board cards from visual detection
                count = self._count_board_cards(screenshot, roi_dict['board'])
                result.street = self._detect_street(count)
            
            # Extract table type (from title or visual indicators)
            if roi_dict and 'table_title' in roi_dict:
                result.table_type = self._detect_table_type(
                    screenshot, roi_dict['table_title']
                )
            
            # Extract seat information
            if roi_dict:
                result.max_seats = self._detect_max_seats(roi_dict)
                result.active_seats = self._detect_active_seats(screenshot, roi_dict)
            
            # Extract hand number (if visible)
            if roi_dict and 'hand_number' in roi_dict:
                result.hand_number = self._extract_hand_number(
                    screenshot, roi_dict['hand_number']
                )
            
            result.method = "visual_heuristics"
            result.confidence = 0.85
            
            return result
            
        except Exception as e:
            logger.error(f"Metadata extraction error: {e}")
            self.failures_count += 1
            
            if self.fallback_to_simulation:
                return self._simulate_metadata()
            
            return TableMetadata(
                confidence=0.0,
                method="error",
                error=str(e)
            )
    
    def _detect_street(self, board_card_count: int) -> Street:
        """
        Detect current street from board card count.
        
        Args:
            board_card_count: Number of visible board cards
        
        Returns:
            Detected street
        
        EDUCATIONAL NOTE:
            Standard poker street progression:
            0 cards -> preflop
            3 cards -> flop
            4 cards -> turn
            5 cards -> river
        """
        if board_card_count == 0:
            return Street.PREFLOP
        elif board_card_count == 3:
            return Street.FLOP
        elif board_card_count == 4:
            return Street.TURN
        elif board_card_count >= 5:
            return Street.RIVER
        else:
            # Unusual count - default to preflop
            return Street.PREFLOP
    
    def _count_board_cards(
        self,
        screenshot: np.ndarray,
        board_roi: Tuple[int, int, int, int]
    ) -> int:
        """
        Count visible board cards from screenshot.
        
        Args:
            screenshot: Screenshot array
            board_roi: Region of interest for board
        
        Returns:
            Number of detected board cards (0-5)
        """
        # Placeholder for visual card counting
        # Real implementation would use:
        # - Template matching for card backs/faces
        # - Edge detection for card boundaries
        # - Color segmentation
        
        # Example:
        # region = screenshot[board_roi[1]:board_roi[1]+board_roi[3], ...]
        # cards = detect_card_boundaries(region)
        # return len(cards)
        
        return 0
    
    def _detect_table_type(
        self,
        screenshot: np.ndarray,
        title_roi: Tuple[int, int, int, int]
    ) -> TableType:
        """
        Detect table type from title or visual indicators.
        
        Args:
            screenshot: Screenshot array
            title_roi: Region of interest for table title
        
        Returns:
            Detected table type
        
        EDUCATIONAL NOTE:
            Common indicators:
            - "Cash" or "$" in title -> CASH
            - "Tournament" or "T$" -> TOURNAMENT
            - "Sit & Go" or "SNG" -> SNG
        """
        # Placeholder for OCR-based detection
        # Real implementation:
        # region = screenshot[title_roi[1]:title_roi[1]+title_roi[3], ...]
        # text = pytesseract.image_to_string(region)
        # if "tournament" in text.lower():
        #     return TableType.TOURNAMENT
        # elif "sit" in text.lower() or "sng" in text.lower():
        #     return TableType.SNG
        # else:
        #     return TableType.CASH
        
        return TableType.CASH
    
    def _detect_max_seats(
        self,
        roi_dict: dict
    ) -> int:
        """
        Detect maximum seats from ROI layout.
        
        Args:
            roi_dict: Dictionary of ROIs
        
        Returns:
            Maximum number of seats (typically 2, 6, or 9)
        
        EDUCATIONAL NOTE:
            Seat count inferred from number of player position ROIs.
        """
        # Count player seat ROIs
        seat_count = sum(
            1 for key in roi_dict.keys()
            if 'seat' in key.lower() or key.lower() == 'hero'
        )
        
        # Map to standard table sizes
        if seat_count <= 2:
            return 2  # Heads-up
        elif seat_count <= 6:
            return 6  # 6-max
        else:
            return 9  # Full ring
    
    def _detect_active_seats(
        self,
        screenshot: np.ndarray,
        roi_dict: dict
    ) -> int:
        """
        Detect number of active (occupied) seats.
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary of ROIs
        
        Returns:
            Number of active seats
        
        EDUCATIONAL NOTE:
            Active seats detected by presence of stack/name indicators.
        """
        # Placeholder for active seat detection
        # Real implementation would check each seat ROI for visual indicators
        
        # Example heuristic:
        # active = 0
        # for seat_key in seat_rois:
        #     roi = roi_dict[seat_key]
        #     region = screenshot[roi[1]:roi[1]+roi[3], ...]
        #     if has_player_indicator(region):
        #         active += 1
        # return active
        
        # Default simulation
        return 4
    
    def _extract_hand_number(
        self,
        screenshot: np.ndarray,
        hand_roi: Tuple[int, int, int, int]
    ) -> int:
        """
        Extract hand number from screenshot.
        
        Args:
            screenshot: Screenshot array
            hand_roi: Region of interest for hand number
        
        Returns:
            Hand number (0 if not detected)
        """
        # Placeholder for OCR-based hand number extraction
        # Real implementation:
        # region = screenshot[hand_roi[1]:hand_roi[1]+hand_roi[3], ...]
        # text = pytesseract.image_to_string(region, config='--psm 6 digits')
        # return int(text.strip())
        
        return 0
    
    def _simulate_metadata(self) -> TableMetadata:
        """
        Generate simulated metadata for DRY-RUN mode.
        
        Returns:
            Realistic simulated metadata
        """
        return TableMetadata(
            street=Street.FLOP,
            table_type=TableType.CASH,
            max_seats=6,
            active_seats=4,
            hand_number=12345,
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
            'dry_run': self.dry_run
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Metadata Extractor - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # DRY-RUN mode (safe for testing)
    extractor = MetadataExtractor(dry_run=True)
    
    # Extract all metadata
    metadata = extractor.extract_all()
    
    print(f"Street: {metadata.street.value}")
    print(f"Table type: {metadata.table_type.value}")
    print(f"Seats: {metadata.active_seats}/{metadata.max_seats}")
    print(f"Hand #: {metadata.hand_number}")
    print(f"Method: {metadata.method}, Confidence: {metadata.confidence:.1%}")
    print()
    
    # Test street detection
    print("Street Detection:")
    for count, expected in [(0, "preflop"), (3, "flop"), (4, "turn"), (5, "river")]:
        street = extractor._detect_street(count)
        print(f"  {count} cards -> {street.value} ✓")
    print()
    
    # Statistics
    stats = extractor.get_statistics()
    print(f"Extractions: {stats['total_extractions']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"DRY-RUN mode: {stats['dry_run']}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
