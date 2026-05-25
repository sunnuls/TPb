"""
PokerStars Vision Extractor (Phase 3 of PS roadmap).

Handles real vision extraction for PokerStars:
- Card detection via OCR on rank region + HSV color-based suit detection
- PS number format (spaces as thousands separator, 'к'/'k' suffix)
- Turn detection via green button highlight or presence of action buttons
- Table window detection via Win32 class name "PokerStarsTableFrameClass"

EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple, Dict

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PokerStars card rank characters (as they appear in OCR on the card corner)
VALID_RANKS = set("A K Q J T 9 8 7 6 5 4 3 2".split())

# Suit color ranges in HSV for PS card suits:
# Spades (black/dark): H any, S low, V low
# Hearts (red): H 0-15 or 165-180, S high, V high
# Diamonds (blue/teal in PS): H 100-130, S moderate, V moderate
# Clubs (green/dark): H 40-80, S moderate, V low

# PS-specific: spades = dark, hearts = red, diamonds = blue, clubs = green
_SUIT_RANGES = {
    "h": [(0, 50, 130), (15, 255, 255), "hearts_red"],
    "h2": [(160, 50, 130), (180, 255, 255), "hearts_red2"],
    "d": [(95, 50, 80), (135, 255, 255), "diamonds_blue"],
    "c": [(35, 40, 40), (90, 255, 150), "clubs_green"],
}


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

def parse_ps_number(text: str) -> float:
    """Parse a PokerStars formatted number into float.

    Handles:
    - Space as thousands separator: "50 000" → 50000
    - Comma as thousands separator: "1,000" → 1000
    - 'к' / 'k' suffix (Russian/English kilo): "20к" → 20000
    - Decimal dot: "1 234.50" → 1234.5
    - Currency prefix stripped: "$100", "100$"
    """
    if not text:
        return 0.0
    s = text.strip()
    # Remove currency symbols and common OCR noise chars
    s = re.sub(r'[¥$€£₽]', '', s)
    # Extract the first numeric token (digits, spaces, commas, dots, optional к/k suffix)
    # This discards trailing OCR artifacts like "400 a" → "400" or "19 190n" → "19 190"
    m = re.search(r'(\d[\d\s\u00a0,.]*)([кКkK])?', s)
    if not m:
        return 0.0
    num_part = m.group(1)
    k_suffix = bool(m.group(2))
    # Remove spaces/commas (thousands separators) and normalize decimal
    num_part = re.sub(r'[\s,\xa0]', '', num_part)
    num_part = num_part.replace(',', '.')
    try:
        value = float(num_part)
        return value * 1000 if k_suffix else value
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Card extraction
# ---------------------------------------------------------------------------

def extract_card_from_roi(
    roi_img: np.ndarray,
    debug: bool = False,
) -> Optional[str]:
    """Extract a single card (e.g. 'As', 'Kh') from a cropped card image.

    Algorithm:
    1. OCR the top-left corner for rank letter
    2. Detect suit via HSV color analysis on the suit area
    Returns a string like "As", "Kh", "Td" or None if detection fails.
    """
    if not CV2_AVAILABLE or roi_img is None:
        return None

    h, w = roi_img.shape[:2]
    if h < 10 or w < 10:
        return None

    # ── Card-face presence check ────────────────────────────────────────────
    # A card has a white face (high mean brightness in the central area).
    # Empty board slots show dark green table felt (mean ≈ 70-90).
    # If the image is too dark → no card present → skip OCR entirely.
    try:
        gray_check = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY) if len(roi_img.shape) == 3 else roi_img
        # Use the central 60% of the image to avoid card edges/shadows
        cy0, cy1 = int(h * 0.2), int(h * 0.8)
        cx0, cx1 = int(w * 0.1), int(w * 0.9)
        centre = gray_check[cy0:cy1, cx0:cx1]
        if centre.size > 0 and float(centre.mean()) < 100:
            # Too dark → likely empty table felt, not a card
            return None
    except Exception:
        pass

    # ── Step 1: detect rank via OCR ──────────────────────────────────────────
    rank = _detect_rank_ocr(roi_img)
    if not rank:
        return None

    # ── Step 2: detect suit via color ────────────────────────────────────────
    suit = _detect_suit_color(roi_img)
    if not suit:
        suit = _detect_suit_ocr(roi_img)
    if not suit:
        return None

    card = f"{rank}{suit}"
    logger.debug("Card detected: %s", card)
    return card


def _detect_rank_ocr(img: np.ndarray) -> Optional[str]:
    """OCR the rank from the top-left area of a card image.

    Card rank text is printed in black (dark) ink on the white card face.
    The top-left corner of the card image may also contain a dark rounded corner
    which can confuse global OTSU thresholding.  We try multiple preprocessing
    approaches and return the first valid result.

    psm 8 (single word) is used so '10' (two characters) can be read as a token.
    """
    if not TESSERACT_AVAILABLE:
        return None
    _WL = "AKQJT10987654321"
    _OCR_CFG8  = f"--psm 8  --oem 1 -c tessedit_char_whitelist={_WL}"
    _OCR_CFG10 = f"--psm 10 --oem 1 -c tessedit_char_whitelist={_WL}"

    def _parse(text: str) -> Optional[str]:
        text = re.sub(r'[^AKQJT10987654321]', '', text.upper())
        if text.startswith("10") or text in ("1O", "IO", "10"):
            return "T"
        if text and text[0] in VALID_RANKS:
            return text[0]
        # "0" alone → must be the "0" part of "10" (Ten); "0" is not a valid rank
        if text == "0":
            return "T"
        return None

    try:
        h, w = img.shape[:2]
        # Rank badge: top 45% of card, left 55% width
        rank_roi = img[0:int(h * 0.45), 0:int(w * 0.55)]
        gray = cv2.cvtColor(rank_roi, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else rank_roi
        gray = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

        # Attempt 1 — OTSU, ensure dark text on white background
        _, bw_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Card face is white (high value) → should be 255 after BINARY
        # If majority is dark (card corner dominates), the image is inverted – fix it.
        if bw_otsu.mean() < 127:
            bw_otsu = 255 - bw_otsu

        for cfg in (_OCR_CFG8, _OCR_CFG10):
            result = _parse(pytesseract.image_to_string(bw_otsu, config=cfg).strip())
            if result:
                return result

        # Attempt 2 — fixed threshold 160 (white card face > 160, dark text < 160)
        _, bw_fixed = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        if bw_fixed.mean() < 127:
            bw_fixed = 255 - bw_fixed
        for cfg in (_OCR_CFG8, _OCR_CFG10):
            result = _parse(pytesseract.image_to_string(bw_fixed, config=cfg).strip())
            if result:
                return result

        # Attempt 3 — adaptive threshold (handles mixed light/dark regions like card corners)
        bw_adapt = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 3
        )
        _OCR_CFG6 = f"--psm 6 --oem 1 -c tessedit_char_whitelist={_WL}"
        for cfg in (_OCR_CFG8, _OCR_CFG10, _OCR_CFG6):
            result = _parse(pytesseract.image_to_string(bw_adapt, config=cfg).strip())
            if result:
                return result

        # Attempt 4 — psm 6 on OTSU (psm 6 scans whole image and often finds the "0" of "10")
        for bw_try in (bw_otsu, bw_fixed):
            result = _parse(pytesseract.image_to_string(bw_try, config=_OCR_CFG6).strip())
            if result:
                return result

    except Exception as exc:
        logger.debug("Rank OCR error: %s", exc)
    return None


def _detect_suit_color(img: np.ndarray) -> Optional[str]:
    """Detect suit color from the card image.

    Modern PokerStars (2-colour theme):
        Red  suits: Hearts (♥) and Diamonds (♦)
        Dark suits: Clubs  (♣) and Spades  (♠)

    Also handles 4-colour PS themes: Diamonds=blue, Clubs=green.

    Within the red pair, hearts have more red pixels in the TOP half of the suit
    icon (two round lobes); diamonds are roughly symmetric (rotated square).
    Within the dark pair, clubs have three lobes → more dark pixels in the top
    third compared to spades (single pointed head + wider shoulders at top).
    """
    if not CV2_AVAILABLE:
        return None
    try:
        h, w = img.shape[:2]
        # Suit badge area — top-left corner: rank+suit stacked vertically
        suit_roi = img[int(h * 0.30):int(h * 0.70), 0:int(w * 0.55)]
        if suit_roi.size == 0:
            return None
        hsv = cv2.cvtColor(suit_roi, cv2.COLOR_BGR2HSV)
        total = suit_roi.shape[0] * suit_roi.shape[1]
        if total == 0:
            return None

        # ── Step 1: identify dominant colour ───────────────────────────────
        red1 = cv2.countNonZero(cv2.inRange(hsv, np.array([0,  70, 60]), np.array([15, 255, 255])))
        red2 = cv2.countNonZero(cv2.inRange(hsv, np.array([155, 70, 60]), np.array([180, 255, 255])))
        red_px = red1 + red2
        blue_px = cv2.countNonZero(cv2.inRange(hsv, np.array([95, 50, 50]), np.array([140, 255, 255])))
        green_px = cv2.countNonZero(cv2.inRange(hsv, np.array([38, 40, 30]), np.array([90, 255, 180])))

        threshold = total * 0.04

        # 4-colour theme shortcuts (blue=diamonds, green=clubs)
        if blue_px > threshold:
            return "d"
        if green_px > threshold:
            return "c"

        is_red = red_px > threshold

        # ── Step 2: shape disambiguation ───────────────────────────────────
        sr_h, sr_w = suit_roi.shape[:2]

        if is_red:
            # Hearts: two round lobes in upper half → top > bottom in red pixel count
            # Diamonds: symmetric rotated square → top ≈ bottom
            top_half = suit_roi[0:sr_h // 2, :]
            bot_half = suit_roi[sr_h // 2:, :]

            def _red_count(region: np.ndarray) -> int:
                if region.size == 0:
                    return 0
                h2 = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                r1 = cv2.countNonZero(cv2.inRange(h2, np.array([0, 70, 60]), np.array([15, 255, 255])))
                r2 = cv2.countNonZero(cv2.inRange(h2, np.array([155, 70, 60]), np.array([180, 255, 255])))
                return r1 + r2

            top_red = _red_count(top_half)
            bot_red = _red_count(bot_half)
            if top_red > 0 and bot_red > 0:
                ratio = top_red / (bot_red + 1)
                return "h" if ratio > 1.1 else "d"
            return "d"  # default red → diamond if shape ambiguous

        else:
            # Clubs: 3 circular lobes at the top → top third darker than bottom
            # Spades: pointed leaf at top + triangle foot
            top_third = suit_roi[0:sr_h // 3, :]
            bot_third = suit_roi[2 * sr_h // 3:, :]

            def _dark_count(region: np.ndarray) -> int:
                if region.size == 0:
                    return 0
                h2 = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
                return cv2.countNonZero(cv2.inRange(h2, np.array([0, 0, 0]), np.array([180, 255, 80])))

            dark_top = _dark_count(top_third)
            dark_bot = _dark_count(bot_third)
            # Clubs: three lobes → more dark in top
            if dark_top > dark_bot * 1.15:
                return "c"
            return "s"

    except Exception as exc:
        logger.debug("Suit color detection error: %s", exc)
    return None


def _detect_suit_ocr(img: np.ndarray) -> Optional[str]:
    """Fallback: OCR the suit symbol text."""
    if not TESSERACT_AVAILABLE:
        return None
    try:
        h, w = img.shape[:2]
        suit_roi = img[int(h * 0.35):int(h * 0.70), 0:int(w * 0.55)]
        gray = cv2.cvtColor(suit_roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(bw, config="--psm 10 --oem 1").strip().lower()
        for char, suit in [("♠", "s"), ("♥", "h"), ("♦", "d"), ("♣", "c"),
                           ("s", "s"), ("h", "h"), ("d", "d"), ("c", "c")]:
            if char in text:
                return suit
    except Exception as exc:
        logger.debug("Suit OCR error: %s", exc)
    return None


def extract_cards_from_screenshot(
    screenshot: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
    card_keys: List[str],
) -> List[str]:
    """Extract multiple cards from a screenshot using named ROIs.

    Args:
        screenshot: Full window screenshot (BGR numpy array)
        rois:       Dict of {name: (x, y, w, h)} from pokerstars.yaml
        card_keys:  List of ROI names to extract, e.g. ["hero_card_1", "hero_card_2"]

    Returns:
        List of card strings, e.g. ["As", "Kh"]
    """
    cards = []
    if screenshot is None or screenshot.size == 0:
        return cards
    sh, sw = screenshot.shape[:2]
    for key in card_keys:
        roi = rois.get(key)
        if roi is None:
            continue
        x, y, w, h = roi
        if y >= sh or x >= sw or y + h <= 0 or x + w <= 0:
            continue
        card_img = screenshot[max(0,y):min(sh,y+h), max(0,x):min(sw,x+w)]
        if card_img.size == 0:
            continue
        card = extract_card_from_roi(card_img)
        if card:
            cards.append(card)
    return cards


# ---------------------------------------------------------------------------
# Turn detection
# ---------------------------------------------------------------------------

def is_bots_turn(
    screenshot: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
) -> bool:
    """Detect if it is the bot's turn to act on PokerStars.

    Modern PokerStars (Flutter/GLFW30) uses DARK RED buttons for actions.
    Method 1: Scan bottom 25% for any large red/crimson button blob.
    Method 2: ROI-based colour check (green/yellow/red highlight).
    Method 3: OCR bottom strip for action keywords.
    """
    if not CV2_AVAILABLE:
        return _is_turn_ocr(screenshot, rois)

    # Method 1 (fastest): look for large red button blob in bottom 25%
    if _has_red_buttons_in_bottom(screenshot):
        logger.debug("Turn detected via red button blob in bottom strip")
        return True

    # Method 2: ROI colour check (green / yellow / red)
    for btn_key in ("fold_button", "call_button", "check_button", "raise_button"):
        roi = rois.get(btn_key)
        if roi is None:
            continue
        x, y, w, h = roi
        if y + h > screenshot.shape[0] or x + w > screenshot.shape[1]:
            continue
        btn_img = screenshot[y:y + h, x:x + w]
        if (_has_green_highlight(btn_img) or
                _has_yellow_highlight(btn_img) or
                _has_red_highlight(btn_img)):
            logger.debug("Turn detected via button highlight in '%s'", btn_key)
            return True

    # Method 3: OCR fallback
    return _is_turn_ocr(screenshot, rois)


def _has_red_buttons_in_bottom(screenshot: np.ndarray) -> bool:
    """Return True if there are large RED button blobs in the bottom 30%.

    Modern PokerStars uses solid crimson (#CC2233 ≈ HSV 350°,80%,80%) for
    action buttons (Fold / Check / Call / Raise / Bet).
    Buttons measured at y≈618 in 870px window → strip must start at ≤70%.
    """
    if not CV2_AVAILABLE:
        return False
    try:
        h, w = screenshot.shape[:2]
        strip_y0 = int(h * 0.70)
        strip = screenshot[strip_y0:h, :]
        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
        # Red wraps in HSV: 0-12 and 163-180
        m1 = cv2.inRange(hsv, np.array([0,   100, 80]), np.array([12, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([163, 100, 80]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw >= 100 and bh >= 35 and bw * bh >= 5000 and bw / max(bh, 1) >= 1.2:
                return True
    except Exception:
        pass
    return False


def _has_green_highlight(img: np.ndarray) -> bool:
    """Return True if the image contains a green highlight (active button)."""
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 60, 60]), np.array([90, 255, 255]))
        ratio = cv2.countNonZero(mask) / (img.shape[0] * img.shape[1])
        return ratio > 0.15
    except Exception:
        return False


def _has_yellow_highlight(img: np.ndarray) -> bool:
    """Return True if the image contains a yellow/orange highlight."""
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([15, 80, 100]), np.array([38, 255, 255]))
        ratio = cv2.countNonZero(mask) / (img.shape[0] * img.shape[1])
        return ratio > 0.15
    except Exception:
        return False


def _has_red_highlight(img: np.ndarray) -> bool:
    """Return True if the image contains a red/crimson highlight (PS action buttons)."""
    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0,   100, 80]), np.array([12, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([163, 100, 80]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        ratio = cv2.countNonZero(mask) / (img.shape[0] * img.shape[1])
        return ratio > 0.15
    except Exception:
        return False


def _is_turn_ocr(
    screenshot: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
) -> bool:
    """OCR-based turn detection: look for action button text."""
    if not TESSERACT_AVAILABLE or screenshot is None:
        return False
    try:
        h, w = screenshot.shape[:2]
        # Action buttons are in the bottom 25%
        bottom_strip = screenshot[int(h * 0.75):h, :]
        # Preprocess: upscale + threshold for better OCR on dark buttons
        strip_big = cv2.resize(bottom_strip, None, fx=2, fy=2,
                               interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(strip_big, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(
            bw, config="--psm 11 -l rus+eng"
        ).lower()
        action_kws = ("fold", "check", "call", "raise", "bet",
                      "пас", "чек", "колл", "рейз", "ставка", "фолд", "бет")
        found = sum(1 for kw in action_kws if kw in text)
        if found >= 1:
            logger.info("Turn OCR: found %d action keyword(s) in bottom strip", found)
            return True
    except Exception as exc:
        logger.debug("Turn OCR detection error: %s", exc)
    return False


# ---------------------------------------------------------------------------
# Dynamic action-button detection (no fixed ROI needed)
# ---------------------------------------------------------------------------

def detect_action_buttons(
    screenshot: np.ndarray,
) -> Dict[str, Tuple[int, int]]:
    """Scan the bottom 30% of the screenshot for action buttons by OCR.

    Returns a dict mapping canonical action name → (cx, cy) in image coordinates:
        "fold"  → centre of the Fold/Пас button
        "check" → centre of the Check/Чек button
        "call"  → centre of the Call/Колл button
        "raise" → centre of the Raise/Рейз button
        "bet"   → centre of the Bet/Ставка button  (may alias "raise")

    Works for any window size — no calibration needed.
    Also saves a debug screenshot to TEMP so ROI calibration is easy.
    """
    result: Dict[str, Tuple[int, int]] = {}
    if not TESSERACT_AVAILABLE or not CV2_AVAILABLE or screenshot is None:
        return result

    try:
        import tempfile, os, time as _time

        h, w = screenshot.shape[:2]
        # Bottom 30% — buttons measured at y≈618 in 870px window (= 71% from top).
        # Using 70% gives a safe margin; 80% was wrong (missed the buttons entirely).
        strip_y0 = int(h * 0.70)
        strip = screenshot[strip_y0:h, :]

        # Save a debug image (overwritten every time) so ROI positions can be
        # verified manually: open %TEMP%\ps_table_latest.png to calibrate.
        try:
            debug_path = os.path.join(tempfile.gettempdir(), "ps_table_latest.png")
            import cv2 as _cv2
            _cv2.imwrite(debug_path, screenshot)
            logger.debug("PS table debug screenshot → %s (%dx%d)", debug_path, w, h)
        except Exception:
            pass

        # Preprocess: upscale + threshold so OCR reads white text on dark buttons
        strip_big = cv2.resize(strip, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(strip_big, cv2.COLOR_BGR2GRAY)
        # Invert so white text on dark background → dark text on white background
        _, bw = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

        # OCR with bounding boxes
        import pytesseract
        data = pytesseract.image_to_data(
            bw,
            config="--psm 11 -l rus+eng",
            output_type=pytesseract.Output.DICT,
        )

        # Mapping: OCR token → canonical action name
        # Include common Tesseract misreads of Cyrillic characters
        _TOKEN_MAP = {
            # Fold
            "фолд": "fold", "pас": "fold", "пас": "fold", "fold": "fold",
            "фол":  "fold", "фоя": "fold", "фод": "fold",
            # Check  — "Ч" is often misread as "4", "q", "ц", "ч"
            "чек":  "check", "check": "check", "chek": "check",
            "чex":  "check", "чех":  "check", "чeк": "check",
            "4ek":  "check", "4eк":  "check", "цек": "check",
            "чeк":  "check", "чёк":  "check",
            # Call
            "колл": "call", "call": "call", "кол": "call", "col": "call",
            "колл ": "call",
            # Raise
            "рейз": "raise", "raise": "raise", "рейз до": "raise",
            "pейз": "raise", "рейс": "raise", "рeйз": "raise",
            # Bet
            "бет":  "bet",  "bet": "bet", "ставка": "bet",
            "бéт":  "bet",  "бет ": "bet",
        }

        for i, txt in enumerate(data.get("text", [])):
            txt_raw = (txt or "").strip()
            if not txt_raw:
                continue
            txt_lo = txt_raw.lower()
            # Direct match
            action = _TOKEN_MAP.get(txt_lo)
            # Partial match for multi-word (e.g. "Рейз до 400")
            if action is None:
                for kw, act in _TOKEN_MAP.items():
                    if kw in txt_lo:
                        action = act
                        break
            if action is None:
                continue
            # Coordinates from OCR are in the 2× upscaled image — divide by 2
            bx   = data["left"][i]  // 2
            by   = data["top"][i]   // 2
            bw_  = data["width"][i] // 2
            bh_  = data["height"][i] // 2
            if bw_ < 5 or bh_ < 5:
                continue
            cx = bx + bw_ // 2
            cy = strip_y0 + by + bh_ // 2
            # Prefer the first (leftmost) occurrence of each action
            if action not in result:
                result[action] = (cx, cy)
                logger.debug(
                    "Button '%s' (%s) detected at (%d, %d) in image",
                    action, txt_raw, cx, cy,
                )

        # Always run colour detection to find ALL button blobs.
        # OCR names take priority; colour fills in any buttons OCR missed.
        color_buttons = _detect_buttons_by_color(screenshot, ocr_found=result)
        for act, coords in color_buttons.items():
            if act not in result:
                result[act] = coords
                logger.debug("Color filled missing button '%s' at %s", act, coords)

    except Exception as exc:
        logger.debug("detect_action_buttons error: %s", exc)

    return result


def _detect_buttons_by_color(
    screenshot: np.ndarray,
    ocr_found: Optional[Dict[str, Tuple[int, int]]] = None,
) -> Dict[str, Tuple[int, int]]:
    """Find action button blobs in the bottom 30% using colour segmentation.

    Modern PokerStars uses DARK RED (#CC2233) for ALL action buttons.
    Layout-aware naming:
        2 blobs  → [Check] [Bet/Raise]          (no-bet scenario)
        3 blobs  → [Fold]  [Call/Check] [Raise]  (facing a bet)
        1 blob   → [Bet]                         (single action)

    If *ocr_found* is provided, blobs that already have an OCR label are
    skipped; only unlabelled blobs get a positional name.
    """
    result: Dict[str, Tuple[int, int]] = {}
    if not CV2_AVAILABLE:
        return result
    try:
        h, w = screenshot.shape[:2]
        # Bottom 30% — buttons measured at y≈618 in 870px window (≈71% from top).
        # 80% was wrong: it started at y=696 and missed the actual buttons.
        strip_y0 = int(h * 0.70)
        strip = screenshot[strip_y0:h, :]

        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)

        # ── RED buttons (modern PS: Fold / Check / Call / Raise) ────────────
        # PS button colour: approx #CC2233 → OpenCV HSV H≈3, S≈210, V≈200
        red1 = cv2.inRange(hsv, np.array([0,   100, 80]),  np.array([12, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([163, 100, 80]),  np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(red1, red2)

        # ── GREEN buttons (legacy PS / some themes) ───────────────────────
        green_mask = cv2.inRange(hsv,
                                  np.array([35, 80, 80]),
                                  np.array([90, 255, 255]))

        combined = cv2.bitwise_or(red_mask, green_mask)
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(combined, kernel, iterations=2)
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        blobs = []
        for cnt in contours:
            bx, by, bw_, bh_ = cv2.boundingRect(cnt)
            # Action buttons are large (≥ 150×35 px, area ≥ 5000).
            # Smaller bet-slider controls (Мин/½/Макс, ~100×28 px) are excluded.
            if bw_ < 100 or bh_ < 35 or bw_ * bh_ < 5000:
                continue
            if bw_ / max(bh_, 1) < 1.2:  # skip non-wide blobs (cards are ~squarish)
                continue
            cx = bx + bw_ // 2
            cy = strip_y0 + by + bh_ // 2
            blobs.append((bx, cx, cy, bw_, bh_))
            logger.debug("Blob candidate: bx=%d by=%d w=%d h=%d", bx, strip_y0 + by, bw_, bh_)

        blobs.sort(key=lambda b: b[0])  # left → right by bx

        n = len(blobs)
        # Layout-aware name assignment (left → right order)
        if n == 1:
            layout = ["bet"]
        elif n == 2:
            # PS 2-button: [Check] [Bet/Raise]  (player acts first / no prior bet)
            layout = ["check", "bet"]
        else:
            # PS 3-button: [Fold] [Call] [Raise]  (facing a bet)
            layout = ["fold", "call", "raise"]

        for idx, (bx, cx, cy, bw_, bh_) in enumerate(blobs[:3]):
            act = layout[idx] if idx < len(layout) else f"btn{idx}"
            result[act] = (cx, cy)
            logger.info(
                "Color-blob button '%s' at (%d,%d) size %dx%d",
                act, cx, cy, bw_, bh_,
            )

    except Exception as exc:
        logger.debug("_detect_buttons_by_color error: %s", exc)
    return result


# Cache the last detected button positions so _get_ps_action_coords can use them
_last_detected_buttons: Dict[str, Tuple[int, int]] = {}


def update_button_cache(buttons: Dict[str, Tuple[int, int]]) -> None:
    """Store button positions from the latest frame for use by action executor."""
    _last_detected_buttons.clear()
    _last_detected_buttons.update(buttons)
    if buttons:
        logger.debug("Button cache updated: %s", list(buttons.keys()))


def get_cached_buttons() -> Dict[str, Tuple[int, int]]:
    """Return the most recently detected button positions."""
    return dict(_last_detected_buttons)


# ---------------------------------------------------------------------------
# Pot and stack extraction
# ---------------------------------------------------------------------------

def extract_pot(
    screenshot: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
) -> float:
    """Extract pot size from screenshot."""
    roi = rois.get("pot")
    if roi is None or not TESSERACT_AVAILABLE or not CV2_AVAILABLE:
        return 0.0
    if screenshot is None or screenshot.size == 0:
        return 0.0
    x, y, w, h = roi
    try:
        sh, sw = screenshot.shape[:2]
        if y >= sh or x >= sw or y + h <= 0 or x + w <= 0:
            return 0.0
        region = screenshot[max(0,y):min(sh, y+h), max(0,x):min(sw, x+w)]
        if region.size == 0:
            return 0.0
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if bw.mean() < 127:
            bw = 255 - bw
        text = pytesseract.image_to_string(bw, config="--psm 7 --oem 1").strip()
        # Strip "Pot:" / "Банк:" prefix
        text = re.sub(r'^[^\d]*', '', text)
        return parse_ps_number(text)
    except Exception as exc:
        logger.debug("Pot extraction error: %s", exc)
    return 0.0


def extract_stack(
    screenshot: np.ndarray,
    rois: Dict[str, Tuple[int, int, int, int]],
    roi_key: str,
) -> float:
    """Extract a single stack value from screenshot."""
    roi = rois.get(roi_key)
    if roi is None or not TESSERACT_AVAILABLE or not CV2_AVAILABLE:
        return 0.0
    if screenshot is None or screenshot.size == 0:
        return 0.0
    x, y, w, h = roi
    try:
        sh, sw = screenshot.shape[:2]
        if y >= sh or x >= sw or y + h <= 0 or x + w <= 0:
            return 0.0
        region = screenshot[max(0,y):min(sh, y+h), max(0,x):min(sw, x+w)]
        if region.size == 0:
            return 0.0
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if bw.mean() < 127:
            bw = 255 - bw
        text = pytesseract.image_to_string(bw, config="--psm 7 --oem 1").strip()
        text = re.sub(r'^[^\d]*', '', text)
        return parse_ps_number(text)
    except Exception as exc:
        logger.debug("Stack extraction '%s' error: %s", roi_key, exc)
    return 0.0


# ---------------------------------------------------------------------------
# PokerStars table window finder
# ---------------------------------------------------------------------------

def find_ps_table_hwnds() -> List[int]:
    """Find all open PokerStars table windows.

    Modern PokerStars uses GLFW30 class (OpenGL rendering) for table windows.
    Legacy versions used PokerStarsTableFrameClass.
    Returns list of HWNDs, newest first (highest HWND = most recently opened).
    """
    if not WIN32_AVAILABLE:
        return []

    # Window class names used by PS table windows
    _TABLE_CLASSES = ("GLFW30", "PokerStarsTableFrameClass", "GlfwWindow")
    # Title keywords that indicate a real PS poker table
    _TABLE_TITLE_KW = (
        "Холдем", "Hold'em", "Holdem", "Omaha", "Омаха",
        "NL-HE", "PL-HE", "FL-HE", "NLHE", "PLHE",
        "Без лимита", "No Limit", "Pot Limit",
        "Условные фишки",  # PS play-money tables always have this
    )
    # Lobby/dialog titles to EXCLUDE
    _EXCLUDE_TITLE_KW = ("Лобби", "Lobby", "PokerStars Lobby", "Бай-ин", "Buy-In")

    # Get all PokerStars PIDs for reliable process filtering
    ps_pids: set = set()
    try:
        import win32process
        def _pid_cb(h, _):
            try:
                if win32gui.IsWindowVisible(h):
                    title = win32gui.GetWindowText(h)
                    if "pokerstars" in title.lower() or "лобби pokerstars" in title.lower():
                        _, pid = win32process.GetWindowThreadProcessId(h)
                        ps_pids.add(pid)
            except Exception:
                pass
            return True
        win32gui.EnumWindows(_pid_cb, None)
        # Also collect from known lobby HWND
        if not ps_pids:
            def _pid_cb2(h, _):
                try:
                    cls = win32gui.GetClassName(h)
                    if cls == "GLFW30" or "PokerStars" in cls:
                        _, pid = win32process.GetWindowThreadProcessId(h)
                        ps_pids.add(pid)
                except Exception:
                    pass
                return True
            win32gui.EnumWindows(_pid_cb2, None)
    except Exception:
        pass

    hwnds = []
    try:
        def _enum_callback(hwnd: int, _lparam) -> bool:
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                cls = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)

                # Skip lobby, dialogs, buy-in windows
                if any(kw in title for kw in _EXCLUDE_TITLE_KW):
                    return True

                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                # Tables are at least 400x350 px
                if w < 400 or h < 350:
                    return True

                # Strategy 1: GLFW30 or known PS table class (most reliable)
                if cls in _TABLE_CLASSES:
                    try:
                        import win32process
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if not ps_pids or pid in ps_pids:
                            hwnds.append(hwnd)
                            return True
                    except Exception:
                        hwnds.append(hwnd)
                        return True

                # Strategy 2: title contains table keywords + belongs to PS process
                if any(kw in title for kw in _TABLE_TITLE_KW):
                    try:
                        import win32process
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if not ps_pids or pid in ps_pids:
                            hwnds.append(hwnd)
                    except Exception:
                        hwnds.append(hwnd)

            except Exception:
                pass
            return True

        win32gui.EnumWindows(_enum_callback, None)
    except Exception as exc:
        logger.debug("find_ps_table_hwnds error: %s", exc)

    return sorted(set(hwnds), reverse=True)


def wait_for_ps_table(
    known_hwnds: Optional[List[int]] = None,
    timeout: float = 15.0,
) -> Optional[int]:
    """Wait for a new PokerStars table window to appear.

    Args:
        known_hwnds: HWNDs already known (to detect newly opened window)
        timeout:     Max wait time in seconds (blocking)

    Returns:
        HWND of the new table window, or None if timeout reached.
    """
    import time
    known = set(known_hwnds or [])
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        current = set(find_ps_table_hwnds())
        new_hwnds = current - known
        if new_hwnds:
            hwnd = sorted(new_hwnds, reverse=True)[0]
            logger.info("New PS table window detected: hwnd=%d", hwnd)
            return hwnd
        time.sleep(0.5)
    logger.warning("wait_for_ps_table: timeout after %.0fs", timeout)
    return None
