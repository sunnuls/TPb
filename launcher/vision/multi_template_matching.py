"""
Multi-template matching & robust OCR for card / numeric recognition.

Phase 2 of vision_fragility.md.

Features:
- TemplateBank:  programmatic generation of rank/suit templates at
                 multiple sizes, fonts, and colour schemes.
- MultiTemplateMatcher:  multi-scale cv2.matchTemplate with NMS.
- RobustOCR:     multi-strategy preprocessing + Tesseract/EasyOCR
                 with voting.
- CardRecognizer: top-level API that chains template → OCR → fallback.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANKS = list("23456789") + ["T", "J", "Q", "K", "A"]
SUITS = ["s", "h", "d", "c"]                       # spade, heart, diamond, club
SUIT_DISPLAY = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RANK_DISPLAY = {r: ("10" if r == "T" else r) for r in RANKS}

# Typical suit colours (BGR)
SUIT_COLORS_BGR = {
    "s": (0, 0, 0),        # black
    "h": (0, 0, 200),      # red
    "d": (180, 0, 0),      # blue (some skins)
    "c": (0, 100, 0),      # green (some skins)
}

# Alternative suit colours seen in various skins
SUIT_ALT_COLORS_BGR = {
    "s": [(0, 0, 0), (40, 40, 40), (20, 20, 80)],
    "h": [(0, 0, 200), (0, 0, 255), (50, 50, 220)],
    "d": [(180, 0, 0), (200, 50, 50), (0, 0, 200)],
    "c": [(0, 100, 0), (0, 130, 0), (0, 0, 0)],
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """Single template match result."""
    token: str              # e.g. "As", "Kh", "9d"
    confidence: float       # 0-1
    method: str             # "template" / "ocr_tesseract" / "ocr_easyocr"
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)   # x, y, w, h
    metadata: Dict = field(default_factory=dict)


@dataclass
class RecognitionResult:
    """Combined recognition output for a single card image."""
    best_token: Optional[str]
    best_confidence: float
    all_matches: List[MatchResult]
    elapsed_ms: float = 0.0

    @property
    def rank(self) -> Optional[str]:
        return self.best_token[0] if self.best_token and len(self.best_token) >= 2 else None

    @property
    def suit(self) -> Optional[str]:
        return self.best_token[1] if self.best_token and len(self.best_token) >= 2 else None


class PreprocessStrategy(Enum):
    """Image preprocessing strategies for OCR."""
    RAW = "raw"
    OTSU = "otsu"
    ADAPTIVE = "adaptive"
    HIGH_CONTRAST = "high_contrast"
    INVERT = "invert"
    MULTI_THRESH = "multi_thresh"


# ---------------------------------------------------------------------------
# TemplateBank — programmatic template generation
# ---------------------------------------------------------------------------

class TemplateBank:
    """
    Generates and caches card rank/suit templates.

    Templates are rendered with OpenCV text drawing at multiple sizes
    and colour schemes so that matchTemplate can match across skins.
    Custom template images can also be loaded from disk.
    """

    DEFAULT_SIZES = [14, 18, 22, 28, 34]
    FONTS = [
        cv2.FONT_HERSHEY_SIMPLEX,
        cv2.FONT_HERSHEY_DUPLEX,
        cv2.FONT_HERSHEY_COMPLEX,
    ]

    def __init__(self, template_dir: Optional[str] = None):
        """
        Args:
            template_dir: optional directory with custom PNG templates
                          named <token>.png (e.g. As.png, Kh.png)
        """
        self.template_dir = Path(template_dir) if template_dir else None
        self._rank_templates: Dict[str, List[np.ndarray]] = {}
        self._suit_templates: Dict[str, List[np.ndarray]] = {}
        self._card_templates: Dict[str, List[np.ndarray]] = {}   # full token → images
        self._generated = False

    def ensure_generated(self) -> None:
        """Generate all templates if not done yet."""
        if self._generated:
            return
        self._generate_rank_templates()
        self._generate_suit_templates()
        self._load_custom_templates()
        self._generated = True
        total = sum(len(v) for v in self._rank_templates.values()) + \
                sum(len(v) for v in self._suit_templates.values()) + \
                sum(len(v) for v in self._card_templates.values())
        logger.info("TemplateBank ready: %d templates total", total)

    # -- generation --

    def _generate_rank_templates(self) -> None:
        for rank in RANKS:
            templates = []
            display = RANK_DISPLAY[rank]
            for size in self.DEFAULT_SIZES:
                for font in self.FONTS:
                    for thickness in (1, 2):
                        img = self._render_text(display, size, font, thickness, (0, 0, 0))
                        templates.append(img)
                        # White-on-black variant
                        img_inv = self._render_text(display, size, font, thickness, (255, 255, 255), bg=(0, 0, 0))
                        templates.append(img_inv)
            self._rank_templates[rank] = templates

    def _generate_suit_templates(self) -> None:
        for suit in SUITS:
            templates = []
            display = SUIT_DISPLAY[suit]
            colors = SUIT_ALT_COLORS_BGR.get(suit, [SUIT_COLORS_BGR[suit]])
            for size in self.DEFAULT_SIZES:
                for font in self.FONTS:
                    for color in colors:
                        img = self._render_text(display, size, font, 1, color)
                        templates.append(img)
                        img2 = self._render_text(display, size, font, 2, color)
                        templates.append(img2)
            self._suit_templates[suit] = templates

    def _load_custom_templates(self) -> None:
        """Load PNG templates from template_dir (if it exists)."""
        if not self.template_dir or not self.template_dir.is_dir():
            return
        count = 0
        for fp in self.template_dir.glob("*.png"):
            token = fp.stem  # e.g. "As"
            img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self._card_templates.setdefault(token, []).append(img)
                count += 1
        if count:
            logger.info("Loaded %d custom card templates from %s", count, self.template_dir)

    @staticmethod
    def _render_text(
        text: str,
        font_size: int,
        font: int,
        thickness: int,
        color: Tuple[int, int, int],
        bg: Tuple[int, int, int] = (255, 255, 255),
    ) -> np.ndarray:
        """Render text string into a tight grayscale image."""
        scale = font_size / 20.0
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        pad = 4
        w, h = tw + 2 * pad, th + baseline + 2 * pad
        img = np.full((h, w, 3), bg, dtype=np.uint8)
        cv2.putText(img, text, (pad, th + pad), font, scale, color, thickness, cv2.LINE_AA)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    # -- public access --

    def get_rank_templates(self, rank: str) -> List[np.ndarray]:
        self.ensure_generated()
        return self._rank_templates.get(rank, [])

    def get_suit_templates(self, suit: str) -> List[np.ndarray]:
        self.ensure_generated()
        return self._suit_templates.get(suit, [])

    def get_card_templates(self, token: str) -> List[np.ndarray]:
        self.ensure_generated()
        return self._card_templates.get(token, [])

    @property
    def all_rank_keys(self) -> List[str]:
        self.ensure_generated()
        return list(self._rank_templates.keys())

    @property
    def all_suit_keys(self) -> List[str]:
        self.ensure_generated()
        return list(self._suit_templates.keys())


# ---------------------------------------------------------------------------
# MultiTemplateMatcher — multi-scale matching with NMS
# ---------------------------------------------------------------------------

class MultiTemplateMatcher:
    """
    Matches an image region against multiple templates at several scales.

    Uses cv2.matchTemplate(TM_CCOEFF_NORMED) and returns the best match
    per symbol with non-maximum suppression.
    """

    SCALES = [0.7, 0.85, 1.0, 1.15, 1.3]

    def __init__(
        self,
        bank: Optional[TemplateBank] = None,
        match_threshold: float = 0.55,
    ):
        self.bank = bank or TemplateBank()
        self.match_threshold = match_threshold

    def match_rank(self, card_img: np.ndarray) -> List[MatchResult]:
        """
        Find the best rank match in the **top portion** of a card image.

        Args:
            card_img: grayscale card image (or BGR — will be converted)

        Returns:
            Sorted list of MatchResult (best first)
        """
        roi = self._top_region(card_img, frac=0.45)
        results: List[MatchResult] = []
        for rank in RANKS:
            templates = self.bank.get_rank_templates(rank)
            best = self._best_match(roi, templates)
            if best is not None:
                score, loc, tw, th = best
                results.append(MatchResult(
                    token=rank,
                    confidence=score,
                    method="template",
                    bbox=(loc[0], loc[1], tw, th),
                ))
        results.sort(key=lambda r: -r.confidence)
        return results

    def match_suit(self, card_img: np.ndarray) -> List[MatchResult]:
        """
        Find the best suit match (typically below the rank).

        Args:
            card_img: grayscale or BGR card image

        Returns:
            Sorted list of MatchResult (best first)
        """
        roi = self._top_region(card_img, frac=0.55)
        results: List[MatchResult] = []
        for suit in SUITS:
            templates = self.bank.get_suit_templates(suit)
            best = self._best_match(roi, templates)
            if best is not None:
                score, loc, tw, th = best
                results.append(MatchResult(
                    token=suit,
                    confidence=score,
                    method="template",
                    bbox=(loc[0], loc[1], tw, th),
                ))
        results.sort(key=lambda r: -r.confidence)
        return results

    def match_card(self, card_img: np.ndarray) -> Optional[MatchResult]:
        """
        Identify a full card token (rank + suit).

        First tries full-token templates (if available), then falls back
        to separate rank + suit matching.
        """
        gray = self._to_gray(card_img)

        # Strategy A: full token templates
        all_tokens = {r + s for r in RANKS for s in SUITS}
        best_full: Optional[MatchResult] = None
        for token in all_tokens:
            templates = self.bank.get_card_templates(token)
            if not templates:
                continue
            best = self._best_match(gray, templates)
            if best and (best_full is None or best[0] > best_full.confidence):
                score, loc, tw, th = best
                best_full = MatchResult(
                    token=token, confidence=score, method="template",
                    bbox=(loc[0], loc[1], tw, th),
                )
        if best_full and best_full.confidence >= self.match_threshold:
            return best_full

        # Strategy B: separate rank + suit
        ranks = self.match_rank(gray)
        suits = self.match_suit(gray)
        if ranks and suits:
            r, s = ranks[0], suits[0]
            combined = min(r.confidence, s.confidence)
            if combined >= self.match_threshold:
                return MatchResult(
                    token=r.token + s.token,
                    confidence=combined,
                    method="template",
                    metadata={"rank_conf": r.confidence, "suit_conf": s.confidence},
                )

        # No confident match
        return best_full if best_full else (
            MatchResult(
                token=(ranks[0].token + suits[0].token) if ranks and suits else None,
                confidence=max(
                    (ranks[0].confidence if ranks else 0),
                    (suits[0].confidence if suits else 0),
                ) * 0.5,
                method="template",
            ) if (ranks or suits) else None
        )

    # -- internals --

    def _best_match(
        self,
        image: np.ndarray,
        templates: List[np.ndarray],
    ) -> Optional[Tuple[float, Tuple[int, int], int, int]]:
        """Return (score, location, tw, th) for best match across templates & scales."""
        gray = self._to_gray(image)
        ih, iw = gray.shape[:2]
        best_score = -1.0
        best_result = None

        for tmpl in templates:
            th0, tw0 = tmpl.shape[:2]
            for scale in self.SCALES:
                tw = max(3, int(tw0 * scale))
                th = max(3, int(th0 * scale))
                if tw >= iw or th >= ih:
                    continue
                resized = cv2.resize(tmpl, (tw, th), interpolation=cv2.INTER_AREA)
                try:
                    result = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(result)
                except cv2.error:
                    continue
                if max_val > best_score:
                    best_score = max_val
                    best_result = (max_val, max_loc, tw, th)

        if best_result and best_result[0] >= self.match_threshold:
            return best_result
        return best_result  # may be below threshold but caller decides

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        if img.ndim == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    @staticmethod
    def _top_region(img: np.ndarray, frac: float = 0.45) -> np.ndarray:
        """Return the top fraction of the image (where rank/suit live)."""
        h = img.shape[0]
        cut = max(1, int(h * frac))
        return img[:cut]


# ---------------------------------------------------------------------------
# RobustOCR — multi-strategy OCR with voting
# ---------------------------------------------------------------------------

class RobustOCR:
    """
    Runs Tesseract (and optionally EasyOCR) with multiple preprocessing
    strategies and picks the consensus result.
    """

    RANK_CHARS = set("23456789TJQKA10")
    SUIT_CHARS = set("shdc♠♥♦♣")

    # Tesseract configs to try
    TESS_CONFIGS = [
        "--psm 7 --oem 3 -c tessedit_char_whitelist=AKQJT9876543210",
        "--psm 8 --oem 3 -c tessedit_char_whitelist=AKQJT9876543210",
        "--psm 10 --oem 3 -c tessedit_char_whitelist=AKQJT9876543210",
    ]

    NUMERIC_TESS_CONFIGS = [
        "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.$,kKmMBB",
        "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789.$,kKmMBB",
    ]

    def __init__(self, use_easyocr: bool = True, easyocr_langs: List[str] = None):
        self.use_easyocr = use_easyocr and EASYOCR_AVAILABLE
        self._easyocr_reader = None
        self._easyocr_langs = easyocr_langs or ["en"]

    def _get_easyocr(self):
        if self._easyocr_reader is None and self.use_easyocr:
            try:
                self._easyocr_reader = easyocr.Reader(self._easyocr_langs, gpu=False)
            except Exception as e:
                logger.warning("EasyOCR init failed: %s", e)
                self.use_easyocr = False
        return self._easyocr_reader

    # -- public --

    def recognize_rank(self, card_img: np.ndarray) -> List[MatchResult]:
        """OCR the top of a card to find the rank character."""
        roi = card_img[:max(1, card_img.shape[0] * 45 // 100)]
        variants = self._preprocess_variants(roi)
        votes: Dict[str, float] = {}

        # Tesseract
        if TESSERACT_AVAILABLE:
            for var in variants:
                for cfg in self.TESS_CONFIGS:
                    text = self._tess_ocr(var, cfg)
                    rank = self._parse_rank(text)
                    if rank:
                        votes[rank] = votes.get(rank, 0) + 1

        # EasyOCR
        if self.use_easyocr:
            reader = self._get_easyocr()
            if reader:
                for var in variants[:3]:
                    texts = self._easyocr_detect(reader, var)
                    for t in texts:
                        rank = self._parse_rank(t)
                        if rank:
                            votes[rank] = votes.get(rank, 0) + 1.5  # slight bonus

        if not votes:
            return []

        total = sum(votes.values())
        results = [
            MatchResult(
                token=rank,
                confidence=min(1.0, count / total),
                method="ocr_easyocr" if self.use_easyocr else "ocr_tesseract",
            )
            for rank, count in sorted(votes.items(), key=lambda x: -x[1])
        ]
        return results

    def recognize_number(self, img: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        OCR a numeric region (pot, stack, bet).

        Returns:
            (value, confidence) or None
        """
        variants = self._preprocess_variants(img)
        candidates: List[Tuple[float, str]] = []

        if TESSERACT_AVAILABLE:
            for var in variants:
                for cfg in self.NUMERIC_TESS_CONFIGS:
                    text = self._tess_ocr(var, cfg)
                    val = self._parse_number(text)
                    if val is not None:
                        candidates.append((val, "tesseract"))

        if self.use_easyocr:
            reader = self._get_easyocr()
            if reader:
                for var in variants[:3]:
                    texts = self._easyocr_detect(reader, var)
                    for t in texts:
                        val = self._parse_number(t)
                        if val is not None:
                            candidates.append((val, "easyocr"))

        if not candidates:
            return None

        # Majority vote / most common value
        from collections import Counter
        rounded = Counter(round(v, 2) for v, _ in candidates)
        best_val = rounded.most_common(1)[0][0]
        confidence = rounded[best_val] / len(candidates)
        return (best_val, min(1.0, confidence))

    # -- preprocessing --

    def _preprocess_variants(self, img: np.ndarray) -> List[np.ndarray]:
        """Generate multiple preprocessed versions of an image."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()
        h, w = gray.shape[:2]

        # Upscale small images
        if max(h, w) < 60:
            scale = max(2, 80 // max(h, w))
            gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        variants = []

        # 1. Raw (auto-level)
        variants.append(gray)

        # 2. OTSU
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)

        # 3. Adaptive threshold
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8,
        )
        variants.append(adaptive)

        # 4. High-contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        hc = clahe.apply(gray)
        _, hc_bin = cv2.threshold(hc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(hc_bin)

        # 5. Inverted
        inv = cv2.bitwise_not(otsu)
        variants.append(inv)

        # 6. Multi-threshold (130, 150, 170)
        for thr in (130, 150, 170):
            _, mt = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)
            variants.append(mt)

        return variants

    # -- engine wrappers --

    @staticmethod
    def _tess_ocr(img: np.ndarray, config: str) -> str:
        try:
            return pytesseract.image_to_string(img, config=config).strip()
        except Exception:
            return ""

    @staticmethod
    def _easyocr_detect(reader, img: np.ndarray) -> List[str]:
        try:
            results = reader.readtext(img, detail=0, paragraph=False)
            return [r.strip() for r in results if r.strip()]
        except Exception:
            return []

    # -- parsing helpers --

    @staticmethod
    def _parse_rank(text: str) -> Optional[str]:
        """Extract a single rank from OCR text."""
        text = text.strip().upper()
        if not text:
            return None
        # "10" → "T"
        if "10" in text:
            return "T"
        for ch in text:
            if ch in "AKQJT98765432":
                return ch
        return None

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """Parse a monetary / numeric string: '$1,234.56', '5.2k', '1.5M' etc."""
        import re
        text = text.strip().replace(" ", "").replace(",", "")
        text = re.sub(r"[^0-9.kKmMbB$]", "", text)
        text = text.replace("$", "")

        multiplier = 1.0
        if text and text[-1].lower() == "k":
            multiplier = 1_000
            text = text[:-1]
        elif text and text[-1].lower() == "m":
            multiplier = 1_000_000
            text = text[:-1]
        elif text and text[-1].lower() == "b":
            multiplier = 1_000_000_000
            text = text[:-1]

        try:
            return float(text) * multiplier
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# CardRecognizer — unified API (template → OCR → fallback)
# ---------------------------------------------------------------------------

class CardRecognizer:
    """
    Recognizes a card from a cropped card image.

    Pipeline:
        1. Multi-template matching (fast, works well when skin is known)
        2. RobustOCR (slower but more flexible)
        3. Consensus: if both agree → high confidence; disagree → lower
    """

    def __init__(
        self,
        template_dir: Optional[str] = None,
        match_threshold: float = 0.55,
        use_easyocr: bool = True,
    ):
        self.bank = TemplateBank(template_dir=template_dir)
        self.matcher = MultiTemplateMatcher(bank=self.bank, match_threshold=match_threshold)
        self.ocr = RobustOCR(use_easyocr=use_easyocr)
        self._match_threshold = match_threshold

    def recognize(self, card_img: np.ndarray) -> RecognitionResult:
        """
        Recognize rank + suit from a single card image.

        Args:
            card_img: BGR or grayscale cropped card image

        Returns:
            RecognitionResult with best_token, confidence, and all matches
        """
        t0 = time.perf_counter()
        all_matches: List[MatchResult] = []

        # --- Stage 1: Template matching ---
        tmpl_result = self.matcher.match_card(card_img)
        if tmpl_result:
            all_matches.append(tmpl_result)

        # --- Stage 2: OCR ---
        ocr_ranks = self.ocr.recognize_rank(card_img)
        if ocr_ranks:
            # We can only reliably OCR rank (suit symbols are hard for OCR)
            # Combine OCR rank with template suit if available
            top_ocr_rank = ocr_ranks[0]
            all_matches.append(top_ocr_rank)

        # --- Stage 3: Consensus ---
        best = self._pick_best(all_matches, tmpl_result, ocr_ranks)

        elapsed = (time.perf_counter() - t0) * 1000
        return RecognitionResult(
            best_token=best.token if best else None,
            best_confidence=best.confidence if best else 0.0,
            all_matches=all_matches,
            elapsed_ms=elapsed,
        )

    def recognize_number(self, img: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Recognize a numeric value (pot, stack, bet).

        Returns:
            (value, confidence) or None
        """
        return self.ocr.recognize_number(img)

    @staticmethod
    def _pick_best(
        all_matches: List[MatchResult],
        tmpl_result: Optional[MatchResult],
        ocr_ranks: List[MatchResult],
    ) -> Optional[MatchResult]:
        """Pick the best result with consensus bonus."""
        if not all_matches:
            return None

        # If template has full token with good confidence, prefer it
        if tmpl_result and tmpl_result.token and len(tmpl_result.token) == 2:
            if tmpl_result.confidence >= 0.6:
                # Check if OCR agrees on the rank
                if ocr_ranks and ocr_ranks[0].token == tmpl_result.token[0]:
                    # Consensus → boost confidence
                    return MatchResult(
                        token=tmpl_result.token,
                        confidence=min(1.0, tmpl_result.confidence + 0.15),
                        method="consensus",
                        metadata={
                            "template_conf": tmpl_result.confidence,
                            "ocr_conf": ocr_ranks[0].confidence,
                        },
                    )
                return tmpl_result

        # Fallback to highest confidence
        return max(all_matches, key=lambda m: m.confidence)


# ---------------------------------------------------------------------------
# NumericRecognizer — specialized for pot / stack / bet values
# ---------------------------------------------------------------------------

class NumericRecognizer:
    """
    Specialized recognizer for numeric poker values
    (pot size, stack sizes, bet amounts).

    Uses multi-strategy OCR with domain-specific parsing.
    """

    def __init__(self, use_easyocr: bool = True):
        self.ocr = RobustOCR(use_easyocr=use_easyocr)

    def recognize(self, img: np.ndarray) -> Optional[Tuple[float, float]]:
        """
        Args:
            img: cropped region containing a numeric value

        Returns:
            (value, confidence) or None
        """
        return self.ocr.recognize_number(img)

    def recognize_batch(
        self, images: Dict[str, np.ndarray],
    ) -> Dict[str, Tuple[float, float]]:
        """
        Recognize numeric values from multiple ROI images.

        Args:
            images: dict of zone_name → cropped image

        Returns:
            dict of zone_name → (value, confidence)
        """
        results: Dict[str, Tuple[float, float]] = {}
        for name, img in images.items():
            result = self.recognize(img)
            if result is not None:
                results[name] = result
        return results


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    print("=" * 60)
    print("Multi-Template Matching — Phase 2 Demo")
    print("=" * 60)

    bank = TemplateBank()
    bank.ensure_generated()
    print(f"\nRank templates: {sum(len(v) for v in bank._rank_templates.values())}")
    print(f"Suit templates: {sum(len(v) for v in bank._suit_templates.values())}")

    if len(sys.argv) >= 2:
        img = cv2.imread(sys.argv[1])
        if img is not None:
            recognizer = CardRecognizer()
            result = recognizer.recognize(img)
            print(f"\nRecognition: {result.best_token}  "
                  f"(conf={result.best_confidence:.2f}, {result.elapsed_ms:.0f}ms)")
            for m in result.all_matches:
                print(f"  {m.method}: {m.token} ({m.confidence:.2f})")
        else:
            print(f"ERROR: cannot read '{sys.argv[1]}'")

    print("\n" + "=" * 60)
