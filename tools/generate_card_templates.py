from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _crop(img: Image.Image, roi: dict) -> Image.Image:
    x = int(roi["x"])
    y = int(roi["y"])
    w = int(roi["w"])
    h = int(roi["h"])
    return img.crop((x, y, x + w, y + h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="coach_app/configs/adapters/pokerstars_live.yaml")
    ap.add_argument("--frame", required=True, help="Path to a sample frame (png/jpg)")
    ap.add_argument("--out", default="templates/cards", help="Output dir for templates")
    ap.add_argument(
        "--roi_key",
        default="hero_hole_cards",
        help="ROI key in config: hero_hole_cards or board_cards, etc.",
    )
    ap.add_argument(
        "--tokens",
        default="",
        help="Comma-separated tokens to name templates, e.g. 'As,Kd' (must match number of ROIs used)",
    )
    args = ap.parse_args()

    root = _repo_root()
    cfg_path = (root / args.config).resolve()
    frame_path = (root / args.frame).resolve()
    out_dir = (root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    rois = dict(cfg.get("rois", {}) or {})

    roi_list = rois.get(args.roi_key)
    if not isinstance(roi_list, list) or not roi_list:
        raise SystemExit(f"roi_key '{args.roi_key}' not found or not a list in {cfg_path}")

    tokens = [t.strip() for t in str(args.tokens).split(",") if t.strip()]
    if tokens and len(tokens) != len(roi_list):
        raise SystemExit("--tokens count must match ROI list length")

    img = _load_image(frame_path)

    for i, roi in enumerate(roi_list):
        crop = _crop(img, roi)
        token = tokens[i] if tokens else f"roi_{args.roi_key}_{i+1}"
        fp = out_dir / f"{token}.png"
        crop.save(fp)
        print(str(fp))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
