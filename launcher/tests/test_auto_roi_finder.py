"""
Tests for AutoROIFinder — Phase 1 of vision_fragility.md.

Generates 10 synthetic poker table screenshots (different skins,
resolutions, themes) and verifies that auto-calibration finds
critical ROI zones.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import math
import unittest
from typing import Tuple

import numpy as np

try:
    import cv2

    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

if CV_AVAILABLE:
    from launcher.vision.auto_roi_finder import AutoROIFinder, CalibrationResult


# ---------------------------------------------------------------------------
# Synthetic screenshot generator
# ---------------------------------------------------------------------------

def _draw_rounded_rect(img, x, y, w, h, color, radius=8, thickness=-1):
    """Draw a filled rounded rectangle."""
    # Top-left
    cv2.ellipse(img, (x + radius, y + radius), (radius, radius), 180, 0, 90, color, thickness)
    # Top-right
    cv2.ellipse(img, (x + w - radius, y + radius), (radius, radius), 270, 0, 90, color, thickness)
    # Bottom-right
    cv2.ellipse(img, (x + w - radius, y + h - radius), (radius, radius), 0, 0, 90, color, thickness)
    # Bottom-left
    cv2.ellipse(img, (x + radius, y + h - radius), (radius, radius), 90, 0, 90, color, thickness)
    # Fill rectangles
    cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, thickness)
    cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, thickness)


def generate_synthetic_table(
    width: int = 1920,
    height: int = 1080,
    felt_color: Tuple[int, int, int] = (40, 100, 50),
    bg_color: Tuple[int, int, int] = (30, 30, 30),
    button_color: Tuple[int, int, int] = (50, 180, 50),
    card_color: Tuple[int, int, int] = (240, 240, 240),
    add_buttons: bool = True,
    add_cards: bool = True,
    add_pot_text: bool = False,
    num_board_cards: int = 5,
    num_hero_cards: int = 2,
    table_shape: str = "ellipse",  # "ellipse" or "rectangle"
) -> np.ndarray:
    """
    Generate a synthetic poker table screenshot (BGR).

    The generated image has:
    - A coloured felt area (table)
    - Action buttons at the bottom
    - Card-shaped white rectangles for hero & board
    - Optional pot text
    """
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    # Table felt
    cx, cy = width // 2, height // 2
    rx, ry = int(width * 0.42), int(height * 0.40)

    if table_shape == "ellipse":
        cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, felt_color, -1)
    else:
        tx, ty = cx - rx, cy - ry
        cv2.rectangle(img, (tx, ty), (tx + 2 * rx, ty + 2 * ry), felt_color, -1)

    # Board cards (center)
    if add_cards:
        card_w = max(50, int(width * 0.04))
        card_h = int(card_w * 1.4)
        gap = max(5, int(width * 0.005))
        total = num_board_cards * card_w + (num_board_cards - 1) * gap
        start_x = cx - total // 2
        for i in range(num_board_cards):
            bx = start_x + i * (card_w + gap)
            by = cy - card_h // 2
            _draw_rounded_rect(img, bx, by, card_w, card_h, card_color, radius=5)

        # Hero cards (bottom center)
        hero_y = cy + int(ry * 0.55)
        for i in range(num_hero_cards):
            hx = cx - (num_hero_cards * card_w + (num_hero_cards - 1) * gap) // 2 + i * (card_w + gap)
            _draw_rounded_rect(img, hx, hero_y, card_w, card_h, card_color, radius=5)

    # Action buttons
    if add_buttons:
        btn_w = max(70, int(width * 0.06))
        btn_h = max(30, int(height * 0.035))
        btn_y = cy + int(ry * 0.85)
        btn_gap = int(width * 0.01)
        labels = ["Fold", "Check", "Call", "Raise"]
        total_btns = len(labels) * btn_w + (len(labels) - 1) * btn_gap
        start_bx = cx - total_btns // 2
        for i, label in enumerate(labels):
            bx = start_bx + i * (btn_w + btn_gap)
            cv2.rectangle(img, (bx, btn_y), (bx + btn_w, btn_y + btn_h), button_color, -1)
            # Put text on button
            font_scale = max(0.35, btn_w / 200)
            cv2.putText(
                img, label,
                (bx + 5, btn_y + btn_h - 8),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

    # Pot text
    if add_pot_text:
        pot_x = cx - 60
        pot_y = cy - int(ry * 0.35)
        cv2.putText(
            img, "Pot: $125.50",
            (pot_x, pot_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (255, 255, 255), 2, cv2.LINE_AA,
        )

    return img


# ---------------------------------------------------------------------------
# 10 different table configs
# ---------------------------------------------------------------------------

TABLE_CONFIGS = [
    {
        "name": "PokerStars Classic 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (40, 100, 50),   # Green felt
        "button_color": (50, 180, 50),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "GGPoker Dark 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (50, 70, 40),    # Dark green
        "bg_color": (15, 15, 20),
        "button_color": (40, 160, 80),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "888poker Blue 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (100, 60, 30),   # Blue felt (BGR)
        "button_color": (30, 130, 200),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "PartyPoker Red 1280x720",
        "width": 1280, "height": 720,
        "felt_color": (30, 40, 120),   # Red felt (BGR)
        "button_color": (50, 180, 50),
        "add_buttons": True, "add_cards": True,
        "table_shape": "rectangle",
    },
    {
        "name": "Ignition Teal 1600x900",
        "width": 1600, "height": 900,
        "felt_color": (80, 80, 30),    # Teal (BGR)
        "button_color": (30, 170, 170),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "No Buttons (cards only) 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (40, 100, 50),
        "add_buttons": False, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "No Cards (buttons only) 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (40, 100, 50),
        "button_color": (50, 180, 50),
        "add_buttons": True, "add_cards": False,
        "table_shape": "ellipse",
    },
    {
        "name": "Small window 800x600",
        "width": 800, "height": 600,
        "felt_color": (40, 100, 50),
        "button_color": (50, 180, 50),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "Ultra-wide 2560x1080",
        "width": 2560, "height": 1080,
        "felt_color": (50, 90, 45),
        "button_color": (40, 160, 80),
        "add_buttons": True, "add_cards": True,
        "table_shape": "ellipse",
    },
    {
        "name": "Rectangle table 1920x1080",
        "width": 1920, "height": 1080,
        "felt_color": (60, 80, 35),
        "button_color": (60, 190, 60),
        "add_buttons": True, "add_cards": True,
        "table_shape": "rectangle",
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

REQUIRED_ZONES = [
    "hero_card_1", "hero_card_2",
    "fold_button", "call_button", "raise_button",
    "pot", "hero_stack",
]


@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestAutoROIFinder(unittest.TestCase):
    """Test auto-calibration across 10 synthetic screenshots."""

    @classmethod
    def setUpClass(cls):
        cls.finder = AutoROIFinder(use_ocr=False)  # OCR off for synthetic tests
        cls.results = {}
        for cfg in TABLE_CONFIGS:
            name = cfg.pop("name")
            img = generate_synthetic_table(**cfg)
            cfg["name"] = name  # restore
            result = cls.finder.find_rois(img)
            cls.results[name] = (img, result)

    # --- Core tests ---

    def test_all_tables_return_zones(self):
        """Every synthetic table must produce at least 10 zones."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                self.assertGreaterEqual(
                    result.zone_count, 10,
                    f"{name}: expected >=10 zones, got {result.zone_count}",
                )

    def test_critical_zones_present(self):
        """All tables must have the critical zones."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                for zone in REQUIRED_ZONES:
                    self.assertIn(
                        zone, result.zones,
                        f"{name}: missing required zone '{zone}'",
                    )

    def test_confidence_above_minimum(self):
        """Confidence should be > 0 for all tables."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                self.assertGreater(
                    result.confidence, 0.0,
                    f"{name}: confidence is zero",
                )

    def test_zones_within_image_bounds(self):
        """All zone coordinates must be within image dimensions."""
        for name, (img, result) in self.results.items():
            h, w = img.shape[:2]
            with self.subTest(table=name):
                for zname, (x, y, zw, zh) in result.zones.items():
                    self.assertGreaterEqual(x, 0, f"{name}/{zname}: x < 0")
                    self.assertGreaterEqual(y, 0, f"{name}/{zname}: y < 0")
                    self.assertLessEqual(x + zw, w, f"{name}/{zname}: right edge > width")
                    self.assertLessEqual(y + zh, h, f"{name}/{zname}: bottom edge > height")

    def test_hero_cards_side_by_side(self):
        """Hero card 1 should be to the left of hero card 2."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                z1 = result.zones.get("hero_card_1")
                z2 = result.zones.get("hero_card_2")
                if z1 and z2:
                    self.assertLess(
                        z1[0], z2[0],
                        f"{name}: hero_card_1 not left of hero_card_2",
                    )

    def test_board_cards_ordered_left_to_right(self):
        """Board cards 1-5 should be ordered left to right."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                xs = []
                for i in range(1, 6):
                    z = result.zones.get(f"board_card_{i}")
                    if z:
                        xs.append(z[0])
                if len(xs) >= 2:
                    self.assertEqual(
                        xs, sorted(xs),
                        f"{name}: board cards not ordered left-to-right",
                    )

    def test_buttons_in_bottom_half(self):
        """Action buttons should be in the bottom half of the image."""
        for name, (img, result) in self.results.items():
            h = img.shape[0]
            with self.subTest(table=name):
                for btn in ("fold_button", "call_button", "raise_button"):
                    z = result.zones.get(btn)
                    if z:
                        mid_y = z[1] + z[3] // 2
                        self.assertGreater(
                            mid_y, h * 0.4,
                            f"{name}/{btn}: button too high (y_mid={mid_y})",
                        )

    def test_resolution_recorded(self):
        """Resolution in result should match image dimensions."""
        for name, (img, result) in self.results.items():
            h, w = img.shape[:2]
            with self.subTest(table=name):
                self.assertEqual(result.resolution, (w, h))

    def test_performance_under_500ms(self):
        """Each calibration should take < 500ms (no OCR)."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                self.assertLess(
                    result.elapsed_ms, 500,
                    f"{name}: took {result.elapsed_ms:.0f}ms (> 500ms)",
                )

    def test_to_roi_config_conversion(self):
        """CalibrationResult should convert to ROIConfig."""
        for name, (img, result) in self.results.items():
            with self.subTest(table=name):
                config = self.finder.to_roi_config(result, account_id="test")
                self.assertEqual(config.account_id, "test")
                self.assertEqual(len(config.zones), result.zone_count)


@unittest.skipUnless(CV_AVAILABLE, "OpenCV not installed")
class TestAnchorDetection(unittest.TestCase):
    """Lower-level tests for individual anchor detectors."""

    def setUp(self):
        self.finder = AutoROIFinder(use_ocr=False)

    def test_table_boundary_green_felt(self):
        img = generate_synthetic_table(felt_color=(40, 100, 50))
        anchors = self.finder._find_table_boundary(img)
        self.assertTrue(len(anchors) > 0, "No table boundary found for green felt")
        self.assertEqual(anchors[0].name, "table_boundary")
        self.assertGreater(anchors[0].confidence, 0.3)

    def test_table_boundary_blue_felt(self):
        img = generate_synthetic_table(felt_color=(100, 60, 30))
        anchors = self.finder._find_table_boundary(img)
        self.assertTrue(len(anchors) > 0, "No table boundary found for blue felt")

    def test_color_button_detection(self):
        img = generate_synthetic_table(
            button_color=(50, 180, 50), add_buttons=True
        )
        anchors = self.finder._find_color_anchors(img)
        self.assertTrue(len(anchors) > 0, "No color buttons detected")

    def test_card_shape_detection(self):
        img = generate_synthetic_table(add_cards=True)
        anchors = self.finder._find_card_shapes(img)
        # Should find at least some card shapes
        self.assertTrue(len(anchors) >= 2, f"Expected >=2 card shapes, found {len(anchors)}")

    def test_no_felt_returns_empty(self):
        """Plain dark image should not produce table boundary."""
        img = np.full((1080, 1920, 3), (20, 20, 20), dtype=np.uint8)
        anchors = self.finder._find_table_boundary(img)
        self.assertEqual(len(anchors), 0, "Should not detect boundary on plain dark image")


if __name__ == "__main__":
    unittest.main(verbosity=2)
