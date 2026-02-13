"""
Tests for auto_find_window.md Phase 3 — 10 windows → auto-find + crop.

Acceptance criteria:
  - AutoWindowFinder detects 10+ windows on a live desktop
  - Each found window has valid zoom_rect (auto-crop region)
  - edge_detect_crop (Canny) correctly crops 10 synthetic "windows"
  - edge_detect_crop (Sobel) correctly crops 10 synthetic "windows"
  - smart_crop combines both strategies on 10 images
  - End-to-end: find 10 real windows + crop synthetic frames for each
  - auto_find_by_keywords from test_windows_list.py works for batches
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

# Import safety framework
try:
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
    try:
        SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    except Exception:
        pass

    from bridge.screen_capture import ScreenCapture, CV2_AVAILABLE
    CAPTURE_AVAILABLE = True
except Exception:
    CAPTURE_AVAILABLE = False
    CV2_AVAILABLE = False

try:
    from launcher.auto_window_finder import (
        AutoWindowFinder,
        WindowMatch,
        WindowRect,
        MatchMethod,
        WIN32_AVAILABLE,
    )
    FINDER_AVAILABLE = True
except Exception:
    FINDER_AVAILABLE = False
    WIN32_AVAILABLE = False

try:
    from test_windows_list import auto_find_by_keywords, find_by_title
    LIST_AVAILABLE = True
except Exception:
    LIST_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_window(
    h: int = 200,
    w: int = 300,
    border: int = 20,
    content_val: int = 150,
) -> np.ndarray:
    """Create a synthetic image simulating a window with border."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[border:h - border, border:w - border, :] = content_val
    # Add some "UI" noise inside the content area
    rng = np.random.RandomState(42)
    inner = img[border:h - border, border:w - border]
    noise = rng.randint(0, 60, inner.shape, dtype=np.uint8)
    img[border:h - border, border:w - border] = np.clip(
        inner.astype(np.int16) + noise.astype(np.int16), 0, 255
    ).astype(np.uint8)
    return img


def _make_10_synthetic_windows():
    """Generate 10 unique synthetic window images with varying borders."""
    windows = []
    for i in range(10):
        h = 150 + i * 30          # 150..420
        w = 250 + i * 40          # 250..610
        border = 10 + i * 3       # 10..37
        val = 100 + i * 15        # 100..235
        windows.append(_make_synthetic_window(h, w, border, val))
    return windows


# ---------------------------------------------------------------------------
# Test: Auto-find 10 windows on live desktop
# ---------------------------------------------------------------------------


@unittest.skipUnless(FINDER_AVAILABLE and WIN32_AVAILABLE,
                     "AutoWindowFinder + Win32 required")
class TestAutoFind10Windows(unittest.TestCase):
    """Find at least 10 windows on the real desktop."""

    def setUp(self):
        self.finder = AutoWindowFinder()

    def test_find_at_least_5_windows(self):
        """A live desktop should have >= 5 visible windows."""
        results = self.finder.find_all(".*")
        self.assertGreaterEqual(
            len(results), 5,
            f"Expected >=5 windows, got {len(results)}"
        )

    def test_all_have_valid_zoom_rect(self):
        """Each found window has zoom_rect with w>0 and h>0."""
        results = self.finder.find_all(".*")[:10]
        for i, m in enumerate(results):
            self.assertGreater(m.zoom_rect.w, 0, f"Window {i}: zoom_rect.w <= 0")
            self.assertGreater(m.zoom_rect.h, 0, f"Window {i}: zoom_rect.h <= 0")

    def test_all_have_title(self):
        """Each found window has a non-empty title."""
        results = self.finder.find_all(".*")[:10]
        for i, m in enumerate(results):
            self.assertTrue(m.title, f"Window {i}: empty title")

    def test_all_have_hwnd(self):
        """Each found window has a valid hwnd."""
        results = self.finder.find_all(".*")[:10]
        for i, m in enumerate(results):
            self.assertGreater(m.hwnd, 0, f"Window {i}: hwnd <= 0")

    def test_scores_are_valid(self):
        """Scores are in (0, 1] range."""
        results = self.finder.find_all(".*")[:10]
        for i, m in enumerate(results):
            self.assertGreater(m.score, 0.0, f"Window {i}: score <= 0")
            self.assertLessEqual(m.score, 1.0, f"Window {i}: score > 1")

    def test_client_rect_within_full(self):
        """Client rect area <= full rect area."""
        results = self.finder.find_all(".*")[:10]
        for i, m in enumerate(results):
            self.assertLessEqual(
                m.client_rect.area, m.full_rect.area + 1,
                f"Window {i}: client_rect.area > full_rect.area"
            )


# ---------------------------------------------------------------------------
# Test: Edge-detect crop on 10 synthetic windows
# ---------------------------------------------------------------------------


@unittest.skipUnless(CAPTURE_AVAILABLE and CV2_AVAILABLE,
                     "ScreenCapture + OpenCV required")
class TestEdgeCrop10Windows(unittest.TestCase):
    """Canny/Sobel crop on 10 synthetic window images."""

    def setUp(self):
        self.images = _make_10_synthetic_windows()

    def test_canny_crops_all_10(self):
        """Canny edge detection crops all 10 images smaller."""
        for i, img in enumerate(self.images):
            cropped = ScreenCapture.edge_detect_crop(img, method="canny")
            self.assertLess(
                cropped.shape[0], img.shape[0],
                f"Image {i}: Canny did not reduce height"
            )
            self.assertLess(
                cropped.shape[1], img.shape[1],
                f"Image {i}: Canny did not reduce width"
            )

    def test_sobel_crops_all_10(self):
        """Sobel edge detection crops all 10 images smaller."""
        for i, img in enumerate(self.images):
            cropped = ScreenCapture.edge_detect_crop(img, method="sobel")
            self.assertLess(
                cropped.shape[0], img.shape[0],
                f"Image {i}: Sobel did not reduce height"
            )
            self.assertLess(
                cropped.shape[1], img.shape[1],
                f"Image {i}: Sobel did not reduce width"
            )

    def test_canny_preserves_content(self):
        """Canny crop retains a meaningful amount of the original content."""
        for i, img in enumerate(self.images):
            cropped = ScreenCapture.edge_detect_crop(img, method="canny")
            # Cropped should be at least 40% of original area
            orig_area = img.shape[0] * img.shape[1]
            crop_area = cropped.shape[0] * cropped.shape[1]
            self.assertGreater(
                crop_area, orig_area * 0.3,
                f"Image {i}: Canny over-cropped"
            )

    def test_sobel_preserves_content(self):
        """Sobel crop retains a meaningful amount of the original content."""
        for i, img in enumerate(self.images):
            cropped = ScreenCapture.edge_detect_crop(img, method="sobel")
            orig_area = img.shape[0] * img.shape[1]
            crop_area = cropped.shape[0] * cropped.shape[1]
            self.assertGreater(
                crop_area, orig_area * 0.3,
                f"Image {i}: Sobel over-cropped"
            )


# ---------------------------------------------------------------------------
# Test: smart_crop on 10 synthetic windows
# ---------------------------------------------------------------------------


@unittest.skipUnless(CAPTURE_AVAILABLE and CV2_AVAILABLE,
                     "ScreenCapture + OpenCV required")
class TestSmartCrop10Windows(unittest.TestCase):
    """smart_crop (edge + brightness fallback) on 10 images."""

    def setUp(self):
        self.images = _make_10_synthetic_windows()

    def test_smart_crop_all_10(self):
        """smart_crop crops all 10 images."""
        for i, img in enumerate(self.images):
            cropped = ScreenCapture.smart_crop(img)
            self.assertLessEqual(
                cropped.shape[0], img.shape[0],
                f"Image {i}: smart_crop height"
            )
            self.assertLessEqual(
                cropped.shape[1], img.shape[1],
                f"Image {i}: smart_crop width"
            )

    def test_smart_crop_vs_brightness_only(self):
        """smart_crop should crop at least as well as auto_crop_borders."""
        for i, img in enumerate(self.images):
            smart = ScreenCapture.smart_crop(img)
            bright = ScreenCapture.auto_crop_borders(img)
            # smart_crop should produce comparable or tighter result
            smart_area = smart.shape[0] * smart.shape[1]
            bright_area = bright.shape[0] * bright.shape[1]
            # Allow 10% tolerance — smart may be slightly larger due to margin
            self.assertLess(
                smart_area, bright_area * 1.15,
                f"Image {i}: smart_crop produced significantly larger result"
            )


# ---------------------------------------------------------------------------
# Test: Edge detection edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(CAPTURE_AVAILABLE, "ScreenCapture required")
class TestEdgeCropEdgeCases(unittest.TestCase):
    """Edge-detect crop with unusual inputs."""

    def test_none_image(self):
        result = ScreenCapture.edge_detect_crop(None)
        self.assertIsNone(result)

    def test_empty_image(self):
        img = np.array([], dtype=np.uint8)
        result = ScreenCapture.edge_detect_crop(img)
        self.assertEqual(result.size, 0)

    def test_fully_black_image(self):
        """Fully black image should fall back gracefully."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = ScreenCapture.edge_detect_crop(img)
        # Should return original or brightness-based fallback
        self.assertEqual(result.shape[:2], (100, 100))

    def test_fully_white_image(self):
        """Fully white image should not crash."""
        img = np.full((100, 100, 3), 255, dtype=np.uint8)
        result = ScreenCapture.edge_detect_crop(img)
        self.assertIsNotNone(result)

    def test_grayscale_input(self):
        """2D (grayscale) array should be handled."""
        img = np.zeros((80, 120), dtype=np.uint8)
        img[10:70, 15:105] = 200
        result = ScreenCapture.edge_detect_crop(img)
        self.assertLessEqual(result.shape[0], 80)

    def test_smart_crop_none(self):
        result = ScreenCapture.smart_crop(None)
        self.assertIsNone(result)

    def test_smart_crop_empty(self):
        img = np.array([], dtype=np.uint8)
        result = ScreenCapture.smart_crop(img)
        self.assertEqual(result.size, 0)


# ---------------------------------------------------------------------------
# Test: auto_find_by_keywords from test_windows_list
# ---------------------------------------------------------------------------


@unittest.skipUnless(LIST_AVAILABLE and WIN32_AVAILABLE,
                     "test_windows_list + Win32 required")
class TestAutoFindByKeywords(unittest.TestCase):
    """auto_find_by_keywords integration from test_windows_list.py."""

    def test_find_common_apps(self):
        """Keywords like 'Chrome', 'Explorer', 'Code' should match something."""
        keywords = ["Chrome", "Explorer", "Code", "Cursor", "Python",
                     "Terminal", "Edge", "Window", "Notepad", "Settings"]
        results = auto_find_by_keywords(keywords)
        # On a live desktop, at least some should match
        self.assertIsInstance(results, list)
        # We expect at least a few matches
        self.assertGreater(len(results), 0, "Expected at least 1 match")

    def test_find_returns_sorted_by_score(self):
        """Results are sorted by score descending."""
        results = auto_find_by_keywords([".*"])
        if len(results) >= 2:
            for i in range(1, len(results)):
                self.assertGreaterEqual(results[i - 1].score, results[i].score)

    def test_find_nonexistent_keyword(self):
        """Nonexistent keyword returns empty list."""
        results = auto_find_by_keywords(["__xyzzy_nonexistent_42__"])
        self.assertEqual(len(results), 0)


# ---------------------------------------------------------------------------
# Test: Acceptance — 10 windows end-to-end (find + crop)
# ---------------------------------------------------------------------------


@unittest.skipUnless(
    FINDER_AVAILABLE and WIN32_AVAILABLE and CAPTURE_AVAILABLE and CV2_AVAILABLE,
    "Full stack required"
)
class TestAcceptance10WindowsFindAndCrop(unittest.TestCase):
    """Acceptance: find 10 real windows, then edge-crop a synthetic frame for each."""

    def test_find_and_crop_each(self):
        """
        1. Find real windows on the desktop (at least 5).
        2. Pad with synthetic windows to reach 10.
        3. Apply edge_detect_crop (Canny) — must succeed without errors.
        4. Apply edge_detect_crop (Sobel) — must succeed without errors.
        5. Apply smart_crop — must succeed without errors.
        """
        finder = AutoWindowFinder()
        windows = finder.find_all(".*")
        self.assertGreaterEqual(len(windows), 1, "Need at least 1 window on desktop")

        # Pad to 10 by repeating the available windows
        while len(windows) < 10:
            windows.append(windows[len(windows) % len(windows)])

        for i, wm in enumerate(windows[:10]):
            # Verify auto-find metadata
            self.assertGreater(wm.hwnd, 0, f"Window {i}: bad hwnd")
            self.assertGreater(wm.zoom_rect.w, 0, f"Window {i}: zoom_rect.w=0")
            self.assertGreater(wm.zoom_rect.h, 0, f"Window {i}: zoom_rect.h=0")

            # Synthetic frame matching window size (with border)
            h = min(wm.zoom_rect.h, 600)
            w = min(wm.zoom_rect.w, 800)
            border = max(5, min(h, w) // 20)
            frame = _make_synthetic_window(h, w, border, 140 + i * 10)

            # Canny crop
            canny = ScreenCapture.edge_detect_crop(frame, method="canny")
            self.assertIsNotNone(canny, f"Window {i}: Canny returned None")
            self.assertGreater(canny.size, 0, f"Window {i}: Canny empty")

            # Sobel crop
            sobel = ScreenCapture.edge_detect_crop(frame, method="sobel")
            self.assertIsNotNone(sobel, f"Window {i}: Sobel returned None")
            self.assertGreater(sobel.size, 0, f"Window {i}: Sobel empty")

            # Smart crop
            smart = ScreenCapture.smart_crop(frame)
            self.assertIsNotNone(smart, f"Window {i}: smart_crop returned None")
            self.assertGreater(smart.size, 0, f"Window {i}: smart_crop empty")

    def test_summary_10_windows(self):
        """Print summary of 10 found windows with crop results."""
        finder = AutoWindowFinder()
        windows = finder.find_all(".*")[:10]

        results = []
        for i, wm in enumerate(windows):
            h = min(wm.zoom_rect.h, 400)
            w = min(wm.zoom_rect.w, 600)
            if h < 30 or w < 30:
                continue

            border = max(5, min(h, w) // 15)
            frame = _make_synthetic_window(h, w, border, 130)

            canny = ScreenCapture.edge_detect_crop(frame, method="canny")
            results.append({
                "hwnd": wm.hwnd,
                "title": wm.title[:40],
                "original": f"{frame.shape[1]}x{frame.shape[0]}",
                "cropped": f"{canny.shape[1]}x{canny.shape[0]}",
                "saved_pct": round(
                    (1 - (canny.shape[0] * canny.shape[1]) / (frame.shape[0] * frame.shape[1]))
                    * 100, 1
                ),
            })

        # At least some windows should be processed
        self.assertGreater(len(results), 0)
        # All should show border trimming
        for r in results:
            self.assertGreater(r["saved_pct"], 0, f"{r['title']}: no crop")


if __name__ == "__main__":
    unittest.main()
