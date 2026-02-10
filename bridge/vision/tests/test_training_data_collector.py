"""
Tests for Training Data Collector (Roadmap4 Phase 2).

Tests annotation creation, validation, and export.
"""

import json
from pathlib import Path

import pytest

from bridge.vision.training_data_collector import (
    CardAnnotation,
    NumericAnnotation,
    ScreenshotAnnotation,
    TrainingDataCollector,
)


class TestCardAnnotation:
    """Test card annotation."""
    
    def test_card_annotation_creation(self):
        """Test creating card annotation."""
        card = CardAnnotation(
            rank='A',
            suit='s',
            x=100,
            y=200,
            width=50,
            height=70
        )
        
        assert card.rank == 'A'
        assert card.suit == 's'
        assert card.x == 100
        assert card.y == 200
        assert card.width == 50
        assert card.height == 70


class TestNumericAnnotation:
    """Test numeric annotation."""
    
    def test_numeric_annotation_creation(self):
        """Test creating numeric annotation."""
        numeric = NumericAnnotation(
            label='pot',
            value=150.0,
            x=500,
            y=300,
            width=100,
            height=30
        )
        
        assert numeric.label == 'pot'
        assert numeric.value == 150.0
        assert numeric.x == 500
        assert numeric.y == 300


class TestScreenshotAnnotation:
    """Test screenshot annotation."""
    
    def test_annotation_creation(self):
        """Test creating screenshot annotation."""
        cards = [
            CardAnnotation('A', 's', 100, 200, 50, 70),
            CardAnnotation('K', 'h', 160, 200, 50, 70)
        ]
        
        numerics = [
            NumericAnnotation('pot', 150.0, 500, 300, 100, 30)
        ]
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=cards,
            numerics=numerics,
            metadata={'test': True}
        )
        
        assert annotation.screenshot_id == 'test_001'
        assert annotation.room == 'pokerstars'
        assert len(annotation.cards) == 2
        assert len(annotation.numerics) == 1


class TestTrainingDataCollector:
    """Test training data collector."""
    
    def test_initialization(self, tmp_path):
        """Test collector initialization."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            capture_interval=5.0,
            room='pokerstars'
        )
        
        assert collector.dataset_dir == tmp_path
        assert collector.capture_interval == 5.0
        assert collector.room == 'pokerstars'
        
        # Check directories created
        assert (tmp_path / "screenshots").exists()
        assert (tmp_path / "annotations").exists()
        assert (tmp_path / "raw").exists()
    
    def test_capture_screenshot(self, tmp_path):
        """Test screenshot capture."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            room='pokerstars'
        )
        
        screenshot_id = collector.capture_screenshot(manual=True)
        
        # Note: May return None if mss not available or no window selected
        # This is expected in test environment
        if screenshot_id is None:
            pytest.skip("Screenshot capture not available in test environment")
        
        assert 'pokerstars' in screenshot_id
        assert 'manual' in screenshot_id
        
        # Annotation template should be created
        annotation_file = tmp_path / "annotations" / f"{screenshot_id}.json"
        assert annotation_file.exists()
    
    def test_annotation_template_structure(self, tmp_path):
        """Test annotation template structure."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            room='pokerstars'
        )
        
        screenshot_id = collector.capture_screenshot(manual=True)
        
        # May be None in test environment
        if screenshot_id is None:
            pytest.skip("Screenshot capture not available in test environment")
        
        # Load and check template
        annotation = collector.load_annotation(screenshot_id)
        
        assert annotation is not None
        assert annotation.screenshot_id == screenshot_id
        assert annotation.room == 'pokerstars'
        assert len(annotation.cards) == 0  # Empty template
        assert len(annotation.numerics) == 0
        assert annotation.metadata['annotated'] is False
    
    def test_save_and_load_annotation(self, tmp_path):
        """Test saving and loading annotation."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            room='pokerstars'
        )
        
        # Create annotation
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('A', 's', 100, 200, 50, 70)],
            numerics=[NumericAnnotation('pot', 150.0, 500, 300, 100, 30)],
            metadata={'annotated': False}
        )
        
        # Save
        success = collector.save_annotation(annotation)
        assert success is True
        
        # Load
        loaded = collector.load_annotation('test_001')
        assert loaded is not None
        assert loaded.screenshot_id == 'test_001'
        assert len(loaded.cards) == 1
        assert len(loaded.numerics) == 1
        assert loaded.metadata['annotated'] is True  # Marked as annotated
    
    def test_validate_annotation_valid(self, tmp_path):
        """Test validation of valid annotation."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[
                CardAnnotation('A', 's', 100, 200, 50, 70),
                CardAnnotation('K', 'h', 160, 200, 50, 70)
            ],
            numerics=[
                NumericAnnotation('pot', 150.0, 500, 300, 100, 30)
            ],
            metadata={'annotated': True}
        )
        
        errors = collector.validate_annotation(annotation)
        
        # Should be valid
        assert len(errors) == 0
    
    def test_validate_annotation_invalid_rank(self, tmp_path):
        """Test validation with invalid rank."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('X', 's', 100, 200, 50, 70)],  # Invalid rank
            numerics=[],
            metadata={'annotated': True}
        )
        
        errors = collector.validate_annotation(annotation)
        
        # Should have validation error
        assert len(errors) > 0
        assert any('rank' in error.lower() for error in errors)
    
    def test_validate_annotation_invalid_suit(self, tmp_path):
        """Test validation with invalid suit."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('A', 'x', 100, 200, 50, 70)],  # Invalid suit
            numerics=[],
            metadata={'annotated': True}
        )
        
        errors = collector.validate_annotation(annotation)
        
        # Should have validation error
        assert len(errors) > 0
        assert any('suit' in error.lower() for error in errors)
    
    def test_validate_annotation_negative_coordinates(self, tmp_path):
        """Test validation with negative coordinates."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('A', 's', -10, 200, 50, 70)],  # Negative x
            numerics=[],
            metadata={'annotated': True}
        )
        
        errors = collector.validate_annotation(annotation)
        
        # Should have validation error
        assert len(errors) > 0
        assert any('coordinates' in error.lower() for error in errors)
    
    def test_validate_annotation_not_annotated(self, tmp_path):
        """Test validation of incomplete annotation."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[],
            numerics=[],
            metadata={'annotated': False}  # Not annotated
        )
        
        errors = collector.validate_annotation(annotation)
        
        # Should have error
        assert len(errors) > 0
        assert any('not marked' in error.lower() for error in errors)
    
    def test_get_annotated_count(self, tmp_path):
        """Test counting annotated screenshots."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        # Initially 0
        assert collector.get_annotated_count() == 0
        
        # Create and save annotated
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('A', 's', 100, 200, 50, 70)],
            numerics=[],
            metadata={'annotated': False}
        )
        collector.save_annotation(annotation)  # Marks as annotated
        
        # Should be 1
        assert collector.get_annotated_count() == 1
    
    def test_get_statistics(self, tmp_path):
        """Test statistics retrieval."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            room='pokerstars'
        )
        
        stats = collector.get_statistics()
        
        assert 'screenshots_captured' in stats
        assert 'annotations_created' in stats
        assert 'total_annotations' in stats
        assert 'annotated_count' in stats
        assert 'annotation_progress' in stats
        assert 'dataset_dir' in stats
        assert 'room' in stats
        assert stats['room'] == 'pokerstars'
    
    def test_export_for_training(self, tmp_path):
        """Test export for training."""
        collector = TrainingDataCollector(dataset_dir=str(tmp_path))
        
        # Create valid annotated data
        annotation = ScreenshotAnnotation(
            screenshot_id='test_001',
            timestamp=1234567890.0,
            room='pokerstars',
            resolution='1920x1080',
            cards=[CardAnnotation('A', 's', 100, 200, 50, 70)],
            numerics=[NumericAnnotation('pot', 150.0, 500, 300, 100, 30)],
            metadata={'annotated': False}
        )
        collector.save_annotation(annotation)
        
        # Export
        output_dir = tmp_path / "export"
        result = collector.export_for_training(str(output_dir))
        
        # Should succeed
        assert result is True
        assert output_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
