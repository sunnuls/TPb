from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from coach_app.ingest.vision.base import VisionAdapter, VisionParseResult


@dataclass(frozen=True)
class _Roi:
    x: int
    y: int
    w: int
    h: int


def _as_roi(v: Any) -> _Roi:
    if not isinstance(v, dict):
        raise TypeError("ROI must be a dict with x,y,w,h")
    return _Roi(x=int(v["x"]), y=int(v["y"]), w=int(v["w"]), h=int(v["h"]))


def _crop_np(img: "Any", roi: _Roi) -> "Any":
    return img[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]


class LiveVisionAdapter(VisionAdapter):
    adapter_name = "live_opencv"
    adapter_version = "1.0"

    def __init__(
        self,
        *,
        config_path: str | os.PathLike[str],
        templates_dir: str | os.PathLike[str] = "templates/cards",
        match_threshold: float = 0.8,
    ) -> None:
        self.config_path = Path(config_path)
        self.templates_dir = Path(templates_dir)
        self.match_threshold = float(match_threshold)

        cfg = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        rois = dict(cfg.get("rois", {}) or {})
        self.rois = rois
        self.anchors = dict(cfg.get("anchors", {}) or {})

        self._card_templates = self._load_card_templates(self.templates_dir)

    def capture_screen(self, region: dict[str, int] | list[int] | tuple[int, int, int, int] | None = None) -> Image.Image:
        import mss
        import numpy as np

        with mss.mss() as sct:
            monitor: dict[str, int]
            if region is None:
                monitor = dict(sct.monitors[1])
            elif isinstance(region, dict):
                monitor = {
                    "left": int(region.get("left", region.get("x", 0))),
                    "top": int(region.get("top", region.get("y", 0))),
                    "width": int(region.get("width", region.get("w", 0))),
                    "height": int(region.get("height", region.get("h", 0))),
                }
            else:
                a = list(region)
                if len(a) != 4:
                    raise ValueError("region must have 4 items")
                left, top, right, bottom = [int(x) for x in a]
                monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}

            raw = sct.grab(monitor)
            arr = np.asarray(raw, dtype=np.uint8)
            rgb = arr[:, :, :3][:, :, ::-1]
            return Image.fromarray(rgb, mode="RGB")

    def parse(self, image: bytes | Image.Image) -> VisionParseResult:
        img = image
        if isinstance(image, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image)).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            raise TypeError("image must be bytes or PIL.Image")

        import numpy as np

        np_img = np.asarray(img)
        partial, conf, warnings = self.extract_state(np_img)
        return VisionParseResult(
            partial_state=partial,
            confidence_map=conf,
            warnings=warnings,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
        )

    def detect_cards(self, roi_img: "Any") -> tuple[str | None, float]:
        import cv2

        if roi_img is None:
            return None, 0.0

        gray = cv2.cvtColor(roi_img, cv2.COLOR_RGB2GRAY) if roi_img.ndim == 3 else roi_img

        best_token: str | None = None
        best_score = -1.0
        for token, templ in self._card_templates.items():
            if templ is None:
                continue
            if gray.shape[0] < templ.shape[0] or gray.shape[1] < templ.shape[1]:
                continue
            res = cv2.matchTemplate(gray, templ, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, _max_loc = cv2.minMaxLoc(res)
            if float(max_val) > best_score:
                best_score = float(max_val)
                best_token = token

        if best_score >= float(self.match_threshold):
            return best_token, float(best_score)
        return None, float(max(0.0, best_score))

    def extract_text(self, roi_img: "Any") -> tuple[str, float]:
        import cv2
        import pytesseract

        if roi_img is None:
            return "", 0.0

        gray = cv2.cvtColor(roi_img, cv2.COLOR_RGB2GRAY) if roi_img.ndim == 3 else roi_img
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        cfg = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.$"
        txt = pytesseract.image_to_string(gray, config=cfg) or ""
        txt = txt.strip()

        # Heuristic confidence: non-empty numeric-like output.
        conf = 0.0
        if txt:
            conf = 0.6
            if re.search(r"\d", txt):
                conf = 0.8
        return txt, float(conf)

    def extract_state(self, img: "Any") -> tuple[dict[str, Any], dict[str, float], list[str]]:
        partial: dict[str, Any] = {}
        conf: dict[str, float] = {}
        warnings: list[str] = []

        table_roi = self.rois.get("table_region")
        table_img = img
        if table_roi is not None:
            table_img = _crop_np(img, _as_roi(table_roi))

        hero_cards: list[str] = []
        hero_scores: list[float] = []
        hero_rois = self.rois.get("hero_hole_cards")
        if isinstance(hero_rois, list):
            for i, r in enumerate(hero_rois):
                token, score = self.detect_cards(_crop_np(table_img, _as_roi(r)))
                if token is not None:
                    hero_cards.append(token)
                    hero_scores.append(float(score))
                else:
                    hero_scores.append(float(score))
                    warnings.append(f"hero_hole_cards[{i}] не распознана")

        if len(hero_cards) == 2 and len(set(hero_cards)) == 2:
            partial["hero_hole"] = list(hero_cards)
            conf["hero_hole"] = float(min(hero_scores)) if hero_scores else 0.0

        board_cards: list[str] = []
        board_scores: list[float] = []
        board_rois = self.rois.get("board_cards")
        if isinstance(board_rois, list):
            for i, r in enumerate(board_rois):
                token, score = self.detect_cards(_crop_np(table_img, _as_roi(r)))
                if token is not None:
                    board_cards.append(token)
                    board_scores.append(float(score))
                else:
                    board_scores.append(float(score))

        if board_cards and len(set(board_cards)) == len(board_cards):
            partial["board"] = list(board_cards)
            conf["board"] = float(min(board_scores)) if board_scores else 0.0

        street: str | None = None
        n = len(board_cards)
        if n == 0:
            if "hero_hole" in partial:
                street = "preflop"
        elif n == 3:
            street = "flop"
        elif n == 4:
            street = "turn"
        elif n == 5:
            street = "river"
        else:
            warnings.append(f"Некорректное число карт борда: {n}")

        if street is not None:
            partial["street"] = street
            conf["street"] = 0.8

        pot_roi = self.rois.get("pot_text")
        if pot_roi is not None:
            txt, tconf = self.extract_text(_crop_np(table_img, _as_roi(pot_roi)))
            if txt:
                m = re.search(r"(\d+(?:\.\d+)?)", txt.replace(",", "."))
                if m:
                    try:
                        partial["pot"] = float(m.group(1))
                        conf["pot"] = float(tconf)
                    except Exception:
                        warnings.append("pot_text распознан, но не удалось преобразовать в число")
                else:
                    warnings.append("pot_text не содержит числа")
            else:
                warnings.append("pot_text пустой")

        stacks_roi = self.rois.get("stacks")
        if isinstance(stacks_roi, list):
            stacks: list[float] = []
            stack_confs: list[float] = []
            for i, r in enumerate(stacks_roi):
                txt, tconf = self.extract_text(_crop_np(table_img, _as_roi(r)))
                if not txt:
                    continue
                m = re.search(r"(\d+(?:\.\d+)?)", txt.replace(",", "."))
                if not m:
                    continue
                try:
                    stacks.append(float(m.group(1)))
                    stack_confs.append(float(tconf))
                    conf[f"stack_{i+1}"] = float(tconf)
                except Exception:
                    continue
            if stacks:
                partial["stacks"] = list(stacks)
                conf["stacks"] = float(min(stack_confs)) if stack_confs else 0.0

        return partial, conf, warnings

    def _load_card_templates(self, templates_dir: Path) -> dict[str, "Any"]:
        import cv2

        out: dict[str, "Any"] = {}
        if not templates_dir.exists():
            return out

        for fp in sorted(templates_dir.glob("*.png")):
            token = fp.stem
            img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            out[token] = img
        return out
