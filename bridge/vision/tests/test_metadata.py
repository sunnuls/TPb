"""
Tests for MetadataExtractor (Roadmap3 Phase 2.3).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import numpy as np

from bridge.vision.metadata import (
    MetadataExtractor,
    TableMetadata,
    TableType
)
from sim_engine.state.table_state import Street


class TestTableMetadata:
    """Test TableMetadata dataclass."""
    
    def test_table_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = TableMetadata(
            street=Street.FLOP,
            table_type=TableType.CASH,
            max_seats=6,
            active_seats=4,
            hand_number=12345,
            confidence=0.9,
            method="visual"
        )
        
        assert metadata.street == Street.FLOP
        assert metadata.table_type == TableType.CASH
        assert metadata.max_seats == 6
        assert metadata.active_seats == 4
        assert metadata.hand_number == 12345
        assert metadata.confidence == 0.9
        assert metadata.method == "visual"
    
    def test_table_metadata_defaults(self):
        """Test metadata default values."""
        metadata = TableMetadata()
        
        assert metadata.street == Street.PREFLOP
        assert metadata.table_type == TableType.CASH
        assert metadata.max_seats == 6
        assert metadata.active_seats == 4
        assert metadata.hand_number == 0
        assert metadata.confidence == 1.0
        assert metadata.method == "simulated"


class TestMetadataExtractor:
    """Test MetadataExtractor in DRY-RUN mode."""
    
    def test_init_dry_run(self):
        """Test initialization in dry-run mode."""
        extractor = MetadataExtractor(dry_run=True)
        
        assert extractor.dry_run is True
        assert extractor.extractions_count == 0
        assert extractor.failures_count == 0
    
    def test_extract_all_dry_run(self):
        """Test all metadata extraction in dry-run mode."""
        extractor = MetadataExtractor(dry_run=True)
        
        metadata = extractor.extract_all()
        
        assert isinstance(metadata.street, Street)
        assert isinstance(metadata.table_type, TableType)
        assert metadata.max_seats > 0
        assert metadata.active_seats >= 0
        assert metadata.confidence == 1.0
        assert metadata.method == "simulated"
        assert metadata.error is None
    
    def test_detect_street_from_board_count(self):
        """Test street detection from board card count."""
        extractor = MetadataExtractor(dry_run=True)
        
        # Test all street progressions
        assert extractor._detect_street(0) == Street.PREFLOP
        assert extractor._detect_street(3) == Street.FLOP
        assert extractor._detect_street(4) == Street.TURN
        assert extractor._detect_street(5) == Street.RIVER
        
        # Test unusual counts
        assert extractor._detect_street(1) == Street.PREFLOP
        assert extractor._detect_street(6) == Street.RIVER
    
    def test_detect_max_seats_from_rois(self):
        """Test max seats detection from ROI dict."""
        extractor = MetadataExtractor(dry_run=True)
        
        # Heads-up (2 seats)
        roi_dict = {
            'hero': (0, 0, 100, 100),
            'seat1': (0, 0, 100, 100)
        }
        assert extractor._detect_max_seats(roi_dict) == 2
        
        # 6-max
        roi_dict = {
            'hero': (0, 0, 100, 100),
            'seat1': (0, 0, 100, 100),
            'seat2': (0, 0, 100, 100),
            'seat3': (0, 0, 100, 100),
            'seat4': (0, 0, 100, 100),
            'seat5': (0, 0, 100, 100)
        }
        assert extractor._detect_max_seats(roi_dict) == 6
        
        # 9-max (full ring)
        roi_dict = {
            'hero': (0, 0, 100, 100),
            **{f'seat{i}': (0, 0, 100, 100) for i in range(1, 9)}
        }
        assert extractor._detect_max_seats(roi_dict) == 9
    
    def test_extract_with_board_card_count(self):
        """Test extraction with explicit board card count."""
        extractor = MetadataExtractor(dry_run=True)
        
        # Test preflop
        metadata = extractor.extract_all(board_card_count=0)
        assert metadata.street == Street.PREFLOP
        
        # Test flop
        metadata = extractor.extract_all(board_card_count=3)
        assert metadata.street == Street.FLOP
        
        # Test turn
        metadata = extractor.extract_all(board_card_count=4)
        assert metadata.street == Street.TURN
        
        # Test river
        metadata = extractor.extract_all(board_card_count=5)
        assert metadata.street == Street.RIVER
    
    def test_multiple_extractions(self):
        """Test multiple extractions increment counter."""
        extractor = MetadataExtractor(dry_run=True)
        
        extractor.extract_all()
        extractor.extract_all()
        extractor.extract_all()
        
        assert extractor.extractions_count == 3
        assert extractor.failures_count == 0
    
    def test_get_statistics(self):
        """Test statistics collection."""
        extractor = MetadataExtractor(dry_run=True)
        
        extractor.extract_all()
        extractor.extract_all()
        
        stats = extractor.get_statistics()
        
        assert stats['total_extractions'] == 2
        assert stats['failures'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['dry_run'] is True


class TestEnums:
    """Test metadata enums."""
    
    def test_street_enum(self):
        """Test Street enum values."""
        assert Street.PREFLOP.value == "preflop"
        assert Street.FLOP.value == "flop"
        assert Street.TURN.value == "turn"
        assert Street.RIVER.value == "river"
    
    def test_table_type_enum(self):
        """Test TableType enum values."""
        assert TableType.CASH.value == "cash"
        assert TableType.TOURNAMENT.value == "tournament"
        assert TableType.SNG.value == "sit_n_go"
        assert TableType.UNKNOWN.value == "unknown"


class TestIntegration:
    """Integration tests for metadata extractor."""
    
    def test_full_extraction_workflow(self):
        """Test complete metadata extraction workflow."""
        extractor = MetadataExtractor(dry_run=True, fallback_to_simulation=True)
        
        # Extract all metadata
        metadata = extractor.extract_all(board_card_count=3)
        
        # Validate street (should be FLOP for 3 cards)
        assert metadata.street == Street.FLOP
        
        # Validate table type
        assert isinstance(metadata.table_type, TableType)
        
        # Validate seats
        assert metadata.max_seats >= 2
        assert metadata.active_seats >= 0
        assert metadata.active_seats <= metadata.max_seats
        
        # Check statistics
        stats = extractor.get_statistics()
        assert stats['total_extractions'] == 1
        assert stats['success_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
