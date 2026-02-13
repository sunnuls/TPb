"""
Tests for AntiPatternExecutor — Phase 3 of action_executor.md.

Core requirement: 100 clicks without detectable pattern.

Tests cover:
  - Single click execution
  - Path, timing, offset variance
  - Pattern detection thresholds
  - 100-click self-test (no pattern)
  - All behavior styles × 100 clicks
  - Pattern detector on synthetic bad data
  - Edge cases

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import statistics
import unittest
from typing import List

try:
    from launcher.vision.anti_pattern_executor import (
        AntiPatternExecutor,
        ClickResult,
        PatternReport,
        PatternDetector,
    )
    from launcher.vision.behavioral_variance import BehaviorStyle, BehaviorProfile
    from launcher.vision.mouse_curve_generator import MousePath, CurvePoint

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Test: Single click
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestSingleClick(unittest.TestCase):
    """Test single click execution."""

    def test_click_returns_result(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(500, 300))
        self.assertIsInstance(r, ClickResult)

    def test_click_has_path(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(500, 300))
        self.assertIsInstance(r.path, MousePath)
        self.assertGreater(r.path.length, 0)

    def test_click_has_think_time(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(500, 300), action="call")
        self.assertGreater(r.think_time, 0)

    def test_click_has_offset(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(500, 300))
        self.assertIsInstance(r.click_offset, tuple)
        self.assertEqual(len(r.click_offset), 2)

    def test_final_position_near_target(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(500, 300))
        d = math.hypot(r.final_x - 500, r.final_y - 300)
        self.assertLess(d, 30, f"Final pos ({r.final_x},{r.final_y}) too far from target")

    def test_click_count_increments(self):
        ex = AntiPatternExecutor(session_seed=42)
        self.assertEqual(ex.click_count, 0)
        ex.execute_click(target=(500, 300))
        self.assertEqual(ex.click_count, 1)
        ex.execute_click(target=(600, 400))
        self.assertEqual(ex.click_count, 2)

    def test_cursor_updates_after_click(self):
        ex = AntiPatternExecutor(session_seed=42, cursor_pos=(100, 100))
        r = ex.execute_click(target=(500, 300))
        # Cursor should now be near the target
        self.assertNotEqual(ex._cursor, (100, 100))


# ---------------------------------------------------------------------------
# Test: Variance across clicks
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestVariance(unittest.TestCase):
    """Verify that repeated clicks to the same target are not identical."""

    def test_different_final_coords(self):
        ex = AntiPatternExecutor(session_seed=42)
        coords = set()
        for _ in range(30):
            r = ex.execute_click(target=(500, 300))
            coords.add((r.final_x, r.final_y))
        # Most should be unique (click offset + jitter)
        self.assertGreater(len(coords), 10)

    def test_different_think_times(self):
        ex = AntiPatternExecutor(session_seed=42)
        times = [ex.execute_click(target=(500, 300), action="call").think_time for _ in range(30)]
        self.assertGreater(statistics.stdev(times), 0.01)

    def test_different_path_durations(self):
        ex = AntiPatternExecutor(session_seed=42)
        durs = [ex.execute_click(target=(500, 300)).path.total_duration for _ in range(30)]
        self.assertGreater(statistics.stdev(durs), 0.001)

    def test_different_path_distances(self):
        """Path distances should vary due to different start positions and offsets."""
        ex = AntiPatternExecutor(session_seed=42)
        dists = [ex.execute_click(target=(500, 300)).path.distance for _ in range(30)]
        # Not all paths should have identical distance
        self.assertGreater(len(set(dists)), 1)


# ---------------------------------------------------------------------------
# Test: Pattern detector on BAD data
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestPatternDetectorBad(unittest.TestCase):
    """Pattern detector should catch obviously robotic patterns."""

    def _make_robotic_results(self, n: int = 100) -> List[ClickResult]:
        """Create results with constant timing, coords, paths."""
        path = MousePath(
            points=[CurvePoint(0, 0, 0), CurvePoint(500, 300, 0.3)],
            total_duration=0.3,
            distance=583.0,
        )
        return [
            ClickResult(
                path=path,
                think_time=1.0,
                inter_delay=2.0,
                click_offset=(0, 0),
                action="call",
            )
            for _ in range(n)
        ]

    def test_detects_fixed_timing(self):
        results = self._make_robotic_results(50)
        report = PatternDetector().analyse(results)
        self.assertTrue(report.pattern_detected, f"Should detect pattern: {report.findings}")

    def test_detects_identical_coords(self):
        results = self._make_robotic_results(50)
        report = PatternDetector().analyse(results)
        self.assertLess(report.coord_unique_frac, 0.05)

    def test_detects_path_similarity(self):
        results = self._make_robotic_results(50)
        report = PatternDetector().analyse(results)
        self.assertGreater(report.path_similarity, 0.8)


# ---------------------------------------------------------------------------
# Test: Pattern detector on GOOD data
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestPatternDetectorGood(unittest.TestCase):
    """Pattern detector should NOT flag humanised data."""

    def test_humanised_passes(self):
        ex = AntiPatternExecutor(session_seed=42)
        results = []
        for i in range(50):
            r = ex.execute_click(target=(500, 300), action=["fold", "call", "raise"][i % 3])
            results.append(r)
        report = PatternDetector().analyse(results)
        self.assertFalse(report.pattern_detected,
                         f"False positive: {report.findings}")


# ---------------------------------------------------------------------------
# Test: 100-click self-test — CORE REQUIREMENT
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestSelfTest100(unittest.TestCase):
    """
    Core requirement from action_executor.md Phase 3:
    100 clicks without detectable pattern.
    """

    def test_100_clicks_balanced_no_pattern(self):
        ex = AntiPatternExecutor(style=BehaviorStyle.BALANCED, session_seed=42)
        report = ex.self_test(n=100, target=(500, 300))

        self.assertEqual(report.n_clicks, 100)
        self.assertFalse(
            report.pattern_detected,
            f"Pattern detected in BALANCED: {report.findings}"
        )
        self.assertGreater(report.delay_cv, PatternDetector.DELAY_CV_MIN)
        self.assertGreater(report.coord_unique_frac, PatternDetector.COORD_UNIQUE_MIN)
        self.assertLess(report.path_similarity, PatternDetector.PATH_SIM_MAX)

    def test_100_clicks_aggressive_no_pattern(self):
        ex = AntiPatternExecutor(style=BehaviorStyle.AGGRESSIVE, session_seed=42)
        report = ex.self_test(n=100, target=(600, 400))

        self.assertEqual(report.n_clicks, 100)
        self.assertFalse(
            report.pattern_detected,
            f"Pattern detected in AGGRESSIVE: {report.findings}"
        )

    def test_100_clicks_passive_no_pattern(self):
        ex = AntiPatternExecutor(style=BehaviorStyle.PASSIVE, session_seed=42)
        report = ex.self_test(n=100, target=(400, 250))

        self.assertEqual(report.n_clicks, 100)
        self.assertFalse(
            report.pattern_detected,
            f"Pattern detected in PASSIVE: {report.findings}"
        )

    def test_100_clicks_erratic_no_pattern(self):
        ex = AntiPatternExecutor(style=BehaviorStyle.ERRATIC, session_seed=42)
        report = ex.self_test(n=100, target=(700, 500))

        self.assertEqual(report.n_clicks, 100)
        self.assertFalse(
            report.pattern_detected,
            f"Pattern detected in ERRATIC: {report.findings}"
        )

    def test_100_clicks_high_coord_uniqueness(self):
        """At least 60% of final click coordinates should be unique.

        With integer pixel coords, some collisions are expected and natural.
        """
        ex = AntiPatternExecutor(session_seed=42)
        report = ex.self_test(n=100, target=(500, 300))
        self.assertGreater(report.coord_unique_frac, 0.60)

    def test_100_clicks_metrics_integrity(self):
        """All report metrics should be within sane ranges."""
        ex = AntiPatternExecutor(session_seed=42)
        report = ex.self_test(n=100, target=(500, 300))
        self.assertGreater(report.delay_cv, 0)
        self.assertGreater(report.coord_unique_frac, 0)
        self.assertLessEqual(report.coord_unique_frac, 1.0)
        self.assertGreaterEqual(report.path_similarity, 0)
        self.assertLessEqual(report.path_similarity, 1.0)
        self.assertGreater(report.timing_cv, 0)


# ---------------------------------------------------------------------------
# Test: Reset
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestReset(unittest.TestCase):
    """Test session reset."""

    def test_reset_clears_results(self):
        ex = AntiPatternExecutor(session_seed=42)
        ex.execute_click(target=(500, 300))
        ex.execute_click(target=(600, 400))
        self.assertEqual(ex.click_count, 2)
        ex.reset()
        self.assertEqual(ex.click_count, 0)

    def test_reset_resets_cursor(self):
        ex = AntiPatternExecutor(session_seed=42)
        ex.execute_click(target=(500, 300))
        ex.reset(cursor_pos=(0, 0))
        self.assertEqual(ex._cursor, (0, 0))


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires anti_pattern_executor")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_click_to_same_position(self):
        """Click where cursor already is."""
        ex = AntiPatternExecutor(cursor_pos=(500, 300), session_seed=42)
        r = ex.execute_click(target=(500, 300))
        self.assertIsInstance(r, ClickResult)

    def test_click_to_corner(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(0, 0))
        self.assertIsInstance(r, ClickResult)

    def test_click_to_large_coords(self):
        ex = AntiPatternExecutor(session_seed=42)
        r = ex.execute_click(target=(3840, 2160))
        self.assertIsInstance(r, ClickResult)

    def test_self_test_small_n(self):
        ex = AntiPatternExecutor(session_seed=42)
        report = ex.self_test(n=3)
        self.assertEqual(report.n_clicks, 3)

    def test_pattern_detector_empty(self):
        d = PatternDetector()
        report = d.analyse([])
        self.assertEqual(report.n_clicks, 0)
        self.assertFalse(report.pattern_detected)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
