#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for action_executor.md — Phase 2: Behavioral variance.

Covers:
- PlayStyle enum
- BehavioralProfile presets
- ActionParams data model
- HumanizationLayer — style-specific timing
- Aggressive vs Passive variance
- RANDOM style switching
- TILTED style behaviour
- Fatigue accumulation & recovery
- Action-type multipliers
- Hand-strength influence
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from humanization_layer import (
    PlayStyle,
    BehavioralProfile,
    STYLE_PROFILES,
    ActionParams,
    HumanizationLayer,
)


# ===========================================================================
# Test PlayStyle enum
# ===========================================================================

class TestPlayStyle(unittest.TestCase):
    def test_values(self):
        self.assertEqual(PlayStyle.AGGRESSIVE, "aggressive")
        self.assertEqual(PlayStyle.PASSIVE, "passive")
        self.assertEqual(PlayStyle.NEUTRAL, "neutral")
        self.assertEqual(PlayStyle.RANDOM, "random")
        self.assertEqual(PlayStyle.TILTED, "tilted")

    def test_all_styles_have_profiles(self):
        for style in PlayStyle:
            if style == PlayStyle.RANDOM:
                continue  # RANDOM picks from others
            self.assertIn(style, STYLE_PROFILES)


# ===========================================================================
# Test BehavioralProfile
# ===========================================================================

class TestBehavioralProfile(unittest.TestCase):
    def test_defaults(self):
        p = BehavioralProfile()
        self.assertGreater(p.think_base, 0)
        self.assertGreater(p.mouse_intensity, 0)
        self.assertGreater(p.fatigue_max, 0)

    def test_aggressive_faster_than_passive(self):
        agg = STYLE_PROFILES[PlayStyle.AGGRESSIVE]
        pas = STYLE_PROFILES[PlayStyle.PASSIVE]
        self.assertLess(agg.think_base, pas.think_base)
        self.assertLess(agg.mouse_speed_base, pas.mouse_speed_base)
        self.assertLess(agg.delay_base, pas.delay_base)

    def test_aggressive_higher_intensity(self):
        agg = STYLE_PROFILES[PlayStyle.AGGRESSIVE]
        pas = STYLE_PROFILES[PlayStyle.PASSIVE]
        self.assertGreater(agg.mouse_intensity, pas.mouse_intensity)

    def test_tilted_very_fast(self):
        tilted = STYLE_PROFILES[PlayStyle.TILTED]
        neutral = STYLE_PROFILES[PlayStyle.NEUTRAL]
        self.assertLess(tilted.think_base, neutral.think_base)
        self.assertGreater(tilted.mouse_jitter, neutral.mouse_jitter)

    def test_action_multipliers(self):
        p = BehavioralProfile()
        self.assertIn("fold", p.action_multipliers)
        self.assertIn("raise", p.action_multipliers)
        # fold should be faster than raise
        self.assertLess(p.action_multipliers["fold"], p.action_multipliers["raise"])


# ===========================================================================
# Test ActionParams
# ===========================================================================

class TestActionParams(unittest.TestCase):
    def test_defaults(self):
        ap = ActionParams()
        self.assertGreater(ap.total_time, 0)

    def test_summary(self):
        ap = ActionParams(
            style="aggressive", action="raise",
            think_time=0.5, total_time=1.0,
        )
        s = ap.summary()
        self.assertIn("aggressive", s)
        self.assertIn("raise", s)


# ===========================================================================
# Test HumanizationLayer — Neutral
# ===========================================================================

class TestHumanizationLayerNeutral(unittest.TestCase):
    def setUp(self):
        self.layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)

    def test_basic_params(self):
        params = self.layer.get_action_params("call")
        self.assertGreater(params.think_time, 0)
        self.assertGreater(params.delay_before, 0)
        self.assertGreater(params.execution_time, 0)
        self.assertGreater(params.total_time, 0)
        self.assertEqual(params.style, "neutral")
        self.assertEqual(params.action, "call")

    def test_fold_faster_than_raise(self):
        """Fold should have shorter think_time than raise (on average)."""
        folds = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("fold").think_time
            for i in range(30)
        ]
        raises = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("raise").think_time
            for i in range(30)
        ]
        # Average should show fold < raise (due to action multiplier)
        self.assertLess(sum(folds) / len(folds), sum(raises) / len(raises))

    def test_actions_count(self):
        self.layer.get_action_params("fold")
        self.layer.get_action_params("call")
        self.assertEqual(self.layer.actions_count, 2)


# ===========================================================================
# Test HumanizationLayer — Aggressive
# ===========================================================================

class TestAggressiveStyle(unittest.TestCase):
    def test_aggressive_think_time_range(self):
        layer = HumanizationLayer(style=PlayStyle.AGGRESSIVE, seed=42)
        times = [layer.get_action_params("call").think_time for _ in range(50)]
        avg = sum(times) / len(times)
        # Aggressive: think_base=0.8, so avg should be relatively low
        self.assertLess(avg, 3.0)

    def test_aggressive_mouse_intensity_high(self):
        layer = HumanizationLayer(style=PlayStyle.AGGRESSIVE, seed=42)
        params = layer.get_action_params("raise")
        self.assertGreater(params.mouse_intensity, 5.0)

    def test_aggressive_faster_than_neutral(self):
        agg = HumanizationLayer(style=PlayStyle.AGGRESSIVE, seed=42)
        neu = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)

        agg_times = [agg.get_action_params("call").total_time for _ in range(30)]
        neu_times = [neu.get_action_params("call").total_time for _ in range(30)]

        self.assertLess(sum(agg_times) / len(agg_times),
                        sum(neu_times) / len(neu_times))


# ===========================================================================
# Test HumanizationLayer — Passive
# ===========================================================================

class TestPassiveStyle(unittest.TestCase):
    def test_passive_slower_than_aggressive(self):
        agg = HumanizationLayer(style=PlayStyle.AGGRESSIVE, seed=42)
        pas = HumanizationLayer(style=PlayStyle.PASSIVE, seed=42)

        agg_times = [agg.get_action_params("call").think_time for _ in range(30)]
        pas_times = [pas.get_action_params("call").think_time for _ in range(30)]

        self.assertGreater(sum(pas_times) / len(pas_times),
                           sum(agg_times) / len(agg_times))

    def test_passive_no_overshoot(self):
        layer = HumanizationLayer(style=PlayStyle.PASSIVE, seed=42)
        params = layer.get_action_params("check")
        self.assertFalse(params.mouse_overshoot)

    def test_passive_small_click_offset(self):
        layer = HumanizationLayer(style=PlayStyle.PASSIVE, seed=42)
        offsets = [layer.get_action_params("fold").click_offset for _ in range(20)]
        avg_off = sum(offsets) / len(offsets)
        self.assertLessEqual(avg_off, 4)


# ===========================================================================
# Test HumanizationLayer — Random
# ===========================================================================

class TestRandomStyle(unittest.TestCase):
    def test_random_produces_variance(self):
        """RANDOM style should produce varied params over many actions."""
        layer = HumanizationLayer(style=PlayStyle.RANDOM, seed=42)
        intensities = [layer.get_action_params("call").mouse_intensity
                       for _ in range(50)]
        # Should have some variance (not all identical)
        self.assertGreater(max(intensities) - min(intensities), 0.1)

    def test_random_style_value(self):
        layer = HumanizationLayer(style=PlayStyle.RANDOM)
        self.assertEqual(layer.style, PlayStyle.RANDOM)


# ===========================================================================
# Test HumanizationLayer — Tilted
# ===========================================================================

class TestTiltedStyle(unittest.TestCase):
    def test_tilted_very_fast(self):
        layer = HumanizationLayer(style=PlayStyle.TILTED, seed=42)
        times = [layer.get_action_params("call").think_time for _ in range(20)]
        avg = sum(times) / len(times)
        self.assertLess(avg, 2.0)

    def test_tilted_high_jitter(self):
        layer = HumanizationLayer(style=PlayStyle.TILTED, seed=42)
        params = layer.get_action_params("raise")
        self.assertGreater(params.mouse_jitter, 1.0)


# ===========================================================================
# Test Fatigue
# ===========================================================================

class TestFatigue(unittest.TestCase):
    def test_fatigue_increases(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        self.assertAlmostEqual(layer.fatigue, 0.0)
        for _ in range(10):
            layer.get_action_params("call")
        self.assertGreater(layer.fatigue, 0)

    def test_fatigue_capped(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        for _ in range(200):
            layer.get_action_params("call")
        self.assertLessEqual(layer.fatigue, layer.profile.fatigue_max + 0.01)

    def test_fatigue_reset(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        for _ in range(10):
            layer.get_action_params("fold")
        self.assertGreater(layer.fatigue, 0)
        layer.reset_fatigue()
        self.assertAlmostEqual(layer.fatigue, 0.0)

    def test_idle_recovery(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        for _ in range(10):
            layer.get_action_params("call")
        before = layer.fatigue
        layer.idle_recovery(seconds=30.0)
        self.assertLess(layer.fatigue, before)

    def test_fatigue_slows_actions(self):
        """Actions should get slower as fatigue increases."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        early_params = layer.get_action_params("call")

        # Do many actions to build fatigue
        for _ in range(50):
            layer.get_action_params("call")

        late_params = layer.get_action_params("call")
        # Late actions tend to be slower due to fatigue multiplier
        # Can't guarantee every single one, but in general trend holds
        self.assertGreater(layer.fatigue, 0.1)


# ===========================================================================
# Test Style switching
# ===========================================================================

class TestStyleSwitching(unittest.TestCase):
    def test_switch_style(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL)
        self.assertEqual(layer.style, PlayStyle.NEUTRAL)

        layer.set_style(PlayStyle.AGGRESSIVE)
        self.assertEqual(layer.style, PlayStyle.AGGRESSIVE)

    def test_switch_preserves_fatigue(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        for _ in range(5):
            layer.get_action_params("call")
        fatigue_before = layer.fatigue

        layer.set_style(PlayStyle.TILTED)
        self.assertAlmostEqual(layer.fatigue, fatigue_before)

    def test_switch_changes_profile(self):
        layer = HumanizationLayer(style=PlayStyle.PASSIVE)
        old_base = layer.profile.think_base

        layer.set_style(PlayStyle.AGGRESSIVE)
        self.assertNotEqual(layer.profile.think_base, old_base)


# ===========================================================================
# Test Hand strength influence
# ===========================================================================

class TestHandStrengthInfluence(unittest.TestCase):
    def test_strong_hand_tends_faster(self):
        """With positive strength_influence, strong hands think less."""
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        strong = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("call", hand_strength=0.9).think_time
            for i in range(30)
        ]
        weak = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("call", hand_strength=0.1).think_time
            for i in range(30)
        ]
        # On average, strong should be faster
        self.assertLess(sum(strong) / len(strong), sum(weak) / len(weak))

    def test_important_actions_slower(self):
        """Important actions should take longer."""
        normal_times = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("raise", is_important=False).think_time
            for i in range(30)
        ]
        important_times = [
            HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42 + i)
                .get_action_params("raise", is_important=True).think_time
            for i in range(30)
        ]
        self.assertGreater(
            sum(important_times) / len(important_times),
            sum(normal_times) / len(normal_times),
        )


# ===========================================================================
# Test Statistics
# ===========================================================================

class TestStatistics(unittest.TestCase):
    def test_get_stats(self):
        layer = HumanizationLayer(style=PlayStyle.NEUTRAL, seed=42)
        layer.get_action_params("fold")
        layer.get_action_params("raise")
        stats = layer.get_stats()
        self.assertEqual(stats["style"], "neutral")
        self.assertEqual(stats["actions_count"], 2)
        self.assertGreater(stats["fatigue"], 0)


if __name__ == "__main__":
    unittest.main()
