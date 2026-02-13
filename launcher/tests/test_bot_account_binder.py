"""
Tests for BotAccountBinder — Phase 2 of bot_fixes.md.

Tests cover:
  - Binding CRUD (bind, unbind, get, list_all)
  - Serialization round-trip (to_dict / from_dict)
  - JSON persistence (save / load)
  - Auto-bind via nickname → window title
  - Health-check (window alive / stale)
  - bind_from_account integration
  - Bulk operations (auto_bind_all, check_all_health, rebind_stale)
"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from launcher.bot_account_binder import (
        BindStatus,
        Binding,
        BotAccountBinder,
        DEFAULT_BINDINGS_PATH,
        FINDER_AVAILABLE,
        WIN32_AVAILABLE,
    )
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestBinding(unittest.TestCase):
    """Binding dataclass."""

    def test_defaults(self):
        b = Binding()
        self.assertEqual(b.bot_id, "")
        self.assertEqual(b.hwnd, 0)
        self.assertEqual(b.status, BindStatus.UNBOUND)
        self.assertFalse(b.is_bound)

    def test_is_bound(self):
        b = Binding(hwnd=12345, status=BindStatus.BOUND)
        self.assertTrue(b.is_bound)

    def test_is_bound_false_when_stale(self):
        b = Binding(hwnd=12345, status=BindStatus.STALE)
        self.assertFalse(b.is_bound)

    def test_round_trip(self):
        b = Binding(
            bot_id="b1",
            nickname="shark99",
            room="pokerstars",
            hwnd=55555,
            title="PokerStars Table",
            process_name="PokerStars.exe",
            client_rect=(100, 200, 800, 600),
            status=BindStatus.BOUND,
            bound_at=1700000000.0,
            account_id="acc_1",
        )
        d = b.to_dict()
        b2 = Binding.from_dict(d)
        self.assertEqual(b2.bot_id, "b1")
        self.assertEqual(b2.nickname, "shark99")
        self.assertEqual(b2.hwnd, 55555)
        self.assertEqual(b2.client_rect, (100, 200, 800, 600))
        self.assertEqual(b2.status, BindStatus.BOUND)
        self.assertEqual(b2.account_id, "acc_1")

    def test_from_dict_missing_fields(self):
        b = Binding.from_dict({"bot_id": "x"})
        self.assertEqual(b.bot_id, "x")
        self.assertEqual(b.status, BindStatus.UNBOUND)
        self.assertEqual(b.client_rect, (0, 0, 0, 0))


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestBindStatus(unittest.TestCase):
    """BindStatus enum."""

    def test_values(self):
        vals = {s.value for s in BindStatus}
        self.assertIn("bound", vals)
        self.assertIn("stale", vals)
        self.assertIn("unbound", vals)
        self.assertIn("error", vals)

    def test_count(self):
        self.assertEqual(len(BindStatus), 4)


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestBotAccountBinderCRUD(unittest.TestCase):
    """Basic CRUD without persistence."""

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

    def test_bind_creates_entry(self):
        b = self.binder.bind("bot_1", nickname="player1", room="pokerstars")
        self.assertEqual(b.bot_id, "bot_1")
        self.assertEqual(b.nickname, "player1")
        self.assertEqual(b.room, "pokerstars")
        self.assertEqual(b.status, BindStatus.UNBOUND)

    def test_bind_updates_existing(self):
        self.binder.bind("bot_1", nickname="old")
        self.binder.bind("bot_1", nickname="new")
        b = self.binder.get("bot_1")
        self.assertEqual(b.nickname, "new")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.binder.get("nope"))

    def test_unbind(self):
        self.binder.bind("bot_1", nickname="x")
        self.assertTrue(self.binder.unbind("bot_1"))
        self.assertIsNone(self.binder.get("bot_1"))

    def test_unbind_nonexistent(self):
        self.assertFalse(self.binder.unbind("nope"))

    def test_list_all(self):
        self.binder.bind("a", nickname="aa")
        self.binder.bind("b", nickname="bb")
        self.assertEqual(len(self.binder.list_all()), 2)

    def test_list_bound_empty(self):
        self.binder.bind("a", nickname="aa")
        self.assertEqual(len(self.binder.list_bound()), 0)

    def test_list_unbound(self):
        self.binder.bind("a", nickname="aa")
        self.binder.bind("b", nickname="bb")
        unbound = self.binder.list_unbound()
        self.assertEqual(len(unbound), 2)


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestPersistence(unittest.TestCase):
    """Save / load round-trip."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_save_and_reload(self):
        binder1 = BotAccountBinder(bindings_path=self.path, auto_save=False)
        binder1.bind("bot_A", nickname="alpha", room="888poker")
        binder1.bind("bot_B", nickname="beta", room="ggpoker")
        binder1.save()

        binder2 = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.assertEqual(len(binder2.list_all()), 2)

        a = binder2.get("bot_A")
        self.assertIsNotNone(a)
        self.assertEqual(a.nickname, "alpha")
        self.assertEqual(a.room, "888poker")

    def test_auto_save(self):
        binder = BotAccountBinder(bindings_path=self.path, auto_save=True)
        binder.bind("bot_X", nickname="x")

        # File should exist and contain the binding
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["count"], 1)
        self.assertEqual(raw["bindings"][0]["bot_id"], "bot_X")

    def test_load_from_empty_file(self):
        self.path.write_text("", encoding="utf-8")
        binder = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.assertEqual(len(binder.list_all()), 0)

    def test_load_from_nonexistent_file(self):
        self.path.unlink(missing_ok=True)
        binder = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.assertEqual(len(binder.list_all()), 0)


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestAutoBindMocked(unittest.TestCase):
    """Auto-bind with mocked finder."""

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

    def _make_mock_match(self, hwnd=99999, title="PokerStars - sunnuls"):
        from launcher.auto_window_finder import WindowMatch, WindowRect, MatchMethod
        return WindowMatch(
            hwnd=hwnd,
            title=title,
            window_class="PokerClass",
            process_name="pokerstars.exe",
            process_id=1234,
            full_rect=WindowRect(0, 0, 1920, 1080),
            client_rect=WindowRect(8, 31, 1904, 1041),
            zoom_rect=WindowRect(8, 31, 1904, 1041),
            match_method=MatchMethod.TITLE_SUBSTRING,
            score=0.8,
        )

    def test_auto_bind_success(self):
        self.binder.bind("bot_1", nickname="sunnuls", room="pokerstars")

        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = self._make_mock_match()
        self.binder._finder = mock_finder

        result = self.binder.auto_bind("bot_1")
        self.assertIsNotNone(result)
        self.assertEqual(result.hwnd, 99999)
        self.assertEqual(result.status, BindStatus.BOUND)
        self.assertIn("sunnuls", result.title)

    def test_auto_bind_not_found(self):
        self.binder.bind("bot_1", nickname="sunnuls")

        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = None
        self.binder._finder = mock_finder

        result = self.binder.auto_bind("bot_1")
        self.assertIsNone(result)
        b = self.binder.get("bot_1")
        self.assertEqual(b.status, BindStatus.STALE)

    def test_auto_bind_no_nickname(self):
        self.binder.bind("bot_1")
        result = self.binder.auto_bind("bot_1")
        self.assertIsNone(result)

    def test_auto_bind_nonexistent_bot(self):
        result = self.binder.auto_bind("no_such_bot")
        self.assertIsNone(result)

    def test_auto_bind_all(self):
        self.binder.bind("b1", nickname="nick1")
        self.binder.bind("b2", nickname="nick2")

        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.side_effect = [
            self._make_mock_match(hwnd=111, title="Table - nick1"),
            None,  # nick2 not found
        ]
        self.binder._finder = mock_finder

        results = self.binder.auto_bind_all()
        self.assertTrue(results["b1"])
        self.assertFalse(results["b2"])


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestHealthCheck(unittest.TestCase):
    """Health-check (window alive / stale)."""

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

    def test_check_health_unbound(self):
        self.binder.bind("bot_1", nickname="x")
        status = self.binder.check_health("bot_1")
        self.assertEqual(status, BindStatus.UNBOUND)

    def test_check_health_nonexistent(self):
        status = self.binder.check_health("nope")
        self.assertEqual(status, BindStatus.UNBOUND)

    @unittest.skipUnless(WIN32_AVAILABLE, "Win32 needed for alive check")
    def test_check_health_stale_hwnd(self):
        """A fake hwnd should be detected as stale."""
        b = self.binder.bind("bot_1", nickname="x")
        # Manually set a bogus hwnd
        b.hwnd = 999999999
        b.status = BindStatus.BOUND
        status = self.binder.check_health("bot_1")
        self.assertEqual(status, BindStatus.STALE)

    def test_check_all_health(self):
        self.binder.bind("a", nickname="aa")
        self.binder.bind("b", nickname="bb")
        results = self.binder.check_all_health()
        self.assertIn("a", results)
        self.assertIn("b", results)

    def test_rebind_stale(self):
        self.binder.bind("bot_1", nickname="nick")
        b = self.binder.get("bot_1")
        b.status = BindStatus.STALE

        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = None
        self.binder._finder = mock_finder

        results = self.binder.rebind_stale()
        self.assertIn("bot_1", results)
        self.assertFalse(results["bot_1"])


@unittest.skipUnless(MODULE_AVAILABLE, "bot_account_binder not importable")
class TestBindFromAccount(unittest.TestCase):
    """bind_from_account integration."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)
        # Disable auto-find for most tests
        self.binder._finder = None

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_bind_from_account_basic(self):
        account = MagicMock()
        account.nickname = "player42"
        account.room = "ggpoker"
        account.account_id = "acc_123"
        account.window_info = None

        b = self.binder.bind_from_account("bot_1", account, auto_find=False)
        self.assertEqual(b.nickname, "player42")
        self.assertEqual(b.room, "ggpoker")
        self.assertEqual(b.account_id, "acc_123")

    def test_bind_from_account_with_hwnd(self):
        account = MagicMock()
        account.nickname = "hero"
        account.room = "pokerstars"
        account.account_id = "acc_1"
        account.window_info = MagicMock()
        account.window_info.hwnd = 0
        account.window_info.window_id = "54321"

        b = self.binder.bind_from_account("bot_1", account, auto_find=False)
        self.assertEqual(b.bot_id, "bot_1")
        # hwnd should be extracted from window_id string
        # (resolve may fail on fake hwnd, but the binding is created)
        self.assertIsNotNone(b)

    def test_bind_from_account_no_window_info(self):
        account = MagicMock()
        account.nickname = "test"
        account.room = "888poker"
        account.account_id = "acc_2"
        account.window_info = None

        b = self.binder.bind_from_account("bot_1", account, auto_find=False)
        self.assertEqual(b.nickname, "test")
        self.assertEqual(b.hwnd, 0)


if __name__ == "__main__":
    unittest.main()
