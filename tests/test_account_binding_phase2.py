"""
Tests for account_binding.md Phase 2 — Load binding at start.

Validates:
  - BotInstance.load_binding() creates/retrieves binding
  - get_binding() / get_binding_dict() accessors
  - check_binding_health() delegates to binder
  - rebind_window() re-discovery
  - to_dict() includes binding info
  - Integration with Account model
  - Multiple bots each get own binding
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

try:
    from launcher.bot_instance import BotInstance, BotStatus
    from launcher.bot_account_binder import (
        BotAccountBinder,
        Binding,
        BindStatus,
    )
    from launcher.models.account import Account, WindowInfo, WindowType
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestLoadBinding(unittest.TestCase):
    """BotInstance.load_binding() integration."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def _make_account(self, nickname="player1", room="pokerstars"):
        acc = Account(nickname=nickname, room=room)
        acc.window_info = WindowInfo(
            window_id="12345",
            window_title=f"Table - {nickname}",
            window_type=WindowType.DESKTOP_CLIENT,
        )
        acc.roi_configured = True
        return acc

    def test_load_binding_basic(self):
        """load_binding creates a binding with account info."""
        bot = BotInstance(account=self._make_account("shark99"))
        ok = bot.load_binding(self.binder, auto_bind=False)
        self.assertTrue(ok)
        b = bot.get_binding()
        self.assertIsNotNone(b)
        self.assertEqual(b.nickname, "shark99")

    def test_load_binding_stores_binder(self):
        """load_binding stores the binder for later use."""
        bot = BotInstance(account=self._make_account())
        bot.load_binding(self.binder, auto_bind=False)
        self.assertIs(bot._binder, self.binder)

    def test_load_binding_creates_default_binder(self):
        """If no binder provided, a default is created."""
        bot = BotInstance(account=self._make_account())
        ok = bot.load_binding(auto_bind=False)
        self.assertTrue(ok)
        self.assertIsNotNone(bot._binder)

    def test_load_binding_no_account(self):
        """load_binding works even without account (empty fields)."""
        bot = BotInstance()
        ok = bot.load_binding(self.binder, auto_bind=False)
        self.assertTrue(ok)
        b = bot.get_binding()
        self.assertIsNotNone(b)
        self.assertEqual(b.nickname, "")

    def test_load_binding_with_auto_bind(self):
        """load_binding + auto_bind triggers finder."""
        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = None
        self.binder._finder = mock_finder

        bot = BotInstance(account=self._make_account("hero"))
        bot.load_binding(self.binder, auto_bind=True)
        # finder.find should have been called
        mock_finder.find.assert_called()


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestGetBinding(unittest.TestCase):
    """get_binding / get_binding_dict accessors."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_get_binding_none_initially(self):
        bot = BotInstance()
        self.assertIsNone(bot.get_binding())

    def test_get_binding_dict_empty_initially(self):
        bot = BotInstance()
        self.assertEqual(bot.get_binding_dict(), {})

    def test_get_binding_after_load(self):
        acc = Account(nickname="test1", room="888poker")
        acc.window_info = None
        bot = BotInstance(account=acc)
        bot.load_binding(self.binder, auto_bind=False)

        b = bot.get_binding()
        self.assertIsNotNone(b)
        self.assertEqual(b.bot_id, bot.bot_id)

    def test_get_binding_dict_has_fields(self):
        acc = Account(nickname="hero", room="pokerstars")
        acc.window_info = None
        bot = BotInstance(account=acc)
        bot.load_binding(self.binder, auto_bind=False)

        d = bot.get_binding_dict()
        self.assertIn("bot_id", d)
        self.assertIn("nickname", d)
        self.assertEqual(d["nickname"], "hero")
        self.assertIn("status", d)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestCheckBindingHealth(unittest.TestCase):
    """check_binding_health delegates to binder."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_check_health_no_binder(self):
        bot = BotInstance()
        result = bot.check_binding_health()
        self.assertIsNone(result)

    def test_check_health_unbound(self):
        acc = Account(nickname="x", room="pokerstars")
        acc.window_info = None
        bot = BotInstance(account=acc)
        bot.load_binding(self.binder, auto_bind=False)

        status = bot.check_binding_health()
        self.assertEqual(status, "unbound")


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestRebindWindow(unittest.TestCase):
    """rebind_window re-discovery."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_rebind_no_binder(self):
        bot = BotInstance()
        self.assertFalse(bot.rebind_window())

    def test_rebind_with_mock_finder(self):
        from launcher.auto_window_finder import WindowMatch, WindowRect, MatchMethod

        mock_finder = MagicMock()
        mock_finder.available = True
        match = WindowMatch(
            hwnd=77777,
            title="PokerStars - hero",
            window_class="Cls",
            process_name="pokerstars.exe",
            process_id=100,
            full_rect=WindowRect(0, 0, 1920, 1080),
            client_rect=WindowRect(8, 31, 1904, 1041),
            zoom_rect=WindowRect(8, 31, 1904, 1041),
            match_method=MatchMethod.TITLE_SUBSTRING,
            score=0.9,
        )
        mock_finder.find.return_value = match
        self.binder._finder = mock_finder

        acc = Account(nickname="hero", room="pokerstars")
        acc.window_info = None
        bot = BotInstance(account=acc)
        bot.load_binding(self.binder, auto_bind=False)

        ok = bot.rebind_window()
        self.assertTrue(ok)
        b = bot.get_binding()
        self.assertEqual(b.hwnd, 77777)
        self.assertEqual(b.status, BindStatus.BOUND)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestToDictBinding(unittest.TestCase):
    """to_dict includes binding info."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_to_dict_has_binding_key(self):
        acc = Account(nickname="test", room="pokerstars")
        acc.window_info = WindowInfo(
            window_id="111",
            window_title="Table - test",
            window_type=WindowType.DESKTOP_CLIENT,
        )
        acc.roi_configured = True
        bot = BotInstance(account=acc)
        bot.load_binding(self.binder, auto_bind=False)

        d = bot.to_dict()
        self.assertIn("binding", d)
        self.assertIsInstance(d["binding"], dict)
        self.assertEqual(d["binding"]["nickname"], "test")

    def test_to_dict_binding_empty_without_load(self):
        bot = BotInstance()
        d = bot.to_dict()
        self.assertIn("binding", d)
        self.assertEqual(d["binding"], {})


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestMultipleBotsBinding(unittest.TestCase):
    """Multiple bots each get their own binding."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_five_bots_unique_bindings(self):
        """5 bots → each knows its own nickname/window."""
        nicknames = ["alpha", "bravo", "charlie", "delta", "echo"]
        bots = []

        for nick in nicknames:
            acc = Account(nickname=nick, room="pokerstars")
            acc.window_info = None
            bot = BotInstance(account=acc)
            bot.load_binding(self.binder, auto_bind=False)
            bots.append(bot)

        # Verify each bot has unique binding with correct nickname
        seen_ids = set()
        for i, bot in enumerate(bots):
            b = bot.get_binding()
            self.assertIsNotNone(b, f"Bot {i} should have binding")
            self.assertEqual(b.nickname, nicknames[i])
            self.assertEqual(b.bot_id, bot.bot_id)
            self.assertNotIn(b.bot_id, seen_ids)
            seen_ids.add(b.bot_id)

        # All 5 bindings registered in single binder
        self.assertEqual(len(self.binder.list_all()), 5)

    def test_five_bots_different_rooms(self):
        """5 bots across different rooms."""
        configs = [
            ("nick1", "pokerstars"),
            ("nick2", "888poker"),
            ("nick3", "ggpoker"),
            ("nick4", "partypoker"),
            ("nick5", "winamax"),
        ]
        bots = []
        for nick, room in configs:
            acc = Account(nickname=nick, room=room)
            acc.window_info = None
            bot = BotInstance(account=acc)
            bot.load_binding(self.binder, auto_bind=False)
            bots.append(bot)

        for i, bot in enumerate(bots):
            b = bot.get_binding()
            self.assertEqual(b.nickname, configs[i][0])
            self.assertEqual(b.room, configs[i][1])


if __name__ == "__main__":
    unittest.main()
