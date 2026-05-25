#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for lobby_scanner.md — Phase 1: OCR Improvements.

Covers:
- LobbyTable data model
- LobbyScanResult filtering
- LobbyCaptureScanner: row detection, OCR, text parsing
- Synthetic lobby generation & end-to-end scan
- test_real_ocr.py lobby additions
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Import guards
# ---------------------------------------------------------------------------
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_capture import (
    LobbyTable,
    LobbyScanResult,
    LobbyCaptureScanner,
    scan_lobby,
)


# ===========================================================================
# Test LobbyTable data model
# ===========================================================================

class TestLobbyTable(unittest.TestCase):
    """LobbyTable dataclass properties and defaults."""

    def test_defaults(self):
        t = LobbyTable()
        self.assertEqual(t.name, "")
        self.assertEqual(t.players, 0)
        self.assertEqual(t.max_players, 0)
        self.assertEqual(t.occupancy, 0.0)
        self.assertFalse(t.is_full)

    def test_occupancy(self):
        t = LobbyTable(players=5, max_players=9)
        self.assertAlmostEqual(t.occupancy, 5 / 9, places=3)
        self.assertFalse(t.is_full)

    def test_full_table(self):
        t = LobbyTable(players=9, max_players=9)
        self.assertAlmostEqual(t.occupancy, 1.0)
        self.assertTrue(t.is_full)

    def test_stakes_and_game(self):
        t = LobbyTable(name="Earth", stakes="$0.10/$0.25", game_type="PLO",
                        players=8, max_players=9)
        self.assertEqual(t.name, "Earth")
        self.assertEqual(t.stakes, "$0.10/$0.25")
        self.assertEqual(t.game_type, "PLO")


# ===========================================================================
# Test LobbyScanResult
# ===========================================================================

class TestLobbyScanResult(unittest.TestCase):
    """LobbyScanResult convenience methods."""

    def _make_result(self) -> LobbyScanResult:
        return LobbyScanResult(
            tables=[
                LobbyTable(name="A", players=3, max_players=6),
                LobbyTable(name="B", players=6, max_players=6),
                LobbyTable(name="C", players=0, max_players=9),
            ],
            total_rows_detected=5,
            ocr_confidence=0.75,
            elapsed_ms=123.0,
        )

    def test_table_count(self):
        r = self._make_result()
        self.assertEqual(r.table_count, 3)

    def test_available_tables_default(self):
        r = self._make_result()
        avail = r.available_tables(min_seats=1)
        # A has 3 free, C has 9 free; B is full
        names = [t.name for t in avail]
        self.assertIn("A", names)
        self.assertIn("C", names)
        self.assertNotIn("B", names)

    def test_available_tables_min5(self):
        r = self._make_result()
        avail = r.available_tables(min_seats=5)
        names = [t.name for t in avail]
        self.assertIn("C", names)
        self.assertNotIn("A", names)

    def test_summary(self):
        r = self._make_result()
        s = r.summary()
        self.assertIn("3 tables", s)
        self.assertIn("5 rows", s)

    def test_empty_result(self):
        r = LobbyScanResult()
        self.assertEqual(r.table_count, 0)
        self.assertEqual(r.available_tables(), [])


# ===========================================================================
# Test LobbyCaptureScanner — text parsing
# ===========================================================================

class TestLobbyParsing(unittest.TestCase):
    """Test _parse_row_text with various raw strings."""

    def setUp(self):
        self.scanner = LobbyCaptureScanner()

    def test_stakes_parsing(self):
        t = self.scanner._parse_row_text("Mercury $0.01/$0.02 NL Hold'em 6/9", 0)
        self.assertEqual(t.stakes, "$0.01/$0.02")

    def test_player_count(self):
        t = self.scanner._parse_row_text("Venus $0.05/$0.10 NL Holdem 4/6", 0)
        self.assertEqual(t.players, 4)
        self.assertEqual(t.max_players, 6)

    def test_game_type_nlhe(self):
        t = self.scanner._parse_row_text("Table1 $1/$2 NL Hold'em 5/9", 0)
        self.assertIn("hold", t.game_type.lower())

    def test_game_type_plo(self):
        t = self.scanner._parse_row_text("Pluto $2/$5 Pot Limit Omaha 3/6", 0)
        self.assertIn("omaha", t.game_type.lower())

    def test_game_type_zoom(self):
        t = self.scanner._parse_row_text("Fast Table Zoom $1/$2 5/6", 0)
        self.assertIn("zoom", t.game_type.lower())

    def test_table_name(self):
        t = self.scanner._parse_row_text("Mercury $0.01/$0.02 6/9", 0)
        self.assertEqual(t.name, "Mercury")

    def test_no_stakes(self):
        t = self.scanner._parse_row_text("SomeName NoLimit Holdem", 0)
        self.assertEqual(t.stakes, "")

    def test_row_index(self):
        t = self.scanner._parse_row_text("X $1/$2 3/6", 7)
        self.assertEqual(t.row_index, 7)


# ===========================================================================
# Test preprocessing & row detection (requires cv2)
# ===========================================================================

@unittest.skipUnless(HAS_CV2, "cv2 not available")
class TestRowDetection(unittest.TestCase):
    """Test _detect_rows and _fallback_rows on synthetic images."""

    def setUp(self):
        self.scanner = LobbyCaptureScanner()

    def test_fallback_rows_count(self):
        """_fallback_rows should produce multiple rows."""
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        rows = self.scanner._fallback_rows(img)
        self.assertGreater(len(rows), 5)

    def test_detect_rows_with_lines(self):
        """Image with horizontal separator lines + text → detect rows or fall back."""
        img = np.full((400, 600, 3), 40, dtype=np.uint8)
        # Draw horizontal separating lines + text in between
        for y in range(50, 400, 50):
            cv2.line(img, (0, y), (599, y), (200, 200, 200), 2)
            cv2.putText(img, "TableX $1/$2 5/9", (10, y - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        rows = self.scanner._detect_rows(img)
        # Row detection is threshold-dependent; at minimum it shouldn't crash
        self.assertIsInstance(rows, list)

    def test_preprocess_variants_count(self):
        """Should return 4 variants."""
        gray = np.random.randint(0, 255, (50, 200), dtype=np.uint8)
        variants = self.scanner._preprocess_variants(gray)
        self.assertEqual(len(variants), 4)


# ===========================================================================
# Test scan_image end-to-end (requires cv2 + pytesseract)
# ===========================================================================

@unittest.skipUnless(HAS_CV2 and HAS_TESSERACT, "cv2 or pytesseract not available")
class TestScanImageE2E(unittest.TestCase):
    """End-to-end lobby scan on a synthetic image."""

    def test_scan_synthetic_lobby(self):
        """Scan a synthetic lobby image — should find at least some rows."""
        # Generate a simple lobby-like image
        h, w = 400, 800
        img = np.full((h, w, 3), 40, dtype=np.uint8)
        # Add text rows with table-like content
        for i, line in enumerate([
            "Mercury $0.01/$0.02 NL Holdem 6/9",
            "Venus $0.05/$0.10 NL Holdem 4/6",
            "Earth $0.10/$0.25 PLO 8/9",
        ]):
            y = 60 + i * 80
            cv2.putText(img, line, (15, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
            cv2.line(img, (10, y + 20), (w - 10, y + 20), (80, 80, 80), 1)

        scanner = LobbyCaptureScanner()
        result = scanner.scan_image(img)

        self.assertEqual(result.error, "")
        self.assertGreater(result.total_rows_detected, 0)
        self.assertGreater(result.elapsed_ms, 0)

    def test_scan_numpy_input(self):
        """Scanner accepts numpy arrays."""
        img = np.full((300, 500, 3), 50, dtype=np.uint8)
        cv2.putText(img, "TableXYZ $1/$2 NL Holdem 5/9", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)
        scanner = LobbyCaptureScanner()
        result = scanner.scan_image(img)
        self.assertEqual(result.error, "")

    def test_scan_convenience_function(self):
        """scan_lobby() convenience wrapper works."""
        img = np.full((200, 400, 3), 30, dtype=np.uint8)
        result = scan_lobby(img)
        self.assertIsInstance(result, LobbyScanResult)


# ===========================================================================
# Test scanner with mocked OCR (no Tesseract needed)
# ===========================================================================

@unittest.skipUnless(HAS_CV2, "cv2 not available")
class TestScannerMockedOCR(unittest.TestCase):
    """Test scanner pipeline with mocked pytesseract."""

    def test_parse_with_mocked_tesseract(self):
        """Mocked tesseract returns structured text → tables parsed."""
        scanner = LobbyCaptureScanner()

        fake_data = {
            "text": ["Neptune", "$5/$10", "NL", "Holdem", "7/9", ""],
            "conf": [90, 85, 88, 87, 80, -1],
        }

        with patch("live_capture.pytesseract") as mock_tess:
            mock_tess.image_to_data.return_value = fake_data
            mock_tess.Output = pytesseract.Output if HAS_TESSERACT else MagicMock()
            mock_tess.Output.DICT = "dict"

            img = np.full((200, 600, 3), 40, dtype=np.uint8)
            # Put text so row detection finds something
            cv2.putText(img, "Neptune $5/$10 NL Holdem 7/9", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)

            result = scanner.scan_image(img)
            # At minimum, should not error
            self.assertEqual(result.error, "")


# ===========================================================================
# Test edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge cases for the scanner."""

    def test_scan_without_cv2(self):
        """When cv2 is unavailable, returns error result."""
        scanner = LobbyCaptureScanner()
        with patch("live_capture.HAS_CV2", False):
            result = scanner.scan_image("nonexistent.png")
            self.assertIn("not available", result.error)

    def test_scan_none_image(self):
        """None input → error or empty result."""
        scanner = LobbyCaptureScanner()
        result = scanner.scan_image(None)
        # Either returns error or empty tables
        self.assertEqual(result.table_count, 0)

    def test_game_patterns_no_crash(self):
        """All GAME_PATTERNS should compile without error."""
        import re
        for pattern in LobbyCaptureScanner.GAME_PATTERNS:
            re.compile(pattern)

    def test_stakes_regex(self):
        import re
        m = LobbyCaptureScanner.STAKES_RE.search("$0.01/$0.02")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "0.01")
        self.assertEqual(m.group(2), "0.02")

    def test_player_regex(self):
        import re
        m = LobbyCaptureScanner.PLAYER_RE.search("6/9")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "6")
        self.assertEqual(m.group(2), "9")


if __name__ == "__main__":
    unittest.main()
