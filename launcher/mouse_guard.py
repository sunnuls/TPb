"""
Mouse Guard — Human Input Detection and Bot Pause Mechanism.

Monitors global mouse movement via pynput. When the user moves the mouse,
all registered bots are paused immediately to prevent:
  - Conflicting mouse positions during gameplay
  - Accidental actions while human overrides the cursor
  - Detection by anti-bot systems that look for mouse conflicts

Usage::

    guard = MouseGuard(pause_duration=20.0)
    guard.register_pause_callback(my_bot.pause)
    guard.register_resume_callback(my_bot.resume)
    guard.start()

The guard fires ``on_human_input()`` when it detects mouse movement with
a delta above the threshold. After ``pause_duration`` seconds of inactivity,
it calls ``on_resume()`` automatically.

Threshold tuning:
  - MOVE_THRESHOLD_PX: minimum pixel delta to consider "human" (default 4).
    Below this catches micro-jitter from the OS itself.
  - PAUSE_DURATION_S:  how long to stay paused after last human move.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

try:
    from pynput import mouse as _pynput_mouse
    PYNPUT_AVAILABLE = True
except (ImportError, Exception):
    PYNPUT_AVAILABLE = False
    logger.warning("pynput not available — mouse guard disabled. "
                   "Install with: pip install pynput")

# Sensitivity: moves smaller than this (pixels) are ignored
MOVE_THRESHOLD_PX: int = 4
# Default pause after last human move (seconds)
DEFAULT_PAUSE_DURATION_S: float = 3.0


class MouseGuard:
    """
    Global mouse movement monitor that pauses bots during human interaction.

    Thread-safe: listener runs in its own daemon thread.
    Resume is handled by a lightweight watchdog thread.
    """

    def __init__(
        self,
        pause_duration: float = DEFAULT_PAUSE_DURATION_S,
        move_threshold_px: int = MOVE_THRESHOLD_PX,
    ) -> None:
        self.pause_duration    = pause_duration
        self.move_threshold_px = move_threshold_px

        self._pause_callbacks:  List[Callable[[], None]] = []
        self._resume_callbacks: List[Callable[[], None]] = []

        self._paused: bool   = False
        self._last_move_ts:  float = 0.0

        self._listener:       Optional[_pynput_mouse.Listener] = None  # type: ignore[name-defined]
        self._watchdog_thread: Optional[threading.Thread] = None
        self._running: bool  = False

        # Track last known position to compute delta
        self._last_x: Optional[int] = None
        self._last_y: Optional[int] = None

        # Suppression: ignore mouse events until this timestamp
        self._suppress_until: float = 0.0

    # ── Callback registration ────────────────────────────────────────────────

    def register_pause_callback(self, cb: Callable[[], None]) -> None:
        """Register a function to call when human input is detected."""
        self._pause_callbacks.append(cb)

    def register_resume_callback(self, cb: Callable[[], None]) -> None:
        """Register a function to call when pause period has expired."""
        self._resume_callbacks.append(cb)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start listening for mouse events.

        Returns:
            True if started successfully, False if pynput is unavailable.
        """
        if not PYNPUT_AVAILABLE:
            logger.warning("MouseGuard: pynput not available, cannot start")
            return False

        if self._running:
            return True

        self._running = True

        # Mouse listener (pynput daemon thread)
        self._listener = _pynput_mouse.Listener(
            on_move=self._on_move,
            daemon=True,
        )
        self._listener.start()

        # Watchdog thread — checks if pause period expired
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="MouseGuardWatchdog",
        )
        self._watchdog_thread.start()

        logger.info(
            "MouseGuard started (pause=%.0fs, threshold=%dpx)",
            self.pause_duration, self.move_threshold_px,
        )
        return True

    def stop(self) -> None:
        """Stop listening and clean up."""
        self._running = False
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        logger.info("MouseGuard stopped")

    # ── State ────────────────────────────────────────────────────────────────

    @property
    def is_paused(self) -> bool:
        """True if bots are currently paused due to human input."""
        return self._paused

    @property
    def seconds_until_resume(self) -> float:
        """Estimated seconds remaining in the pause period (0 if not paused)."""
        if not self._paused:
            return 0.0
        elapsed = time.time() - self._last_move_ts
        remaining = self.pause_duration - elapsed
        return max(0.0, remaining)

    # ── Suppression API (use before bot-initiated mouse moves) ───────────────

    def suppress(self, duration_s: float = 1.0) -> None:
        """Ignore all mouse events for *duration_s* seconds.

        Call this BEFORE moving the cursor programmatically so the bot's own
        mouse movements don't trigger a human-input pause.
        """
        self._suppress_until = time.time() + duration_s

    def suppress_resume(self) -> None:
        """Cancel active suppression immediately."""
        self._suppress_until = 0.0

    # ── Internal callbacks ───────────────────────────────────────────────────

    def _on_move(self, x: int, y: int) -> None:
        """pynput callback: called on every mouse move event."""
        # Ignore events while suppressed (bot-initiated movement)
        if time.time() < self._suppress_until:
            self._last_x = x
            self._last_y = y
            return

        # Compute movement delta
        if self._last_x is not None and self._last_y is not None:
            dx = abs(x - self._last_x)
            dy = abs(y - self._last_y)
            delta = (dx * dx + dy * dy) ** 0.5
            if delta < self.move_threshold_px:
                # Micro-jitter / OS noise — ignore
                return

        self._last_x = x
        self._last_y = y
        self._last_move_ts = time.time()

        if not self._paused:
            self._paused = True
            logger.info(
                "MouseGuard: human input detected at (%d, %d) — pausing bots for %.0fs",
                x, y, self.pause_duration,
            )
            self._fire_pause()

    def _watchdog_loop(self) -> None:
        """Background thread: resumes bots once pause period expires."""
        while self._running:
            time.sleep(0.5)
            if self._paused and self._last_move_ts > 0:
                elapsed = time.time() - self._last_move_ts
                if elapsed >= self.pause_duration:
                    self._paused = False
                    logger.info(
                        "MouseGuard: pause expired (%.0fs) — resuming bots",
                        elapsed,
                    )
                    self._fire_resume()

    def _fire_pause(self) -> None:
        for cb in self._pause_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("MouseGuard pause callback error: %s", exc)

    def _fire_resume(self) -> None:
        for cb in self._resume_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("MouseGuard resume callback error: %s", exc)

    # ── Singleton-style global guard ─────────────────────────────────────────

    _instance: Optional["MouseGuard"] = None

    @classmethod
    def get_global(cls) -> "MouseGuard":
        """Return the process-wide MouseGuard instance (lazy init)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __repr__(self) -> str:
        return (
            f"MouseGuard(paused={self._paused}, "
            f"pause_duration={self.pause_duration}s, "
            f"pynput={PYNPUT_AVAILABLE})"
        )
