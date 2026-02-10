"""
Tests for CardExtractor (Roadmap3 Phase 2.1).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import numpy as np

from bridge.vision.card_extractor import (
    CardExtractor,
    CardDetection,
    CardRank,
    CardSuit
)


class TestCardDetection:
    """Test CardDetection dataclass."""
    
    def test_card_detection_creation(self):
        """Test basic card detection creation."""
        detection = CardDetection(
            cards=["As", "Kh"],
            confidence=0.95,
            method="vision"
        )
        
        assert detection.cards == ["As", "Kh"]
        assert detection.confidence == 0.95
        assert detection.method == "vision"
        assert detection.error is None
    
    def test_card_detection_with_error(self):
        """Test card detection with error."""
        detection = CardDetection(
            cards=[],
            confidence=0.0,
            method="failed",
            error="OCR failed"
        )
        
        assert detection.cards == []
        assert detection.confidence == 0.0
        assert detection.error == "OCR failed"


class TestCardExtractor:
    """Test CardExtractor in DRY-RUN mode."""
    
    def test_init_dry_run(self):
        """Test initialization in dry-run mode."""
        extractor = CardExtractor(dry_run=True)
        
        assert extractor.dry_run is True
        assert extractor.vision_adapter is None
        assert extractor.extractions_count == 0
        assert extractor.failures_count == 0
    
    def test_extract_hero_cards_dry_run(self):
        """Test hero card extraction in dry-run mode."""
        extractor = CardExtractor(dry_run=True)
        
        detection = extractor.extract_hero_cards()
        
        assert len(detection.cards) == 2
        assert detection.confidence == 1.0
        assert detection.method == "simulated"
        assert detection.error is None
        assert extractor.extractions_count == 1
    
    def test_extract_board_cards_dry_run(self):
        """Test board card extraction in dry-run mode."""
        extractor = CardExtractor(dry_run=True)
        
        detection = extractor.extract_board_cards()
        
        assert len(detection.cards) == 3  # Simulated flop
        assert detection.confidence == 1.0
        assert detection.method == "simulated"
        assert detection.error is None
    
    def test_multiple_extractions(self):
        """Test multiple extractions increment counter."""
        extractor = CardExtractor(dry_run=True)
        
        extractor.extract_hero_cards()
        extractor.extract_board_cards()
        extractor.extract_hero_cards()
        
        assert extractor.extractions_count == 3
        assert extractor.failures_count == 0
    
    def test_get_statistics(self):
        """Test statistics collection."""
        extractor = CardExtractor(dry_run=True)
        
        extractor.extract_hero_cards()
        extractor.extract_board_cards()
        
        stats = extractor.get_statistics()
        
        assert stats['total_extractions'] == 2
        assert stats['failures'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['dry_run'] is True
        assert stats['adapter_available'] is False


class TestEnums:
    """Test card enums."""
    
    def test_card_rank_enum(self):
        """Test CardRank enum values."""
        assert CardRank.ACE.value == "A"
        assert CardRank.KING.value == "K"
        assert CardRank.QUEEN.value == "Q"
        assert CardRank.DEUCE.value == "2"
    
    def test_card_suit_enum(self):
        """Test CardSuit enum values."""
        assert CardSuit.SPADES.value == "s"
        assert CardSuit.HEARTS.value == "h"
        assert CardSuit.DIAMONDS.value == "d"
        assert CardSuit.CLUBS.value == "c"


class TestIntegration:
    """Integration tests for card extractor."""
    
    def test_full_extraction_workflow(self):
        """Test complete card extraction workflow."""
        extractor = CardExtractor(dry_run=True, fallback_to_simulation=True)
        
        # Extract hero cards
        hero = extractor.extract_hero_cards()
        assert len(hero.cards) == 2
        assert all(len(card) == 2 for card in hero.cards)
        
        # Extract board cards
        board = extractor.extract_board_cards()
        assert len(board.cards) >= 0
        assert len(board.cards) <= 5
        
        # Check statistics
        stats = extractor.get_statistics()
        assert stats['total_extractions'] == 2
        assert stats['success_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
