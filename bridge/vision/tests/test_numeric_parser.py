"""
Tests for NumericParser (Roadmap3 Phase 2.2).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import numpy as np

from bridge.vision.numeric_parser import NumericParser, NumericData


class TestNumericData:
    """Test NumericData dataclass."""
    
    def test_numeric_data_creation(self):
        """Test basic numeric data creation."""
        data = NumericData(
            pot=150.0,
            stacks={'hero': 1000.0, 'v1': 950.0},
            bets={'hero': 50.0, 'v1': 50.0},
            positions={'hero': 'BTN', 'v1': 'BB'},
            confidence=0.9,
            method="ocr"
        )
        
        assert data.pot == 150.0
        assert len(data.stacks) == 2
        assert len(data.bets) == 2
        assert len(data.positions) == 2
        assert data.confidence == 0.9
        assert data.method == "ocr"
    
    def test_numeric_data_defaults(self):
        """Test numeric data default values."""
        data = NumericData()
        
        assert data.pot == 0.0
        assert data.stacks == {}
        assert data.bets == {}
        assert data.positions == {}
        assert data.confidence == 1.0
        assert data.method == "simulated"


class TestNumericParser:
    """Test NumericParser in DRY-RUN mode."""
    
    def test_init_dry_run(self):
        """Test initialization in dry-run mode."""
        parser = NumericParser(dry_run=True)
        
        assert parser.dry_run is True
        assert parser.ocr_available is False
        assert parser.extractions_count == 0
        assert parser.failures_count == 0
    
    def test_extract_all_dry_run(self):
        """Test all numeric extraction in dry-run mode."""
        parser = NumericParser(dry_run=True)
        
        data = parser.extract_all()
        
        assert data.pot > 0
        assert len(data.stacks) > 0
        assert len(data.bets) > 0
        assert len(data.positions) > 0
        assert data.confidence == 1.0
        assert data.method == "simulated"
        assert data.error is None
    
    def test_simulated_data_structure(self):
        """Test simulated data has correct structure."""
        parser = NumericParser(dry_run=True)
        
        data = parser.extract_all()
        
        # Check pot is a float
        assert isinstance(data.pot, float)
        
        # Check stacks are dict of player -> stack
        assert isinstance(data.stacks, dict)
        for player_id, stack in data.stacks.items():
            assert isinstance(player_id, str)
            assert isinstance(stack, float)
            assert stack >= 0
        
        # Check bets structure
        assert isinstance(data.bets, dict)
        
        # Check positions structure
        assert isinstance(data.positions, dict)
    
    def test_parse_numeric_text(self):
        """Test _parse_numeric_text helper."""
        parser = NumericParser(dry_run=True)
        
        # Test basic number
        assert parser._parse_numeric_text("150.50") == 150.5
        
        # Test with currency
        assert parser._parse_numeric_text("$1,234") == 1234.0
        
        # Test with BB suffix
        assert parser._parse_numeric_text("25 BB") == 25.0
        
        # Test invalid text
        assert parser._parse_numeric_text("invalid") == 0.0
    
    def test_multiple_extractions(self):
        """Test multiple extractions increment counter."""
        parser = NumericParser(dry_run=True)
        
        parser.extract_all()
        parser.extract_all()
        parser.extract_all()
        
        assert parser.extractions_count == 3
        assert parser.failures_count == 0
    
    def test_get_statistics(self):
        """Test statistics collection."""
        parser = NumericParser(dry_run=True)
        
        parser.extract_all()
        parser.extract_all()
        
        stats = parser.get_statistics()
        
        assert stats['total_extractions'] == 2
        assert stats['failures'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['dry_run'] is True
        assert stats['ocr_available'] is False


class TestIntegration:
    """Integration tests for numeric parser."""
    
    def test_full_extraction_workflow(self):
        """Test complete numeric extraction workflow."""
        parser = NumericParser(dry_run=True, fallback_to_simulation=True)
        
        # Extract all numeric data
        data = parser.extract_all()
        
        # Validate pot
        assert data.pot >= 0
        
        # Validate stacks
        assert len(data.stacks) > 0
        assert 'hero' in data.stacks or any('seat' in k for k in data.stacks.keys())
        
        # Validate all stacks are positive
        for stack in data.stacks.values():
            assert stack >= 0
        
        # Validate bets are non-negative
        for bet in data.bets.values():
            assert bet >= 0
        
        # Check statistics
        stats = parser.get_statistics()
        assert stats['total_extractions'] == 1
        assert stats['success_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
