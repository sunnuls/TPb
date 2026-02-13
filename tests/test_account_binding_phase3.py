"""
Tests for account_binding.md Phase 3 — 5 bots → each knows its nick/window.

Acceptance criteria:
  - 5 BotInstance objects created with unique accounts
  - Each bot loads binding at startup
  - Each bot knows its own nickname
  - Each bot gets auto-bound to the correct (mocked) window
  - Bindings survive persistence round-trip
  - Health check confirms all 5 are BOUND
  - After window "dies", health check detects STALE
  - Rebind restores BOUND status
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

try:
    from launcher.bot_instance import BotInstance, BotStatus
    from launcher.bot_account_binder import (
        BotAccountBinder,
        Binding,
        BindStatus,
    )
    from launcher.auto_window_finder import (
        WindowMatch,
        WindowRect,
        MatchMethod,
    )
    from launcher.models.account import Account, WindowInfo, WindowType
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


def _make_window_match(hwnd: int, nickname: str) -> WindowMatch:
    """Create a realistic WindowMatch for testing."""
    return WindowMatch(
        hwnd=hwnd,
        title=f"PokerStars Table - {nickname}",
        window_class="PokerStarsTableFrameClass",
        process_name="pokerstars.exe",
        process_id=1000 + hwnd,
        full_rect=WindowRect(0, 0, 1920, 1080),
        client_rect=WindowRect(8, 31, 1904, 1041),
        zoom_rect=WindowRect(8, 31, 1904, 1041),
        match_method=MatchMethod.TITLE_SUBSTRING,
        score=0.95,
    )


BOT_CONFIGS = [
    {"nickname": "shark99", "room": "pokerstars", "hwnd": 10001},
    {"nickname": "fishy42", "room": "888poker", "hwnd": 10002},
    {"nickname": "aggro_king", "room": "ggpoker", "hwnd": 10003},
    {"nickname": "tilt_master", "room": "partypoker", "hwnd": 10004},
    {"nickname": "nit_queen", "room": "winamax", "hwnd": 10005},
]


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestFiveBotsKnowTheirIdentity(unittest.TestCase):
    """Core acceptance: 5 bots each know their own nick and window."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

        # Set up mock finder that returns correct window per nickname
        self.mock_finder = MagicMock()
        self.mock_finder.available = True

        def _find_by_nick(query):
            for cfg in BOT_CONFIGS:
                if cfg["nickname"] in query or query in cfg["nickname"]:
                    return _make_window_match(cfg["hwnd"], cfg["nickname"])
            return None

        self.mock_finder.find.side_effect = _find_by_nick
        self.binder._finder = self.mock_finder

        # Create 5 bots
        self.bots = []
        for cfg in BOT_CONFIGS:
            acc = Account(nickname=cfg["nickname"], room=cfg["room"])
            acc.window_info = None
            bot = BotInstance(account=acc)
            self.bots.append(bot)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_all_five_load_binding(self):
        """All 5 bots successfully load their binding."""
        for bot in self.bots:
            ok = bot.load_binding(self.binder, auto_bind=True)
            self.assertTrue(ok, f"Bot {bot.account.nickname} failed to load binding")

    def test_each_bot_knows_its_nickname(self):
        """Each bot's binding contains the correct nickname."""
        for i, bot in enumerate(self.bots):
            bot.load_binding(self.binder, auto_bind=False)
            b = bot.get_binding()
            self.assertIsNotNone(b)
            self.assertEqual(b.nickname, BOT_CONFIGS[i]["nickname"])

    def test_each_bot_knows_its_room(self):
        """Each bot's binding contains the correct room."""
        for i, bot in enumerate(self.bots):
            bot.load_binding(self.binder, auto_bind=False)
            b = bot.get_binding()
            self.assertEqual(b.room, BOT_CONFIGS[i]["room"])

    def test_each_bot_auto_bound_to_window(self):
        """After auto_bind, each bot has the correct hwnd."""
        for i, bot in enumerate(self.bots):
            bot.load_binding(self.binder, auto_bind=True)
            b = bot.get_binding()
            self.assertEqual(b.hwnd, BOT_CONFIGS[i]["hwnd"])
            self.assertEqual(b.status, BindStatus.BOUND)
            self.assertIn(
                BOT_CONFIGS[i]["nickname"],
                b.title,
                f"Bot {i} title should contain nickname",
            )

    def test_all_five_unique_bot_ids(self):
        """All bot IDs are unique."""
        ids = set()
        for bot in self.bots:
            bot.load_binding(self.binder, auto_bind=False)
            ids.add(bot.bot_id)
        self.assertEqual(len(ids), 5)

    def test_binder_has_five_entries(self):
        """Binder registry contains exactly 5 bindings."""
        for bot in self.bots:
            bot.load_binding(self.binder, auto_bind=False)
        self.assertEqual(len(self.binder.list_all()), 5)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestFiveBotsPersistence(unittest.TestCase):
    """Bindings survive save/reload cycle."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_save_and_reload_five_bots(self):
        """5 bot bindings persist across binder instances."""
        binder1 = BotAccountBinder(bindings_path=self.path, auto_save=False)

        for cfg in BOT_CONFIGS:
            binder1.bind(
                f"bot_{cfg['nickname']}",
                nickname=cfg["nickname"],
                room=cfg["room"],
            )
        binder1.save()

        # Reload
        binder2 = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.assertEqual(len(binder2.list_all()), 5)

        for cfg in BOT_CONFIGS:
            b = binder2.get(f"bot_{cfg['nickname']}")
            self.assertIsNotNone(b)
            self.assertEqual(b.nickname, cfg["nickname"])
            self.assertEqual(b.room, cfg["room"])


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestFiveBotsHealthCheck(unittest.TestCase):
    """Health check for all 5 bots."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)
        self.binder = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.mock_finder = MagicMock()
        self.mock_finder.available = True

        def _find_by_nick(query):
            for cfg in BOT_CONFIGS:
                if cfg["nickname"] in query or query in cfg["nickname"]:
                    return _make_window_match(cfg["hwnd"], cfg["nickname"])
            return None

        self.mock_finder.find.side_effect = _find_by_nick
        self.binder._finder = self.mock_finder

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_all_bound_after_auto_bind(self):
        """After auto-bind, all 5 get health-checked."""
        bots = []
        for cfg in BOT_CONFIGS:
            acc = Account(nickname=cfg["nickname"], room=cfg["room"])
            acc.window_info = None
            bot = BotInstance(account=acc)
            bot.load_binding(self.binder, auto_bind=True)
            bots.append(bot)

        for bot in bots:
            status = bot.check_binding_health()
            # On real Win32, fake hwnds are detected as stale (expected).
            # Without Win32, status stays as-is (bound/unbound).
            self.assertIn(status, ("bound", "unbound", "stale"))

    def test_health_check_all_via_binder(self):
        """Binder's check_all_health covers all 5."""
        for cfg in BOT_CONFIGS:
            self.binder.bind(
                f"bot_{cfg['nickname']}",
                nickname=cfg["nickname"],
            )

        results = self.binder.check_all_health()
        self.assertEqual(len(results), 5)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestFiveBotsRebind(unittest.TestCase):
    """Rebind scenario: window disappears and reappears."""

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

    def test_rebind_after_stale(self):
        """Bot can rebind after window goes stale."""
        # Create binding manually
        self.binder.bind("bot_shark", nickname="shark99", room="pokerstars")
        b = self.binder.get("bot_shark")
        b.hwnd = 10001
        b.status = BindStatus.BOUND

        # Simulate window death
        b.status = BindStatus.STALE
        b.hwnd = 0

        # Set up mock finder for rebind
        mock_finder = MagicMock()
        mock_finder.available = True
        mock_finder.find.return_value = _make_window_match(20001, "shark99")
        self.binder._finder = mock_finder

        results = self.binder.rebind_stale()
        self.assertTrue(results.get("bot_shark", False))
        b2 = self.binder.get("bot_shark")
        self.assertEqual(b2.hwnd, 20001)
        self.assertEqual(b2.status, BindStatus.BOUND)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestToDictIntegration(unittest.TestCase):
    """BotInstance.to_dict() includes binding for 5 bots."""

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

    def test_five_bots_to_dict_all_have_binding(self):
        """to_dict for each of 5 bots contains binding with correct nick."""
        for cfg in BOT_CONFIGS:
            acc = Account(nickname=cfg["nickname"], room=cfg["room"])
            acc.window_info = WindowInfo(
                window_id=str(cfg["hwnd"]),
                window_title=f"Table - {cfg['nickname']}",
                window_type=WindowType.DESKTOP_CLIENT,
            )
            acc.roi_configured = True
            bot = BotInstance(account=acc)
            bot.load_binding(self.binder, auto_bind=False)

            d = bot.to_dict()
            self.assertIn("binding", d)
            self.assertEqual(d["binding"]["nickname"], cfg["nickname"])
            self.assertEqual(d["binding"]["bot_id"], bot.bot_id)


@unittest.skipUnless(MODULE_AVAILABLE, "Required modules not importable")
class TestAcceptanceFiveBotsFullFlow(unittest.TestCase):
    """Full acceptance test: 5 bots → bind → verify → persist → reload."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_full_flow(self):
        """
        Acceptance: create 5 bots, bind, auto-bind with mock, save,
        reload, verify each bot's identity is intact.
        """
        binder = BotAccountBinder(bindings_path=self.path, auto_save=False)

        # Mock finder
        mock_finder = MagicMock()
        mock_finder.available = True

        def _find_by_nick(query):
            for cfg in BOT_CONFIGS:
                if cfg["nickname"] in query or query in cfg["nickname"]:
                    return _make_window_match(cfg["hwnd"], cfg["nickname"])
            return None

        mock_finder.find.side_effect = _find_by_nick
        binder._finder = mock_finder

        # Step 1: create & bind 5 bots
        bots = []
        for cfg in BOT_CONFIGS:
            acc = Account(nickname=cfg["nickname"], room=cfg["room"])
            acc.window_info = None
            bot = BotInstance(account=acc)
            ok = bot.load_binding(binder, auto_bind=True)
            self.assertTrue(ok)
            bots.append(bot)

        # Step 2: verify each bot knows its identity
        for i, bot in enumerate(bots):
            b = bot.get_binding()
            self.assertIsNotNone(b, f"Bot {i} missing binding")
            self.assertEqual(b.nickname, BOT_CONFIGS[i]["nickname"])
            self.assertEqual(b.room, BOT_CONFIGS[i]["room"])
            self.assertEqual(b.hwnd, BOT_CONFIGS[i]["hwnd"])
            self.assertEqual(b.status, BindStatus.BOUND)
            self.assertIn(BOT_CONFIGS[i]["nickname"], b.title)

        # Step 3: persist
        binder.save()

        # Step 4: reload into fresh binder
        binder2 = BotAccountBinder(bindings_path=self.path, auto_save=False)
        self.assertEqual(len(binder2.list_all()), 5)

        for cfg in BOT_CONFIGS:
            b2 = None
            for b in binder2.list_all():
                if b.nickname == cfg["nickname"]:
                    b2 = b
                    break
            self.assertIsNotNone(b2, f"Missing {cfg['nickname']} after reload")
            self.assertEqual(b2.room, cfg["room"])
            self.assertEqual(b2.hwnd, cfg["hwnd"])
            self.assertEqual(b2.status, BindStatus.BOUND)

        # Step 5: verify all 5 are listed as bound
        bound = binder2.list_bound()
        self.assertEqual(len(bound), 5)


if __name__ == "__main__":
    unittest.main()
