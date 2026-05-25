"""
Tests for roadmap13 Phase 3 — multi-scale matchTemplate + calculate_all_roi.
"""
import os
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from bridge.vision.anchor_detector import (
    AnchorMatch,
    ROIZone,
    _match_template_multiscale,
    calculate_all_roi,
    calculate_relative_roi,
    detect_roi,
    find_anchors,
    load_config,
)

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates", "anchors")


def _build_synthetic_screenshot(width=800, height=600):
    """Build a synthetic screenshot with all 10 templates pasted at known positions."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (30, 50, 30)  # dark green table

    positions = {}
    anchor_files = [
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

    for name, (px, py) in anchor_files:
        path = os.path.join(TEMPLATES_DIR, f"{name}.png")
        tmpl = cv2.imread(path)
        if tmpl is None:
            continue
        th, tw = tmpl.shape[:2]
        # Clamp
        if py + th > height:
            py = height - th
        if px + tw > width:
            px = width - tw
        img[py:py + th, px:px + tw] = tmpl
        positions[name] = (px, py, tw, th)

    return img, positions


class TestMultiScaleHelper(unittest.TestCase):
    """Tests for _match_template_multiscale."""

    def test_single_scale(self):
        tmpl = np.random.randint(0, 255, (20, 30), dtype=np.uint8)
        img = np.zeros((100, 100), dtype=np.uint8)
        img[10:30, 20:50] = tmpl
        val, loc, mw, mh, sc = _match_template_multiscale(
            img, tmpl, [1.0], cv2.TM_CCOEFF_NORMED,
        )
        self.assertGreater(val, 0.9)
        self.assertAlmostEqual(sc, 1.0)

    def test_multi_scale_finds_better(self):
        tmpl = np.random.randint(50, 200, (20, 30), dtype=np.uint8)
        scaled = cv2.resize(tmpl, (45, 30))  # 1.5x
        img = np.zeros((200, 200), dtype=np.uint8)
        img[50:80, 60:105] = scaled
        val, loc, mw, mh, sc = _match_template_multiscale(
            img, tmpl, [0.8, 1.0, 1.2, 1.5], cv2.TM_CCOEFF_NORMED,
        )
        self.assertGreater(val, 0.7)

    def test_returns_five_tuple(self):
        tmpl = np.ones((10, 10), dtype=np.uint8) * 128
        img = np.ones((100, 100), dtype=np.uint8) * 128
        result = _match_template_multiscale(img, tmpl, [1.0], cv2.TM_CCOEFF_NORMED)
        self.assertEqual(len(result), 5)

    def test_skip_too_large_scale(self):
        tmpl = np.ones((50, 50), dtype=np.uint8)
        img = np.ones((60, 60), dtype=np.uint8)
        val, loc, mw, mh, sc = _match_template_multiscale(
            img, tmpl, [2.0, 3.0], cv2.TM_CCOEFF_NORMED,
        )
        self.assertEqual(val, -1.0)


class TestFindAnchorsMultiScale(unittest.TestCase):
    """Tests for find_anchors with multi-scale config."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.img, cls.positions = _build_synthetic_screenshot()

    def test_finds_anchors(self):
        matches = find_anchors(self.img, config=self.config)
        self.assertGreater(len(matches), 0)

    def test_each_match_has_scale(self):
        matches = find_anchors(self.img, config=self.config)
        for m in matches:
            self.assertIsInstance(m.scale, float)
            self.assertGreater(m.scale, 0)

    def test_config_scales_used(self):
        """Verify that config has scales for all anchors."""
        for name, acfg in self.config["anchors"].items():
            self.assertIn("scales", acfg, f"{name} missing scales in config")

    def test_finds_majority_of_anchors(self):
        matches = find_anchors(self.img, config=self.config)
        self.assertGreaterEqual(len(matches), 5, "Expected >=5 anchors found")

    def test_confidence_above_zero(self):
        matches = find_anchors(self.img, config=self.config)
        for m in matches:
            self.assertGreater(m.confidence, 0)

    def test_blank_image_few_matches(self):
        blank = np.zeros((600, 800, 3), dtype=np.uint8)
        matches = find_anchors(blank, config=self.config)
        high_conf = [m for m in matches if m.confidence > 0.8]
        self.assertLessEqual(len(high_conf), 3)


class TestCalculateAllROI(unittest.TestCase):
    """Tests for calculate_all_roi."""

    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.img, cls.positions = _build_synthetic_screenshot()
        cls.anchors = find_anchors(cls.img, config=cls.config)

    def test_produces_zones(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        self.assertGreater(len(zones), 0)

    def test_zones_have_positive_dims(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        for z in zones:
            self.assertGreater(z.w, 0, f"{z.name} has w=0")
            self.assertGreater(z.h, 0, f"{z.name} has h=0")

    def test_zones_clamped_to_image(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        for z in zones:
            self.assertGreaterEqual(z.x, 0, f"{z.name} x<0")
            self.assertGreaterEqual(z.y, 0, f"{z.name} y<0")
            self.assertLessEqual(z.x + z.w, 800, f"{z.name} exceeds width")
            self.assertLessEqual(z.y + z.h, 600, f"{z.name} exceeds height")

    def test_derived_zone_bounding_box(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        names = [z.name for z in zones]
        btn_names = {"btn_fold", "btn_call", "btn_check", "btn_raise"}
        found_btns = btn_names.intersection(n for a in self.anchors for n in [a.name])
        if len(found_btns) >= 2:
            self.assertIn("action_buttons", names)

    def test_derived_zone_midpoint(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        names = [z.name for z in zones]
        anchor_names = {a.name for a in self.anchors}
        if "logo_coinpoker" in anchor_names and "btn_fold" in anchor_names:
            self.assertIn("board", names)

    def test_backward_compat_alias(self):
        self.assertIs(calculate_relative_roi, calculate_all_roi)

    def test_to_dict(self):
        zones = calculate_all_roi(self.anchors, (600, 800), self.config)
        if zones:
            d = zones[0].to_dict()
            for key in ("name", "x", "y", "w", "h", "source", "confidence"):
                self.assertIn(key, d)


class TestDetectROIPipeline(unittest.TestCase):
    """Tests for detect_roi full pipeline."""

    def test_returns_tuple(self):
        img, _ = _build_synthetic_screenshot()
        result = detect_roi(img)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_anchors_and_zones(self):
        img, _ = _build_synthetic_screenshot()
        anchors, zones = detect_roi(img)
        self.assertIsInstance(anchors, list)
        self.assertIsInstance(zones, list)
        self.assertGreater(len(anchors), 0)
        self.assertGreater(len(zones), 0)

    def test_accuracy_10_screenshots(self):
        """Run on 10 varied screenshots, expect >=50% anchors each."""
        config = load_config()
        total_anchors = len(config["anchors"])
        for i in range(10):
            w = 700 + i * 20
            h = 500 + i * 15
            img, _ = _build_synthetic_screenshot(w, h)
            anchors, zones = detect_roi(img, config=config)
            self.assertGreaterEqual(
                len(anchors), total_anchors * 0.5,
                f"Screenshot {i}: only {len(anchors)}/{total_anchors} anchors",
            )


if __name__ == "__main__":
    unittest.main()
