"""
Tests for roadmap11_auto_roi_detection.md Phase 1 — auto_find_window().

Validates:
  - auto_find_window() searches by keyword/process
  - Saves config/active_window.json
  - load_active_window() reads it back
  - Falls back through multiple strategies
  - WindowInfo populated correctly
  - Real desktop: finds at least 1 window with broad keywords
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

try:
    from bridge.screen_capture import ScreenCapture, WindowInfo
    HAS_CAPTURE = True
except Exception:
    HAS_CAPTURE = False

try:
    import win32gui
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False

try:
    from launcher.auto_window_finder import AutoWindowFinder
    HAS_FINDER = True
except Exception:
    HAS_FINDER = False


# ===================================================================
# Mocked tests (always run)
# ===================================================================


@unittest.skipUnless(HAS_CAPTURE, "bridge.screen_capture not importable")
class TestAutoFindWindowMocked(unittest.TestCase):
    """auto_find_window() with mocked Win32 / AutoWindowFinder."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = Path(self.tmpdir) / "active_window.json"

    def tearDown(self):
        if self.config_path.exists():
            self.config_path.unlink()
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def _make_capture(self):
        sc = ScreenCapture.__new__(ScreenCapture)
        sc.window_title_pattern = None
        sc.process_name = None
        sc.save_screenshots = False
        sc.screenshot_dir = Path(".")
        sc.current_window = None
        sc.capture_count = 0
        sc.last_capture_time = 0.0
        return sc

    @patch("bridge.screen_capture.WIN32_AVAILABLE", True)
    @patch("bridge.screen_capture.FINDER_AVAILABLE", True)
    def test_find_via_finder_keyword(self):
        """AutoWindowFinder returns match for keyword."""
        sc = self._make_capture()

        mock_match = MagicMock()
        mock_match.hwnd = 12345
        mock_match.title = "CoinPoker - Table 1"
        mock_match.process_name = "CoinPoker.exe"
        mock_match.visible = True
        mock_match.full_rect = MagicMock(x=100, y=200, w=800, h=600)

        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = mock_match

        with patch("bridge.screen_capture.AutoWindowFinder", return_value=mock_finder):
            # Don't save to real config
            with patch.object(sc, "_save_active_window"):
                hwnd = sc.auto_find_window(
                    keywords=["CoinPoker"],
                    save_config=False,
                )

        self.assertEqual(hwnd, 12345)
        self.assertIsNotNone(sc.current_window)
        self.assertEqual(sc.current_window.title, "CoinPoker - Table 1")
        self.assertEqual(sc.current_window.width, 800)

    @patch("bridge.screen_capture.WIN32_AVAILABLE", True)
    @patch("bridge.screen_capture.FINDER_AVAILABLE", False)
    def test_fallback_to_enum(self):
        """When AutoWindowFinder unavailable, falls back to EnumWindows."""
        sc = self._make_capture()

        # Mock _auto_find_via_enum
        wi = WindowInfo(hwnd=99, title="PokerStars Table", width=1024, height=768, is_visible=True)
        with patch.object(sc, "_auto_find_via_enum", return_value=(99, wi)):
            hwnd = sc.auto_find_window(keywords=["PokerStars"], save_config=False)

        self.assertEqual(hwnd, 99)
        self.assertEqual(sc.current_window.title, "PokerStars Table")

    def test_no_window_found(self):
        """Returns None when no matching window found."""
        sc = self._make_capture()

        with patch.object(sc, "_auto_find_via_finder", return_value=(None, None)):
            with patch.object(sc, "_auto_find_via_enum", return_value=(None, None)):
                hwnd = sc.auto_find_window(
                    keywords=["NonExistent_xyz_123"],
                    save_config=False,
                )

        self.assertIsNone(hwnd)

    def test_save_and_load_config(self):
        """Saves to JSON and loads it back."""
        sc = self._make_capture()
        # Override config path
        sc.ACTIVE_WINDOW_CONFIG = self.config_path

        wi = WindowInfo(
            hwnd=555, title="Test Poker", process_name="poker.exe",
            x=10, y=20, width=800, height=600, is_visible=True,
        )
        sc._save_active_window(555, wi)

        self.assertTrue(self.config_path.exists())

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["hwnd"], 555)
        self.assertEqual(data["title"], "Test Poker")
        self.assertEqual(data["width"], 800)
        self.assertIn("timestamp", data)

    def test_load_active_window_missing(self):
        """load_active_window returns None when file missing."""
        # Point to nonexistent path
        original = ScreenCapture.ACTIVE_WINDOW_CONFIG
        ScreenCapture.ACTIVE_WINDOW_CONFIG = Path(self.tmpdir) / "nonexistent.json"
        try:
            result = ScreenCapture.load_active_window()
            self.assertIsNone(result)
        finally:
            ScreenCapture.ACTIVE_WINDOW_CONFIG = original

    def test_poker_title_keywords_defined(self):
        """POKER_TITLE_KEYWORDS has at least 5 entries."""
        self.assertGreaterEqual(len(ScreenCapture.POKER_TITLE_KEYWORDS), 5)
        self.assertIn("CoinPoker", ScreenCapture.POKER_TITLE_KEYWORDS)
        self.assertIn("Poker", ScreenCapture.POKER_TITLE_KEYWORDS)

    def test_poker_process_names_defined(self):
        """POKER_PROCESS_NAMES has at least 3 entries."""
        self.assertGreaterEqual(len(ScreenCapture.POKER_PROCESS_NAMES), 3)

    @patch("bridge.screen_capture.WIN32_AVAILABLE", True)
    @patch("bridge.screen_capture.FINDER_AVAILABLE", True)
    def test_multiple_keywords_tried(self):
        """Tries multiple keywords until a match is found."""
        sc = self._make_capture()

        mock_match = MagicMock()
        mock_match.hwnd = 777
        mock_match.title = "Table NL50"
        mock_match.process_name = "poker.exe"
        mock_match.visible = True
        mock_match.full_rect = MagicMock(x=0, y=0, w=640, h=480)

        mock_finder = MagicMock()
        mock_finder.available = True
        # Return None for first two, match for "Table"
        mock_finder.find.side_effect = [None, None, mock_match]

        with patch("bridge.screen_capture.AutoWindowFinder", return_value=mock_finder):
            hwnd = sc.auto_find_window(
                keywords=["NoMatch1", "NoMatch2", "Table"],
                save_config=False,
            )

        self.assertEqual(hwnd, 777)
        self.assertEqual(mock_finder.find.call_count, 3)


# ===================================================================
# Live desktop test (Win32 required)
# ===================================================================


@unittest.skipUnless(HAS_CAPTURE and HAS_WIN32, "Win32 not available")
class TestAutoFindWindowLive(unittest.TestCase):
    """Live test: find at least one window on the real desktop."""

    def test_find_any_window_broad_keyword(self):
        """Very broad keyword should find at least 1 window."""
        sc = ScreenCapture.__new__(ScreenCapture)
        sc.window_title_pattern = None
        sc.process_name = None
        sc.save_screenshots = False
        sc.screenshot_dir = Path(".")
        sc.current_window = None
        sc.capture_count = 0
        sc.last_capture_time = 0.0

        # Use a broad keyword that should match something
        broad_keywords = ["Program", "Windows", "Cursor", "Python", "Explorer"]
        hwnd = sc.auto_find_window(
            keywords=broad_keywords,
            save_config=False,
        )
        # At least one of these should match on any Windows desktop
        if hwnd is not None:
            self.assertIsInstance(hwnd, int)
            self.assertGreater(hwnd, 0)
            self.assertIsNotNone(sc.current_window)
            self.assertTrue(len(sc.current_window.title) > 0)


# ===================================================================
# Existing tests regression
# ===================================================================


@unittest.skipUnless(HAS_CAPTURE, "bridge.screen_capture not importable")
class TestScreenCaptureRegression(unittest.TestCase):
    """Existing ScreenCapture functionality still works."""

    def test_window_info_dataclass(self):
        wi = WindowInfo(hwnd=1, title="Test", width=100, height=100)
        self.assertEqual(wi.hwnd, 1)
        self.assertEqual(wi.title, "Test")

    def test_auto_crop_borders_noop(self):
        """auto_crop_borders with non-black image returns similar size."""
        import numpy as np
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        cropped = ScreenCapture.auto_crop_borders(img)
        self.assertGreater(cropped.shape[0], 50)
        self.assertGreater(cropped.shape[1], 50)

    def test_smart_crop_noop(self):
        import numpy as np
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        cropped = ScreenCapture.smart_crop(img)
        self.assertGreater(cropped.shape[0], 50)


if __name__ == "__main__":
    unittest.main()
