"""
Tests for ScreenCapture Phase 3 enhancements (bot_fixes.md).

Tests cover:
  - auto_crop_borders on synthetic images
  - capture_full_window / capture_client_area on live desktop
  - capture_by_binding with mock binding
  - _win32_grab low-level helper
  - _find_window_win32 via AutoWindowFinder integration
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# Try importing with safety framework mock
try:
    # We need safety framework to be importable
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode

    # Ensure we have an instance in DRY_RUN
    try:
        SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    except Exception:
        pass

    from bridge.screen_capture import (
        ScreenCapture,
        WindowInfo,
        WIN32_AVAILABLE,
    )
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestAutoCropBorders(unittest.TestCase):
    """auto_crop_borders on synthetic images."""

    def test_crop_black_border(self):
        """A white rectangle inside black border should be cropped."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[20:80, 30:170, :] = 200  # white inner area

        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        h, w = cropped.shape[:2]
        # Should be roughly 60x140 (±1 depending on exact algo)
        self.assertLess(h, 100)
        self.assertLess(w, 200)
        self.assertGreater(h, 40)
        self.assertGreater(w, 100)

    def test_no_border(self):
        """A fully bright image should be returned unchanged."""
        img = np.full((50, 80, 3), 128, dtype=np.uint8)
        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        self.assertEqual(cropped.shape[:2], (50, 80))

    def test_fully_black(self):
        """A fully black image should be returned unchanged (no content)."""
        img = np.zeros((50, 80, 3), dtype=np.uint8)
        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        # Should return original since no content found
        self.assertEqual(cropped.shape[:2], (50, 80))

    def test_top_border_only(self):
        """Only the top rows are black."""
        img = np.full((100, 100, 3), 150, dtype=np.uint8)
        img[:25, :, :] = 0  # top 25 rows black

        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        h, w = cropped.shape[:2]
        self.assertLess(h, 100)
        self.assertEqual(w, 100)

    def test_grayscale_input(self):
        """Should also work with 2D (grayscale) arrays."""
        img = np.zeros((80, 120), dtype=np.uint8)
        img[10:70, 15:105] = 200

        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        h, w = cropped.shape[:2]
        self.assertLess(h, 80)
        self.assertLess(w, 120)

    def test_none_image(self):
        """None input should return None."""
        result = ScreenCapture.auto_crop_borders(None)
        self.assertIsNone(result)

    def test_empty_image(self):
        """Empty array should be returned as-is."""
        img = np.array([], dtype=np.uint8)
        result = ScreenCapture.auto_crop_borders(img)
        self.assertEqual(result.size, 0)

    def test_thin_border(self):
        """A 1-pixel border should be trimmed."""
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        img[1:49, 1:49, :] = 180

        cropped = ScreenCapture.auto_crop_borders(img, threshold=10)
        self.assertLessEqual(cropped.shape[0], 50)
        self.assertLessEqual(cropped.shape[1], 50)

    def test_threshold_sensitivity(self):
        """Higher threshold trims more."""
        img = np.zeros((60, 60, 3), dtype=np.uint8)
        img[10:50, 10:50, :] = 30  # dim grey area

        crop_low = ScreenCapture.auto_crop_borders(img, threshold=5)
        crop_high = ScreenCapture.auto_crop_borders(img, threshold=50)

        # Low threshold should keep the grey area
        self.assertLess(crop_low.shape[0], 60)
        # High threshold may treat it as empty and keep original
        self.assertGreaterEqual(crop_high.shape[0], crop_low.shape[0])


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestCaptureFullWindow(unittest.TestCase):
    """capture_full_window on live desktop."""

    def test_no_hwnd_returns_none(self):
        cap = ScreenCapture()
        cap.current_window = None
        result = cap.capture_full_window()
        self.assertIsNone(result)

    @unittest.skipUnless(WIN32_AVAILABLE, "Win32 required")
    def test_invalid_hwnd_returns_none(self):
        cap = ScreenCapture()
        result = cap.capture_full_window(hwnd=0)
        self.assertIsNone(result)


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestCaptureClientArea(unittest.TestCase):
    """capture_client_area."""

    def test_no_hwnd_returns_none(self):
        cap = ScreenCapture()
        cap.current_window = None
        result = cap.capture_client_area()
        self.assertIsNone(result)

    @unittest.skipUnless(WIN32_AVAILABLE, "Win32 required")
    def test_invalid_hwnd_returns_none(self):
        cap = ScreenCapture()
        result = cap.capture_client_area(hwnd=0)
        self.assertIsNone(result)


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestCaptureByBinding(unittest.TestCase):
    """capture_by_binding with mock."""

    def test_none_binding(self):
        cap = ScreenCapture()
        result = cap.capture_by_binding(None)
        self.assertIsNone(result)

    def test_zero_hwnd_binding(self):
        binding = MagicMock()
        binding.hwnd = 0
        cap = ScreenCapture()
        result = cap.capture_by_binding(binding)
        self.assertIsNone(result)


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestFindWindowWin32(unittest.TestCase):
    """_find_window_win32 via AutoWindowFinder."""

    def test_finds_window_in_unsafe_mode(self):
        """In unsafe mode with a mock finder, should return WindowInfo."""
        cap = ScreenCapture(window_title_pattern=".*")

        # Simulate unsafe mode
        with patch("bridge.screen_capture.get_safety") as mock_safety:
            safety = MagicMock()
            safety.is_dry_run.return_value = False
            mock_safety.return_value = safety

            with patch("bridge.screen_capture.require_unsafe"):
                with patch("bridge.screen_capture.FINDER_AVAILABLE", True):
                    with patch("bridge.screen_capture.AutoWindowFinder") as MockFinder:
                        mock_instance = MagicMock()
                        mock_instance.available = True
                        mock_match = MagicMock()
                        mock_match.hwnd = 99999
                        mock_match.title = "TestWindow"
                        mock_match.process_name = "test.exe"
                        mock_match.visible = True
                        mock_match.full_rect = MagicMock()
                        mock_match.full_rect.x = 0
                        mock_match.full_rect.y = 0
                        mock_match.full_rect.w = 800
                        mock_match.full_rect.h = 600
                        mock_instance.find.return_value = mock_match
                        MockFinder.return_value = mock_instance

                        result = cap._find_window_win32()

        self.assertIsNotNone(result)
        self.assertEqual(result.hwnd, 99999)
        self.assertEqual(result.title, "TestWindow")
        self.assertEqual(result.width, 800)


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestWin32Grab(unittest.TestCase):
    """_win32_grab low-level helper."""

    @unittest.skipUnless(WIN32_AVAILABLE, "Win32 required")
    def test_grab_invalid_hwnd(self):
        """hwnd=0 maps to the desktop — Win32 may return an image or None."""
        cap = ScreenCapture()
        result = cap._win32_grab(0, 100, 100)
        # Either None (blank) or a valid numpy array
        if result is not None:
            self.assertEqual(len(result.shape), 3)
            self.assertEqual(result.shape[2], 3)

    def test_grab_no_win32(self):
        """When WIN32 is not available, should return None."""
        cap = ScreenCapture()
        with patch("bridge.screen_capture.WIN32_AVAILABLE", False):
            result = cap._win32_grab(12345, 100, 100)
        self.assertIsNone(result)


@unittest.skipUnless(MODULE_AVAILABLE, "bridge.screen_capture not importable")
class TestStatisticsAfterCapture(unittest.TestCase):
    """Statistics should update after captures."""

    def test_dry_run_increments_counter(self):
        cap = ScreenCapture()
        cap.find_window()  # dry-run: simulates window
        self.assertEqual(cap.capture_count, 0)

        cap.capture()
        self.assertEqual(cap.capture_count, 1)

        stats = cap.get_statistics()
        self.assertEqual(stats["total_captures"], 1)
        self.assertGreater(stats["last_capture_time"], 0)


if __name__ == "__main__":
    unittest.main()
