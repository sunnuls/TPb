"""Offline audit for YOLO-format image datasets.

Reads metadata and annotations only. Does not train models or run live clients.
Usage: python tools/audit_dataset.py path/to/data.yaml
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from pathlib import Path

import yaml


def names_from_yaml(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        keys = sorted(int(k) for k in value)
        if keys != list(range(len(keys))):
            raise ValueError("class IDs in names must be contiguous from zero")
        return [str(value[i] if i in value else value[str(i)]) for i in keys]
    raise ValueError("data.yaml must provide names as list or ID map")


def audit(yaml_path: Path) -> int:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected YAML mapping")
    names = names_from_yaml(data.get("names"))
    if len(names) != len(set(names)):
        raise ValueError("Duplicate class names in data.yaml")
    root = Path(data.get("path") or yaml_path.parent)
    if not root.is_absolute():
        relative_to_yaml = (yaml_path.parent / root).resolve()
        root = relative_to_yaml if relative_to_yaml.exists() else (Path.cwd() / root).resolve()
    counts = Counter()
    errors = []
    seen_hashes = defaultdict(set)
    total_images = 0
    for split in ("train", "val", "valid", "test"):
        rel = data.get(split)
        if rel is None:
            continue
        if isinstance(rel, list):
            errors.append(f"{split}: multiple image roots not supported by this audit")
            continue
        folder = Path(rel)
        if not folder.is_absolute():
            folder = root / folder
        if not folder.is_dir():
            errors.append(f"{split}: missing directory {folder}")
            continue
        images = [p for p in folder.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        total_images += len(images)
        print(f"{split}: {len(images)} images")
        for image in images:
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            seen_hashes[digest].add(split)
            try:
                relative = image.relative_to(folder)
                parts = list(folder.parts)
                if "images" not in parts:
                    errors.append(f"{image}: path has no images directory")
                    continue
                parts[parts.index("images")] = "labels"
                label = Path(*parts) / relative.with_suffix(".txt")
                if not label.exists():
                    errors.append(f"{image}: missing annotation file")
                    continue
                for n, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                    if not line.strip():
                        continue
                    fields = line.split()
                    if len(fields) != 5:
                        errors.append(f"{label}:{n}: expected 5 fields, got {len(fields)}")
                        continue
                    try:
                        class_id = int(fields[0])
                        box = [float(x) for x in fields[1:]]
                    except ValueError:
                        errors.append(f"{label}:{n}: invalid numeric values")
                        continue
                    if not 0 <= class_id < len(names):
                        errors.append(f"{label}:{n}: class ID {class_id} outside 0..{len(names)-1}")
                    else:
                        counts[names[class_id]] += 1
                    x, y, w, h = box
                    if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1
                            and x-w/2 >= -1e-5 and x+w/2 <= 1+1e-5
                            and y-h/2 >= -1e-5 and y+h/2 <= 1+1e-5):
                        errors.append(f"{label}:{n}: bounding box out of bounds")
            except OSError as exc:
                errors.append(f"{image}: {exc}")
    leaks = sum(len(splits) > 1 for splits in seen_hashes.values())
    print(f"Images: {total_images}; classes: {len(names)}")
    for name in names:
        print(f"  {name}: {counts[name]} boxes")
        if counts[name] == 0:
            errors.append(f"class {name}: zero examples")
    if leaks:
        errors.append(f"{leaks} exact duplicate images shared across splits")
    for error in errors[:100]:
        print("WARNING:", error)
    if len(errors) > 100:
        print(f"... and {len(errors)-100} more warnings")
    print(f"Audit finished: {len(errors)} warning(s)")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit YOLO annotations without training")
    parser.add_argument("data_yaml", type=Path)
    args = parser.parse_args()
    return audit(args.data_yaml.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
