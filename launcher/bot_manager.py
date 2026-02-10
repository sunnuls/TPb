"""
Bot Manager - Launcher Application (Roadmap6 Phase 2).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Manage pool of bot instances
- Start/stop selected bots
- Track active bots
- Aggregate statistics
"""

import asyncio
import logging
from typing import List, Dict, Optional

from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig
from launcher.bot_instance import BotInstance, BotStatus

logger = logging.getLogger(__name__)


class BotManager:
    """
    Bot pool manager.
    
    Features:
    - Create bot instances from accounts
    - Start/stop individual or all bots
    - Track active bots
    - Aggregate statistics
    
    ⚠️ EDUCATIONAL NOTE:
        Manages coordinated bot operation pool.
    """
    
    def __init__(self, max_vision_errors: int = 5):
        """
        Initialize bot manager.
        
        Args:
            max_vision_errors: Max consecutive vision errors before auto-stop
        """
        self.bots: Dict[str, BotInstance] = {}  # bot_id -> BotInstance
        self.account_to_bot: Dict[str, str] = {}  # account_id -> bot_id
        self.max_vision_errors = max_vision_errors
        self._consecutive_vision_errors: Dict[str, int] = {}  # bot_id -> count
        
        logger.info("Bot manager initialized")
        logger.warning(
            "CRITICAL: Bot manager for COORDINATED COLLUSION. "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def create_bot(
        self,
        account: Account,
        roi_config: ROIConfig
    ) -> BotInstance:
        """
        Create bot instance for account.
        
        Args:
            account: Account to use
            roi_config: ROI configuration
        
        Returns:
            Created bot instance
        """
        # Check if account already has a bot
        if account.account_id in self.account_to_bot:
            existing_bot_id = self.account_to_bot[account.account_id]
            logger.warning(f"Account {account.nickname} already has bot {existing_bot_id[:8]}")
            return self.bots[existing_bot_id]
        
        # Create bot
        bot = BotInstance(
            account=account,
            roi_config=roi_config
        )
        
        # Register
        self.bots[bot.bot_id] = bot
        self.account_to_bot[account.account_id] = bot.bot_id
        
        logger.info(f"Bot created: {bot.bot_id[:8]} for {account.nickname}")
        
        return bot
    
    def get_bot(self, bot_id: str) -> Optional[BotInstance]:
        """
        Get bot by ID.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            Bot instance if found
        """
        return self.bots.get(bot_id)
    
    def get_bot_by_account(self, account_id: str) -> Optional[BotInstance]:
        """
        Get bot by account ID.
        
        Args:
            account_id: Account ID
        
        Returns:
            Bot instance if found
        """
        bot_id = self.account_to_bot.get(account_id)
        return self.bots.get(bot_id) if bot_id else None
    
    def get_all_bots(self) -> List[BotInstance]:
        """
        Get all bots.
        
        Returns:
            List of all bots
        """
        return list(self.bots.values())
    
    def get_active_bots(self) -> List[BotInstance]:
        """
        Get active bots.
        
        Returns:
            List of active bots
        """
        return [bot for bot in self.bots.values() if bot.is_active()]
    
    def get_idle_bots(self) -> List[BotInstance]:
        """
        Get idle bots that can be started.
        
        Returns:
            List of idle bots
        """
        return [bot for bot in self.bots.values() if bot.can_start()]
    
    async def start_bot(self, bot_id: str) -> bool:
        """
        Start specific bot.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True if started
        """
        bot = self.get_bot(bot_id)
        
        if not bot:
            logger.error(f"Bot {bot_id[:8]} not found")
            return False
        
        if not bot.can_start():
            logger.error(f"Bot {bot_id[:8]} cannot start (status: {bot.status.value})")
            return False
        
        await bot.start()
        logger.info(f"Bot {bot_id[:8]} started")
        
        return True
    
    async def start_selected(self, bot_ids: List[str]) -> int:
        """
        Start selected bots.
        
        Args:
            bot_ids: List of bot IDs to start
        
        Returns:
            Number of bots started
        """
        started = 0
        
        for bot_id in bot_ids:
            if await self.start_bot(bot_id):
                started += 1
        
        logger.info(f"Started {started}/{len(bot_ids)} bots")
        
        return started
    
    async def start_all(self, max_count: Optional[int] = None) -> int:
        """
        Start all idle bots.
        
        Args:
            max_count: Maximum number of bots to start (None = all)
        
        Returns:
            Number of bots started
        """
        idle_bots = self.get_idle_bots()
        
        if max_count:
            idle_bots = idle_bots[:max_count]
        
        started = 0
        
        for bot in idle_bots:
            if await self.start_bot(bot.bot_id):
                started += 1
        
        logger.info(f"Started {started} bots (max: {max_count or 'unlimited'})")
        
        return started
    
    async def stop_bot(self, bot_id: str) -> bool:
        """
        Stop specific bot.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True if stopped
        """
        bot = self.get_bot(bot_id)
        
        if not bot:
            logger.error(f"Bot {bot_id[:8]} not found")
            return False
        
        await bot.stop()
        logger.info(f"Bot {bot_id[:8]} stopped")
        
        return True
    
    async def stop_all(self) -> int:
        """
        Stop all active bots.
        
        Returns:
            Number of bots stopped
        """
        active_bots = self.get_active_bots()
        
        stopped = 0
        
        for bot in active_bots:
            if await self.stop_bot(bot.bot_id):
                stopped += 1
        
        logger.info(f"Stopped {stopped} bots")
        
        return stopped
    
    async def emergency_stop(self):
        """
        Emergency stop all bots.
        
        Force-stops all bots immediately.
        """
        logger.critical("EMERGENCY STOP - Stopping all bots")
        
        # Stop all bots
        tasks = [bot.stop() for bot in self.bots.values() if bot.is_active()]
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.critical(f"Emergency stop complete: {len(tasks)} bots stopped")
    
    def remove_bot(self, bot_id: str) -> bool:
        """
        Remove bot from pool.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True if removed
        """
        bot = self.get_bot(bot_id)
        
        if not bot:
            return False
        
        # Remove mappings
        if bot.account:
            self.account_to_bot.pop(bot.account.account_id, None)
        
        self.bots.pop(bot_id, None)
        
        logger.info(f"Bot {bot_id[:8]} removed from pool")
        
        return True
    
    def get_statistics(self) -> dict:
        """
        Get aggregate statistics.
        
        Returns:
            Statistics dictionary
        """
        all_bots = self.get_all_bots()
        active_bots = self.get_active_bots()
        
        total_hands = sum(bot.stats.hands_played for bot in all_bots)
        total_profit = sum(bot.stats.net_profit() for bot in all_bots)
        total_errors = sum(bot.stats.vision_errors for bot in all_bots)
        total_actions = sum(bot.stats.actions_executed for bot in all_bots)
        total_uptime = sum(bot.stats.uptime_seconds for bot in all_bots)
        
        # Active tables (unique tables)
        active_tables = len(set(bot.current_table for bot in active_bots if bot.current_table))
        
        # HIVE teams (placeholder - would need integration)
        hive_teams = 0
        
        # Avg collective edge
        avg_collective_edge = 0.0
        if active_bots:
            avg_collective_edge = sum(bot.collective_edge for bot in active_bots) / len(active_bots)
        
        return {
            'total_bots': len(all_bots),
            'active_bots': len(active_bots),
            'idle_bots': len(self.get_idle_bots()),
            'active_tables': active_tables,
            'hive_teams': hive_teams,
            'hands_played': total_hands,
            'total_profit': total_profit,
            'vision_errors': total_errors,
            'actions_executed': total_actions,
            'uptime_seconds': total_uptime,
            'avg_collective_edge': avg_collective_edge,
            'bots_by_status': {
                status.value: len([b for b in all_bots if b.status == status])
                for status in BotStatus
            }
        }
    
    def record_vision_error(self, bot_id: str) -> bool:
        """
        Record vision error for bot.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True if bot should be stopped
        """
        if bot_id not in self.bots:
            return False
        
        # Increment error count
        if bot_id not in self._consecutive_vision_errors:
            self._consecutive_vision_errors[bot_id] = 0
        
        self._consecutive_vision_errors[bot_id] += 1
        
        error_count = self._consecutive_vision_errors[bot_id]
        
        logger.warning(
            f"Vision error for bot {bot_id[:8]}: "
            f"{error_count}/{self.max_vision_errors}"
        )
        
        # Check threshold
        if error_count >= self.max_vision_errors:
            logger.error(
                f"Bot {bot_id[:8]} exceeded max vision errors "
                f"({error_count}). Auto-stopping."
            )
            return True
        
        return False
    
    def record_vision_success(self, bot_id: str):
        """
        Record successful vision for bot (resets error count).
        
        Args:
            bot_id: Bot ID
        """
        if bot_id in self._consecutive_vision_errors:
            self._consecutive_vision_errors[bot_id] = 0
    
    async def check_and_stop_error_bots(self) -> int:
        """
        Check all bots for vision errors and stop if needed.
        
        Returns:
            Number of bots stopped
        """
        stopped_count = 0
        
        for bot_id in list(self.bots.keys()):
            if bot_id in self._consecutive_vision_errors:
                if self._consecutive_vision_errors[bot_id] >= self.max_vision_errors:
                    logger.critical(
                        f"Auto-stopping bot {bot_id[:8]} due to vision errors"
                    )
                    if await self.stop_bot(bot_id):
                        stopped_count += 1
        
        return stopped_count


# Educational example
if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("Bot Manager - Educational Research")
    print("=" * 60)
    print()
    
    # Create manager
    manager = BotManager()
    
    print(f"Bot manager created")
    print(f"  Total bots: {len(manager.get_all_bots())}")
    print()
    
    # Create test accounts
    from launcher.models.account import Account, WindowInfo, WindowType
    from launcher.models.roi_config import ROIConfig, ROIZone
    
    accounts = []
    for i in range(3):
        account = Account(nickname=f"TestBot{i+1:03d}", room="pokerstars")
        account.window_info = WindowInfo(
            window_id=f"{12345 + i}",
            window_title=f"PokerStars - Bot {i+1}",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        accounts.append(account)
    
    # Create bots
    print("Creating bots...")
    for account in accounts:
        roi_config = ROIConfig(account_id=account.account_id)
        roi_config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
        
        bot = manager.create_bot(account, roi_config)
        print(f"  Created: {bot.bot_id[:8]} for {account.nickname}")
    
    print()
    
    # Statistics
    stats = manager.get_statistics()
    print(f"Statistics:")
    print(f"  Total bots: {stats['total_bots']}")
    print(f"  Active bots: {stats['active_bots']}")
    print(f"  Idle bots: {stats['idle_bots']}")
    print()
    
    # Demonstrate start/stop (async)
    async def demo_async():
        print("Starting all bots...")
        started = await manager.start_all()
        print(f"  Started: {started} bots")
        print()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Check status
        active = manager.get_active_bots()
        print(f"Active bots: {len(active)}")
        for bot in active:
            print(f"  - {bot.account.nickname}: {bot.status.value}")
        print()
        
        # Stop all
        print("Stopping all bots...")
        stopped = await manager.stop_all()
        print(f"  Stopped: {stopped} bots")
        print()
        
        # Final stats
        stats = manager.get_statistics()
        print(f"Final statistics:")
        print(f"  Total bots: {stats['total_bots']}")
        print(f"  Active bots: {stats['active_bots']}")
    
    # Run async demo
    asyncio.run(demo_async())
    
    print("=" * 60)
    print("Bot manager demonstration complete")
    print("=" * 60)
