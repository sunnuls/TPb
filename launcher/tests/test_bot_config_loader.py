"""
Tests for BotConfigLoader — Phase 2 of settings.md.

Tests cover:
  - Assignment CRUD (assign, unassign, list)
  - Settings loading with profile resolution + fallback
  - Per-bot overrides
  - Hot-swap and hot-override
  - Startup integration (startup_load_all)
  - Persistence (save/load round-trip)
  - Changelog tracking
  - Default profile

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from launcher.bot_config_loader import (
        BotConfigLoader,
        BotAssignment,
        ChangeLogEntry,
    )
    from launcher.bot_profile_manager import BotProfileManager, BotProfile
    from launcher.bot_settings import BotSettings, StrategyPreset

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeBotInstance:
    """Minimal mock with a .settings attribute."""
    bot_id: str = "bot_1"
    settings: BotSettings = field(default_factory=BotSettings)


# ---------------------------------------------------------------------------
# Test: Assignment CRUD
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestAssignment(unittest.TestCase):
    """Test assign / unassign / list."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm)

    def test_assign_known_profile(self):
        self.assertTrue(self.loader.assign("bot_1", "shark"))

    def test_assign_unknown_profile_fails(self):
        self.assertFalse(self.loader.assign("bot_1", "nonexistent"))

    def test_get_assignment(self):
        self.loader.assign("bot_1", "rock")
        a = self.loader.get_assignment("bot_1")
        self.assertIsNotNone(a)
        self.assertEqual(a.profile_name, "rock")

    def test_get_unassigned_returns_none(self):
        self.assertIsNone(self.loader.get_assignment("bot_99"))

    def test_unassign(self):
        self.loader.assign("bot_1", "shark")
        self.assertTrue(self.loader.unassign("bot_1"))
        self.assertIsNone(self.loader.get_assignment("bot_1"))

    def test_unassign_missing_returns_false(self):
        self.assertFalse(self.loader.unassign("bot_99"))

    def test_list_assignments(self):
        self.loader.assign("bot_1", "shark")
        self.loader.assign("bot_2", "rock")
        mapping = self.loader.list_assignments()
        self.assertEqual(mapping["bot_1"], "shark")
        self.assertEqual(mapping["bot_2"], "rock")

    def test_reassign_overwrites(self):
        self.loader.assign("bot_1", "shark")
        self.loader.assign("bot_1", "rock")
        self.assertEqual(self.loader.get_assignment("bot_1").profile_name, "rock")

    def test_assignment_count(self):
        self.assertEqual(self.loader.assignment_count, 0)
        self.loader.assign("bot_1", "tag")
        self.assertEqual(self.loader.assignment_count, 1)


# ---------------------------------------------------------------------------
# Test: Settings loading
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestLoadForBot(unittest.TestCase):
    """Test settings resolution: assignment → default → hardcoded."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm, default_profile="tag")

    def test_load_assigned_profile(self):
        self.loader.assign("bot_1", "shark")
        s = self.loader.load_for_bot("bot_1")
        self.assertIsInstance(s, BotSettings)
        self.assertEqual(s.aggression_level, 8)

    def test_load_falls_back_to_default(self):
        # No assignment — should use "tag" default
        s = self.loader.load_for_bot("bot_99")
        self.assertIsInstance(s, BotSettings)
        self.assertEqual(s.aggression_level, 6)  # tag = 6

    def test_load_hardcoded_if_no_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_path = Path(tmpdir) / "empty.json"
            empty_pm = BotProfileManager(empty_path)
            loader = BotConfigLoader(profile_manager=empty_pm, default_profile="none")
            s = loader.load_for_bot("bot_1")
            self.assertIsInstance(s, BotSettings)  # hardcoded defaults

    def test_load_profile_object(self):
        self.loader.assign("bot_1", "lag")
        p = self.loader.load_profile_for_bot("bot_1")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "lag")

    def test_effective_profile_name(self):
        self.loader.assign("bot_1", "fish")
        self.assertEqual(self.loader.get_effective_profile_name("bot_1"), "fish")
        # Unassigned bot gets default
        self.assertEqual(self.loader.get_effective_profile_name("bot_99"), "tag")


# ---------------------------------------------------------------------------
# Test: Overrides
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestOverrides(unittest.TestCase):
    """Test per-bot field overrides."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm)

    def test_assign_with_overrides(self):
        self.loader.assign("bot_1", "tag", overrides={"aggression_level": 10})
        s = self.loader.load_for_bot("bot_1")
        self.assertEqual(s.aggression_level, 10)  # overridden

    def test_override_preserves_other_fields(self):
        self.loader.assign("bot_1", "shark", overrides={"aggression_level": 1})
        s = self.loader.load_for_bot("bot_1")
        self.assertEqual(s.aggression_level, 1)
        # delay_min should still come from shark profile
        self.assertAlmostEqual(s.delay_min, 0.3)

    def test_unknown_override_key_ignored(self):
        self.loader.assign("bot_1", "tag", overrides={"nonexistent_field": 999})
        s = self.loader.load_for_bot("bot_1")
        # Should not crash, just load normally
        self.assertIsInstance(s, BotSettings)


# ---------------------------------------------------------------------------
# Test: Hot-swap / hot-override
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestHotReload(unittest.TestCase):
    """Test on-the-fly profile changes."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm)

    def test_hot_swap(self):
        self.loader.assign("bot_1", "shark")
        new_s = self.loader.hot_swap("bot_1", "rock")
        self.assertIsNotNone(new_s)
        self.assertEqual(new_s.aggression_level, 2)  # rock

    def test_hot_swap_nonexistent_returns_none(self):
        self.assertIsNone(self.loader.hot_swap("bot_1", "nonexistent"))

    def test_hot_override(self):
        self.loader.assign("bot_1", "tag")
        new_s = self.loader.hot_override("bot_1", {"delay_max": 8.0})
        self.assertIsNotNone(new_s)
        self.assertAlmostEqual(new_s.delay_max, 8.0)

    def test_hot_override_unassigned_uses_default(self):
        self.loader.default_profile = "tag"
        new_s = self.loader.hot_override("bot_new", {"aggression_level": 9})
        self.assertIsNotNone(new_s)
        self.assertEqual(new_s.aggression_level, 9)
        # Should now be assigned to default
        self.assertEqual(self.loader.get_assignment("bot_new").profile_name, "tag")

    def test_hot_override_accumulates(self):
        self.loader.assign("bot_1", "tag")
        self.loader.hot_override("bot_1", {"delay_min": 2.0})
        self.loader.hot_override("bot_1", {"delay_max": 9.0})
        s = self.loader.load_for_bot("bot_1")
        self.assertAlmostEqual(s.delay_min, 2.0)
        self.assertAlmostEqual(s.delay_max, 9.0)


# ---------------------------------------------------------------------------
# Test: Startup integration
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestStartup(unittest.TestCase):
    """Test startup_load_all with mock bots."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm, default_profile="tag")

    def test_startup_loads_assigned(self):
        self.loader.assign("b1", "shark")
        self.loader.assign("b2", "rock")

        bots = {
            "b1": FakeBotInstance(bot_id="b1"),
            "b2": FakeBotInstance(bot_id="b2"),
        }

        loaded = self.loader.startup_load_all(bots)
        self.assertEqual(loaded, 2)
        self.assertEqual(bots["b1"].settings.aggression_level, 8)
        self.assertEqual(bots["b2"].settings.aggression_level, 2)

    def test_startup_unassigned_gets_default(self):
        bots = {"b3": FakeBotInstance(bot_id="b3")}
        self.loader.startup_load_all(bots)
        # Default = "tag" → aggression 6
        self.assertEqual(bots["b3"].settings.aggression_level, 6)

    def test_startup_empty_dict(self):
        loaded = self.loader.startup_load_all({})
        self.assertEqual(loaded, 0)

    def test_startup_with_overrides(self):
        self.loader.assign("b1", "shark", overrides={"aggression_level": 3})
        bots = {"b1": FakeBotInstance(bot_id="b1")}
        self.loader.startup_load_all(bots)
        self.assertEqual(bots["b1"].settings.aggression_level, 3)


# ---------------------------------------------------------------------------
# Test: Persistence
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestPersistence(unittest.TestCase):
    """Test save/load round-trip."""

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "assignments.json"
            pm = BotProfileManager(Path("config/bot_profiles.json"))

            # Create loader, assign, save
            loader1 = BotConfigLoader(profile_manager=pm, assignments_path=path)
            loader1.assign("bot_A", "shark")
            loader1.assign("bot_B", "fish", overrides={"delay_min": 1.5})
            loader1.default_profile = "rock"
            loader1.save_assignments()

            # New loader loads from file
            loader2 = BotConfigLoader(profile_manager=pm, assignments_path=path)
            self.assertEqual(loader2.assignment_count, 2)
            self.assertEqual(loader2.get_assignment("bot_A").profile_name, "shark")
            self.assertEqual(loader2.get_assignment("bot_B").profile_name, "fish")
            self.assertEqual(loader2.default_profile, "rock")

    def test_overrides_persist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "assignments.json"
            pm = BotProfileManager(Path("config/bot_profiles.json"))

            loader1 = BotConfigLoader(profile_manager=pm, assignments_path=path)
            loader1.assign("bot_X", "tag", overrides={"aggression_level": 10})
            loader1.save_assignments()

            loader2 = BotConfigLoader(profile_manager=pm, assignments_path=path)
            a = loader2.get_assignment("bot_X")
            self.assertEqual(a.overrides.get("aggression_level"), 10)


# ---------------------------------------------------------------------------
# Test: Changelog
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestChangelog(unittest.TestCase):
    """Test change log tracking."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm)

    def test_assign_logs_change(self):
        self.loader.assign("bot_1", "shark")
        self.assertEqual(len(self.loader.changelog), 1)
        entry = self.loader.changelog[0]
        self.assertEqual(entry.bot_id, "bot_1")
        self.assertEqual(entry.new_profile, "shark")

    def test_hot_swap_logs_change(self):
        self.loader.assign("bot_1", "shark")
        self.loader.hot_swap("bot_1", "rock")
        log = self.loader.changelog_for_bot("bot_1")
        self.assertEqual(len(log), 2)
        self.assertEqual(log[1].old_profile, "shark")
        self.assertEqual(log[1].new_profile, "rock")
        self.assertEqual(log[1].source, "hot_swap")

    def test_clear_changelog(self):
        self.loader.assign("bot_1", "shark")
        self.loader.clear_changelog()
        self.assertEqual(len(self.loader.changelog), 0)

    def test_changelog_for_specific_bot(self):
        self.loader.assign("bot_1", "shark")
        self.loader.assign("bot_2", "rock")
        log1 = self.loader.changelog_for_bot("bot_1")
        self.assertEqual(len(log1), 1)
        self.assertEqual(log1[0].new_profile, "shark")


# ---------------------------------------------------------------------------
# Test: Default profile
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestDefaultProfile(unittest.TestCase):
    """Test default profile setting."""

    def setUp(self):
        self.pm = BotProfileManager(Path("config/bot_profiles.json"))
        self.loader = BotConfigLoader(profile_manager=self.pm, default_profile="tag")

    def test_default_profile_initial(self):
        self.assertEqual(self.loader.default_profile, "tag")

    def test_set_default_profile(self):
        self.loader.default_profile = "shark"
        self.assertEqual(self.loader.default_profile, "shark")

    def test_set_nonexistent_default_ignored(self):
        self.loader.default_profile = "nonexistent"
        self.assertEqual(self.loader.default_profile, "tag")  # unchanged


# ---------------------------------------------------------------------------
# Test: BotAssignment data class
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires bot_config_loader")
class TestBotAssignment(unittest.TestCase):
    """Test BotAssignment to_dict / from_dict."""

    def test_roundtrip(self):
        a = BotAssignment(
            bot_id="bot_1",
            profile_name="shark",
            overrides={"aggression_level": 10},
        )
        d = a.to_dict()
        a2 = BotAssignment.from_dict("bot_1", d)
        self.assertEqual(a2.profile_name, "shark")
        self.assertEqual(a2.overrides["aggression_level"], 10)

    def test_defaults(self):
        a = BotAssignment()
        self.assertEqual(a.profile_name, "tag")
        self.assertEqual(a.overrides, {})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
