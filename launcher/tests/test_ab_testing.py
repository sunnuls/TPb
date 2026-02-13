"""
Tests for A/B Testing Framework — Phase 3 of settings.md.

Core requirement: test all 5 presets and rank them.

Tests cover:
  - SessionSimulator (single session metrics)
  - ABTestRunner (add profiles, run, ranking)
  - All 5 presets (shark, rock, tag, lag, fish) comparison
  - Statistical validity (CI, mean, std)
  - Report generation
  - Edge cases

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    from launcher.ab_testing import (
        ABTestRunner,
        ABTestResult,
        SessionSimulator,
        SessionMetrics,
        ProfileStats,
    )
    from launcher.bot_profile_manager import BotProfileManager, BotProfile

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Test: SessionSimulator
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestSessionSimulator(unittest.TestCase):
    """Test single session simulation."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.sim = SessionSimulator(seed=42)

    def test_simulate_returns_metrics(self):
        profile = self.pm.get_profile("tag")
        m = self.sim.simulate(profile, hands=100)
        self.assertIsInstance(m, SessionMetrics)
        self.assertEqual(m.hands_played, 100)
        self.assertEqual(m.profile_name, "tag")

    def test_vpip_in_range(self):
        profile = self.pm.get_profile("tag")
        m = self.sim.simulate(profile, hands=500)
        self.assertGreaterEqual(m.vpip, 0.0)
        self.assertLessEqual(m.vpip, 1.0)

    def test_pfr_in_range(self):
        profile = self.pm.get_profile("tag")
        m = self.sim.simulate(profile, hands=500)
        self.assertGreaterEqual(m.pfr, 0.0)
        self.assertLessEqual(m.pfr, 1.0)

    def test_pfr_lte_vpip(self):
        """PFR should never exceed VPIP (can't raise without putting $ in)."""
        for name in ["shark", "rock", "tag", "lag", "fish"]:
            profile = self.pm.get_profile(name)
            m = self.sim.simulate(profile, hands=500)
            self.assertLessEqual(m.pfr, m.vpip + 0.01,
                                 f"{name}: PFR ({m.pfr:.2f}) > VPIP ({m.vpip:.2f})")

    def test_aggression_factor_positive(self):
        profile = self.pm.get_profile("lag")
        m = self.sim.simulate(profile, hands=500)
        self.assertGreater(m.aggression_factor, 0)

    def test_showdown_wins_in_range(self):
        profile = self.pm.get_profile("tag")
        m = self.sim.simulate(profile, hands=500)
        self.assertGreaterEqual(m.showdown_wins, 0.0)
        self.assertLessEqual(m.showdown_wins, 1.0)

    def test_duration_positive(self):
        profile = self.pm.get_profile("tag")
        m = self.sim.simulate(profile, hands=100)
        self.assertGreaterEqual(m.duration_s, 0.0)

    def test_aggressive_higher_vpip_than_rock(self):
        """LAG should have much higher VPIP than rock."""
        lag = self.pm.get_profile("lag")
        rock = self.pm.get_profile("rock")
        m_lag = self.sim.simulate(lag, hands=1000)
        sim2 = SessionSimulator(seed=42)
        m_rock = sim2.simulate(rock, hands=1000)
        self.assertGreater(m_lag.vpip, m_rock.vpip)

    def test_reproducible_with_seed(self):
        profile = self.pm.get_profile("tag")
        s1 = SessionSimulator(seed=123)
        s2 = SessionSimulator(seed=123)
        m1 = s1.simulate(profile, hands=200)
        m2 = s2.simulate(profile, hands=200)
        self.assertAlmostEqual(m1.net_profit_bb, m2.net_profit_bb)
        self.assertAlmostEqual(m1.vpip, m2.vpip)


# ---------------------------------------------------------------------------
# Test: ABTestRunner basics
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestABTestRunner(unittest.TestCase):
    """Test runner configuration and execution."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))

    def test_add_profile(self):
        ab = ABTestRunner(profile_manager=self.pm)
        self.assertTrue(ab.add_profile("shark"))
        self.assertIn("shark", ab.profile_names)

    def test_add_unknown_profile(self):
        ab = ABTestRunner(profile_manager=self.pm)
        self.assertFalse(ab.add_profile("nonexistent"))

    def test_add_all_profiles(self):
        ab = ABTestRunner(profile_manager=self.pm)
        added = ab.add_all_profiles()
        self.assertEqual(added, 5)

    def test_add_duplicate_ignored(self):
        ab = ABTestRunner(profile_manager=self.pm)
        ab.add_profile("shark")
        ab.add_profile("shark")
        self.assertEqual(len(ab.profile_names), 1)

    def test_run_returns_result(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("shark")
        ab.add_profile("rock")
        result = ab.run(hands_per_session=50, sessions_per_profile=5)
        self.assertIsInstance(result, ABTestResult)

    def test_run_populates_profiles(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("shark")
        ab.add_profile("rock")
        result = ab.run(hands_per_session=50, sessions_per_profile=5)
        self.assertIn("shark", result.profiles)
        self.assertIn("rock", result.profiles)

    def test_run_has_ranking(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("shark")
        ab.add_profile("rock")
        result = ab.run(hands_per_session=50, sessions_per_profile=5)
        self.assertEqual(len(result.ranking), 2)
        self.assertIn(result.best_profile, ["shark", "rock"])

    def test_total_counts(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("tag")
        result = ab.run(hands_per_session=100, sessions_per_profile=10)
        self.assertEqual(result.total_hands, 1000)
        self.assertEqual(result.total_sessions, 10)


# ---------------------------------------------------------------------------
# Test: ProfileStats aggregation
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestProfileStats(unittest.TestCase):
    """Test that aggregated stats are sane."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("tag")
        self._result = ab.run(hands_per_session=200, sessions_per_profile=30)
        self._stats = self._result.profiles["tag"]

    def test_has_sessions(self):
        self.assertEqual(len(self._stats.sessions), 30)

    def test_mean_profit_finite(self):
        self.assertTrue(math.isfinite(self._stats.mean_profit))

    def test_std_profit_positive(self):
        self.assertGreater(self._stats.std_profit, 0)

    def test_ci_contains_mean(self):
        s = self._stats
        self.assertLessEqual(s.ci_95_low, s.mean_profit)
        self.assertGreaterEqual(s.ci_95_high, s.mean_profit)

    def test_ci_width_positive(self):
        s = self._stats
        self.assertGreater(s.ci_95_high - s.ci_95_low, 0)

    def test_mean_vpip_in_range(self):
        self.assertGreater(self._stats.mean_vpip, 0)
        self.assertLess(self._stats.mean_vpip, 1)

    def test_mean_af_positive(self):
        self.assertGreater(self._stats.mean_af, 0)


import math  # needed for isfinite above


# ---------------------------------------------------------------------------
# Test: ALL 5 PRESETS — CORE REQUIREMENT
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestAll5Presets(unittest.TestCase):
    """Core requirement: compare all 5 presets and produce ranking."""

    @classmethod
    def setUpClass(cls):
        cls.pm = BotProfileManager(Path("config/bot_profiles.json"))
        cls.ab = ABTestRunner(profile_manager=cls.pm, seed=42)
        cls.ab.add_all_profiles()
        cls.result = cls.ab.run(
            hands_per_session=200,
            sessions_per_profile=30,
        )

    def test_all_5_profiles_tested(self):
        self.assertEqual(len(self.result.profiles), 5)

    def test_all_5_in_ranking(self):
        self.assertEqual(len(self.result.ranking), 5)
        for name in ["shark", "rock", "tag", "lag", "fish"]:
            self.assertIn(name, self.result.ranking)

    def test_best_profile_identified(self):
        self.assertIn(self.result.best_profile, ["shark", "rock", "tag", "lag", "fish"])

    def test_each_profile_has_sessions(self):
        for name, stats in self.result.profiles.items():
            self.assertEqual(len(stats.sessions), 30,
                             f"{name}: expected 30 sessions")

    def test_total_hands(self):
        # 5 profiles × 30 sessions × 200 hands = 30,000
        self.assertEqual(self.result.total_hands, 30000)

    def test_total_sessions(self):
        self.assertEqual(self.result.total_sessions, 150)

    def test_profiles_differ_in_vpip(self):
        """Different profiles should show different VPIP ranges."""
        vpips = {
            name: stats.mean_vpip
            for name, stats in self.result.profiles.items()
        }
        # LAG should have highest VPIP, rock lowest
        self.assertGreater(vpips["lag"], vpips["rock"])

    def test_profiles_differ_in_aggression(self):
        """Aggressive profiles should have higher AF."""
        afs = {
            name: stats.mean_af
            for name, stats in self.result.profiles.items()
        }
        self.assertGreater(afs["shark"], afs["rock"])

    def test_rock_tightest_pfr(self):
        """Rock should have lowest PFR."""
        pfrs = {
            name: stats.mean_pfr
            for name, stats in self.result.profiles.items()
        }
        rock_pfr = pfrs["rock"]
        for name, pfr in pfrs.items():
            if name != "rock":
                self.assertLessEqual(rock_pfr, pfr + 0.05,
                                     f"Rock PFR ({rock_pfr:.2f}) not lowest vs {name} ({pfr:.2f})")

    def test_lag_widest_vpip(self):
        """LAG should have highest or near-highest VPIP."""
        vpips = {
            name: stats.mean_vpip
            for name, stats in self.result.profiles.items()
        }
        lag_vpip = vpips["lag"]
        # LAG should be in top 2
        sorted_vpips = sorted(vpips.values(), reverse=True)
        self.assertGreaterEqual(lag_vpip, sorted_vpips[1] - 0.05)

    def test_confidence_intervals_exist(self):
        for name, stats in self.result.profiles.items():
            self.assertLess(stats.ci_95_low, stats.ci_95_high,
                            f"{name}: CI inverted")

    def test_elapsed_time_reasonable(self):
        """30k hands should complete in under 30 seconds."""
        self.assertLess(self.result.elapsed_s, 30.0)


# ---------------------------------------------------------------------------
# Test: Report
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestReport(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.ab = ABTestRunner(profile_manager=self.pm, seed=42)
        self.ab.add_all_profiles()
        self.ab.run(hands_per_session=100, sessions_per_profile=10)

    def test_report_not_empty(self):
        r = self.ab.report()
        self.assertGreater(len(r), 100)

    def test_report_contains_all_profiles(self):
        r = self.ab.report()
        for name in ["shark", "rock", "tag", "lag", "fish"]:
            self.assertIn(name, r)

    def test_report_contains_ranking(self):
        r = self.ab.report()
        self.assertIn("Rank", r)
        self.assertIn("BEST", r)

    def test_report_contains_metrics(self):
        r = self.ab.report()
        self.assertIn("WR bb/100", r)
        self.assertIn("VPIP", r)
        self.assertIn("PFR", r)
        self.assertIn("AF", r)

    def test_report_before_run(self):
        ab2 = ABTestRunner(profile_manager=self.pm)
        r = ab2.report()
        self.assertIn("No test has been run", r)


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires ab_testing")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))

    def test_single_profile(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("tag")
        result = ab.run(hands_per_session=50, sessions_per_profile=5)
        self.assertEqual(len(result.ranking), 1)
        self.assertEqual(result.best_profile, "tag")

    def test_no_profiles(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        result = ab.run(hands_per_session=50, sessions_per_profile=5)
        self.assertEqual(len(result.ranking), 0)
        self.assertEqual(result.best_profile, "")

    def test_single_hand(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        ab.add_profile("tag")
        result = ab.run(hands_per_session=1, sessions_per_profile=3)
        self.assertEqual(result.total_hands, 3)

    def test_result_stored(self):
        ab = ABTestRunner(profile_manager=self.pm, seed=42)
        self.assertIsNone(ab.result)
        ab.add_profile("tag")
        ab.run(hands_per_session=50, sessions_per_profile=3)
        self.assertIsNotNone(ab.result)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
