"""Train YOLOv8 detect and/or card classification models."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLO detect and card-cls weights")
    p.add_argument("--stage", choices=("detect", "cls", "both"), default="both")
    p.add_argument("--detect-data", default="dataset/detect/poker_detect.yaml")
    p.add_argument("--cls-data", default="dataset/cls/poker_cls.yaml")
    p.add_argument("--models-dir", default="models/yolo")
    p.add_argument("--detect-epochs", type=int, default=120)
    p.add_argument("--cls-epochs", type=int, default=60)
    p.add_argument("--device", default="")
    return p.parse_args(argv)


def _copy_best(run_dir: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    candidates = [
        run_dir / "weights" / "best.pt",
        run_dir / "best.pt",
    ]
    for src in candidates:
        if src.is_file():
            shutil.copy2(src, dest)
            print(f"copied {src} -> {dest}")
            return
    raise FileNotFoundError(f"best.pt not found under {run_dir}")


def train_detect(data: Path, models_dir: Path, epochs: int, device: str) -> None:
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")
    kwargs = dict(
        data=str(data),
        epochs=epochs,
        imgsz=640,
        batch=16,
        hsv_h=0.05,
        hsv_s=0.7,
        hsv_v=0.4,
        scale=0.5,
        translate=0.15,
        flipud=0.0,
        project="runs/detect",
        name="poker_detect",
        exist_ok=True,
    )
    if device:
        kwargs["device"] = device
    results = model.train(**kwargs)
    save_dir = Path(getattr(results, "save_dir", "runs/detect/poker_detect"))
    _copy_best(save_dir, models_dir / "detect_best.pt")


def train_cls(data: Path, models_dir: Path, epochs: int, device: str) -> None:
    from ultralytics import YOLO

    model = YOLO("yolov8n-cls.pt")
    kwargs = dict(
        data=str(data),
        epochs=epochs,
        imgsz=128,
        project="runs/cls",
        name="poker_cls",
        exist_ok=True,
    )
    if device:
        kwargs["device"] = device
    results = model.train(**kwargs)
    save_dir = Path(getattr(results, "save_dir", "runs/cls/poker_cls"))
    _copy_best(save_dir, models_dir / "cls_best.pt")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models_dir = Path(args.models_dir)
    if args.stage in ("detect", "both"):
        train_detect(Path(args.detect_data), models_dir, args.detect_epochs, args.device)
    if args.stage in ("cls", "both"):
        train_cls(Path(args.cls_data), models_dir, args.cls_epochs, args.device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
