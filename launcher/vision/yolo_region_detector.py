"""
YOLOv8-based poker table region detector.

Phase 3 of vision_fragility.md.

Detects semantic regions on a poker table screenshot:
    hero_cards, board_cards, pot, fold_btn, check_btn,
    call_btn, raise_btn, dealer_btn, player_stack (×N)

Works as a drop-in replacement / enhancement for the CV-based
AutoROIFinder (Phase 1).  Falls back to AutoROIFinder when no
trained YOLO model is available.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except (ImportError, OSError, Exception) as _yolo_err:
    YOLO_AVAILABLE = False
    YOLO = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Region classes (same order used by the YOLO training dataset)
# ---------------------------------------------------------------------------

REGION_CLASSES = [
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
]

CLASS_TO_IDX = {name: i for i, name in enumerate(REGION_CLASSES)}
IDX_TO_CLASS = {i: name for i, name in enumerate(REGION_CLASSES)}

# Mapping from YOLO region names → standard ROI zone names
REGION_TO_ZONE = {
    "hero_cards":   ["hero_card_1", "hero_card_2"],
    "board_cards":  [f"board_card_{i}" for i in range(1, 6)],
    "pot":          ["pot"],
    "fold_btn":     ["fold_button"],
    "check_btn":    ["check_button"],
    "call_btn":     ["call_button"],
    "raise_btn":    ["raise_button"],
    "bet_input":    ["bet_input"],
    "player_stack": ["hero_stack"] + [f"villain_{i}_stack" for i in range(1, 6)],
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RegionDetection:
    """Single detected region on the poker table."""
    class_name: str
    class_id: int
    bbox: Tuple[int, int, int, int]   # x, y, w, h (absolute pixels)
    confidence: float
    metadata: Dict = field(default_factory=dict)

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]


@dataclass
class RegionDetectionResult:
    """Full result of region detection on one image."""
    detections: List[RegionDetection]
    zones: Dict[str, Tuple[int, int, int, int]]   # standard zone → bbox
    model_used: str           # "yolo", "cv_fallback", "hybrid"
    confidence: float         # average confidence
    elapsed_ms: float = 0.0

    @property
    def count(self) -> int:
        return len(self.detections)

    def get_detections(self, class_name: str) -> List[RegionDetection]:
        return [d for d in self.detections if d.class_name == class_name]

    def summary(self) -> str:
        lines = [
            f"RegionDetection: {self.count} regions, "
            f"model={self.model_used}, conf={self.confidence:.0%}, "
            f"{self.elapsed_ms:.0f}ms",
        ]
        by_class: Dict[str, int] = {}
        for d in self.detections:
            by_class[d.class_name] = by_class.get(d.class_name, 0) + 1
        for cls, cnt in sorted(by_class.items()):
            lines.append(f"  {cls}: {cnt}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model weight search paths (priority order)
# ---------------------------------------------------------------------------

_MODEL_SEARCH_PATHS = [
    "weights/regions_best.pt",
    "weights/yolo_regions.pt",
    "weights/best_regions.pt",
    "online_poker_training/yolov8_regions/weights/best.pt",
]


# ---------------------------------------------------------------------------
# YOLORegionDetector
# ---------------------------------------------------------------------------

class YOLORegionDetector:
    """
    Detects poker table regions using YOLOv8 with CV fallback.

    Pipeline:
        1. Try YOLOv8 inference (if trained model available)
        2. Fallback to AutoROIFinder (Phase 1 CV-based detection)
        3. Merge results when both are available (hybrid mode)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        img_size: int = 640,
        enable_fallback: bool = True,
    ):
        """
        Args:
            model_path: explicit path to YOLO .pt weights
            confidence_threshold: minimum detection confidence
            iou_threshold: NMS IoU threshold
            img_size: inference image size
            enable_fallback: use AutoROIFinder as fallback
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.img_size = img_size
        self.enable_fallback = enable_fallback

        # Try to load YOLO model
        self._model = None
        self._model_path = None
        self._load_model(model_path)

        # Lazy-load CV fallback
        self._cv_finder = None

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self, explicit_path: Optional[str]) -> None:
        if not YOLO_AVAILABLE:
            logger.info("ultralytics not installed — YOLO unavailable, using CV fallback")
            return

        paths = [explicit_path] if explicit_path else []
        paths += _MODEL_SEARCH_PATHS

        for p in paths:
            if p and Path(p).is_file():
                try:
                    self._model = YOLO(p)
                    self._model_path = p
                    logger.info("Loaded YOLO region model: %s", p)
                    return
                except Exception as e:
                    logger.warning("Failed to load %s: %s", p, e)

        logger.info("No trained region model found — will use CV fallback")

    @property
    def yolo_available(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> RegionDetectionResult:
        """
        Detect poker table regions in an image.

        Args:
            image: BGR numpy array (screenshot)

        Returns:
            RegionDetectionResult with all detections and zone mappings
        """
        t0 = time.perf_counter()
        h, w = image.shape[:2]

        yolo_dets: List[RegionDetection] = []
        cv_zones: Dict[str, Tuple[int, int, int, int]] = {}

        # --- Strategy 1: YOLO ---
        if self.yolo_available:
            yolo_dets = self._yolo_detect(image)

        # --- Strategy 2: CV Fallback ---
        if self.enable_fallback and (not yolo_dets or len(yolo_dets) < 3):
            cv_zones = self._cv_detect(image)

        # --- Merge ---
        if yolo_dets and cv_zones:
            model_used = "hybrid"
            detections = yolo_dets
            zones = self._merge_zones(yolo_dets, cv_zones, w, h)
        elif yolo_dets:
            model_used = "yolo"
            detections = yolo_dets
            zones = self._detections_to_zones(yolo_dets, w, h)
        else:
            model_used = "cv_fallback"
            detections = self._zones_to_detections(cv_zones)
            zones = cv_zones

        avg_conf = (
            sum(d.confidence for d in detections) / len(detections)
            if detections else 0.0
        )
        elapsed = (time.perf_counter() - t0) * 1000

        return RegionDetectionResult(
            detections=detections,
            zones=zones,
            model_used=model_used,
            confidence=avg_conf,
            elapsed_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # YOLO inference
    # ------------------------------------------------------------------

    def _yolo_detect(self, image: np.ndarray) -> List[RegionDetection]:
        """Run YOLO inference and return region detections."""
        detections: List[RegionDetection] = []
        try:
            results = self._model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.img_size,
                verbose=False,
            )
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)

                    cls_name = IDX_TO_CLASS.get(cls_id, f"unknown_{cls_id}")

                    detections.append(RegionDetection(
                        class_name=cls_name,
                        class_id=cls_id,
                        bbox=(x, y, w, h),
                        confidence=conf,
                    ))
        except Exception as e:
            logger.error("YOLO inference failed: %s", e)

        return detections

    # ------------------------------------------------------------------
    # CV Fallback (AutoROIFinder from Phase 1)
    # ------------------------------------------------------------------

    def _cv_detect(self, image: np.ndarray) -> Dict[str, Tuple[int, int, int, int]]:
        """Use AutoROIFinder as fallback."""
        if self._cv_finder is None:
            from launcher.vision.auto_roi_finder import AutoROIFinder
            self._cv_finder = AutoROIFinder(use_ocr=False)

        try:
            result = self._cv_finder.find_rois(image)
            return result.zones
        except Exception as e:
            logger.error("CV fallback failed: %s", e)
            return {}

    # ------------------------------------------------------------------
    # Zone mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _detections_to_zones(
        detections: List[RegionDetection],
        img_w: int,
        img_h: int,
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Convert YOLO detections to standard zone dict."""
        zones: Dict[str, Tuple[int, int, int, int]] = {}

        # Group detections by class
        by_class: Dict[str, List[RegionDetection]] = {}
        for d in detections:
            by_class.setdefault(d.class_name, []).append(d)

        for cls_name, dets in by_class.items():
            zone_names = REGION_TO_ZONE.get(cls_name, [cls_name])

            if cls_name == "hero_cards" and dets:
                # Single bbox covers both cards — split into two halves
                best = max(dets, key=lambda d: d.confidence)
                x, y, w, h = best.bbox
                half_w = w // 2
                zones["hero_card_1"] = (x, y, half_w, h)
                zones["hero_card_2"] = (x + half_w, y, w - half_w, h)

            elif cls_name == "board_cards" and dets:
                best = max(dets, key=lambda d: d.confidence)
                x, y, w, h = best.bbox
                card_w = w // 5
                for i in range(5):
                    zones[f"board_card_{i + 1}"] = (x + i * card_w, y, card_w, h)

            elif cls_name == "player_stack":
                # Sort by angle from center
                sorted_dets = sorted(dets, key=lambda d: d.center[1], reverse=True)
                if sorted_dets:
                    zones["hero_stack"] = sorted_dets[0].bbox
                for i, d in enumerate(sorted_dets[1:6], start=1):
                    zones[f"villain_{i}_stack"] = d.bbox

            elif len(zone_names) == 1:
                if dets:
                    best = max(dets, key=lambda d: d.confidence)
                    zones[zone_names[0]] = best.bbox
            else:
                for i, d in enumerate(dets):
                    if i < len(zone_names):
                        zones[zone_names[i]] = d.bbox

        return zones

    @staticmethod
    def _merge_zones(
        yolo_dets: List[RegionDetection],
        cv_zones: Dict[str, Tuple[int, int, int, int]],
        img_w: int,
        img_h: int,
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Merge YOLO detections with CV zones, preferring YOLO."""
        yolo_zones = YOLORegionDetector._detections_to_zones(yolo_dets, img_w, img_h)
        merged = dict(cv_zones)
        merged.update(yolo_zones)  # YOLO takes priority
        return merged

    @staticmethod
    def _zones_to_detections(
        zones: Dict[str, Tuple[int, int, int, int]],
    ) -> List[RegionDetection]:
        """Convert zone dict back to RegionDetection list (for CV fallback)."""
        detections: List[RegionDetection] = []
        for name, bbox in zones.items():
            # Map zone name back to region class
            cls_name = "unknown"
            for region, zone_list in REGION_TO_ZONE.items():
                if name in zone_list:
                    cls_name = region
                    break

            detections.append(RegionDetection(
                class_name=cls_name,
                class_id=CLASS_TO_IDX.get(cls_name, -1),
                bbox=bbox,
                confidence=0.7,  # CV-based estimate
            ))
        return detections

    # ------------------------------------------------------------------
    # Utility: compute IoU
    # ------------------------------------------------------------------

    @staticmethod
    def iou(
        box1: Tuple[int, int, int, int],
        box2: Tuple[int, int, int, int],
    ) -> float:
        """Compute IoU between two (x, y, w, h) boxes."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        xa = max(x1, x2)
        ya = max(y1, y2)
        xb = min(x1 + w1, x2 + w2)
        yb = min(y1 + h1, y2 + h2)
        inter = max(0, xb - xa) * max(0, yb - ya)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union else 0.0

    # ------------------------------------------------------------------
    # Accuracy evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_accuracy(
        predictions: Dict[str, Tuple[int, int, int, int]],
        ground_truth: Dict[str, Tuple[int, int, int, int]],
        iou_threshold: float = 0.3,
    ) -> Dict[str, float]:
        """
        Evaluate detection accuracy against ground truth.

        Args:
            predictions: detected zones
            ground_truth: expected zones
            iou_threshold: minimum IoU to count as correct

        Returns:
            dict with 'accuracy', 'precision', 'recall', 'avg_iou',
            and per-zone results
        """
        tp, fp, fn = 0, 0, 0
        ious: List[float] = []
        per_zone: Dict[str, Dict] = {}

        for name, gt_box in ground_truth.items():
            if name in predictions:
                iou_val = YOLORegionDetector.iou(predictions[name], gt_box)
                ious.append(iou_val)
                if iou_val >= iou_threshold:
                    tp += 1
                    per_zone[name] = {"status": "correct", "iou": iou_val}
                else:
                    fp += 1
                    fn += 1
                    per_zone[name] = {"status": "misaligned", "iou": iou_val}
            else:
                fn += 1
                per_zone[name] = {"status": "missed", "iou": 0.0}

        # Extra predictions not in GT
        for name in predictions:
            if name not in ground_truth:
                fp += 1

        total = tp + fn
        accuracy = tp / total if total else 0.0
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        avg_iou = sum(ious) / len(ious) if ious else 0.0

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "avg_iou": avg_iou,
            "tp": tp, "fp": fp, "fn": fn,
            "per_zone": per_zone,
        }


# ---------------------------------------------------------------------------
# Dataset generation for YOLO training
# ---------------------------------------------------------------------------

class RegionDatasetGenerator:
    """
    Generates synthetic poker table screenshots with YOLO-format annotations.

    Produces labeled images for training YOLOv8 to detect poker table regions.
    Each image has a corresponding .txt label file with:
        class_id center_x center_y width height  (normalized 0-1)
    """

    def __init__(self, output_dir: str = "training_data/regions_dataset"):
        self.output_dir = Path(output_dir)

    def generate(
        self,
        count: int = 1000,
        split: Tuple[float, float, float] = (0.7, 0.2, 0.1),
    ) -> Dict[str, int]:
        """
        Generate a complete dataset.

        Args:
            count: total number of images
            split: (train, val, test) fractions

        Returns:
            dict with counts per split
        """
        if not CV_AVAILABLE:
            raise RuntimeError("OpenCV required for dataset generation")

        # Create directory structure
        for subset in ("train", "valid", "test"):
            (self.output_dir / subset / "images").mkdir(parents=True, exist_ok=True)
            (self.output_dir / subset / "labels").mkdir(parents=True, exist_ok=True)

        # Split counts
        n_train = int(count * split[0])
        n_val = int(count * split[1])
        n_test = count - n_train - n_val
        splits = (
            [("train", n_train), ("valid", n_val), ("test", n_test)]
        )

        generated = {}
        idx = 0
        for subset, n in splits:
            for i in range(n):
                img, annotations = self._generate_one(idx)
                fname = f"table_{idx:05d}"

                # Save image
                img_path = self.output_dir / subset / "images" / f"{fname}.jpg"
                cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])

                # Save label
                lbl_path = self.output_dir / subset / "labels" / f"{fname}.txt"
                with open(lbl_path, "w") as f:
                    for ann in annotations:
                        f.write(
                            f"{ann['class_id']} "
                            f"{ann['cx']:.6f} {ann['cy']:.6f} "
                            f"{ann['w']:.6f} {ann['h']:.6f}\n"
                        )
                idx += 1
            generated[subset] = n

        # Write data.yaml
        self._write_data_yaml()

        logger.info(
            "Dataset generated: %d images (%s)",
            count,
            ", ".join(f"{k}={v}" for k, v in generated.items()),
        )
        return generated

    def _generate_one(self, seed: int) -> Tuple[np.ndarray, List[Dict]]:
        """Generate one annotated synthetic table image."""
        rng = np.random.RandomState(seed)

        # Random resolution
        w = rng.choice([800, 1024, 1280, 1600, 1920, 2560])
        h = rng.choice([600, 720, 768, 900, 1080])

        # Random colours
        bg = tuple(int(x) for x in rng.randint(10, 50, 3))
        felt_hue = rng.randint(0, 180)
        felt_sat = rng.randint(40, 200)
        felt_val = rng.randint(30, 160)
        felt_hsv = np.array([[[felt_hue, felt_sat, felt_val]]], dtype=np.uint8)
        felt_bgr = tuple(int(x) for x in cv2.cvtColor(felt_hsv, cv2.COLOR_HSV2BGR)[0, 0])

        img = np.full((h, w, 3), bg, dtype=np.uint8)
        annotations: List[Dict] = []

        # Table felt (ellipse)
        cx, cy = w // 2, h // 2
        rx = int(w * rng.uniform(0.35, 0.45))
        ry = int(h * rng.uniform(0.32, 0.42))
        cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, felt_bgr, -1)

        # Table felt annotation
        tx, ty = max(0, cx - rx), max(0, cy - ry)
        tw, th = min(w, 2 * rx), min(h, 2 * ry)
        annotations.append(self._make_ann(CLASS_TO_IDX["table_felt"], tx, ty, tw, th, w, h))

        # Hero cards region
        hc_w = int(w * rng.uniform(0.08, 0.14))
        hc_h = int(h * rng.uniform(0.09, 0.14))
        hc_x = cx - hc_w // 2 + int(rng.uniform(-w * 0.02, w * 0.02))
        hc_y = cy + int(ry * rng.uniform(0.45, 0.65))
        self._draw_region(img, hc_x, hc_y, hc_w, hc_h, (240, 240, 240), rng)
        annotations.append(self._make_ann(CLASS_TO_IDX["hero_cards"], hc_x, hc_y, hc_w, hc_h, w, h))

        # Board cards region
        bc_w = int(w * rng.uniform(0.20, 0.30))
        bc_h = int(h * rng.uniform(0.08, 0.12))
        bc_x = cx - bc_w // 2 + int(rng.uniform(-w * 0.01, w * 0.01))
        bc_y = cy - int(ry * rng.uniform(0.05, 0.15))
        self._draw_region(img, bc_x, bc_y, bc_w, bc_h, (230, 230, 230), rng)
        annotations.append(self._make_ann(CLASS_TO_IDX["board_cards"], bc_x, bc_y, bc_w, bc_h, w, h))

        # Pot display
        pot_w = int(w * rng.uniform(0.08, 0.14))
        pot_h = int(h * rng.uniform(0.03, 0.05))
        pot_x = cx - pot_w // 2
        pot_y = cy - int(ry * rng.uniform(0.25, 0.40))
        cv2.rectangle(img, (pot_x, pot_y), (pot_x + pot_w, pot_y + pot_h), (200, 200, 200), -1)
        cv2.putText(img, f"${rng.randint(10, 9999)}", (pot_x + 4, pot_y + pot_h - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        annotations.append(self._make_ann(CLASS_TO_IDX["pot"], pot_x, pot_y, pot_w, pot_h, w, h))

        # Action buttons
        btn_w = int(w * rng.uniform(0.05, 0.08))
        btn_h = int(h * rng.uniform(0.03, 0.05))
        btn_y = cy + int(ry * rng.uniform(0.75, 0.92))
        btn_gap = int(w * rng.uniform(0.005, 0.015))
        btn_colors = [(0, 0, 180), (0, 150, 0), (0, 150, 0), (180, 100, 0)]
        btn_names = ["fold_btn", "check_btn", "call_btn", "raise_btn"]
        total_btn_w = len(btn_names) * btn_w + (len(btn_names) - 1) * btn_gap
        btn_start_x = cx - total_btn_w // 2
        for i, (bname, bcolor) in enumerate(zip(btn_names, btn_colors)):
            bx = btn_start_x + i * (btn_w + btn_gap)
            cv2.rectangle(img, (bx, btn_y), (bx + btn_w, btn_y + btn_h), bcolor, -1)
            annotations.append(self._make_ann(CLASS_TO_IDX[bname], bx, btn_y, btn_w, btn_h, w, h))

        # Player stacks (2-6 positions around table)
        n_stacks = rng.randint(2, 7)
        import math
        for si in range(n_stacks):
            angle = (360 / n_stacks) * si + rng.uniform(-15, 15)
            rad = math.radians(angle)
            sx = int(cx + rx * 0.9 * math.cos(rad))
            sy = int(cy - ry * 0.85 * math.sin(rad))
            sw = int(w * rng.uniform(0.05, 0.08))
            sh = int(h * rng.uniform(0.02, 0.035))
            sx = max(0, min(sx - sw // 2, w - sw))
            sy = max(0, min(sy - sh // 2, h - sh))
            cv2.rectangle(img, (sx, sy), (sx + sw, sy + sh), (200, 200, 180), -1)
            cv2.putText(img, f"${rng.randint(10, 999)}", (sx + 2, sy + sh - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
            annotations.append(self._make_ann(CLASS_TO_IDX["player_stack"], sx, sy, sw, sh, w, h))

        # Bet input
        bi_w = int(w * rng.uniform(0.04, 0.07))
        bi_h = int(h * rng.uniform(0.025, 0.04))
        bi_x = cx + int(w * rng.uniform(0.05, 0.12))
        bi_y = btn_y - bi_h - int(h * rng.uniform(0.01, 0.02))
        cv2.rectangle(img, (bi_x, bi_y), (bi_x + bi_w, bi_y + bi_h), (180, 180, 180), -1)
        annotations.append(self._make_ann(CLASS_TO_IDX["bet_input"], bi_x, bi_y, bi_w, bi_h, w, h))

        # Dealer button (small circle)
        db_radius = int(min(w, h) * rng.uniform(0.01, 0.02))
        db_angle = rng.uniform(0, 360)
        db_rad = math.radians(db_angle)
        db_x = int(cx + rx * 0.6 * math.cos(db_rad))
        db_y = int(cy - ry * 0.55 * math.sin(db_rad))
        cv2.circle(img, (db_x, db_y), db_radius, (0, 200, 200), -1)
        db_box_x = max(0, db_x - db_radius)
        db_box_y = max(0, db_y - db_radius)
        db_box_w = min(2 * db_radius, w - db_box_x)
        db_box_h = min(2 * db_radius, h - db_box_y)
        annotations.append(self._make_ann(
            CLASS_TO_IDX["dealer_btn"], db_box_x, db_box_y, db_box_w, db_box_h, w, h
        ))

        # Random noise & blur
        if rng.random() < 0.3:
            noise = rng.randint(0, 15, img.shape, dtype=np.uint8)
            img = cv2.add(img, noise)
        if rng.random() < 0.2:
            ksize = rng.choice([3, 5])
            img = cv2.GaussianBlur(img, (ksize, ksize), 0)

        # Filter valid annotations
        annotations = [a for a in annotations if self._valid_ann(a)]

        return img, annotations

    @staticmethod
    def _make_ann(
        class_id: int, x: int, y: int, bw: int, bh: int, img_w: int, img_h: int,
    ) -> Dict:
        """Create YOLO-format annotation (normalized)."""
        cx = (x + bw / 2) / img_w
        cy = (y + bh / 2) / img_h
        nw = bw / img_w
        nh = bh / img_h
        return {"class_id": class_id, "cx": cx, "cy": cy, "w": nw, "h": nh}

    @staticmethod
    def _valid_ann(ann: Dict) -> bool:
        """Check annotation is within valid bounds."""
        return (
            0 <= ann["cx"] <= 1 and 0 <= ann["cy"] <= 1
            and 0 < ann["w"] <= 1 and 0 < ann["h"] <= 1
        )

    @staticmethod
    def _draw_region(img, x, y, w, h, color, rng):
        """Draw a card-like region (rounded rectangle)."""
        # Simple filled rectangle for now
        x = max(0, x)
        y = max(0, y)
        cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
        # Draw sub-card outlines
        n_cards = rng.randint(2, 6)
        card_w = w // max(n_cards, 1)
        for i in range(n_cards):
            cx = x + i * card_w
            cv2.rectangle(img, (cx + 1, y + 1), (cx + card_w - 2, y + h - 2), (180, 180, 180), 1)

    def _write_data_yaml(self) -> None:
        """Write the data.yaml config for YOLO training."""
        yaml_path = self.output_dir / "data.yaml"
        lines = [
            f"train: {self.output_dir / 'train' / 'images'}",
            f"val: {self.output_dir / 'valid' / 'images'}",
            f"test: {self.output_dir / 'test' / 'images'}",
            "",
            f"nc: {len(REGION_CLASSES)}",
            f"names: {REGION_CLASSES}",
        ]
        yaml_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Wrote %s", yaml_path)


# ---------------------------------------------------------------------------
# Training launcher
# ---------------------------------------------------------------------------

def train_region_model(
    dataset_dir: str = "training_data/regions_dataset",
    base_model: str = "yolov8n.pt",
    epochs: int = 50,
    batch_size: int = 16,
    img_size: int = 640,
    output_dir: str = "online_poker_training/yolov8_regions",
) -> Optional[str]:
    """
    Train / fine-tune YOLOv8 on region detection dataset.

    Args:
        dataset_dir: path to dataset (must have data.yaml)
        base_model: pre-trained YOLO weights to start from
        epochs: training epochs
        batch_size: batch size
        img_size: image size
        output_dir: output directory for trained model

    Returns:
        Path to best.pt weights, or None on failure
    """
    if not YOLO_AVAILABLE:
        logger.error("ultralytics not installed — cannot train")
        return None

    data_yaml = Path(dataset_dir) / "data.yaml"
    if not data_yaml.is_file():
        logger.error("data.yaml not found at %s", data_yaml)
        return None

    logger.info("Starting region model training: %d epochs, model=%s", epochs, base_model)

    try:
        model = YOLO(base_model)
        results = model.train(
            data=str(data_yaml),
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            project=str(Path(output_dir).parent),
            name=Path(output_dir).name,
            patience=15,
            save=True,
            save_period=10,
            plots=True,
            verbose=True,
        )

        best_path = Path(output_dir) / "weights" / "best.pt"
        if best_path.is_file():
            logger.info("Training complete. Best model: %s", best_path)
            return str(best_path)
        else:
            logger.warning("Training complete but best.pt not found at %s", best_path)
            return None

    except Exception as e:
        logger.error("Training failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "detect"

    if cmd == "generate":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        gen = RegionDatasetGenerator()
        result = gen.generate(count=count)
        print(f"Generated dataset: {result}")

    elif cmd == "train":
        best = train_region_model()
        print(f"Best model: {best}")

    elif cmd == "detect":
        if len(sys.argv) < 3:
            print("Usage: python yolo_region_detector.py detect <image.png>")
            sys.exit(1)
        img = cv2.imread(sys.argv[2])
        if img is None:
            print(f"Cannot read {sys.argv[2]}")
            sys.exit(1)
        detector = YOLORegionDetector()
        result = detector.detect(img)
        print(result.summary())

    else:
        print("Commands: detect <img>, generate [count], train")
