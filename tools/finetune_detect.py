"""Fine-tune detect_best.pt on Roboflow v2 + auto-labeled table frames."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RF = ROOT / "dataset" / "roboflow_v2"
TABLE = ROOT / "dataset" / "sorted" / "table"
OUT = ROOT / "dataset" / "detect_ft"
WEIGHTS = ROOT / "models" / "yolo" / "detect_best.pt"
BACKUP = ROOT / "models" / "yolo" / "detect_best_roboflow.pt"


def _copy_split(name: str) -> None:
    for kind in ("images", "labels"):
        src = RF / name / kind
        dst = OUT / name / kind
        dst.mkdir(parents=True, exist_ok=True)
        if not src.is_dir():
            continue
        for p in src.iterdir():
            if p.is_file():
                shutil.copy2(p, dst / p.name)


def _write_yaml() -> Path:
    yaml_path = OUT / "data.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {OUT.as_posix()}",
                "train: train/images",
                "val: valid/images",
                "test: test/images",
                "nc: 21",
                "names: ['bet_quick_buttons', 'bet_slider', 'button_allin', 'button_bet', "
                "'button_call', 'button_check', 'button_fold', 'button_raise', 'card', "
                "'dealer_button', 'join_button', 'lobby_blinds', 'lobby_buyin', "
                "'lobby_mode_button', 'lobby_players_count', 'lobby_table_card', "
                "'player_action_badge', 'pot', 'seat_avatar', 'stack_enemy', 'stack_own']",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path


def auto_label_table(model, stride: int = 8, conf: float = 0.35) -> int:
    pngs = sorted(TABLE.glob("*.png"))
    picked = pngs[:: max(1, stride)]
    img_dir = OUT / "train" / "images"
    lbl_dir = OUT / "train" / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, png in enumerate(picked, 1):
        r = model.predict(
            source=str(png),
            imgsz=640,
            conf=conf,
            device="cpu",
            save=False,
            verbose=False,
        )[0]
        if r.boxes is None or len(r.boxes) == 0:
            continue
        lines = []
        for box in r.boxes:
            cls_id = int(box.cls[0])
            x, y, w, h = box.xywhn[0].tolist()
            lines.append(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
        shutil.copy2(png, img_dir / png.name)
        (lbl_dir / f"{png.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        n += 1
        if i % 20 == 0:
            print(f"auto {i}/{len(picked)} saved={n}", flush=True)
    print(f"auto-labeled {n} table frames", flush=True)
    return n


def main() -> int:
    from ultralytics import YOLO

    if OUT.exists():
        shutil.rmtree(OUT)
    for split in ("train", "valid", "test"):
        _copy_split(split)
    yaml_path = _write_yaml()
    if not BACKUP.is_file() and WEIGHTS.is_file():
        shutil.copy2(WEIGHTS, BACKUP)
        print("backup", BACKUP)
    model = YOLO(str(WEIGHTS))
    auto_label_table(model)
    print("train start", yaml_path, flush=True)
    model.train(
        data=str(yaml_path),
        epochs=25,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=0,
        patience=8,
        project=str(ROOT / "runs" / "detect"),
        name="pkr_ft",
        exist_ok=True,
        pretrained=True,
    )
    best = ROOT / "runs" / "detect" / "pkr_ft" / "weights" / "best.pt"
    if best.is_file():
        shutil.copy2(best, WEIGHTS)
        print("updated", WEIGHTS)
    else:
        print("best.pt missing", best)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
