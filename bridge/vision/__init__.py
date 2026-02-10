"""
Vision extraction modules for bridge (Roadmap3 Phase 2).

EDUCATIONAL USE ONLY: For HCI research studying external application interfaces.
All extraction operates in DRY-RUN mode by default.
"""

from bridge.vision.card_extractor import CardExtractor, CardDetection
from bridge.vision.numeric_parser import NumericParser, NumericData
from bridge.vision.metadata import MetadataExtractor, TableMetadata

__all__ = [
    "CardExtractor",
    "CardDetection",
    "NumericParser",
    "NumericData",
    "MetadataExtractor",
    "TableMetadata",
]
