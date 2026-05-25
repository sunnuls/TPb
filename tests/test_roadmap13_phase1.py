"""
Tests for roadmap13 Phase 1 — Template preparation (one-time training).
Validates 10 anchor templates and anchor_templates.yaml config.
"""
import os
import unittest
import yaml
import cv2
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates", "anchors")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "anchor_templates.yaml")

REQUIRED_ANCHORS = [
    "logo_coinpoker", "btn_fold", "btn_call", "btn_raise",
    "btn_check", "chip_icon", "pot_icon", "dealer_button",
    "table_border", "table_corner",
]


class TestPhase1Templates(unittest.TestCase):
    """Validate that all 10 template images exist and are usable."""

    def test_templates_dir_exists(self):
        self.assertTrue(os.path.isdir(TEMPLATES_DIR))

    def test_at_least_10_templates(self):
        pngs = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".png")]
        self.assertGreaterEqual(len(pngs), 10, f"Found only {len(pngs)} PNGs")

    def test_all_required_files_present(self):
        for name in REQUIRED_ANCHORS:
            path = os.path.join(TEMPLATES_DIR, f"{name}.png")
            self.assertTrue(os.path.isfile(path), f"Missing {name}.png")

    def test_images_loadable_opencv(self):
        for name in REQUIRED_ANCHORS:
            path = os.path.join(TEMPLATES_DIR, f"{name}.png")
            img = cv2.imread(path)
            self.assertIsNotNone(img, f"{name}.png unreadable by cv2")
            self.assertGreater(img.size, 0)

    def test_images_loadable_numpy(self):
        for name in REQUIRED_ANCHORS:
            path = os.path.join(TEMPLATES_DIR, f"{name}.png")
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            self.assertIsInstance(img, np.ndarray)

    def test_reasonable_sizes(self):
        for name in REQUIRED_ANCHORS:
            path = os.path.join(TEMPLATES_DIR, f"{name}.png")
            img = cv2.imread(path)
            h, w = img.shape[:2]
            self.assertGreaterEqual(w, 8, f"{name} too narrow ({w}px)")
            self.assertGreaterEqual(h, 8, f"{name} too short ({h}px)")
            self.assertLessEqual(w, 300, f"{name} too wide ({w}px)")
            self.assertLessEqual(h, 300, f"{name} too tall ({h}px)")


class TestPhase1Config(unittest.TestCase):
    """Validate anchor_templates.yaml structure."""

    @classmethod
    def setUpClass(cls):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)

    def test_config_exists(self):
        self.assertTrue(os.path.isfile(CONFIG_PATH))

    def test_has_anchors_section(self):
        self.assertIn("anchors", self.config)

    def test_has_derived_zones_section(self):
        self.assertIn("derived_zones", self.config)

    def test_10_anchors_defined(self):
        self.assertEqual(len(self.config["anchors"]), 10)

    def test_all_required_anchors_in_config(self):
        for name in REQUIRED_ANCHORS:
            self.assertIn(name, self.config["anchors"], f"Missing anchor: {name}")

    def test_anchor_required_fields(self):
        required = {"file", "threshold", "zone", "relative", "roi_offsets"}
        for name, spec in self.config["anchors"].items():
            for field in required:
                self.assertIn(field, spec, f"{name} missing field '{field}'")

    def test_anchor_has_scales(self):
        for name, spec in self.config["anchors"].items():
            self.assertIn("scales", spec, f"{name} missing 'scales' for multi-scale")
            self.assertIsInstance(spec["scales"], list)
            self.assertGreater(len(spec["scales"]), 0)

    def test_thresholds_in_range(self):
        for name, spec in self.config["anchors"].items():
            t = spec["threshold"]
            self.assertGreaterEqual(t, 0.3, f"{name} threshold too low")
            self.assertLessEqual(t, 1.0, f"{name} threshold too high")

    def test_relative_coords_valid(self):
        for name, spec in self.config["anchors"].items():
            rel = spec["relative"]
            for k in ("x_min", "y_min", "x_max", "y_max"):
                self.assertIn(k, rel, f"{name} relative missing '{k}'")
                self.assertGreaterEqual(rel[k], 0.0)
                self.assertLessEqual(rel[k], 1.0)

    def test_file_paths_valid(self):
        for name, spec in self.config["anchors"].items():
            path = os.path.join(PROJECT_ROOT, spec["file"])
            self.assertTrue(os.path.isfile(path), f"{name}: file not found at {spec['file']}")

    def test_derived_zones_count(self):
        self.assertGreaterEqual(len(self.config["derived_zones"]), 6)

    def test_derived_zones_have_method(self):
        for name, spec in self.config["derived_zones"].items():
            self.assertIn("method", spec, f"derived zone '{name}' missing method")


if __name__ == "__main__":
    unittest.main()
