#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
mouse_curve_generator.py — Bezier mouse paths + pyautogui integration.

Phase 1 of action_executor.md.

Root-level facade that:
- Re-exports the Bézier engine from launcher/vision/mouse_curve_generator.py
- Adds pyautogui integration (move_along_path, click_at)
- Provides ActionExecutor class for reliable humanised clicks

Usage::

    from mouse_curve_generator import ActionExecutor

    executor = ActionExecutor(intensity=5)
    executor.move(start=(100, 200), end=(500, 400))
    executor.click(target=(500, 400))

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import Bézier engine
# ---------------------------------------------------------------------------

try:
    from launcher.vision.mouse_curve_generator import (
        MouseCurveGenerator,
        MousePath,
        CurvePoint,
        bezier_point,
        bezier_curve,
    )
    HAS_BEZIER = True
except (ImportError, SyntaxError, Exception):
    HAS_BEZIER = False

# Fallback minimal implementations if launcher module unavailable
if not HAS_BEZIER:
    @dataclass
    class CurvePoint:
        x: int
        y: int
        dt: float = 0.0

    @dataclass
    class MousePath:
        points: List[CurvePoint] = field(default_factory=list)
        total_duration: float = 0.0
        distance: float = 0.0
        control_points: List[Tuple[float, float]] = field(default_factory=list)

        @property
        def length(self) -> int:
            return len(self.points)

    def _comb(n: int, k: int) -> int:
        if k < 0 or k > n:
            return 0
        if k == 0 or k == n:
            return 1
        k = min(k, n - k)
        result = 1
        for i in range(k):
            result = result * (n - i) // (i + 1)
        return result

    def _bernstein(n: int, i: int, t: float) -> float:
        return _comb(n, i) * (t ** i) * ((1 - t) ** (n - i))

    def bezier_point(
        control_points: List[Tuple[float, float]], t: float
    ) -> Tuple[float, float]:
        n = len(control_points) - 1
        x = sum(_bernstein(n, i, t) * p[0] for i, p in enumerate(control_points))
        y = sum(_bernstein(n, i, t) * p[1] for i, p in enumerate(control_points))
        return (x, y)

    def bezier_curve(
        control_points: List[Tuple[float, float]], num_points: int = 50
    ) -> List[Tuple[float, float]]:
        return [
            bezier_point(control_points, t / max(num_points - 1, 1))
            for t in range(num_points)
        ]

    class MouseCurveGenerator:
        """Minimal fallback Bézier generator."""

        def __init__(self, intensity: float = 5.0, speed_base: float = 0.6,
                     jitter_amplitude: float = 0.8, overshoot: bool = True,
                     num_points: int = 60, speed_steepness: float = 10.0):
            self.intensity = max(0.0, min(10.0, intensity))
            self.speed_base = max(0.05, speed_base)
            self.jitter_amplitude = max(0.0, jitter_amplitude)
            self.overshoot = overshoot
            self.num_points = max(5, num_points)
            self.speed_steepness = speed_steepness

        def generate(self, start: Tuple[int, int], end: Tuple[int, int],
                     duration: Optional[float] = None) -> MousePath:
            sx, sy = float(start[0]), float(start[1])
            ex, ey = float(end[0]), float(end[1])
            dist = math.hypot(ex - sx, ey - sy)
            if dist < 1:
                return MousePath(
                    points=[CurvePoint(int(ex), int(ey), 0.0)],
                    total_duration=0.0, distance=0.0,
                )
            if duration is None:
                duration = max(0.05, self.speed_base * dist / 1000.0)
                duration *= random.uniform(0.8, 1.2)

            # Simple cubic Bézier
            mx, my = (sx + ex) / 2, (sy + ey) / 2
            offset = dist * 0.1 * (self.intensity / 10.0)
            c1 = (mx + random.gauss(0, offset), my + random.gauss(0, offset))
            ctrl = [(sx, sy), c1, (ex, ey)]
            raw = bezier_curve(ctrl, self.num_points)

            dt_each = duration / max(len(raw) - 1, 1)
            points = [CurvePoint(int(round(x)), int(round(y)),
                                 dt_each if i > 0 else 0.0)
                      for i, (x, y) in enumerate(raw)]
            return MousePath(
                points=points, total_duration=duration,
                distance=dist, control_points=ctrl,
            )

        def generate_click_path(self, start: Tuple[int, int],
                                target: Tuple[int, int],
                                click_offset_range: int = 3,
                                duration: Optional[float] = None) -> MousePath:
            ox = random.randint(-click_offset_range, click_offset_range)
            oy = random.randint(-click_offset_range, click_offset_range)
            return self.generate(start, (target[0] + ox, target[1] + oy), duration)


# ---------------------------------------------------------------------------
# pyautogui integration
# ---------------------------------------------------------------------------

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    HAS_PYAUTOGUI = True
except (ImportError, Exception):
    HAS_PYAUTOGUI = False


# ---------------------------------------------------------------------------
# Action result
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Result of a mouse action."""
    success: bool = True
    action: str = ""            # "move", "click", "double_click", "drag"
    start: Tuple[int, int] = (0, 0)
    end: Tuple[int, int] = (0, 0)
    duration_ms: float = 0.0
    path_length: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# ActionExecutor
# ---------------------------------------------------------------------------

class ActionExecutor:
    """Executes mouse actions using Bézier paths.

    Integrates MouseCurveGenerator with pyautogui for real execution,
    or runs in dry-run mode for testing.

    Args:
        intensity: Bézier curvature (0–10)
        speed_base: base speed (seconds per 1000px)
        jitter: hand-tremor amplitude (px)
        overshoot: enable overshoot-and-correct
        dry_run: if True, don't actually move the mouse
    """

    def __init__(
        self,
        intensity: float = 5.0,
        speed_base: float = 0.6,
        jitter: float = 0.8,
        overshoot: bool = True,
        dry_run: bool = False,
    ):
        self.generator = MouseCurveGenerator(
            intensity=intensity,
            speed_base=speed_base,
            jitter_amplitude=jitter,
            overshoot=overshoot,
        )
        self.dry_run = dry_run
        self._last_position: Tuple[int, int] = (0, 0)

    @property
    def last_position(self) -> Tuple[int, int]:
        return self._last_position

    def move(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: Optional[float] = None,
    ) -> ActionResult:
        """Move mouse along a Bézier path from start to end.

        Returns ActionResult.
        """
        t0 = time.perf_counter()
        path = self.generator.generate(start, end, duration)
        result = ActionResult(
            action="move", start=start, end=end,
            path_length=path.length,
        )

        if not self.dry_run and HAS_PYAUTOGUI:
            try:
                for pt in path.points:
                    if pt.dt > 0:
                        time.sleep(pt.dt)
                    pyautogui.moveTo(pt.x, pt.y, _pause=False)
            except Exception as exc:
                result.success = False
                result.error = str(exc)

        self._last_position = end
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result

    def click(
        self,
        target: Tuple[int, int],
        start: Optional[Tuple[int, int]] = None,
        button: str = "left",
        duration: Optional[float] = None,
    ) -> ActionResult:
        """Move to target and click.

        If start is None, uses last_position.
        """
        if start is None:
            start = self._last_position

        t0 = time.perf_counter()
        path = self.generator.generate_click_path(start, target, duration=duration)
        result = ActionResult(
            action="click", start=start, end=target,
            path_length=path.length,
        )

        if not self.dry_run and HAS_PYAUTOGUI:
            try:
                for pt in path.points:
                    if pt.dt > 0:
                        time.sleep(pt.dt)
                    pyautogui.moveTo(pt.x, pt.y, _pause=False)
                pyautogui.click(button=button, _pause=False)
            except Exception as exc:
                result.success = False
                result.error = str(exc)

        self._last_position = target
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result

    def double_click(
        self,
        target: Tuple[int, int],
        start: Optional[Tuple[int, int]] = None,
        duration: Optional[float] = None,
    ) -> ActionResult:
        """Move to target and double-click."""
        if start is None:
            start = self._last_position

        t0 = time.perf_counter()
        path = self.generator.generate_click_path(start, target, duration=duration)
        result = ActionResult(
            action="double_click", start=start, end=target,
            path_length=path.length,
        )

        if not self.dry_run and HAS_PYAUTOGUI:
            try:
                for pt in path.points:
                    if pt.dt > 0:
                        time.sleep(pt.dt)
                    pyautogui.moveTo(pt.x, pt.y, _pause=False)
                pyautogui.doubleClick(_pause=False)
            except Exception as exc:
                result.success = False
                result.error = str(exc)

        self._last_position = target
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result

    def drag(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        button: str = "left",
        duration: Optional[float] = None,
    ) -> ActionResult:
        """Drag from start to end."""
        t0 = time.perf_counter()
        path = self.generator.generate(start, end, duration)
        result = ActionResult(
            action="drag", start=start, end=end,
            path_length=path.length,
        )

        if not self.dry_run and HAS_PYAUTOGUI:
            try:
                pyautogui.moveTo(start[0], start[1], _pause=False)
                pyautogui.mouseDown(button=button, _pause=False)
                for pt in path.points[1:]:
                    if pt.dt > 0:
                        time.sleep(pt.dt)
                    pyautogui.moveTo(pt.x, pt.y, _pause=False)
                pyautogui.mouseUp(button=button, _pause=False)
            except Exception as exc:
                result.success = False
                result.error = str(exc)

        self._last_position = end
        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result
