"""
Bot Instance - Launcher Application (Roadmap6 Phase 2 + settings.md Phase 2 + account_binding.md Phase 2).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Wrapper for single bot instance
- Vision → Decision → Action cycle
- Status tracking
- Statistics collection
- Per-bot profile loading from BotProfileManager (settings.md Phase 2)
- On-the-fly profile switching
- Profile → BotSettings conversion
- Account binding: load binding at start, auto-bind window (account_binding.md Phase 2)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig
from launcher.bot_settings import BotSettings

# Graceful import of profile manager (settings.md Phase 1)
try:
    from launcher.bot_profile_manager import BotProfileManager, BotProfile
    HAS_PROFILE_MANAGER = True
except (ImportError, Exception):
    HAS_PROFILE_MANAGER = False

# Graceful import of account binder (account_binding.md Phase 2)
try:
    from launcher.bot_account_binder import (
        BotAccountBinder,
        Binding,
        BindStatus,
    )
    HAS_ACCOUNT_BINDER = True
except (ImportError, Exception):
    HAS_ACCOUNT_BINDER = False

logger = logging.getLogger(__name__)


class BotStatus(str, Enum):
    """Bot operational status."""
    IDLE = "idle"
    STARTING = "starting"
    SEARCHING = "searching"
    SEATED = "seated"
    PLAYING = "playing"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class BotStatistics:
    """
    Bot statistics.
    
    Attributes:
        hands_played: Number of hands played
        pot_won: Total pot won
        pot_lost: Total pot lost
        vision_errors: Number of vision errors
        decisions_made: Number of decisions made
        actions_executed: Number of actions executed
        uptime_seconds: Total uptime in seconds
    """
    hands_played: int = 0
    pot_won: float = 0.0
    pot_lost: float = 0.0
    vision_errors: int = 0
    decisions_made: int = 0
    actions_executed: int = 0
    uptime_seconds: float = 0.0
    
    def net_profit(self) -> float:
        """Calculate net profit."""
        return self.pot_won - self.pot_lost


@dataclass
class BotInstance:
    """
    Single bot instance.
    
    Attributes:
        bot_id: Unique bot identifier
        account: Associated account
        roi_config: ROI configuration
        status: Current status
        current_table: Current table name
        stack: Current stack size
        collective_edge: Current collective edge (if in HIVE)
        stats: Bot statistics
        start_time: Start timestamp
        error_message: Last error message
    
    ⚠️ EDUCATIONAL NOTE:
        Represents single bot instance for coordinated operation.
    """
    bot_id: str = field(default_factory=lambda: str(uuid4()))
    account: Optional[Account] = None
    roi_config: Optional[ROIConfig] = None
    settings: BotSettings = field(default_factory=BotSettings)
    status: BotStatus = BotStatus.IDLE
    current_table: str = ""
    stack: float = 0.0
    collective_edge: float = 0.0
    stats: BotStatistics = field(default_factory=BotStatistics)
    start_time: Optional[float] = None
    error_message: str = ""

    # Per-bot profile (settings.md Phase 2)
    profile_name: str = ""
    _profile: Optional[Any] = field(default=None, repr=False)
    _profile_manager: Optional[Any] = field(default=None, repr=False)

    # Account binding (account_binding.md Phase 2)
    _binding: Optional[Any] = field(default=None, repr=False)
    _binder: Optional[Any] = field(default=None, repr=False)

    # Internal state
    _running: bool = False
    _task: Optional[asyncio.Task] = None
    
    def is_active(self) -> bool:
        """Check if bot is active."""
        return self.status in [
            BotStatus.STARTING,
            BotStatus.SEARCHING,
            BotStatus.SEATED,
            BotStatus.PLAYING
        ]
    
    def can_start(self) -> bool:
        """Check if bot can be started."""
        return (
            self.status == BotStatus.IDLE and
            self.account is not None and
            self.account.is_ready_to_run()
        )

    # -- Per-bot profile loading (settings.md Phase 2) -----------------------

    def load_profile(
        self,
        profile_name: str,
        manager: Optional[Any] = None,
    ) -> bool:
        """Load a named profile and apply its settings.

        Args:
            profile_name: Profile key (e.g. "shark", "tag").
            manager: Optional BotProfileManager instance.
                     If not provided, uses self._profile_manager or creates
                     a default one from ``config/bot_profiles.json``.

        Returns:
            True if profile was loaded successfully.
        """
        if not HAS_PROFILE_MANAGER:
            logger.warning("BotProfileManager not available — cannot load profile")
            return False

        mgr = manager or self._profile_manager
        if mgr is None:
            mgr = BotProfileManager()
            self._profile_manager = mgr

        profile = mgr.get_profile(profile_name)
        if profile is None:
            logger.warning("Profile '%s' not found", profile_name)
            return False

        settings = mgr.profile_to_settings(profile_name)
        if settings is None:
            return False

        self.settings = settings
        self.profile_name = profile_name
        self._profile = profile
        mgr.set_active_profile(self.bot_id, profile_name)

        logger.info(
            "Bot %s loaded profile '%s' (aggression=%d, equity=%.2f)",
            self.bot_id[:8], profile_name,
            settings.aggression_level, settings.equity_threshold,
        )
        return True

    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different profile on the fly.

        Same as load_profile but logs the transition.
        """
        old = self.profile_name or "(none)"
        ok = self.load_profile(profile_name)
        if ok:
            logger.info("Bot %s switched profile: %s → %s",
                        self.bot_id[:8], old, profile_name)
        return ok

    def get_profile(self) -> Optional[Any]:
        """Return the currently loaded BotProfile (or None)."""
        return self._profile

    def get_profile_dict(self) -> Dict[str, Any]:
        """Return current profile as dict (for UI / API)."""
        if self._profile and hasattr(self._profile, "to_dict"):
            return self._profile.to_dict()
        return {}

    # -- Account binding (account_binding.md Phase 2) -------------------------

    def load_binding(
        self,
        binder: Optional[Any] = None,
        *,
        auto_bind: bool = True,
    ) -> bool:
        """Load account binding at startup.

        Looks up or creates a binding for this bot in the
        :class:`BotAccountBinder`. If *auto_bind* is True, also tries
        to discover the window automatically by nickname.

        Args:
            binder: Optional BotAccountBinder instance.
                    If not provided, uses self._binder or creates a default.
            auto_bind: Attempt window auto-discovery.

        Returns:
            True if a binding is associated (even if window not yet found).
        """
        if not HAS_ACCOUNT_BINDER:
            logger.warning("BotAccountBinder not available — cannot load binding")
            return False

        mgr = binder or self._binder
        if mgr is None:
            mgr = BotAccountBinder(auto_save=False)
            self._binder = mgr

        nickname = self.account.nickname if self.account else ""
        room = self.account.room if self.account else ""
        account_id = self.account.account_id if self.account else ""

        # Use bind_from_account if we have an account object
        if self.account is not None:
            binding = mgr.bind_from_account(
                self.bot_id,
                self.account,
                auto_find=auto_bind,
            )
        else:
            binding = mgr.bind(
                self.bot_id,
                nickname=nickname,
                room=room,
                account_id=account_id,
            )
            if auto_bind:
                mgr.auto_bind(self.bot_id)
                binding = mgr.get(self.bot_id) or binding

        self._binding = binding
        self._binder = mgr
        logger.info(
            "Bot %s binding loaded: nickname=%r window=%r status=%s",
            self.bot_id[:8],
            binding.nickname,
            binding.title or "(none)",
            binding.status.value,
        )
        return True

    def get_binding(self) -> Optional[Any]:
        """Return the current Binding or None."""
        return self._binding

    def get_binding_dict(self) -> Dict[str, Any]:
        """Return current binding as dict (for UI / API)."""
        if self._binding and hasattr(self._binding, "to_dict"):
            return self._binding.to_dict()
        return {}

    def check_binding_health(self) -> Optional[str]:
        """Check if bound window is still alive.

        Returns status string or None if no binder.
        """
        if not HAS_ACCOUNT_BINDER or self._binder is None:
            return None
        status = self._binder.check_health(self.bot_id)
        if self._binding:
            self._binding = self._binder.get(self.bot_id) or self._binding
        return status.value if hasattr(status, "value") else str(status)

    def rebind_window(self) -> bool:
        """Try to re-discover the window (e.g. after poker client restart)."""
        if not HAS_ACCOUNT_BINDER or self._binder is None:
            return False
        result = self._binder.auto_bind(self.bot_id)
        if result:
            self._binding = result
        return result is not None and result.is_bound

    async def start(self):
        """
        Start bot instance.
        
        This is a high-level wrapper that would integrate with:
        - bridge/bridge_main.py (vision + state)
        - sim_engine/collective_decision.py (decision)
        - bridge/action/real_executor.py (action)
        """
        if not self.can_start():
            logger.error(f"Bot {self.bot_id[:8]} cannot start")
            return
        
        logger.info(f"Starting bot {self.bot_id[:8]} ({self.account.nickname})...")
        
        self._running = True
        self.status = BotStatus.STARTING
        self.start_time = time.time()

        # Load account binding at start (account_binding.md Phase 2)
        if self._binding is None and HAS_ACCOUNT_BINDER:
            try:
                self.load_binding()
            except Exception as exc:
                logger.warning("Failed to load binding at start: %s", exc)
        
        # Create async task
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """Stop bot instance."""
        logger.info(f"Stopping bot {self.bot_id[:8]} ({self.account.nickname})...")
        
        self._running = False
        
        # Cancel task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Update status
        self.status = BotStatus.STOPPED
        
        # Update uptime
        if self.start_time:
            self.stats.uptime_seconds = time.time() - self.start_time
    
    async def _run_loop(self):
        """
        Main bot loop (placeholder for Phase 2).
        
        In Phase 4, this will integrate with:
        - BridgeMain for vision
        - CollectiveDecision for HIVE decisions
        - RealActionExecutor for actions
        """
        try:
            logger.info(f"Bot {self.bot_id[:8]} entering main loop...")
            
            # Transition to searching
            self.status = BotStatus.SEARCHING
            
            while self._running:
                # Placeholder cycle
                await asyncio.sleep(1.0)
                
                # Update uptime
                if self.start_time:
                    self.stats.uptime_seconds = time.time() - self.start_time
                
                # Simulate status progression (for testing)
                if self.status == BotStatus.SEARCHING:
                    # Would search for tables here
                    pass
        
        except Exception as e:
            logger.error(f"Bot {self.bot_id[:8]} error: {e}")
            self.status = BotStatus.ERROR
            self.error_message = str(e)
        
        finally:
            logger.info(f"Bot {self.bot_id[:8]} loop exited")
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'bot_id': self.bot_id,
            'account_id': self.account.account_id if self.account else None,
            'nickname': self.account.nickname if self.account else "N/A",
            'status': self.status.value,
            'current_table': self.current_table,
            'stack': self.stack,
            'collective_edge': self.collective_edge,
            'profile_name': self.profile_name,
            'binding': self.get_binding_dict(),
            'settings': self.settings.to_dict(),
            'stats': {
                'hands_played': self.stats.hands_played,
                'pot_won': self.stats.pot_won,
                'pot_lost': self.stats.pot_lost,
                'net_profit': self.stats.net_profit(),
                'vision_errors': self.stats.vision_errors,
                'decisions_made': self.stats.decisions_made,
                'actions_executed': self.stats.actions_executed,
                'uptime_seconds': self.stats.uptime_seconds
            },
            'error_message': self.error_message
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Bot Instance - Educational Research")
    print("=" * 60)
    print()
    
    # Create account and ROI
    from launcher.models.account import Account, WindowInfo, WindowType
    from launcher.models.roi_config import ROIConfig, ROIZone
    
    account = Account(nickname="TestBot001", room="pokerstars")
    account.window_info = WindowInfo(
        window_id="12345",
        window_title="PokerStars",
        window_type=WindowType.DESKTOP_CLIENT
    )
    account.roi_configured = True
    
    roi_config = ROIConfig(account_id=account.account_id)
    roi_config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
    
    # Create bot instance
    bot = BotInstance(
        account=account,
        roi_config=roi_config
    )
    
    print(f"Bot instance created:")
    print(f"  ID: {bot.bot_id[:8]}...")
    print(f"  Account: {bot.account.nickname}")
    print(f"  Status: {bot.status.value}")
    print(f"  Can start: {bot.can_start()}")
    print()
    
    # Simulate stats
    bot.stats.hands_played = 50
    bot.stats.pot_won = 125.50
    bot.stats.pot_lost = 75.25
    bot.stats.decisions_made = 150
    
    print(f"Simulated statistics:")
    print(f"  Hands played: {bot.stats.hands_played}")
    print(f"  Net profit: ${bot.stats.net_profit():.2f}")
    print(f"  Decisions made: {bot.stats.decisions_made}")
    print()
    
    # Convert to dict
    data = bot.to_dict()
    print(f"Bot as dict: {len(data)} fields")
    print()
    
    print("=" * 60)
    print("Bot instance demonstration complete")
    print("=" * 60)
