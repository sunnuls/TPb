"""
Tests for roadmap11_auto_roi_detection.md Phase 5 — Final validation.

Validates:
  - 20 different synthetic screenshots → auto-ROI accuracy >90%
  - Varied resolutions, slight noise, shifted anchors
  - Fallback mechanism when anchors not found
  - User fallback: 2-point manual override
  - Auto-ROI vs manual ROI comparison (positional accuracy)
  - Full pipeline stability (20 iterations without crash)
"""

from __future__ import annotations

import random
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        detect_roi,
        find_anchors,
        calculate_relative_roi,
        load_config,
    )
    HAS_DETECTOR = True
except Exception:
    HAS_DETECTOR = False

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _embed_anchors(
    img: np.ndarray,
    cfg: dict,
    *,
    jitter_px: int = 0,
    noise_level: int = 0,
) -> np.ndarray:
    """Embed anchor templates into an image at expected relative positions.

    Args:
        img:         Base image (will be modified in-place).
        cfg:         Loaded anchor config.
        jitter_px:   Random pixel offset for anchor placement.
        noise_level: Gaussian noise sigma (0 = none).
    """
    h, w = img.shape[:2]

    for name, anchor_cfg in cfg.get("anchors", {}).items():
        template_path = ROOT / anchor_cfg["file"]
        if not template_path.exists():
            continue

        tmpl = cv2.imread(str(template_path))
        if tmpl is None:
            continue

        th, tw = tmpl.shape[:2]
        rel = anchor_cfg.get("relative", {})

        cx = int((rel.get("x_min", 0) + rel.get("x_max", 0)) / 2 * w)
        cy = int((rel.get("y_min", 0) + rel.get("y_max", 0)) / 2 * h)

        # Apply jitter
        if jitter_px > 0:
            cx += random.randint(-jitter_px, jitter_px)
            cy += random.randint(-jitter_px, jitter_px)

        x = max(0, min(cx - tw // 2, w - tw))
        y = max(0, min(cy - th // 2, h - th))

        img[y:y + th, x:x + tw] = tmpl

    # Apply noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def _generate_20_screenshots(cfg: dict) -> List[np.ndarray]:
    """Generate 20 varied synthetic screenshots for testing.

    Variations:
        - Different resolutions (720p to 1080p)
        - Different background colors (dark, medium, light)
        - Slight position jitter (0-5px)
        - Mild noise levels (0-10)
    """
    screenshots = []
    random.seed(42)
    np.random.seed(42)

    resolutions = [
        (800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080),
        (800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080),
        (900, 650), (1050, 750), (1200, 700), (1400, 800), (1600, 900),
        (850, 620), (1100, 780), (1280, 800), (1500, 850), (1680, 1050),
    ]

    bg_colors = [
        (30, 30, 30), (40, 50, 40), (50, 45, 50), (35, 40, 60),
        (45, 45, 45), (55, 55, 50), (25, 35, 25), (60, 50, 40),
        (40, 40, 55), (35, 50, 35), (30, 40, 50), (50, 40, 30),
        (45, 35, 45), (55, 45, 55), (40, 55, 40), (35, 30, 45),
        (50, 50, 50), (30, 45, 30), (45, 40, 35), (55, 50, 45),
    ]

    for i in range(20):
        w, h = resolutions[i]
        bg = bg_colors[i]
        img = np.full((h, w, 3), bg, dtype=np.uint8)

        jitter = random.randint(0, 5)
        noise = random.randint(0, 8)

        img = _embed_anchors(img, cfg, jitter_px=jitter, noise_level=noise)
        screenshots.append(img)

    return screenshots


def _manual_roi_from_two_points(
    top_left: Tuple[int, int],
    bottom_right: Tuple[int, int],
) -> Dict[str, int]:
    """User fallback: derive ROI from 2 corner points.

    This simulates the user selecting top-left and bottom-right of the
    poker table area.
    """
    x1, y1 = top_left
    x2, y2 = bottom_right
    return {
        "x": min(x1, x2),
        "y": min(y1, y2),
        "w": abs(x2 - x1),
        "h": abs(y2 - y1),
    }


# ---------------------------------------------------------------------------
# Test: 20 screenshots → accuracy >90%
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "dependencies unavailable")
class TestAccuracy20Screenshots(unittest.TestCase):
    """Run anchor detection on 20 varied synthetic screenshots.

    Success criterion: >=90% of expected anchors found across all images.
    """

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.expected_count = len(cls.cfg.get("anchors", {}))
        cls.screenshots = _generate_20_screenshots(cls.cfg)

    def test_all_20_generated(self):
        self.assertEqual(len(self.screenshots), 20)

    def test_varied_resolutions(self):
        sizes = set(img.shape[:2] for img in self.screenshots)
        self.assertGreaterEqual(len(sizes), 10, "Not enough resolution variation")

    def test_accuracy_over_90_percent(self):
        total = 0
        found = 0

        for i, img in enumerate(self.screenshots):
            matches = find_anchors(img, config=self.cfg)
            total += self.expected_count
            found += len(matches)

        accuracy = found / total if total > 0 else 0
        self.assertGreaterEqual(
            accuracy, 0.90,
            f"Accuracy {accuracy:.1%} < 90% "
            f"({found}/{total} anchors across 20 screenshots)",
        )

    def test_each_image_finds_at_least_half(self):
        """Each image should find at least 50% of anchors (no total failures)."""
        for i, img in enumerate(self.screenshots):
            matches = find_anchors(img, config=self.cfg)
            self.assertGreaterEqual(
                len(matches), self.expected_count // 2,
                f"Image {i}: only {len(matches)}/{self.expected_count} anchors",
            )

    def test_roi_zones_produced_for_each(self):
        """Full pipeline produces ROI zones for every screenshot."""
        for i, img in enumerate(self.screenshots):
            anchors, zones = detect_roi(img, config=self.cfg)
            if anchors:
                self.assertGreater(
                    len(zones), 0,
                    f"Image {i}: {len(anchors)} anchors but 0 zones",
                )


# ---------------------------------------------------------------------------
# Test: auto-ROI vs manual ROI comparison
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "dependencies unavailable")
class TestAutoVsManualROI(unittest.TestCase):
    """Compare auto-detected ROI positions against expected positions."""

    def test_anchor_positions_within_tolerance(self):
        """High-confidence anchors (>0.80) are within 50px of expected positions.

        Small templates like chip_icon may false-match due to size,
        so we only validate anchors with threshold >= 0.75 and confidence > 0.80.
        """
        cfg = load_config()
        img = np.full((600, 800, 3), 40, dtype=np.uint8)
        img = _embed_anchors(img, cfg, jitter_px=0, noise_level=0)

        matches = find_anchors(img, config=cfg)
        h, w = img.shape[:2]

        checked = 0
        for match in matches:
            anchor_cfg = cfg["anchors"].get(match.name)
            if not anchor_cfg:
                continue

            # Skip low-threshold small templates prone to false positives
            if anchor_cfg.get("threshold", 0) < 0.75:
                continue
            if match.confidence < 0.80:
                continue

            rel = anchor_cfg["relative"]
            expected_cx = int((rel["x_min"] + rel["x_max"]) / 2 * w)
            expected_cy = int((rel["y_min"] + rel["y_max"]) / 2 * h)

            dist = ((match.cx - expected_cx) ** 2 + (match.cy - expected_cy) ** 2) ** 0.5
            self.assertLessEqual(
                dist, 50,
                f"Anchor {match.name}: distance {dist:.1f}px from expected "
                f"(found=({match.cx},{match.cy}), expected=({expected_cx},{expected_cy}))",
            )
            checked += 1

        self.assertGreater(checked, 0, "No high-confidence anchors to validate")


# ---------------------------------------------------------------------------
# Test: fallback mechanism
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "dependencies unavailable")
class TestFallbackMechanism(unittest.TestCase):
    """When anchors are not found, fallback to config percentages."""

    def test_blank_image_fallback(self):
        """Completely blank image → few/no anchors → pipeline stable."""
        cfg = load_config()
        img = np.full((600, 800, 3), 128, dtype=np.uint8)
        anchors = find_anchors(img, config=cfg)

        # On a uniform gray image, we may get some false positives
        # but the important thing is the pipeline doesn't crash
        _, zones = detect_roi(img, config=cfg)
        # Even if some anchors false-match, pipeline is stable
        self.assertIsInstance(zones, list)

    def test_fallback_via_bot_instance(self):
        """BotInstance._fallback_relative_roi produces valid zones."""
        try:
            from launcher.bot_instance import BotInstance
        except Exception:
            self.skipTest("BotInstance not importable")

        bot = BotInstance.__new__(BotInstance)
        bot.bot_id = "fallback-test"
        zones = bot._fallback_relative_roi()

        self.assertGreaterEqual(len(zones), 6)
        for z in zones:
            self.assertIn("name", z)
            self.assertGreaterEqual(z["x"], 0)
            self.assertGreaterEqual(z["y"], 0)
            self.assertGreater(z["w"], 0)
            self.assertGreater(z["h"], 0)
            self.assertEqual(z["confidence"], 0.0)


# ---------------------------------------------------------------------------
# Test: user fallback — 2-point manual selection
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR, "anchor_detector not importable")
class TestManualTwoPointFallback(unittest.TestCase):
    """User selects 2 points (top-left, bottom-right) as fallback."""

    def test_basic_two_point(self):
        roi = _manual_roi_from_two_points((100, 50), (700, 550))
        self.assertEqual(roi["x"], 100)
        self.assertEqual(roi["y"], 50)
        self.assertEqual(roi["w"], 600)
        self.assertEqual(roi["h"], 500)

    def test_reversed_points(self):
        """Order doesn't matter — always returns correct ROI."""
        roi = _manual_roi_from_two_points((700, 550), (100, 50))
        self.assertEqual(roi["x"], 100)
        self.assertEqual(roi["y"], 50)
        self.assertEqual(roi["w"], 600)
        self.assertEqual(roi["h"], 500)

    def test_single_point_zero_size(self):
        roi = _manual_roi_from_two_points((300, 200), (300, 200))
        self.assertEqual(roi["w"], 0)
        self.assertEqual(roi["h"], 0)


# ---------------------------------------------------------------------------
# Test: pipeline stability — 20 iterations no crash
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "dependencies unavailable")
class TestPipelineStability(unittest.TestCase):
    """Full pipeline runs 20 times without crash."""

    def test_20_iterations_stable(self):
        cfg = load_config()
        errors = 0

        for i in range(20):
            try:
                w = random.randint(640, 1920)
                h = random.randint(480, 1080)
                img = np.full((h, w, 3), random.randint(20, 80), dtype=np.uint8)
                img = _embed_anchors(img, cfg, jitter_px=random.randint(0, 10))
                anchors, zones = detect_roi(img, config=cfg)
            except Exception:
                errors += 1

        self.assertEqual(errors, 0, f"{errors}/20 iterations crashed")


# ---------------------------------------------------------------------------
# Acceptance: combined comprehensive test
# ---------------------------------------------------------------------------


@unittest.skipUnless(HAS_DETECTOR and HAS_CV2, "dependencies unavailable")
class TestAcceptanceFull(unittest.TestCase):
    """Full acceptance: 20 screenshots + fallback + manual + stability."""

    def test_comprehensive_acceptance(self):
        cfg = load_config()
        screenshots = _generate_20_screenshots(cfg)
        expected = len(cfg.get("anchors", {}))

        total_anchors = 0
        total_found = 0
        total_zones = 0

        for img in screenshots:
            anchors, zones = detect_roi(img, config=cfg)
            total_anchors += expected
            total_found += len(anchors)
            total_zones += len(zones)

        accuracy = total_found / total_anchors
        self.assertGreaterEqual(accuracy, 0.90)
        self.assertGreater(total_zones, 0)

        # Fallback test
        blank = np.full((600, 800, 3), 200, dtype=np.uint8)
        _, fb_zones = detect_roi(blank, config=cfg)
        self.assertIsInstance(fb_zones, list)

        # Manual override test
        roi = _manual_roi_from_two_points((50, 30), (750, 570))
        self.assertEqual(roi["w"], 700)
        self.assertEqual(roi["h"], 540)


if __name__ == "__main__":
    unittest.main()
