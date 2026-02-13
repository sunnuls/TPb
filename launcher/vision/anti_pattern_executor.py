"""
Anti-Pattern Executor — Phase 3 of action_executor.md.

Orchestrates humanised action execution that passes anti-pattern
detection.  Combines:
  - Bézier mouse curves  (mouse_curve_generator.py)
  - Behavioral variance   (behavioral_variance.py)
  - Random delays with key/mouse variance
  - Pattern-detection self-test

A "click" produced by this module should be statistically
indistinguishable from a human click sequence when analysed for:
  - Fixed inter-click intervals (repeating delays)
  - Fixed mouse paths (same trajectory every time)
  - Fixed click coordinates (always exactly the same pixel)
  - Fixed timing profiles (same speed curve)

Usage::

    exec = AntiPatternExecutor(style=BehaviorStyle.BALANCED)
    result = exec.execute_click(target=(500, 300))
    # result contains the full trajectory, timing, offsets

    # Self-test: 100 clicks should show no detectable patterns
    report = exec.self_test(n=100, target=(500, 300))
    assert report.pattern_detected is False

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from launcher.vision.mouse_curve_generator import (
    MouseCurveGenerator,
    MousePath,
    CurvePoint,
)
from launcher.vision.behavioral_variance import (
    BehaviorProfile,
    BehaviorSampler,
    BehaviorStyle,
    ProfileMixer,
)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ClickResult:
    """Result of a single anti-pattern click execution.

    Attributes:
        path:           the Bézier mouse trajectory used
        think_time:     pre-action delay (seconds)
        inter_delay:    delay since previous click (seconds)
        click_offset:   (dx, dy) from target center
        hovered:        whether cursor hovered before click
        hover_time:     duration of hover (seconds)
        double_click:   accidental double-click?
        action:         the action type string
        timestamp:      when the click was executed
    """
    path: MousePath
    think_time: float
    inter_delay: float
    click_offset: Tuple[int, int] = (0, 0)
    hovered: bool = False
    hover_time: float = 0.0
    double_click: bool = False
    action: str = "click"
    timestamp: float = field(default_factory=time.time)

    @property
    def final_x(self) -> int:
        return self.path.points[-1].x if self.path.points else 0

    @property
    def final_y(self) -> int:
        return self.path.points[-1].y if self.path.points else 0


@dataclass
class PatternReport:
    """Result of the anti-pattern self-test.

    Attributes:
        n_clicks:           total clicks tested
        pattern_detected:   True if any pattern was found
        delay_cv:           coefficient of variation of inter-delays
        coord_unique_frac:  fraction of unique final coordinates
        path_similarity:    average pairwise path similarity (0–1; 1=identical)
        timing_cv:          CV of total move durations
        findings:           list of detected issues (empty = good)
    """
    n_clicks: int = 0
    pattern_detected: bool = False
    delay_cv: float = 0.0
    coord_unique_frac: float = 1.0
    path_similarity: float = 0.0
    timing_cv: float = 0.0
    findings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern detector (self-test analyser)
# ---------------------------------------------------------------------------


class PatternDetector:
    """Analyse a batch of ClickResults for detectable patterns.

    Thresholds:
      - delay_cv < 0.10  → suspiciously regular timing
      - coord_unique < 0.50 → too many identical coords
      - path_similarity > 0.85 → mouse paths too alike
      - timing_cv < 0.08 → move durations too uniform
    """

    DELAY_CV_MIN = 0.10
    COORD_UNIQUE_MIN = 0.50
    PATH_SIM_MAX = 0.85
    TIMING_CV_MIN = 0.08

    def analyse(self, results: List[ClickResult]) -> PatternReport:
        if len(results) < 2:
            return PatternReport(n_clicks=len(results))

        findings: List[str] = []

        # 1. Inter-delay regularity
        delays = [r.inter_delay for r in results if r.inter_delay > 0]
        delay_cv = self._cv(delays)
        if delay_cv < self.DELAY_CV_MIN and len(delays) > 5:
            findings.append(
                f"Delay CV={delay_cv:.3f} < {self.DELAY_CV_MIN} — timing too regular"
            )

        # 2. Coordinate uniqueness
        coords = [(r.final_x, r.final_y) for r in results]
        unique_frac = len(set(coords)) / len(coords)
        if unique_frac < self.COORD_UNIQUE_MIN:
            findings.append(
                f"Unique coords={unique_frac:.2%} < {self.COORD_UNIQUE_MIN:.0%} — repeated positions"
            )

        # 3. Path similarity (sample pairs)
        path_sim = self._avg_path_similarity(results)
        if path_sim > self.PATH_SIM_MAX:
            findings.append(
                f"Path similarity={path_sim:.3f} > {self.PATH_SIM_MAX} — paths too alike"
            )

        # 4. Timing profile regularity
        durations = [r.path.total_duration for r in results if r.path.total_duration > 0]
        timing_cv = self._cv(durations)
        if timing_cv < self.TIMING_CV_MIN and len(durations) > 5:
            findings.append(
                f"Timing CV={timing_cv:.3f} < {self.TIMING_CV_MIN} — move durations too uniform"
            )

        return PatternReport(
            n_clicks=len(results),
            pattern_detected=len(findings) > 0,
            delay_cv=delay_cv,
            coord_unique_frac=unique_frac,
            path_similarity=path_sim,
            timing_cv=timing_cv,
            findings=findings,
        )

    @staticmethod
    def _cv(values: List[float]) -> float:
        """Coefficient of variation (std / mean)."""
        if len(values) < 2:
            return 1.0
        mean = statistics.mean(values)
        if mean == 0:
            return 1.0
        return statistics.stdev(values) / mean

    @staticmethod
    def _avg_path_similarity(
        results: List[ClickResult], max_pairs: int = 50
    ) -> float:
        """Sample pairwise path similarity (cosine-like metric on path shapes)."""
        if len(results) < 2:
            return 0.0

        pairs = min(max_pairs, len(results) * (len(results) - 1) // 2)
        sims: List[float] = []

        indices = list(range(len(results)))
        for _ in range(pairs):
            i, j = random.sample(indices, 2)
            s = PatternDetector._path_sim(results[i].path, results[j].path)
            sims.append(s)

        return statistics.mean(sims) if sims else 0.0

    @staticmethod
    def _path_sim(a: MousePath, b: MousePath) -> float:
        """Compute similarity between two paths (0 = different, 1 = identical).

        Samples 20 evenly-spaced points and computes normalised distance.
        """
        n = 20
        if a.length < 2 or b.length < 2:
            return 0.0

        def _sample(path: MousePath, k: int) -> List[Tuple[int, int]]:
            step = max(1, (path.length - 1) / (k - 1))
            return [
                (path.points[min(int(i * step), path.length - 1)].x,
                 path.points[min(int(i * step), path.length - 1)].y)
                for i in range(k)
            ]

        sa = _sample(a, n)
        sb = _sample(b, n)

        total_dist = sum(
            math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            for pa, pb in zip(sa, sb)
        )

        # Normalise by diagonal of bounding box
        max_dim = max(a.distance, b.distance, 1.0)
        avg_dist = total_dist / n
        sim = max(0.0, 1.0 - avg_dist / max_dim)
        return sim


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------


class AntiPatternExecutor:
    """Humanised click executor that defeats pattern detection.

    Combines Bézier mouse curves, behavioral profiles, and randomised
    delays to produce non-repeating, human-like click sequences.

    Parameters:
        style:          behavior profile style
        profile:        explicit profile (overrides style)
        session_seed:   RNG seed for reproducibility
        cursor_pos:     initial cursor position (x, y)
    """

    def __init__(
        self,
        style: BehaviorStyle = BehaviorStyle.BALANCED,
        profile: Optional[BehaviorProfile] = None,
        session_seed: Optional[int] = None,
        cursor_pos: Tuple[int, int] = (960, 540),
    ):
        if profile is None:
            profile = {
                BehaviorStyle.AGGRESSIVE: BehaviorProfile.aggressive,
                BehaviorStyle.PASSIVE: BehaviorProfile.passive,
                BehaviorStyle.BALANCED: BehaviorProfile.balanced,
                BehaviorStyle.ERRATIC: BehaviorProfile.erratic,
            }.get(style, BehaviorProfile.balanced)()

        self._sampler = BehaviorSampler(profile, session_seed=session_seed)
        self._cursor = cursor_pos
        self._results: List[ClickResult] = []
        self._last_time = time.monotonic()

    # -- public API ----------------------------------------------------------

    def execute_click(
        self,
        target: Tuple[int, int],
        action: str = "click",
    ) -> ClickResult:
        """Simulate a single humanised click at *target*.

        Does NOT actually move the mouse or click — it produces the
        complete plan (path, timings, offsets) that a real executor
        would replay.

        Returns:
            ``ClickResult`` with all execution details.
        """
        now = time.monotonic()
        inter_delay = now - self._last_time

        # 1. Think time
        think_time = self._sampler.sample_think_time(action)

        # 2. Mouse config
        mcfg = self._sampler.sample_mouse_config()

        # 3. Click offset (integer base + continuous Gaussian jitter)
        offset = self._sampler.sample_click_offset()
        # Add continuous random displacement for higher coord uniqueness
        extra_dx = self._sampler._rng.gauss(0, 2.5)
        extra_dy = self._sampler._rng.gauss(0, 2.5)
        end = (
            int(round(target[0] + offset[0] + extra_dx)),
            int(round(target[1] + offset[1] + extra_dy)),
        )

        # 4. Build mouse curve
        gen = MouseCurveGenerator(
            intensity=mcfg["curve_intensity"],
            speed_base=0.6 * mcfg["speed_mult"],
            jitter_amplitude=mcfg["jitter"],
            overshoot=bool(mcfg["overshoot"]),
        )
        path = gen.generate(start=self._cursor, end=end)

        # 5. Hover?
        hovered = self._sampler.sample_should_hover()
        hover_time = self._sampler.sample_hover_time() if hovered else 0.0

        # 6. Double click?
        double = self._sampler.sample_double_click_prob()

        result = ClickResult(
            path=path,
            think_time=think_time,
            inter_delay=inter_delay,
            click_offset=offset,
            hovered=hovered,
            hover_time=hover_time,
            double_click=double,
            action=action,
        )

        # Update state
        self._cursor = end
        self._last_time = time.monotonic()
        self._results.append(result)

        return result

    def self_test(
        self,
        n: int = 100,
        target: Tuple[int, int] = (500, 300),
        actions: Optional[List[str]] = None,
    ) -> PatternReport:
        """Run *n* clicks and check for detectable patterns.

        Args:
            n:       number of clicks
            target:  button center to click
            actions: list of action types to cycle through

        Returns:
            ``PatternReport`` — ``pattern_detected`` should be False.
        """
        if actions is None:
            actions = ["fold", "check", "call", "bet", "raise", "allin"]

        results: List[ClickResult] = []
        for i in range(n):
            act = actions[i % len(actions)]
            r = self.execute_click(target=target, action=act)
            results.append(r)

        detector = PatternDetector()
        return detector.analyse(results)

    @property
    def results(self) -> List[ClickResult]:
        return list(self._results)

    @property
    def click_count(self) -> int:
        return len(self._results)

    def reset(self, cursor_pos: Tuple[int, int] = (960, 540)):
        """Reset session state."""
        self._results.clear()
        self._cursor = cursor_pos
        self._last_time = time.monotonic()
        self._sampler.reset_drift()
