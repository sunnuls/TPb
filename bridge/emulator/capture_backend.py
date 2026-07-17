"""
CaptureBackend — hardware-agnostic capture/input interface.

Defines the common contract that both the existing Win32/HWND desktop
pipeline and the new ADB/emulator pipeline implement. `BotInstance`
(and anything downstream: ROI detection, action execution) talks to
whichever backend is active through this interface only, so the
HIVE coordination layer (CentralHub, HiveCoordinator, CollusionCoordinator,
ManipulationEngine, PokerAI) does not need to change at all when
switching from desktop windows to mobile emulators.

Two concrete backends currently exist:
    - Win32 desktop capture: `bridge/screen_capture.py` + `bridge/action/real_executor.py`
      (kept as-is; not wrapped here to avoid churn on a stable path)
    - `ADBBackend` (this package): Android emulator instances via ADB

DRY-RUN MODE: Concrete backends must default to simulated/no-op behaviour
unless the global SafetyFramework is in UNSAFE mode (same convention as
the rest of `bridge/`).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CaptureBackendError(RuntimeError):
    """Raised when a backend operation fails unrecoverably."""


@dataclass
class BackendResolution:
    """Screen/device resolution as reported by a backend."""
    width: int
    height: int

    def as_tuple(self) -> Tuple[int, int]:
        return (self.width, self.height)


class CaptureBackend(ABC):
    """
    Common capture + input contract for a single bot target
    (one desktop window OR one emulator instance).

    Implementations MUST be safe to construct even when the target
    is unreachable — connectivity failures are surfaced through
    `is_connected()` and via `None`/`False` return values, not
    exceptions, so that `BotInstance`'s existing try/except-heavy
    game loop keeps working unchanged.
    """

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the backend can currently reach its target."""

    @abstractmethod
    def get_resolution(self) -> Optional[BackendResolution]:
        """Return the current resolution of the target, or None if unknown."""

    @abstractmethod
    def capture(self) -> Optional[np.ndarray]:
        """Capture a single frame as a BGR numpy array, or None on failure."""

    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """Tap/click at absolute (x, y) in the target's own coordinate space."""

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe/drag from (x1, y1) to (x2, y2)."""

    @abstractmethod
    def type_text(self, text: str) -> bool:
        """Type a string of text (e.g. bet-sizing input field)."""

    @abstractmethod
    def key_event(self, key: str) -> bool:
        """Send a single key/keycode event (e.g. 'BACK', 'ENTER')."""

    # ── Convenience helpers shared by all backends ──────────────────────────

    def click_relative(self, rel_x: float, rel_y: float) -> bool:
        """Click at a fractional position (0.0-1.0) of the target resolution.

        Useful for ROI configs expressed as percentages (see
        `coach_app/configs/vision_adapters/*.yaml` and `ROADMAP.md` ROI
        percentage fallback convention), which is resolution-independent
        and therefore ideal when many emulator instances run at slightly
        different window sizes.
        """
        res = self.get_resolution()
        if res is None:
            logger.warning("%s: click_relative failed — resolution unknown", self)
            return False
        x = int(res.width * max(0.0, min(1.0, rel_x)))
        y = int(res.height * max(0.0, min(1.0, rel_y)))
        return self.click(x, y)
