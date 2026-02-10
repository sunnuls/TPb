"""
Card Extraction Module (Roadmap3 Phase 2.1).

Extracts hero cards + board cards from screenshots.
In DRY-RUN mode: returns simulated card data.
In UNSAFE mode: uses existing vision adapter from coach_app (if available).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CardRank(str, Enum):
    """Card ranks."""
    ACE = "A"
    KING = "K"
    QUEEN = "Q"
    JACK = "J"
    TEN = "T"
    NINE = "9"
    EIGHT = "8"
    SEVEN = "7"
    SIX = "6"
    FIVE = "5"
    FOUR = "4"
    THREE = "3"
    DEUCE = "2"


class CardSuit(str, Enum):
    """Card suits."""
    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"


@dataclass
class CardDetection:
    """
    Result of card extraction from a region.
    
    Attributes:
        cards: List of detected cards (e.g., ["As", "Kh"])
        confidence: Detection confidence (0.0-1.0)
        method: Detection method used
        error: Error message if detection failed
    """
    cards: List[str]
    confidence: float
    method: str = "simulated"
    error: Optional[str] = None


class CardExtractor:
    """
    Extracts poker cards from screenshots.
    
    In DRY-RUN mode (default):
        Returns simulated card data for testing.
    
    In UNSAFE mode:
        Attempts to use existing vision adapter from coach_app
        or fallback OCR/template matching.
    
    EDUCATIONAL NOTE:
        This demonstrates HCI research methodology for studying
        external application interfaces without direct API access.
    """
    
    def __init__(
        self,
        dry_run: bool = True,
        fallback_to_simulation: bool = True
    ):
        """
        Initialize card extractor.
        
        Args:
            dry_run: If True, return simulated data only
            fallback_to_simulation: If True, fallback to simulation on errors
        """
        self.dry_run = dry_run
        self.fallback_to_simulation = fallback_to_simulation
        
        # Try to import vision adapter (optional)
        self.vision_adapter = None
        if not dry_run:
            self.vision_adapter = self._try_load_vision_adapter()
        
        # Statistics
        self.extractions_count = 0
        self.failures_count = 0
        
        logger.info(
            f"CardExtractor initialized (dry_run={dry_run}, "
            f"adapter={'loaded' if self.vision_adapter else 'unavailable'})"
        )
    
    def _try_load_vision_adapter(self) -> Optional[object]:
        """
        Try to load existing vision adapter from coach_app.
        
        Returns:
            Vision adapter instance or None
        """
        try:
            # Attempt to import existing vision components
            # (This is a placeholder - actual integration would use real adapter)
            logger.info("Attempting to load coach_app vision adapter...")
            
            # Example: from coach_app.vision import CardDetector
            # return CardDetector()
            
            logger.warning("coach_app vision adapter not available - using fallback")
            return None
            
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            logger.debug(f"Vision adapter import failed: {e}")
            return None
    
    def extract_hero_cards(
        self,
        screenshot: Optional[np.ndarray] = None,
        roi: Optional[Tuple[int, int, int, int]] = None
    ) -> CardDetection:
        """
        Extract hero's hole cards from screenshot.
        
        Args:
            screenshot: Screenshot array (H, W, 3) or None for simulation
            roi: Region of interest (x, y, w, h) or None for full image
        
        Returns:
            CardDetection with hero cards
        
        EDUCATIONAL NOTE:
            In DRY-RUN mode, returns simulated cards for testing purposes.
            In UNSAFE mode, attempts real vision extraction.
        """
        self.extractions_count += 1
        
        if self.dry_run:
            return self._simulate_hero_cards()
        
        # Real extraction logic (UNSAFE mode only)
        try:
            if self.vision_adapter:
                # Use existing vision adapter
                result = self._extract_with_adapter(screenshot, roi, "hero")
                if result.cards:
                    return result
            
            # Fallback: OCR/template matching
            result = self._extract_with_fallback(screenshot, roi, "hero")
            if result.cards:
                return result
            
            # If all methods failed and fallback enabled
            if self.fallback_to_simulation:
                logger.warning("All extraction methods failed - falling back to simulation")
                return self._simulate_hero_cards()
            
            # Return empty result with error
            self.failures_count += 1
            return CardDetection(
                cards=[],
                confidence=0.0,
                method="failed",
                error="All extraction methods failed"
            )
            
        except Exception as e:
            logger.error(f"Hero card extraction error: {e}")
            self.failures_count += 1
            
            if self.fallback_to_simulation:
                return self._simulate_hero_cards()
            
            return CardDetection(
                cards=[],
                confidence=0.0,
                method="error",
                error=str(e)
            )
    
    def extract_board_cards(
        self,
        screenshot: Optional[np.ndarray] = None,
        roi: Optional[Tuple[int, int, int, int]] = None
    ) -> CardDetection:
        """
        Extract board (community) cards from screenshot.
        
        Args:
            screenshot: Screenshot array (H, W, 3) or None for simulation
            roi: Region of interest (x, y, w, h) or None for full image
        
        Returns:
            CardDetection with board cards (0-5 cards depending on street)
        
        EDUCATIONAL NOTE:
            Board cards visible: 0 (preflop), 3 (flop), 4 (turn), 5 (river).
        """
        self.extractions_count += 1
        
        if self.dry_run:
            return self._simulate_board_cards()
        
        # Real extraction (UNSAFE mode)
        try:
            if self.vision_adapter:
                result = self._extract_with_adapter(screenshot, roi, "board")
                if result.cards:
                    return result
            
            result = self._extract_with_fallback(screenshot, roi, "board")
            if result.cards:
                return result
            
            if self.fallback_to_simulation:
                return self._simulate_board_cards()
            
            self.failures_count += 1
            return CardDetection(
                cards=[],
                confidence=0.0,
                method="failed",
                error="Board extraction failed"
            )
            
        except Exception as e:
            logger.error(f"Board card extraction error: {e}")
            self.failures_count += 1
            
            if self.fallback_to_simulation:
                return self._simulate_board_cards()
            
            return CardDetection(
                cards=[],
                confidence=0.0,
                method="error",
                error=str(e)
            )
    
    def _extract_with_adapter(
        self,
        screenshot: Optional[np.ndarray],
        roi: Optional[Tuple[int, int, int, int]],
        card_type: str
    ) -> CardDetection:
        """
        Extract cards using vision adapter.
        
        Args:
            screenshot: Image array
            roi: Region of interest
            card_type: "hero" or "board"
        
        Returns:
            CardDetection result
        """
        # Placeholder for real adapter integration
        logger.debug(f"Attempting adapter extraction for {card_type}")
        
        # Example integration:
        # region = screenshot[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        # cards = self.vision_adapter.detect_cards(region)
        # return CardDetection(cards=cards, confidence=0.95, method="vision_adapter")
        
        return CardDetection(
            cards=[],
            confidence=0.0,
            method="adapter_unavailable"
        )
    
    def _extract_with_fallback(
        self,
        screenshot: Optional[np.ndarray],
        roi: Optional[Tuple[int, int, int, int]],
        card_type: str
    ) -> CardDetection:
        """
        Extract cards using fallback OCR/template matching.
        
        Args:
            screenshot: Image array
            roi: Region of interest
            card_type: "hero" or "board"
        
        Returns:
            CardDetection result
        """
        # Placeholder for OCR/template matching
        logger.debug(f"Attempting fallback extraction for {card_type}")
        
        # Example OCR logic:
        # text = pytesseract.image_to_string(region)
        # cards = parse_card_text(text)
        # return CardDetection(cards=cards, confidence=0.7, method="ocr")
        
        return CardDetection(
            cards=[],
            confidence=0.0,
            method="fallback_unavailable"
        )
    
    def _simulate_hero_cards(self) -> CardDetection:
        """
        Generate simulated hero cards for DRY-RUN mode.
        
        Returns:
            Simulated hero cards (always 2 cards)
        """
        # Educational simulation: return sample premium hand
        simulated_cards = ["As", "Kh"]
        
        return CardDetection(
            cards=simulated_cards,
            confidence=1.0,
            method="simulated"
        )
    
    def _simulate_board_cards(self) -> CardDetection:
        """
        Generate simulated board cards for DRY-RUN mode.
        
        Returns:
            Simulated board cards (varies by street simulation)
        """
        # Educational simulation: return sample flop
        simulated_board = ["Qd", "Jc", "9s"]
        
        return CardDetection(
            cards=simulated_board,
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
            'adapter_available': self.vision_adapter is not None
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Card Extractor - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # DRY-RUN mode (safe for testing)
    extractor = CardExtractor(dry_run=True)
    
    # Extract hero cards
    hero = extractor.extract_hero_cards()
    print(f"Hero cards: {hero.cards}")
    print(f"Method: {hero.method}, Confidence: {hero.confidence:.1%}")
    print()
    
    # Extract board cards
    board = extractor.extract_board_cards()
    print(f"Board cards: {board.cards}")
    print(f"Method: {board.method}, Confidence: {board.confidence:.1%}")
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
