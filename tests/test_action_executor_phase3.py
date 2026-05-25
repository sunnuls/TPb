#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for action_executor.md — Phase 3: Anti-pattern.

Covers:
- Random delays between actions have sufficient variance
- Key/mouse variance — no two clicks are identical
- Pattern detection: timing, coordinates, intervals must be non-repetitive
- 100 clicks without detectable pattern (key acceptance test)
- Integration: MouseCurveGenerator + HumanizationLayer + ActionExecutor
"""
from __future__ import annotations

import math
import random
import statistics
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mouse_curve_generator import (
    ActionExecutor,
    ActionResult,
    MouseCurveGenerator,
    CurvePoint,
    MousePath,
)
from humanization_layer import (
    HumanizationLayer,
    PlayStyle,
    ActionParams,
)


# ===========================================================================
# Helpers for pattern detection
# ===========================================================================

def _runs_test(sequence: list, threshold: float = 0.05) -> bool:
    """Wald–Wolfowitz runs test for randomness.

    Returns True if sequence appears random (p > threshold).
    Simplified version — checks that runs count is within expected range.
    """
    if len(sequence) < 10:
        return True

    median = statistics.median(sequence)
    binary = [1 if v >= median else 0 for v in sequence]

    # Count runs
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i - 1]:
            runs += 1

    n1 = sum(binary)
    n0 = len(binary) - n1
    if n0 == 0 or n1 == 0:
        return True

    # Expected runs and std
    n = n0 + n1
    expected = 1 + (2 * n0 * n1) / n
    std = math.sqrt((2 * n0 * n1 * (2 * n0 * n1 - n)) / (n * n * (n - 1)))

    if std < 0.001:
        return True

    z = abs(runs - expected) / std
    # z < 1.96 → p > 0.05 → random
    return z < 2.5  # slightly relaxed


def _autocorrelation(values: list, lag: int = 1) -> float:
    """Compute autocorrelation at given lag."""
    n = len(values)
    if n <= lag:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    if var < 1e-12:
        return 0.0
    cov = sum((values[i] - mean) * (values[i + lag] - mean)
              for i in range(n - lag)) / (n - lag)
    return cov / var


# ===========================================================================
# Test: Random delays have variance
# ===========================================================================

class TestRandomDelays(unittest.TestCase):
    """Delays between actions must have sufficient variance."""

    def test_delay_variance(self):
        """100 delays should not be constant."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        delays = [layer.get_action_params("call").delay_before for _ in range(100)]

        # Std dev should be > 0
        self.assertGreater(statistics.stdev(delays), 0.01)

    def test_think_time_variance(self):
        """Think times should vary significantly."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        times = [layer.get_action_params("call").think_time for _ in range(100)]

        self.assertGreater(statistics.stdev(times), 0.05)

    def test_no_constant_interval(self):
        """No two consecutive intervals should be identical."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        totals = [layer.get_action_params("call").total_time for _ in range(100)]

        # Check no consecutive duplicates (within float precision)
        duplicates = sum(1 for i in range(1, len(totals))
                         if abs(totals[i] - totals[i - 1]) < 1e-6)
        self.assertEqual(duplicates, 0)


# ===========================================================================
# Test: Mouse coordinate variance
# ===========================================================================

class TestMouseVariance(unittest.TestCase):
    """No two mouse paths should be identical."""

    def test_path_endpoints_vary(self):
        """Click paths should land at different endpoints (offset)."""
        gen = MouseCurveGenerator(intensity=5)
        endpoints = []
        for _ in range(100):
            path = gen.generate_click_path(
                start=(100, 100), target=(500, 400), click_offset_range=3
            )
            last = path.points[-1]
            endpoints.append((last.x, last.y))

        # Not all the same
        unique = len(set(endpoints))
        self.assertGreater(unique, 10)

    def test_path_shapes_vary(self):
        """Two paths with same start/end should have different shapes."""
        gen = MouseCurveGenerator(intensity=5)
        paths = []
        for _ in range(20):
            path = gen.generate((100, 100), (500, 400))
            # Capture middle point as shape proxy
            mid_idx = path.length // 2
            mid = path.points[mid_idx]
            paths.append((mid.x, mid.y))

        unique = len(set(paths))
        self.assertGreater(unique, 5)

    def test_durations_vary(self):
        """Path durations should not be constant."""
        gen = MouseCurveGenerator(intensity=5)
        durations = [
            gen.generate((100, 100), (500, 400)).total_duration
            for _ in range(50)
        ]
        self.assertGreater(statistics.stdev(durations), 0.001)


# ===========================================================================
# Test: No detectable timing patterns
# ===========================================================================

class TestNoTimingPattern(unittest.TestCase):
    """Timing sequences must pass randomness tests."""

    def test_runs_test_think_times(self):
        """Think times should appear random (runs test)."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        times = [layer.get_action_params("call").think_time for _ in range(100)]
        self.assertTrue(_runs_test(times))

    def test_runs_test_total_times(self):
        """Total times should appear random."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        times = [layer.get_action_params("call").total_time for _ in range(100)]
        self.assertTrue(_runs_test(times))

    def test_low_autocorrelation(self):
        """Consecutive timings should not be strongly correlated."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        times = [layer.get_action_params("call").think_time for _ in range(100)]

        ac1 = _autocorrelation(times, lag=1)
        # Autocorrelation should be weak (< 0.5)
        # Note: fatigue causes slight upward trend, so some correlation is expected
        self.assertLess(abs(ac1), 0.6)

    def test_no_periodic_pattern(self):
        """Check multiple lags for periodicity."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        times = [layer.get_action_params("call").total_time for _ in range(100)]

        for lag in [2, 3, 5, 10]:
            ac = _autocorrelation(times, lag=lag)
            self.assertLess(abs(ac), 0.5,
                            f"Strong autocorrelation at lag {lag}: {ac:.3f}")


# ===========================================================================
# Test: Coordinate patterns
# ===========================================================================

class TestNoCoordinatePattern(unittest.TestCase):
    """Click coordinates must not form a detectable pattern."""

    def test_click_position_distribution(self):
        """Click positions should be distributed around target."""
        gen = MouseCurveGenerator(intensity=5)
        xs, ys = [], []
        for _ in range(100):
            path = gen.generate_click_path(
                start=(100, 100), target=(500, 400), click_offset_range=5
            )
            last = path.points[-1]
            xs.append(last.x)
            ys.append(last.y)

        # Mean should be near target
        self.assertAlmostEqual(statistics.mean(xs), 500, delta=10)
        self.assertAlmostEqual(statistics.mean(ys), 400, delta=10)

        # Should have some spread
        self.assertGreater(statistics.stdev(xs), 0.5)
        self.assertGreater(statistics.stdev(ys), 0.5)

    def test_no_grid_snap(self):
        """Endpoints should not snap to a grid."""
        gen = MouseCurveGenerator(intensity=5)
        xs = []
        for _ in range(100):
            path = gen.generate_click_path(
                start=(100, 100), target=(500, 400), click_offset_range=5
            )
            xs.append(path.points[-1].x)

        # Check that x values don't all share a common factor
        # (indicating grid alignment)
        diffs = [abs(xs[i] - xs[i - 1]) for i in range(1, len(xs)) if xs[i] != xs[i - 1]]
        if len(diffs) > 5:
            unique_diffs = len(set(diffs))
            self.assertGreater(unique_diffs, 3)


# ===========================================================================
# KEY ACCEPTANCE TEST: 100 clicks without pattern
# ===========================================================================

class TestHundredClicksNoPattern(unittest.TestCase):
    """
    Acceptance test from action_executor.md Phase 3:
    100 clicks without detectable pattern.

    Validates that the combined pipeline (Bezier + Humanization + Executor)
    produces non-repetitive, human-like click sequences.
    """

    def test_100_clicks_all_unique_timings(self):
        """100 clicks — all timing values must be unique."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        executor = ActionExecutor(dry_run=True, intensity=5)

        timings = []
        positions = []
        actions = ["fold", "check", "call", "bet", "raise", "all_in"]

        for i in range(100):
            action = actions[i % len(actions)]
            params = layer.get_action_params(action, hand_strength=random.random())

            # Execute click
            target = (500 + random.randint(-50, 50), 400 + random.randint(-50, 50))
            result = executor.click(target=target)

            timings.append(params.total_time)
            positions.append((result.end[0], result.end[1]))

        # All 100 timings should be unique
        self.assertEqual(len(set(timings)), 100)

        # Position uniqueness — high but some may collide due to int rounding
        unique_pos = len(set(positions))
        self.assertGreater(unique_pos, 80)

    def test_100_clicks_pass_runs_test(self):
        """100 clicks — timing sequence passes randomness test."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)

        timings = []
        for i in range(100):
            action = ["fold", "call", "raise"][i % 3]
            params = layer.get_action_params(action)
            timings.append(params.total_time)

        self.assertTrue(_runs_test(timings))

    def test_100_clicks_low_autocorrelation(self):
        """100 clicks — no strong serial correlation in timing."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)

        timings = []
        for i in range(100):
            action = ["fold", "call", "raise", "check"][i % 4]
            params = layer.get_action_params(action, hand_strength=random.random())
            timings.append(params.total_time)

        for lag in [1, 2, 3, 5]:
            ac = _autocorrelation(timings, lag=lag)
            self.assertLess(abs(ac), 0.6,
                            f"Autocorrelation too high at lag {lag}: {ac:.3f}")

    def test_100_clicks_mixed_styles(self):
        """100 clicks across different styles — all succeed, no pattern."""
        styles = [PlayStyle.AGGRESSIVE, PlayStyle.PASSIVE, PlayStyle.NEUTRAL, PlayStyle.TILTED]
        executor = ActionExecutor(dry_run=True)

        all_timings = []
        all_results = []

        for i in range(100):
            style = styles[i % len(styles)]
            layer = HumanizationLayer(style=style, seed=42 + i)
            params = layer.get_action_params("call", hand_strength=0.5)

            target = (500 + random.randint(-30, 30), 400 + random.randint(-30, 30))
            result = executor.click(target=target)

            all_timings.append(params.total_time)
            all_results.append(result)

        # All results should succeed
        self.assertTrue(all(r.success for r in all_results))

        # Sufficient variance in timings
        self.assertGreater(statistics.stdev(all_timings), 0.1)

    def test_100_clicks_no_timing_duplicates(self):
        """Among 100 clicks, no exact duplicate total_time values."""
        layer = HumanizationLayer(style=PlayStyle.RANDOM, seed=42)
        timings = [
            layer.get_action_params(
                ["fold", "call", "raise", "check"][i % 4],
                hand_strength=random.random(),
            ).total_time
            for i in range(100)
        ]
        counter = Counter(timings)
        duplicates = sum(1 for c in counter.values() if c > 1)
        self.assertEqual(duplicates, 0, "Found duplicate timing values")


# ===========================================================================
# Test: Full pipeline integration
# ===========================================================================

class TestFullPipelineIntegration(unittest.TestCase):
    """Integration: HumanizationLayer + MouseCurveGenerator + ActionExecutor."""

    def test_pipeline_produces_valid_results(self):
        """Full pipeline: params → path → action → result."""
        layer = HumanizationLayer(style=PlayStyle.AGGRESSIVE, seed=42)
        executor = ActionExecutor(
            dry_run=True,
            intensity=layer.profile.mouse_intensity,
            speed_base=layer.profile.mouse_speed_base,
            jitter=layer.profile.mouse_jitter,
            overshoot=layer.profile.mouse_overshoot,
        )

        for i in range(20):
            params = layer.get_action_params("raise", hand_strength=0.8)
            result = executor.click(target=(500, 400))
            self.assertTrue(result.success)
            self.assertGreater(result.path_length, 0)

    def test_pipeline_style_switch_mid_session(self):
        """Switch style mid-session — all results valid."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        executor = ActionExecutor(dry_run=True)

        for i in range(50):
            if i == 20:
                layer.set_style(PlayStyle.TILTED)
            if i == 40:
                layer.set_style(PlayStyle.PASSIVE)

            params = layer.get_action_params("call")
            result = executor.click(target=(500, 400))
            self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
