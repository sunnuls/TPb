#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for settings.md — Phase 2: Per-bot config loading in bot_instance.py.

Covers:
- BotInstance.load_profile() — load named profile
- BotInstance.switch_profile() — on-the-fly switch
- BotInstance.get_profile() / get_profile_dict()
- Settings applied correctly from profile
- Profile not found handling
- Multiple bots with different profiles
- to_dict() includes profile_name
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from launcher.bot_instance import BotInstance, BotStatus, BotStatistics
    from launcher.bot_settings import BotSettings, StrategyPreset
    from launcher.bot_profile_manager import (
        BotProfileManager, BotProfile, EquityThresholds,
        BetSizing, TimingConfig, MouseProfile, SessionConfig,
    )
    MODULES_OK = True
except (ImportError, Exception) as e:
    MODULES_OK = False


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestLoadProfile(unittest.TestCase):
    """Test BotInstance.load_profile()."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))
        self.bot = BotInstance()

    def test_load_shark(self):
        ok = self.bot.load_profile("shark", manager=self.mgr)
        self.assertTrue(ok)
        self.assertEqual(self.bot.profile_name, "shark")
        self.assertEqual(self.bot.settings.aggression_level, 8)
        self.assertEqual(self.bot.settings.preset, StrategyPreset.AGGRESSIVE)

    def test_load_rock(self):
        ok = self.bot.load_profile("rock", manager=self.mgr)
        self.assertTrue(ok)
        self.assertEqual(self.bot.profile_name, "rock")
        self.assertEqual(self.bot.settings.aggression_level, 2)
        self.assertEqual(self.bot.settings.preset, StrategyPreset.CONSERVATIVE)

    def test_load_tag(self):
        ok = self.bot.load_profile("tag", manager=self.mgr)
        self.assertTrue(ok)
        self.assertEqual(self.bot.settings.preset, StrategyPreset.BALANCED)

    def test_load_lag(self):
        ok = self.bot.load_profile("lag", manager=self.mgr)
        self.assertTrue(ok)
        self.assertEqual(self.bot.settings.aggression_level, 9)

    def test_load_fish(self):
        ok = self.bot.load_profile("fish", manager=self.mgr)
        self.assertTrue(ok)
        self.assertEqual(self.bot.settings.preset, StrategyPreset.CUSTOM)

    def test_load_nonexistent(self):
        ok = self.bot.load_profile("nonexistent_profile", manager=self.mgr)
        self.assertFalse(ok)
        self.assertEqual(self.bot.profile_name, "")

    def test_settings_delay_from_profile(self):
        self.bot.load_profile("shark", manager=self.mgr)
        p = self.mgr.get_profile("shark")
        self.assertAlmostEqual(self.bot.settings.delay_min, p.timing.delay_min)
        self.assertAlmostEqual(self.bot.settings.delay_max, p.timing.delay_max)

    def test_settings_mouse_from_profile(self):
        self.bot.load_profile("rock", manager=self.mgr)
        p = self.mgr.get_profile("rock")
        self.assertEqual(self.bot.settings.mouse_curve_intensity, p.mouse.curve_intensity)

    def test_settings_session_from_profile(self):
        self.bot.load_profile("lag", manager=self.mgr)
        p = self.mgr.get_profile("lag")
        self.assertEqual(self.bot.settings.max_session_time, p.session.max_session_time)
        self.assertEqual(self.bot.settings.auto_rejoin, p.session.auto_rejoin)

    def test_settings_equity_from_profile(self):
        self.bot.load_profile("tag", manager=self.mgr)
        p = self.mgr.get_profile("tag")
        self.assertAlmostEqual(self.bot.settings.equity_threshold, p.equity.postflop_bet)


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestSwitchProfile(unittest.TestCase):
    """Test on-the-fly profile switching."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))
        self.bot = BotInstance()

    def test_switch(self):
        self.bot.load_profile("shark", manager=self.mgr)
        self.assertEqual(self.bot.settings.aggression_level, 8)

        ok = self.bot.switch_profile("rock")
        self.assertTrue(ok)
        self.assertEqual(self.bot.profile_name, "rock")
        self.assertEqual(self.bot.settings.aggression_level, 2)

    def test_switch_nonexistent(self):
        self.bot.load_profile("shark", manager=self.mgr)
        ok = self.bot.switch_profile("nonexistent")
        self.assertFalse(ok)
        # Should keep previous profile
        self.assertEqual(self.bot.profile_name, "shark")

    def test_switch_multiple_times(self):
        profiles = ["shark", "rock", "tag", "lag", "fish"]
        for pname in profiles:
            ok = self.bot.load_profile(pname, manager=self.mgr)
            self.assertTrue(ok)
            self.assertEqual(self.bot.profile_name, pname)


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestGetProfile(unittest.TestCase):
    """Test get_profile() and get_profile_dict()."""

    def setUp(self):
        self.mgr = BotProfileManager(Path("config/bot_profiles.json"))
        self.bot = BotInstance()

    def test_get_profile_none_initially(self):
        self.assertIsNone(self.bot.get_profile())

    def test_get_profile_after_load(self):
        self.bot.load_profile("shark", manager=self.mgr)
        p = self.bot.get_profile()
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "shark")

    def test_get_profile_dict_empty(self):
        d = self.bot.get_profile_dict()
        self.assertEqual(d, {})

    def test_get_profile_dict_loaded(self):
        self.bot.load_profile("tag", manager=self.mgr)
        d = self.bot.get_profile_dict()
        self.assertIn("aggression_level", d)
        self.assertIn("equity_thresholds", d)
        self.assertIn("bet_sizing", d)


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestMultipleBots(unittest.TestCase):
    """Test multiple bots with different profiles."""

    def test_different_profiles(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        bot1 = BotInstance()
        bot2 = BotInstance()
        bot3 = BotInstance()

        bot1.load_profile("shark", manager=mgr)
        bot2.load_profile("rock", manager=mgr)
        bot3.load_profile("lag", manager=mgr)

        self.assertEqual(bot1.settings.aggression_level, 8)
        self.assertEqual(bot2.settings.aggression_level, 2)
        self.assertEqual(bot3.settings.aggression_level, 9)

        # Different presets
        self.assertNotEqual(bot1.settings.preset, bot2.settings.preset)

    def test_same_profile_different_bots(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        bot1 = BotInstance()
        bot2 = BotInstance()

        bot1.load_profile("shark", manager=mgr)
        bot2.load_profile("shark", manager=mgr)

        self.assertEqual(bot1.settings.aggression_level, bot2.settings.aggression_level)
        self.assertNotEqual(bot1.bot_id, bot2.bot_id)

    def test_active_profile_tracked_in_manager(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        bot1 = BotInstance()
        bot2 = BotInstance()

        bot1.load_profile("shark", manager=mgr)
        bot2.load_profile("rock", manager=mgr)

        active = mgr.list_active()
        self.assertEqual(active[bot1.bot_id], "shark")
        self.assertEqual(active[bot2.bot_id], "rock")


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestToDict(unittest.TestCase):
    """Test to_dict() includes profile info."""

    def test_profile_name_in_dict(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        bot = BotInstance()
        bot.load_profile("shark", manager=mgr)

        d = bot.to_dict()
        self.assertEqual(d["profile_name"], "shark")

    def test_profile_name_empty_without_load(self):
        bot = BotInstance()
        d = bot.to_dict()
        self.assertEqual(d["profile_name"], "")

    def test_settings_in_dict_match_profile(self):
        mgr = BotProfileManager(Path("config/bot_profiles.json"))
        bot = BotInstance()
        bot.load_profile("lag", manager=mgr)

        d = bot.to_dict()
        self.assertEqual(d["settings"]["aggression_level"], 9)


@unittest.skipUnless(MODULES_OK, "Requires launcher modules")
class TestDefaultManager(unittest.TestCase):
    """Test that load_profile works without passing manager."""

    def test_auto_creates_manager(self):
        bot = BotInstance()
        # Should auto-create BotProfileManager from default path
        ok = bot.load_profile("shark")
        self.assertTrue(ok)
        self.assertEqual(bot.profile_name, "shark")
        self.assertIsNotNone(bot._profile_manager)


if __name__ == "__main__":
    unittest.main()
