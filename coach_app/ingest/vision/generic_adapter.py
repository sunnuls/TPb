from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from coach_app.ingest.vision.base import VisionAdapter


class GenericVisionAdapter(VisionAdapter):
    """
    Stub adapter: returns an empty partial state with low confidence.
    Intended as an integration point for OCR/card recognition plugins.
    """

    adapter_name = "generic"

    def analyze_frame(self, image_path: Path, *, adapter_config: Mapping[str, Any]) -> dict[str, Any]:
        # In real life:
        # - use adapter_config ROIs to crop regions
        # - run OCR on stack/pot labels
        # - run card recognition on card ROIs
        # - return partial poker/blackjack state
        _ = (image_path, adapter_config)
        return {"confidence": {"value": 0.1, "source": "vision", "notes": ["Stub vision adapter"]}}


