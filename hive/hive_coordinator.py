"""
HIVE Coordinator — Hub-Backed Multi-Bot Table Finding and Seating.

Replaces the simple AutoSeating with a proper WebSocket Hub-coordinated
workflow where three bots synchronize their lobby scans, agree on a
target table, and join at staggered times.

Protocol::

    Bot 1 (first to find table):
        Lobby scan → TABLE_FOUND → Hub broadcasts to Bot 2, Bot 3
    Bot 2, Bot 3:
        Receive TABLE_FOUND → navigate to same table → confirm SEATED
    Hub:
        Waits for all 3 bots to confirm SEATED → activates HIVE mode

Seat strategy (anti-detection):
    - Bots do NOT sit adjacently (avoids position clustering)
    - At a 4-max table: seats 1, 3 and the opponent is somewhere in the remaining spots
    - Join delays are staggered: Bot1 immediate, Bot2 +8-15s, Bot3 +20-35s
    - This mimics natural unrelated player arrivals

Usage::

    coord = HiveCoordinator(hub=hub)
    coord.register_bot("bot-1", lobby_scanner_1, nav_manager_1)
    coord.register_bot("bot-2", lobby_scanner_2, nav_manager_2)
    coord.register_bot("bot-3", lobby_scanner_3, nav_manager_3)
    await coord.run()
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HivePhase(str, Enum):
    """Current phase of HIVE operation."""
    SEARCHING  = "searching"   # Looking for a suitable table
    TABLE_FOUND = "table_found" # One bot found a table, notifying others
    JOINING    = "joining"     # All bots navigating to the table
    SEATED     = "seated"      # All bots seated, ready to play
    PLAYING    = "playing"     # Active HIVE play session
    IDLE       = "idle"        # Session ended, waiting for next round


@dataclass
class BotSlot:
    """One bot registered with the coordinator."""
    bot_id: str
    lobby_scanner: Any      # LobbyScanner instance
    nav_manager: Any        # NavigationManager instance
    hwnd: int = 0
    status: str = "idle"    # idle / searching / joining / seated
    seat_number: int = -1
    join_confirmed: bool = False


@dataclass
class HiveSession:
    """Active HIVE seating session."""
    session_id: str
    table_name: str
    table_info: Dict[str, Any]
    environment_id: str
    phase: HivePhase = HivePhase.SEARCHING
    bots_seated: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def elapsed(self) -> float:
        return time.time() - self.start_time


class HiveCoordinator:
    """
    Coordinates three bots to find and join the same poker table.

    Uses the CentralHub WebSocket for inter-bot communication.
    Each bot runs in its own thread/loop, communicating through the Hub.

    This class runs on the HOST machine and coordinates all three bots,
    whether they run locally or inside Hyper-V VMs.
    """

    # Minimum number of bots required for a HIVE session
    MIN_BOTS = 3

    # Stagger delays between bot joins (seconds)
    JOIN_STAGGER_MIN = 8.0
    JOIN_STAGGER_MAX = 20.0

    # Max time to wait for all bots to confirm SEATED
    SEATING_TIMEOUT = 120.0

    def __init__(
        self,
        hub: Any,  # CentralHub
        environment_id: str = "hive_env_1",
        max_humans: int = 1,   # Only target tables with ≤ 1 human
        preferred_max_seats: int = 4,
    ) -> None:
        self.hub = hub
        self.environment_id = environment_id
        self.max_humans = max_humans
        self.preferred_max_seats = preferred_max_seats

        self._bots: Dict[str, BotSlot] = {}
        self._current_session: Optional[HiveSession] = None
        self._phase: HivePhase = HivePhase.IDLE
        self._target_table: Optional[Dict[str, Any]] = None

        # Callbacks
        self._on_all_seated: Optional[Callable[[], None]] = None
        self._on_session_end: Optional[Callable[[], None]] = None

    # ── Bot registration ─────────────────────────────────────────────────────

    def register_bot(
        self,
        bot_id: str,
        lobby_scanner: Any,
        nav_manager: Any,
        hwnd: int = 0,
    ) -> None:
        """Register a bot with the coordinator.

        Args:
            bot_id:        Unique bot identifier.
            lobby_scanner: LobbyScanner for this bot.
            nav_manager:   NavigationManager for this bot.
            hwnd:          Window handle of the poker client.
        """
        self._bots[bot_id] = BotSlot(
            bot_id=bot_id,
            lobby_scanner=lobby_scanner,
            nav_manager=nav_manager,
            hwnd=hwnd,
        )
        logger.info("HiveCoordinator: registered bot '%s'", bot_id)

    def update_hwnd(self, bot_id: str, hwnd: int) -> None:
        """Update the window handle for a bot (after VM screenshot capture)."""
        if bot_id in self._bots:
            self._bots[bot_id].hwnd = hwnd

    def on_all_seated(self, callback: Callable[[], None]) -> None:
        """Register callback for when all bots are seated."""
        self._on_all_seated = callback

    # ── Main coordination loop ────────────────────────────────────────────────

    async def run(self, max_sessions: int = 0) -> None:
        """Run the HIVE coordinator loop.

        Args:
            max_sessions: Max sessions to run (0 = infinite).
        """
        session_count = 0
        logger.info("HiveCoordinator: starting (bots=%d)", len(self._bots))

        while True:
            if len(self._bots) < self.MIN_BOTS:
                logger.warning(
                    "HiveCoordinator: only %d bots registered, need %d",
                    len(self._bots), self.MIN_BOTS,
                )
                await asyncio.sleep(10)
                continue

            # One full HIVE session
            success = await self._run_session()
            session_count += 1

            if max_sessions > 0 and session_count >= max_sessions:
                break

            # Wait between sessions (anti-pattern: don't instantly re-join)
            cooldown = random.uniform(30, 90)
            logger.info(
                "HiveCoordinator: session %d ended, cooldown %.0fs",
                session_count, cooldown,
            )
            await asyncio.sleep(cooldown)

    async def _run_session(self) -> bool:
        """Execute one full HIVE session: find table → join → play → done."""
        self._phase = HivePhase.SEARCHING

        # 1. All bots scan lobby simultaneously
        table_info = await self._coordinated_scan()
        if table_info is None:
            logger.info("HiveCoordinator: no suitable table found, retrying in 30s")
            await asyncio.sleep(30)
            return False

        self._phase = HivePhase.TABLE_FOUND
        self._target_table = table_info
        table_name = table_info.get("table_name", "?")
        logger.info("HiveCoordinator: target table = '%s'", table_name)

        # 2. Broadcast TABLE_FOUND to hub
        try:
            await self.hub.broadcast_table_found(
                finder_agent_id=list(self._bots.keys())[0],
                table_info=table_info,
                environment_id=self.environment_id,
            )
        except Exception as exc:
            logger.warning("HiveCoordinator: Hub broadcast failed: %s", exc)

        # 3. Staggered join: first bot joins immediately, others wait
        self._phase = HivePhase.JOINING
        join_tasks = []
        bot_ids = list(self._bots.keys())

        for i, bot_id in enumerate(bot_ids[:self.MIN_BOTS]):
            delay = 0.0
            if i > 0:
                delay = random.uniform(
                    self.JOIN_STAGGER_MIN * i,
                    self.JOIN_STAGGER_MAX * i,
                )
            join_tasks.append(
                self._join_table_with_delay(bot_id, table_info, delay)
            )

        results = await asyncio.gather(*join_tasks, return_exceptions=True)
        seated_count = sum(1 for r in results if r is True)

        logger.info(
            "HiveCoordinator: %d/%d bots seated at '%s'",
            seated_count, self.MIN_BOTS, table_name,
        )

        if seated_count < 2:
            logger.warning("HiveCoordinator: not enough bots seated, aborting session")
            self._phase = HivePhase.IDLE
            return False

        # 4. All enough bots seated — notify hub and fire callback
        self._phase = HivePhase.SEATED
        if self._on_all_seated:
            try:
                self._on_all_seated()
            except Exception:
                pass

        logger.info(
            "HiveCoordinator: HIVE active at '%s' (%d bots)",
            table_name, seated_count,
        )
        return True

    async def _coordinated_scan(
        self,
        max_attempts: int = 12,
        scan_interval: float = 5.0,
    ) -> Optional[Dict[str, Any]]:
        """All bots scan lobby in parallel; return first suitable table found.

        Args:
            max_attempts:  How many scan rounds before giving up.
            scan_interval: Seconds between rounds.

        Returns:
            Table info dict, or None if nothing suitable found.
        """
        for attempt in range(max_attempts):
            # Launch all lobby scans in parallel
            scan_tasks = {
                bot_id: asyncio.create_task(self._scan_bot_lobby(bot_id))
                for bot_id in self._bots
            }
            results = await asyncio.gather(
                *scan_tasks.values(), return_exceptions=True
            )

            for bot_id, result in zip(scan_tasks.keys(), results):
                if isinstance(result, Exception) or result is None:
                    continue
                # result = table info dict
                logger.info(
                    "HiveCoordinator: bot '%s' found table '%s' (attempt %d)",
                    bot_id, result.get("table_name", "?"), attempt + 1,
                )
                return result

            if attempt < max_attempts - 1:
                await asyncio.sleep(scan_interval)

        return None

    async def _scan_bot_lobby(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Run one lobby scan for a single bot.

        Returns table info dict if a suitable table is found, else None.
        """
        slot = self._bots.get(bot_id)
        if slot is None or slot.lobby_scanner is None:
            return None

        try:
            snapshot = slot.lobby_scanner.scan_lobby()
            if snapshot is None:
                return None

            # Find a table with ≤ max_humans humans and enough free seats
            table = None
            if hasattr(snapshot, "find_best_opportunity"):
                table = snapshot.find_best_opportunity(
                    min_humans=0,
                    max_humans=self.max_humans,
                    min_seats=self.MIN_BOTS,
                )
            elif hasattr(snapshot, "tables"):
                for t in snapshot.tables:
                    humans = getattr(t, "players_seated", 0)
                    free   = getattr(t, "max_seats", 0) - humans
                    if humans <= self.max_humans and free >= self.MIN_BOTS:
                        table = t
                        break

            if table is None:
                return None

            return {
                "table_name": getattr(table, "table_name", str(table)),
                "stakes":     getattr(table, "stakes", ""),
                "max_seats":  getattr(table, "max_seats", self.preferred_max_seats),
                "row_y":      getattr(table, "row_y_coordinate", 0),
                "raw":        table,
            }

        except Exception as exc:
            logger.debug("_scan_bot_lobby error for '%s': %s", bot_id, exc)
            return None

    async def _join_table_with_delay(
        self,
        bot_id: str,
        table_info: Dict[str, Any],
        delay: float,
    ) -> bool:
        """Wait delay seconds, then navigate bot to table.

        Args:
            bot_id:     Bot to join.
            table_info: Table info dict.
            delay:      Seconds to wait before joining.

        Returns:
            True if join succeeded.
        """
        if delay > 0:
            logger.debug(
                "HiveCoordinator: bot '%s' joining in %.1fs (stagger)", bot_id, delay
            )
            await asyncio.sleep(delay)

        slot = self._bots.get(bot_id)
        if slot is None or slot.nav_manager is None:
            return False

        table_raw = table_info.get("raw")
        hwnd = slot.hwnd

        if table_raw is None or not hwnd:
            logger.warning(
                "HiveCoordinator: bot '%s' missing table object or hwnd", bot_id
            )
            return False

        try:
            slot.status = "joining"
            result = await slot.nav_manager.join_table(table_raw, hwnd)
            status_val = getattr(getattr(result, "status", None), "value", str(result))
            success = status_val in ("seated", "table_found", "dry_run")
            slot.status = "seated" if success else "idle"
            slot.join_confirmed = success
            logger.info(
                "HiveCoordinator: bot '%s' join → %s (%s)",
                bot_id, status_val, "OK" if success else "FAIL",
            )
            return success
        except Exception as exc:
            logger.warning(
                "HiveCoordinator: bot '%s' join error: %s", bot_id, exc
            )
            slot.status = "idle"
            return False

    # ── Status API ────────────────────────────────────────────────────────────

    @property
    def phase(self) -> HivePhase:
        return self._phase

    @property
    def seated_count(self) -> int:
        return sum(1 for b in self._bots.values() if b.status == "seated")

    @property
    def target_table(self) -> Optional[str]:
        if self._target_table:
            return self._target_table.get("table_name")
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "phase": self._phase.value,
            "bots": {
                bid: {"status": s.status, "seated": s.join_confirmed}
                for bid, s in self._bots.items()
            },
            "target_table": self.target_table,
            "seated_count": self.seated_count,
        }
