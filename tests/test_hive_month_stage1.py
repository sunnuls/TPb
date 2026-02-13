"""
Tests for full_hive_month.md Этап 1 — Скан столов и авто-заполнение.

Validates:
  - SeatInfo dataclass and properties
  - LiveTableScanner.scan_with_seats() enriched scan
  - LiveTableScanner.find_targets() filtering
  - AutoFiller pool management
  - AutoFiller.fill_once() assignment logic
  - AutoFiller cooldown / capacity logic
  - Acceptance: 3 bots join a table with 1–3 humans
"""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

try:
    from live_table_scanner import (
        LiveTableScanner,
        SeatInfo,
        ScanStats,
        DelayController,
        DelayConfig,
        DelayStrategy,
    )
    SCANNER_AVAILABLE = True
except Exception:
    SCANNER_AVAILABLE = False

try:
    from auto_fill import (
        AutoFiller,
        FillResult,
        FillAssignment,
    )
    FILLER_AVAILABLE = True
except Exception:
    FILLER_AVAILABLE = False


# ---------------------------------------------------------------------------
# SeatInfo tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(SCANNER_AVAILABLE, "live_table_scanner not importable")
class TestSeatInfo(unittest.TestCase):
    """SeatInfo dataclass."""

    def test_defaults(self):
        s = SeatInfo()
        self.assertEqual(s.total_seats, 0)
        self.assertEqual(s.occupied, 0)
        self.assertEqual(s.free_seats, 0)
        self.assertEqual(s.fill_slots, 0)
        self.assertFalse(s.is_target)

    def test_free_seats(self):
        s = SeatInfo(total_seats=6, occupied=2)
        self.assertEqual(s.free_seats, 4)

    def test_fill_slots(self):
        s = SeatInfo(total_seats=6, occupied=2, bot_count=1)
        self.assertEqual(s.fill_slots, 3)

    def test_fill_slots_no_negative(self):
        s = SeatInfo(total_seats=6, occupied=6, bot_count=0)
        self.assertEqual(s.fill_slots, 0)

    def test_human_count(self):
        s = SeatInfo(total_seats=6, occupied=4, human_count=3, bot_count=1)
        self.assertEqual(s.human_count, 3)


# ---------------------------------------------------------------------------
# LiveTableScanner.find_targets
# ---------------------------------------------------------------------------


@unittest.skipUnless(SCANNER_AVAILABLE, "live_table_scanner not importable")
class TestFindTargets(unittest.TestCase):
    """LiveTableScanner.find_targets() filtering."""

    def setUp(self):
        self.scanner = LiveTableScanner(delay_strategy="fixed", delay_base=0)

    def test_filters_by_humans(self):
        seats = [
            SeatInfo(table_name="A", total_seats=6, occupied=2, human_count=2),
            SeatInfo(table_name="B", total_seats=6, occupied=5, human_count=5),
            SeatInfo(table_name="C", total_seats=6, occupied=1, human_count=1),
        ]
        # Fix free_seats (property-based)
        targets = self.scanner.find_targets(seats, min_humans=1, max_humans=3, min_free=3)
        names = [t.table_name for t in targets]
        self.assertIn("A", names)
        self.assertIn("C", names)
        self.assertNotIn("B", names)

    def test_filters_by_free_seats(self):
        seats = [
            SeatInfo(table_name="Full", total_seats=6, occupied=5, human_count=2),
        ]
        targets = self.scanner.find_targets(seats, min_free=3)
        self.assertEqual(len(targets), 0)

    def test_filters_by_table_size(self):
        seats = [
            SeatInfo(table_name="Big", total_seats=12, occupied=3, human_count=3),
        ]
        targets = self.scanner.find_targets(seats, max_table_size=9)
        self.assertEqual(len(targets), 0)

    def test_marks_is_target(self):
        seats = [SeatInfo(table_name="Good", total_seats=6, occupied=2, human_count=2)]
        targets = self.scanner.find_targets(seats, min_humans=1, max_humans=3, min_free=3)
        self.assertTrue(targets[0].is_target)

    def test_empty_list(self):
        targets = self.scanner.find_targets([])
        self.assertEqual(len(targets), 0)


# ---------------------------------------------------------------------------
# AutoFiller pool management
# ---------------------------------------------------------------------------


@unittest.skipUnless(FILLER_AVAILABLE, "auto_fill not importable")
class TestAutoFillerPool(unittest.TestCase):
    """Bot pool management."""

    def test_available_bots(self):
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"])
        self.assertEqual(len(filler.available_bots), 3)

    def test_assigned_bots_empty(self):
        filler = AutoFiller(bot_pool=["b1"])
        self.assertEqual(len(filler.assigned_bots), 0)

    def test_release_bot(self):
        filler = AutoFiller(bot_pool=["b1", "b2"], dry_run=True)
        filler._assigned["b1"] = "table_x"
        self.assertEqual(len(filler.available_bots), 1)
        filler.release_bot("b1")
        self.assertEqual(len(filler.available_bots), 2)

    def test_release_nonexistent(self):
        filler = AutoFiller(bot_pool=["b1"])
        self.assertFalse(filler.release_bot("nope"))

    def test_release_table(self):
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], dry_run=True)
        filler._assigned = {"b1": "T1", "b2": "T1", "b3": "T2"}
        released = filler.release_table("T1")
        self.assertEqual(released, 2)
        self.assertEqual(len(filler.available_bots), 2)


# ---------------------------------------------------------------------------
# AutoFiller.fill_once
# ---------------------------------------------------------------------------


@unittest.skipUnless(FILLER_AVAILABLE and SCANNER_AVAILABLE,
                     "auto_fill + live_table_scanner required")
class TestAutoFillerFillOnce(unittest.TestCase):
    """fill_once() assignment logic."""

    def test_fill_dry_run_basic(self):
        """3 bots assigned to a table with 2 humans."""
        seats = [
            SeatInfo(table_name="Alpha", stakes="NL50",
                     total_seats=6, occupied=2, human_count=2),
        ]
        filler = AutoFiller(
            bot_pool=["b1", "b2", "b3", "b4", "b5"],
            bots_per_table=3,
            dry_run=True,
        )
        result = filler.fill_once(seats=seats)
        self.assertEqual(result.targets_found, 1)
        self.assertEqual(result.bots_assigned, 3)
        self.assertEqual(len(result.assignments), 3)
        for a in result.assignments:
            self.assertEqual(a.table_name, "Alpha")
            self.assertEqual(a.status, "dry_run")

    def test_fill_not_enough_bots(self):
        """Only 2 bots available, need 3 → no assignment."""
        seats = [
            SeatInfo(table_name="Beta", total_seats=6,
                     occupied=2, human_count=2),
        ]
        filler = AutoFiller(bot_pool=["b1", "b2"], bots_per_table=3, dry_run=True)
        result = filler.fill_once(seats=seats)
        self.assertEqual(result.bots_assigned, 0)

    def test_fill_multiple_tables(self):
        """6 bots, 2 tables → 3 bots per table."""
        seats = [
            SeatInfo(table_name="T1", stakes="NL50",
                     total_seats=6, occupied=1, human_count=1),
            SeatInfo(table_name="T2", stakes="NL100",
                     total_seats=6, occupied=2, human_count=2),
        ]
        filler = AutoFiller(
            bot_pool=[f"b{i}" for i in range(6)],
            bots_per_table=3,
            dry_run=True,
        )
        result = filler.fill_once(seats=seats)
        self.assertEqual(result.bots_assigned, 6)
        self.assertEqual(result.targets_found, 2)

    def test_fill_no_targets(self):
        """No tables match criteria → 0 assignments."""
        seats = [
            SeatInfo(table_name="Full", total_seats=6,
                     occupied=5, human_count=5),
        ]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], dry_run=True)
        result = filler.fill_once(seats=seats)
        self.assertEqual(result.bots_assigned, 0)
        self.assertEqual(result.targets_found, 0)

    def test_fill_cooldown(self):
        """Table on cooldown is skipped in next round."""
        seats = [
            SeatInfo(table_name="Cool", total_seats=6,
                     occupied=2, human_count=2),
        ]
        filler = AutoFiller(
            bot_pool=[f"b{i}" for i in range(6)],
            bots_per_table=3,
            cooldown_seconds=60,
            dry_run=True,
        )
        r1 = filler.fill_once(seats=seats)
        self.assertEqual(r1.bots_assigned, 3)

        # Release bots and try again — should be on cooldown
        filler.release_table("Cool")
        r2 = filler.fill_once(seats=seats)
        self.assertEqual(r2.bots_assigned, 0)

    def test_history_tracking(self):
        seats = [SeatInfo(table_name="H", total_seats=6, occupied=1, human_count=1)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        filler.fill_once(seats=seats)
        self.assertEqual(len(filler.history), 3)


# ---------------------------------------------------------------------------
# AutoFiller summary
# ---------------------------------------------------------------------------


@unittest.skipUnless(FILLER_AVAILABLE, "auto_fill not importable")
class TestAutoFillerSummary(unittest.TestCase):
    def test_summary_non_empty(self):
        filler = AutoFiller(bot_pool=["b1", "b2"], dry_run=True)
        s = filler.summary()
        self.assertIn("AutoFiller", s)
        self.assertIn("2 bots", s)


# ---------------------------------------------------------------------------
# Acceptance: 3 bots join table with 1–3 humans
# ---------------------------------------------------------------------------


@unittest.skipUnless(FILLER_AVAILABLE and SCANNER_AVAILABLE,
                     "auto_fill + live_table_scanner required")
class TestAcceptanceThreeBotsJoin(unittest.TestCase):
    """Acceptance: 3 bots → table with 1–3 humans."""

    def test_acceptance_1_human(self):
        """Table with 1 human, 5 free seats → 3 bots join."""
        seats = [SeatInfo(table_name="T1", total_seats=6, occupied=1, human_count=1)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.bots_assigned, 3)
        self.assertEqual(r.assignments[0].table_name, "T1")

    def test_acceptance_2_humans(self):
        """Table with 2 humans, 4 free seats → 3 bots join."""
        seats = [SeatInfo(table_name="T2", total_seats=6, occupied=2, human_count=2)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.bots_assigned, 3)

    def test_acceptance_3_humans(self):
        """Table with 3 humans, 3 free seats → 3 bots join."""
        seats = [SeatInfo(table_name="T3", total_seats=6, occupied=3, human_count=3)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.bots_assigned, 3)

    def test_acceptance_4_humans_rejected(self):
        """Table with 4 humans → not a target (max_humans=3)."""
        seats = [SeatInfo(table_name="T4", total_seats=6, occupied=4, human_count=4)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.bots_assigned, 0)

    def test_acceptance_0_humans_rejected(self):
        """Empty table → not a target (min_humans=1)."""
        seats = [SeatInfo(table_name="Empty", total_seats=6, occupied=0, human_count=0)]
        filler = AutoFiller(bot_pool=["b1", "b2", "b3"], bots_per_table=3, dry_run=True)
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.bots_assigned, 0)

    def test_acceptance_full_flow(self):
        """Full flow: 5 bots, 2 tables (1 good, 1 bad) → 3 bots to good table."""
        seats = [
            SeatInfo(table_name="Good", stakes="NL50",
                     total_seats=6, occupied=2, human_count=2),
            SeatInfo(table_name="Bad", stakes="NL50",
                     total_seats=6, occupied=6, human_count=6),
        ]
        filler = AutoFiller(
            bot_pool=["b1", "b2", "b3", "b4", "b5"],
            bots_per_table=3,
            dry_run=True,
        )
        r = filler.fill_once(seats=seats)
        self.assertEqual(r.tables_scanned, 2)
        self.assertEqual(r.targets_found, 1)
        self.assertEqual(r.bots_assigned, 3)
        self.assertEqual(r.bots_available, 2)

        # All 3 assigned to "Good"
        for a in r.assignments:
            self.assertEqual(a.table_name, "Good")

        # Verify pool state
        self.assertEqual(len(filler.available_bots), 2)
        self.assertEqual(len(filler.assigned_bots), 3)


if __name__ == "__main__":
    unittest.main()
