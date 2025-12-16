from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_adapter_config(path: Path) -> dict[str, Any]:
    """
    Load adapter config from YAML/JSON.
    Expected fields (example): adapter, rois, anchors.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported config format: {suffix}")

    if not isinstance(data, dict):
        raise ValueError("Adapter config must be a mapping")
    return data


