"""
Mouse Curve Generator — Phase 1 of action_executor.md.

Generates realistic Bézier-based mouse trajectories that mimic human
hand movement.  Replaces simple easing (``pyautogui.easeInOutQuad``)
with multi-point cubic Bézier splines featuring:

  - Random control-point offsets (humans don't move in straight lines)
  - Speed profile: slow start → fast middle → slow landing (sigma curve)
  - Micro-jitter overlay (natural hand tremor)
  - Overshoot / correction near the target
  - Configurable intensity (0 = straight line, 10 = very curvy)
  - Per-point timestamps for replay at variable speed

Usage::

    gen = MouseCurveGenerator(intensity=5)
    path = gen.generate(start=(100, 200), end=(500, 400))
    for pt in path.points:
        move_to(pt.x, pt.y)      # send to OS
        sleep(pt.dt)             # wait before next step

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CurvePoint:
    """A single point along the mouse path.

    Attributes:
        x:  pixel X
        y:  pixel Y
        dt: seconds to wait *before* moving to this point
    """
    x: int
    y: int
    dt: float = 0.0


@dataclass
class MousePath:
    """Complete mouse trajectory from start to end.

    Attributes:
        points:         ordered list of CurvePoints
        total_duration: sum of all dt values (seconds)
        distance:       Euclidean distance start→end (pixels)
        control_points: Bézier control points used for generation
    """
    points: List[CurvePoint] = field(default_factory=list)
    total_duration: float = 0.0
    distance: float = 0.0
    control_points: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.points)


# ---------------------------------------------------------------------------
# Bézier math
# ---------------------------------------------------------------------------


def _bernstein(n: int, i: int, t: float) -> float:
    """Bernstein basis polynomial B_{i,n}(t)."""
    return _comb(n, i) * (t ** i) * ((1 - t) ** (n - i))


def _comb(n: int, k: int) -> int:
    """Binomial coefficient C(n, k)."""
    if k < 0 or k > n:
        return 0
    if k == 0 or k == n:
        return 1
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def bezier_point(
    control_points: List[Tuple[float, float]], t: float
) -> Tuple[float, float]:
    """Evaluate a Bézier curve at parameter *t* ∈ [0, 1].

    Works for any degree (linear, quadratic, cubic, …).
    """
    n = len(control_points) - 1
    x = sum(_bernstein(n, i, t) * p[0] for i, p in enumerate(control_points))
    y = sum(_bernstein(n, i, t) * p[1] for i, p in enumerate(control_points))
    return (x, y)


def bezier_curve(
    control_points: List[Tuple[float, float]], num_points: int = 50
) -> List[Tuple[float, float]]:
    """Sample *num_points* evenly-spaced (in t) points along a Bézier curve."""
    return [
        bezier_point(control_points, t / max(num_points - 1, 1))
        for t in range(num_points)
    ]


# ---------------------------------------------------------------------------
# Speed profile
# ---------------------------------------------------------------------------


def _sigma_speed(t: float, steepness: float = 10.0) -> float:
    """Sigma-shaped speed profile: slow → fast → slow.

    Returns a value ∈ (0, 1) representing the *position* along the
    curve at normalised time *t* ∈ [0, 1].
    """
    return 1.0 / (1.0 + math.exp(-steepness * (t - 0.5)))


def _remap_t(t: float, steepness: float = 10.0) -> float:
    """Re-map linear t to sigma-profile t (normalised to [0, 1])."""
    raw = _sigma_speed(t, steepness)
    lo = _sigma_speed(0, steepness)
    hi = _sigma_speed(1, steepness)
    return (raw - lo) / (hi - lo)


# ---------------------------------------------------------------------------
# Jitter
# ---------------------------------------------------------------------------


def _apply_jitter(
    points: List[Tuple[float, float]],
    amplitude: float = 1.0,
) -> List[Tuple[float, float]]:
    """Add micro-jitter (simulating hand tremor) to interior points.

    First and last points are kept exact.
    """
    if len(points) <= 2 or amplitude <= 0:
        return points

    result = [points[0]]
    for x, y in points[1:-1]:
        jx = x + random.gauss(0, amplitude)
        jy = y + random.gauss(0, amplitude)
        result.append((jx, jy))
    result.append(points[-1])
    return result


# ---------------------------------------------------------------------------
# Overshoot
# ---------------------------------------------------------------------------


def _overshoot_endpoint(
    end: Tuple[float, float],
    distance: float,
    overshoot_frac: float = 0.04,
    angle_range: float = 0.5,
) -> Tuple[float, float]:
    """Generate an overshoot point past *end*.

    Returns a point slightly past the target — the path will then
    curve back to the actual target for a natural "correction" feel.
    """
    angle = random.uniform(-angle_range, angle_range)
    overshoot_dist = distance * overshoot_frac
    dx = overshoot_dist * math.cos(angle)
    dy = overshoot_dist * math.sin(angle)
    return (end[0] + dx, end[1] + dy)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class MouseCurveGenerator:
    """Generate realistic Bézier mouse paths.

    Parameters:
        intensity:       curvature intensity 0–10 (0 = straight, 10 = wild)
        speed_base:      base movement duration in seconds per 1000 px
        jitter_amplitude: hand-tremor jitter in pixels (0 = off)
        overshoot:       whether to add overshoot-and-correct near target
        num_points:      number of sample points along the Bézier curve
        speed_steepness: steepness of the sigma speed profile (higher = snappier)
    """

    def __init__(
        self,
        intensity: float = 5.0,
        speed_base: float = 0.6,
        jitter_amplitude: float = 0.8,
        overshoot: bool = True,
        num_points: int = 60,
        speed_steepness: float = 10.0,
    ):
        self.intensity = max(0.0, min(10.0, intensity))
        self.speed_base = max(0.05, speed_base)
        self.jitter_amplitude = max(0.0, jitter_amplitude)
        self.overshoot = overshoot
        self.num_points = max(5, num_points)
        self.speed_steepness = speed_steepness

    # -- public API ----------------------------------------------------------

    def generate(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: Optional[float] = None,
    ) -> MousePath:
        """Generate a mouse path from *start* to *end*.

        Args:
            start:    (x, y) start pixel
            end:      (x, y) target pixel
            duration: total move duration (seconds); auto-calculated if None

        Returns:
            ``MousePath`` with sampled points and timing.
        """
        sx, sy = float(start[0]), float(start[1])
        ex, ey = float(end[0]), float(end[1])

        dist = math.hypot(ex - sx, ey - sy)
        if dist < 1:
            return MousePath(
                points=[CurvePoint(int(ex), int(ey), 0.0)],
                total_duration=0.0,
                distance=0.0,
            )

        # Auto-duration based on distance
        if duration is None:
            duration = self._auto_duration(dist)

        # 1. Build control points
        ctrl = self._build_control_points(sx, sy, ex, ey, dist)

        # 2. Sample Bézier with sigma speed re-mapping
        raw_points = self._sample_with_speed(ctrl, self.num_points)

        # 3. Overshoot correction
        if self.overshoot and dist > 30:
            raw_points = self._add_overshoot(raw_points, ex, ey, dist)

        # 4. Jitter
        if self.jitter_amplitude > 0:
            jitter_amp = self.jitter_amplitude * (self.intensity / 10.0 + 0.3)
            raw_points = _apply_jitter(raw_points, jitter_amp)

        # 5. Build timed CurvePoints
        points = self._assign_timing(raw_points, duration)

        return MousePath(
            points=points,
            total_duration=sum(p.dt for p in points),
            distance=dist,
            control_points=ctrl,
        )

    def generate_click_path(
        self,
        start: Tuple[int, int],
        target: Tuple[int, int],
        click_offset_range: int = 3,
        duration: Optional[float] = None,
    ) -> MousePath:
        """Generate a path that ends near *target* with a small random offset.

        This mimics real clicks that rarely land on the exact centre.
        """
        ox = random.randint(-click_offset_range, click_offset_range)
        oy = random.randint(-click_offset_range, click_offset_range)
        end = (target[0] + ox, target[1] + oy)
        return self.generate(start, end, duration)

    # -- control points ------------------------------------------------------

    def _build_control_points(
        self, sx: float, sy: float, ex: float, ey: float, dist: float
    ) -> List[Tuple[float, float]]:
        """Build a cubic (or higher-order) Bézier from start to end.

        The number and offset of interior control points depend on
        ``self.intensity``.
        """
        # Fraction of distance used as max perpendicular offset
        offset_frac = 0.05 + 0.15 * (self.intensity / 10.0)

        # Direction vector and normal
        dx, dy = ex - sx, ey - sy
        nx, ny = -dy / dist, dx / dist  # unit normal

        # Number of interior control points: 1–3 based on intensity
        if self.intensity < 2:
            n_inner = 1
        elif self.intensity < 6:
            n_inner = 2
        else:
            n_inner = 3

        ctrl: List[Tuple[float, float]] = [(sx, sy)]

        for i in range(n_inner):
            # Parameter along the line (evenly spaced)
            frac = (i + 1) / (n_inner + 1)
            # Base point on the straight line
            bx = sx + dx * frac
            by = sy + dy * frac
            # Random perpendicular offset
            offset = random.gauss(0, dist * offset_frac)
            cx = bx + nx * offset
            cy = by + ny * offset
            ctrl.append((cx, cy))

        ctrl.append((ex, ey))
        return ctrl

    # -- sampling with speed profile ----------------------------------------

    def _sample_with_speed(
        self, ctrl: List[Tuple[float, float]], n: int
    ) -> List[Tuple[float, float]]:
        """Sample Bézier using sigma-remapped t for realistic speed."""
        points: List[Tuple[float, float]] = []
        for i in range(n):
            t_linear = i / max(n - 1, 1)
            t_curved = _remap_t(t_linear, self.speed_steepness)
            pt = bezier_point(ctrl, t_curved)
            points.append(pt)
        return points

    # -- overshoot -----------------------------------------------------------

    def _add_overshoot(
        self,
        points: List[Tuple[float, float]],
        ex: float,
        ey: float,
        dist: float,
    ) -> List[Tuple[float, float]]:
        """Add overshoot + correction segment at the end of the path."""
        overshoot_frac = 0.02 + 0.03 * (self.intensity / 10.0)
        if random.random() > 0.4:  # 60% chance of overshoot
            over_pt = _overshoot_endpoint((ex, ey), dist, overshoot_frac)
            # Append overshoot then actual target
            n_correction = max(3, self.num_points // 10)
            correction = bezier_curve(
                [points[-1], over_pt, (ex, ey)], n_correction
            )
            points = points + correction[1:]  # skip duplicate
        return points

    # -- timing --------------------------------------------------------------

    def _assign_timing(
        self, points: List[Tuple[float, float]], total_duration: float
    ) -> List[CurvePoint]:
        """Convert raw (x, y) sequence into timed CurvePoints.

        Time is distributed proportional to segment length, so faster
        segments (middle) get less dt, and slow segments (start/end)
        get more dt.
        """
        if not points:
            return []

        # Compute per-segment distances
        seg_dists: List[float] = []
        for i in range(1, len(points)):
            d = math.hypot(points[i][0] - points[i - 1][0],
                           points[i][1] - points[i - 1][1])
            seg_dists.append(max(d, 0.01))

        total_path_len = sum(seg_dists)
        if total_path_len < 0.01:
            total_path_len = 1.0

        result: List[CurvePoint] = [
            CurvePoint(int(round(points[0][0])), int(round(points[0][1])), 0.0)
        ]

        for i, sd in enumerate(seg_dists):
            frac = sd / total_path_len
            dt = total_duration * frac
            # Add tiny random variance to dt (±15%)
            dt *= random.uniform(0.85, 1.15)
            result.append(CurvePoint(
                int(round(points[i + 1][0])),
                int(round(points[i + 1][1])),
                max(dt, 0.0001),
            ))

        return result

    # -- auto duration -------------------------------------------------------

    def _auto_duration(self, distance: float) -> float:
        """Compute duration based on distance (Fitts' law inspired).

        Longer distances → more time, but sub-linearly.
        """
        # Base: speed_base seconds per 1000px
        base = self.speed_base * (distance / 1000.0)
        # Sub-linear (square-root-ish) for long distances
        duration = base * (1.0 + 0.5 * math.log1p(distance / 200.0))
        # Clamp
        duration = max(0.05, min(duration, 3.0))
        # Random ±20%
        duration *= random.uniform(0.8, 1.2)
        return duration
