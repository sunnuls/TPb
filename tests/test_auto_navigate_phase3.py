"""
Tests for auto_navigate.md Phase 3 — lobby to table automatically (dry-run).

Acceptance criteria:
  - Full dry-run pipeline: lobby → detect screen → scan tables → match → "join"
  - NavigationManager dry-run returns NavStatus.DRY_RUN
  - Mocked pipeline: lobby → table found → seated
  - Mocked pipeline: lobby → no match → scroll → retry → timeout
  - RealActionExecutor nav integration: click_table_entry, execute_nav_action
  - End-to-end: NavManager + RealActionExecutor together (dry-run)
"""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

try:
    from launcher.navigation_manager import (
        NavigationManager,
        NavResult,
        NavStatus,
        ScreenType,
        TableEntry,
        LOBBY_KEYWORDS,
        TABLE_KEYWORDS,
    )
    NAV_AVAILABLE = True
except Exception:
    NAV_AVAILABLE = False

try:
    from bridge.action.real_executor import (
        RealActionExecutor,
        ActionCoordinates,
        ExecutionLog,
        ExecutionResult,
        RiskLevel,
        NAV_AVAILABLE as EXEC_NAV_AVAILABLE,
    )
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
    EXEC_AVAILABLE = True
except Exception:
    EXEC_AVAILABLE = False


# ---------------------------------------------------------------------------
# NavigationManager dry-run tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(NAV_AVAILABLE, "navigation_manager not importable")
class TestDryRunLobbyToTable(unittest.TestCase):
    """Dry-run: lobby → table pipeline."""

    def test_navigate_dry_run_returns_dry_run(self):
        """In dry_run mode, navigate_to_table returns DRY_RUN status."""
        nav = NavigationManager(dry_run=True)
        result = nav.navigate_to_table(stakes="NL50")
        self.assertEqual(result.status, NavStatus.DRY_RUN)

    def test_dry_run_click_at(self):
        nav = NavigationManager(dry_run=True)
        self.assertTrue(nav.click_at(100, 200))

    def test_dry_run_scroll(self):
        nav = NavigationManager(dry_run=True)
        self.assertTrue(nav.scroll_lobby("down", 5))

    def test_dry_run_click_table_row(self):
        nav = NavigationManager(dry_run=True)
        entry = TableEntry(name="TestTable", stakes="NL50", bbox=(100, 130))
        result = nav.click_table_row(entry)
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# Mocked full pipeline
# ---------------------------------------------------------------------------


@unittest.skipUnless(NAV_AVAILABLE, "navigation_manager not importable")
class TestMockedLobbyToTable(unittest.TestCase):
    """Mocked pipeline: detect → scan → match → join → verify."""

    def test_lobby_to_table_success(self):
        """Simulate: lobby → find table → click → join → seated."""
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        table = TableEntry(
            name="Merapi", stakes="NL50",
            players=4, max_players=6,
            game_type="hold'em", bbox=(200, 230),
        )

        # First call: LOBBY, then TABLE after join
        screens = iter([ScreenType.LOBBY, ScreenType.TABLE])

        with patch.object(nav, "detect_screen", side_effect=lambda img=None: next(screens)):
            with patch.object(nav, "scan_lobby_tables", return_value=[table]):
                with patch.object(nav, "click_table_row", return_value=True):
                    with patch.object(nav, "click_join_button", return_value=True):
                        result = nav.navigate_to_table(
                            stakes="NL50", timeout=10,
                        )

        self.assertEqual(result.status, NavStatus.SEATED)
        self.assertIsNotNone(result.table)
        self.assertEqual(result.table.name, "Merapi")
        self.assertGreater(result.elapsed, 0)

    def test_lobby_no_match_scrolls_and_times_out(self):
        """Simulate: lobby → no match → scroll 3 times → no match → LOBBY status."""
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        with patch.object(nav, "detect_screen", return_value=ScreenType.LOBBY):
            with patch.object(nav, "scan_lobby_tables", return_value=[]):
                with patch.object(nav, "scroll_lobby", return_value=True):
                    result = nav.navigate_to_table(
                        stakes="NL9999",
                        timeout=5,
                        max_scrolls=3,
                        scroll_delay=0.01,
                    )

        self.assertEqual(result.status, NavStatus.LOBBY)
        self.assertGreater(result.attempts, 1)

    def test_already_at_table(self):
        """If already at table, returns SEATED immediately."""
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        with patch.object(nav, "detect_screen", return_value=ScreenType.TABLE):
            result = nav.navigate_to_table(timeout=5)

        self.assertEqual(result.status, NavStatus.SEATED)
        self.assertEqual(result.screen_type, ScreenType.TABLE)

    def test_popup_is_dismissed(self):
        """Popup screen triggers click_join_button to dismiss."""
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        # POPUP → TABLE
        screens = iter([ScreenType.POPUP, ScreenType.TABLE])

        with patch.object(nav, "detect_screen", side_effect=lambda img=None: next(screens)):
            with patch.object(nav, "click_join_button", return_value=True):
                result = nav.navigate_to_table(timeout=10, max_scrolls=1, scroll_delay=0.01)

        self.assertEqual(result.status, NavStatus.SEATED)

    def test_table_found_but_join_unconfirmed(self):
        """Table found but screen didn't change to TABLE → TABLE_FOUND."""
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        table = TableEntry(name="Test", stakes="NL50", players=3, max_players=6, bbox=(50, 80))

        # detect_screen always returns LOBBY
        with patch.object(nav, "detect_screen", return_value=ScreenType.LOBBY):
            with patch.object(nav, "scan_lobby_tables", return_value=[table]):
                with patch.object(nav, "click_table_row", return_value=True):
                    with patch.object(nav, "click_join_button", return_value=True):
                        result = nav.navigate_to_table(
                            stakes="NL50", timeout=10, max_scrolls=0,
                        )

        self.assertEqual(result.status, NavStatus.TABLE_FOUND)
        self.assertIsNotNone(result.table)


# ---------------------------------------------------------------------------
# Screen detection edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(NAV_AVAILABLE, "navigation_manager not importable")
class TestScreenDetectionVariations(unittest.TestCase):
    """Different screen types are detected correctly."""

    def _detect(self, text):
        nav = NavigationManager(dry_run=True)
        with patch.object(nav, "ocr_full", return_value=text):
            return nav.detect_screen(image=np.zeros((10, 10, 3), dtype=np.uint8))

    def test_lobby_ru(self):
        self.assertEqual(self._detect("лобби кэш столы игроки"), ScreenType.LOBBY)

    def test_table_ru(self):
        self.assertEqual(self._detect("фолд колл рейз банк дилер"), ScreenType.TABLE)

    def test_login(self):
        self.assertEqual(self._detect("login password username"), ScreenType.LOGIN)

    def test_mixed_lobby_wins(self):
        """When lobby keywords outnumber table keywords → LOBBY."""
        self.assertEqual(
            self._detect("lobby tables join players stakes cash game fold"),
            ScreenType.LOBBY,
        )


# ---------------------------------------------------------------------------
# Table parsing variations
# ---------------------------------------------------------------------------


@unittest.skipUnless(NAV_AVAILABLE, "navigation_manager not importable")
class TestTableParsing(unittest.TestCase):
    """Various OCR row formats."""

    def test_standard_row(self):
        e = NavigationManager._parse_table_row("Alpha NL50 $0.25/$0.50 Hold'em 4/6", 0, 30)
        self.assertIsNotNone(e)
        self.assertEqual(e.players, 4)
        self.assertEqual(e.max_players, 6)

    def test_cyrillic_row(self):
        e = NavigationManager._parse_table_row("Стол Холдем 100/200 2/6", 0, 30)
        self.assertIsNotNone(e)
        self.assertIn("холдем", e.game_type.lower())

    def test_omaha_plo(self):
        e = NavigationManager._parse_table_row("PLO Omaha $1/$2 5/9", 0, 30)
        self.assertIsNotNone(e)
        self.assertIn("omaha", e.game_type.lower())


# ---------------------------------------------------------------------------
# RealActionExecutor nav integration
# ---------------------------------------------------------------------------


@unittest.skipUnless(EXEC_AVAILABLE, "real_executor not importable")
class TestExecutorNavIntegration(unittest.TestCase):
    """RealActionExecutor nav methods (requires UNSAFE mode)."""

    def _make_executor(self):
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        try:
            return RealActionExecutor(
                safety=safety,
                max_risk_level=RiskLevel.LOW,
                humanization_enabled=False,
            )
        except ImportError:
            self.skipTest("pyautogui not available")

    def test_click_nav_region(self):
        executor = self._make_executor()
        log = executor.click_nav_region(
            100, 200,
            image_offset=(50, 50),
            description="test_click",
        )
        # May be SUCCESS or INVALID_COORDINATES depending on screen size
        self.assertIn(log.result, (
            ExecutionResult.SUCCESS,
            ExecutionResult.INVALID_COORDINATES,
        ))

    def test_click_table_entry(self):
        executor = self._make_executor()
        entry = TableEntry(name="TestTable", stakes="NL50", bbox=(100, 130))
        log = executor.click_table_entry(entry, image_offset=(0, 0))
        self.assertIsInstance(log, ExecutionLog)
        self.assertIn("click_table", log.action_type)

    def test_execute_nav_action_with_table(self):
        executor = self._make_executor()
        table = TableEntry(name="Merapi", stakes="NL50", bbox=(200, 230))
        nav_result = NavResult(
            status=NavStatus.TABLE_FOUND,
            table=table,
        )
        log = executor.execute_nav_action(nav_result)
        self.assertIsInstance(log, ExecutionLog)

    def test_execute_nav_action_no_table(self):
        executor = self._make_executor()
        nav_result = NavResult(status=NavStatus.LOBBY)
        log = executor.execute_nav_action(nav_result)
        self.assertEqual(log.action_type, "nav_noop")
        self.assertEqual(log.result, ExecutionResult.SUCCESS)

    def test_scroll_nav(self):
        executor = self._make_executor()
        log = executor.scroll_nav("down", 3)
        self.assertIsInstance(log, ExecutionLog)
        self.assertEqual(log.action_type, "scroll_down")


# ---------------------------------------------------------------------------
# End-to-end acceptance: NavManager + Executor (dry-run)
# ---------------------------------------------------------------------------


@unittest.skipUnless(NAV_AVAILABLE, "navigation_manager not importable")
class TestAcceptanceLobbyToTableDryRun(unittest.TestCase):
    """Full acceptance test: lobby → table in dry-run mode."""

    def test_full_flow_dry_run(self):
        """
        Acceptance: complete lobby-to-table flow.
        1. Create NavigationManager in dry-run mode
        2. navigate_to_table returns DRY_RUN
        3. Verify all sub-actions work in dry-run
        """
        nav = NavigationManager(dry_run=True)

        # Full navigation
        result = nav.navigate_to_table(
            stakes="NL50",
            min_players=2,
            max_players=6,
            game_type="hold'em",
            timeout=5,
        )
        self.assertEqual(result.status, NavStatus.DRY_RUN)

        # Click operations
        self.assertTrue(nav.click_at(400, 300))
        self.assertTrue(nav.scroll_lobby("down", 5))
        self.assertTrue(nav.scroll_lobby("up", 2))

        entry = TableEntry(name="Dry", stakes="NL50", bbox=(100, 130))
        self.assertTrue(nav.click_table_row(entry, image_offset=(0, 0)))

    def test_mocked_end_to_end_seated(self):
        """
        Acceptance: mocked end-to-end from lobby to seated.
        """
        nav = NavigationManager()
        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        nav._capture_fn = lambda h: fake_img

        tables = [
            TableEntry(name="Alpha", stakes="NL50", players=3, max_players=6,
                       game_type="hold'em", bbox=(50, 80)),
            TableEntry(name="Beta", stakes="NL100", players=5, max_players=6,
                       game_type="hold'em", bbox=(90, 120)),
        ]

        screens = iter([ScreenType.LOBBY, ScreenType.TABLE])

        with patch.object(nav, "detect_screen",
                          side_effect=lambda img=None: next(screens)):
            with patch.object(nav, "scan_lobby_tables", return_value=tables):
                with patch.object(nav, "click_table_row", return_value=True):
                    with patch.object(nav, "click_join_button", return_value=True):
                        result = nav.navigate_to_table(
                            stakes="NL50",
                            min_players=2,
                            timeout=10,
                        )

        self.assertEqual(result.status, NavStatus.SEATED)
        self.assertEqual(result.table.name, "Alpha")
        self.assertEqual(result.table.stakes, "NL50")
        self.assertGreater(result.elapsed, 0)
        self.assertGreater(result.attempts, 0)


if __name__ == "__main__":
    unittest.main()
