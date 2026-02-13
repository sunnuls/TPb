"""
Tests for NavigationManager — Phase 4 of bot_fixes.md.

Tests cover:
  - Data models (TableEntry, NavResult, enums)
  - Screen detection from OCR keywords
  - Table-row parsing from raw text
  - Table matching / filtering
  - Lobby scanning on synthetic images
  - navigate_to_table dry-run
  - Full lobby→table pipeline (mocked capture + OCR)
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

try:
    from launcher.navigation_manager import (
        NavigationManager,
        ScreenType,
        NavStatus,
        NavResult,
        TableEntry,
        LOBBY_KEYWORDS,
        TABLE_KEYWORDS,
    )
    MODULE_AVAILABLE = True
except Exception:
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestScreenType(unittest.TestCase):
    def test_values(self):
        vals = {s.value for s in ScreenType}
        for expected in ("lobby", "table", "login", "popup", "unknown"):
            self.assertIn(expected, vals)


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestNavStatus(unittest.TestCase):
    def test_values(self):
        vals = {s.value for s in NavStatus}
        for expected in ("seated", "table_found", "lobby", "scrolled",
                         "timeout", "error", "dry_run"):
            self.assertIn(expected, vals)


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestTableEntry(unittest.TestCase):
    def test_defaults(self):
        t = TableEntry()
        self.assertEqual(t.name, "")
        self.assertEqual(t.players, 0)
        self.assertEqual(t.bbox, (0, 0))

    def test_custom(self):
        t = TableEntry(name="Merapi", stakes="NL50", players=4, max_players=6)
        self.assertEqual(t.name, "Merapi")
        self.assertEqual(t.stakes, "NL50")
        self.assertEqual(t.players, 4)


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestNavResult(unittest.TestCase):
    def test_defaults(self):
        r = NavResult()
        self.assertEqual(r.status, NavStatus.ERROR)
        self.assertIsNone(r.table)

    def test_custom(self):
        r = NavResult(
            status=NavStatus.SEATED,
            screen_type=ScreenType.TABLE,
            message="OK",
            elapsed=1.5,
            attempts=2,
        )
        self.assertEqual(r.status, NavStatus.SEATED)
        self.assertEqual(r.elapsed, 1.5)


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestKeywords(unittest.TestCase):
    def test_lobby_keywords_non_empty(self):
        self.assertGreater(len(LOBBY_KEYWORDS), 5)

    def test_table_keywords_non_empty(self):
        self.assertGreater(len(TABLE_KEYWORDS), 5)

    def test_keywords_are_lowercase(self):
        for kw in LOBBY_KEYWORDS + TABLE_KEYWORDS:
            self.assertEqual(kw, kw.lower(), f"Keyword should be lowercase: {kw}")


# ---------------------------------------------------------------------------
# _parse_table_row
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestParseTableRow(unittest.TestCase):
    def test_full_row(self):
        text = "Merapi NL50 $0.25/$0.50 Hold'em 4/6"
        entry = NavigationManager._parse_table_row(text, 100, 130)
        self.assertIsNotNone(entry)
        self.assertIn("Merapi", entry.name)
        self.assertEqual(entry.players, 4)
        self.assertEqual(entry.max_players, 6)
        self.assertIn("0.25", entry.stakes)

    def test_minimal_row(self):
        text = "Table123 3/9"
        entry = NavigationManager._parse_table_row(text, 0, 20)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.players, 3)
        self.assertEqual(entry.max_players, 9)

    def test_stakes_only(self):
        text = "NL100 $0.50/$1.00"
        entry = NavigationManager._parse_table_row(text, 0, 20)
        self.assertIsNotNone(entry)
        self.assertIn("0.50", entry.stakes)

    def test_garbage_text(self):
        text = "..."
        entry = NavigationManager._parse_table_row(text, 0, 10)
        self.assertIsNone(entry)

    def test_empty_text(self):
        entry = NavigationManager._parse_table_row("", 0, 0)
        self.assertIsNone(entry)

    def test_game_type_holdem(self):
        text = "River Hold'em 100/200 2/6"
        entry = NavigationManager._parse_table_row(text, 0, 25)
        self.assertIsNotNone(entry)
        self.assertIn("hold", entry.game_type.lower())

    def test_game_type_omaha(self):
        text = "PLO Omaha $1/$2 5/6"
        entry = NavigationManager._parse_table_row(text, 0, 25)
        self.assertIsNotNone(entry)
        self.assertIn("omaha", entry.game_type.lower())

    def test_bbox_preserved(self):
        entry = NavigationManager._parse_table_row("Test 2/6", 50, 80)
        self.assertEqual(entry.bbox, (50, 80))


# ---------------------------------------------------------------------------
# match_table
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestMatchTable(unittest.TestCase):
    def setUp(self):
        self.tables = [
            TableEntry(name="Alpha", stakes="NL50", players=3, max_players=6, game_type="hold'em"),
            TableEntry(name="Beta", stakes="NL100", players=6, max_players=6, game_type="hold'em"),
            TableEntry(name="Gamma", stakes="NL50", players=1, max_players=6, game_type="omaha"),
            TableEntry(name="Delta", stakes="NL200", players=4, max_players=9, game_type="hold'em"),
        ]

    def test_match_by_stakes(self):
        result = NavigationManager.match_table(self.tables, stakes="NL50")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Alpha")

    def test_match_by_min_players(self):
        result = NavigationManager.match_table(
            self.tables, stakes="NL50", min_players=2)
        self.assertEqual(result.name, "Alpha")

    def test_no_match_full_table(self):
        result = NavigationManager.match_table(
            self.tables, stakes="NL100", max_players=5)
        # Beta has 6 players, max_players filter=5 → no match
        self.assertIsNone(result)

    def test_match_by_game_type(self):
        result = NavigationManager.match_table(
            self.tables, stakes="NL50", game_type="omaha")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Gamma")

    def test_no_match_wrong_stakes(self):
        result = NavigationManager.match_table(self.tables, stakes="NL500")
        self.assertIsNone(result)

    def test_empty_list(self):
        result = NavigationManager.match_table([])
        self.assertIsNone(result)

    def test_no_filter_returns_first(self):
        result = NavigationManager.match_table(self.tables)
        self.assertEqual(result.name, "Alpha")


# ---------------------------------------------------------------------------
# Screen detection (mocked OCR)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestDetectScreen(unittest.TestCase):
    def test_lobby_detection(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value="lobby cash game tables players join"):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.LOBBY)

    def test_table_detection(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value="fold call raise pot dealer"):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.TABLE)

    def test_login_detection(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value="login username password sign in"):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.LOGIN)

    def test_popup_detection(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value="ok cancel accept"):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.POPUP)

    def test_unknown_screen(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value="xyzzy gibberish"):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.UNKNOWN)

    def test_empty_ocr(self):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value=""):
            screen = nav.detect_screen(image=np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(screen, ScreenType.UNKNOWN)

    def test_no_image_returns_unknown(self):
        nav = NavigationManager(dry_run=True)
        nav._capture_fn = lambda h: None
        screen = nav.detect_screen()
        self.assertEqual(screen, ScreenType.UNKNOWN)


# ---------------------------------------------------------------------------
# Dry-run navigation
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestDryRun(unittest.TestCase):
    def test_navigate_dry_run(self):
        nav = NavigationManager(dry_run=True)
        result = nav.navigate_to_table(stakes="NL50")
        self.assertEqual(result.status, NavStatus.DRY_RUN)

    def test_click_at_dry_run(self):
        nav = NavigationManager(dry_run=True)
        self.assertTrue(nav.click_at(100, 200))

    def test_scroll_dry_run(self):
        nav = NavigationManager(dry_run=True)
        self.assertTrue(nav.scroll_lobby("down", 3))


# ---------------------------------------------------------------------------
# Full pipeline (mocked)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestFullPipelineMocked(unittest.TestCase):
    """Simulates a complete lobby→table navigation with mocked components."""

    def test_already_at_table(self):
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        with patch.object(nav, "detect_screen", return_value=ScreenType.TABLE):
            result = nav.navigate_to_table(timeout=5)

        self.assertEqual(result.status, NavStatus.SEATED)
        self.assertEqual(result.screen_type, ScreenType.TABLE)

    def test_lobby_no_match_scrolls(self):
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        with patch.object(nav, "detect_screen", return_value=ScreenType.LOBBY):
            with patch.object(nav, "scan_lobby_tables", return_value=[]):
                with patch.object(nav, "scroll_lobby", return_value=True):
                    result = nav.navigate_to_table(
                        stakes="NL9999",
                        timeout=5,
                        max_scrolls=2,
                        scroll_delay=0.1,
                    )

        self.assertEqual(result.status, NavStatus.LOBBY)
        self.assertGreater(result.attempts, 1)

    def test_lobby_table_found_and_joined(self):
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        table = TableEntry(name="Test", stakes="NL50", players=3, max_players=6)
        screens = iter([ScreenType.LOBBY, ScreenType.TABLE])

        with patch.object(nav, "detect_screen", side_effect=lambda img=None: next(screens)):
            with patch.object(nav, "scan_lobby_tables", return_value=[table]):
                with patch.object(nav, "click_table_row", return_value=True):
                    with patch.object(nav, "click_join_button", return_value=True):
                        result = nav.navigate_to_table(stakes="NL50", timeout=10)

        self.assertEqual(result.status, NavStatus.SEATED)
        self.assertIsNotNone(result.table)
        self.assertEqual(result.table.name, "Test")


# ---------------------------------------------------------------------------
# Click / scroll without pyautogui
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "navigation_manager not importable")
class TestClickScroll(unittest.TestCase):
    def test_click_no_autogui(self):
        nav = NavigationManager()
        with patch("launcher.navigation_manager.AUTOGUI_AVAILABLE", False):
            self.assertFalse(nav.click_at(0, 0))

    def test_scroll_no_autogui(self):
        nav = NavigationManager()
        with patch("launcher.navigation_manager.AUTOGUI_AVAILABLE", False):
            self.assertFalse(nav.scroll_lobby())

    def test_click_table_row(self):
        nav = NavigationManager(dry_run=True)
        table = TableEntry(name="X", bbox=(100, 130))
        result = nav.click_table_row(table, image_offset=(50, 50))
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
