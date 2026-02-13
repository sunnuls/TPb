"""
Tests for BotProfileManager — Phase 1 of settings.md.

Tests cover:
  - JSON loading (bot_profiles.json)
  - Profile data model (BotProfile, EquityThresholds, BetSizing, etc.)
  - CRUD operations (list, get, add, update, delete, clone)
  - Validation
  - Conversion to BotSettings
  - Active profile tracking
  - Save / reload round-trip

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Dict

try:
    from launcher.bot_profile_manager import (
        BotProfileManager,
        BotProfile,
        EquityThresholds,
        BetSizing,
        TimingConfig,
        MouseProfile,
        SessionConfig,
        ProfileValidator,
        ValidationError,
        VALID_BEHAVIOR_STYLES,
    )
    from launcher.bot_settings import BotSettings, StrategyPreset

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Test: JSON loading
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestJSONLoading(unittest.TestCase):
    """Test loading profiles from the shipped bot_profiles.json."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))

    def test_profiles_loaded(self):
        self.assertGreaterEqual(self.mgr.profile_count(), 5)

    def test_known_profiles_exist(self):
        names = self.mgr.list_profiles()
        for expected in ["shark", "rock", "tag", "lag", "fish"]:
            self.assertIn(expected, names)

    def test_shark_profile_structure(self):
        p = self.mgr.get_profile("shark")
        self.assertIsNotNone(p)
        self.assertEqual(p.display_name, "Shark")
        self.assertEqual(p.aggression_level, 8)
        self.assertIsInstance(p.equity, EquityThresholds)
        self.assertIsInstance(p.bet_sizing, BetSizing)
        self.assertIsInstance(p.timing, TimingConfig)
        self.assertIsInstance(p.mouse, MouseProfile)
        self.assertIsInstance(p.session, SessionConfig)

    def test_rock_is_conservative(self):
        p = self.mgr.get_profile("rock")
        self.assertEqual(p.aggression_level, 2)
        self.assertGreater(p.equity.preflop_open, 0.70)

    def test_lag_is_aggressive(self):
        p = self.mgr.get_profile("lag")
        self.assertEqual(p.aggression_level, 9)
        self.assertLess(p.equity.preflop_open, 0.50)

    def test_all_profiles_valid(self):
        errors = self.mgr.validate_all()
        for name, errs in errors.items():
            self.fail(f"Profile '{name}' has validation errors: {errs}")


# ---------------------------------------------------------------------------
# Test: Data model
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestDataModel(unittest.TestCase):
    """Test individual data classes."""

    def test_equity_thresholds_roundtrip(self):
        eq = EquityThresholds(preflop_open=0.70, river_bluff=0.20)
        d = eq.to_dict()
        eq2 = EquityThresholds.from_dict(d)
        self.assertAlmostEqual(eq2.preflop_open, 0.70)
        self.assertAlmostEqual(eq2.river_bluff, 0.20)

    def test_bet_sizing_roundtrip(self):
        bs = BetSizing(open_raise_bb=3.5, max_bet_multiplier=7.0)
        d = bs.to_dict()
        bs2 = BetSizing.from_dict(d)
        self.assertAlmostEqual(bs2.open_raise_bb, 3.5)
        self.assertAlmostEqual(bs2.max_bet_multiplier, 7.0)

    def test_timing_config_pairs(self):
        tc = TimingConfig(think_time_fold=(0.2, 0.8))
        d = tc.to_dict()
        tc2 = TimingConfig.from_dict(d)
        self.assertEqual(tc2.think_time_fold, (0.2, 0.8))

    def test_mouse_profile_roundtrip(self):
        mp = MouseProfile(curve_intensity=8, jitter=1.5)
        d = mp.to_dict()
        mp2 = MouseProfile.from_dict(d)
        self.assertEqual(mp2.curve_intensity, 8)
        self.assertAlmostEqual(mp2.jitter, 1.5)

    def test_session_config_roundtrip(self):
        sc = SessionConfig(max_session_time=60, auto_rejoin=False)
        d = sc.to_dict()
        sc2 = SessionConfig.from_dict(d)
        self.assertEqual(sc2.max_session_time, 60)
        self.assertFalse(sc2.auto_rejoin)

    def test_bot_profile_full_roundtrip(self):
        p = BotProfile(
            name="test",
            display_name="Test",
            aggression_level=7,
            behavior_style="aggressive",
        )
        d = p.to_dict()
        p2 = BotProfile.from_dict("test", d)
        self.assertEqual(p2.aggression_level, 7)
        self.assertEqual(p2.behavior_style, "aggressive")

    def test_aggression_clamped(self):
        p = BotProfile(aggression_level=15)
        self.assertEqual(p.aggression_level, 10)
        p2 = BotProfile(aggression_level=-3)
        self.assertEqual(p2.aggression_level, 1)

    def test_invalid_behavior_style_defaults(self):
        p = BotProfile(behavior_style="invalid_style")
        self.assertEqual(p.behavior_style, "balanced")


# ---------------------------------------------------------------------------
# Test: CRUD
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestCRUD(unittest.TestCase):
    """Test CRUD operations."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))

    def test_list_profiles(self):
        names = self.mgr.list_profiles()
        self.assertIsInstance(names, list)
        self.assertEqual(names, sorted(names))

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.mgr.get_profile("nonexistent"))

    def test_add_profile(self):
        p = BotProfile(name="custom_test", display_name="Custom Test", aggression_level=6)
        self.mgr.add_profile(p)
        loaded = self.mgr.get_profile("custom_test")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.display_name, "Custom Test")

    def test_get_returns_deep_copy(self):
        p1 = self.mgr.get_profile("shark")
        p2 = self.mgr.get_profile("shark")
        p1.aggression_level = 1
        self.assertNotEqual(p1.aggression_level, p2.aggression_level)

    def test_update_simple_field(self):
        updated = self.mgr.update_profile("shark", {"aggression_level": 5})
        self.assertIsNotNone(updated)
        self.assertEqual(updated.aggression_level, 5)

    def test_update_nested_field(self):
        updated = self.mgr.update_profile("shark", {"equity.preflop_open": 0.80})
        self.assertIsNotNone(updated)
        self.assertAlmostEqual(updated.equity.preflop_open, 0.80)

    def test_update_missing_returns_none(self):
        self.assertIsNone(self.mgr.update_profile("no_such", {"aggression_level": 3}))

    def test_delete_profile(self):
        self.mgr.add_profile(BotProfile(name="to_delete"))
        self.assertTrue(self.mgr.delete_profile("to_delete"))
        self.assertIsNone(self.mgr.get_profile("to_delete"))

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.mgr.delete_profile("no_such"))

    def test_clone_profile(self):
        cloned = self.mgr.clone_profile("shark", "shark_v2")
        self.assertIsNotNone(cloned)
        self.assertEqual(cloned.name, "shark_v2")
        self.assertIn("(copy)", cloned.display_name)
        self.assertEqual(cloned.aggression_level, 8)

    def test_clone_missing_returns_none(self):
        self.assertIsNone(self.mgr.clone_profile("no_such", "clone"))


# ---------------------------------------------------------------------------
# Test: Validation
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestValidation(unittest.TestCase):
    """Test profile validation."""

    def test_valid_profile_no_errors(self):
        v = ProfileValidator()
        p = BotProfile(name="ok", aggression_level=5)
        errors = v.validate(p)
        self.assertEqual(len(errors), 0)

    def test_bad_equity_range(self):
        v = ProfileValidator()
        p = BotProfile(name="bad")
        p.equity.preflop_open = 1.5
        errors = v.validate(p)
        eq_errors = [e for e in errors if "equity" in e.field]
        self.assertGreater(len(eq_errors), 0)

    def test_bad_delay_order(self):
        v = ProfileValidator()
        p = BotProfile(name="bad")
        p.timing.delay_min = 5.0
        p.timing.delay_max = 1.0
        errors = v.validate(p)
        delay_errors = [e for e in errors if "delay" in e.field]
        self.assertGreater(len(delay_errors), 0)

    def test_bad_think_time_pair(self):
        v = ProfileValidator()
        p = BotProfile(name="bad")
        p.timing.think_time_fold = (3.0, 1.0)
        errors = v.validate(p)
        pair_errors = [e for e in errors if "think_time" in e.field]
        self.assertGreater(len(pair_errors), 0)

    def test_bad_mouse_curve(self):
        v = ProfileValidator()
        p = BotProfile(name="bad")
        p.mouse.curve_intensity = 15
        errors = v.validate(p)
        mouse_errors = [e for e in errors if "curve_intensity" in e.field]
        self.assertGreater(len(mouse_errors), 0)

    def test_bad_overshoot_prob(self):
        v = ProfileValidator()
        p = BotProfile(name="bad")
        p.mouse.overshoot_prob = 2.0
        errors = v.validate(p)
        self.assertGreater(len(errors), 0)

    def test_validate_nonexistent(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        errors = mgr.validate_profile("no_such")
        self.assertGreater(len(errors), 0)


# ---------------------------------------------------------------------------
# Test: Conversion to BotSettings
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestConversion(unittest.TestCase):
    """Test profile → BotSettings conversion."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))

    def test_shark_to_settings(self):
        s = self.mgr.profile_to_settings("shark")
        self.assertIsInstance(s, BotSettings)
        self.assertEqual(s.aggression_level, 8)
        self.assertEqual(s.preset, StrategyPreset.AGGRESSIVE)

    def test_rock_to_settings(self):
        s = self.mgr.profile_to_settings("rock")
        self.assertEqual(s.preset, StrategyPreset.CONSERVATIVE)
        self.assertEqual(s.aggression_level, 2)

    def test_tag_to_settings(self):
        s = self.mgr.profile_to_settings("tag")
        self.assertEqual(s.preset, StrategyPreset.BALANCED)

    def test_fish_to_settings(self):
        s = self.mgr.profile_to_settings("fish")
        self.assertEqual(s.preset, StrategyPreset.CUSTOM)

    def test_missing_returns_none(self):
        self.assertIsNone(self.mgr.profile_to_settings("no_such"))

    def test_settings_delay_match(self):
        s = self.mgr.profile_to_settings("shark")
        p = self.mgr.get_profile("shark")
        self.assertAlmostEqual(s.delay_min, p.timing.delay_min)
        self.assertAlmostEqual(s.delay_max, p.timing.delay_max)


# ---------------------------------------------------------------------------
# Test: Active profile tracking
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestActiveProfile(unittest.TestCase):
    """Test per-bot active profile management."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))

    def test_set_and_get_active(self):
        self.assertTrue(self.mgr.set_active_profile("bot_1", "shark"))
        self.assertEqual(self.mgr.get_active_profile("bot_1"), "shark")

    def test_set_nonexistent_fails(self):
        self.assertFalse(self.mgr.set_active_profile("bot_1", "no_such"))

    def test_get_unset_returns_none(self):
        self.assertIsNone(self.mgr.get_active_profile("bot_99"))

    def test_get_active_settings(self):
        self.mgr.set_active_profile("bot_1", "tag")
        s = self.mgr.get_active_settings("bot_1")
        self.assertIsInstance(s, BotSettings)
        self.assertEqual(s.preset, StrategyPreset.BALANCED)

    def test_delete_clears_active(self):
        self.mgr.add_profile(BotProfile(name="temp"))
        self.mgr.set_active_profile("bot_1", "temp")
        self.mgr.delete_profile("temp")
        self.assertIsNone(self.mgr.get_active_profile("bot_1"))

    def test_list_active(self):
        self.mgr.set_active_profile("bot_1", "shark")
        self.mgr.set_active_profile("bot_2", "rock")
        active = self.mgr.list_active()
        self.assertEqual(active["bot_1"], "shark")
        self.assertEqual(active["bot_2"], "rock")


# ---------------------------------------------------------------------------
# Test: Save / reload round-trip
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_profile_manager")
class TestSaveReload(unittest.TestCase):
    """Test save + reload cycle."""

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"

            # Create manager, add profiles, save
            mgr1 = BotProfileManager(path)
            mgr1.add_profile(BotProfile(name="alpha", aggression_level=3))
            mgr1.add_profile(BotProfile(name="beta", aggression_level=9))
            mgr1.save()

            # New manager, load from same file
            mgr2 = BotProfileManager(path)
            self.assertEqual(mgr2.profile_count(), 2)
            self.assertEqual(mgr2.get_profile("alpha").aggression_level, 3)
            self.assertEqual(mgr2.get_profile("beta").aggression_level, 9)

    def test_save_preserves_all_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "profiles.json"

            mgr = BotProfileManager(path)
            p = BotProfile(
                name="full",
                display_name="Full Test",
                description="A full test profile",
                aggression_level=7,
                equity=EquityThresholds(preflop_open=0.70),
                bet_sizing=BetSizing(open_raise_bb=4.0),
                timing=TimingConfig(delay_min=0.5, delay_max=2.5),
                mouse=MouseProfile(curve_intensity=9),
                session=SessionConfig(max_session_time=180),
                behavior_style="aggressive",
            )
            mgr.add_profile(p)
            mgr.save()

            mgr2 = BotProfileManager(path)
            p2 = mgr2.get_profile("full")
            self.assertEqual(p2.display_name, "Full Test")
            self.assertEqual(p2.aggression_level, 7)
            self.assertAlmostEqual(p2.equity.preflop_open, 0.70)
            self.assertAlmostEqual(p2.bet_sizing.open_raise_bb, 4.0)
            self.assertAlmostEqual(p2.timing.delay_min, 0.5)
            self.assertEqual(p2.mouse.curve_intensity, 9)
            self.assertEqual(p2.session.max_session_time, 180)
            self.assertEqual(p2.behavior_style, "aggressive")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
