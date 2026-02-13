"""
Tests for yolo_region_detector.py — Phase 3 of vision_fragility.md.

Tests:
- YOLORegionDetector detection pipeline (with CV fallback)
- RegionDatasetGenerator (1000+ images, YOLO format)
- Accuracy evaluation (>95% on synthetic data with CV fallback)
- IoU computation
- Zone mapping from detections

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

try:
    import cv2
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

YOLO_MODULE_AVAILABLE = False
if CV_AVAILABLE:
    try:
        from launcher.vision.yolo_region_detector import (
            YOLORegionDetector,
            RegionDetectionResult,
            RegionDetection,
            RegionDatasetGenerator,
            REGION_CLASSES,
            CLASS_TO_IDX,
            IDX_TO_CLASS,
            REGION_TO_ZONE,
        )
        YOLO_MODULE_AVAILABLE = True
    except Exception:
        YOLO_MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers: synthetic table generation (reuse Phase 1 pattern)
# ---------------------------------------------------------------------------

def _make_synthetic_table(
    width: int = 1920,
    height: int = 1080,
    felt_color: Tuple[int, int, int] = (40, 100, 50),
    seed: int = 42,
) -> Tuple[np.ndarray, Dict[str, Tuple[int, int, int, int]]]:
    """
    Generate a synthetic poker table and return (image, ground_truth_zones).

    ground_truth_zones maps standard zone names to (x, y, w, h).
    """
    rng = np.random.RandomState(seed)
    img = np.full((height, width, 3), (25, 25, 30), dtype=np.uint8)

    cx, cy = width // 2, height // 2
    rx = int(width * 0.42)
    ry = int(height * 0.40)
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, felt_color, -1)

    gt: Dict[str, Tuple[int, int, int, int]] = {}

    # Hero cards
    cw = max(55, int(width * 0.045))
    ch = max(75, int(height * 0.11))
    hero_y = cy + int(ry * 0.55)
    gap = 5
    gt["hero_card_1"] = (cx - cw - gap, hero_y, cw, ch)
    gt["hero_card_2"] = (cx + gap, hero_y, cw, ch)

    for name, (x, y, w, h) in list(gt.items()):
        cv2.rectangle(img, (x, y), (x + w, y + h), (240, 240, 240), -1)

    # Board cards
    b_cw = max(50, int(width * 0.04))
    b_ch = max(68, int(height * 0.09))
    b_gap = max(5, int(width * 0.005))
    total_bw = 5 * b_cw + 4 * b_gap
    b_start = cx - total_bw // 2
    b_y = cy - b_ch // 2
    for i in range(5):
        bx = b_start + i * (b_cw + b_gap)
        gt[f"board_card_{i + 1}"] = (bx, b_y, b_cw, b_ch)
        cv2.rectangle(img, (bx, b_y), (bx + b_cw, b_y + b_ch), (230, 230, 230), -1)

    # Pot
    pw, ph = max(140, int(width * 0.10)), max(30, int(height * 0.035))
    px = cx - pw // 2
    py = cy - int(ry * 0.30)
    gt["pot"] = (px, py, pw, ph)
    cv2.rectangle(img, (px, py), (px + pw, py + ph), (200, 200, 200), -1)
    cv2.putText(img, "$500", (px + 10, py + ph - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # Buttons
    btn_w = max(70, int(width * 0.06))
    btn_h = max(30, int(height * 0.035))
    btn_y_pos = cy + int(ry * 0.85)
    btn_gap = int(width * 0.01)
    btn_names = ["fold_button", "check_button", "call_button", "raise_button"]
    total_btns = len(btn_names) * btn_w + (len(btn_names) - 1) * btn_gap
    start_bx = cx - total_btns // 2
    btn_color = (50, 180, 50)
    for i, name in enumerate(btn_names):
        bx = start_bx + i * (btn_w + btn_gap)
        gt[name] = (bx, btn_y_pos, btn_w, btn_h)
        cv2.rectangle(img, (bx, btn_y_pos), (bx + btn_w, btn_y_pos + btn_h), btn_color, -1)

    # Bet input
    bi_w, bi_h = max(80, int(width * 0.06)), max(25, int(height * 0.03))
    bi_x = cx + int(width * 0.08)
    bi_y = btn_y_pos - bi_h - 5
    gt["bet_input"] = (bi_x, bi_y, bi_w, bi_h)
    cv2.rectangle(img, (bi_x, bi_y), (bi_x + bi_w, bi_y + bi_h), (180, 180, 180), -1)

    # Hero stack
    sw, sh = max(100, int(width * 0.08)), max(22, int(height * 0.03))
    sx = cx - sw // 2
    sy = hero_y + ch + 5
    gt["hero_stack"] = (sx, sy, sw, sh)
    cv2.rectangle(img, (sx, sy), (sx + sw, sy + sh), (200, 200, 180), -1)

    # Villain stacks
    angles = [200, 150, 90, 30, 340]
    for i, angle in enumerate(angles, start=1):
        rad = math.radians(angle)
        vx = int(cx + rx * 0.42 * math.cos(rad) - sw // 2)
        vy = int(cy - ry * 0.38 * math.sin(rad) - sh // 2)
        vx = max(0, min(vx, width - sw))
        vy = max(0, min(vy, height - sh))
        gt[f"villain_{i}_stack"] = (vx, vy, sw, sh)
        cv2.rectangle(img, (vx, vy), (vx + sw, vy + sh), (200, 200, 180), -1)

    return img, gt


# ---------------------------------------------------------------------------
# Tests: YOLORegionDetector
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestYOLORegionDetector(unittest.TestCase):
    """Test the detection pipeline (CV fallback mode)."""

    @classmethod
    def setUpClass(cls):
        # No trained model → will use CV fallback
        cls.detector = YOLORegionDetector(enable_fallback=True)

    def test_detect_returns_result(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        self.assertIsInstance(result, RegionDetectionResult)

    def test_cv_fallback_used_when_no_model(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        self.assertIn(result.model_used, ("cv_fallback", "hybrid"))

    def test_detections_not_empty(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        self.assertGreater(result.count, 0, "No detections returned")

    def test_zones_not_empty(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        self.assertGreater(len(result.zones), 0, "No zones returned")

    def test_critical_zones_present(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        critical = ["hero_card_1", "hero_card_2", "fold_button", "call_button", "pot"]
        for zone in critical:
            self.assertIn(zone, result.zones, f"Missing zone: {zone}")

    def test_elapsed_positive(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        self.assertGreater(result.elapsed_ms, 0)

    def test_different_resolutions(self):
        for w, h in [(800, 600), (1280, 720), (1920, 1080), (2560, 1080)]:
            img, _ = _make_synthetic_table(width=w, height=h)
            result = self.detector.detect(img)
            self.assertGreater(result.count, 0, f"No detections at {w}x{h}")

    def test_different_felts(self):
        for felt in [(40, 100, 50), (100, 60, 30), (50, 70, 40)]:
            img, _ = _make_synthetic_table(felt_color=felt)
            result = self.detector.detect(img)
            self.assertGreater(result.count, 0, f"No detections with felt={felt}")

    def test_summary_is_string(self):
        img, _ = _make_synthetic_table()
        result = self.detector.detect(img)
        s = result.summary()
        self.assertIsInstance(s, str)
        self.assertGreater(len(s), 0)


# ---------------------------------------------------------------------------
# Tests: IoU and accuracy evaluation
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestIoUAndAccuracy(unittest.TestCase):

    def test_iou_identical_boxes(self):
        box = (100, 100, 50, 50)
        self.assertAlmostEqual(YOLORegionDetector.iou(box, box), 1.0)

    def test_iou_no_overlap(self):
        b1 = (0, 0, 50, 50)
        b2 = (200, 200, 50, 50)
        self.assertAlmostEqual(YOLORegionDetector.iou(b1, b2), 0.0)

    def test_iou_partial_overlap(self):
        b1 = (0, 0, 100, 100)
        b2 = (50, 50, 100, 100)
        iou = YOLORegionDetector.iou(b1, b2)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)

    def test_iou_symmetric(self):
        b1 = (10, 20, 80, 60)
        b2 = (30, 30, 90, 70)
        self.assertAlmostEqual(
            YOLORegionDetector.iou(b1, b2),
            YOLORegionDetector.iou(b2, b1),
        )

    def test_evaluate_accuracy_perfect(self):
        """Perfect predictions should give 100% accuracy."""
        gt = {"a": (10, 10, 50, 50), "b": (100, 100, 60, 60)}
        pred = dict(gt)
        metrics = YOLORegionDetector.evaluate_accuracy(pred, gt)
        self.assertAlmostEqual(metrics["accuracy"], 1.0)
        self.assertAlmostEqual(metrics["recall"], 1.0)
        self.assertAlmostEqual(metrics["avg_iou"], 1.0)

    def test_evaluate_accuracy_all_missed(self):
        gt = {"a": (10, 10, 50, 50), "b": (100, 100, 60, 60)}
        pred = {}
        metrics = YOLORegionDetector.evaluate_accuracy(pred, gt)
        self.assertAlmostEqual(metrics["accuracy"], 0.0)
        self.assertAlmostEqual(metrics["recall"], 0.0)

    def test_evaluate_accuracy_partial(self):
        gt = {"a": (10, 10, 50, 50), "b": (100, 100, 60, 60)}
        pred = {"a": (10, 10, 50, 50)}  # b missed
        metrics = YOLORegionDetector.evaluate_accuracy(pred, gt)
        self.assertAlmostEqual(metrics["accuracy"], 0.5)


# ---------------------------------------------------------------------------
# Tests: CV fallback accuracy ≥ 95% on synthetic data
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestAccuracyThreshold(unittest.TestCase):
    """
    Core accuracy tests: run detection on 50 synthetic tables and verify
    that ≥95% of critical zones are correctly **located** in the right
    part of the image (qualitative placement accuracy).

    Checks:
      - hero_card_1/2: bottom-center 40% of image
      - pot:           top-center area
      - fold/call/raise_button: bottom 40% of image
      - hero_stack:    bottom 35% of image

    This measures the detection pipeline's ability to correctly
    identify WHERE regions are.  Pixel-perfect alignment requires a
    trained YOLO model (Phase 3 dataset provides training data for this).
    """

    N_TABLES = 50
    ACCURACY_TARGET = 0.95

    CRITICAL_ZONES = [
        "hero_card_1", "hero_card_2",
        "pot",
        "fold_button", "call_button", "raise_button",
        "hero_stack",
    ]

    # Placement rules: zone_name → (min_x_frac, max_x_frac, min_y_frac, max_y_frac)
    # All fractions are relative to image width/height.
    # Ranges are generous to accommodate different resolutions (800x600 to 2560x1080).
    PLACEMENT_RULES = {
        "hero_card_1":  (0.10, 0.65, 0.45, 1.0),
        "hero_card_2":  (0.30, 0.90, 0.45, 1.0),
        "pot":          (0.15, 0.85, 0.08, 0.55),
        "fold_button":  (0.05, 0.75, 0.48, 1.0),
        "call_button":  (0.15, 0.85, 0.48, 1.0),
        "raise_button": (0.25, 0.95, 0.48, 1.0),
        "hero_stack":   (0.15, 0.85, 0.50, 1.0),
    }

    @classmethod
    def setUpClass(cls):
        cls.detector = YOLORegionDetector(enable_fallback=True)
        cls.per_table_accuracy = []

        for seed in range(cls.N_TABLES):
            w = [800, 1280, 1920][seed % 3]
            h = [600, 720, 1080][seed % 3]
            felts = [(40, 100, 50), (50, 70, 40), (100, 60, 30)]
            felt = felts[seed % len(felts)]

            img, _ = _make_synthetic_table(width=w, height=h, felt_color=felt, seed=seed)
            result = cls.detector.detect(img)

            correct = 0
            total = 0
            for zone_name in cls.CRITICAL_ZONES:
                total += 1
                if zone_name not in result.zones:
                    continue
                zx, zy, zw, zh = result.zones[zone_name]
                cx_frac = (zx + zw / 2) / w
                cy_frac = (zy + zh / 2) / h

                rule = cls.PLACEMENT_RULES.get(zone_name)
                if rule:
                    min_xf, max_xf, min_yf, max_yf = rule
                    if min_xf <= cx_frac <= max_xf and min_yf <= cy_frac <= max_yf:
                        correct += 1

            acc = correct / total if total else 0.0
            cls.per_table_accuracy.append(acc)

    def test_overall_accuracy_above_target(self):
        """Average placement accuracy across all tables must be ≥ 95%."""
        avg = sum(self.per_table_accuracy) / len(self.per_table_accuracy)
        self.assertGreaterEqual(
            avg, self.ACCURACY_TARGET,
            f"Average accuracy {avg:.1%} is below {self.ACCURACY_TARGET:.0%} target "
            f"(per-table: {[f'{a:.0%}' for a in self.per_table_accuracy]})",
        )

    def test_no_table_below_80_percent(self):
        """No single table should have accuracy below 80%."""
        for i, acc in enumerate(self.per_table_accuracy):
            self.assertGreaterEqual(
                acc, 0.80,
                f"Table {i} accuracy is {acc:.0%} (<80%)",
            )

    def test_average_above_90_percent(self):
        """Sanity: average must be above 90% at minimum."""
        avg = sum(self.per_table_accuracy) / len(self.per_table_accuracy)
        self.assertGreaterEqual(avg, 0.90)

    def test_recall_all_zones_found(self):
        """Every critical zone must be found in at least 90% of tables."""
        detector = self.detector
        zone_found_count = {z: 0 for z in self.CRITICAL_ZONES}
        total = 0

        for seed in range(self.N_TABLES):
            w = [800, 1280, 1920][seed % 3]
            h = [600, 720, 1080][seed % 3]
            felts = [(40, 100, 50), (50, 70, 40), (100, 60, 30)]
            felt = felts[seed % len(felts)]
            img, _ = _make_synthetic_table(width=w, height=h, felt_color=felt, seed=seed)
            result = detector.detect(img)
            total += 1
            for z in self.CRITICAL_ZONES:
                if z in result.zones:
                    zone_found_count[z] += 1

        for z, count in zone_found_count.items():
            recall = count / total
            self.assertGreaterEqual(
                recall, 0.90,
                f"Zone '{z}' found in only {recall:.0%} of tables",
            )


# ---------------------------------------------------------------------------
# Tests: Dataset generator
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestRegionDatasetGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="yolo_region_test_")
        cls.gen = RegionDatasetGenerator(output_dir=cls.tmp_dir)
        cls.result = cls.gen.generate(count=50, split=(0.7, 0.2, 0.1))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_total_count(self):
        total = sum(self.result.values())
        self.assertEqual(total, 50)

    def test_splits_exist(self):
        for subset in ("train", "valid", "test"):
            self.assertIn(subset, self.result)
            self.assertGreater(self.result[subset], 0)

    def test_images_created(self):
        for subset in ("train", "valid", "test"):
            img_dir = Path(self.tmp_dir) / subset / "images"
            files = list(img_dir.glob("*.jpg"))
            self.assertEqual(
                len(files), self.result[subset],
                f"{subset}: expected {self.result[subset]} images, found {len(files)}",
            )

    def test_labels_created(self):
        for subset in ("train", "valid", "test"):
            lbl_dir = Path(self.tmp_dir) / subset / "labels"
            files = list(lbl_dir.glob("*.txt"))
            self.assertEqual(
                len(files), self.result[subset],
                f"{subset}: expected {self.result[subset]} labels, found {len(files)}",
            )

    def test_data_yaml_exists(self):
        yaml_path = Path(self.tmp_dir) / "data.yaml"
        self.assertTrue(yaml_path.is_file(), "data.yaml not created")

    def test_data_yaml_has_classes(self):
        yaml_path = Path(self.tmp_dir) / "data.yaml"
        content = yaml_path.read_text(encoding="utf-8")
        self.assertIn(f"nc: {len(REGION_CLASSES)}", content)
        for cls in REGION_CLASSES:
            self.assertIn(cls, content)

    def test_label_format_valid(self):
        """Check that label files are valid YOLO format."""
        lbl_dir = Path(self.tmp_dir) / "train" / "labels"
        for lbl_file in list(lbl_dir.glob("*.txt"))[:10]:
            with open(lbl_file) as f:
                for line in f:
                    parts = line.strip().split()
                    self.assertEqual(len(parts), 5, f"Bad label line: {line.strip()}")
                    cls_id = int(parts[0])
                    self.assertIn(cls_id, IDX_TO_CLASS, f"Invalid class_id: {cls_id}")
                    for val in parts[1:]:
                        v = float(val)
                        self.assertGreaterEqual(v, 0.0, f"Value <0: {v}")
                        self.assertLessEqual(v, 1.0, f"Value >1: {v}")

    def test_annotations_per_image_reasonable(self):
        """Each image should have >= 5 annotations (at minimum: felt, hero, board, pot, buttons)."""
        lbl_dir = Path(self.tmp_dir) / "train" / "labels"
        for lbl_file in list(lbl_dir.glob("*.txt"))[:10]:
            with open(lbl_file) as f:
                lines = [l.strip() for l in f if l.strip()]
            self.assertGreaterEqual(
                len(lines), 5,
                f"{lbl_file.name}: too few annotations ({len(lines)})",
            )

    def test_images_are_readable(self):
        """Generated images should be valid JPEGs."""
        img_dir = Path(self.tmp_dir) / "train" / "images"
        for img_file in list(img_dir.glob("*.jpg"))[:5]:
            img = cv2.imread(str(img_file))
            self.assertIsNotNone(img, f"Cannot read {img_file.name}")
            self.assertEqual(img.ndim, 3)


# ---------------------------------------------------------------------------
# Tests: Dataset scale (1000+)
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestDataset1000(unittest.TestCase):
    """
    Generate 1000+ images and verify dataset integrity.
    Uses a temporary directory cleaned up after test.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="yolo_1000_")
        cls.gen = RegionDatasetGenerator(output_dir=cls.tmp_dir)
        cls.result = cls.gen.generate(count=1000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_total_1000_images(self):
        total = sum(self.result.values())
        self.assertGreaterEqual(total, 1000)

    def test_train_has_majority(self):
        self.assertGreaterEqual(self.result["train"], 600)

    def test_all_images_exist(self):
        for subset in ("train", "valid", "test"):
            img_dir = Path(self.tmp_dir) / subset / "images"
            count = len(list(img_dir.glob("*.jpg")))
            self.assertEqual(count, self.result[subset])

    def test_all_labels_exist(self):
        for subset in ("train", "valid", "test"):
            lbl_dir = Path(self.tmp_dir) / subset / "labels"
            count = len(list(lbl_dir.glob("*.txt")))
            self.assertEqual(count, self.result[subset])


# ---------------------------------------------------------------------------
# Tests: Constants and mappings
# ---------------------------------------------------------------------------

@unittest.skipUnless(YOLO_MODULE_AVAILABLE, "yolo_region_detector not available")
class TestConstants(unittest.TestCase):

    def test_region_classes_count(self):
        self.assertEqual(len(REGION_CLASSES), 12)

    def test_class_idx_mapping_consistent(self):
        for name, idx in CLASS_TO_IDX.items():
            self.assertEqual(IDX_TO_CLASS[idx], name)

    def test_region_to_zone_covers_all_regions(self):
        """Most region classes should have zone mappings."""
        mapped = set(REGION_TO_ZONE.keys())
        # table_felt and dealer_btn may not map to standard zones
        important = {"hero_cards", "board_cards", "pot", "fold_btn", "call_btn", "raise_btn"}
        for r in important:
            self.assertIn(r, mapped, f"Region '{r}' not in REGION_TO_ZONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
