"""Ensure manual scripts run with project root as cwd and on sys.path."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def setup_project_root() -> Path:
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(PROJECT_ROOT)
    return PROJECT_ROOT
