from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field


class VisionParseResult(BaseModel):
    partial_state: dict[str, Any] = Field(default_factory=dict)
    confidence_map: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    adapter_name: str
    adapter_version: str


class VisionAdapter(ABC):
    """
    Plugin interface for screenshot/video ingestion.
    A real adapter would do OCR + card recognition + table parsing and return partial state with confidence.
    """

    adapter_name: str
    adapter_version: str

    @abstractmethod
    def parse(self, image: bytes | Image.Image) -> VisionParseResult:
        """Parse screenshot/frame into PARTIAL state + confidence (never invent missing facts)."""




