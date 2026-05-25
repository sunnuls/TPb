"""
Tests for roadmap13 Phase 2 — auto_find_window with visual logo search.
"""
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from bridge.screen_capture import ScreenCapture, WindowInfo


class TestAutoFindWindowVisual(unittest.TestCase):
    """Tests for the visual logo search strategy in auto_find_window."""

    def _make_sc(self) -> ScreenCapture:
        with patch("bridge.screen_capture.get_safety") as mock_safety:
            mock_safety.return_value.is_dry_run.return_value = True
            return ScreenCapture()

    # ---------------------------------------------------------------
    # Unit tests for _auto_find_via_logo
    # ---------------------------------------------------------------

    @patch("bridge.screen_capture.CV2_AVAILABLE", True)
    @patch("bridge.screen_capture.MSS_AVAILABLE", True)
    @patch("bridge.screen_capture.WIN32_AVAILABLE", True)
    def test_visual_search_called_when_title_fails(self):
        """If title/process strategies return None, visual search is tried."""
        sc = self._make_sc()
        mock_logo_result = (99999, WindowInfo(hwnd=99999, title="Poker", width=800, height=600))

        with patch.object(sc, "_auto_find_via_finder", return_value=(None, None)), \
             patch.object(sc, "_auto_find_via_enum", return_value=(None, None)), \
             patch.object(sc, "_auto_find_via_logo", return_value=mock_logo_result) as mock_logo, \
             patch.object(sc, "_save_active_window"):

            result = sc.auto_find_window()
            mock_logo.assert_called_once()
            self.assertEqual(result, 99999)

    @patch("bridge.screen_capture.CV2_AVAILABLE", True)
    @patch("bridge.screen_capture.MSS_AVAILABLE", True)
    def test_visual_not_called_when_title_succeeds(self):
        """If title strategy works, visual search is skipped."""
        sc = self._make_sc()
        title_result = (11111, WindowInfo(hwnd=11111, title="CoinPoker"))

        with patch.object(sc, "_auto_find_via_finder", return_value=title_result), \
             patch.object(sc, "_auto_find_via_logo") as mock_logo, \
             patch.object(sc, "_save_active_window"):

            result = sc.auto_find_window()
            mock_logo.assert_not_called()
            self.assertEqual(result, 11111)

    @patch("bridge.screen_capture.CV2_AVAILABLE", False)
    @patch("bridge.screen_capture.MSS_AVAILABLE", True)
    def test_visual_skipped_without_cv2(self):
        """Visual search is skipped if cv2 is not available."""
        sc = self._make_sc()

        with patch.object(sc, "_auto_find_via_finder", return_value=(None, None)), \
             patch.object(sc, "_auto_find_via_enum", return_value=(None, None)), \
             patch("bridge.screen_capture.WIN32_AVAILABLE", False):
            result = sc.auto_find_window()
            self.assertIsNone(result)

    @patch("bridge.screen_capture.CV2_AVAILABLE", True)
    @patch("bridge.screen_capture.MSS_AVAILABLE", False)
    def test_visual_skipped_without_mss(self):
        """Visual search is skipped if mss is not available."""
        sc = self._make_sc()

        with patch.object(sc, "_auto_find_via_finder", return_value=(None, None)), \
             patch.object(sc, "_auto_find_via_enum", return_value=(None, None)), \
             patch("bridge.screen_capture.WIN32_AVAILABLE", False):
            result = sc.auto_find_window()
            self.assertIsNone(result)

    def test_logo_template_path_attribute(self):
        """ScreenCapture has LOGO_TEMPLATE_PATH pointing to logo."""
        self.assertTrue(hasattr(ScreenCapture, "LOGO_TEMPLATE_PATH"))
        self.assertIn("logo", str(ScreenCapture.LOGO_TEMPLATE_PATH))

    def test_logo_match_threshold_attribute(self):
        """ScreenCapture has LOGO_MATCH_THRESHOLD in sensible range."""
        self.assertTrue(hasattr(ScreenCapture, "LOGO_MATCH_THRESHOLD"))
        self.assertGreater(ScreenCapture.LOGO_MATCH_THRESHOLD, 0.3)
        self.assertLess(ScreenCapture.LOGO_MATCH_THRESHOLD, 0.9)


class TestAutoFindVialogoUnit(unittest.TestCase):
    """Isolated unit tests for _auto_find_via_logo internals."""

    def _make_sc(self) -> ScreenCapture:
        with patch("bridge.screen_capture.get_safety") as mock_safety:
            mock_safety.return_value.is_dry_run.return_value = True
            return ScreenCapture()

    @patch("bridge.screen_capture.CV2_AVAILABLE", True)
    @patch("bridge.screen_capture.MSS_AVAILABLE", True)
    def test_logo_not_found_returns_none(self):
        """If logo template file doesn't exist, returns (None, None)."""
        sc = self._make_sc()
        with patch.object(type(sc), "LOGO_TEMPLATE_PATH", Path("nonexistent.png")):
            result = sc._auto_find_via_logo()
            self.assertEqual(result, (None, None))

    @patch("bridge.screen_capture.CV2_AVAILABLE", False)
    def test_no_cv2_returns_none(self):
        sc = self._make_sc()
        result = sc._auto_find_via_logo()
        self.assertEqual(result, (None, None))

    @patch("bridge.screen_capture.CV2_AVAILABLE", True)
    @patch("bridge.screen_capture.MSS_AVAILABLE", True)
    def test_low_confidence_returns_none(self):
        """If template match on blank screen is below threshold, returns None."""
        sc = self._make_sc()
        import cv2 as _cv2

        fake_logo = np.zeros((20, 40), dtype=np.uint8)
        fake_screen = np.zeros((600, 800, 3), dtype=np.uint8)

        # Build a mock mss context manager
        mock_grab = MagicMock()
        mock_grab.__array__ = lambda s: fake_screen

        mock_ctx = MagicMock()
        mock_ctx.monitors = [{"left": 0, "top": 0, "width": 800, "height": 600}]
        mock_ctx.grab.return_value = mock_grab

        mock_mss_cls = MagicMock()
        mock_mss_cls.__enter__ = MagicMock(return_value=mock_ctx)
        mock_mss_cls.__exit__ = MagicMock(return_value=False)

        import bridge.screen_capture as sc_mod
        original_mss = getattr(sc_mod, "mss", None)

        mock_mss_module = MagicMock()
        mock_mss_module.mss.return_value = mock_mss_cls
        sc_mod.mss = mock_mss_module

        try:
            with patch.object(_cv2, "imread", return_value=fake_logo):
                result = sc._auto_find_via_logo()
                self.assertEqual(result, (None, None))
        finally:
            if original_mss is not None:
                sc_mod.mss = original_mss


class TestWindowAtPoint(unittest.TestCase):
    """Tests for _window_at_point helper."""

    def _make_sc(self) -> ScreenCapture:
        with patch("bridge.screen_capture.get_safety") as mock_safety:
            mock_safety.return_value.is_dry_run.return_value = True
            return ScreenCapture()

    @patch("bridge.screen_capture.WIN32_AVAILABLE", False)
    def test_no_win32_returns_none(self):
        sc = self._make_sc()
        result = sc._window_at_point(100, 200)
        self.assertEqual(result, (None, None))

    @patch("bridge.screen_capture.WIN32_AVAILABLE", True)
    def test_returns_tuple(self):
        """_window_at_point returns a tuple of (hwnd_or_None, info_or_None)."""
        sc = self._make_sc()
        result = sc._window_at_point(100, 200)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


class TestSaveLoadActiveWindow(unittest.TestCase):
    """Verify config persistence works with new strategies."""

    def _make_sc(self) -> ScreenCapture:
        with patch("bridge.screen_capture.get_safety") as mock_safety:
            mock_safety.return_value.is_dry_run.return_value = True
            return ScreenCapture()

    def test_save_and_load(self):
        import tempfile
        sc = self._make_sc()
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "active_window.json"
            with patch.object(type(sc), "ACTIVE_WINDOW_CONFIG", cfg_path):
                info = WindowInfo(hwnd=42, title="TestPoker", width=800, height=600)
                sc._save_active_window(42, info)
                self.assertTrue(cfg_path.exists())
                data = json.loads(cfg_path.read_text())
                self.assertEqual(data["hwnd"], 42)
                self.assertEqual(data["title"], "TestPoker")

    def test_load_nonexistent(self):
        result = ScreenCapture.load_active_window()
        # May or may not exist on disk, just verify it doesn't crash
        self.assertIn(type(result), (dict, type(None)))


if __name__ == "__main__":
    unittest.main()
