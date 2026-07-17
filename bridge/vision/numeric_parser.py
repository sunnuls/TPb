"""
Numeric Parser Module.

Extracts numeric data from screenshots:
- Pot size
- Player stacks
- Current bets
- Player positions

In DRY-RUN mode: returns simulated numeric data.
In LIVE mode: uses OCR (pytesseract).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_OCR_CFG = "--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789.,$₮BbKkMm "


@dataclass
class NumericData:
    """Result of numeric extraction."""

    pot: float = 0.0
    stacks: Dict[str, float] = None
    bets: Dict[str, float] = None
    positions: Dict[str, str] = None
    confidence: float = 1.0
    method: str = "simulated"
    error: Optional[str] = None

    def __post_init__(self):
        if self.stacks is None:
            self.stacks = {}
        if self.bets is None:
            self.bets = {}
        if self.positions is None:
            self.positions = {}


class NumericParser:
    """Extracts numeric data from poker screenshots via OCR or simulation."""

    def __init__(
        self,
        dry_run: bool = True,
        fallback_to_simulation: bool = True,
    ):
        self.dry_run = dry_run
        self.fallback_to_simulation = fallback_to_simulation
        self._pytesseract = None
        self.ocr_available = False
        if not dry_run:
            self.ocr_available = self._try_load_ocr()

        self.extractions_count = 0
        self.failures_count = 0

        logger.info(
            "NumericParser initialized (dry_run=%s, ocr=%s)",
            dry_run,
            "available" if self.ocr_available else "unavailable",
        )

    def set_dry_run(self, dry_run: bool) -> None:
        """Update dry_run and lazy-load OCR when switching to live."""
        self.dry_run = dry_run
        if not dry_run and not self.ocr_available:
            self.ocr_available = self._try_load_ocr()

    def _try_load_ocr(self) -> bool:
        """Try to load pytesseract and verify tesseract binary."""
        try:
            import pytesseract

            version = pytesseract.get_tesseract_version()
            self._pytesseract = pytesseract
            logger.info("pytesseract loaded (tesseract %s)", version)
            return True
        except Exception as e:
            logger.warning("OCR unavailable — numeric live extract disabled: %s", e)
            self._pytesseract = None
            return False

    def extract_all(
        self,
        screenshot: Optional[np.ndarray] = None,
        roi_dict: Optional[Dict[str, Tuple[int, int, int, int]]] = None,
    ) -> NumericData:
        """Extract all numeric data from screenshot."""
        self.extractions_count += 1

        if self.dry_run:
            return self._simulate_numeric_data()

        try:
            if screenshot is None:
                raise ValueError("screenshot required for live extraction")
            if roi_dict is None:
                raise ValueError("roi_dict required for real extraction")
            if not self.ocr_available:
                self.ocr_available = self._try_load_ocr()
            if not self.ocr_available:
                raise RuntimeError("OCR not available")

            result = NumericData()
            if "pot" in roi_dict:
                result.pot = self._extract_pot(screenshot, roi_dict["pot"])
            result.stacks = self._extract_stacks(screenshot, roi_dict)
            result.bets = self._extract_bets(screenshot, roi_dict)
            result.positions = self._extract_positions(roi_dict)
            result.method = "ocr"
            result.confidence = 0.8 if result.pot > 0 or result.stacks else 0.4
            return result

        except Exception as e:
            logger.error("Numeric extraction error: %s", e)
            self.failures_count += 1

            if self.fallback_to_simulation:
                logger.warning("NumericParser falling back to simulation")
                return self._simulate_numeric_data()

            return NumericData(confidence=0.0, method="error", error=str(e))

    def _crop_roi(
        self,
        screenshot: np.ndarray,
        roi: Tuple[int, int, int, int],
    ) -> Optional[np.ndarray]:
        x, y, w, h = roi
        if w <= 0 or h <= 0:
            return None
        H, W = screenshot.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(W, x1 + int(w)), min(H, y1 + int(h))
        if x2 <= x1 or y2 <= y1:
            return None
        return screenshot[y1:y2, x1:x2]

    def _ocr_roi(self, screenshot: np.ndarray, roi: Tuple[int, int, int, int]) -> float:
        """OCR a single ROI and parse the first numeric value."""
        if self._pytesseract is None:
            return 0.0
        region = self._crop_roi(screenshot, roi)
        if region is None or region.size == 0:
            return 0.0
        try:
            import cv2

            if len(region.shape) == 3:
                gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            else:
                gray = region
            # Upscale tiny ROIs for better OCR
            h, w = gray.shape[:2]
            if h < 40 or w < 60:
                scale = max(2, int(40 / max(h, 1)))
                gray = cv2.resize(
                    gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC
                )
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = self._pytesseract.image_to_string(bw, config=_OCR_CFG).strip()
            if not text:
                text = self._pytesseract.image_to_string(gray, config=_OCR_CFG).strip()
            return self._parse_numeric_text(text)
        except Exception as exc:
            logger.debug("OCR ROI failed: %s", exc)
            return 0.0

    def _extract_pot(
        self,
        screenshot: np.ndarray,
        roi: Tuple[int, int, int, int],
    ) -> float:
        return self._ocr_roi(screenshot, roi)

    def _extract_stacks(
        self,
        screenshot: np.ndarray,
        roi_dict: Dict[str, Tuple[int, int, int, int]],
    ) -> Dict[str, float]:
        stacks = {}
        for player_id, roi in roi_dict.items():
            if "stack" not in player_id.lower():
                continue
            stacks[player_id] = self._ocr_roi(screenshot, roi)
        return stacks

    def _extract_bets(
        self,
        screenshot: np.ndarray,
        roi_dict: Dict[str, Tuple[int, int, int, int]],
    ) -> Dict[str, float]:
        bets = {}
        for player_id, roi in roi_dict.items():
            if "bet" not in player_id.lower():
                continue
            bets[player_id] = self._ocr_roi(screenshot, roi)
        return bets

    def _extract_positions(
        self,
        roi_dict: Dict[str, Tuple[int, int, int, int]],
    ) -> Dict[str, str]:
        positions = {}
        seat_map = {
            "hero": "BTN",
            "seat1": "SB",
            "seat2": "BB",
            "seat3": "UTG",
            "seat4": "MP",
            "seat5": "CO",
        }
        for player_id in roi_dict.keys():
            key = player_id.lower()
            for seat_id, position in seat_map.items():
                if seat_id in key:
                    positions[player_id] = position
                    break
        return positions

    def _parse_numeric_text(self, text: str) -> float:
        """Parse numeric value from OCR text (supports K/M suffixes)."""
        if not text:
            return 0.0
        # Prefer first number-like token
        match = re.search(
            r"([\$₮]?\s*[\d]+(?:[.,]\d+)?)\s*([KkMmBb]{0,2})?",
            text.replace(" ", ""),
        )
        if not match:
            cleaned = re.sub(r"[^\d.,]", "", text).replace(",", "")
            try:
                return float(cleaned) if cleaned else 0.0
            except ValueError:
                return 0.0

        raw = match.group(1)
        suffix = (match.group(2) or "").upper()
        cleaned = re.sub(r"[^\d.,]", "", raw).replace(",", "")
        # Handle European decimal comma when no other separators
        if cleaned.count(",") == 1 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        try:
            value = float(cleaned)
        except ValueError:
            return 0.0

        if "K" in suffix:
            value *= 1000.0
        elif "M" in suffix:
            value *= 1_000_000.0
        return value

    def _simulate_numeric_data(self) -> NumericData:
        return NumericData(
            pot=150.0,
            stacks={
                "hero": 1000.0,
                "seat1": 950.0,
                "seat2": 1100.0,
                "seat3": 800.0,
            },
            bets={
                "hero": 0.0,
                "seat1": 10.0,
                "seat2": 10.0,
                "seat3": 0.0,
            },
            positions={
                "hero": "BTN",
                "seat1": "SB",
                "seat2": "BB",
                "seat3": "UTG",
            },
            confidence=1.0,
            method="simulated",
        )

    def get_statistics(self) -> dict:
        success_rate = 0.0
        if self.extractions_count > 0:
            success_rate = (
                (self.extractions_count - self.failures_count)
                / self.extractions_count
            )
        return {
            "total_extractions": self.extractions_count,
            "failures": self.failures_count,
            "success_rate": success_rate,
            "dry_run": self.dry_run,
            "ocr_available": self.ocr_available,
        }


if __name__ == "__main__":
    parser = NumericParser(dry_run=True)
    data = parser.extract_all()
    print(f"Pot: {data.pot}  method={data.method}")
