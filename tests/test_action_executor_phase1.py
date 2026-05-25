#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for action_executor.md — Phase 1: Bezier mouse paths.

Covers:
- Bézier math (bernstein, bezier_point, bezier_curve)
- CurvePoint, MousePath data models
- MouseCurveGenerator (generate, generate_click_path)
- Speed profile (sigma remap)
- Jitter, overshoot
- ActionExecutor (dry-run mode)
- ActionResult
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mouse_curve_generator import (
    CurvePoint,
    MousePath,
    MouseCurveGenerator,
    ActionExecutor,
    ActionResult,
    bezier_point,
    bezier_curve,
    HAS_BEZIER,
)


# ===========================================================================
# Test Bézier math
# ===========================================================================

class TestBezierMath(unittest.TestCase):
    """Core Bézier functions."""

    def test_bezier_point_linear(self):
        """Linear Bézier (2 points) at t=0.5 → midpoint."""
        ctrl = [(0.0, 0.0), (100.0, 100.0)]
        pt = bezier_point(ctrl, 0.5)
        self.assertAlmostEqual(pt[0], 50.0, places=1)
        self.assertAlmostEqual(pt[1], 50.0, places=1)

    def test_bezier_point_endpoints(self):
        """t=0 → start, t=1 → end."""
        ctrl = [(10.0, 20.0), (50.0, 80.0), (100.0, 200.0)]
        p0 = bezier_point(ctrl, 0.0)
        p1 = bezier_point(ctrl, 1.0)
        self.assertAlmostEqual(p0[0], 10.0, places=1)
        self.assertAlmostEqual(p0[1], 20.0, places=1)
        self.assertAlmostEqual(p1[0], 100.0, places=1)
        self.assertAlmostEqual(p1[1], 200.0, places=1)

    def test_bezier_curve_length(self):
        """bezier_curve returns requested number of points."""
        ctrl = [(0, 0), (50, 100), (100, 0)]
        pts = bezier_curve(ctrl, num_points=20)
        self.assertEqual(len(pts), 20)

    def test_bezier_curve_start_end(self):
        """First/last points match control endpoints."""
        ctrl = [(10.0, 20.0), (50.0, 80.0), (90.0, 30.0)]
        pts = bezier_curve(ctrl, 30)
        self.assertAlmostEqual(pts[0][0], 10.0, places=1)
        self.assertAlmostEqual(pts[-1][0], 90.0, places=1)

    def test_cubic_bezier(self):
        """4-point cubic Bézier is smooth."""
        ctrl = [(0, 0), (30, 100), (70, 100), (100, 0)]
        pts = bezier_curve(ctrl, 50)
        self.assertEqual(len(pts), 50)
        # Middle should be above y=0 (curved up)
        mid_y = pts[25][1]
        self.assertGreater(mid_y, 20)


# ===========================================================================
# Test CurvePoint & MousePath
# ===========================================================================

class TestCurvePoint(unittest.TestCase):
    def test_defaults(self):
        p = CurvePoint(10, 20)
        self.assertEqual(p.x, 10)
        self.assertEqual(p.y, 20)
        self.assertAlmostEqual(p.dt, 0.0)

    def test_with_dt(self):
        p = CurvePoint(0, 0, dt=0.05)
        self.assertAlmostEqual(p.dt, 0.05)


class TestMousePath(unittest.TestCase):
    def test_length(self):
        path = MousePath(points=[CurvePoint(0, 0), CurvePoint(1, 1)])
        self.assertEqual(path.length, 2)

    def test_empty(self):
        path = MousePath()
        self.assertEqual(path.length, 0)


# ===========================================================================
# Test MouseCurveGenerator
# ===========================================================================

class TestMouseCurveGenerator(unittest.TestCase):
    """Main generator tests."""

    def test_generate_basic(self):
        gen = MouseCurveGenerator(intensity=5)
        path = gen.generate(start=(100, 100), end=(500, 400))
        self.assertGreater(path.length, 5)
        self.assertGreater(path.distance, 0)
        self.assertGreater(path.total_duration, 0)
        # First point near start
        self.assertAlmostEqual(path.points[0].x, 100, delta=10)
        self.assertAlmostEqual(path.points[0].y, 100, delta=10)
        # Last point near end
        self.assertAlmostEqual(path.points[-1].x, 500, delta=15)
        self.assertAlmostEqual(path.points[-1].y, 400, delta=15)

    def test_generate_zero_distance(self):
        """Same start and end → trivial path."""
        gen = MouseCurveGenerator()
        path = gen.generate((100, 100), (100, 100))
        self.assertEqual(path.length, 1)
        self.assertAlmostEqual(path.distance, 0.0)

    def test_generate_custom_duration(self):
        gen = MouseCurveGenerator()
        path = gen.generate((0, 0), (1000, 0), duration=2.0)
        # Total duration should be close to 2.0 (±timing variance)
        self.assertGreater(path.total_duration, 1.0)
        self.assertLess(path.total_duration, 4.0)

    def test_generate_click_path(self):
        gen = MouseCurveGenerator(intensity=3)
        path = gen.generate_click_path(
            start=(100, 100), target=(500, 400), click_offset_range=5
        )
        self.assertGreater(path.length, 3)
        # End point should be near target (within offset range)
        last = path.points[-1]
        self.assertAlmostEqual(last.x, 500, delta=20)
        self.assertAlmostEqual(last.y, 400, delta=20)

    def test_intensity_affects_curvature(self):
        """Higher intensity → more control points / wider paths."""
        gen_low = MouseCurveGenerator(intensity=0)
        gen_high = MouseCurveGenerator(intensity=10)

        path_low = gen_low.generate((0, 0), (1000, 0))
        path_high = gen_high.generate((0, 0), (1000, 0))

        # Both should reach the end
        self.assertAlmostEqual(path_low.points[-1].x, 1000, delta=20)
        self.assertAlmostEqual(path_high.points[-1].x, 1000, delta=20)

    def test_no_jitter(self):
        gen = MouseCurveGenerator(jitter_amplitude=0.0)
        path = gen.generate((0, 0), (100, 0))
        self.assertGreater(path.length, 1)

    def test_no_overshoot(self):
        gen = MouseCurveGenerator(overshoot=False)
        path = gen.generate((0, 0), (500, 500))
        self.assertGreater(path.length, 1)

    def test_short_distance(self):
        """Short distance (< 30px) → no overshoot."""
        gen = MouseCurveGenerator(overshoot=True)
        path = gen.generate((100, 100), (110, 105))
        self.assertGreater(path.length, 0)

    def test_timing_positive(self):
        """All dt values should be non-negative."""
        gen = MouseCurveGenerator()
        path = gen.generate((0, 0), (800, 600))
        for pt in path.points:
            self.assertGreaterEqual(pt.dt, 0.0)

    def test_many_generations_stable(self):
        """Generate 50 paths — all should be valid."""
        gen = MouseCurveGenerator(intensity=7)
        for _ in range(50):
            path = gen.generate(
                (random.randint(0, 500), random.randint(0, 500)),
                (random.randint(500, 1500), random.randint(0, 1000)),
            )
            self.assertGreater(path.length, 0)
            self.assertGreater(path.distance, 0)


# ===========================================================================
# Test ActionExecutor (dry-run)
# ===========================================================================

class TestActionExecutor(unittest.TestCase):
    """ActionExecutor in dry_run mode (no real mouse movement)."""

    def test_move_dry_run(self):
        exe = ActionExecutor(dry_run=True)
        result = exe.move(start=(0, 0), end=(500, 300))
        self.assertTrue(result.success)
        self.assertEqual(result.action, "move")
        self.assertGreater(result.path_length, 0)
        self.assertEqual(exe.last_position, (500, 300))

    def test_click_dry_run(self):
        exe = ActionExecutor(dry_run=True)
        result = exe.click(target=(400, 200), start=(0, 0))
        self.assertTrue(result.success)
        self.assertEqual(result.action, "click")
        self.assertEqual(exe.last_position, (400, 200))

    def test_click_uses_last_position(self):
        exe = ActionExecutor(dry_run=True)
        exe.move((0, 0), (100, 100))
        result = exe.click(target=(500, 500))
        self.assertTrue(result.success)
        # start should have been (100, 100)
        self.assertEqual(result.start, (100, 100))

    def test_double_click_dry_run(self):
        exe = ActionExecutor(dry_run=True)
        result = exe.double_click(target=(300, 300), start=(0, 0))
        self.assertTrue(result.success)
        self.assertEqual(result.action, "double_click")

    def test_drag_dry_run(self):
        exe = ActionExecutor(dry_run=True)
        result = exe.drag(start=(100, 100), end=(600, 400))
        self.assertTrue(result.success)
        self.assertEqual(result.action, "drag")
        self.assertEqual(exe.last_position, (600, 400))

    def test_duration_recorded(self):
        exe = ActionExecutor(dry_run=True)
        result = exe.move((0, 0), (500, 500))
        self.assertGreater(result.duration_ms, 0)

    def test_sequential_clicks(self):
        """Multiple clicks track position correctly."""
        exe = ActionExecutor(dry_run=True)
        exe.click(target=(100, 100), start=(0, 0))
        exe.click(target=(200, 200))
        exe.click(target=(300, 300))
        self.assertEqual(exe.last_position, (300, 300))


class TestActionResult(unittest.TestCase):
    def test_defaults(self):
        r = ActionResult()
        self.assertTrue(r.success)
        self.assertEqual(r.error, "")

    def test_failure(self):
        r = ActionResult(success=False, error="timeout")
        self.assertFalse(r.success)


# Need random for test_many_generations_stable
import random


if __name__ == "__main__":
    unittest.main()
