"""Split dataset/raw/<serial> PNG+JSON into table / lobby / home / other."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

TABLE_CLASSES = {
    "card",
    "pot",
    "stack_own",
    "stack_enemy",
    "dealer_button",
    "seat_avatar",
    "button_fold",
    "button_check",
    "button_call",
    "button_raise",
    "button_allin",
    "button_bet",
    "bet_slider",
    "bet_quick_buttons",
    "player_action_badge",
}
LOBBY_CLASSES = {
    "lobby_table_card",
    "lobby_blinds",
    "lobby_buyin",
    "lobby_players_count",
    "lobby_mode_button",
    "join_button",
}


def _green_ratio(bgr: np.ndarray) -> float:
    h, w = bgr.shape[:2]
    y0, y1 = int(h * 0.18), int(h * 0.78)
    x0, x1 = int(w * 0.08), int(w * 0.92)
    crop = bgr[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (35, 40, 40), (90, 255, 255))
    return float(np.count_nonzero(mask)) / float(mask.size)


def classify(pkg: str, names: list[str], green: float) -> str:
    pkg = (pkg or "").lower()
    if "launcher" in pkg:
        return "home"
    n_table = sum(1 for n in names if n in TABLE_CLASSES)
    n_lobby = sum(1 for n in names if n in LOBBY_CLASSES)
    if "coinpoker" not in pkg and "coingames" not in pkg:
        return "other"
    if n_lobby >= 3 and n_table < 2:
        return "lobby"
    if n_table >= 2 or green >= 0.10:
        return "table"
    if n_lobby >= 1:
        return "lobby"
    if green >= 0.06:
        return "table"
    return "other"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sort raw screenshots into table/lobby/home/other")
    p.add_argument("--src", default="dataset/raw/e2d0507")
    p.add_argument("--dst", default="dataset/sorted")
    p.add_argument("--weights", default="models/yolo/detect_best.pt")
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--copy", action="store_true", help="copy instead of move")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    src = Path(args.src)
    dst = Path(args.dst)
    pngs = sorted(src.glob("*.png"))
    if not pngs:
        print(f"no png in {src}")
        return 1
    from ultralytics import YOLO

    model = YOLO(args.weights)
    counts: Counter[str] = Counter()
    for i, png in enumerate(pngs, 1):
        js = png.with_suffix(".json")
        pkg = ""
        if js.is_file():
            try:
                pkg = json.loads(js.read_text(encoding="utf-8")).get("app_package") or ""
            except json.JSONDecodeError:
                pkg = ""
        img = cv2.imread(str(png))
        green = _green_ratio(img) if img is not None else 0.0
        names: list[str] = []
        if "launcher" not in (pkg or "").lower():
            r = model.predict(
                source=str(png),
                imgsz=640,
                conf=args.conf,
                device="cpu",
                save=False,
                verbose=False,
            )[0]
            if r.boxes is not None:
                for box in r.boxes:
                    names.append(r.names[int(box.cls[0])])
        folder = classify(pkg, names, green)
        out_dir = dst / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        op = shutil.copy2 if args.copy else shutil.move
        op(str(png), str(out_dir / png.name))
        if js.is_file():
            op(str(js), str(out_dir / js.name))
        counts[folder] += 1
        if i % 50 == 0 or i == len(pngs):
            print(f"{i}/{len(pngs)} {dict(counts)}", flush=True)
    print("done", dict(counts), "->", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
