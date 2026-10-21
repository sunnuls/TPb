"""Train detect weights on Roboflow v3 (103 images, 24 classes)."""

from __future__ import annotations

import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RF = ROOT / "dataset" / "roboflow_v3"
OUT = ROOT / "dataset" / "detect_v3"
WEIGHTS = ROOT / "models" / "yolo" / "detect_best.pt"
BACKUP = ROOT / "models" / "yolo" / "detect_best_v2.pt"
NAMES = [
    "button_call",
    "button_check",
    "button_fold",
    "button_raise",
    "buyin_amount",
    "buyin_button",
    "buyin_max",
    "buyin_mid",
    "buyin_min",
    "buyin_slider",
    "card",
    "dealer_button",
    "join_button",
    "lobby_blinds",
    "lobby_buyin",
    "lobby_mode_button",
    "lobby_players_count",
    "lobby_table_card",
    "own_nickname",
    "player_action_badge",
    "pot",
    "seat_avatar",
    "stack_enemy",
    "stack_own",
]


def _split() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    img_dir = RF / "train" / "images"
    lbl_dir = RF / "train" / "labels"
    images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    rng = random.Random(42)
    rng.shuffle(images)
    n_val = max(12, len(images) // 7)
    val, train = images[:n_val], images[n_val:]
    for split, files in (("train", train), ("valid", val)):
        (OUT / split / "images").mkdir(parents=True)
        (OUT / split / "labels").mkdir(parents=True)
        for img in files:
            shutil.copy2(img, OUT / split / "images" / img.name)
            lbl = lbl_dir / f"{img.stem}.txt"
            if lbl.is_file():
                shutil.copy2(lbl, OUT / split / "labels" / lbl.name)
    yaml = OUT / "data.yaml"
    yaml.write_text(
        "\n".join(
            [
                f"path: {OUT.as_posix()}",
                "train: train/images",
                "val: valid/images",
                f"nc: {len(NAMES)}",
                f"names: {NAMES}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"split train={len(train)} val={len(val)} yaml={yaml}", flush=True)


def main() -> int:
    from ultralytics import YOLO

    _split()
    if WEIGHTS.is_file() and not BACKUP.is_file():
        shutil.copy2(WEIGHTS, BACKUP)
        print("backup", BACKUP, flush=True)
    model = YOLO(str(WEIGHTS) if WEIGHTS.is_file() else "yolov8s.pt")
    model.train(
        data=str(OUT / "data.yaml"),
        epochs=40,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=0,
        patience=10,
        project=str(ROOT / "runs" / "detect"),
        name="pkr_v3",
        exist_ok=True,
        pretrained=True,
    )
    best = ROOT / "runs" / "detect" / "pkr_v3" / "weights" / "best.pt"
    if not best.is_file():
        print("best.pt missing", best)
        return 1
    shutil.copy2(best, WEIGHTS)
    print("updated", WEIGHTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
