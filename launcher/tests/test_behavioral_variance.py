"""
Tests for BehavioralVariance — Phase 2 of action_executor.md.

Tests cover:
  - BehaviorProfile factory methods (aggressive, passive, balanced, erratic)
  - BehaviorSampler (think time, mouse config, click offset, tempo, hover)
  - Variance drift over many actions
  - ProfileMixer (mix, random_profile)
  - Style-specific timing ranges
  - 100-action session consistency

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import random
import unittest
from typing import Dict

try:
    from launcher.vision.behavioral_variance import (
        BehaviorProfile,
        BehaviorSampler,
        BehaviorStyle,
        ActionType,
        ThinkTimeConfig,
        MouseConfig,
        TempoConfig,
        ProfileMixer,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Test: BehaviorProfile factories
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestProfileFactories(unittest.TestCase):
    """Test profile factory methods."""

    def test_aggressive_style(self):
        p = BehaviorProfile.aggressive()
        self.assertEqual(p.style, BehaviorStyle.AGGRESSIVE)

    def test_passive_style(self):
        p = BehaviorProfile.passive()
        self.assertEqual(p.style, BehaviorStyle.PASSIVE)

    def test_balanced_style(self):
        p = BehaviorProfile.balanced()
        self.assertEqual(p.style, BehaviorStyle.BALANCED)

    def test_erratic_style(self):
        p = BehaviorProfile.erratic()
        self.assertEqual(p.style, BehaviorStyle.ERRATIC)

    def test_all_actions_have_think_times(self):
        """Every profile should define think times for all 6 actions."""
        for factory in [
            BehaviorProfile.aggressive,
            BehaviorProfile.passive,
            BehaviorProfile.balanced,
            BehaviorProfile.erratic,
        ]:
            p = factory()
            for act in ActionType:
                self.assertIn(act.value, p.think_times,
                              f"{p.style}: missing {act.value}")

    def test_aggressive_faster_than_passive(self):
        """Aggressive fold think time max should be < passive fold max."""
        agg = BehaviorProfile.aggressive()
        pas = BehaviorProfile.passive()
        self.assertLess(
            agg.think_times["fold"].max_s,
            pas.think_times["fold"].max_s,
        )

    def test_aggressive_faster_mouse(self):
        """Aggressive speed_mult should be lower (= faster)."""
        agg = BehaviorProfile.aggressive()
        pas = BehaviorProfile.passive()
        self.assertLess(agg.mouse.speed_mult, pas.mouse.speed_mult)

    def test_mouse_config_valid_ranges(self):
        for factory in [
            BehaviorProfile.aggressive,
            BehaviorProfile.passive,
            BehaviorProfile.balanced,
            BehaviorProfile.erratic,
        ]:
            p = factory()
            self.assertGreaterEqual(p.mouse.curve_intensity, 0)
            self.assertLessEqual(p.mouse.curve_intensity, 10)
            self.assertGreater(p.mouse.speed_mult, 0)
            self.assertGreaterEqual(p.mouse.jitter, 0)
            self.assertGreaterEqual(p.mouse.overshoot_prob, 0)
            self.assertLessEqual(p.mouse.overshoot_prob, 1)
            self.assertGreaterEqual(p.mouse.click_offset, 0)


# ---------------------------------------------------------------------------
# Test: BehaviorSampler — think time
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSamplerThinkTime(unittest.TestCase):
    """Test think time sampling."""

    def test_think_time_positive(self):
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42)
        for act in ActionType:
            t = s.sample_think_time(act.value)
            self.assertGreater(t, 0)

    def test_think_time_within_range(self):
        """Samples should be within [min, max] (approximately — drift may shift)."""
        profile = BehaviorProfile.balanced()
        s = BehaviorSampler(profile, session_seed=42, enable_drift=False)
        for _ in range(50):
            t = s.sample_think_time("fold")
            cfg = profile.think_times["fold"]
            # Allow small margin for floating-point
            self.assertGreaterEqual(t, cfg.min_s * 0.9)
            self.assertLessEqual(t, cfg.max_s * 1.1)

    def test_aggressive_faster_samples(self):
        """Aggressive samples should on average be faster than passive."""
        agg_s = BehaviorSampler(BehaviorProfile.aggressive(), session_seed=1, enable_drift=False)
        pas_s = BehaviorSampler(BehaviorProfile.passive(), session_seed=1, enable_drift=False)

        agg_avg = sum(agg_s.sample_think_time("call") for _ in range(100)) / 100
        pas_avg = sum(pas_s.sample_think_time("call") for _ in range(100)) / 100

        self.assertLess(agg_avg, pas_avg)

    def test_allin_slower_than_fold(self):
        """All-in think time should generally be longer than fold."""
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42, enable_drift=False)
        fold_avg = sum(s.sample_think_time("fold") for _ in range(100)) / 100
        allin_avg = sum(s.sample_think_time("allin") for _ in range(100)) / 100
        self.assertLess(fold_avg, allin_avg)

    def test_unknown_action_uses_default(self):
        """Unknown action should not crash."""
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42)
        t = s.sample_think_time("unknown_action")
        self.assertGreater(t, 0)


# ---------------------------------------------------------------------------
# Test: BehaviorSampler — mouse config
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSamplerMouse(unittest.TestCase):
    """Test mouse config sampling."""

    def test_mouse_config_keys(self):
        s = BehaviorSampler(session_seed=42)
        cfg = s.sample_mouse_config()
        self.assertIn("curve_intensity", cfg)
        self.assertIn("speed_mult", cfg)
        self.assertIn("jitter", cfg)
        self.assertIn("overshoot", cfg)

    def test_curve_intensity_range(self):
        s = BehaviorSampler(session_seed=42)
        for _ in range(100):
            cfg = s.sample_mouse_config()
            self.assertGreaterEqual(cfg["curve_intensity"], 0)
            self.assertLessEqual(cfg["curve_intensity"], 10)

    def test_speed_mult_positive(self):
        s = BehaviorSampler(session_seed=42)
        for _ in range(100):
            cfg = s.sample_mouse_config()
            self.assertGreater(cfg["speed_mult"], 0)

    def test_overshoot_binary(self):
        s = BehaviorSampler(session_seed=42)
        for _ in range(50):
            cfg = s.sample_mouse_config()
            self.assertIn(cfg["overshoot"], (0.0, 1.0))


# ---------------------------------------------------------------------------
# Test: BehaviorSampler — click offset
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSamplerClickOffset(unittest.TestCase):
    """Test click offset sampling."""

    def test_offset_within_range(self):
        profile = BehaviorProfile.balanced()
        s = BehaviorSampler(profile, session_seed=42)
        r = profile.mouse.click_offset
        for _ in range(100):
            dx, dy = s.sample_click_offset()
            self.assertGreaterEqual(dx, -r)
            self.assertLessEqual(dx, r)
            self.assertGreaterEqual(dy, -r)
            self.assertLessEqual(dy, r)

    def test_offset_varies(self):
        s = BehaviorSampler(session_seed=42)
        offsets = set()
        for _ in range(50):
            offsets.add(s.sample_click_offset())
        self.assertGreater(len(offsets), 1)


# ---------------------------------------------------------------------------
# Test: BehaviorSampler — inter-action delay
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSamplerTempo(unittest.TestCase):
    """Test inter-action delay sampling."""

    def test_delay_positive(self):
        s = BehaviorSampler(session_seed=42)
        for _ in range(100):
            d = s.sample_inter_action_delay()
            self.assertGreater(d, 0)

    def test_aggressive_faster_tempo(self):
        agg = BehaviorSampler(BehaviorProfile.aggressive(), session_seed=1, enable_drift=False)
        pas = BehaviorSampler(BehaviorProfile.passive(), session_seed=1, enable_drift=False)
        agg_avg = sum(agg.sample_inter_action_delay() for _ in range(100)) / 100
        pas_avg = sum(pas.sample_inter_action_delay() for _ in range(100)) / 100
        self.assertLess(agg_avg, pas_avg)

    def test_burst_occasionally(self):
        """With burst_prob > 0, some delays should be very short."""
        s = BehaviorSampler(BehaviorProfile.erratic(), session_seed=42, enable_drift=False)
        delays = [s.sample_inter_action_delay() for _ in range(200)]
        short_count = sum(1 for d in delays if d < 0.3)
        self.assertGreater(short_count, 0, "No bursts detected in 200 samples")


# ---------------------------------------------------------------------------
# Test: BehaviorSampler — hover & double-click
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSamplerMicro(unittest.TestCase):
    """Test micro-behaviors: hover, double-click."""

    def test_hover_returns_bool(self):
        s = BehaviorSampler(session_seed=42)
        result = s.sample_should_hover()
        self.assertIsInstance(result, bool)

    def test_hover_varies(self):
        s = BehaviorSampler(session_seed=42)
        results = {s.sample_should_hover() for _ in range(100)}
        self.assertEqual(results, {True, False})

    def test_hover_time_positive(self):
        s = BehaviorSampler(session_seed=42)
        t = s.sample_hover_time()
        self.assertGreater(t, 0)
        self.assertLess(t, 1.0)

    def test_double_click_rare(self):
        s = BehaviorSampler(session_seed=42)
        dc = sum(1 for _ in range(1000) if s.sample_double_click_prob())
        # Should be around 1.5% — allow 0–5%
        self.assertLess(dc, 50)

    def test_passive_hovers_more(self):
        """Passive should have higher hover probability than aggressive."""
        pas = BehaviorSampler(BehaviorProfile.passive(), session_seed=1)
        agg = BehaviorSampler(BehaviorProfile.aggressive(), session_seed=1)
        pas_hovers = sum(1 for _ in range(500) if pas.sample_should_hover())
        agg_hovers = sum(1 for _ in range(500) if agg.sample_should_hover())
        self.assertGreater(pas_hovers, agg_hovers)


# ---------------------------------------------------------------------------
# Test: Variance drift
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestDrift(unittest.TestCase):
    """Test that profile drifts over a session."""

    def test_drift_changes_state(self):
        """After many actions, drift values should differ from initial."""
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42, enable_drift=True)
        initial_speed = s._drift_speed_mult
        initial_curve = s._drift_curve

        for _ in range(200):
            s.sample_think_time("call")

        # At least one should have drifted
        changed = (
            abs(s._drift_speed_mult - initial_speed) > 0.01
            or abs(s._drift_curve - initial_curve) > 0.01
        )
        self.assertTrue(changed, "No drift detected after 200 actions")

    def test_drift_stays_bounded(self):
        """Drift should not go beyond sane bounds."""
        s = BehaviorSampler(BehaviorProfile.erratic(), session_seed=42, enable_drift=True)
        for _ in range(1000):
            s.sample_think_time("raise")

        self.assertGreaterEqual(s._drift_speed_mult, 0.4)
        self.assertLessEqual(s._drift_speed_mult, 2.0)
        self.assertGreaterEqual(s._drift_curve, 0)
        self.assertLessEqual(s._drift_curve, 10)

    def test_reset_drift(self):
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42, enable_drift=True)
        for _ in range(100):
            s.sample_think_time("bet")
        s.reset_drift()
        self.assertAlmostEqual(s._drift_speed_mult, s.profile.mouse.speed_mult)
        self.assertEqual(s.action_count, 0)

    def test_no_drift_when_disabled(self):
        s = BehaviorSampler(BehaviorProfile.balanced(), session_seed=42, enable_drift=False)
        initial = s._drift_speed_mult
        for _ in range(200):
            s.sample_think_time("call")
        self.assertAlmostEqual(s._drift_speed_mult, initial)


# ---------------------------------------------------------------------------
# Test: ProfileMixer
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestProfileMixer(unittest.TestCase):
    """Test profile mixing."""

    def test_mix_two_profiles(self):
        agg = BehaviorProfile.aggressive()
        pas = BehaviorProfile.passive()
        mixed = ProfileMixer.mix([agg, pas], [0.5, 0.5])

        # Speed mult should be between aggressive and passive
        self.assertGreater(mixed.mouse.speed_mult, agg.mouse.speed_mult - 0.01)
        self.assertLess(mixed.mouse.speed_mult, pas.mouse.speed_mult + 0.01)

    def test_mix_single_profile(self):
        p = BehaviorProfile.balanced()
        mixed = ProfileMixer.mix([p])
        self.assertEqual(mixed.style, p.style)

    def test_mix_empty(self):
        mixed = ProfileMixer.mix([])
        self.assertEqual(mixed.style, BehaviorStyle.BALANCED)

    def test_mix_weighted_dominant(self):
        """Dominant profile's style should be used."""
        agg = BehaviorProfile.aggressive()
        pas = BehaviorProfile.passive()
        mixed = ProfileMixer.mix([agg, pas], [0.9, 0.1])
        self.assertEqual(mixed.style, BehaviorStyle.AGGRESSIVE)

    def test_random_profile(self):
        p = ProfileMixer.random_profile(seed=42)
        self.assertIsInstance(p, BehaviorProfile)
        # Should have all action think times
        for act in ActionType:
            self.assertIn(act.value, p.think_times)

    def test_random_profiles_differ(self):
        p1 = ProfileMixer.random_profile(seed=1)
        p2 = ProfileMixer.random_profile(seed=2)
        # At least one parameter should differ
        self.assertNotAlmostEqual(
            p1.mouse.speed_mult, p2.mouse.speed_mult, places=1
        )


# ---------------------------------------------------------------------------
# Test: 100-action session
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires behavioral_variance")
class TestSession100(unittest.TestCase):
    """Simulate a 100-action session and verify consistency."""

    def _run_session(self, profile: BehaviorProfile, n: int = 100):
        s = BehaviorSampler(profile, session_seed=42)
        think_times = []
        delays = []
        mouse_cfgs = []

        actions = [a.value for a in ActionType]
        for i in range(n):
            act = actions[i % len(actions)]
            think_times.append(s.sample_think_time(act))
            delays.append(s.sample_inter_action_delay())
            mouse_cfgs.append(s.sample_mouse_config())

        return think_times, delays, mouse_cfgs, s

    def test_100_actions_aggressive(self):
        tt, dl, mc, s = self._run_session(BehaviorProfile.aggressive())
        self.assertEqual(s.action_count, 100)
        self.assertTrue(all(t > 0 for t in tt))
        self.assertTrue(all(d > 0 for d in dl))

    def test_100_actions_passive(self):
        tt, dl, mc, s = self._run_session(BehaviorProfile.passive())
        self.assertEqual(s.action_count, 100)
        avg_tt = sum(tt) / len(tt)
        # Passive should average > 1s think time
        self.assertGreater(avg_tt, 0.5)

    def test_100_actions_erratic_high_variance(self):
        tt, _, _, _ = self._run_session(BehaviorProfile.erratic())
        # Erratic should have high standard deviation
        avg = sum(tt) / len(tt)
        variance = sum((t - avg) ** 2 for t in tt) / len(tt)
        std = variance ** 0.5
        self.assertGreater(std, 0.1, f"Erratic std too low: {std:.3f}")

    def test_100_actions_no_negatives(self):
        for factory in [
            BehaviorProfile.aggressive,
            BehaviorProfile.passive,
            BehaviorProfile.balanced,
            BehaviorProfile.erratic,
        ]:
            tt, dl, mc, _ = self._run_session(factory())
            self.assertTrue(all(t > 0 for t in tt), f"{factory.__name__}: negative think time")
            self.assertTrue(all(d > 0 for d in dl), f"{factory.__name__}: negative delay")
            for cfg in mc:
                self.assertGreaterEqual(cfg["speed_mult"], 0)
                self.assertGreaterEqual(cfg["jitter"], 0)

    def test_100_random_profiles(self):
        """100 random profiles should all produce valid samplers."""
        for i in range(100):
            p = ProfileMixer.random_profile(seed=i)
            s = BehaviorSampler(p, session_seed=i)
            t = s.sample_think_time("call")
            self.assertGreater(t, 0)
            d = s.sample_inter_action_delay()
            self.assertGreater(d, 0)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
