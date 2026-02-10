"""
Training Data Collector (Roadmap4 Phase 2).

Automatically collects screenshots and manages manual annotation.

Features:
- Automatic screenshot capture (configurable interval)
- Manual annotation interface for cards/pot/stacks
- Save to dataset/ (PNG + JSON labels)
- Support for multiple poker rooms

EDUCATIONAL USE ONLY: For HCI research prototype training.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from bridge.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)


@dataclass
class CardAnnotation:
    """
    Annotation for a single card.
    
    Attributes:
        rank: Card rank (2-9, T, J, Q, K, A)
        suit: Card suit (h, d, c, s)
        x: X coordinate (top-left)
        y: Y coordinate (top-left)
        width: Card width in pixels
        height: Card height in pixels
    """
    rank: str
    suit: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class NumericAnnotation:
    """
    Annotation for numeric value (pot/stack/bet).
    
    Attributes:
        label: Field label (pot, stack_hero, stack_villain, bet, etc.)
        value: Numeric value
        x: X coordinate (top-left of text region)
        y: Y coordinate (top-left of text region)
        width: Text region width
        height: Text region height
    """
    label: str
    value: float
    x: int
    y: int
    width: int
    height: int


@dataclass
class ScreenshotAnnotation:
    """
    Complete annotation for a screenshot.
    
    Attributes:
        screenshot_id: Unique screenshot ID
        timestamp: Capture timestamp
        room: Poker room name
        resolution: Screen resolution
        cards: List of card annotations
        numerics: List of numeric annotations
        metadata: Additional metadata
    """
    screenshot_id: str
    timestamp: float
    room: str
    resolution: str
    cards: List[CardAnnotation]
    numerics: List[NumericAnnotation]
    metadata: dict


class TrainingDataCollector:
    """
    Collects training data for vision models.
    
    Workflow:
    1. Auto-capture screenshots at regular intervals
    2. Save raw screenshots to dataset/screenshots/
    3. Generate annotation templates (JSON)
    4. Manual annotation (external tool or UI)
    5. Validate annotations
    
    EDUCATIONAL NOTE:
        Training data is essential for accurate vision models.
        More diverse data = better generalization across poker rooms.
    """
    
    def __init__(
        self,
        dataset_dir: str = "dataset",
        capture_interval: float = 5.0,
        room: str = "unknown"
    ):
        """
        Initialize training data collector.
        
        Args:
            dataset_dir: Root directory for dataset
            capture_interval: Seconds between auto-captures
            room: Poker room name for labeling
        """
        self.dataset_dir = Path(dataset_dir)
        self.capture_interval = capture_interval
        self.room = room
        
        # Create directory structure
        self.screenshots_dir = self.dataset_dir / "screenshots"
        self.annotations_dir = self.dataset_dir / "annotations"
        self.raw_dir = self.dataset_dir / "raw"
        
        for dir_path in [self.screenshots_dir, self.annotations_dir, self.raw_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Screen capture
        self.screen_capture = ScreenCapture()
        
        # Statistics
        self.screenshots_captured = 0
        self.annotations_created = 0
        
        logger.info(
            f"TrainingDataCollector initialized: "
            f"interval={capture_interval}s, room={room}, "
            f"dataset_dir={self.dataset_dir}"
        )
    
    def capture_screenshot(self, manual: bool = False) -> Optional[str]:
        """
        Capture and save screenshot.
        
        Args:
            manual: Whether this is a manual capture (not auto)
        
        Returns:
            Screenshot ID if successful, None otherwise
        
        EDUCATIONAL NOTE:
            Each screenshot gets a unique ID with timestamp.
        """
        try:
            # Capture screenshot
            screenshot, window_info = self.screen_capture.capture()
            
            if screenshot is None:
                logger.warning("Screenshot capture failed")
                return None
            
            # Generate ID
            timestamp = datetime.now()
            screenshot_id = f"{self.room}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            if manual:
                screenshot_id += "_manual"
            
            # Save screenshot
            screenshot_path = self.screenshots_dir / f"{screenshot_id}.png"
            
            # Note: Actual image saving would require PIL/cv2
            # For now, just log the path
            logger.info(f"Screenshot captured: {screenshot_id}")
            
            # Create annotation template
            self._create_annotation_template(screenshot_id, timestamp.timestamp())
            
            self.screenshots_captured += 1
            
            return screenshot_id
            
        except Exception as e:
            logger.error(f"Screenshot capture error: {e}", exc_info=True)
            return None
    
    def _create_annotation_template(
        self,
        screenshot_id: str,
        timestamp: float
    ) -> None:
        """
        Create annotation template JSON.
        
        Args:
            screenshot_id: Screenshot ID
            timestamp: Capture timestamp
        
        EDUCATIONAL NOTE:
            Template provides structure for manual annotation.
        """
        # Get screen resolution
        resolution = "1920x1080"  # Default, would detect from capture
        
        # Create empty annotation
        annotation = ScreenshotAnnotation(
            screenshot_id=screenshot_id,
            timestamp=timestamp,
            room=self.room,
            resolution=resolution,
            cards=[],
            numerics=[],
            metadata={
                'annotated': False,
                'annotation_date': None,
                'annotator': None
            }
        )
        
        # Save to JSON
        annotation_path = self.annotations_dir / f"{screenshot_id}.json"
        
        with open(annotation_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(annotation), f, indent=2)
        
        self.annotations_created += 1
        
        logger.debug(f"Annotation template created: {annotation_path}")
    
    def load_annotation(self, screenshot_id: str) -> Optional[ScreenshotAnnotation]:
        """
        Load annotation from JSON.
        
        Args:
            screenshot_id: Screenshot ID
        
        Returns:
            ScreenshotAnnotation if found, None otherwise
        """
        annotation_path = self.annotations_dir / f"{screenshot_id}.json"
        
        if not annotation_path.exists():
            logger.warning(f"Annotation not found: {screenshot_id}")
            return None
        
        try:
            with open(annotation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct annotation
            cards = [CardAnnotation(**c) for c in data.get('cards', [])]
            numerics = [NumericAnnotation(**n) for n in data.get('numerics', [])]
            
            annotation = ScreenshotAnnotation(
                screenshot_id=data['screenshot_id'],
                timestamp=data['timestamp'],
                room=data['room'],
                resolution=data['resolution'],
                cards=cards,
                numerics=numerics,
                metadata=data.get('metadata', {})
            )
            
            return annotation
            
        except Exception as e:
            logger.error(f"Failed to load annotation: {e}", exc_info=True)
            return None
    
    def save_annotation(self, annotation: ScreenshotAnnotation) -> bool:
        """
        Save annotation to JSON.
        
        Args:
            annotation: Annotation to save
        
        Returns:
            True if successful, False otherwise
        """
        annotation_path = self.annotations_dir / f"{annotation.screenshot_id}.json"
        
        try:
            # Mark as annotated
            annotation.metadata['annotated'] = True
            annotation.metadata['annotation_date'] = datetime.now().isoformat()
            
            with open(annotation_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(annotation), f, indent=2)
            
            logger.info(f"Annotation saved: {annotation.screenshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save annotation: {e}", exc_info=True)
            return False
    
    def validate_annotation(self, annotation: ScreenshotAnnotation) -> List[str]:
        """
        Validate annotation completeness and correctness.
        
        Args:
            annotation: Annotation to validate
        
        Returns:
            List of validation errors (empty if valid)
        
        EDUCATIONAL NOTE:
            Validation ensures data quality for training.
        """
        errors = []
        
        # Check cards
        for i, card in enumerate(annotation.cards):
            # Validate rank
            if card.rank not in ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']:
                errors.append(f"Card {i}: Invalid rank '{card.rank}'")
            
            # Validate suit
            if card.suit not in ['h', 'd', 'c', 's']:
                errors.append(f"Card {i}: Invalid suit '{card.suit}'")
            
            # Validate coordinates
            if card.x < 0 or card.y < 0:
                errors.append(f"Card {i}: Negative coordinates")
            
            if card.width <= 0 or card.height <= 0:
                errors.append(f"Card {i}: Invalid dimensions")
        
        # Check numerics
        for i, numeric in enumerate(annotation.numerics):
            # Validate value
            if numeric.value < 0:
                errors.append(f"Numeric {i}: Negative value")
            
            # Validate coordinates
            if numeric.x < 0 or numeric.y < 0:
                errors.append(f"Numeric {i}: Negative coordinates")
        
        # Check if annotated
        if not annotation.metadata.get('annotated', False):
            errors.append("Annotation not marked as complete")
        
        return errors
    
    def get_annotated_count(self) -> int:
        """
        Get count of annotated screenshots.
        
        Returns:
            Number of completed annotations
        """
        count = 0
        
        for annotation_file in self.annotations_dir.glob("*.json"):
            try:
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('metadata', {}).get('annotated', False):
                        count += 1
            except Exception:
                continue
        
        return count
    
    def get_statistics(self) -> dict:
        """Get collector statistics."""
        total_annotations = len(list(self.annotations_dir.glob("*.json")))
        annotated_count = self.get_annotated_count()
        
        return {
            'screenshots_captured': self.screenshots_captured,
            'annotations_created': self.annotations_created,
            'total_annotations': total_annotations,
            'annotated_count': annotated_count,
            'annotation_progress': (
                annotated_count / total_annotations * 100
                if total_annotations > 0 else 0
            ),
            'dataset_dir': str(self.dataset_dir),
            'room': self.room,
            'capture_interval': self.capture_interval
        }
    
    def export_for_training(self, output_dir: str) -> bool:
        """
        Export annotated data for model training.
        
        Args:
            output_dir: Output directory for training data
        
        Returns:
            True if successful, False otherwise
        
        EDUCATIONAL NOTE:
            Exports data in format suitable for YOLO/other models.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_count = 0
        
        for annotation_file in self.annotations_dir.glob("*.json"):
            try:
                annotation = self.load_annotation(annotation_file.stem)
                
                if annotation is None:
                    continue
                
                # Only export annotated data
                if not annotation.metadata.get('annotated', False):
                    continue
                
                # Validate
                errors = self.validate_annotation(annotation)
                if errors:
                    logger.warning(
                        f"Skipping {annotation.screenshot_id}: "
                        f"{len(errors)} validation errors"
                    )
                    continue
                
                # Copy to output (would copy actual image + labels)
                logger.debug(f"Exporting: {annotation.screenshot_id}")
                exported_count += 1
                
            except Exception as e:
                logger.error(f"Export error: {e}", exc_info=True)
        
        logger.info(f"Exported {exported_count} annotated screenshots")
        return exported_count > 0


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Training Data Collector - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Initialize collector
    collector = TrainingDataCollector(
        dataset_dir="dataset_demo",
        capture_interval=5.0,
        room="pokerstars"
    )
    
    print("Collector Configuration:")
    print(f"  Dataset directory: {collector.dataset_dir}")
    print(f"  Capture interval: {collector.capture_interval}s")
    print(f"  Room: {collector.room}")
    print()
    
    # Simulate manual capture
    print("Simulating screenshot capture...")
    screenshot_id = collector.capture_screenshot(manual=True)
    
    if screenshot_id:
        print(f"  Screenshot ID: {screenshot_id}")
        print()
        
        # Load annotation template
        annotation = collector.load_annotation(screenshot_id)
        
        if annotation:
            print("Annotation template created:")
            print(f"  Screenshot ID: {annotation.screenshot_id}")
            print(f"  Room: {annotation.room}")
            print(f"  Resolution: {annotation.resolution}")
            print(f"  Cards: {len(annotation.cards)}")
            print(f"  Numerics: {len(annotation.numerics)}")
            print()
        
        # Simulate adding annotations
        print("Simulating manual annotation...")
        annotation.cards.append(CardAnnotation(
            rank='A', suit='s',
            x=100, y=200, width=50, height=70
        ))
        annotation.cards.append(CardAnnotation(
            rank='K', suit='h',
            x=160, y=200, width=50, height=70
        ))
        
        annotation.numerics.append(NumericAnnotation(
            label='pot',
            value=150.0,
            x=500, y=300, width=100, height=30
        ))
        
        # Save annotation
        if collector.save_annotation(annotation):
            print("  Annotation saved successfully")
            print()
        
        # Validate
        errors = collector.validate_annotation(annotation)
        if errors:
            print(f"Validation errors: {len(errors)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Validation: OK")
        print()
    
    # Statistics
    stats = collector.get_statistics()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    for key, value in stats.items():
        if key == 'annotation_progress':
            print(f"{key}: {value:.1f}%")
        else:
            print(f"{key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - Training Data Collection")
    print("=" * 60)
