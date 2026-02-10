"""
Bot Instance - Launcher Application (Roadmap6 Phase 2).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Wrapper for single bot instance
- Vision → Decision → Action cycle
- Status tracking
- Statistics collection
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig
from launcher.bot_settings import BotSettings

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
