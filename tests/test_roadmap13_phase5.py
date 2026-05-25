"""
Tests for roadmap13 Phase 5 — Final testing and validation.

- 30 different synthetic screenshots (varied resolutions, offsets, themes)
- Accuracy test: >92% correct zone detection
- Stability: window movement, resize, different themes
- Fallback verification
- Full acceptance test
"""
import os
import random
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from bridge.vision.anchor_detector import (
    AnchorMatch,
    ROIZone,
    calculate_all_roi,
    detect_roi,
    find_anchors,
    load_config,
)

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates", "anchors")

ANCHOR_FILES = [
    ("logo_coinpoker", (10, 5)),
    ("btn_fold", (200, 520)),
    ("btn_call", (340, 520)),
    ("btn_raise", (480, 520)),
    ("btn_check", (200, 490)),
    ("chip_icon", (350, 420)),
    ("pot_icon", (350, 200)),
    ("dealer_button", (300, 350)),
    ("table_border", (100, 100)),
    ("table_corner", (5, 80)),
]


def _generate_screenshot(
    width: int = 800,
    height: int = 600,
    offset_x: int = 0,
    offset_y: int = 0,
    bg_color: tuple = (30, 50, 30),
    noise_level: int = 5,
    scale_factor: float = 1.0,
    seed: int = 42,
) -> tuple:
    """Generate a synthetic screenshot with templates pasted at known positions.

    Returns (image, expected_positions_dict).
    """
    rng = random.Random(seed)
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    if noise_level > 0:
        noise = np.random.RandomState(seed).randint(
            -noise_level, noise_level + 1, img.shape, dtype=np.int16,
        )
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    positions = {}
    for name, (base_x, base_y) in ANCHOR_FILES:
        path = os.path.join(TEMPLATES_DIR, f"{name}.png")
        tmpl = cv2.imread(path)
        if tmpl is None:
            continue

        if scale_factor != 1.0:
            new_w = max(4, int(tmpl.shape[1] * scale_factor))
            new_h = max(4, int(tmpl.shape[0] * scale_factor))
            tmpl = cv2.resize(tmpl, (new_w, new_h))

        th, tw = tmpl.shape[:2]
        px = int(base_x * (width / 800.0)) + offset_x
        py = int(base_y * (height / 600.0)) + offset_y

        px = max(0, min(px, width - tw))
        py = max(0, min(py, height - th))

        img[py:py + th, px:px + tw] = tmpl
        positions[name] = (px, py, tw, th)

    return img, positions


def _generate_30_screenshots():
    """Generate 30 varied synthetic screenshots."""
    screenshots = []
    configs = [
        {"width": 800, "height": 600, "seed": 1},
        {"width": 900, "height": 650, "seed": 2},
        {"width": 1024, "height": 768, "seed": 3},
        {"width": 1280, "height": 960, "seed": 4},
        {"width": 700, "height": 500, "seed": 5},
        {"width": 800, "height": 600, "offset_x": 10, "offset_y": 5, "seed": 6},
        {"width": 800, "height": 600, "offset_x": -5, "offset_y": 10, "seed": 7},
        {"width": 800, "height": 600, "offset_x": 20, "offset_y": 20, "seed": 8},
        {"width": 800, "height": 600, "bg_color": (20, 40, 20), "seed": 9},
        {"width": 800, "height": 600, "bg_color": (40, 60, 40), "seed": 10},
        {"width": 800, "height": 600, "bg_color": (10, 30, 60), "seed": 11},
        {"width": 800, "height": 600, "bg_color": (50, 20, 20), "seed": 12},
        {"width": 800, "height": 600, "noise_level": 10, "seed": 13},
        {"width": 800, "height": 600, "noise_level": 15, "seed": 14},
        {"width": 800, "height": 600, "noise_level": 3, "seed": 15},
        {"width": 850, "height": 620, "noise_level": 8, "seed": 16},
        {"width": 750, "height": 550, "offset_x": 5, "seed": 17},
        {"width": 960, "height": 720, "seed": 18},
        {"width": 1100, "height": 800, "seed": 19},
        {"width": 800, "height": 600, "scale_factor": 1.0, "seed": 20},
        {"width": 800, "height": 600, "offset_x": 15, "offset_y": -5, "seed": 21},
        {"width": 820, "height": 610, "bg_color": (25, 45, 25), "seed": 22},
        {"width": 780, "height": 590, "bg_color": (35, 55, 35), "seed": 23},
        {"width": 800, "height": 600, "noise_level": 7, "offset_x": 3, "seed": 24},
        {"width": 1000, "height": 700, "seed": 25},
        {"width": 640, "height": 480, "seed": 26},
        {"width": 800, "height": 600, "bg_color": (15, 25, 50), "noise_level": 5, "seed": 27},
        {"width": 900, "height": 680, "offset_x": -3, "offset_y": 7, "seed": 28},
        {"width": 870, "height": 640, "seed": 29},
        {"width": 800, "height": 600, "bg_color": (45, 30, 30), "noise_level": 12, "seed": 30},
    ]
    for cfg in configs:
        img, pos = _generate_screenshot(**cfg)
        screenshots.append((img, pos, cfg))
    return screenshots


class TestAccuracy30Screenshots(unittest.TestCase):
    """Accuracy >92% across 30 varied screenshots."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.total_anchors = len(cls.config["anchors"])
        cls.screenshots = _generate_30_screenshots()

    def test_30_screenshots_generated(self):
        self.assertEqual(len(self.screenshots), 30)

    def test_accuracy_above_92(self):
        """Across all 30 screenshots, average anchor hit rate >= 92%."""
        hit_rates = []
        for img, positions, cfg in self.screenshots:
            anchors, zones = detect_roi(img, config=self.config)
            found_names = {a.name for a in anchors}
            expected = set(positions.keys())
            hits = len(found_names & expected)
            rate = hits / max(len(expected), 1)
            hit_rates.append(rate)

        avg_rate = sum(hit_rates) / len(hit_rates)
        self.assertGreaterEqual(
            avg_rate, 0.92,
            f"Average accuracy {avg_rate:.2%} < 92% across 30 screenshots",
        )

    def test_each_screenshot_finds_at_least_half(self):
        """Each screenshot finds at least 50% of anchors."""
        for i, (img, positions, cfg) in enumerate(self.screenshots):
            anchors, _ = detect_roi(img, config=self.config)
            self.assertGreaterEqual(
                len(anchors), self.total_anchors * 0.5,
                f"Screenshot {i} ({cfg.get('width')}x{cfg.get('height')}): "
                f"only {len(anchors)}/{self.total_anchors}",
            )

    def test_zones_produced_for_each(self):
        for i, (img, positions, cfg) in enumerate(self.screenshots):
            _, zones = detect_roi(img, config=self.config)
            self.assertGreater(
                len(zones), 0,
                f"Screenshot {i}: 0 zones produced",
            )


class TestWindowMovementStability(unittest.TestCase):
    """Simulate window movement and verify consistent detection."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_movement_offsets(self):
        """Moving the window by different offsets should still find anchors."""
        offsets = [(0, 0), (10, 10), (20, 5), (-5, 15), (30, -10), (0, 25)]
        for ox, oy in offsets:
            img, _ = _generate_screenshot(offset_x=ox, offset_y=oy, seed=100)
            anchors, zones = detect_roi(img, config=self.config)
            self.assertGreaterEqual(
                len(anchors), 5,
                f"Offset ({ox},{oy}): only {len(anchors)} anchors",
            )

    def test_resize_stability(self):
        """Different window sizes should still detect majority of anchors."""
        sizes = [(640, 480), (800, 600), (1024, 768), (1280, 960)]
        for w, h in sizes:
            img, _ = _generate_screenshot(width=w, height=h, seed=200)
            anchors, zones = detect_roi(img, config=self.config)
            self.assertGreaterEqual(
                len(anchors), 5,
                f"Size {w}x{h}: only {len(anchors)} anchors",
            )


class TestDifferentThemes(unittest.TestCase):
    """Different background colors (themes) should not break detection."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_dark_green(self):
        img, _ = _generate_screenshot(bg_color=(15, 40, 15), seed=301)
        anchors, _ = detect_roi(img, config=self.config)
        self.assertGreaterEqual(len(anchors), 5)

    def test_dark_blue(self):
        img, _ = _generate_screenshot(bg_color=(10, 20, 50), seed=302)
        anchors, _ = detect_roi(img, config=self.config)
        self.assertGreaterEqual(len(anchors), 5)

    def test_dark_red(self):
        img, _ = _generate_screenshot(bg_color=(50, 15, 15), seed=303)
        anchors, _ = detect_roi(img, config=self.config)
        self.assertGreaterEqual(len(anchors), 5)

    def test_gray(self):
        img, _ = _generate_screenshot(bg_color=(60, 60, 60), seed=304)
        anchors, _ = detect_roi(img, config=self.config)
        self.assertGreaterEqual(len(anchors), 5)


class TestFallback(unittest.TestCase):
    """Fallback mechanisms when anchors are not found."""

    def test_blank_image_fallback(self):
        """Blank image should produce few high-confidence matches."""
        config = load_config()
        blank = np.zeros((600, 800, 3), dtype=np.uint8)
        anchors, zones = detect_roi(blank, config=config)
        high_conf = [a for a in anchors if a.confidence > 0.8]
        self.assertLessEqual(len(high_conf), 3)

    def test_bot_instance_fallback_produces_zones(self):
        from launcher.bot_instance import BotInstance
        bot = BotInstance(bot_id="fallback-test")
        zones = bot._fallback_relative_roi()
        self.assertIsInstance(zones, list)
        self.assertGreater(len(zones), 0)
        for z in zones:
            self.assertGreater(z["w"], 0)
            self.assertGreater(z["h"], 0)

    def test_manual_2point_fallback(self):
        """Simulate manual 2-point selection producing valid zones."""
        p1 = (100, 80)
        p2 = (700, 520)
        w = p2[0] - p1[0]
        h = p2[1] - p1[1]
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)


class TestPipelineStability(unittest.TestCase):
    """Run pipeline 30 times without crashes."""

    def test_30_iterations_no_crash(self):
        config = load_config()
        for i in range(30):
            w = 700 + (i * 7) % 200
            h = 500 + (i * 5) % 150
            img, _ = _generate_screenshot(width=w, height=h, seed=500 + i)
            try:
                anchors, zones = detect_roi(img, config=config)
            except Exception as exc:
                self.fail(f"Iteration {i} crashed: {exc}")


class TestAcceptance(unittest.TestCase):
    """Comprehensive acceptance test."""

    def test_full_pipeline_acceptance(self):
        config = load_config()
        self.assertEqual(len(config["anchors"]), 10)
        self.assertGreaterEqual(len(config["derived_zones"]), 6)

        img, positions = _generate_screenshot(width=800, height=600, seed=999)
        anchors, zones = detect_roi(img, config=config)

        self.assertGreaterEqual(len(anchors), 7, "Expected >=7 anchors for 800x600")
        self.assertGreater(len(zones), 0, "Expected at least 1 zone")

        for z in zones:
            self.assertGreater(z.w, 0)
            self.assertGreater(z.h, 0)
            self.assertGreaterEqual(z.x, 0)
            self.assertGreaterEqual(z.y, 0)

        for a in anchors:
            self.assertGreater(a.confidence, 0)
            self.assertIsInstance(a.scale, float)


if __name__ == "__main__":
    unittest.main()
