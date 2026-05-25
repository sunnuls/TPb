"""
Tests for roadmap11_auto_roi_detection.md Phase 2 — Anchor templates & config.

Validates:
  - templates/anchors/ directory exists with 6 PNG files
  - Each PNG is a valid image (loadable by cv2/PIL)
  - config/anchor_templates.yaml exists and is valid YAML
  - YAML contains 6 anchors with required fields
  - YAML contains derived_zones section
  - Template files referenced in YAML actually exist
  - Anchor images have reasonable sizes
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


ROOT = Path(__file__).resolve().parent.parent
ANCHORS_DIR = ROOT / "templates" / "anchors"
CONFIG_FILE = ROOT / "config" / "anchor_templates.yaml"

EXPECTED_ANCHORS = [
    "logo_coinpoker",
    "btn_fold",
    "btn_call",
    "btn_raise",
    "chip_icon",
    "table_border",
]


class TestAnchorDirectory(unittest.TestCase):
    """templates/anchors/ directory structure."""

    def test_directory_exists(self):
        self.assertTrue(ANCHORS_DIR.exists(), f"{ANCHORS_DIR} does not exist")
        self.assertTrue(ANCHORS_DIR.is_dir())

    def test_all_anchor_pngs_exist(self):
        for name in EXPECTED_ANCHORS:
            path = ANCHORS_DIR / f"{name}.png"
            self.assertTrue(path.exists(), f"Missing: {path}")

    def test_no_extra_files(self):
        """Only expected anchors + maybe .gitkeep."""
        files = [f.stem for f in ANCHORS_DIR.glob("*.png")]
        for f in files:
            self.assertIn(f, EXPECTED_ANCHORS, f"Unexpected file: {f}.png")


class TestAnchorImages(unittest.TestCase):
    """Anchor images are valid and reasonable size."""

    @unittest.skipUnless(HAS_CV2, "cv2 not available")
    def test_cv2_loadable(self):
        for name in EXPECTED_ANCHORS:
            path = str(ANCHORS_DIR / f"{name}.png")
            img = cv2.imread(path)
            self.assertIsNotNone(img, f"cv2 cannot load {name}.png")
            h, w = img.shape[:2]
            self.assertGreater(h, 0)
            self.assertGreater(w, 0)

    @unittest.skipUnless(HAS_PIL, "PIL not available")
    def test_pil_loadable(self):
        for name in EXPECTED_ANCHORS:
            path = ANCHORS_DIR / f"{name}.png"
            img = Image.open(path)
            self.assertGreater(img.width, 0)
            self.assertGreater(img.height, 0)

    @unittest.skipUnless(HAS_CV2, "cv2 not available")
    def test_reasonable_sizes(self):
        """Anchor images are between 8px and 200px in each dimension."""
        for name in EXPECTED_ANCHORS:
            path = str(ANCHORS_DIR / f"{name}.png")
            img = cv2.imread(path)
            h, w = img.shape[:2]
            self.assertGreaterEqual(w, 8, f"{name} too narrow: w={w}")
            self.assertLessEqual(w, 200, f"{name} too wide: w={w}")
            self.assertGreaterEqual(h, 8, f"{name} too short: h={h}")
            self.assertLessEqual(h, 200, f"{name} too tall: h={h}")


@unittest.skipUnless(HAS_YAML, "pyyaml not available")
class TestAnchorConfig(unittest.TestCase):
    """config/anchor_templates.yaml validation."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))

    def test_config_file_exists(self):
        self.assertTrue(CONFIG_FILE.exists())

    def test_has_anchors_section(self):
        self.assertIn("anchors", self.cfg)
        self.assertIsInstance(self.cfg["anchors"], dict)

    def test_has_6_anchors(self):
        self.assertEqual(len(self.cfg["anchors"]), 6)

    def test_all_expected_anchors_present(self):
        for name in EXPECTED_ANCHORS:
            self.assertIn(name, self.cfg["anchors"], f"Missing anchor: {name}")

    def test_anchor_required_fields(self):
        for name, anchor in self.cfg["anchors"].items():
            self.assertIn("file", anchor, f"{name}: missing 'file'")
            self.assertIn("threshold", anchor, f"{name}: missing 'threshold'")
            self.assertIn("zone", anchor, f"{name}: missing 'zone'")
            self.assertIn("relative", anchor, f"{name}: missing 'relative'")
            self.assertIn("roi_offsets", anchor, f"{name}: missing 'roi_offsets'")

    def test_threshold_range(self):
        for name, anchor in self.cfg["anchors"].items():
            t = anchor["threshold"]
            self.assertGreaterEqual(t, 0.0, f"{name}: threshold < 0")
            self.assertLessEqual(t, 1.0, f"{name}: threshold > 1")

    def test_relative_coords_valid(self):
        for name, anchor in self.cfg["anchors"].items():
            rel = anchor["relative"]
            for key in ("x_min", "y_min", "x_max", "y_max"):
                self.assertIn(key, rel, f"{name}: missing relative.{key}")
                v = rel[key]
                self.assertGreaterEqual(v, 0.0, f"{name}.{key} < 0")
                self.assertLessEqual(v, 1.0, f"{name}.{key} > 1")

    def test_file_references_exist(self):
        for name, anchor in self.cfg["anchors"].items():
            path = ROOT / anchor["file"]
            self.assertTrue(path.exists(), f"{name}: file not found: {path}")

    def test_has_derived_zones(self):
        self.assertIn("derived_zones", self.cfg)
        zones = self.cfg["derived_zones"]
        self.assertIsInstance(zones, dict)
        self.assertGreaterEqual(len(zones), 5)

    def test_derived_zones_have_description(self):
        for name, zone in self.cfg["derived_zones"].items():
            self.assertIn("description", zone, f"zone '{name}': missing description")

    def test_roi_offsets_structure(self):
        for name, anchor in self.cfg["anchors"].items():
            for roi_name, offsets in anchor["roi_offsets"].items():
                self.assertIn("dx", offsets, f"{name}.{roi_name}: missing dx")
                self.assertIn("dy", offsets, f"{name}.{roi_name}: missing dy")
                self.assertIn("w", offsets, f"{name}.{roi_name}: missing w")
                self.assertIn("h", offsets, f"{name}.{roi_name}: missing h")


if __name__ == "__main__":
    unittest.main()
