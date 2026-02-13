"""
auto_fill.py — Auto-fill tables with 3 bots (full_hive_month.md Этап 1).

Strategy:
  1. Scan lobby via LiveTableScanner.scan_with_seats()
  2. Filter tables with 1–3 human players and ≥3 free seats
  3. Assign 3 bots from the pool to each target table
  4. Execute join via NavigationManager (or dry-run)

Features:
  - Configurable min/max humans per table
  - Configurable bots-per-table (default 3)
  - Bot pool management: track which bots are assigned
  - Dry-run mode: log assignments without real clicks
  - Cooldown: don't re-fill the same table within N seconds
  - Capacity-aware: skip tables already containing our bots

Usage::

    filler = AutoFiller(
        bot_pool=["bot_1", "bot_2", "bot_3", "bot_4", "bot_5"],
        bots_per_table=3,
        dry_run=True,
    )
    result = filler.fill_once(scanner)
    print(result)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Graceful imports
try:
    from live_table_scanner import LiveTableScanner, SeatInfo
    HAS_SCANNER = True
except Exception:
    HAS_SCANNER = False

try:
    from launcher.navigation_manager import NavigationManager, NavResult, NavStatus
    HAS_NAV = True
except Exception:
    HAS_NAV = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FillAssignment:
    """One bot → table assignment.

    Attributes:
        bot_id:     Bot identifier.
        table_name: Target table name.
        stakes:     Table stakes.
        seat_info:  Full seat information snapshot.
        status:     "pending" / "joined" / "failed" / "dry_run".
        assigned_at: Timestamp of assignment.
    """
    bot_id: str = ""
    table_name: str = ""
    stakes: str = ""
    seat_info: Optional[SeatInfo] = None
    status: str = "pending"
    assigned_at: float = 0.0


@dataclass
class FillResult:
    """Result of one fill_once() cycle.

    Attributes:
        tables_scanned:  How many tables were seen in the lobby.
        targets_found:   How many tables matched the fill criteria.
        assignments:     List of bot→table assignments made.
        bots_assigned:   Total bots assigned this cycle.
        bots_available:  Bots remaining in the pool.
        elapsed:         Time spent (seconds).
        message:         Summary message.
    """
    tables_scanned: int = 0
    targets_found: int = 0
    assignments: List[FillAssignment] = field(default_factory=list)
    bots_assigned: int = 0
    bots_available: int = 0
    elapsed: float = 0.0
    message: str = ""


# ---------------------------------------------------------------------------
# AutoFiller
# ---------------------------------------------------------------------------

class AutoFiller:
    """Assigns bots from a pool to lobby tables with few humans.

    Parameters
    ----------
    bot_pool : list[str]
        Available bot IDs that can be assigned.
    bots_per_table : int
        How many bots to send to each target table (default 3).
    min_humans : int
        Minimum human players at a table (default 1).
    max_humans : int
        Maximum human players at a table (default 3).
    min_free_seats : int
        Minimum free seats required at the table.
    max_table_size : int
        Maximum table size to consider.
    known_bot_nicks : list[str] | None
        Nicknames of our bots (to distinguish from humans in seat scan).
    cooldown_seconds : float
        Don't re-target the same table within this period.
    dry_run : bool
        If True, log assignments but don't actually join.
    """

    def __init__(
        self,
        bot_pool: List[str] | None = None,
        bots_per_table: int = 3,
        min_humans: int = 1,
        max_humans: int = 3,
        min_free_seats: int = 3,
        max_table_size: int = 9,
        known_bot_nicks: List[str] | None = None,
        cooldown_seconds: float = 120.0,
        dry_run: bool = False,
    ) -> None:
        self.bot_pool = list(bot_pool or [])
        self.bots_per_table = bots_per_table
        self.min_humans = min_humans
        self.max_humans = max_humans
        self.min_free_seats = min_free_seats
        self.max_table_size = max_table_size
        self.known_bot_nicks = known_bot_nicks or []
        self.cooldown_seconds = cooldown_seconds
        self.dry_run = dry_run

        # State
        self._assigned: Dict[str, str] = {}  # bot_id → table_name
        self._table_cooldown: Dict[str, float] = {}  # table_name → last fill time
        self._history: List[FillAssignment] = []

    # -- pool management ----------------------------------------------------

    @property
    def available_bots(self) -> List[str]:
        """Bots not currently assigned to a table."""
        return [b for b in self.bot_pool if b not in self._assigned]

    @property
    def assigned_bots(self) -> Dict[str, str]:
        """bot_id → table_name mapping."""
        return dict(self._assigned)

    def release_bot(self, bot_id: str) -> bool:
        """Return a bot to the available pool."""
        if bot_id in self._assigned:
            del self._assigned[bot_id]
            return True
        return False

    def release_table(self, table_name: str) -> int:
        """Release all bots assigned to a table."""
        to_release = [b for b, t in self._assigned.items() if t == table_name]
        for b in to_release:
            del self._assigned[b]
        return len(to_release)

    # -- core fill logic ----------------------------------------------------

    def fill_once(
        self,
        scanner: Optional[Any] = None,
        seats: Optional[List[SeatInfo]] = None,
    ) -> FillResult:
        """Run one fill cycle: scan → filter → assign.

        Provide either a *scanner* (will call scan_with_seats)
        or pre-computed *seats* list.

        Returns:
            FillResult with assignments.
        """
        t0 = time.monotonic()
        result = FillResult()

        # Step 1: get seat info
        if seats is None and scanner is not None and HAS_SCANNER:
            seats = scanner.scan_with_seats(
                known_bot_nicks=self.known_bot_nicks,
            )
        elif seats is None:
            seats = []

        result.tables_scanned = len(seats)

        # Step 2: filter targets
        if HAS_SCANNER and scanner is not None:
            targets = scanner.find_targets(
                seats,
                min_humans=self.min_humans,
                max_humans=self.max_humans,
                min_free=self.min_free_seats,
                max_table_size=self.max_table_size,
            )
        else:
            targets = self._filter_targets(seats)

        # Apply cooldown
        now = time.monotonic()
        targets = [
            t for t in targets
            if now - self._table_cooldown.get(t.table_name, 0) > self.cooldown_seconds
        ]

        result.targets_found = len(targets)

        # Step 3: assign bots
        available = self.available_bots
        for target in targets:
            if len(available) < self.bots_per_table:
                break  # not enough bots

            # Assign N bots
            batch = available[:self.bots_per_table]
            for bot_id in batch:
                assignment = FillAssignment(
                    bot_id=bot_id,
                    table_name=target.table_name,
                    stakes=target.stakes,
                    seat_info=target,
                    status="dry_run" if self.dry_run else "pending",
                    assigned_at=time.time(),
                )
                self._assigned[bot_id] = target.table_name
                self._history.append(assignment)
                result.assignments.append(assignment)

                logger.info(
                    "[%s] Assigned bot %s → table '%s' (%s)",
                    "DRY-RUN" if self.dry_run else "FILL",
                    bot_id, target.table_name, target.stakes,
                )

            self._table_cooldown[target.table_name] = now
            available = self.available_bots  # refresh

        result.bots_assigned = len(result.assignments)
        result.bots_available = len(self.available_bots)
        result.elapsed = time.monotonic() - t0
        result.message = (
            f"Scanned {result.tables_scanned} tables, "
            f"{result.targets_found} targets, "
            f"assigned {result.bots_assigned} bots"
        )

        logger.info("fill_once: %s", result.message)
        return result

    def fill_loop(
        self,
        scanner: Optional[Any] = None,
        rounds: int = 5,
        delay_between: float = 10.0,
    ) -> List[FillResult]:
        """Run multiple fill cycles with delays.

        Args:
            scanner:       LiveTableScanner instance.
            rounds:        Number of cycles.
            delay_between: Seconds between cycles.

        Returns:
            List of FillResult per round.
        """
        results = []
        for i in range(rounds):
            logger.info("fill_loop round %d/%d", i + 1, rounds)
            r = self.fill_once(scanner=scanner)
            results.append(r)

            if i < rounds - 1 and delay_between > 0:
                time.sleep(delay_between)

        return results

    # -- internal helpers ---------------------------------------------------

    def _filter_targets(self, seats: List[SeatInfo]) -> List[SeatInfo]:
        """Standalone target filter (without scanner)."""
        targets = []
        for s in seats:
            if s.total_seats > self.max_table_size:
                continue
            if not (self.min_humans <= s.human_count <= self.max_humans):
                continue
            if s.free_seats < self.min_free_seats:
                continue
            s.is_target = True
            targets.append(s)
        return targets

    @property
    def history(self) -> List[FillAssignment]:
        """All assignments ever made."""
        return list(self._history)

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"AutoFiller: {len(self.bot_pool)} bots in pool",
            f"  Assigned: {len(self._assigned)}",
            f"  Available: {len(self.available_bots)}",
            f"  Total assignments: {len(self._history)}",
            f"  Tables on cooldown: {len(self._table_cooldown)}",
        ]
        if self._assigned:
            lines.append("  Current assignments:")
            for bot, table in self._assigned.items():
                lines.append(f"    {bot} → {table}")
        return "\n".join(lines)
