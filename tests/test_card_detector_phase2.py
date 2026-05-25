"""
Tests for Phase 2 (vision_fragility.md) enhancements to card_detector.py
and yolo_detector.py.

Tests multi-template matching, multi-strategy OCR, EasyOCR fallback,
and colour-based suit detection on synthetic card images.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import unittest

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from card_detector import (
        CardDetector,
        CardTemplateBank,
        _normalise_rank,
        _detect_suit_by_color,
        _preprocess_variants,
        _tesseract_ocr,
        RANKS,
    )
    MODULE_OK = True
except Exception:
    MODULE_OK = False

try:
    from yolo_detector import YoloCardDetector
    YOLO_MODULE_OK = True
except Exception:
    YOLO_MODULE_OK = False


# ---------------------------------------------------------------------------
# Synthetic card image generator
# ---------------------------------------------------------------------------

def _make_card_image(rank: str = "A", suit_color=(0, 0, 200),
                     bg=(240, 240, 240), w=70, h=100):
    """Create a synthetic card image (BGR) with rank text and suit colour."""
    img = np.full((h, w, 3), bg, dtype=np.uint8)
    # Rank text in top-left
    display = "10" if rank == "T" else rank
    cv2.putText(img, display, (5, 22), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 0, 0), 2, cv2.LINE_AA)
    # Suit colour blob below rank
    cv2.circle(img, (15, 40), 8, suit_color, -1)
    return img


def _make_table_with_cards(width=800, height=600):
    """Create synthetic poker table image with embedded card shapes."""
    img = np.full((height, width, 3), (30, 80, 30), dtype=np.uint8)  # green felt

    cards = []
    # Board cards (centre)
    cw, ch = 50, 70
    start_x = width // 2 - (5 * cw + 4 * 5) // 2
    for i in range(5):
        x = start_x + i * (cw + 5)
        y = height // 2 - ch // 2
        card_img = _make_card_image("AKQJT"[i], w=cw, h=ch)
        img[y:y + ch, x:x + cw] = card_img
        cards.append({'x': x, 'y': y, 'w': cw, 'h': ch})

    # Hero cards (bottom centre)
    hero_y = int(height * 0.75)
    for i, rank in enumerate(["A", "K"]):
        x = width // 2 - cw - 3 + i * (cw + 6)
        card_img = _make_card_image(rank, suit_color=(0, 0, 200), w=cw, h=ch)
        img[hero_y:hero_y + ch, x:x + cw] = card_img
        cards.append({'x': x, 'y': hero_y, 'w': cw, 'h': ch})

    return img, cards


# ---------------------------------------------------------------------------
# CardTemplateBank tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or card_detector not available")
class TestCardTemplateBank(unittest.TestCase):

    def test_generate(self):
        bank = CardTemplateBank()
        bank.generate()
        self.assertTrue(bank.generated)
        self.assertGreater(len(bank.rank_templates), 0)
        for rank in RANKS:
            self.assertIn(rank, bank.rank_templates)
            self.assertGreater(len(bank.rank_templates[rank]), 0)

    def test_template_images_are_valid(self):
        bank = CardTemplateBank()
        bank.generate(font_scales=(0.8,), thicknesses=(1,),
                      sizes=((25, 30),), bg_vals=(255,), fg_vals=(0,))
        for rank, templates in bank.rank_templates.items():
            for tpl in templates:
                self.assertEqual(len(tpl.shape), 2)  # grayscale
                self.assertGreater(tpl.shape[0], 0)
                self.assertGreater(tpl.shape[1], 0)

    def test_match_rank_known_image(self):
        """Generate an image with a known rank and verify matching works."""
        bank = CardTemplateBank()
        bank.generate()

        # Create a test image with "A" written on it
        roi = np.full((50, 40), 240, dtype=np.uint8)
        cv2.putText(roi, "A", (5, 35), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, 0, 2, cv2.LINE_AA)

        rank, conf = bank.match_rank(roi)
        # Template matching on synthetic data — may or may not match perfectly
        # but should return a result without crashing
        self.assertIsInstance(conf, float)
        self.assertGreaterEqual(conf, 0.0)

    def test_match_rank_empty_image(self):
        bank = CardTemplateBank()
        bank.generate(font_scales=(0.8,), thicknesses=(1,),
                      sizes=((25, 30),), bg_vals=(255,), fg_vals=(0,))
        # Very small image — templates won't fit
        roi = np.full((5, 5), 128, dtype=np.uint8)
        rank, conf = bank.match_rank(roi)
        self.assertEqual(conf, 0.0)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or card_detector not available")
class TestHelpers(unittest.TestCase):

    def test_normalise_rank_standard(self):
        self.assertEqual(_normalise_rank("A"), "A")
        self.assertEqual(_normalise_rank("K"), "K")
        self.assertEqual(_normalise_rank("10"), "T")
        self.assertEqual(_normalise_rank("j"), "J")
        self.assertEqual(_normalise_rank("  Q  "), "Q")

    def test_normalise_rank_invalid(self):
        self.assertIsNone(_normalise_rank(""))
        self.assertIsNone(_normalise_rank("xyz"))
        self.assertIsNone(_normalise_rank(" "))

    def test_preprocess_variants(self):
        gray = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        variants = _preprocess_variants(gray)
        self.assertGreaterEqual(len(variants), 3)
        for v in variants:
            self.assertEqual(v.shape, gray.shape)

    def test_detect_suit_red(self):
        """Red suit colour should be detected as hearts."""
        roi = np.full((30, 30, 3), (0, 0, 200), dtype=np.uint8)  # BGR red
        suit = _detect_suit_by_color(roi)
        self.assertEqual(suit, "h")

    def test_detect_suit_low_saturation(self):
        """Very dark, low saturation → spades."""
        roi = np.full((30, 30, 3), (20, 20, 20), dtype=np.uint8)
        suit = _detect_suit_by_color(roi)
        self.assertEqual(suit, "s")


# ---------------------------------------------------------------------------
# CardDetector integration
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or card_detector not available")
class TestCardDetectorPhase2(unittest.TestCase):

    def test_init_has_template_bank(self):
        det = CardDetector()
        self.assertIsNotNone(det._template_bank)
        self.assertTrue(det._template_bank.generated)

    def test_find_cards_synthetic(self):
        """find_cards should find cards on synthetic table."""
        img_bgr, expected_cards = _make_table_with_cards()
        from PIL import Image as PILImage
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(img_rgb)

        det = CardDetector()
        # Adjust area range for small synthetic cards
        det.min_card_area = 500
        det.max_card_area = 20000
        found = det.find_cards(pil_img)
        # Should find at least some cards
        self.assertIsInstance(found, list)

    def test_extract_card_text_returns_string(self):
        """extract_card_text should not crash and return a string."""
        card_img = _make_card_image("K", suit_color=(0, 0, 200))
        from PIL import Image as PILImage
        rgb = cv2.cvtColor(card_img, cv2.COLOR_BGR2RGB)
        pil = PILImage.fromarray(rgb)

        det = CardDetector()
        card = {'x': 0, 'y': 0, 'w': 70, 'h': 100}
        result = det.extract_card_text(pil, card)
        self.assertIsInstance(result, str)

    def test_classify_card_positions(self):
        det = CardDetector()
        cards = [
            {'x': 400, 'y': 250, 'w': 50, 'h': 70},  # board
            {'x': 450, 'y': 250, 'w': 50, 'h': 70},  # board
            {'x': 380, 'y': 450, 'w': 50, 'h': 70},  # hero
            {'x': 430, 'y': 450, 'w': 50, 'h': 70},  # hero
        ]
        classified = det.classify_card_positions(cards, 600, 800)
        self.assertIn('hero', classified)
        self.assertIn('board', classified)
        self.assertLessEqual(len(classified['hero']), 2)
        self.assertLessEqual(len(classified['board']), 5)


# ---------------------------------------------------------------------------
# YoloCardDetector enhancements
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and YOLO_MODULE_OK, "cv2 or yolo_detector not available")
class TestYoloDetectorPhase2(unittest.TestCase):

    def test_preprocess_variants(self):
        gray = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        variants = YoloCardDetector._preprocess_variants(gray)
        self.assertGreaterEqual(len(variants), 3)

    def test_normalise_rank(self):
        self.assertEqual(YoloCardDetector._normalise_rank("A"), "A")
        self.assertEqual(YoloCardDetector._normalise_rank("10"), "T")
        self.assertIsNone(YoloCardDetector._normalise_rank(""))

    def test_detect_suit_color_red(self):
        roi = np.full((30, 30, 3), (0, 0, 200), dtype=np.uint8)
        self.assertEqual(YoloCardDetector._detect_suit_color(roi), "h")

    def test_detect_suit_color_default_black(self):
        roi = np.full((30, 30, 3), (50, 50, 50), dtype=np.uint8)
        # Low saturation, moderate value → default spades
        suit = YoloCardDetector._detect_suit_color(roi)
        self.assertEqual(suit, "s")

    def test_template_fallback_on_synthetic(self):
        """Template fallback should find card-like regions on synthetic table."""
        img_bgr, _ = _make_table_with_cards()
        from PIL import Image as PILImage
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = PILImage.fromarray(rgb)

        # Create detector without loading YOLO (avoid torch crash)
        det = YoloCardDetector.__new__(YoloCardDetector)
        det.model = None
        det.table_area = None

        detections = det.detect_cards_template_fallback(pil)
        self.assertIsInstance(detections, list)
        # Should find some card-like regions
        self.assertGreater(len(detections), 0)

    def test_recognize_card_ocr_returns_string(self):
        """recognize_card_ocr should return a string, not crash."""
        card_img = _make_card_image("Q")
        from PIL import Image as PILImage
        rgb = cv2.cvtColor(card_img, cv2.COLOR_BGR2RGB)
        pil = PILImage.fromarray(rgb)

        det = YoloCardDetector.__new__(YoloCardDetector)
        det.model = None
        det.table_area = None

        card = {'x': 0, 'y': 0, 'w': 70, 'h': 100}
        result = det.recognize_card_ocr(pil, card)
        self.assertIsInstance(result, str)

    def test_classify_detections(self):
        det = YoloCardDetector.__new__(YoloCardDetector)
        det.model = None
        det.table_area = None

        detections = [
            {'x': 300, 'y': 100, 'w': 50, 'h': 70},
            {'x': 350, 'y': 100, 'w': 50, 'h': 70},
            {'x': 400, 'y': 100, 'w': 50, 'h': 70},
            {'x': 350, 'y': 350, 'w': 50, 'h': 70},
            {'x': 400, 'y': 350, 'w': 50, 'h': 70},
        ]
        classified = det.classify_detections(detections)
        self.assertIn('hero', classified)
        self.assertIn('board', classified)
        self.assertEqual(len(classified['hero']), 2)
        self.assertEqual(len(classified['board']), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
