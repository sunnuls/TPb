"""
Tests for roadmap11_auto_roi_detection.md Phase 3 — anchor_detector.py.

Validates:
  - load_config() reads YAML correctly
  - find_anchors() with cv2.matchTemplate
  - AnchorMatch / ROIZone dataclasses
  - calculate_relative_roi() computes zones from anchors
  - detect_roi() full pipeline
  - Accuracy: on 10 synthetic screenshots → anchors found >90%
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import List

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from bridge.vision.anchor_detector import (
        AnchorMatch,
        ROIZone,
        find_anchors,
        calculate_relative_roi,
        detect_roi,
        load_config,
    )
    HAS_DETECTOR = True
except Exception:
    HAS_DETECTOR = False

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_screenshot(
    width: int = 800,
    height: int = 600,
    embed_anchors: bool = True,
) -> np.ndarray:
    """Create a synthetic screenshot with anchor templates embedded.

    Places each anchor template at a position matching its 'relative'
    config coordinates.
    """
    img = np.full((height, width, 3), 40, dtype=np.uint8)  # dark background

    if not embed_anchors or not HAS_CV2:
        return img

    try:
        cfg = load_config()
    except Exception:
        return img

    for name, anchor_cfg in cfg.get("anchors", {}).items():
        template_path = ROOT / anchor_cfg["file"]
        if not template_path.exists():
            continue

        tmpl = cv2.imread(str(template_path))
        if tmpl is None:
            continue

        th, tw = tmpl.shape[:2]
        rel = anchor_cfg.get("relative", {})

        # Place at center of the relative zone
        cx = int((rel.get("x_min", 0) + rel.get("x_max", 0)) / 2 * width)
        cy = int((rel.get("y_min", 0) + rel.get("y_max", 0)) / 2 * height)

        x = max(0, min(cx - tw // 2, width - tw))
        y = max(0, min(cy - th // 2, height - th))

        img[y:y + th, x:x + tw] = tmpl

    return img


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR, "anchor_detector not importable")
class TestLoadConfig(unittest.TestCase):
    def test_loads_successfully(self):
        cfg = load_config()
        self.assertIn("anchors", cfg)
        self.assertIn("derived_zones", cfg)
        self.assertEqual(len(cfg["anchors"]), 6)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_config(Path("nonexistent.yaml"))


# ---------------------------------------------------------------------------
# AnchorMatch dataclass
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR, "anchor_detector not importable")
class TestAnchorMatch(unittest.TestCase):
    def test_center(self):
        m = AnchorMatch(name="test", x=100, y=200, w=60, h=30)
        self.assertEqual(m.cx, 130)
        self.assertEqual(m.cy, 215)

    def test_bbox(self):
        m = AnchorMatch(name="test", x=10, y=20, w=50, h=40)
        self.assertEqual(m.bbox, (10, 20, 60, 60))


# ---------------------------------------------------------------------------
# ROIZone dataclass
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR, "anchor_detector not importable")
class TestROIZone(unittest.TestCase):
    def test_bbox(self):
        z = ROIZone(name="board", x=100, y=200, w=300, h=80)
        self.assertEqual(z.bbox, (100, 200, 400, 280))

    def test_to_dict(self):
        z = ROIZone(name="pot", x=50, y=60, w=100, h=30, source="btn_call", confidence=0.85)
        d = z.to_dict()
        self.assertEqual(d["name"], "pot")
        self.assertEqual(d["confidence"], 0.85)


# ---------------------------------------------------------------------------
# find_anchors — synthetic images
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "cv2 or anchor_detector not available")
class TestFindAnchors(unittest.TestCase):
    """find_anchors with synthetic screenshot containing embedded templates."""

    def test_finds_all_anchors(self):
        img = _make_synthetic_screenshot(800, 600, embed_anchors=True)
        matches = find_anchors(img)
        names = [m.name for m in matches]
        # Should find most anchors (embedded at expected positions)
        self.assertGreaterEqual(len(matches), 4, f"Only found: {names}")

    def test_confidence_above_threshold(self):
        img = _make_synthetic_screenshot(800, 600, embed_anchors=True)
        matches = find_anchors(img)
        for m in matches:
            self.assertGreater(m.confidence, 0.0)

    def test_no_matches_on_blank(self):
        """Blank white image should find few/no anchors."""
        img = np.full((600, 800, 3), 255, dtype=np.uint8)
        matches = find_anchors(img)
        # Most anchors are dark templates on white → should NOT match well
        high_conf = [m for m in matches if m.confidence > 0.9]
        # Allow some false positives but not all 6
        self.assertLess(len(high_conf), 6)

    def test_anchor_position_reasonable(self):
        img = _make_synthetic_screenshot(800, 600, embed_anchors=True)
        matches = find_anchors(img)
        for m in matches:
            self.assertGreaterEqual(m.x, 0)
            self.assertGreaterEqual(m.y, 0)
            self.assertLess(m.x, 800)
            self.assertLess(m.y, 600)

    def test_anchor_has_zone(self):
        img = _make_synthetic_screenshot(800, 600, embed_anchors=True)
        matches = find_anchors(img)
        for m in matches:
            self.assertTrue(len(m.zone) > 0, f"{m.name} has no zone")


# ---------------------------------------------------------------------------
# calculate_relative_roi
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR, "anchor_detector not importable")
class TestCalculateRelativeROI(unittest.TestCase):
    def test_basic_roi_from_offsets(self):
        anchor = AnchorMatch(
            name="btn_fold", x=200, y=500, w=60, h=30,
            confidence=0.9, zone="action_buttons",
            roi_offsets={"hero_cards": {"dx": -150, "dy": -80, "w": 120, "h": 80}},
        )
        zones = calculate_relative_roi([anchor], image_shape=(600, 800))
        self.assertGreaterEqual(len(zones), 1)
        hero = [z for z in zones if z.name == "hero_cards"]
        self.assertEqual(len(hero), 1)
        self.assertEqual(hero[0].source, "btn_fold")

    def test_clamped_to_image(self):
        anchor = AnchorMatch(
            name="test", x=0, y=0, w=10, h=10,
            confidence=0.8,
            roi_offsets={"off": {"dx": -100, "dy": -100, "w": 50, "h": 50}},
        )
        zones = calculate_relative_roi([anchor], image_shape=(100, 100))
        z = zones[0]
        self.assertGreaterEqual(z.x, 0)
        self.assertGreaterEqual(z.y, 0)

    def test_bounding_box_derived(self):
        cfg = {
            "derived_zones": {
                "buttons": {
                    "anchors": ["a", "b"],
                    "method": "bounding_box",
                    "description": "test",
                },
            },
        }
        anchors = [
            AnchorMatch(name="a", x=100, y=400, w=60, h=30, confidence=0.8),
            AnchorMatch(name="b", x=300, y=400, w=60, h=30, confidence=0.9),
        ]
        zones = calculate_relative_roi(anchors, config=cfg)
        bb = [z for z in zones if z.name == "buttons"]
        self.assertEqual(len(bb), 1)
        self.assertEqual(bb[0].x, 100)
        self.assertEqual(bb[0].w, 260)  # 360 - 100

    def test_midpoint_derived(self):
        cfg = {
            "derived_zones": {
                "center": {
                    "primary_anchor": "top",
                    "secondary_anchor": "bottom",
                    "method": "midpoint_vertical",
                    "description": "test",
                },
            },
        }
        anchors = [
            AnchorMatch(name="top", x=350, y=50, w=100, h=40, confidence=0.85),
            AnchorMatch(name="bottom", x=250, y=500, w=60, h=30, confidence=0.80),
        ]
        zones = calculate_relative_roi(anchors, image_shape=(600, 800), config=cfg)
        mid = [z for z in zones if z.name == "center"]
        self.assertEqual(len(mid), 1)
        # Midpoint between y=70 and y=515 → ~292
        self.assertAlmostEqual(mid[0].y + mid[0].h // 2, 292, delta=50)

    def test_empty_anchors(self):
        zones = calculate_relative_roi([])
        self.assertEqual(len(zones), 0)


# ---------------------------------------------------------------------------
# detect_roi — full pipeline
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "cv2 or anchor_detector not available")
class TestDetectROI(unittest.TestCase):
    def test_pipeline_returns_tuple(self):
        img = _make_synthetic_screenshot(800, 600, embed_anchors=True)
        anchors, zones = detect_roi(img)
        self.assertIsInstance(anchors, list)
        self.assertIsInstance(zones, list)
        self.assertGreater(len(anchors), 0)
        self.assertGreater(len(zones), 0)


# ---------------------------------------------------------------------------
# Accuracy: 10 synthetic screenshots → >90% anchors found
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "cv2 or anchor_detector not available")
class TestAccuracy10Screenshots(unittest.TestCase):
    """On 10 synthetic screenshots, anchor detection accuracy >90%."""

    def test_accuracy_over_90_percent(self):
        total_anchors = 0
        found_anchors = 0

        cfg = load_config()
        expected_count = len(cfg.get("anchors", {}))

        for i in range(10):
            # Slightly vary size to test robustness
            w = 780 + i * 5  # 780..825
            h = 580 + i * 4  # 580..616

            img = _make_synthetic_screenshot(w, h, embed_anchors=True)
            matches = find_anchors(img, config=cfg)

            total_anchors += expected_count
            found_anchors += len(matches)

        accuracy = found_anchors / total_anchors if total_anchors > 0 else 0
        self.assertGreaterEqual(
            accuracy, 0.90,
            f"Accuracy {accuracy:.1%} < 90% "
            f"({found_anchors}/{total_anchors} anchors found across 10 images)",
        )


if __name__ == "__main__":
    unittest.main()
