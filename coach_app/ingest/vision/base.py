from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping


class VisionAdapter(ABC):
    """
    Plugin interface for screenshot/video ingestion.
    A real adapter would do OCR + card recognition + table parsing and return partial state with confidence.
    """

    adapter_name: str

    @abstractmethod
    def analyze_frame(self, image_path: Path, *, adapter_config: Mapping[str, Any]) -> dict[str, Any]:
        """
        Return a JSON-serializable dict representing partial state + confidence.
        Must NOT invent: return unknown fields as absent.
        """


