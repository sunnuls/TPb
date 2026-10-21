"""Prepare YOLO detect/cls datasets from a Roboflow YOLO export."""

from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

DETECT_NAMES = [
    "card",
    "button_fold",
    "button_check",
    "button_call",
    "button_raise",
    "button_allin",
    "pot",
    "stack_own",
    "stack_enemy",
    "dealer_button",
    "seat_avatar",
    "lobby_row",
    "join_button",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split Roboflow YOLO export and build card crops")
    p.add_argument(
        "--src",
        required=False,
        default=".",
        help="Roboflow YOLO folder (data.yaml + images/ + labels/)",
    )
    p.add_argument("--out-detect", default="dataset/detect", help="detect dataset root")
    p.add_argument("--out-cls", default="dataset/cls", help="classification crops root")
    p.add_argument(
        "--crops-map",
        default="crops_map.csv",
        help="CSV with columns image,card_text (optional index)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-detect", action="store_true")
    p.add_argument("--skip-cls", action="store_true")
    return p.parse_args(argv)


def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    names: list[str] = []
    in_names = False
    for line in text.splitlines():
        if line.strip().startswith("names:"):
            rest = line.split(":", 1)[1].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                names = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
                break
            in_names = True
            continue
        if in_names:
            if not line.strip().startswith("-"):
                break
            names.append(line.split("-", 1)[1].strip().strip("'\""))
    return {"names": names}


def _iter_pairs(src: Path) -> list[tuple[Path, Path]]:
    """Yield (image_path, label_path) pairs from a Roboflow-style tree."""
    pairs: list[tuple[Path, Path]] = []
    seen: set[str] = set()

    def add(img: Path, label: Path) -> None:
        key = str(img.resolve())
        if key in seen or not img.is_file():
            return
        seen.add(key)
        pairs.append((img, label))

    for img_dir in src.rglob("images"):
        if not img_dir.is_dir():
            continue
        rel = img_dir.relative_to(src)
        parts = list(rel.parts)
        if "labels" in parts:
            continue
        label_dir = src.joinpath(*["labels" if p == "images" else p for p in parts])
        for img in img_dir.iterdir():
            if img.suffix.lower() not in IMAGE_EXTS:
                continue
            add(img, label_dir / f"{img.stem}.txt")

    for split in ("train", "valid", "val", "test"):
        img_dir = src / split / "images"
        lab_dir = src / split / "labels"
        if img_dir.is_dir():
            for img in img_dir.iterdir():
                if img.suffix.lower() not in IMAGE_EXTS:
                    continue
                add(img, lab_dir / f"{img.stem}.txt")

    flat_img = src / "images"
    flat_lab = src / "labels"
    if flat_img.is_dir():
        for img in flat_img.iterdir():
            if img.suffix.lower() not in IMAGE_EXTS or img.is_dir():
                continue
            add(img, flat_lab / f"{img.stem}.txt")

    return pairs


def _split(items: list, seed: int) -> tuple[list, list, list]:
    rng = random.Random(seed)
    shuffled = list(items)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    if n >= 3:
        if not val and train:
            val.append(train.pop())
        if not test and train:
            test.append(train.pop())
    return train, val, test


def _copy_split(pairs: list[tuple[Path, Path]], dest_root: Path, split_name: str) -> None:
    img_out = dest_root / split_name / "images"
    lab_out = dest_root / split_name / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lab_out.mkdir(parents=True, exist_ok=True)
    for img, lab in pairs:
        shutil.copy2(img, img_out / img.name)
        dst_lab = lab_out / f"{img.stem}.txt"
        if lab.is_file():
            shutil.copy2(lab, dst_lab)
        else:
            dst_lab.write_text("", encoding="utf-8")


def _write_detect_yaml(dest: Path, names: list[str]) -> Path:
    yaml_path = dest / "poker_detect.yaml"
    lines = [
        f"path: {dest.resolve().as_posix()}",
        "train: train/images",
        "val: val/images",
        "test: test/images",
        f"nc: {len(names)}",
        "names:",
    ]
    for i, name in enumerate(names):
        lines.append(f"  {i}: {name}")
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return yaml_path


def _names_from_src(src: Path) -> list[str]:
    data_yaml = src / "data.yaml"
    if data_yaml.is_file():
        data = _load_yaml(data_yaml)
        names = data.get("names")
        if isinstance(names, dict):
            return [str(names[k]) for k in sorted(names, key=lambda x: int(x))]
        if isinstance(names, list) and names:
            return [str(n) for n in names]
    return list(DETECT_NAMES)


def _load_crops_map(path: Path) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    if not path.is_file():
        return mapping
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return mapping
        for row in reader:
            image = (row.get("image") or "").strip()
            text = (row.get("card_text") or "").strip()
            if not image or not text:
                continue
            mapping[Path(image).name].append(text)
            mapping[Path(image).stem].append(text)
    return mapping


def _parse_yolo_line(line: str) -> tuple[int, float, float, float, float] | None:
    parts = line.split()
    if len(parts) < 5:
        return None
    try:
        cls = int(float(parts[0]))
        x, y, w, h = map(float, parts[1:5])
    except ValueError:
        return None
    return cls, x, y, w, h


def _crop_box(img, xc: float, yc: float, bw: float, bh: float):
    from PIL import Image

    if not isinstance(img, Image.Image):
        return None
    w, h = img.size
    pw, ph = bw * w, bh * h
    x1 = int((xc * w) - pw / 2)
    y1 = int((yc * h) - ph / 2)
    x2 = int((xc * w) + pw / 2)
    y2 = int((yc * h) + ph / 2)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return img.crop((x1, y1, x2, y2))


def stage_detect(src: Path, dest: Path, seed: int) -> list[str]:
    names = _names_from_src(src)
    pairs = _iter_pairs(src)
    if not pairs:
        raise SystemExit(f"Не найдены пары image/label в {src}")
    train, val, test = _split(pairs, seed)
    dest.mkdir(parents=True, exist_ok=True)
    _copy_split(train, dest, "train")
    _copy_split(val, dest, "val")
    _copy_split(test, dest, "test")
    yml = _write_detect_yaml(dest, names)
    print(f"detect: train={len(train)} val={len(val)} test={len(test)} yaml={yml}")
    return names


def stage_cls(src: Path, dest: Path, map_path: Path, names: list[str], seed: int) -> None:
    from PIL import Image

    card_id = None
    for i, n in enumerate(names):
        if n == "card":
            card_id = i
            break
    if card_id is None:
        print("cls: класс card не найден в names — пропуск")
        return
    mapping = _load_crops_map(map_path)
    if not mapping:
        print(f"cls: нет маппинга {map_path} — пропуск кропов")
        return
    pairs = _iter_pairs(src)
    crops: list[tuple[str, object]] = []
    for img_path, lab_path in pairs:
        keys = [img_path.name, img_path.stem]
        texts: list[str] = []
        for k in keys:
            if k in mapping:
                texts = mapping[k]
                break
        if not texts or not lab_path.is_file():
            continue
        lines = lab_path.read_text(encoding="utf-8").splitlines()
        boxes = []
        for line in lines:
            parsed = _parse_yolo_line(line)
            if parsed and parsed[0] == card_id:
                boxes.append(parsed)
        boxes.sort(key=lambda b: (b[2], b[1]))
        img = Image.open(img_path).convert("RGB")
        for i, box in enumerate(boxes):
            if i >= len(texts):
                break
            crop = _crop_box(img, box[1], box[2], box[3], box[4])
            if crop is None:
                continue
            crops.append((texts[i], crop))
    if not crops:
        print("cls: кропы не собраны")
        return
    by_class: dict[str, list] = defaultdict(list)
    for label, crop in crops:
        by_class[label].append(crop)
    dest.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        (dest / split).mkdir(exist_ok=True)
    n_saved = 0
    for label, items in by_class.items():
        train, val, test = _split(list(enumerate(items)), seed)
        for split_name, group in (("train", train), ("val", val), ("test", test)):
            folder = dest / split_name / label
            folder.mkdir(parents=True, exist_ok=True)
            for idx, crop in group:
                out = folder / f"{label}_{idx:04d}.jpg"
                crop.save(out, format="JPEG", quality=90)
                n_saved += 1
    yaml_path = dest / "poker_cls.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {dest.resolve().as_posix()}",
                "train: train",
                "val: val",
                "test: test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"cls: crops={n_saved} classes={len(by_class)} yaml={yaml_path}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    src = Path(args.src)
    names = DETECT_NAMES
    if not args.skip_detect:
        names = stage_detect(src, Path(args.out_detect), args.seed)
    elif (src / "data.yaml").is_file():
        names = _names_from_src(src)
    if not args.skip_cls:
        map_path = Path(args.crops_map)
        if not map_path.is_file():
            alt = src / args.crops_map
            if alt.is_file():
                map_path = alt
        stage_cls(src, Path(args.out_cls), map_path, names, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
