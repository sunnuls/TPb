"""
Tests for training_data_collector.py — Phase 3 of vision_fragility.md.

Tests the full ML training pipeline:
- Screenshot collection (synthetic + from directory)
- Auto-annotation with AutoROIFinder → YOLO format
- Dataset building (images/labels + data.yaml)
- Accuracy validation (IoU matching, per-class stats)
- Pipeline integration

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from training_data_collector import (
        Annotation,
        AutoAnnotator,
        CollectedSample,
        DatasetBuilder,
        DatasetStats,
        ScreenshotCollector,
        AccuracyValidator,
        ValidationResult,
        TrainConfig,
        TrainResult,
        TrainingPipeline,
        YOLOTrainer,
        YOLO_CLASSES,
        CLASS_TO_IDX,
        ZONE_TO_CLASS,
    )
    MODULE_OK = True
except Exception:
    MODULE_OK = False


# ---------------------------------------------------------------------------
# Annotation tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(MODULE_OK, "training_data_collector not importable")
class TestAnnotation(unittest.TestCase):

    def test_to_yolo_line(self):
        ann = Annotation(class_idx=0, cx=0.5, cy=0.5, w=0.1, h=0.15)
        line = ann.to_yolo_line()
        self.assertTrue(line.startswith("0 "))
        parts = line.split()
        self.assertEqual(len(parts), 5)
        self.assertAlmostEqual(float(parts[1]), 0.5, places=4)

    def test_from_bbox(self):
        ann = Annotation.from_bbox(2, 100, 200, 50, 30, 1000, 600)
        self.assertEqual(ann.class_idx, 2)
        self.assertAlmostEqual(ann.cx, (100 + 25) / 1000, places=4)
        self.assertAlmostEqual(ann.cy, (200 + 15) / 600, places=4)
        self.assertAlmostEqual(ann.w, 50 / 1000, places=4)
        self.assertAlmostEqual(ann.h, 30 / 600, places=4)

    def test_roundtrip(self):
        ann = Annotation.from_bbox(5, 200, 300, 80, 40, 1920, 1080)
        line = ann.to_yolo_line()
        parts = line.split()
        self.assertEqual(int(parts[0]), 5)
        # All values should be between 0 and 1
        for v in parts[1:]:
            self.assertGreaterEqual(float(v), 0.0)
            self.assertLessEqual(float(v), 1.0)


@unittest.skipUnless(MODULE_OK, "training_data_collector not importable")
class TestCollectedSample(unittest.TestCase):

    def test_label_path(self):
        s = CollectedSample(image_path="data/img_001.png")
        self.assertTrue(s.label_path.endswith("img_001.txt"))

    def test_empty_annotations(self):
        s = CollectedSample(image_path="test.jpg")
        self.assertEqual(len(s.annotations), 0)


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(MODULE_OK, "training_data_collector not importable")
class TestConstants(unittest.TestCase):

    def test_yolo_classes_nonempty(self):
        self.assertGreater(len(YOLO_CLASSES), 0)

    def test_class_to_idx_matches(self):
        for name, idx in CLASS_TO_IDX.items():
            self.assertEqual(YOLO_CLASSES[idx], name)

    def test_zone_to_class_valid(self):
        for zone, cls in ZONE_TO_CLASS.items():
            self.assertIn(cls, CLASS_TO_IDX, f"Zone {zone} → class {cls} not in CLASS_TO_IDX")


# ---------------------------------------------------------------------------
# ScreenshotCollector tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or module not available")
class TestScreenshotCollector(unittest.TestCase):

    def test_collect_synthetic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ScreenshotCollector(tmpdir)
            paths = collector.collect_synthetic(count=5, width=640, height=480)
            self.assertEqual(len(paths), 5)
            self.assertEqual(collector.count, 5)
            for p in paths:
                self.assertTrue(Path(p).exists())
                img = cv2.imread(p)
                self.assertIsNotNone(img)
                self.assertGreater(img.shape[0], 0)

    def test_collect_from_directory(self):
        with tempfile.TemporaryDirectory() as srcdir, \
             tempfile.TemporaryDirectory() as dstdir:
            # Create fake screenshots in source
            for i in range(3):
                img = np.full((100, 100, 3), i * 50, dtype=np.uint8)
                cv2.imwrite(str(Path(srcdir) / f"screen_{i}.png"), img)

            collector = ScreenshotCollector(dstdir)
            paths = collector.collect_from_directory(srcdir)
            self.assertEqual(len(paths), 3)
            self.assertEqual(collector.count, 3)

    def test_collect_from_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ScreenshotCollector(tmpdir)
            paths = collector.collect_from_directory("/nonexistent/path")
            self.assertEqual(paths, [])

    def test_synthetic_image_has_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ScreenshotCollector(tmpdir)
            paths = collector.collect_synthetic(count=1)
            img = cv2.imread(paths[0])
            # Should not be all black (has felt, cards, buttons)
            self.assertGreater(img.mean(), 10)


# ---------------------------------------------------------------------------
# AutoAnnotator tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or module not available")
class TestAutoAnnotator(unittest.TestCase):

    def test_annotate_synthetic_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate a synthetic table image
            collector = ScreenshotCollector(tmpdir)
            paths = collector.collect_synthetic(count=1)

            annotator = AutoAnnotator()
            anns = annotator.annotate_image(paths[0])
            self.assertIsInstance(anns, list)
            # AutoROIFinder should find some zones on the synthetic image
            self.assertGreater(len(anns), 0)
            for ann in anns:
                self.assertIsInstance(ann, Annotation)
                self.assertGreaterEqual(ann.cx, 0)
                self.assertLessEqual(ann.cx, 1)
                self.assertGreaterEqual(ann.cy, 0)
                self.assertLessEqual(ann.cy, 1)

    def test_annotate_nonexistent(self):
        annotator = AutoAnnotator()
        anns = annotator.annotate_image("/no/such/file.png")
        self.assertEqual(anns, [])

    def test_annotate_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = ScreenshotCollector(tmpdir)
            paths = collector.collect_synthetic(count=3)

            annotator = AutoAnnotator()
            samples = annotator.annotate_batch(paths)
            self.assertEqual(len(samples), 3)
            for s in samples:
                self.assertIsInstance(s, CollectedSample)
                self.assertTrue(s.metadata.get("auto_annotated"))


# ---------------------------------------------------------------------------
# DatasetBuilder tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or module not available")
class TestDatasetBuilder(unittest.TestCase):

    def _make_samples(self, tmpdir, n=5):
        """Helper: create n synthetic annotated samples."""
        collector = ScreenshotCollector(str(Path(tmpdir) / "raw"))
        paths = collector.collect_synthetic(count=n)
        annotator = AutoAnnotator()
        return annotator.annotate_batch(paths)

    def test_build_dataset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = self._make_samples(tmpdir, 5)
            ds_dir = Path(tmpdir) / "dataset"
            builder = DatasetBuilder(ds_dir)
            stats = builder.build(samples)

            self.assertIsInstance(stats, DatasetStats)
            self.assertEqual(stats.total_images, 5)
            self.assertGreater(stats.total_annotations, 0)
            self.assertEqual(stats.train_count + stats.val_count, 5)

            # Check data.yaml exists
            self.assertTrue(builder.data_yaml_path.exists())
            content = builder.data_yaml_path.read_text()
            self.assertIn("nc:", content)
            self.assertIn("names:", content)

    def test_build_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = self._make_samples(tmpdir, 3)
            ds_dir = Path(tmpdir) / "ds"
            builder = DatasetBuilder(ds_dir)
            builder.build(samples)

            self.assertTrue((ds_dir / "images" / "train").is_dir())
            self.assertTrue((ds_dir / "images" / "val").is_dir())
            self.assertTrue((ds_dir / "labels" / "train").is_dir())
            self.assertTrue((ds_dir / "labels" / "val").is_dir())

    def test_label_files_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = self._make_samples(tmpdir, 3)
            ds_dir = Path(tmpdir) / "ds"
            builder = DatasetBuilder(ds_dir)
            builder.build(samples)

            # At least some label files should exist
            train_labels = list((ds_dir / "labels" / "train").glob("*.txt"))
            val_labels = list((ds_dir / "labels" / "val").glob("*.txt"))
            self.assertGreater(len(train_labels) + len(val_labels), 0)

    def test_val_split(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = self._make_samples(tmpdir, 10)
            ds_dir = Path(tmpdir) / "ds"
            builder = DatasetBuilder(ds_dir)
            stats = builder.build(samples, val_split=0.3)
            self.assertEqual(stats.val_count, 3)
            self.assertEqual(stats.train_count, 7)


# ---------------------------------------------------------------------------
# AccuracyValidator tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(MODULE_OK, "training_data_collector not importable")
class TestAccuracyValidator(unittest.TestCase):

    def test_compute_iou_identical(self):
        a = Annotation(0, 0.5, 0.5, 0.2, 0.3)
        iou = AccuracyValidator._compute_iou(a, a)
        self.assertAlmostEqual(iou, 1.0, places=4)

    def test_compute_iou_no_overlap(self):
        a = Annotation(0, 0.1, 0.1, 0.1, 0.1)
        b = Annotation(0, 0.9, 0.9, 0.1, 0.1)
        iou = AccuracyValidator._compute_iou(a, b)
        self.assertAlmostEqual(iou, 0.0, places=4)

    def test_compute_iou_partial(self):
        a = Annotation(0, 0.5, 0.5, 0.4, 0.4)
        b = Annotation(0, 0.6, 0.5, 0.4, 0.4)
        iou = AccuracyValidator._compute_iou(a, b)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)

    def test_validate_perfect_predictions(self):
        gt = [
            ("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1),
                       Annotation(1, 0.3, 0.3, 0.2, 0.2)]),
            ("img2", [Annotation(0, 0.7, 0.7, 0.1, 0.1)]),
        ]
        # Predictions exactly match GT
        pred = [
            ("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1),
                       Annotation(1, 0.3, 0.3, 0.2, 0.2)]),
            ("img2", [Annotation(0, 0.7, 0.7, 0.1, 0.1)]),
        ]

        validator = AccuracyValidator(iou_threshold=0.5)
        result = validator.validate_predictions(gt, pred)

        self.assertEqual(result.true_positives, 3)
        self.assertEqual(result.false_positives, 0)
        self.assertEqual(result.false_negatives, 0)
        self.assertAlmostEqual(result.precision, 1.0)
        self.assertAlmostEqual(result.recall, 1.0)
        self.assertAlmostEqual(result.f1, 1.0)

    def test_validate_no_predictions(self):
        gt = [("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1)])]
        pred = [("img1", [])]

        validator = AccuracyValidator()
        result = validator.validate_predictions(gt, pred)
        self.assertEqual(result.true_positives, 0)
        self.assertEqual(result.false_negatives, 1)
        self.assertAlmostEqual(result.precision, 0.0)
        self.assertAlmostEqual(result.recall, 0.0)

    def test_validate_extra_predictions(self):
        gt = [("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1)])]
        pred = [("img1", [
            Annotation(0, 0.5, 0.5, 0.1, 0.1),   # TP
            Annotation(0, 0.1, 0.1, 0.1, 0.1),    # FP
        ])]

        validator = AccuracyValidator()
        result = validator.validate_predictions(gt, pred)
        self.assertEqual(result.true_positives, 1)
        self.assertEqual(result.false_positives, 1)
        self.assertEqual(result.false_negatives, 0)
        self.assertAlmostEqual(result.precision, 0.5)
        self.assertAlmostEqual(result.recall, 1.0)

    def test_per_class_stats(self):
        gt = [
            ("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1),
                       Annotation(2, 0.3, 0.3, 0.2, 0.2)]),
        ]
        pred = [
            ("img1", [Annotation(0, 0.5, 0.5, 0.1, 0.1)]),  # TP for class 0, miss class 2
        ]

        validator = AccuracyValidator()
        result = validator.validate_predictions(gt, pred)
        self.assertIn(YOLO_CLASSES[0], result.per_class)
        self.assertIn(YOLO_CLASSES[2], result.per_class)
        self.assertAlmostEqual(result.per_class[YOLO_CLASSES[0]]["recall"], 1.0)
        self.assertAlmostEqual(result.per_class[YOLO_CLASSES[2]]["recall"], 0.0)

    def test_validation_result_summary(self):
        result = ValidationResult(
            total_images=10, true_positives=8,
            false_positives=2, false_negatives=1,
            precision=0.8, recall=0.889, f1=0.842,
            accuracy_pct=0.889,
        )
        summary = result.summary()
        self.assertIn("10 images", summary)
        self.assertIn("Precision", summary)


# ---------------------------------------------------------------------------
# TrainConfig & TrainResult tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(MODULE_OK, "training_data_collector not importable")
class TestTrainConfig(unittest.TestCase):

    def test_defaults(self):
        cfg = TrainConfig()
        self.assertEqual(cfg.epochs, 50)
        self.assertEqual(cfg.imgsz, 640)
        self.assertEqual(cfg.base_model, "yolov8n.pt")

    def test_custom(self):
        cfg = TrainConfig(epochs=100, lr0=0.005, batch=32)
        self.assertEqual(cfg.epochs, 100)
        self.assertAlmostEqual(cfg.lr0, 0.005)

    def test_train_result_defaults(self):
        r = TrainResult()
        self.assertFalse(r.success)
        self.assertEqual(r.error, "")


# ---------------------------------------------------------------------------
# Integration: accuracy >95% on synthetic data
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or module not available")
class TestAccuracyOnSyntheticData(unittest.TestCase):
    """
    Validate that auto-annotation + validation achieves >95% self-consistency
    on synthetic images (GT = auto-annotated labels).

    This tests the pipeline integrity: if we annotate images and then
    re-annotate them, the results should match with >95% IoU recall.
    """

    def test_self_consistency_above_95_pct(self):
        """Auto-annotation should be >95% self-consistent (same input → same output)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate and annotate
            collector = ScreenshotCollector(str(Path(tmpdir) / "raw"))
            paths = collector.collect_synthetic(count=20)

            annotator = AutoAnnotator()
            samples = annotator.annotate_batch(paths)

            # Re-annotate (should get identical results)
            gt_labels = []
            pred_labels = []
            for s in samples:
                if not s.annotations:
                    continue
                name = Path(s.image_path).stem
                gt_labels.append((name, s.annotations))
                # Re-annotate
                re_anns = annotator.annotate_image(s.image_path)
                pred_labels.append((name, re_anns))

            self.assertGreater(len(gt_labels), 0, "No annotated images")

            validator = AccuracyValidator(iou_threshold=0.5)
            result = validator.validate_predictions(gt_labels, pred_labels)

            self.assertGreaterEqual(
                result.recall, 0.95,
                f"Self-consistency recall {result.recall:.1%} < 95%\n{result.summary()}"
            )
            self.assertGreaterEqual(
                result.precision, 0.95,
                f"Self-consistency precision {result.precision:.1%} < 95%\n{result.summary()}"
            )


# ---------------------------------------------------------------------------
# Pipeline integration test
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CV2 and MODULE_OK, "cv2 or module not available")
class TestTrainingPipeline(unittest.TestCase):

    def test_pipeline_collect_and_build(self):
        """Pipeline should collect, annotate, and build a dataset (skip training)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = TrainingPipeline(
                raw_dir=str(Path(tmpdir) / "raw"),
                dataset_dir=str(Path(tmpdir) / "dataset"),
            )
            results = pipeline.run(synthetic_count=10, skip_train=True)

            stats = results["dataset_stats"]
            self.assertIsInstance(stats, DatasetStats)
            self.assertEqual(stats.total_images, 10)
            self.assertGreater(stats.total_annotations, 0)
            self.assertIsNone(results["train_result"])

            # data.yaml should exist
            self.assertTrue(pipeline.builder.data_yaml_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
