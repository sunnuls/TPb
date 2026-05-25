"""
Anchor Detector — roadmap13 Phase 3 (multi-scale).

Uses cv2.matchTemplate with multi-scale support to find anchor elements
(logo, buttons, chips, table edges) in a poker-client screenshot, then
computes all ROI zones relative to the found anchors.

Features:
  - find_anchors(image): multi-scale template matching for 10 anchors
  - calculate_all_roi(anchors): full ROI computation (offsets + derived)
  - load_config(): read config/anchor_templates.yaml (with scales)
  - detect_roi(): convenience full-pipeline

EDUCATIONAL USE ONLY.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except (ImportError, ModuleNotFoundError):
    HAS_CV2 = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AnchorMatch:
    """Result of a single anchor template match."""
    name: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    confidence: float = 0.0
    zone: str = ""
    roi_offsets: Dict[str, Dict[str, int]] = field(default_factory=dict)
    scale: float = 1.0

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass
class ROIZone:
    """A derived ROI zone computed from anchors."""
    name: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    source: str = ""
    confidence: float = 0.0

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "x": self.x, "y": self.y,
            "w": self.w, "h": self.h,
            "source": self.source,
            "confidence": round(self.confidence, 3),
        }


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = Path("config/anchor_templates.yaml")


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load anchor templates configuration."""
    if not HAS_YAML:
        raise ImportError("pyyaml is required: pip install pyyaml")
    path = path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Anchor config not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Multi-scale template matching helper
# ---------------------------------------------------------------------------

_DEFAULT_SCALES = [1.0]


def _match_template_multiscale(
    gray: np.ndarray,
    tmpl: np.ndarray,
    scales: List[float],
    method: int,
) -> Tuple[float, Tuple[int, int], int, int, float]:
    """Run matchTemplate at multiple scales and return best hit.

    Returns:
        (best_confidence, (x, y), matched_w, matched_h, best_scale)
    """
    best_val = -1.0
    best_loc = (0, 0)
    best_w, best_h = tmpl.shape[1], tmpl.shape[0]
    best_scale = 1.0
    ih, iw = gray.shape[:2]

    for scale in scales:
        new_w = max(4, int(tmpl.shape[1] * scale))
        new_h = max(4, int(tmpl.shape[0] * scale))
        if new_w >= iw or new_h >= ih:
            continue

        resized = cv2.resize(tmpl, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        result = cv2.matchTemplate(gray, resized, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_w = new_w
            best_h = new_h
            best_scale = scale

    return best_val, best_loc, best_w, best_h, best_scale


# ---------------------------------------------------------------------------
# Core: find_anchors (multi-scale)
# ---------------------------------------------------------------------------

def find_anchors(
    image: np.ndarray,
    config: Optional[Dict[str, Any]] = None,
    *,
    config_path: Optional[Path] = None,
    method: int = None,
) -> List[AnchorMatch]:
    """Find all anchors in an image using multi-scale cv2.matchTemplate.

    For each anchor, tries all scales defined in config (or [1.0] default).
    Returns matches whose best confidence exceeds the configured threshold.
    """
    if not HAS_CV2:
        logger.error("find_anchors: cv2 not available")
        return []

    if method is None:
        method = cv2.TM_CCOEFF_NORMED

    if config is None:
        config = load_config(config_path)

    anchors_cfg = config.get("anchors", {})
    matches: List[AnchorMatch] = []

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    for name, anchor_cfg in anchors_cfg.items():
        template_path = Path(anchor_cfg["file"])
        threshold = anchor_cfg.get("threshold", 0.7)
        zone = anchor_cfg.get("zone", "")
        roi_offsets = anchor_cfg.get("roi_offsets", {})
        scales = anchor_cfg.get("scales", _DEFAULT_SCALES)

        if not template_path.exists():
            logger.warning("Template not found: %s", template_path)
            continue

        tmpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if tmpl is None:
            logger.warning("Failed to load template: %s", template_path)
            continue

        if tmpl.shape[0] > gray.shape[0] or tmpl.shape[1] > gray.shape[1]:
            logger.debug("Template %s larger than image — skipping", name)
            continue

        best_val, best_loc, mw, mh, best_scale = _match_template_multiscale(
            gray, tmpl, scales, method,
        )

        if best_val >= threshold:
            match = AnchorMatch(
                name=name,
                x=best_loc[0], y=best_loc[1],
                w=mw, h=mh,
                confidence=float(best_val),
                zone=zone,
                roi_offsets=roi_offsets,
                scale=best_scale,
            )
            matches.append(match)
            logger.info(
                "Anchor '%s' found at (%d,%d) conf=%.3f scale=%.2f",
                name, best_loc[0], best_loc[1], best_val, best_scale,
            )
        else:
            logger.debug(
                "Anchor '%s' below threshold: %.3f < %.3f",
                name, best_val, threshold,
            )

    logger.info("find_anchors: %d/%d anchors found", len(matches), len(anchors_cfg))
    return matches


# ---------------------------------------------------------------------------
# Core: calculate_all_roi
# ---------------------------------------------------------------------------

def calculate_all_roi(
    anchors: List[AnchorMatch],
    image_shape: Optional[Tuple[int, int]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[ROIZone]:
    """Compute all ROI zones from anchor positions.

    Handles:
      1. Per-anchor roi_offsets (dx/dy/w/h relative to anchor position)
      2. Derived zones: midpoint_vertical, bounding_box, offset_from_anchor
    """
    zones: List[ROIZone] = []
    anchor_map = {a.name: a for a in anchors}

    img_h = image_shape[0] if image_shape else 9999
    img_w = image_shape[1] if image_shape else 9999

    def _clamp(x: int, y: int, w: int, h: int) -> Tuple[int, int, int, int]:
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))
        return x, y, w, h

    # 1. ROI from per-anchor offsets
    for anchor in anchors:
        for roi_name, offsets in anchor.roi_offsets.items():
            dx = offsets.get("dx", 0)
            dy = offsets.get("dy", 0)
            w = offsets.get("w", 100)
            h = offsets.get("h", 50)
            x, y, w, h = _clamp(anchor.x + dx, anchor.y + dy, w, h)
            zones.append(ROIZone(
                name=roi_name, x=x, y=y, w=w, h=h,
                source=anchor.name, confidence=anchor.confidence,
            ))

    # 2. Derived zones
    if config:
        derived = config.get("derived_zones", {})
        for zone_name, zone_cfg in derived.items():
            meth = zone_cfg.get("method", "")
            primary = zone_cfg.get("primary_anchor", "")
            secondary = zone_cfg.get("secondary_anchor", "")
            fallback = zone_cfg.get("fallback_anchor", "")
            anchor_list = zone_cfg.get("anchors", [])

            if meth == "midpoint_vertical":
                a1 = anchor_map.get(primary)
                a2 = anchor_map.get(secondary)
                if a1 and a2:
                    mid_y = (a1.cy + a2.cy) // 2
                    mid_x = (a1.cx + a2.cx) // 2
                    w = abs(a2.cx - a1.cx) or 300
                    h = abs(a2.cy - a1.cy) // 3 or 80
                    x, y, w, h = _clamp(mid_x - w // 2, mid_y - h // 2, w, h)
                    zones.append(ROIZone(
                        name=zone_name, x=x, y=y, w=w, h=h,
                        source=f"{primary}+{secondary}",
                        confidence=min(a1.confidence, a2.confidence),
                    ))

            elif meth == "bounding_box" and anchor_list:
                found = [anchor_map[n] for n in anchor_list if n in anchor_map]
                if found:
                    x1 = min(a.x for a in found)
                    y1 = min(a.y for a in found)
                    x2 = max(a.x + a.w for a in found)
                    y2 = max(a.y + a.h for a in found)
                    x, y, w, h = _clamp(x1, y1, x2 - x1, y2 - y1)
                    zones.append(ROIZone(
                        name=zone_name, x=x, y=y, w=w, h=h,
                        source="+".join(a.name for a in found),
                        confidence=min(a.confidence for a in found),
                    ))

            elif meth == "offset_from_anchor":
                anchor_key = primary or fallback
                a = anchor_map.get(anchor_key)
                if a is None and fallback:
                    a = anchor_map.get(fallback)
                if a:
                    for roi_name, offsets in a.roi_offsets.items():
                        if roi_name not in [z.name for z in zones]:
                            dx = offsets.get("dx", 0)
                            dy = offsets.get("dy", 0)
                            w = offsets.get("w", 100)
                            h = offsets.get("h", 50)
                            x, y, w, h = _clamp(a.x + dx, a.y + dy, w, h)
                            zones.append(ROIZone(
                                name=roi_name, x=x, y=y, w=w, h=h,
                                source=a.name, confidence=a.confidence,
                            ))

    logger.info("calculate_all_roi: %d zones computed", len(zones))
    return zones


# Backward-compatible alias
calculate_relative_roi = calculate_all_roi


# ---------------------------------------------------------------------------
# Convenience: full pipeline
# ---------------------------------------------------------------------------

def detect_roi(
    image: np.ndarray,
    config: Optional[Dict[str, Any]] = None,
    *,
    config_path: Optional[Path] = None,
) -> Tuple[List[AnchorMatch], List[ROIZone]]:
    """Full pipeline: find anchors -> compute all ROI zones."""
    if config is None:
        config = load_config(config_path)

    anchors = find_anchors(image, config=config)
    img_shape = image.shape[:2] if image is not None else None
    zones = calculate_all_roi(anchors, image_shape=img_shape, config=config)

    return anchors, zones
