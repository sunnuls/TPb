#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Training Data Collector — сбор и аннотация скриншотов для дообучения YOLOv8.

Phase 3 of vision_fragility.md.

Features:
- Автоматический захват скриншотов из покер-клиента (через live_capture.py)
- Авто-аннотация с помощью AutoROIFinder + CardDetector
- Генерация датасета в формате YOLO (images/ + labels/)
- Pipeline дообучения YOLOv8 (fine-tuning)
- Валидация точности на тестовой выборке

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import json
import logging
import os
import random
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except (ImportError, OSError):
    HAS_YOLO = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# YOLO class mapping for poker table regions
YOLO_CLASSES = [
    "hero_cards",      # 0
    "board_cards",     # 1
    "pot",             # 2
    "fold_btn",        # 3
    "check_btn",       # 4
    "call_btn",        # 5
    "raise_btn",       # 6
    "dealer_btn",      # 7
    "player_stack",    # 8
    "bet_amount",      # 9
    "bet_input",       # 10
    "table_felt",      # 11
    "card",            # 12
]

CLASS_TO_IDX = {name: i for i, name in enumerate(YOLO_CLASSES)}

# Mapping from AutoROIFinder zone names → YOLO class indices
ZONE_TO_CLASS = {
    "hero_card_1": "card",
    "hero_card_2": "card",
    "board_card_1": "card",
    "board_card_2": "card",
    "board_card_3": "card",
    "board_card_4": "card",
    "board_card_5": "card",
    "pot": "pot",
    "fold_button": "fold_btn",
    "check_button": "check_btn",
    "call_button": "call_btn",
    "raise_button": "raise_btn",
    "bet_input": "bet_input",
    "hero_stack": "player_stack",
}

# Add villain stacks
for _i in range(1, 6):
    ZONE_TO_CLASS[f"villain_{_i}_stack"] = "player_stack"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Annotation:
    """A single bounding-box annotation in YOLO format."""
    class_idx: int
    cx: float  # center x (normalised 0-1)
    cy: float  # center y (normalised 0-1)
    w: float   # width (normalised 0-1)
    h: float   # height (normalised 0-1)

    def to_yolo_line(self) -> str:
        return f"{self.class_idx} {self.cx:.6f} {self.cy:.6f} {self.w:.6f} {self.h:.6f}"

    @classmethod
    def from_bbox(cls, class_idx: int, x: int, y: int, bw: int, bh: int,
                  img_w: int, img_h: int) -> "Annotation":
        """Create from pixel bbox (x, y, w, h) and image dimensions."""
        cx = (x + bw / 2) / img_w
        cy = (y + bh / 2) / img_h
        w = bw / img_w
        h = bh / img_h
        return cls(class_idx=class_idx, cx=cx, cy=cy, w=w, h=h)


@dataclass
class CollectedSample:
    """A single collected screenshot with its annotations."""
    image_path: str
    annotations: List[Annotation] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @property
    def label_path(self) -> str:
        p = Path(self.image_path)
        return str(p.with_suffix(".txt"))


@dataclass
class DatasetStats:
    """Statistics for a collected dataset."""
    total_images: int = 0
    total_annotations: int = 0
    class_counts: Dict[str, int] = field(default_factory=dict)
    train_count: int = 0
    val_count: int = 0
    avg_annotations_per_image: float = 0.0


# ---------------------------------------------------------------------------
# Screenshot Collector
# ---------------------------------------------------------------------------

class ScreenshotCollector:
    """
    Collects screenshots from poker client windows.

    Uses window capture methods from the project (live_capture.py pattern).
    Can also accept pre-existing screenshot directories.
    """

    def __init__(self, output_dir: str | Path = "training_data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def collect_from_directory(self, source_dir: str | Path) -> List[str]:
        """Copy existing screenshots from *source_dir* into the raw collection."""
        source = Path(source_dir)
        if not source.is_dir():
            logger.warning("Source directory not found: %s", source)
            return []

        paths = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
            for fp in sorted(source.glob(ext)):
                dst = self.output_dir / f"screenshot_{self._count:05d}{fp.suffix}"
                shutil.copy2(fp, dst)
                paths.append(str(dst))
                self._count += 1

        logger.info("Collected %d screenshots from %s", len(paths), source)
        return paths

    def collect_synthetic(self, count: int = 100, width: int = 1920,
                          height: int = 1080) -> List[str]:
        """Generate synthetic poker table screenshots for training.

        This provides a baseline dataset when real screenshots are unavailable.
        """
        if not HAS_CV2:
            logger.warning("OpenCV not available — cannot generate synthetic data")
            return []

        paths = []
        felt_colors = [
            (40, 100, 50), (50, 70, 40), (100, 60, 30),
            (30, 40, 120), (80, 80, 30), (60, 80, 35),
        ]
        bg_colors = [(30, 30, 30), (15, 15, 20), (25, 25, 35)]

        for i in range(count):
            felt = random.choice(felt_colors)
            bg = random.choice(bg_colors)
            w = random.choice([1280, 1600, 1920])
            h = random.choice([720, 900, 1080])

            img = self._generate_table(w, h, felt, bg)
            fname = f"synthetic_{self._count:05d}.png"
            fpath = self.output_dir / fname
            cv2.imwrite(str(fpath), img)
            paths.append(str(fpath))
            self._count += 1

        logger.info("Generated %d synthetic screenshots", len(paths))
        return paths

    @staticmethod
    def _generate_table(w: int, h: int, felt_color: tuple,
                        bg_color: tuple) -> np.ndarray:
        """Generate a single synthetic poker table image."""
        img = np.full((h, w, 3), bg_color, dtype=np.uint8)

        # Table felt ellipse
        cx, cy = w // 2, h // 2
        rx, ry = int(w * 0.42), int(h * 0.40)
        cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, felt_color, -1)

        # Cards (board — center)
        card_w, card_h = max(50, int(w * 0.04)), int(max(50, int(w * 0.04)) * 1.4)
        gap = max(5, int(w * 0.005))
        num_board = random.choice([0, 3, 4, 5])
        if num_board > 0:
            total = num_board * card_w + (num_board - 1) * gap
            start_x = cx - total // 2
            for j in range(num_board):
                bx = start_x + j * (card_w + gap)
                by = cy - card_h // 2
                cv2.rectangle(img, (bx, by), (bx + card_w, by + card_h),
                              (240, 240, 240), -1)

        # Hero cards
        hero_y = cy + int(ry * 0.55)
        for j in range(2):
            hx = cx - card_w - 3 + j * (card_w + 6)
            cv2.rectangle(img, (hx, hero_y), (hx + card_w, hero_y + card_h),
                          (240, 240, 240), -1)

        # Buttons
        btn_w = max(70, int(w * 0.06))
        btn_h = max(30, int(h * 0.035))
        btn_y = cy + int(ry * 0.85)
        btn_colors = [(50, 180, 50), (50, 50, 200), (200, 180, 50), (50, 180, 50)]
        labels = ["Fold", "Check", "Call", "Raise"]
        total_btns = len(labels) * btn_w + 3 * int(w * 0.01)
        start_bx = cx - total_btns // 2
        for j, label in enumerate(labels):
            bx = start_bx + j * (btn_w + int(w * 0.01))
            cv2.rectangle(img, (bx, btn_y), (bx + btn_w, btn_y + btn_h),
                          btn_colors[j], -1)
            fs = max(0.35, btn_w / 200)
            cv2.putText(img, label, (bx + 5, btn_y + btn_h - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), 1)

        # Pot text
        cv2.putText(img, f"Pot: ${random.randint(10, 5000)}", (cx - 60, cy - int(ry * 0.35)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return img


# ---------------------------------------------------------------------------
# Auto-Annotator
# ---------------------------------------------------------------------------

class AutoAnnotator:
    """
    Automatically annotates poker screenshots using AutoROIFinder.

    Converts detected ROI zones into YOLO format annotations.
    """

    def __init__(self):
        self._finder = None

    def _get_finder(self):
        if self._finder is None:
            try:
                from launcher.vision.auto_roi_finder import AutoROIFinder
                self._finder = AutoROIFinder(use_ocr=False, use_templates=False)
            except Exception as e:
                logger.warning("Could not init AutoROIFinder: %s", e)
        return self._finder

    def annotate_image(self, image_path: str) -> List[Annotation]:
        """Auto-annotate a single image file."""
        if not HAS_CV2:
            return []

        try:
            img = cv2.imread(image_path)
        except Exception:
            img = None
        if img is None:
            logger.warning("Cannot read image: %s", image_path)
            return []

        h, w = img.shape[:2]
        annotations = []

        finder = self._get_finder()
        if finder is None:
            return annotations

        result = finder.find_rois(img)

        for zone_name, (zx, zy, zw, zh) in result.zones.items():
            yolo_class = ZONE_TO_CLASS.get(zone_name)
            if yolo_class is None:
                continue
            class_idx = CLASS_TO_IDX.get(yolo_class)
            if class_idx is None:
                continue
            ann = Annotation.from_bbox(class_idx, zx, zy, zw, zh, w, h)
            annotations.append(ann)

        return annotations

    def annotate_batch(self, image_paths: List[str]) -> List[CollectedSample]:
        """Annotate a batch of images, returning CollectedSample list."""
        samples = []
        for path in image_paths:
            anns = self.annotate_image(path)
            sample = CollectedSample(
                image_path=path,
                annotations=anns,
                metadata={"auto_annotated": True, "ann_count": len(anns)},
            )
            samples.append(sample)
        return samples


# ---------------------------------------------------------------------------
# Dataset Builder — converts samples into YOLO dataset structure
# ---------------------------------------------------------------------------

class DatasetBuilder:
    """
    Builds a YOLO-format dataset from collected samples.

    Output structure::

        dataset_dir/
            data.yaml
            images/
                train/
                val/
            labels/
                train/
                val/
    """

    def __init__(self, dataset_dir: str | Path = "training_data/dataset"):
        self.dataset_dir = Path(dataset_dir)

    def build(self, samples: List[CollectedSample],
              val_split: float = 0.2,
              shuffle: bool = True) -> DatasetStats:
        """Write samples to YOLO dataset directory.

        Returns DatasetStats with counts.
        """
        # Create dirs
        for split in ("train", "val"):
            (self.dataset_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.dataset_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

        if shuffle:
            samples = list(samples)
            random.shuffle(samples)

        n_val = max(1, int(len(samples) * val_split))
        val_samples = samples[:n_val]
        train_samples = samples[n_val:]

        stats = DatasetStats()
        stats.total_images = len(samples)
        stats.train_count = len(train_samples)
        stats.val_count = len(val_samples)

        for split, subset in [("train", train_samples), ("val", val_samples)]:
            for sample in subset:
                src = Path(sample.image_path)
                if not src.exists():
                    continue
                dst_img = self.dataset_dir / "images" / split / src.name
                shutil.copy2(src, dst_img)

                # Write label file
                label_name = src.stem + ".txt"
                dst_label = self.dataset_dir / "labels" / split / label_name
                with open(dst_label, "w") as f:
                    for ann in sample.annotations:
                        f.write(ann.to_yolo_line() + "\n")
                        cls_name = YOLO_CLASSES[ann.class_idx] if ann.class_idx < len(YOLO_CLASSES) else "unknown"
                        stats.class_counts[cls_name] = stats.class_counts.get(cls_name, 0) + 1
                        stats.total_annotations += 1

        if stats.total_images > 0:
            stats.avg_annotations_per_image = stats.total_annotations / stats.total_images

        # Write data.yaml
        self._write_data_yaml()

        logger.info("Dataset built: %d images (%d train, %d val), %d annotations",
                     stats.total_images, stats.train_count, stats.val_count,
                     stats.total_annotations)
        return stats

    def _write_data_yaml(self):
        """Write data.yaml config for YOLO training."""
        yaml_path = self.dataset_dir / "data.yaml"
        lines = [
            f"path: {self.dataset_dir.resolve()}",
            "train: images/train",
            "val: images/val",
            "",
            f"nc: {len(YOLO_CLASSES)}",
            f"names: {YOLO_CLASSES}",
        ]
        yaml_path.write_text("\n".join(lines), encoding="utf-8")

    @property
    def data_yaml_path(self) -> Path:
        return self.dataset_dir / "data.yaml"


# ---------------------------------------------------------------------------
# YOLOv8 Trainer — fine-tuning pipeline
# ---------------------------------------------------------------------------

@dataclass
class TrainConfig:
    """Configuration for YOLOv8 fine-tuning."""
    base_model: str = "yolov8n.pt"
    epochs: int = 50
    imgsz: int = 640
    batch: int = 16
    lr0: float = 0.01
    patience: int = 10
    device: str = ""        # "" = auto, "cpu", "0" (GPU 0)
    project: str = "training_data/runs"
    name: str = "poker_finetune"
    exist_ok: bool = True


@dataclass
class TrainResult:
    """Result from a training run."""
    best_model_path: str = ""
    final_map50: float = 0.0
    final_map50_95: float = 0.0
    epochs_completed: int = 0
    success: bool = False
    error: str = ""


class YOLOTrainer:
    """Fine-tunes YOLOv8 on a custom poker dataset."""

    def __init__(self, config: TrainConfig | None = None):
        self.config = config or TrainConfig()

    def train(self, data_yaml: str | Path) -> TrainResult:
        """Run the fine-tuning pipeline.

        Args:
            data_yaml: Path to dataset data.yaml

        Returns:
            TrainResult with model path and metrics
        """
        if not HAS_YOLO:
            return TrainResult(success=False, error="ultralytics not installed")

        data_yaml = str(data_yaml)
        result = TrainResult()

        try:
            model = YOLO(self.config.base_model)
            metrics = model.train(
                data=data_yaml,
                epochs=self.config.epochs,
                imgsz=self.config.imgsz,
                batch=self.config.batch,
                lr0=self.config.lr0,
                patience=self.config.patience,
                device=self.config.device or None,
                project=self.config.project,
                name=self.config.name,
                exist_ok=self.config.exist_ok,
                verbose=True,
            )

            # Extract results
            run_dir = Path(self.config.project) / self.config.name
            best_pt = run_dir / "weights" / "best.pt"
            if best_pt.exists():
                result.best_model_path = str(best_pt)

            # Try to get mAP from metrics
            if hasattr(metrics, "results_dict"):
                rd = metrics.results_dict
                result.final_map50 = rd.get("metrics/mAP50(B)", 0.0)
                result.final_map50_95 = rd.get("metrics/mAP50-95(B)", 0.0)
            result.epochs_completed = self.config.epochs
            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False
            logger.error("Training failed: %s", e)

        return result


# ---------------------------------------------------------------------------
# Accuracy Validator
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of accuracy validation."""
    total_images: int = 0
    total_gt_boxes: int = 0
    total_pred_boxes: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    accuracy_pct: float = 0.0
    iou_threshold: float = 0.5
    per_class: Dict[str, Dict] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Validation: {self.total_images} images",
            f"  GT boxes: {self.total_gt_boxes}, Pred boxes: {self.total_pred_boxes}",
            f"  TP={self.true_positives} FP={self.false_positives} FN={self.false_negatives}",
            f"  Precision: {self.precision:.1%}",
            f"  Recall:    {self.recall:.1%}",
            f"  F1:        {self.f1:.1%}",
            f"  Accuracy:  {self.accuracy_pct:.1%}",
        ]
        for cls_name, m in sorted(self.per_class.items()):
            lines.append(f"  [{cls_name}] P={m.get('precision', 0):.1%} "
                         f"R={m.get('recall', 0):.1%} F1={m.get('f1', 0):.1%}")
        return "\n".join(lines)


class AccuracyValidator:
    """
    Validates model accuracy against ground-truth labels.

    Measures IoU-based matching between predictions and GT annotations.
    """

    def __init__(self, iou_threshold: float = 0.5):
        self.iou_threshold = iou_threshold

    def validate_model(self, model_path: str, data_yaml: str,
                       split: str = "val") -> ValidationResult:
        """Validate a trained YOLO model against the val split."""
        if not HAS_YOLO:
            return ValidationResult()

        model = YOLO(model_path)
        metrics = model.val(data=data_yaml, split=split, verbose=False)

        result = ValidationResult(iou_threshold=self.iou_threshold)
        if hasattr(metrics, "results_dict"):
            rd = metrics.results_dict
            result.accuracy_pct = rd.get("metrics/mAP50(B)", 0.0)
            result.precision = rd.get("metrics/precision(B)", 0.0)
            result.recall = rd.get("metrics/recall(B)", 0.0)
            if result.precision + result.recall > 0:
                result.f1 = 2 * result.precision * result.recall / (result.precision + result.recall)

        return result

    def validate_predictions(
        self,
        gt_labels: List[Tuple[str, List[Annotation]]],
        pred_labels: List[Tuple[str, List[Annotation]]],
    ) -> ValidationResult:
        """Validate raw prediction annotations against ground truth.

        Args:
            gt_labels: list of (image_name, [Annotation, ...])
            pred_labels: list of (image_name, [Annotation, ...])

        Returns:
            ValidationResult
        """
        gt_map = {name: anns for name, anns in gt_labels}
        pred_map = {name: anns for name, anns in pred_labels}

        result = ValidationResult(iou_threshold=self.iou_threshold)
        result.total_images = len(gt_map)

        per_class_tp: Dict[int, int] = {}
        per_class_fp: Dict[int, int] = {}
        per_class_fn: Dict[int, int] = {}

        for img_name, gt_anns in gt_map.items():
            pred_anns = pred_map.get(img_name, [])
            result.total_gt_boxes += len(gt_anns)
            result.total_pred_boxes += len(pred_anns)

            matched_gt = set()
            matched_pred = set()

            for pi, pred in enumerate(pred_anns):
                best_iou = 0.0
                best_gi = -1
                for gi, gt in enumerate(gt_anns):
                    if gi in matched_gt:
                        continue
                    if pred.class_idx != gt.class_idx:
                        continue
                    iou = self._compute_iou(pred, gt)
                    if iou > best_iou:
                        best_iou = iou
                        best_gi = gi

                if best_iou >= self.iou_threshold and best_gi >= 0:
                    result.true_positives += 1
                    matched_gt.add(best_gi)
                    matched_pred.add(pi)
                    cls = pred.class_idx
                    per_class_tp[cls] = per_class_tp.get(cls, 0) + 1
                else:
                    result.false_positives += 1
                    cls = pred.class_idx
                    per_class_fp[cls] = per_class_fp.get(cls, 0) + 1

            for gi, gt in enumerate(gt_anns):
                if gi not in matched_gt:
                    result.false_negatives += 1
                    cls = gt.class_idx
                    per_class_fn[cls] = per_class_fn.get(cls, 0) + 1

        # Aggregate
        tp, fp, fn = result.true_positives, result.false_positives, result.false_negatives
        result.precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        result.recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if result.precision + result.recall > 0:
            result.f1 = 2 * result.precision * result.recall / (result.precision + result.recall)
        result.accuracy_pct = result.recall  # recall ≈ detection accuracy

        # Per-class stats
        all_classes = set(per_class_tp) | set(per_class_fp) | set(per_class_fn)
        for cls in all_classes:
            tp_c = per_class_tp.get(cls, 0)
            fp_c = per_class_fp.get(cls, 0)
            fn_c = per_class_fn.get(cls, 0)
            p = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
            r = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
            f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            cls_name = YOLO_CLASSES[cls] if cls < len(YOLO_CLASSES) else f"class_{cls}"
            result.per_class[cls_name] = {"precision": p, "recall": r, "f1": f}

        return result

    @staticmethod
    def _compute_iou(a: Annotation, b: Annotation) -> float:
        """Compute IoU between two normalised YOLO annotations."""
        ax1 = a.cx - a.w / 2
        ay1 = a.cy - a.h / 2
        ax2 = a.cx + a.w / 2
        ay2 = a.cy + a.h / 2

        bx1 = b.cx - b.w / 2
        by1 = b.cy - b.h / 2
        bx2 = b.cx + b.w / 2
        by2 = b.cy + b.h / 2

        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)

        area_a = a.w * a.h
        area_b = b.w * b.h
        union = area_a + area_b - inter

        return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

class TrainingPipeline:
    """
    End-to-end pipeline: collect → annotate → build dataset → train → validate.
    """

    def __init__(
        self,
        raw_dir: str = "training_data/raw",
        dataset_dir: str = "training_data/dataset",
        train_config: TrainConfig | None = None,
    ):
        self.collector = ScreenshotCollector(raw_dir)
        self.annotator = AutoAnnotator()
        self.builder = DatasetBuilder(dataset_dir)
        self.trainer = YOLOTrainer(train_config)
        self.validator = AccuracyValidator()

    def run(
        self,
        synthetic_count: int = 200,
        source_dirs: List[str] | None = None,
        skip_train: bool = False,
    ) -> Dict:
        """Run the full pipeline.

        Returns dict with dataset_stats, train_result, validation_result.
        """
        logger.info("=== Training Pipeline START ===")

        # 1. Collect screenshots
        all_paths: List[str] = []
        if source_dirs:
            for sd in source_dirs:
                all_paths += self.collector.collect_from_directory(sd)
        if synthetic_count > 0:
            all_paths += self.collector.collect_synthetic(count=synthetic_count)

        logger.info("Collected %d total screenshots", len(all_paths))

        # 2. Auto-annotate
        samples = self.annotator.annotate_batch(all_paths)
        annotated = [s for s in samples if s.annotations]
        logger.info("Annotated %d / %d images", len(annotated), len(samples))

        # 3. Build dataset
        stats = self.builder.build(annotated)
        logger.info("Dataset: %s", json.dumps(stats.class_counts, indent=2))

        result = {
            "dataset_stats": stats,
            "train_result": None,
            "validation_result": None,
        }

        # 4. Train (optional)
        if not skip_train and HAS_YOLO:
            train_result = self.trainer.train(self.builder.data_yaml_path)
            result["train_result"] = train_result

            # 5. Validate
            if train_result.success and train_result.best_model_path:
                val_result = self.validator.validate_model(
                    train_result.best_model_path,
                    str(self.builder.data_yaml_path),
                )
                result["validation_result"] = val_result
                logger.info("Validation mAP50: %.1f%%", val_result.accuracy_pct * 100)

        logger.info("=== Training Pipeline END ===")
        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Poker Training Data Collector & Trainer")
    parser.add_argument("--collect-synthetic", type=int, default=200,
                        help="Number of synthetic screenshots to generate")
    parser.add_argument("--source-dir", type=str, nargs="*",
                        help="Directories with existing screenshots")
    parser.add_argument("--skip-train", action="store_true",
                        help="Only collect and annotate, skip training")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--base-model", type=str, default="yolov8n.pt",
                        help="Base YOLO model for fine-tuning")

    args = parser.parse_args()

    config = TrainConfig(
        epochs=args.epochs,
        base_model=args.base_model,
    )

    pipeline = TrainingPipeline(train_config=config)
    results = pipeline.run(
        synthetic_count=args.collect_synthetic,
        source_dirs=args.source_dir,
        skip_train=args.skip_train,
    )

    print("\n=== RESULTS ===")
    stats = results["dataset_stats"]
    print(f"Dataset: {stats.total_images} images, {stats.total_annotations} annotations")
    print(f"  Train: {stats.train_count}, Val: {stats.val_count}")
    print(f"  Classes: {stats.class_counts}")

    if results["train_result"]:
        tr = results["train_result"]
        print(f"\nTraining: {'SUCCESS' if tr.success else 'FAILED'}")
        if tr.success:
            print(f"  Best model: {tr.best_model_path}")
            print(f"  mAP50: {tr.final_map50:.1%}")

    if results["validation_result"]:
        vr = results["validation_result"]
        print(f"\nValidation:\n{vr.summary()}")
