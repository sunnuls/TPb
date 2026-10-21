"""
YOLO vision engine — resolution-independent detection pipeline.

Stage 1: YOLODetector (object detection in letterboxed 640 space)
Stage 2: RankSuitClassifier (52-class card crop classification)
Facade:  VisionEngine (capture → detect → classify → GameState)

No absolute ROI / template matching. Coordinates map via LetterboxMapper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_DETECT_CLASSES = [
    "hero_card",
    "board_card",
    "fold_button",
    "call_button",
    "raise_button",
    "check_button",
    "pot",
    "stack",
]


@dataclass
class GameState:
    """Structured vision output for one frame."""

    hero_cards: List[str] = field(default_factory=list)
    board_cards: List[str] = field(default_factory=list)
    buttons: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    pot_box: Optional[Tuple[int, int, int, int]] = None
    stack_box: Optional[Tuple[int, int, int, int]] = None
    resolution: Tuple[int, int] = (0, 0)
    # Compatibility with BotInstance decision path
    is_bots_turn: bool = False
    pot: float = 0.0
    hand_number: int = 0
    players: list = field(default_factory=list)

    def get_hero_cards(self) -> List[str]:
        return list(self.hero_cards)

    def empty(self) -> bool:
        return (
            not self.hero_cards
            and not self.board_cards
            and not self.buttons
            and self.pot_box is None
        )


class LetterboxMapper:
    """Map boxes from letterboxed model space (e.g. 640×640) back to native pixels."""

    def __init__(self, native_w: int, native_h: int, model_size: int = 640):
        if native_w <= 0 or native_h <= 0:
            raise ValueError(f"invalid native size {native_w}x{native_h}")
        if model_size <= 0:
            raise ValueError(f"invalid model_size {model_size}")
        self.native_w = int(native_w)
        self.native_h = int(native_h)
        self.model_size = int(model_size)
        self.scale = min(model_size / native_w, model_size / native_h)
        self.new_w = native_w * self.scale
        self.new_h = native_h * self.scale
        self.pad_x = (model_size - self.new_w) / 2.0
        self.pad_y = (model_size - self.new_h) / 2.0

    def to_native(self, box_xyxy_norm: Sequence[float]) -> Tuple[int, int, int, int]:
        """Normalize box in model canvas [0,1] → native pixel xyxy (clamped)."""
        x1, y1, x2, y2 = [float(v) for v in box_xyxy_norm]
        mx1, my1 = x1 * self.model_size, y1 * self.model_size
        mx2, my2 = x2 * self.model_size, y2 * self.model_size
        nx1 = int(round((mx1 - self.pad_x) / self.scale))
        ny1 = int(round((my1 - self.pad_y) / self.scale))
        nx2 = int(round((mx2 - self.pad_x) / self.scale))
        ny2 = int(round((my2 - self.pad_y) / self.scale))
        nx1 = max(0, min(self.native_w - 1, nx1))
        ny1 = max(0, min(self.native_h - 1, ny1))
        nx2 = max(0, min(self.native_w, nx2))
        ny2 = max(0, min(self.native_h, ny2))
        if nx2 < nx1:
            nx1, nx2 = nx2, nx1
        if ny2 < ny1:
            ny1, ny2 = ny2, ny1
        return nx1, ny1, nx2, ny2

    def center(self, box_xyxy_norm: Sequence[float]) -> Tuple[int, int]:
        """Native pixel center of box — intended for adb tap."""
        x1, y1, x2, y2 = self.to_native(box_xyxy_norm)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cx = max(0, min(self.native_w - 1, cx))
        cy = max(0, min(self.native_h - 1, cy))
        return cx, cy

    def native_point_to_norm(self, x: float, y: float) -> Tuple[float, float]:
        """Native pixel → normalized model-canvas coords (for round-trip tests)."""
        mx = x * self.scale + self.pad_x
        my = y * self.scale + self.pad_y
        return mx / self.model_size, my / self.model_size


class YOLODetector:
    """Stage 1 — load detect weights and return normalized boxes."""

    def __init__(self, weights_path: Optional[str], classes: Optional[List[str]] = None):
        self.classes = list(classes or DEFAULT_DETECT_CLASSES)
        self.weights_path = weights_path
        self._model = None
        self._stub = True
        if weights_path and Path(weights_path).is_file():
            try:
                from ultralytics import YOLO  # type: ignore

                self._model = YOLO(weights_path)
                self._stub = False
                logger.info("YOLODetector loaded weights=%s", weights_path)
            except Exception as exc:
                logger.warning("YOLODetector load failed (%s) — stub mode", exc)
                self._model = None
                self._stub = True
        else:
            logger.warning(
                "YOLODetector stub mode (weights missing: %s)", weights_path
            )

    def detect(self, image: np.ndarray) -> List[dict]:
        """Return list of {cls, box_norm, conf}. Stub → []."""
        if self._stub or self._model is None or image is None:
            return []
        try:
            results = self._model.predict(image, verbose=False)
            if not results:
                return []
            r0 = results[0]
            out: List[dict] = []
            names = getattr(r0, "names", None) or {}
            boxes = getattr(r0, "boxes", None)
            if boxes is None:
                return []
            h, w = image.shape[:2]
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                conf = float(box.conf[0]) if box.conf is not None else 0.0
                cls_id = int(box.cls[0]) if box.cls is not None else -1
                cls_name = names.get(cls_id, str(cls_id))
                # Normalize against letterboxed model canvas (assume square input)
                # Ultralytics returns coords in original image space — re-norm to [0,1]
                # relative to native image; LetterboxMapper expects model-canvas norms.
                # For Stage-1 scaffold we emit native-relative norms; VisionEngine
                # remaps via LetterboxMapper built from image shape.
                box_norm = (
                    xyxy[0] / max(w, 1),
                    xyxy[1] / max(h, 1),
                    xyxy[2] / max(w, 1),
                    xyxy[3] / max(h, 1),
                )
                out.append({"cls": cls_name, "box_norm": box_norm, "conf": conf})
            return out
        except Exception as exc:
            logger.warning("YOLODetector.detect error: %s", exc)
            return []


class RankSuitClassifier:
    """Stage 2 — classify a card crop into 52 classes (As..Kc)."""

    def __init__(self, weights_path: Optional[str]):
        self.weights_path = weights_path
        self._model = None
        self._stub = True
        if weights_path and Path(weights_path).is_file():
            try:
                from ultralytics import YOLO  # type: ignore

                self._model = YOLO(weights_path)
                self._stub = False
                logger.info("RankSuitClassifier loaded weights=%s", weights_path)
            except Exception as exc:
                logger.warning("RankSuitClassifier load failed (%s) — stub", exc)
        else:
            logger.warning(
                "RankSuitClassifier stub mode (weights missing: %s)", weights_path
            )

    def classify(self, crop: np.ndarray) -> Tuple[str, float]:
        if self._stub or self._model is None or crop is None or crop.size == 0:
            return ("", 0.0)
        try:
            results = self._model.predict(crop, verbose=False)
            if not results:
                return ("", 0.0)
            r0 = results[0]
            probs = getattr(r0, "probs", None)
            names = getattr(r0, "names", {}) or {}
            if probs is None:
                return ("", 0.0)
            top = int(probs.top1)
            conf = float(probs.top1conf)
            label = names.get(top, str(top))
            return (str(label), conf)
        except Exception as exc:
            logger.warning("RankSuitClassifier.classify error: %s", exc)
            return ("", 0.0)


class VisionEngine:
    """Facade: image → GameState via detect + classify."""

    def __init__(
        self,
        detect_weights: Optional[str] = None,
        cls_weights: Optional[str] = None,
        model_size: int = 640,
        classes: Optional[List[str]] = None,
        backend: str = "yolo",
    ):
        self.model_size = model_size
        self.backend = (backend or "yolo").lower()
        use_weights = self.backend != "stub"
        self.detector = YOLODetector(
            detect_weights if use_weights else None,
            classes=classes,
        )
        self.classifier = RankSuitClassifier(
            cls_weights if use_weights else None
        )

    @classmethod
    def from_config(cls, cfg: Optional[dict] = None) -> "VisionEngine":
        vision = (cfg or {}).get("vision", cfg or {})
        return cls(
            detect_weights=vision.get("detect_weights"),
            cls_weights=vision.get("cls_weights"),
            model_size=int(vision.get("model_size", 640)),
            backend=str(vision.get("backend", "yolo")),
        )

    def get_game_state(self, image: Optional[np.ndarray]) -> GameState:
        if image is None or not hasattr(image, "shape") or image.size == 0:
            return GameState()
        h, w = image.shape[:2]
        state = GameState(resolution=(w, h))
        if self.backend == "stub" or self.detector._stub:
            return state

        detections = self.detector.detect(image)
        if not detections:
            return state

        # Detections from Ultralytics are native-relative norms; build mapper
        # and treat box_norm as already in native [0,1] — convert via fake
        # identity letterbox (native==model letterbox of same aspect).
        mapper = LetterboxMapper(w, h, self.model_size)

        hero_crops: List[Tuple[float, Tuple[int, int, int, int]]] = []
        board_crops: List[Tuple[float, Tuple[int, int, int, int]]] = []

        for det in detections:
            cls = str(det.get("cls", "")).lower()
            conf = float(det.get("conf", 0.0))
            box_norm = det.get("box_norm") or (0, 0, 0, 0)
            # Native-relative norm → model-canvas norm for LetterboxMapper
            # Identity path: map native xyxy pixels through letterbox forward.
            x1n, y1n, x2n, y2n = (
                box_norm[0] * w,
                box_norm[1] * h,
                box_norm[2] * w,
                box_norm[3] * h,
            )
            n1 = mapper.native_point_to_norm(x1n, y1n)
            n2 = mapper.native_point_to_norm(x2n, y2n)
            model_norm = (n1[0], n1[1], n2[0], n2[1])
            xyxy = mapper.to_native(model_norm)
            cx, cy = mapper.center(model_norm)

            if "fold" in cls:
                state.buttons["fold"] = (cx, cy)
                state.is_bots_turn = True
            elif "call" in cls or "check" in cls:
                key = "call" if "call" in cls else "check"
                state.buttons[key] = (cx, cy)
                state.is_bots_turn = True
            elif "raise" in cls or "bet" in cls:
                state.buttons["raise"] = (cx, cy)
                state.is_bots_turn = True
            elif "pot" in cls:
                state.pot_box = xyxy
            elif "stack" in cls:
                state.stack_box = xyxy
            elif "hero" in cls and "card" in cls:
                hero_crops.append((conf, xyxy))
            elif "board" in cls and "card" in cls:
                board_crops.append((conf, xyxy))

        hero_crops.sort(key=lambda t: t[1][0])  # left→right
        board_crops.sort(key=lambda t: t[1][0])

        for _, xyxy in hero_crops[:2]:
            crop = _safe_crop(image, xyxy)
            label, _c = self.classifier.classify(crop)
            if label:
                state.hero_cards.append(label)

        for _, xyxy in board_crops[:5]:
            crop = _safe_crop(image, xyxy)
            label, _c = self.classifier.classify(crop)
            if label:
                state.board_cards.append(label)

        return state


def _safe_crop(image: np.ndarray, xyxy: Tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = xyxy
    h, w = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((1, 1, 3), dtype=np.uint8)
    return image[y1:y2, x1:x2]


def load_bots_vision_config(path: str = "config/bots.yaml") -> dict:
    """Load vision section from config/bots.yaml (empty dict on failure)."""
    try:
        import yaml

        p = Path(path)
        if not p.is_file():
            return {}
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.debug("load_bots_vision_config: %s", exc)
        return {}
