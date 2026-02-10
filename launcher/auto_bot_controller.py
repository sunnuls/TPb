"""
Automatic Bot Controller - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Automatic bot startup
- Auto-navigation to game mode
- Table finding and joining
- Multi-bot coordination (3vs1 collusion)
"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading

from launcher.models.account import Account
from launcher.models.game_settings import GamePreferences, GameType
from launcher.vision import AutoNavigator, AutoUIDetector, NavigationResult

logger = logging.getLogger(__name__)


class BotState(Enum):
    """Bot operational state."""
    IDLE = "idle"
    NAVIGATING = "navigating"
    SEARCHING_TABLE = "searching_table"
    JOINING = "joining"
    SEATED = "seated"
    PLAYING = "playing"
    ERROR = "error"


@dataclass
class BotSession:
    """
    Active bot session.
    
    Attributes:
        account: Associated account
        state: Current state
        table_id: Current table ID (if seated)
        seat_number: Seat number (if seated)
        stack: Current stack
        session_start: Session start time
    """
    account: Account
    state: BotState = BotState.IDLE
    table_id: Optional[str] = None
    seat_number: Optional[int] = None
    stack: float = 0.0
    session_start: float = 0.0
    
    def get_uptime(self) -> float:
        """Get session uptime in seconds."""
        if self.session_start == 0:
            return 0
        return time.time() - self.session_start


class AutoBotController:
    """
    Automatic bot controller.
    
    ⚠️ EDUCATIONAL NOTE:
        Coordinates multiple bots for collusion strategy.
    """
    
    def __init__(self):
        """Initialize controller."""
        self.sessions: Dict[str, BotSession] = {}  # account_id -> session
        self.navigator = AutoNavigator()
        self.detector = AutoUIDetector()
        
        self.running = False
        self.collusion_groups: List[List[str]] = []  # Groups of 3 bot IDs
        
        logger.info("AutoBotController initialized")
    
    def start_bot(self, account: Account) -> bool:
        """
        Start bot for account.
        
        Args:
            account: Account to start bot for
        
        Returns:
            True if started successfully
        """
        if account.account_id in self.sessions:
            logger.warning(f"Bot already running for {account.nickname}")
            return False
        
        if not account.game_preferences:
            logger.error(f"No game preferences for {account.nickname}")
            return False
        
        logger.info(f"Starting bot for {account.nickname}")
        
        # Create session
        session = BotSession(
            account=account,
            state=BotState.IDLE,
            session_start=time.time()
        )
        
        self.sessions[account.account_id] = session
        
        # Start bot thread
        thread = threading.Thread(
            target=self._bot_main_loop,
            args=(session,),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Bot started for {account.nickname}")
        return True
    
    def stop_bot(self, account_id: str) -> bool:
        """
        Stop bot.
        
        Args:
            account_id: Account ID
        
        Returns:
            True if stopped
        """
        if account_id not in self.sessions:
            return False
        
        session = self.sessions[account_id]
        logger.info(f"Stopping bot for {session.account.nickname}")
        
        session.state = BotState.IDLE
        del self.sessions[account_id]
        
        return True
    
    def _bot_main_loop(self, session: BotSession):
        """
        Main bot loop.
        
        Args:
            session: Bot session
        """
        account = session.account
        prefs = account.game_preferences
        
        logger.info(f"[{account.nickname}] Bot main loop started")
        
        try:
            # Step 1: Navigate to game mode
            session.state = BotState.NAVIGATING
            success = self._navigate_to_mode(session)
            
            if not success:
                logger.error(f"[{account.nickname}] Navigation failed")
                session.state = BotState.ERROR
                return
            
            # Step 2: Find and join table
            session.state = BotState.SEARCHING_TABLE
            table_found = self._find_and_join_table(session)
            
            if not table_found:
                logger.warning(f"[{account.nickname}] No suitable table found")
                session.state = BotState.ERROR
                return
            
            # Step 3: Play
            session.state = BotState.PLAYING
            self._play_loop(session)
        
        except Exception as e:
            logger.error(f"[{account.nickname}] Bot error: {e}", exc_info=True)
            session.state = BotState.ERROR
        
        finally:
            logger.info(f"[{account.nickname}] Bot main loop ended")
    
    def _navigate_to_mode(self, session: BotSession) -> bool:
        """
        Navigate to game mode.
        
        Args:
            session: Bot session
        
        Returns:
            True if successful
        """
        account = session.account
        prefs = account.game_preferences
        
        # Get first enabled game
        if not prefs.enabled_games:
            logger.error(f"[{account.nickname}] No enabled games")
            return False
        
        game_mode = prefs.enabled_games[0].value
        logger.info(f"[{account.nickname}] Navigating to {game_mode}")
        
        # Get window handle (prefer HWND for direct capture)
        hwnd = account.window_info.hwnd
        window_bbox = None
        
        if not hwnd:
            logger.warning(f"[{account.nickname}] HWND not available, using screen region capture")
            x, y, w, h = account.window_info.position
            window_bbox = (x, y, w, h)
        
        # Navigate
        result = self.navigator.navigate_to_game_mode(
            game_mode,
            hwnd=hwnd,
            window_bbox=window_bbox,
            wait_after_click=3.0
        )
        
        success = (result == NavigationResult.SUCCESS)
        
        if success:
            logger.info(f"[{account.nickname}] Navigation successful")
        else:
            logger.error(f"[{account.nickname}] Navigation failed: {result.value}")
        
        return success
    
    def _find_and_join_table(self, session: BotSession) -> bool:
        """
        Find and join suitable table.
        
        Args:
            session: Bot session
        
        Returns:
            True if joined
        """
        account = session.account
        prefs = account.game_preferences
        
        logger.info(f"[{account.nickname}] Searching for table")
        logger.info(f"  Stakes: {prefs.min_stake} - {prefs.max_stake}")
        logger.info(f"  Players: {prefs.min_players}-{prefs.max_players}")
        
        # Get window bounds
        x, y, w, h = account.window_info.position
        
        # Define scroll area (adjust based on actual UI)
        scroll_bbox = (x + 50, y + 150, w - 100, h - 200)
        
        # Find table
        table = self.navigator.find_and_scroll_to_table(
            stake_filter=prefs.min_stake,
            min_players=prefs.min_players,
            max_players=prefs.max_players,
            scroll_area_bbox=scroll_bbox,
            max_scrolls=15
        )
        
        if not table:
            logger.warning(f"[{account.nickname}] No suitable table found")
            return False
        
        logger.info(f"[{account.nickname}] Found table: {table.text}")
        
        # Join table
        session.state = BotState.JOINING
        result = self.navigator.join_table(table)
        
        if result == NavigationResult.SUCCESS:
            session.state = BotState.SEATED
            session.table_id = table.text  # Store table identifier
            logger.info(f"[{account.nickname}] Joined table successfully")
            return True
        else:
            logger.error(f"[{account.nickname}] Failed to join table")
            return False
    
    def _play_loop(self, session: BotSession):
        """
        Main play loop.
        
        Args:
            session: Bot session
        """
        account = session.account
        logger.info(f"[{account.nickname}] Play loop started")
        
        # TODO: Implement actual play logic
        # This will integrate with existing poker bot logic
        
        while session.state == BotState.PLAYING:
            # Check if still seated
            # Process game state
            # Make decisions
            # Execute actions
            
            time.sleep(1.0)
    
    def start_collusion_group(self, accounts: List[Account]) -> bool:
        """
        Start collusion group (3 bots on same table).
        
        Args:
            accounts: List of 3 accounts for collusion
        
        Returns:
            True if started successfully
        """
        if len(accounts) != 3:
            logger.error("Collusion requires exactly 3 accounts")
            return False
        
        logger.info("=" * 60)
        logger.info("STARTING COLLUSION GROUP")
        logger.info(f"Bots: {[a.nickname for a in accounts]}")
        logger.info("=" * 60)
        
        # Verify all accounts have preferences
        for account in accounts:
            if not account.game_preferences:
                logger.error(f"Account {account.nickname} missing game preferences")
                return False
        
        # Start bots sequentially with delays
        group_ids = []
        
        for i, account in enumerate(accounts):
            logger.info(f"Starting bot {i+1}/3: {account.nickname}")
            
            success = self.start_bot(account)
            if not success:
                logger.error(f"Failed to start bot for {account.nickname}")
                return False
            
            group_ids.append(account.account_id)
            
            # Wait before starting next bot
            if i < 2:
                logger.info(f"Waiting 5 seconds before starting next bot...")
                time.sleep(5.0)
        
        # Register collusion group
        self.collusion_groups.append(group_ids)
        
        logger.info("=" * 60)
        logger.info("COLLUSION GROUP STARTED SUCCESSFULLY")
        logger.info("All 3 bots are now searching for suitable table")
        logger.info("=" * 60)
        
        return True
    
    def get_session_status(self, account_id: str) -> Optional[Dict]:
        """
        Get session status.
        
        Args:
            account_id: Account ID
        
        Returns:
            Status dictionary or None
        """
        if account_id not in self.sessions:
            return None
        
        session = self.sessions[account_id]
        
        return {
            'account_id': account_id,
            'nickname': session.account.nickname,
            'state': session.state.value,
            'table_id': session.table_id,
            'seat_number': session.seat_number,
            'stack': session.stack,
            'uptime': session.get_uptime()
        }
    
    def get_all_sessions(self) -> List[Dict]:
        """
        Get all active sessions.
        
        Returns:
            List of session status dictionaries
        """
        return [
            self.get_session_status(account_id)
            for account_id in self.sessions.keys()
        ]
    
    def stop_all(self):
        """Stop all bots."""
        logger.info("Stopping all bots...")
        
        account_ids = list(self.sessions.keys())
        for account_id in account_ids:
            self.stop_bot(account_id)
        
        self.collusion_groups.clear()
        logger.info("All bots stopped")


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Auto Bot Controller - Educational Research")
    print("=" * 60)
    print()
    
    controller = AutoBotController()
    
    print(f"Controller initialized")
    print(f"Active sessions: {len(controller.sessions)}")
    print()
    
    print("This controller manages:")
    print("  - Automatic bot startup")
    print("  - Navigation to game modes")
    print("  - Table finding and joining")
    print("  - Multi-bot coordination (3vs1)")
    print()
    
    print("=" * 60)
