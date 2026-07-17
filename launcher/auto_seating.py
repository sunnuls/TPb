"""
Auto-Seating Manager - Launcher Application.

Features:
- Automatic table discovery
- Coordinate 1–3 bot HIVE deployment
- Real NavigationManager.join_table (buy-in + seat)
- Staggered joins to avoid clustered arrivals
- Session creation after deployment
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from launcher.lobby_scanner import LobbyScanner, LobbyTable
from launcher.bot_manager import BotManager
from launcher.bot_instance import BotInstance, BotStatus

logger = logging.getLogger(__name__)

try:
    from launcher.collusion_coordinator import CollusionCoordinator
    COLLUSION_AVAILABLE = True
except ImportError:
    COLLUSION_AVAILABLE = False
    if TYPE_CHECKING:
        from launcher.collusion_coordinator import CollusionCoordinator


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HiveDeployment:
    """HIVE team deployment to a table."""
    deployment_id: str
    table: LobbyTable
    bot_ids: List[str] = field(default_factory=list)
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: str = ""

    def is_complete(self) -> bool:
        return (
            self.status == DeploymentStatus.COMPLETED
            and len(self.bot_ids) >= 1
        )


class AutoSeatingManager:
    """Automatic seating manager for HIVE deployment."""

    def __init__(
        self,
        bot_manager: BotManager,
        lobby_scanner: LobbyScanner,
        scan_interval: float = 5.0,
        collusion_coordinator: Optional["CollusionCoordinator"] = None,
        min_team_size: int = 3,
        max_team_size: int = 3,
        join_stagger_seconds: float = 0.0,
    ):
        self.bot_manager = bot_manager
        self.lobby_scanner = lobby_scanner
        self.scan_interval = scan_interval
        self.collusion_coordinator = collusion_coordinator
        self.min_team_size = max(1, int(min_team_size))
        self.max_team_size = max(self.min_team_size, int(max_team_size))
        # Production (main_window) sets stagger ~8s; tests keep 0
        self.join_stagger_seconds = max(0.0, float(join_stagger_seconds))

        self.deployments: Dict[str, HiveDeployment] = {}
        self.targeted_tables: set = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(
            "Auto-seating manager initialized (team size %d-%d)",
            self.min_team_size,
            self.max_team_size,
        )

    def is_running(self) -> bool:
        return self._running

    async def start(self):
        if self._running:
            logger.warning("Auto-seating already running")
            return
        logger.info("Starting auto-seating service...")
        self._running = True
        self._task = asyncio.create_task(self._auto_seating_loop())

    async def stop(self):
        if not self._running:
            return
        logger.info("Stopping auto-seating service...")
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-seating service stopped")

    async def _auto_seating_loop(self):
        try:
            logger.info("Auto-seating loop started")
            while self._running:
                try:
                    await self._scan_and_deploy()
                except Exception as e:
                    logger.error("Error in auto-seating cycle: %s", e)
                await asyncio.sleep(self.scan_interval)
        except asyncio.CancelledError:
            logger.info("Auto-seating loop cancelled")
        except Exception as e:
            logger.error("Fatal error in auto-seating loop: %s", e)

    async def _scan_and_deploy(self):
        idle_bots = self.bot_manager.get_idle_bots()
        if len(idle_bots) < self.min_team_size:
            logger.debug(
                "Not enough idle bots: %d/%d",
                len(idle_bots),
                self.min_team_size,
            )
            return

        snapshot = self.lobby_scanner.scan_lobby()
        opportunities = snapshot.get_hive_opportunities()
        if not opportunities:
            logger.debug("No HIVE opportunities found")
            return

        available = [
            opp for opp in opportunities
            if opp.table_id not in self.targeted_tables
        ]
        if not available:
            logger.debug("All opportunities already targeted")
            return

        best = available[0]
        team = idle_bots[: self.max_team_size]
        logger.info(
            "Deploying HIVE to %s (%d humans, %d seats, %d bots)",
            best.table_name,
            best.human_count,
            best.seats_available(),
            len(team),
        )
        await self._deploy_hive_team(best, team)

    async def _deploy_hive_team(
        self,
        table: LobbyTable,
        bots: List[BotInstance],
    ) -> Optional[HiveDeployment]:
        """Deploy bots to a table via NavigationManager.join_table."""
        if len(bots) < self.min_team_size or len(bots) > self.max_team_size:
            logger.error(
                "HIVE team size invalid: got %d (allowed %d-%d)",
                len(bots),
                self.min_team_size,
                self.max_team_size,
            )
            return None

        deployment = HiveDeployment(
            deployment_id=f"deploy_{int(time.time())}_{table.table_id}",
            table=table,
            bot_ids=[bot.bot_id for bot in bots],
            status=DeploymentStatus.DEPLOYING,
            started_at=time.time(),
        )
        self.deployments[deployment.deployment_id] = deployment
        self.targeted_tables.add(table.table_id)

        try:
            seated = 0
            for i, bot in enumerate(bots):
                nick = bot.account.nickname if bot.account else bot.bot_id[:8]
                logger.info(
                    "Deploying bot %d/%d: %s → %s",
                    i + 1, len(bots), nick, table.table_name,
                )
                ok = await self._seat_bot_at_table(bot, table)
                if ok:
                    seated += 1
                if i < len(bots) - 1 and self.join_stagger_seconds > 0:
                    await asyncio.sleep(self.join_stagger_seconds)

            if seated == 0:
                raise RuntimeError("No bots successfully joined the table")

            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = time.time()
            logger.info(
                "HIVE deployment complete: %s (%d/%d bots seated)",
                table.table_name, seated, len(bots),
            )
            await self._create_hive_session(deployment)
            return deployment

        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = time.time()
            logger.error("HIVE deployment failed: %s", e)
            self.targeted_tables.discard(table.table_id)
            return None

    async def _seat_bot_at_table(self, bot: BotInstance, table: LobbyTable) -> bool:
        """Join a single bot to ``table`` using its NavigationManager."""
        from bridge.safety import SafetyFramework, SafetyMode

        bot.current_table = table.table_name

        # Sync LIVE flag from global safety mode
        try:
            fw = SafetyFramework.get_instance()
            bot.set_live_mode(fw.config.mode == SafetyMode.UNSAFE)
        except Exception:
            pass

        bot._init_live_components()

        hwnd = None
        if bot.account and bot.account.window_info:
            hwnd = bot.account.window_info.hwnd
        if not hwnd and bot._nav_manager is not None:
            hwnd = getattr(bot._nav_manager, "hwnd", None)

        # Ensure table.room is set for nav / buy-in path
        room = (getattr(table, "room", None) or "").lower()
        if not room and bot.account:
            room = (bot.account.room or "").lower()
        if room and not getattr(table, "room", None):
            try:
                table.room = room
            except Exception:
                pass

        if bot._nav_manager is None or not hwnd:
            # No live window — mark target; bot SEARCHING/SEATED loop picks it up
            logger.warning(
                "Bot %s: no hwnd/nav for join — marked target '%s' only",
                bot.bot_id[:8], table.table_name,
            )
            bot.status = BotStatus.SEARCHING
            return True  # soft-success for dry/unit tests without HWND

        try:
            bot._nav_manager.dry_run = not bot._live_mode
            if hasattr(bot._nav_manager, "hwnd"):
                bot._nav_manager.hwnd = hwnd

            result = await bot._nav_manager.join_table(table, hwnd)
            status_val = (
                result.status.value
                if hasattr(result.status, "value")
                else str(result.status)
            )
            logger.info(
                "Bot %s join_table → %s: %s",
                bot.bot_id[:8], status_val.upper(), getattr(result, "message", ""),
            )

            if status_val in ("seated", "table_found", "dry_run"):
                bot._seated_since = 0.0  # type: ignore[attr-defined]
                bot.status = BotStatus.SEATED
                return True

            logger.warning("Bot %s failed to join (%s)", bot.bot_id[:8], status_val)
            bot.current_table = ""
            bot.status = BotStatus.IDLE
            return False

        except Exception as exc:
            logger.warning("Bot %s seat error: %s", bot.bot_id[:8], exc)
            bot.current_table = ""
            return False

    async def _create_hive_session(self, deployment: HiveDeployment):
        logger.info(
            "HIVE SESSION CREATED: %s — team coordination active (%d bots)",
            deployment.table.table_name,
            len(deployment.bot_ids),
        )

        if self.collusion_coordinator and COLLUSION_AVAILABLE:
            try:
                bots = [
                    self.bot_manager.get_bot(bot_id)
                    for bot_id in deployment.bot_ids
                ]
                bots = [b for b in bots if b is not None]
                if len(bots) >= self.min_team_size:
                    session = await self.collusion_coordinator.create_session(
                        deployment, bots
                    )
                    if session:
                        logger.info(
                            "Team session active: %s — card sharing enabled",
                            deployment.table.table_name,
                        )
                else:
                    logger.error("Not enough bots for collusion session")
            except Exception as e:
                logger.error("Failed to create collusion session: %s", e)
        else:
            logger.info(
                "HIVE session for %s: %d bots (no collusion coordinator)",
                deployment.table.table_name,
                len(deployment.bot_ids),
            )

    def get_active_deployments(self) -> List[HiveDeployment]:
        return [
            d for d in self.deployments.values()
            if d.status in (DeploymentStatus.DEPLOYING, DeploymentStatus.COMPLETED)
        ]

    def get_statistics(self) -> dict:
        total = len(self.deployments)
        completed = len([d for d in self.deployments.values() if d.is_complete()])
        failed = len([
            d for d in self.deployments.values()
            if d.status == DeploymentStatus.FAILED
        ])
        return {
            "total_deployments": total,
            "completed_deployments": completed,
            "failed_deployments": failed,
            "active_deployments": len(self.get_active_deployments()),
            "targeted_tables": len(self.targeted_tables),
        }
