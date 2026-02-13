"""
Auto ROI Finder — automatic calibration of ROI zones by visual anchors.

Phase 1 of vision_fragility.md.

Detects anchors (buttons, table felt, card shapes, text) and infers
all standard ROI zones from their relative positions.

Works across different skins, resolutions, and themes.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2

    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class AnchorType(Enum):
    """How the anchor was detected."""
    TEXT = "text"
    COLOR = "color"
    SHAPE = "shape"
    EDGE = "edge"


@dataclass
class Anchor:
    """A detected visual anchor used to infer ROI positions."""
    anchor_type: AnchorType
    name: str
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)


@dataclass
class CalibrationResult:
    """Result of auto-calibration."""
    zones: Dict[str, Tuple[int, int, int, int]]  # name → (x, y, w, h)
    anchors_found: List[Anchor]
    confidence: float  # overall 0-1
    resolution: Tuple[int, int]
    elapsed_ms: float = 0.0

    @property
    def zone_count(self) -> int:
        return len(self.zones)

    def summary(self) -> str:
        lines = [
            f"Calibration: {self.zone_count} zones, "
            f"confidence {self.confidence:.0%}, "
            f"{len(self.anchors_found)} anchors, "
            f"{self.elapsed_ms:.0f}ms",
        ]
        for name, (x, y, w, h) in sorted(self.zones.items()):
            lines.append(f"  {name:25s} → ({x:4d}, {y:4d}, {w:3d}, {h:3d})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Keyword lists used by text-anchor detector
# ---------------------------------------------------------------------------

BUTTON_KEYWORDS = {
    "fold":  ["fold", "сбросить", "пас"],
    "check": ["check", "чек"],
    "call":  ["call", "колл", "уравнять"],
    "raise": ["raise", "рейз", "повысить"],
    "bet":   ["bet", "ставка"],
    "allin": ["all-in", "all in", "олл-ин", "ва-банк"],
}

POT_KEYWORDS = ["pot", "пот", "банк", "total"]


# ---------------------------------------------------------------------------
# AutoROIFinder
# ---------------------------------------------------------------------------

class AutoROIFinder:
    """
    Finds ROI zones automatically using visual anchors.

    Strategy (priority order):
        1. Text anchors  — OCR for button labels (Fold/Call/Raise) & pot text
        2. Color anchors — table felt (green), colored action buttons
        3. Shape anchors — card-shaped rectangles, dealer button circle
        4. Edge anchors  — table boundary (ellipse / rectangle)

    From anchors the class infers *all* standard ROI zones relative to the
    detected table geometry.
    """

    # Felt color ranges (HSV) — covers many poker skins
    FELT_RANGES = [
        # Classic green
        (np.array([30, 30, 30]),  np.array([85, 255, 200])),
        # Dark teal / blue-green
        (np.array([85, 25, 20]),  np.array([110, 255, 180])),
        # Dark/blue tables
        (np.array([100, 30, 15]), np.array([135, 255, 160])),
        # Red felt
        (np.array([0, 50, 50]),   np.array([15, 255, 200])),
        (np.array([165, 50, 50]), np.array([180, 255, 200])),
    ]

    # Button color ranges (HSV)
    BUTTON_COLOR_RANGES = {
        "green_btn": (np.array([35, 60, 60]),  np.array([85, 255, 255])),
        "red_btn":   (np.array([0, 80, 80]),   np.array([12, 255, 255])),
        "blue_btn":  (np.array([100, 60, 60]), np.array([130, 255, 255])),
        "yellow_btn":(np.array([20, 80, 80]),  np.array([35, 255, 255])),
    }

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_lang: str = "eng+rus",
        min_felt_area_ratio: float = 0.08,
    ):
        self.use_ocr = use_ocr and TESSERACT_AVAILABLE
        self.ocr_lang = ocr_lang
        self.min_felt_area_ratio = min_felt_area_ratio

        if not CV_AVAILABLE:
            raise RuntimeError("OpenCV (cv2) is required for AutoROIFinder")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_rois(
        self,
        image: np.ndarray,
        account_id: str = "auto",
    ) -> CalibrationResult:
        """
        Main entry — analyse *image* and return calibrated ROI zones.

        Args:
            image:      BGR numpy array (screenshot of poker table)
            account_id: optional account id for the resulting ROIConfig

        Returns:
            CalibrationResult with zones, anchors, confidence
        """
        t0 = time.perf_counter()
        h, w = image.shape[:2]
        resolution = (w, h)

        # --- Step 1: collect anchors ---
        anchors: List[Anchor] = []
        anchors += self._find_table_boundary(image)
        anchors += self._find_color_anchors(image)
        if self.use_ocr:
            anchors += self._find_text_anchors(image)
        anchors += self._find_card_shapes(image)

        logger.info(
            "Anchors found: %d (text=%d, color=%d, shape=%d, edge=%d)",
            len(anchors),
            sum(1 for a in anchors if a.anchor_type == AnchorType.TEXT),
            sum(1 for a in anchors if a.anchor_type == AnchorType.COLOR),
            sum(1 for a in anchors if a.anchor_type == AnchorType.SHAPE),
            sum(1 for a in anchors if a.anchor_type == AnchorType.EDGE),
        )

        # --- Step 2: infer ROIs from anchors ---
        zones = self._infer_rois(anchors, w, h)

        # --- Step 3: confidence ---
        confidence = self._calc_confidence(anchors, zones)

        elapsed = (time.perf_counter() - t0) * 1000

        result = CalibrationResult(
            zones=zones,
            anchors_found=anchors,
            confidence=confidence,
            resolution=resolution,
            elapsed_ms=elapsed,
        )
        logger.info(result.summary())
        return result

    # ------------------------------------------------------------------
    # Anchor detectors
    # ------------------------------------------------------------------

    def _find_table_boundary(self, image: np.ndarray) -> List[Anchor]:
        """Detect the table felt region and return its bounding rect as an EDGE anchor."""
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        total_pixels = h * w

        best_mask = None
        best_area = 0

        for lo, hi in self.FELT_RANGES:
            mask = cv2.inRange(hsv, lo, hi)
            # Morphology to clean noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            area = cv2.countNonZero(mask)
            if area > best_area:
                best_area = area
                best_mask = mask

        if best_mask is None or best_area / total_pixels < self.min_felt_area_ratio:
            logger.debug("Table felt not detected (best ratio %.2f%%)", 100 * best_area / total_pixels)
            return []

        # Largest contour → table boundary
        contours, _ = cv2.findContours(best_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        largest = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(largest)

        conf = min(1.0, (best_area / total_pixels) / 0.30)  # 30% ≈ full confidence

        return [Anchor(
            anchor_type=AnchorType.EDGE,
            name="table_boundary",
            bbox=(x, y, bw, bh),
            confidence=conf,
            metadata={"felt_ratio": best_area / total_pixels},
        )]

    def _find_color_anchors(self, image: np.ndarray) -> List[Anchor]:
        """Detect coloured buttons (green/red/blue/yellow).

        Subtracts the table-felt mask so buttons sitting on a same-colour
        felt (e.g. green buttons on green felt) can still be separated.
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_img, w_img = image.shape[:2]

        # Build a felt mask to subtract (buttons are brighter / more saturated)
        felt_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        for lo, hi in self.FELT_RANGES:
            felt_mask |= cv2.inRange(hsv, lo, hi)
        kernel_big = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        felt_mask = cv2.morphologyEx(felt_mask, cv2.MORPH_CLOSE, kernel_big)
        felt_mask = cv2.morphologyEx(felt_mask, cv2.MORPH_OPEN, kernel_big)

        # Use brightness to separate buttons from felt: buttons tend to be
        # brighter than the surrounding felt.
        v_channel = hsv[:, :, 2]
        bright_mask = cv2.threshold(v_channel, 140, 255, cv2.THRESH_BINARY)[1]

        anchors: List[Anchor] = []

        for label, (lo, hi) in self.BUTTON_COLOR_RANGES.items():
            mask = cv2.inRange(hsv, lo, hi)

            # Subtract large felt blobs: keep only small bright regions
            # (buttons are bright + small, felt is large + dimmer)
            mask_no_felt = cv2.bitwise_and(mask, cv2.bitwise_or(bright_mask, cv2.bitwise_not(felt_mask)))

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask_no_felt = cv2.morphologyEx(mask_no_felt, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask_no_felt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                x, y, bw, bh = cv2.boundingRect(cnt)
                # Button-like aspect ratio & reasonable size
                if bw < 25 or bh < 12 or bw > w_img * 0.3 or bh > h_img * 0.15:
                    continue
                aspect = bw / bh
                if not (1.0 < aspect < 7.0):
                    continue
                # Buttons usually in bottom 55% of image
                if y < h_img * 0.45:
                    continue

                area = cv2.contourArea(cnt)
                rect_area = bw * bh
                fill = area / rect_area if rect_area else 0
                if fill < 0.4:
                    continue

                anchors.append(Anchor(
                    anchor_type=AnchorType.COLOR,
                    name=label,
                    bbox=(x, y, bw, bh),
                    confidence=min(1.0, fill),
                    metadata={"fill": fill, "aspect": aspect},
                ))

        # Deduplicate overlapping
        anchors = self._dedupe_anchors(anchors, iou_thresh=0.4)
        return anchors

    def _find_text_anchors(self, image: np.ndarray) -> List[Anchor]:
        """OCR-based anchor detection for button labels and pot text."""
        if not self.use_ocr:
            return []

        anchors: List[Anchor] = []
        try:
            data = pytesseract.image_to_data(
                image, lang=self.ocr_lang, output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            logger.warning("OCR failed: %s", e)
            return []

        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if not text or conf < 25:
                continue

            x, y, bw, bh = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            text_low = text.lower()

            # Check button keywords
            for btn_name, keywords in BUTTON_KEYWORDS.items():
                if any(kw in text_low for kw in keywords):
                    anchors.append(Anchor(
                        anchor_type=AnchorType.TEXT,
                        name=f"btn_{btn_name}",
                        bbox=(x, y, bw, bh),
                        confidence=conf / 100.0,
                        metadata={"raw_text": text},
                    ))
                    break

            # Check pot keywords
            if any(kw in text_low for kw in POT_KEYWORDS):
                anchors.append(Anchor(
                    anchor_type=AnchorType.TEXT,
                    name="pot_label",
                    bbox=(x, y, bw, bh),
                    confidence=conf / 100.0,
                    metadata={"raw_text": text},
                ))

        return anchors

    def _find_card_shapes(self, image: np.ndarray) -> List[Anchor]:
        """Detect card-shaped white/light rectangles with rounded corners."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h_img, w_img = image.shape[:2]

        # Cards are usually light-coloured with distinct edges
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        anchors: List[Anchor] = []
        # Expected card proportions (h/w ≈ 1.3-1.6)
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw < 20 or bh < 25:
                continue
            if bw > w_img * 0.12 or bh > h_img * 0.18:
                continue
            ratio = bh / bw if bw else 0
            if not (1.1 < ratio < 1.8):
                continue

            area = cv2.contourArea(cnt)
            rect_area = bw * bh
            fill = area / rect_area if rect_area else 0
            if fill < 0.70:
                continue

            anchors.append(Anchor(
                anchor_type=AnchorType.SHAPE,
                name="card",
                bbox=(x, y, bw, bh),
                confidence=min(1.0, fill),
                metadata={"ratio": ratio},
            ))

        anchors = self._dedupe_anchors(anchors, iou_thresh=0.3)
        return anchors

    # ------------------------------------------------------------------
    # ROI inference from anchors
    # ------------------------------------------------------------------

    def _infer_rois(
        self,
        anchors: List[Anchor],
        img_w: int,
        img_h: int,
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """
        From detected anchors, produce the standard ROI zones.

        Strategies (in priority order):
            A. Button-anchored — if we found Fold/Call/Raise text or colored buttons
            B. Felt-anchored   — from table boundary
            C. Proportional fallback — assume standard proportions
        """
        zones: Dict[str, Tuple[int, int, int, int]] = {}

        # Gather categorized anchors
        table_anchor = self._best_anchor(anchors, "table_boundary")
        btn_anchors = self._button_anchors(anchors)
        card_anchors = [a for a in anchors if a.name == "card"]
        pot_anchor = self._best_anchor(anchors, "pot_label")

        # Table bounding box (or full image)
        if table_anchor:
            tx, ty, tw, th = table_anchor.bbox
        else:
            tx, ty, tw, th = 0, 0, img_w, img_h

        tcx, tcy = tx + tw // 2, ty + th // 2  # table center

        # --- A) ACTION BUTTONS ---
        if btn_anchors:
            self._place_buttons_from_anchors(zones, btn_anchors, img_w, img_h)
        else:
            # Estimate buttons in bottom area of table
            btn_y = ty + int(th * 0.88)
            btn_h = max(30, int(th * 0.04))
            btn_w = max(70, int(tw * 0.07))
            gap = int(tw * 0.01)
            start_x = tcx - int(1.5 * btn_w + gap)
            for i, name in enumerate(["fold_button", "check_button", "call_button", "raise_button"]):
                zones[name] = (start_x + i * (btn_w + gap), btn_y, btn_w, btn_h)

        # --- B) HERO CARDS ---
        hero_cards = self._pick_hero_cards(card_anchors, tcx, tcy, ty + th)
        if hero_cards and len(hero_cards) >= 2:
            for idx, a in enumerate(hero_cards[:2]):
                zones[f"hero_card_{idx + 1}"] = a.bbox
        else:
            # Estimate hero cards bottom-center
            cw = max(55, int(tw * 0.045))
            ch = max(75, int(th * 0.11))
            cy = ty + int(th * 0.76)
            zones["hero_card_1"] = (tcx - cw - 5, cy, cw, ch)
            zones["hero_card_2"] = (tcx + 5, cy, cw, ch)

        # --- C) BOARD CARDS ---
        board_cards = self._pick_board_cards(card_anchors, tcx, tcy)
        if board_cards and len(board_cards) >= 3:
            for idx, a in enumerate(board_cards[:5]):
                zones[f"board_card_{idx + 1}"] = a.bbox
            # If fewer than 5 found, extrapolate remaining
            if len(board_cards) < 5:
                self._extrapolate_board(zones, board_cards, tcx)
        else:
            cw = max(50, int(tw * 0.04))
            ch = max(68, int(th * 0.09))
            gap = max(5, int(tw * 0.005))
            total_w = 5 * cw + 4 * gap
            start_x = tcx - total_w // 2
            cy = tcy - ch // 2
            for idx in range(5):
                zones[f"board_card_{idx + 1}"] = (start_x + idx * (cw + gap), cy, cw, ch)

        # --- D) POT ---
        if pot_anchor:
            px, py, pw, ph = pot_anchor.bbox
            # Widen the zone to capture the amount next to the label
            zones["pot"] = (px, py, max(pw, int(tw * 0.12)), ph)
        else:
            pw = max(140, int(tw * 0.12))
            ph = max(30, int(th * 0.04))
            zones["pot"] = (tcx - pw // 2, tcy - int(th * 0.15), pw, ph)

        # --- E) BET INPUT ---
        if "raise_button" in zones:
            rx, ry, rw, rh = zones["raise_button"]
            zones["bet_input"] = (rx, ry - rh - 5, rw, rh)
        else:
            biw = max(80, int(tw * 0.06))
            bih = max(25, int(th * 0.03))
            zones["bet_input"] = (tcx + int(tw * 0.06), ty + int(th * 0.82), biw, bih)

        # --- F) STACKS (hero + up to 5 villains) ---
        # Hero stack below hero cards
        if "hero_card_1" in zones:
            hx, hy, hw, hh = zones["hero_card_1"]
            sw = max(100, int(tw * 0.08))
            sh = max(22, int(th * 0.03))
            zones["hero_stack"] = (tcx - sw // 2, hy + hh + 5, sw, sh)
        else:
            sw = max(100, int(tw * 0.08))
            sh = max(22, int(th * 0.03))
            zones["hero_stack"] = (tcx - sw // 2, ty + int(th * 0.90), sw, sh)

        # Villain stacks around the table (elliptical layout)
        self._place_villain_stacks(zones, tx, ty, tw, th)

        # Clamp all zones to image bounds
        zones = self._clamp_zones(zones, img_w, img_h)

        return zones

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    def _place_buttons_from_anchors(
        self,
        zones: Dict,
        btn_anchors: Dict[str, Anchor],
        img_w: int,
        img_h: int,
    ) -> None:
        """Place action-button zones from detected text/color anchors."""
        # Map named text anchors first
        name_map = {
            "btn_fold": "fold_button",
            "btn_check": "check_button",
            "btn_call": "call_button",
            "btn_raise": "raise_button",
            "btn_bet": "raise_button",
            "btn_allin": "raise_button",
        }
        for anchor_name, zone_name in name_map.items():
            if anchor_name in btn_anchors:
                a = btn_anchors[anchor_name]
                zones[zone_name] = a.bbox

        # If no named buttons mapped, use color-detected buttons
        # sorted left-to-right → assign Fold/Check/Call/Raise order
        placed = sum(1 for n in ("fold_button", "check_button", "call_button", "raise_button") if n in zones)
        if placed == 0:
            color_btns = sorted(btn_anchors.values(), key=lambda a: a.center[0])
            btn_names = ["fold_button", "check_button", "call_button", "raise_button"]
            for i, anchor in enumerate(color_btns[:4]):
                zones[btn_names[i]] = anchor.bbox

        # If check_button missing but call_button found, alias it
        if "call_button" in zones and "check_button" not in zones:
            zones["check_button"] = zones["call_button"]

        # Fill missing buttons by extrapolation from known ones
        known = [(n, zones[n]) for n in ("fold_button", "check_button", "call_button", "raise_button") if n in zones]
        if known and len(known) < 4:
            # Estimate button width/height and y from first known
            _, (_, ky, kw, kh) = known[0]
            xs = sorted(bx for _, (bx, _, _, _) in known)
            if len(xs) >= 2:
                avg_gap = (xs[-1] - xs[0]) / (len(xs) - 1)
            else:
                avg_gap = kw + 10

            # Place missing
            all_names = ["fold_button", "check_button", "call_button", "raise_button"]
            for i, name in enumerate(all_names):
                if name not in zones:
                    est_x = int(xs[0] + i * avg_gap)
                    zones[name] = (est_x, ky, kw, kh)

    def _pick_hero_cards(
        self,
        card_anchors: List[Anchor],
        tcx: int,
        tcy: int,
        table_bottom: int,
    ) -> List[Anchor]:
        """Pick the two card-shaped anchors most likely to be hero cards."""
        if len(card_anchors) < 2:
            return []
        # Hero cards: close to center-x, in bottom 40% of table
        threshold_y = tcy + (table_bottom - tcy) * 0.2
        candidates = [a for a in card_anchors if a.center[1] > threshold_y]
        # Sort by proximity to center-x
        candidates.sort(key=lambda a: abs(a.center[0] - tcx))
        # Take the two closest that are side-by-side
        if len(candidates) >= 2:
            # Ensure they are horizontally adjacent (not too far apart)
            c0, c1 = candidates[0], candidates[1]
            dx = abs(c0.center[0] - c1.center[0])
            _, _, w0, _ = c0.bbox
            if dx < w0 * 3:
                return sorted([c0, c1], key=lambda a: a.center[0])
        return []

    def _pick_board_cards(
        self,
        card_anchors: List[Anchor],
        tcx: int,
        tcy: int,
    ) -> List[Anchor]:
        """Pick card anchors in the center of the table (board cards)."""
        if not card_anchors:
            return []
        # Board cards: near vertical center, close to horizontal center
        candidates = []
        for a in card_anchors:
            cx, cy = a.center
            if abs(cy - tcy) < tcy * 0.3:
                candidates.append(a)
        candidates.sort(key=lambda a: a.center[0])
        return candidates[:5]

    def _extrapolate_board(
        self,
        zones: Dict,
        found: List[Anchor],
        tcx: int,
    ) -> None:
        """Fill in missing board card slots (up to 5) by extrapolation."""
        if not found:
            return
        xs = [a.bbox[0] for a in found]
        _, _, cw, ch = found[0].bbox
        y = found[0].bbox[1]
        if len(xs) >= 2:
            gap = (xs[-1] - xs[0]) / (len(xs) - 1)
        else:
            gap = cw + 5
        # Existing indices
        existing = set()
        for idx in range(5):
            if f"board_card_{idx + 1}" in zones:
                existing.add(idx)
        start_x = xs[0] - list(existing)[0] * gap if existing else tcx - 2 * gap
        for idx in range(5):
            key = f"board_card_{idx + 1}"
            if key not in zones:
                zones[key] = (int(start_x + idx * gap), y, cw, ch)

    def _place_villain_stacks(
        self,
        zones: Dict,
        tx: int, ty: int, tw: int, th: int,
    ) -> None:
        """Place villain stack zones in an elliptical layout around the table."""
        import math
        cx, cy = tx + tw // 2, ty + th // 2
        rx, ry = tw * 0.42, th * 0.38

        sw = max(90, int(tw * 0.07))
        sh = max(20, int(th * 0.028))

        # 5 villain positions: left, top-left, top, top-right, right
        angles_deg = [200, 150, 90, 30, 340]
        for i, angle in enumerate(angles_deg, start=1):
            rad = math.radians(angle)
            px = int(cx + rx * math.cos(rad) - sw // 2)
            py = int(cy - ry * math.sin(rad) - sh // 2)
            zones[f"villain_{i}_stack"] = (px, py, sw, sh)

    @staticmethod
    def _clamp_zones(
        zones: Dict[str, Tuple[int, int, int, int]],
        img_w: int,
        img_h: int,
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Clamp all zone coordinates to stay within image bounds."""
        clamped = {}
        for name, (x, y, w, h) in zones.items():
            x = max(0, min(x, img_w - 1))
            y = max(0, min(y, img_h - 1))
            w = max(1, min(w, img_w - x))
            h = max(1, min(h, img_h - y))
            clamped[name] = (x, y, w, h)
        return clamped

    # ------------------------------------------------------------------
    # Utility: anchor selection & deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _best_anchor(anchors: List[Anchor], name: str) -> Optional[Anchor]:
        matching = [a for a in anchors if a.name == name]
        if not matching:
            return None
        return max(matching, key=lambda a: a.confidence)

    @staticmethod
    def _button_anchors(anchors: List[Anchor]) -> Dict[str, Anchor]:
        """Collect best button-like anchors (by name prefix 'btn_' or color label)."""
        btns: Dict[str, Anchor] = {}
        for a in anchors:
            if a.name.startswith("btn_") or a.name.endswith("_btn"):
                key = a.name
                if key not in btns or a.confidence > btns[key].confidence:
                    btns[key] = a
        return btns

    @staticmethod
    def _dedupe_anchors(anchors: List[Anchor], iou_thresh: float = 0.4) -> List[Anchor]:
        """Remove overlapping anchors, keeping highest confidence."""
        if not anchors:
            return []
        anchors = sorted(anchors, key=lambda a: -a.confidence)
        keep: List[Anchor] = []
        for a in anchors:
            overlap = False
            for k in keep:
                if AutoROIFinder._iou(a.bbox, k.bbox) > iou_thresh:
                    overlap = True
                    break
            if not overlap:
                keep.append(a)
        return keep

    @staticmethod
    def _iou(b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        xa = max(x1, x2)
        ya = max(y1, y2)
        xb = min(x1 + w1, x2 + w2)
        yb = min(y1 + h1, y2 + h2)
        inter = max(0, xb - xa) * max(0, yb - ya)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union else 0

    # ------------------------------------------------------------------
    # Confidence calculation
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_confidence(anchors: List[Anchor], zones: Dict) -> float:
        """
        Overall confidence based on:
         - number of anchors found
         - anchor confidence values
         - how many critical zones are anchor-backed
        """
        if not anchors:
            return 0.1  # Pure fallback

        avg_conf = sum(a.confidence for a in anchors) / len(anchors)

        # Bonus for critical anchor types
        has_table = any(a.name == "table_boundary" for a in anchors)
        has_buttons = any(a.name.startswith("btn_") for a in anchors)
        has_cards = any(a.name == "card" for a in anchors)

        bonus = 0.0
        if has_table:
            bonus += 0.15
        if has_buttons:
            bonus += 0.20
        if has_cards:
            bonus += 0.10

        # Zone coverage: expect ~20 zones
        coverage = min(1.0, len(zones) / 20)

        score = 0.4 * avg_conf + 0.3 * bonus + 0.3 * coverage
        return round(min(1.0, score), 3)

    # ------------------------------------------------------------------
    # Conversion to ROIConfig (launcher model)
    # ------------------------------------------------------------------

    def to_roi_config(
        self,
        result: CalibrationResult,
        account_id: str = "auto",
    ):
        """Convert CalibrationResult to launcher ROIConfig."""
        from launcher.models.roi_config import ROIConfig, ROIZone

        config = ROIConfig(
            account_id=account_id,
            resolution=result.resolution,
        )
        for name, (x, y, w, h) in result.zones.items():
            config.add_zone(ROIZone(name=name, x=x, y=y, width=w, height=h))

        return config


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python auto_roi_finder.py <screenshot.png>")
        print("  Analyses a poker table screenshot and prints detected ROI zones.")
        sys.exit(0)

    img = cv2.imread(sys.argv[1])
    if img is None:
        print(f"ERROR: cannot read image '{sys.argv[1]}'")
        sys.exit(1)

    finder = AutoROIFinder(use_ocr=TESSERACT_AVAILABLE)
    result = finder.find_rois(img)
    print()
    print(result.summary())
