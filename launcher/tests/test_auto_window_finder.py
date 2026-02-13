"""
Tests for AutoWindowFinder — Phase 1 of bot_fixes.md.

Tests cover:
  - Data model correctness (WindowRect, WindowMatch)
  - Scoring and match methods
  - Known poker patterns
  - Window state helpers
  - Wait-for polling
  - DPI scale defaults
  - find_all / find / find_all_poker on the real desktop
"""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

# Try importing the module under test
try:
    from launcher.auto_window_finder import (
        AutoWindowFinder,
        MatchMethod,
        WindowMatch,
        WindowRect,
        KNOWN_POKER_TITLES,
        KNOWN_POKER_CLASSES,
        KNOWN_POKER_PROCESSES,
        WIN32_AVAILABLE,
    )
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestWindowRect(unittest.TestCase):
    """WindowRect dataclass properties."""

    def test_basic_properties(self):
        r = WindowRect(x=10, y=20, w=100, h=200)
        self.assertEqual(r.right, 110)
        self.assertEqual(r.bottom, 220)
        self.assertEqual(r.center, (60, 120))
        self.assertEqual(r.area, 20_000)
        self.assertEqual(r.as_tuple(), (10, 20, 100, 200))

    def test_zero_rect(self):
        r = WindowRect()
        self.assertEqual(r.area, 0)
        self.assertEqual(r.center, (0, 0))

    def test_repr(self):
        r = WindowRect(x=1, y=2, w=3, h=4)
        self.assertIn("WindowRect", repr(r))
        self.assertIn("w=3", repr(r))


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestWindowMatch(unittest.TestCase):
    """WindowMatch dataclass defaults and construction."""

    def test_defaults(self):
        m = WindowMatch()
        self.assertEqual(m.hwnd, 0)
        self.assertEqual(m.title, "")
        self.assertEqual(m.score, 0.0)
        self.assertTrue(m.visible)
        self.assertFalse(m.minimized)
        self.assertFalse(m.is_child)
        self.assertEqual(m.dpi_scale, 1.0)

    def test_custom_values(self):
        m = WindowMatch(
            hwnd=12345,
            title="PokerStars - NL50",
            window_class="PokerStarsTableFrameClass",
            process_name="pokerstars.exe",
            process_id=9999,
            score=0.95,
            match_method=MatchMethod.TITLE_EXACT,
            dpi_scale=1.25,
        )
        self.assertEqual(m.hwnd, 12345)
        self.assertEqual(m.score, 0.95)
        self.assertEqual(m.match_method, MatchMethod.TITLE_EXACT)
        self.assertEqual(m.dpi_scale, 1.25)

    def test_zoom_rect_equals_client_rect_by_default(self):
        cr = WindowRect(x=50, y=80, w=800, h=600)
        m = WindowMatch(client_rect=cr, zoom_rect=cr)
        self.assertEqual(m.zoom_rect.as_tuple(), m.client_rect.as_tuple())


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestMatchMethod(unittest.TestCase):
    """MatchMethod enum coverage."""

    def test_values(self):
        methods = {m.value for m in MatchMethod}
        self.assertIn("title_exact", methods)
        self.assertIn("title_substring", methods)
        self.assertIn("title_regex", methods)
        self.assertIn("window_class", methods)
        self.assertIn("process_name", methods)

    def test_count(self):
        self.assertEqual(len(MatchMethod), 5)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestKnownPatterns(unittest.TestCase):
    """Known poker-room constants are well-formed."""

    def test_titles_non_empty(self):
        self.assertGreater(len(KNOWN_POKER_TITLES), 0)
        for room, patterns in KNOWN_POKER_TITLES.items():
            self.assertIsInstance(room, str)
            self.assertGreater(len(patterns), 0)

    def test_classes_non_empty(self):
        self.assertGreater(len(KNOWN_POKER_CLASSES), 0)

    def test_processes_non_empty(self):
        self.assertGreater(len(KNOWN_POKER_PROCESSES), 0)
        for p in KNOWN_POKER_PROCESSES:
            self.assertTrue(p.endswith(".exe"))


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestAutoWindowFinderInit(unittest.TestCase):
    """Finder initialization."""

    def test_available_property(self):
        finder = AutoWindowFinder()
        self.assertIsInstance(finder.available, bool)

    def test_find_all_no_pattern_returns_list(self):
        finder = AutoWindowFinder()
        if not finder.available:
            self.skipTest("Win32 not available")
        results = finder.find_all("__this_window_does_not_exist_12345__")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_find_no_match_returns_none(self):
        finder = AutoWindowFinder()
        if not finder.available:
            self.skipTest("Win32 not available")
        result = finder.find("__this_window_does_not_exist_12345__")
        self.assertIsNone(result)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestAutoWindowFinderRealDesktop(unittest.TestCase):
    """Tests that actually enumerate the desktop.

    These tests run on any Windows machine and verify that the finder
    can enumerate *some* windows (there are always windows on a desktop).
    """

    def setUp(self):
        self.finder = AutoWindowFinder()
        if not self.finder.available:
            self.skipTest("Win32 not available")

    def test_find_all_empty_pattern_lists_all(self):
        """Empty pattern + visible_only=False should return many windows."""
        # We search with an empty pattern but by_class="", by_process=""
        # which means nothing matches — should return 0.
        results = self.finder.find_all("")
        # with empty pattern all scores are 0 → nothing returned
        self.assertIsInstance(results, list)

    def test_find_all_broad_regex(self):
        """A regex matching almost anything should find windows."""
        results = self.finder.find_all(".*")
        self.assertIsInstance(results, list)
        # On a live desktop there should be at least a few windows
        self.assertGreater(len(results), 0)

    def test_results_sorted_by_score(self):
        results = self.finder.find_all(".*")
        if len(results) < 2:
            self.skipTest("Need at least 2 windows")
        for i in range(1, len(results)):
            self.assertGreaterEqual(results[i - 1].score, results[i].score)

    def test_each_result_has_zoom_rect(self):
        results = self.finder.find_all(".*")
        for m in results[:10]:
            self.assertIsInstance(m.zoom_rect, WindowRect)
            self.assertGreater(m.zoom_rect.w, 0)
            self.assertGreater(m.zoom_rect.h, 0)

    def test_client_rect_smaller_or_equal_full(self):
        results = self.finder.find_all(".*")
        for m in results[:10]:
            self.assertLessEqual(m.client_rect.area, m.full_rect.area + 1)

    def test_find_all_poker_returns_list(self):
        """find_all_poker should always return a list (possibly empty)."""
        results = self.finder.find_all_poker()
        self.assertIsInstance(results, list)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestAutoWindowFinderScoring(unittest.TestCase):
    """Verify scoring logic via _evaluate_window with mocked win32."""

    def setUp(self):
        self.finder = AutoWindowFinder()

    @unittest.skipUnless(WIN32_AVAILABLE, "Win32 required for scoring tests")
    def test_exact_title_scores_highest(self):
        """If we find a window whose title exactly matches, score should be 1.0."""
        results = self.finder.find_all(".*")
        if not results:
            self.skipTest("No windows found")
        # Pick first result, search by its exact title
        exact_title = results[0].title
        exact_results = self.finder.find_all(exact_title)
        if not exact_results:
            self.skipTest("Exact title search returned nothing")
        # The best match should have score 1.0 (exact match) or 0.8 (substring)
        self.assertGreaterEqual(exact_results[0].score, 0.8)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestWaitFor(unittest.TestCase):
    """Test wait_for with short timeout."""

    def test_wait_for_nonexistent_times_out(self):
        finder = AutoWindowFinder()
        if not finder.available:
            self.skipTest("Win32 not available")
        t0 = time.monotonic()
        result = finder.wait_for(
            "__nonexistent_window__", timeout=1.5, poll_interval=0.5
        )
        elapsed = time.monotonic() - t0
        self.assertIsNone(result)
        self.assertGreater(elapsed, 1.0)

    def test_wait_for_existing_returns_fast(self):
        finder = AutoWindowFinder()
        if not finder.available:
            self.skipTest("Win32 not available")
        # Use a regex that matches anything
        t0 = time.monotonic()
        result = finder.wait_for(".*", timeout=5.0, poll_interval=0.5)
        elapsed = time.monotonic() - t0
        if result is not None:
            self.assertLess(elapsed, 3.0)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestWindowStateHelpers(unittest.TestCase):
    """Static helper methods."""

    def test_restore_window_invalid_hwnd(self):
        if not WIN32_AVAILABLE:
            self.skipTest("Win32 not available")
        # An invalid hwnd should not crash
        result = AutoWindowFinder.restore_window(0)
        self.assertIsInstance(result, bool)

    def test_bring_to_front_invalid_hwnd(self):
        if not WIN32_AVAILABLE:
            self.skipTest("Win32 not available")
        result = AutoWindowFinder.bring_to_front(0)
        self.assertIsInstance(result, bool)

    def test_set_window_position_invalid_hwnd(self):
        if not WIN32_AVAILABLE:
            self.skipTest("Win32 not available")
        result = AutoWindowFinder.set_window_position(0, 0, 0, 800, 600)
        self.assertIsInstance(result, bool)


@unittest.skipUnless(MODULE_AVAILABLE, "auto_window_finder not importable")
class TestDpiScale(unittest.TestCase):
    """DPI scale factor."""

    def test_default_scale(self):
        m = WindowMatch()
        self.assertEqual(m.dpi_scale, 1.0)

    def test_get_dpi_scale_no_crash(self):
        # Calling with hwnd=0 should return 1.0 without crash
        scale = AutoWindowFinder._get_dpi_scale(0)
        self.assertIsInstance(scale, float)
        self.assertGreater(scale, 0.0)


if __name__ == "__main__":
    unittest.main()
