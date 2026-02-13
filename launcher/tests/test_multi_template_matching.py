"""
Tests for multi_template_matching.py — Phase 2 of vision_fragility.md.

Covers:
- TemplateBank generation and structure
- MultiTemplateMatcher rank/suit/card matching on synthetic card images
- RobustOCR preprocessing variants
- CardRecognizer end-to-end pipeline
- NumericRecognizer for pot/stack parsing
- Edge cases (blank, tiny, noisy images)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import unittest
from typing import Tuple

import numpy as np

try:
    import cv2
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

if CV_AVAILABLE:
    from launcher.vision.multi_template_matching import (
        TemplateBank,
        MultiTemplateMatcher,
        RobustOCR,
        CardRecognizer,
        NumericRecognizer,
        MatchResult,
        RecognitionResult,
        RANKS,
        SUITS,
        RANK_DISPLAY,
        SUIT_DISPLAY,
    )


# ---------------------------------------------------------------------------
# Synthetic card image generators
# ---------------------------------------------------------------------------

def make_card_image(
    rank: str = "A",
    suit: str = "s",
    width: int = 80,
    height: int = 112,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    text_color: Tuple[int, int, int] = (0, 0, 0),
    font_scale: float = 1.0,
) -> np.ndarray:
    """Generate a synthetic card image with rank and suit drawn on it."""
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    # Draw rank (top-left)
    display_rank = "10" if rank == "T" else rank
    cv2.putText(
        img, display_rank,
        (8, 28), cv2.FONT_HERSHEY_SIMPLEX,
        font_scale, text_color, 2, cv2.LINE_AA,
    )

    # Draw suit symbol below rank
    suit_sym = {"s": "S", "h": "H", "d": "D", "c": "C"}  # simple letters
    suit_colors = {
        "s": (0, 0, 0),
        "h": (0, 0, 200),
        "d": (180, 0, 0),
        "c": (0, 100, 0),
    }
    cv2.putText(
        img, suit_sym.get(suit, "?"),
        (10, 55), cv2.FONT_HERSHEY_SIMPLEX,
        font_scale * 0.8, suit_colors.get(suit, text_color), 2, cv2.LINE_AA,
    )

    return img


def make_numeric_image(
    text: str = "$125",
    width: int = 150,
    height: int = 40,
    bg_color: Tuple[int, int, int] = (30, 80, 50),
    text_color: Tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """Generate a synthetic numeric display (pot / stack)."""
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)
    cv2.putText(
        img, text,
        (8, height - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.7, text_color, 2, cv2.LINE_AA,
    )
    return img


# ---------------------------------------------------------------------------
# Tests: TemplateBank
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestTemplateBank(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bank = TemplateBank()
        cls.bank.ensure_generated()

    def test_all_ranks_have_templates(self):
        for rank in RANKS:
            templates = self.bank.get_rank_templates(rank)
            self.assertGreater(
                len(templates), 0,
                f"No templates for rank '{rank}'",
            )

    def test_all_suits_have_templates(self):
        for suit in SUITS:
            templates = self.bank.get_suit_templates(suit)
            self.assertGreater(
                len(templates), 0,
                f"No templates for suit '{suit}'",
            )

    def test_rank_template_is_grayscale(self):
        tmpl = self.bank.get_rank_templates("A")[0]
        self.assertEqual(tmpl.ndim, 2, "Rank template should be grayscale")

    def test_suit_template_is_grayscale(self):
        tmpl = self.bank.get_suit_templates("h")[0]
        self.assertEqual(tmpl.ndim, 2, "Suit template should be grayscale")

    def test_template_count_reasonable(self):
        """Each rank should have multiple templates (sizes × fonts × thickness × variants)."""
        for rank in RANKS:
            count = len(self.bank.get_rank_templates(rank))
            self.assertGreaterEqual(count, 10, f"Rank '{rank}' has too few templates: {count}")

    def test_no_empty_templates(self):
        for rank in RANKS:
            for tmpl in self.bank.get_rank_templates(rank):
                self.assertGreater(tmpl.size, 0)
                h, w = tmpl.shape[:2]
                self.assertGreater(h, 0)
                self.assertGreater(w, 0)

    def test_idempotent_generation(self):
        """Calling ensure_generated twice should be safe."""
        count_before = len(self.bank.get_rank_templates("A"))
        self.bank.ensure_generated()
        count_after = len(self.bank.get_rank_templates("A"))
        self.assertEqual(count_before, count_after)


# ---------------------------------------------------------------------------
# Tests: MultiTemplateMatcher
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestMultiTemplateMatcher(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bank = TemplateBank()
        cls.matcher = MultiTemplateMatcher(bank=cls.bank, match_threshold=0.35)

    def test_match_rank_returns_results(self):
        card = make_card_image("A", "s")
        results = self.matcher.match_rank(card)
        self.assertGreater(len(results), 0, "No rank matches returned")

    def test_match_suit_returns_results(self):
        card = make_card_image("K", "h")
        results = self.matcher.match_suit(card)
        self.assertGreater(len(results), 0, "No suit matches returned")

    def test_match_card_returns_match_result(self):
        card = make_card_image("Q", "d")
        result = self.matcher.match_card(card)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MatchResult)

    def test_match_card_token_has_two_chars(self):
        card = make_card_image("9", "c")
        result = self.matcher.match_card(card)
        if result and result.token:
            self.assertEqual(len(result.token), 2, f"Token '{result.token}' should be 2 chars")

    def test_confidence_is_float_0_to_1(self):
        card = make_card_image("J", "s")
        results = self.matcher.match_rank(card)
        for r in results:
            self.assertGreaterEqual(r.confidence, 0.0)
            self.assertLessEqual(r.confidence, 1.0)

    def test_different_card_sizes(self):
        """Matching should work at various card sizes."""
        for w, h in [(60, 84), (80, 112), (100, 140), (120, 168)]:
            card = make_card_image("K", "h", width=w, height=h)
            result = self.matcher.match_card(card)
            self.assertIsNotNone(result, f"No match at size {w}x{h}")

    def test_different_backgrounds(self):
        """Cards with different background colours should still match."""
        for bg in [(255, 255, 255), (230, 230, 220), (200, 200, 200), (180, 180, 190)]:
            card = make_card_image("A", "s", bg_color=bg)
            result = self.matcher.match_card(card)
            self.assertIsNotNone(result, f"No match with bg={bg}")

    def test_blank_image_low_confidence(self):
        blank = np.full((112, 80, 3), 200, dtype=np.uint8)
        result = self.matcher.match_card(blank)
        if result:
            self.assertLess(result.confidence, 0.8, "Blank should have low confidence")

    def test_noisy_image_still_works(self):
        card = make_card_image("5", "h")
        noise = np.random.randint(0, 30, card.shape, dtype=np.uint8)
        noisy = cv2.add(card, noise)
        result = self.matcher.match_card(noisy)
        self.assertIsNotNone(result)


# ---------------------------------------------------------------------------
# Tests: RobustOCR
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestRobustOCR(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ocr = RobustOCR(use_easyocr=False)  # Tesseract only for tests

    def test_preprocess_variants_count(self):
        img = make_card_image("A", "s")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants = self.ocr._preprocess_variants(gray)
        self.assertGreaterEqual(len(variants), 5, "Expected at least 5 preprocessing variants")

    def test_preprocess_variants_are_2d(self):
        img = make_card_image("K", "h")
        variants = self.ocr._preprocess_variants(img)
        for v in variants:
            self.assertEqual(v.ndim, 2, "Preprocessed variant should be grayscale")

    def test_small_image_upscaled(self):
        """Small images should be upscaled during preprocessing."""
        tiny = np.full((20, 15, 3), 200, dtype=np.uint8)
        cv2.putText(tiny, "A", (2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        variants = self.ocr._preprocess_variants(tiny)
        # After upscaling, variants should be larger
        for v in variants:
            self.assertGreater(v.shape[0], 20, "Small image should have been upscaled")

    def test_parse_rank_basic(self):
        self.assertEqual(RobustOCR._parse_rank("A"), "A")
        self.assertEqual(RobustOCR._parse_rank("10"), "T")
        self.assertEqual(RobustOCR._parse_rank("K"), "K")
        self.assertEqual(RobustOCR._parse_rank("2"), "2")
        self.assertIsNone(RobustOCR._parse_rank(""))
        self.assertIsNone(RobustOCR._parse_rank("xyz"))

    def test_parse_number_basic(self):
        self.assertAlmostEqual(RobustOCR._parse_number("$125.50"), 125.50)
        self.assertAlmostEqual(RobustOCR._parse_number("1,234"), 1234.0)
        self.assertAlmostEqual(RobustOCR._parse_number("5.2k"), 5200.0)
        self.assertAlmostEqual(RobustOCR._parse_number("1.5M"), 1_500_000.0)
        self.assertIsNone(RobustOCR._parse_number(""))
        self.assertIsNone(RobustOCR._parse_number("abc"))

    def test_parse_number_edge_cases(self):
        self.assertAlmostEqual(RobustOCR._parse_number("$0"), 0.0)
        self.assertAlmostEqual(RobustOCR._parse_number("100"), 100.0)
        self.assertAlmostEqual(RobustOCR._parse_number("2.5B"), 2_500_000_000.0)


# ---------------------------------------------------------------------------
# Tests: CardRecognizer (end-to-end)
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestCardRecognizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.recognizer = CardRecognizer(use_easyocr=False)

    def test_recognize_returns_result(self):
        card = make_card_image("A", "s")
        result = self.recognizer.recognize(card)
        self.assertIsInstance(result, RecognitionResult)

    def test_result_has_elapsed(self):
        card = make_card_image("K", "h")
        result = self.recognizer.recognize(card)
        self.assertGreater(result.elapsed_ms, 0)

    def test_result_has_matches(self):
        card = make_card_image("Q", "d")
        result = self.recognizer.recognize(card)
        self.assertGreater(len(result.all_matches), 0)

    def test_all_ranks_produce_results(self):
        """Every rank should produce some recognition result."""
        for rank in RANKS:
            card = make_card_image(rank, "s")
            result = self.recognizer.recognize(card)
            self.assertIsNotNone(
                result.best_token,
                f"No recognition for rank '{rank}'",
            )

    def test_confidence_bounded(self):
        card = make_card_image("7", "c")
        result = self.recognizer.recognize(card)
        self.assertGreaterEqual(result.best_confidence, 0.0)
        self.assertLessEqual(result.best_confidence, 1.0)

    def test_multiple_card_sizes(self):
        """Recognition should work at different card image sizes."""
        for w, h in [(50, 70), (80, 112), (120, 168)]:
            card = make_card_image("A", "s", width=w, height=h)
            result = self.recognizer.recognize(card)
            self.assertIsNotNone(result)
            self.assertGreater(len(result.all_matches), 0)

    def test_performance_single_card(self):
        """Single card recognition should be fast (< 2s without EasyOCR)."""
        card = make_card_image("A", "s")
        result = self.recognizer.recognize(card)
        self.assertLess(result.elapsed_ms, 2000)


# ---------------------------------------------------------------------------
# Tests: NumericRecognizer
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestNumericRecognizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.recognizer = NumericRecognizer(use_easyocr=False)

    def test_recognize_batch_returns_dict(self):
        images = {
            "pot": make_numeric_image("$100"),
            "hero_stack": make_numeric_image("$500"),
        }
        results = self.recognizer.recognize_batch(images)
        self.assertIsInstance(results, dict)

    def test_recognize_returns_tuple_or_none(self):
        img = make_numeric_image("$250")
        result = self.recognizer.recognize(img)
        if result is not None:
            val, conf = result
            self.assertIsInstance(val, float)
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestEdgeCases(unittest.TestCase):

    def test_very_small_image(self):
        """Recognition on a tiny image should not crash."""
        tiny = np.full((5, 5, 3), 200, dtype=np.uint8)
        recognizer = CardRecognizer(use_easyocr=False)
        result = recognizer.recognize(tiny)
        self.assertIsInstance(result, RecognitionResult)

    def test_grayscale_input(self):
        """Passing grayscale instead of BGR should still work."""
        card = make_card_image("A", "s")
        gray = cv2.cvtColor(card, cv2.COLOR_BGR2GRAY)
        recognizer = CardRecognizer(use_easyocr=False)
        result = recognizer.recognize(gray)
        self.assertIsInstance(result, RecognitionResult)

    def test_all_black_image(self):
        black = np.zeros((112, 80, 3), dtype=np.uint8)
        recognizer = CardRecognizer(use_easyocr=False)
        result = recognizer.recognize(black)
        self.assertIsInstance(result, RecognitionResult)

    def test_all_white_image(self):
        white = np.full((112, 80, 3), 255, dtype=np.uint8)
        recognizer = CardRecognizer(use_easyocr=False)
        result = recognizer.recognize(white)
        self.assertIsInstance(result, RecognitionResult)


if __name__ == "__main__":
    unittest.main(verbosity=2)
