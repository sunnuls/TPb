"""
Lobby OCR Module — Phase 1 of lobby_scanner.md.

Captures a poker lobby screenshot and extracts structured table information
via row segmentation + multi-strategy OCR.

Pipeline:
  1. Preprocess (grayscale, denoise, contrast)
  2. Detect individual table rows (horizontal separators / alternating colors)
  3. Segment each row into columns (fixed ratios or vertical lines)
  4. OCR each cell with specialised configs (name, stakes, players, numbers)
  5. Parse raw text into LobbyTable objects

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2

    CV_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CV_AVAILABLE = False

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TESSERACT_AVAILABLE = False

try:
    import easyocr

    EASYOCR_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class LobbyLayout(str, Enum):
    """Supported lobby column layouts."""

    POKERSTARS = "pokerstars"
    GGPOKER = "ggpoker"
    GENERIC = "generic"


@dataclass
class ColumnSpec:
    """Describes a single column inside the lobby table.

    Attributes:
        name:       semantic name (table_name, stakes, players …)
        x_start:    left edge as fraction of row width  [0‥1]
        x_end:      right edge as fraction of row width [0‥1]
        ocr_type:   hint for OCR config selection
    """

    name: str
    x_start: float
    x_end: float
    ocr_type: str = "text"  # text | numeric | stakes | players


@dataclass
class RowBBox:
    """Bounding box of a detected lobby row (absolute pixel coords)."""

    x: int
    y: int
    w: int
    h: int


@dataclass
class CellResult:
    """OCR result for a single cell."""

    column: str
    raw_text: str
    parsed_value: object = None
    confidence: float = 0.0


@dataclass
class LobbyRowResult:
    """Parsed result for one lobby row (= one table)."""

    cells: Dict[str, CellResult] = field(default_factory=dict)
    bbox: Optional[RowBBox] = None
    confidence: float = 0.0

    # Convenience accessors --------------------------------------------------
    def get(self, key: str, default: object = None) -> object:
        cell = self.cells.get(key)
        if cell is None:
            return default
        return cell.parsed_value if cell.parsed_value is not None else default


@dataclass
class LobbyOCRResult:
    """Aggregate result returned by LobbyOCR.scan()."""

    rows: List[LobbyRowResult] = field(default_factory=list)
    layout: LobbyLayout = LobbyLayout.GENERIC
    processing_time_ms: float = 0.0
    image_size: Tuple[int, int] = (0, 0)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Layout presets
# ---------------------------------------------------------------------------

# Column specifications for known poker clients.
# Fractions are *approximate* — the row segmenter will try to refine them
# using detected vertical separators when possible.

LAYOUT_COLUMNS: Dict[LobbyLayout, List[ColumnSpec]] = {
    LobbyLayout.POKERSTARS: [
        ColumnSpec("table_name", 0.00, 0.28, "text"),
        ColumnSpec("game_type", 0.28, 0.38, "text"),
        ColumnSpec("stakes", 0.38, 0.50, "stakes"),
        ColumnSpec("players", 0.50, 0.60, "players"),
        ColumnSpec("avg_pot", 0.60, 0.72, "numeric"),
        ColumnSpec("hands_hr", 0.72, 0.84, "numeric"),
        ColumnSpec("wait", 0.84, 1.00, "numeric"),
    ],
    LobbyLayout.GGPOKER: [
        ColumnSpec("table_name", 0.00, 0.30, "text"),
        ColumnSpec("stakes", 0.30, 0.45, "stakes"),
        ColumnSpec("game_type", 0.45, 0.55, "text"),
        ColumnSpec("players", 0.55, 0.68, "players"),
        ColumnSpec("avg_pot", 0.68, 0.82, "numeric"),
        ColumnSpec("wait", 0.82, 1.00, "numeric"),
    ],
    LobbyLayout.GENERIC: [
        ColumnSpec("table_name", 0.00, 0.30, "text"),
        ColumnSpec("stakes", 0.30, 0.45, "stakes"),
        ColumnSpec("players", 0.45, 0.60, "players"),
        ColumnSpec("avg_pot", 0.60, 0.78, "numeric"),
        ColumnSpec("hands_hr", 0.78, 0.90, "numeric"),
        ColumnSpec("wait", 0.90, 1.00, "numeric"),
    ],
}


# ---------------------------------------------------------------------------
# Tesseract OCR configurations per cell type
# ---------------------------------------------------------------------------

TESS_CONFIGS = {
    "text": "--psm 7 --oem 3",
    "stakes": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.$,/\\",
    "players": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/",
    "numeric": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.$,kKmM",
}

# Secondary configs to try on low‐confidence results
TESS_FALLBACK_CONFIGS = {
    "text": "--psm 6 --oem 3",
    "stakes": "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789.$,/\\",
    "players": "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789/",
    "numeric": "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789.$,kKmM",
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class LobbyOCR:
    """
    OCR engine for poker lobby screenshots.

    Usage::

        ocr = LobbyOCR(layout=LobbyLayout.POKERSTARS)
        result = ocr.scan(image)          # numpy BGR image
        for row in result.rows:
            print(row.get("table_name"), row.get("stakes"), row.get("players"))

    Features:
    - Multi‐strategy image preprocessing (threshold, CLAHE, invert)
    - Row detection via horizontal line / color‐band analysis
    - Column segmentation by layout preset or vertical line detection
    - Per‐cell OCR with type‐specific Tesseract configs
    - Voting across preprocessing variants
    - Parsing of stakes, player counts, and numeric values
    """

    # Minimum row height in pixels — below this we ignore (header / footer)
    MIN_ROW_HEIGHT = 14
    MAX_ROW_HEIGHT_FRAC = 0.15  # max row height as fraction of image

    # Confidence below which we attempt fallback OCR config
    CONFIDENCE_RETRY_THRESHOLD = 0.55

    def __init__(
        self,
        layout: LobbyLayout = LobbyLayout.GENERIC,
        use_easyocr: bool = True,
        min_confidence: float = 0.30,
    ):
        self.layout = layout
        self.columns = LAYOUT_COLUMNS[layout]
        self.use_easyocr = use_easyocr and EASYOCR_AVAILABLE
        self.min_confidence = min_confidence

        self._easyocr_reader: Optional[object] = None

        logger.info("LobbyOCR initialised — layout=%s, easyocr=%s", layout.value, self.use_easyocr)

    # -- public API ----------------------------------------------------------

    def scan(self, image: np.ndarray) -> LobbyOCRResult:
        """Run full lobby OCR pipeline on *image* (BGR numpy array).

        Returns a ``LobbyOCRResult`` with a list of parsed rows.
        """
        if not CV_AVAILABLE:
            return LobbyOCRResult(error="OpenCV not available")
        if not TESSERACT_AVAILABLE and not self.use_easyocr:
            return LobbyOCRResult(error="No OCR backend available (install pytesseract or easyocr)")

        t0 = time.perf_counter()
        h_img, w_img = image.shape[:2]

        # 1. Detect rows
        rows_bboxes = self._detect_rows(image)
        if not rows_bboxes:
            return LobbyOCRResult(
                image_size=(w_img, h_img),
                processing_time_ms=(time.perf_counter() - t0) * 1000,
                error="No table rows detected",
            )

        # 2. OCR each row → cells
        parsed_rows: List[LobbyRowResult] = []
        for bbox in rows_bboxes:
            row_img = image[bbox.y : bbox.y + bbox.h, bbox.x : bbox.x + bbox.w]
            if row_img.size == 0:
                continue
            cells = self._ocr_row(row_img)
            row_conf = (
                sum(c.confidence for c in cells.values()) / max(len(cells), 1)
            )
            parsed_rows.append(
                LobbyRowResult(cells=cells, bbox=bbox, confidence=row_conf)
            )

        elapsed = (time.perf_counter() - t0) * 1000
        return LobbyOCRResult(
            rows=parsed_rows,
            layout=self.layout,
            processing_time_ms=elapsed,
            image_size=(w_img, h_img),
        )

    def detect_layout(self, image: np.ndarray) -> LobbyLayout:
        """Try to auto‐detect which poker client layout the image uses.

        Heuristic: look for distinctive keywords in the top area.
        """
        if not CV_AVAILABLE or not TESSERACT_AVAILABLE:
            return LobbyLayout.GENERIC

        h, w = image.shape[:2]
        header = image[0 : max(1, h // 6), :]
        gray = cv2.cvtColor(header, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, config="--psm 6 --oem 3").lower()

        if "pokerstars" in text or "ps " in text:
            return LobbyLayout.POKERSTARS
        if "ggpoker" in text or "gg " in text:
            return LobbyLayout.GGPOKER

        return LobbyLayout.GENERIC

    # -- row detection -------------------------------------------------------

    def _detect_rows(self, image: np.ndarray) -> List[RowBBox]:
        """Detect individual table rows in the lobby image.

        Strategy:
          1. Convert to grayscale
          2. Apply horizontal projection (sum of white pixels per row)
          3. Find row boundaries where projection drops (separators)
          4. Fall back to fixed-height slicing if no clear separators
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape[:2]

        # Binary threshold – dark text on light bg or light on dark
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Horizontal projection profile
        projection = np.sum(thresh, axis=1).astype(np.float64)
        projection /= max(projection.max(), 1)

        # Detect separator lines (low‐projection valleys)
        rows = self._rows_from_projection(projection, w_img, h_img)

        if len(rows) < 2:
            # Fallback: try edge detection for horizontal lines
            rows = self._rows_from_edges(gray, w_img, h_img)

        if len(rows) < 2:
            # Fallback: try alternating row colours
            rows = self._rows_from_color_bands(image)

        if len(rows) < 2:
            # Last resort: fixed height slicing
            rows = self._rows_fixed_height(h_img, w_img)

        return rows

    def _rows_from_projection(
        self, projection: np.ndarray, w: int, h: int
    ) -> List[RowBBox]:
        """Use horizontal projection valleys to find separators."""
        # Smooth
        kernel_size = max(3, h // 80) | 1  # ensure odd
        smoothed = np.convolve(projection, np.ones(kernel_size) / kernel_size, mode="same")

        # Threshold for "low" projection (separator)
        threshold = 0.35
        is_low = smoothed < threshold

        # Find transitions low→high (start of row) and high→low (end of row)
        rows: List[RowBBox] = []
        in_row = False
        row_start = 0

        for y in range(len(is_low)):
            if not in_row and not is_low[y]:
                in_row = True
                row_start = y
            elif in_row and is_low[y]:
                in_row = False
                rh = y - row_start
                if self.MIN_ROW_HEIGHT <= rh <= h * self.MAX_ROW_HEIGHT_FRAC:
                    rows.append(RowBBox(x=0, y=row_start, w=w, h=rh))

        # Capture last row if still open
        if in_row:
            rh = h - row_start
            if self.MIN_ROW_HEIGHT <= rh <= h * self.MAX_ROW_HEIGHT_FRAC:
                rows.append(RowBBox(x=0, y=row_start, w=w, h=rh))

        return rows

    def _rows_from_edges(
        self, gray: np.ndarray, w: int, h: int
    ) -> List[RowBBox]:
        """Detect horizontal lines (edges) as row separators."""
        edges = cv2.Canny(gray, 50, 150)

        # Morphology: keep only long horizontal segments
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
        horiz = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horiz_kernel)

        # Row profile of horizontal edges
        profile = np.sum(horiz, axis=1).astype(np.float64)
        profile /= max(profile.max(), 1)

        # Peaks in profile → separator y‐positions
        sep_threshold = 0.3
        seps: List[int] = []
        prev_high = False
        for y, val in enumerate(profile):
            if val > sep_threshold and not prev_high:
                seps.append(y)
                prev_high = True
            elif val <= sep_threshold:
                prev_high = False

        rows: List[RowBBox] = []
        for i in range(len(seps) - 1):
            y0 = seps[i]
            y1 = seps[i + 1]
            rh = y1 - y0
            if self.MIN_ROW_HEIGHT <= rh <= h * self.MAX_ROW_HEIGHT_FRAC:
                rows.append(RowBBox(x=0, y=y0, w=w, h=rh))

        return rows

    def _rows_from_color_bands(self, image: np.ndarray) -> List[RowBBox]:
        """Detect alternating colour bands (zebra striping) in the lobby."""
        h_img, w_img = image.shape[:2]
        # Average colour per row
        avg = np.mean(image, axis=1)  # shape (h, 3)
        luma = 0.299 * avg[:, 2] + 0.587 * avg[:, 1] + 0.114 * avg[:, 0]

        # Quantise luma to 2 levels
        median_luma = np.median(luma)
        band = (luma > median_luma).astype(np.int8)

        rows: List[RowBBox] = []
        in_band = band[0]
        band_start = 0

        for y in range(1, len(band)):
            if band[y] != in_band:
                rh = y - band_start
                if self.MIN_ROW_HEIGHT <= rh <= h_img * self.MAX_ROW_HEIGHT_FRAC:
                    rows.append(RowBBox(x=0, y=band_start, w=w_img, h=rh))
                band_start = y
                in_band = band[y]

        # Last band
        rh = h_img - band_start
        if self.MIN_ROW_HEIGHT <= rh <= h_img * self.MAX_ROW_HEIGHT_FRAC:
            rows.append(RowBBox(x=0, y=band_start, w=w_img, h=rh))

        return rows

    def _rows_fixed_height(self, h: int, w: int, row_h: int = 0) -> List[RowBBox]:
        """Fall back to evenly spaced rows."""
        if row_h <= 0:
            row_h = max(self.MIN_ROW_HEIGHT, h // 15)
        rows: List[RowBBox] = []
        y = 0
        while y + row_h <= h:
            rows.append(RowBBox(x=0, y=y, w=w, h=row_h))
            y += row_h
        return rows

    # -- column segmentation + OCR -------------------------------------------

    def _ocr_row(self, row_img: np.ndarray) -> Dict[str, CellResult]:
        """Segment *row_img* into columns and OCR each cell."""
        rh, rw = row_img.shape[:2]
        cells: Dict[str, CellResult] = {}

        for col in self.columns:
            x0 = int(col.x_start * rw)
            x1 = int(col.x_end * rw)
            cell_img = row_img[:, x0:x1]
            if cell_img.size == 0:
                continue

            raw, conf = self._ocr_cell(cell_img, col.ocr_type)
            parsed = self._parse_cell(raw, col.ocr_type, col.name)

            cells[col.name] = CellResult(
                column=col.name,
                raw_text=raw,
                parsed_value=parsed,
                confidence=conf,
            )

        return cells

    def _ocr_cell(self, cell_img: np.ndarray, ocr_type: str) -> Tuple[str, float]:
        """OCR a single cell using multiple preprocessing variants.

        Returns (best_text, confidence).
        """
        variants = self._preprocess_variants(cell_img)

        results: List[Tuple[str, float]] = []

        for var_img in variants:
            text, conf = self._tesseract_ocr(var_img, ocr_type)
            if text:
                results.append((text, conf))

        # Try EasyOCR as extra voter
        if self.use_easyocr:
            text, conf = self._easyocr_ocr(cell_img)
            if text:
                results.append((text, conf))

        if not results:
            return "", 0.0

        # Pick best by confidence, with optional voting
        return self._vote(results)

    def _tesseract_ocr(self, gray_img: np.ndarray, ocr_type: str) -> Tuple[str, float]:
        """Run Tesseract on a grayscale image."""
        if not TESSERACT_AVAILABLE:
            return "", 0.0

        config = TESS_CONFIGS.get(ocr_type, TESS_CONFIGS["text"])
        try:
            data = pytesseract.image_to_data(
                gray_img, config=config, output_type=pytesseract.Output.DICT
            )
        except Exception as exc:
            logger.debug("Tesseract error: %s", exc)
            return "", 0.0

        texts = []
        confs = []
        for i, conf in enumerate(data["conf"]):
            c = float(conf)
            if c < 0:
                continue
            t = str(data["text"][i]).strip()
            if t:
                texts.append(t)
                confs.append(c / 100.0)

        if not texts:
            return "", 0.0

        combined = " ".join(texts)
        avg_conf = sum(confs) / len(confs)

        # If confidence is low, try fallback config
        if avg_conf < self.CONFIDENCE_RETRY_THRESHOLD:
            fb_config = TESS_FALLBACK_CONFIGS.get(ocr_type)
            if fb_config:
                try:
                    fb_data = pytesseract.image_to_data(
                        gray_img, config=fb_config, output_type=pytesseract.Output.DICT
                    )
                    fb_texts = []
                    fb_confs = []
                    for i, c in enumerate(fb_data["conf"]):
                        cf = float(c)
                        if cf < 0:
                            continue
                        t = str(fb_data["text"][i]).strip()
                        if t:
                            fb_texts.append(t)
                            fb_confs.append(cf / 100.0)
                    if fb_texts:
                        fb_combined = " ".join(fb_texts)
                        fb_avg = sum(fb_confs) / len(fb_confs)
                        if fb_avg > avg_conf:
                            return fb_combined, fb_avg
                except Exception:
                    pass

        return combined, avg_conf

    def _easyocr_ocr(self, cell_img: np.ndarray) -> Tuple[str, float]:
        """Run EasyOCR on a cell image (BGR or gray)."""
        reader = self._get_easyocr()
        if reader is None:
            return "", 0.0

        try:
            if len(cell_img.shape) == 2:
                img = cell_img
            else:
                img = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)

            results = reader.readtext(img)
            if not results:
                return "", 0.0

            texts = [r[1] for r in results]
            confs = [r[2] for r in results]
            combined = " ".join(texts)
            avg_conf = sum(confs) / len(confs)
            return combined, avg_conf
        except Exception as exc:
            logger.debug("EasyOCR error: %s", exc)
            return "", 0.0

    def _get_easyocr(self):
        """Lazy-init EasyOCR reader."""
        if self._easyocr_reader is None and self.use_easyocr:
            try:
                self._easyocr_reader = easyocr.Reader(["en"], gpu=False)
            except Exception as exc:
                logger.warning("EasyOCR init failed: %s", exc)
                self.use_easyocr = False
        return self._easyocr_reader

    # -- preprocessing -------------------------------------------------------

    @staticmethod
    def _preprocess_variants(cell_img: np.ndarray) -> List[np.ndarray]:
        """Generate multiple grayscale preprocessing variants for voting."""
        if len(cell_img.shape) == 3:
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = cell_img.copy()

        variants: List[np.ndarray] = []

        # 1. Raw grayscale
        variants.append(gray)

        # 2. Otsu threshold
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)

        # 3. CLAHE + threshold
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        _, clahe_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(clahe_thresh)

        # 4. Inverted (for light text on dark bg)
        inverted = cv2.bitwise_not(otsu)
        variants.append(inverted)

        # 5. Gaussian blur + thresh (reduce noise)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, blur_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(blur_thresh)

        return variants

    # -- voting --------------------------------------------------------------

    @staticmethod
    def _vote(results: List[Tuple[str, float]]) -> Tuple[str, float]:
        """Pick the best OCR result using frequency + confidence voting."""
        if not results:
            return "", 0.0
        if len(results) == 1:
            return results[0]

        # Count how often each normalised text appears
        counts: Dict[str, Tuple[int, float]] = {}
        for text, conf in results:
            key = text.strip().lower()
            if not key:
                continue
            if key in counts:
                old_count, old_conf = counts[key]
                counts[key] = (old_count + 1, max(old_conf, conf))
            else:
                counts[key] = (1, conf)

        if not counts:
            # All empty → return highest-confidence raw
            return max(results, key=lambda r: r[1])

        # Sort by (count desc, confidence desc)
        best_key = max(counts, key=lambda k: (counts[k][0], counts[k][1]))
        best_conf = counts[best_key][1]

        # Return original-case version
        for text, conf in results:
            if text.strip().lower() == best_key:
                return text.strip(), best_conf

        return results[0]

    # -- parsing -------------------------------------------------------------

    def _parse_cell(self, raw: str, ocr_type: str, col_name: str) -> object:
        """Parse raw OCR text based on expected type."""
        raw = raw.strip()
        if not raw:
            return None

        if ocr_type == "stakes":
            return self._parse_stakes(raw)
        elif ocr_type == "players":
            return self._parse_players(raw)
        elif ocr_type == "numeric":
            return self._parse_numeric(raw)
        else:
            return raw  # text — return as-is

    @staticmethod
    def _parse_stakes(raw: str) -> str:
        """Parse stakes like '0.25/0.50', '$1/$2', '25/50'."""
        # Clean common OCR artefacts
        cleaned = raw.replace("\\", "/").replace("|", "/").replace("l", "1")
        cleaned = cleaned.replace("$", "").replace("€", "").strip()

        # Try to find pattern N/N
        match = re.search(r"(\d+\.?\d*)\s*[/]\s*(\d+\.?\d*)", cleaned)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return cleaned

    @staticmethod
    def _parse_players(raw: str) -> Tuple[int, int]:
        """Parse player counts like '5/9', '3/6'.

        Returns (occupied, max_seats).
        """
        cleaned = raw.replace("\\", "/").replace("|", "/").replace("l", "1")
        match = re.search(r"(\d+)\s*/\s*(\d+)", cleaned)
        if match:
            return (int(match.group(1)), int(match.group(2)))

        # Single number — assume occupied out of 9
        digits = re.findall(r"\d+", cleaned)
        if digits:
            return (int(digits[0]), 9)

        return (0, 9)

    @staticmethod
    def _parse_numeric(raw: str) -> float:
        """Parse a numeric value, handling $, k, m suffixes."""
        cleaned = raw.replace("$", "").replace("€", "").replace(",", "").strip()

        # Handle k/m/b multipliers
        multiplier = 1.0
        if cleaned and cleaned[-1].lower() in ("k", "м"):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        elif cleaned and cleaned[-1].lower() in ("m",):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        elif cleaned and cleaned[-1].lower() in ("b",):
            multiplier = 1_000_000_000
            cleaned = cleaned[:-1]

        try:
            return float(cleaned) * multiplier
        except (ValueError, TypeError):
            return 0.0

    # -- conversion to LobbyTable -------------------------------------------

    def to_lobby_tables(self, result: LobbyOCRResult) -> list:
        """Convert OCR result rows into launcher-compatible LobbyTable dicts.

        Each dict has keys matching ``launcher.lobby_scanner.LobbyTable`` fields.
        The caller can unpack these into LobbyTable instances.
        """
        tables: list = []
        for i, row in enumerate(result.rows):
            players = row.get("players", (0, 9))
            if isinstance(players, tuple):
                occupied, max_seats = players
            else:
                occupied, max_seats = 0, 9

            table = {
                "table_id": f"ocr_{i + 1:03d}",
                "table_name": row.get("table_name", f"Table {i + 1}") or f"Table {i + 1}",
                "game_type": row.get("game_type", "NLHE") or "NLHE",
                "stakes": row.get("stakes", "0/0") or "0/0",
                "players_seated": occupied,
                "max_seats": max_seats,
                "avg_pot": row.get("avg_pot", 0.0) or 0.0,
                "hands_per_hour": int(row.get("hands_hr", 0) or 0),
                "waiting": int(row.get("wait", 0) or 0),
            }
            tables.append(table)

        return tables

    # -- debug / visualisation -----------------------------------------------

    def debug_image(self, image: np.ndarray, result: LobbyOCRResult) -> np.ndarray:
        """Draw detected rows and OCR text on *image* for debugging.

        Returns annotated image copy (BGR).
        """
        vis = image.copy()
        h, w = vis.shape[:2]

        for i, row in enumerate(result.rows):
            if row.bbox is None:
                continue
            b = row.bbox
            # Row rectangle
            color = (0, 255, 0) if row.confidence > 0.5 else (0, 165, 255)
            cv2.rectangle(vis, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 1)

            # Row index
            cv2.putText(
                vis,
                f"#{i}",
                (b.x + 2, b.y + b.h - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                color,
                1,
            )

            # Column cells
            for col in self.columns:
                x0 = b.x + int(col.x_start * b.w)
                x1 = b.x + int(col.x_end * b.w)
                # Column separator
                cv2.line(vis, (x0, b.y), (x0, b.y + b.h), (128, 128, 128), 1)

                cell = row.cells.get(col.name)
                if cell and cell.raw_text:
                    label = f"{cell.raw_text[:12]}"
                    cv2.putText(
                        vis,
                        label,
                        (x0 + 2, b.y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.30,
                        (255, 255, 255),
                        1,
                    )

        return vis
