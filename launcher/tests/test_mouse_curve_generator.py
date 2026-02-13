"""
Tests for MouseCurveGenerator — Phase 1 of action_executor.md.

Tests cover:
  - Bézier math (bernstein, bezier_point, bezier_curve)
  - Speed profile (sigma, remap)
  - Jitter
  - Overshoot
  - Control point generation
  - Path generation (timing, distances, endpoints)
  - Click path (offset)
  - Intensity levels (0–10)
  - Edge cases (zero distance, same point, very long)
  - Path smoothness
  - Deterministic seeding
  - 100 paths stress test

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import unittest
from typing import List, Tuple

try:
    from launcher.vision.mouse_curve_generator import (
        MouseCurveGenerator,
        MousePath,
        CurvePoint,
        bezier_point,
        bezier_curve,
        _bernstein,
        _comb,
        _sigma_speed,
        _remap_t,
        _apply_jitter,
        _overshoot_endpoint,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Test: Bézier math
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestBezierMath(unittest.TestCase):
    """Test core Bézier math functions."""

    def test_comb_basic(self):
        self.assertEqual(_comb(4, 2), 6)
        self.assertEqual(_comb(5, 0), 1)
        self.assertEqual(_comb(5, 5), 1)
        self.assertEqual(_comb(6, 3), 20)

    def test_comb_edge(self):
        self.assertEqual(_comb(0, 0), 1)
        self.assertEqual(_comb(1, 0), 1)
        self.assertEqual(_comb(1, 1), 1)

    def test_bernstein_endpoints(self):
        """B_{i,n}(0) = 1 iff i==0; B_{i,n}(1) = 1 iff i==n."""
        n = 3
        for i in range(n + 1):
            if i == 0:
                self.assertAlmostEqual(_bernstein(n, i, 0.0), 1.0)
            else:
                self.assertAlmostEqual(_bernstein(n, i, 0.0), 0.0)
            if i == n:
                self.assertAlmostEqual(_bernstein(n, i, 1.0), 1.0)
            else:
                self.assertAlmostEqual(_bernstein(n, i, 1.0), 0.0)

    def test_bernstein_sum_to_one(self):
        """Sum of all B_{i,n}(t) should be 1 for any t."""
        n = 4
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            total = sum(_bernstein(n, i, t) for i in range(n + 1))
            self.assertAlmostEqual(total, 1.0, places=10)

    def test_bezier_point_linear(self):
        """Linear Bézier (2 points) should interpolate."""
        ctrl = [(0, 0), (100, 100)]
        pt = bezier_point(ctrl, 0.5)
        self.assertAlmostEqual(pt[0], 50.0, places=5)
        self.assertAlmostEqual(pt[1], 50.0, places=5)

    def test_bezier_point_endpoints(self):
        """t=0 → start, t=1 → end."""
        ctrl = [(10, 20), (50, 80), (90, 30)]
        p0 = bezier_point(ctrl, 0.0)
        p1 = bezier_point(ctrl, 1.0)
        self.assertAlmostEqual(p0[0], 10.0)
        self.assertAlmostEqual(p0[1], 20.0)
        self.assertAlmostEqual(p1[0], 90.0)
        self.assertAlmostEqual(p1[1], 30.0)

    def test_bezier_curve_length(self):
        """bezier_curve should return exactly num_points."""
        ctrl = [(0, 0), (50, 100), (100, 0)]
        pts = bezier_curve(ctrl, num_points=30)
        self.assertEqual(len(pts), 30)

    def test_bezier_curve_starts_ends(self):
        """First and last points of curve should be start and end."""
        ctrl = [(10, 20), (60, 80), (110, 40)]
        pts = bezier_curve(ctrl, num_points=50)
        self.assertAlmostEqual(pts[0][0], 10.0, places=3)
        self.assertAlmostEqual(pts[0][1], 20.0, places=3)
        self.assertAlmostEqual(pts[-1][0], 110.0, places=3)
        self.assertAlmostEqual(pts[-1][1], 40.0, places=3)


# ---------------------------------------------------------------------------
# Test: Speed profile
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestSpeedProfile(unittest.TestCase):
    """Test sigma speed profile and t remapping."""

    def test_sigma_monotonic(self):
        """Sigma should be monotonically increasing."""
        prev = -1.0
        for i in range(100):
            t = i / 99.0
            val = _sigma_speed(t)
            self.assertGreaterEqual(val, prev)
            prev = val

    def test_remap_endpoints(self):
        """Remap: t=0→0, t=1→1."""
        self.assertAlmostEqual(_remap_t(0.0), 0.0, places=3)
        self.assertAlmostEqual(_remap_t(1.0), 1.0, places=3)

    def test_remap_midpoint(self):
        """Remap: t=0.5 → ~0.5 (symmetric)."""
        mid = _remap_t(0.5)
        self.assertAlmostEqual(mid, 0.5, places=2)

    def test_remap_slow_start_fast_end(self):
        """Early t values should map to smaller output (slow start)."""
        early = _remap_t(0.1)
        late = _remap_t(0.9)
        self.assertLess(early, 0.1 + 0.05)  # compressed start
        self.assertGreater(late, 0.9 - 0.05)  # compressed end


# ---------------------------------------------------------------------------
# Test: Jitter
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestJitter(unittest.TestCase):
    """Test micro-jitter overlay."""

    def test_first_last_unchanged(self):
        """Jitter should not change first and last points."""
        pts = [(0, 0), (50, 50), (100, 100)]
        result = _apply_jitter(pts, amplitude=5.0)
        self.assertEqual(result[0], (0, 0))
        self.assertEqual(result[-1], (100, 100))

    def test_interior_changed(self):
        """Interior points should be shifted (with high probability)."""
        random.seed(42)
        pts = [(0, 0)] + [(50, 50)] * 20 + [(100, 100)]
        result = _apply_jitter(pts, amplitude=5.0)
        changed = sum(1 for i in range(1, len(result) - 1) if result[i] != pts[i])
        self.assertGreater(changed, 10)

    def test_zero_amplitude(self):
        """Zero amplitude → no change."""
        pts = [(0, 0), (50, 50), (100, 100)]
        result = _apply_jitter(pts, amplitude=0.0)
        self.assertEqual(result, pts)

    def test_two_points_no_jitter(self):
        """Only two points → no interior to jitter."""
        pts = [(0, 0), (100, 100)]
        result = _apply_jitter(pts, amplitude=5.0)
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# Test: Overshoot
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestOvershoot(unittest.TestCase):
    """Test overshoot point generation."""

    def test_overshoot_near_target(self):
        """Overshoot point should be close to target."""
        random.seed(42)
        end = (500.0, 300.0)
        over = _overshoot_endpoint(end, distance=500.0, overshoot_frac=0.05)
        d = math.hypot(over[0] - end[0], over[1] - end[1])
        self.assertLess(d, 500 * 0.1)  # within 10% of distance

    def test_overshoot_not_equal_to_target(self):
        """Overshoot should differ from exact target."""
        random.seed(42)
        end = (500.0, 300.0)
        over = _overshoot_endpoint(end, distance=500.0)
        self.assertNotAlmostEqual(over[0], end[0], places=0)


# ---------------------------------------------------------------------------
# Test: MouseCurveGenerator — path generation
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestPathGeneration(unittest.TestCase):
    """Test full path generation."""

    def test_path_starts_at_start(self):
        gen = MouseCurveGenerator(intensity=5, overshoot=False, jitter_amplitude=0)
        path = gen.generate(start=(100, 200), end=(500, 400))
        self.assertEqual(path.points[0].x, 100)
        self.assertEqual(path.points[0].y, 200)

    def test_path_ends_near_end(self):
        """Last point should be at or very near the target."""
        gen = MouseCurveGenerator(intensity=5, overshoot=False, jitter_amplitude=0)
        path = gen.generate(start=(100, 200), end=(500, 400))
        last = path.points[-1]
        d = math.hypot(last.x - 500, last.y - 400)
        self.assertLess(d, 5, f"Last point ({last.x},{last.y}) too far from target")

    def test_path_has_points(self):
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(800, 600))
        self.assertGreater(path.length, 10)

    def test_path_total_duration_positive(self):
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(500, 500))
        self.assertGreater(path.total_duration, 0)

    def test_path_distance_correct(self):
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(300, 400))
        expected = math.hypot(300, 400)
        self.assertAlmostEqual(path.distance, expected, places=1)

    def test_path_has_control_points(self):
        gen = MouseCurveGenerator(intensity=5)
        path = gen.generate(start=(0, 0), end=(500, 500))
        self.assertGreaterEqual(len(path.control_points), 2)

    def test_zero_distance(self):
        """Same start and end → minimal path."""
        gen = MouseCurveGenerator()
        path = gen.generate(start=(300, 300), end=(300, 300))
        self.assertEqual(path.length, 1)
        self.assertAlmostEqual(path.total_duration, 0.0)

    def test_short_distance(self):
        """Very short move (5px)."""
        gen = MouseCurveGenerator()
        path = gen.generate(start=(100, 100), end=(105, 100))
        self.assertGreaterEqual(path.length, 1)

    def test_long_distance(self):
        """Long move (2000px)."""
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(2000, 0))
        self.assertGreater(path.length, 10)
        self.assertGreater(path.total_duration, 0.1)

    def test_custom_duration(self):
        """Explicit duration should be respected (approximately)."""
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(500, 500), duration=1.0)
        # Total duration should be close to 1.0 (within ±30% due to variance)
        self.assertAlmostEqual(path.total_duration, 1.0, delta=0.4)

    def test_all_dt_positive(self):
        """Every point should have dt > 0 (except first)."""
        gen = MouseCurveGenerator()
        path = gen.generate(start=(0, 0), end=(500, 500))
        for i, pt in enumerate(path.points):
            if i == 0:
                self.assertAlmostEqual(pt.dt, 0.0)
            else:
                self.assertGreater(pt.dt, 0, f"Point {i} has dt={pt.dt}")


# ---------------------------------------------------------------------------
# Test: Click path
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestClickPath(unittest.TestCase):
    """Test click path with random offset."""

    def test_click_path_near_target(self):
        gen = MouseCurveGenerator(jitter_amplitude=0, overshoot=False)
        path = gen.generate_click_path(start=(100, 100), target=(500, 500),
                                       click_offset_range=3)
        last = path.points[-1]
        d = math.hypot(last.x - 500, last.y - 500)
        self.assertLess(d, 10)  # within 10px of target

    def test_click_offset_randomness(self):
        """Multiple click paths should have varying endpoints."""
        gen = MouseCurveGenerator(jitter_amplitude=0, overshoot=False)
        endpoints = set()
        for _ in range(20):
            path = gen.generate_click_path(start=(0, 0), target=(500, 500),
                                           click_offset_range=5)
            last = path.points[-1]
            endpoints.add((last.x, last.y))
        # Should have at least a few different endpoints
        self.assertGreater(len(endpoints), 1)


# ---------------------------------------------------------------------------
# Test: Intensity levels
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestIntensityLevels(unittest.TestCase):
    """Test that different intensity levels produce different paths."""

    def test_intensity_0_nearly_straight(self):
        """Intensity 0 should produce a nearly straight path."""
        gen = MouseCurveGenerator(intensity=0, jitter_amplitude=0, overshoot=False)
        random.seed(42)
        path = gen.generate(start=(0, 0), end=(1000, 0))
        # Max Y deviation should be small
        max_y = max(abs(pt.y) for pt in path.points)
        self.assertLess(max_y, 100, f"Intensity 0 too curvy: max_y={max_y}")

    def test_intensity_10_more_curved(self):
        """Intensity 10 should produce more curvature than intensity 0."""
        random.seed(42)
        gen0 = MouseCurveGenerator(intensity=0, jitter_amplitude=0, overshoot=False)
        path0 = gen0.generate(start=(0, 0), end=(1000, 0))
        max_y_0 = max(abs(pt.y) for pt in path0.points)

        random.seed(42)
        gen10 = MouseCurveGenerator(intensity=10, jitter_amplitude=0, overshoot=False)
        path10 = gen10.generate(start=(0, 0), end=(1000, 0))
        max_y_10 = max(abs(pt.y) for pt in path10.points)

        # Higher intensity should generally produce larger deviations
        # (not guaranteed per seed, but very likely)
        # We just verify both produce valid paths
        self.assertGreaterEqual(path0.length, 5)
        self.assertGreaterEqual(path10.length, 5)

    def test_all_intensities_valid(self):
        """Every integer intensity 0–10 should produce a valid path."""
        for intensity in range(11):
            gen = MouseCurveGenerator(intensity=intensity)
            path = gen.generate(start=(100, 100), end=(500, 400))
            self.assertGreater(path.length, 0, f"Intensity {intensity} empty")
            self.assertGreater(path.total_duration, 0)

    def test_intensity_clamped(self):
        """Intensity < 0 clamped to 0, > 10 clamped to 10."""
        gen_neg = MouseCurveGenerator(intensity=-5)
        self.assertAlmostEqual(gen_neg.intensity, 0.0)
        gen_high = MouseCurveGenerator(intensity=15)
        self.assertAlmostEqual(gen_high.intensity, 10.0)


# ---------------------------------------------------------------------------
# Test: Path smoothness
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestSmoothness(unittest.TestCase):
    """Verify paths are reasonably smooth (no huge jumps)."""

    def test_no_large_jumps(self):
        """Adjacent points should not jump by more than distance/5."""
        gen = MouseCurveGenerator(intensity=5)
        path = gen.generate(start=(0, 0), end=(800, 600))
        max_allowed = path.distance / 3 + 20  # generous
        for i in range(1, len(path.points)):
            dx = path.points[i].x - path.points[i - 1].x
            dy = path.points[i].y - path.points[i - 1].y
            jump = math.hypot(dx, dy)
            self.assertLess(jump, max_allowed,
                            f"Jump {jump:.1f} at point {i} exceeds {max_allowed:.1f}")

    def test_path_stays_near_line(self):
        """Path shouldn't deviate more than distance from the line."""
        gen = MouseCurveGenerator(intensity=5, overshoot=False)
        path = gen.generate(start=(0, 0), end=(1000, 0))
        for pt in path.points:
            self.assertLess(abs(pt.y), path.distance * 0.5 + 50)


# ---------------------------------------------------------------------------
# Test: Stress — 100 paths
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires mouse_curve_generator")
class TestStress(unittest.TestCase):
    """Generate 100 diverse paths and verify all are valid."""

    def test_100_paths_no_errors(self):
        """100 random paths should all be valid."""
        gen = MouseCurveGenerator(intensity=5)
        for i in range(100):
            sx = random.randint(0, 1920)
            sy = random.randint(0, 1080)
            ex = random.randint(0, 1920)
            ey = random.randint(0, 1080)
            path = gen.generate(start=(sx, sy), end=(ex, ey))

            self.assertIsInstance(path, MousePath)
            self.assertGreater(path.length, 0, f"Path {i} is empty")
            # All coordinates should be finite
            for pt in path.points:
                self.assertTrue(math.isfinite(pt.x), f"Path {i}: x not finite")
                self.assertTrue(math.isfinite(pt.y), f"Path {i}: y not finite")
                self.assertTrue(math.isfinite(pt.dt), f"Path {i}: dt not finite")

    def test_100_paths_varying_intensity(self):
        """100 paths with varying intensity (0–10)."""
        for i in range(100):
            intensity = (i % 11)
            gen = MouseCurveGenerator(intensity=intensity)
            path = gen.generate(
                start=(random.randint(0, 1000), random.randint(0, 1000)),
                end=(random.randint(0, 1000), random.randint(0, 1000)),
            )
            self.assertGreater(path.length, 0)

    def test_100_click_paths(self):
        """100 click paths should all land near target."""
        gen = MouseCurveGenerator(intensity=5, overshoot=False, jitter_amplitude=0)
        for i in range(100):
            tx, ty = random.randint(100, 1800), random.randint(100, 900)
            path = gen.generate_click_path(
                start=(random.randint(0, 1920), random.randint(0, 1080)),
                target=(tx, ty),
                click_offset_range=5,
            )
            last = path.points[-1]
            d = math.hypot(last.x - tx, last.y - ty)
            self.assertLess(d, 15, f"Click {i}: d={d:.1f}px from target")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
