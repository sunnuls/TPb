"""
Bot Pool Management - Educational Game Theory Research.

⚠️ ETHICAL WARNING:
    This implements coordinated multi-agent systems for RESEARCH ONLY.
    Demonstrates game theory concepts in controlled environments.
    NEVER use without explicit participant consent.

Manages pool of coordinating agents:
- Bot lifecycle (idle, scanning, seated, playing)
- Task assignment (table joining)
- HIVE group formation (3-bot teams)
- Performance tracking
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class BotStatus(str, Enum):
    """Bot operational status."""
    IDLE = "idle"
    SCANNING = "scanning"
    JOINING = "joining"
    SEATED = "seated"
    PLAYING = "playing"
    DISCONNECTED = "disconnected"


@dataclass
class BotInstance:
    """
    Individual bot instance.
    
    Attributes:
        bot_id: Unique bot identifier
        group_hash: HIVE group identifier
        status: Current operational status
        current_table: Table ID if seated
        hands_played: Total hands played
        session_start: Session start timestamp
        last_active: Last activity timestamp
    """
    bot_id: str
    group_hash: str
    status: BotStatus = BotStatus.IDLE
    current_table: Optional[str] = None
    hands_played: int = 0
    session_start: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    def update_status(self, new_status: BotStatus) -> None:
        """
        Update bot status.
        
        Args:
            new_status: New status
        """
        self.status = new_status
        self.last_active = time.time()
        logger.debug(f"Bot {self.bot_id[:8]} status: {new_status.value}")
    
    def assign_table(self, table_id: str) -> None:
        """
        Assign bot to table.
        
        Args:
            table_id: Table identifier
        """
        self.current_table = table_id
        self.update_status(BotStatus.SEATED)
    
    def leave_table(self) -> None:
        """Leave current table and return to idle."""
        if self.current_table:
            logger.info(f"Bot {self.bot_id[:8]} leaving table {self.current_table}")
        
        self.current_table = None
        self.update_status(BotStatus.IDLE)
    
    def record_hand(self) -> None:
        """Record hand played."""
        self.hands_played += 1
        self.last_active = time.time()
    
    def get_session_duration(self) -> float:
        """
        Get session duration.
        
        Returns:
            Duration in seconds
        """
        return time.time() - self.session_start
    
    def is_active(self, timeout: float = 300.0) -> bool:
        """
        Check if bot is active.
        
        Args:
            timeout: Activity timeout in seconds
        
        Returns:
            True if active within timeout
        """
        return (time.time() - self.last_active) < timeout


@dataclass
class HiveTeam:
    """
    3-bot HIVE team.
    
    Attributes:
        team_id: Unique team identifier
        bot_ids: List of 3 bot IDs
        table_id: Assigned table
        formation_time: Team formation timestamp
        active: Whether team is active
    
    EDUCATIONAL NOTE:
        Represents coordinated agent group for game theory research.
    """
    team_id: str
    bot_ids: List[str]
    table_id: str
    formation_time: float = field(default_factory=time.time)
    active: bool = True
    
    def __post_init__(self):
        """Validate team size."""
        if len(self.bot_ids) != 3:
            raise ValueError(f"HIVE team requires exactly 3 bots, got {len(self.bot_ids)}")
    
    def contains_bot(self, bot_id: str) -> bool:
        """Check if bot is in team."""
        return bot_id in self.bot_ids
    
    def deactivate(self) -> None:
        """Deactivate team."""
        self.active = False
        logger.info(f"Team {self.team_id[:8]} deactivated")


class BotPool:
    """
    Bot pool manager.
    
    Manages pool of coordinating bots for educational research.
    
    Features:
    - Bot lifecycle management
    - HIVE team formation (3-bot groups)
    - Task assignment
    - Performance tracking
    
    ⚠️ EDUCATIONAL USE ONLY:
        This demonstrates multi-agent coordination concepts.
        NOT for use in real games.
    """
    
    def __init__(
        self,
        group_hash: str,
        pool_size: int = 100,
        max_teams: int = 30
    ):
        """
        Initialize bot pool.
        
        Args:
            group_hash: HIVE group identifier
            pool_size: Total bots in pool
            max_teams: Maximum simultaneous teams
        """
        self.group_hash = group_hash
        self.pool_size = pool_size
        self.max_teams = max_teams
        
        # Bot instances
        self.bots: Dict[str, BotInstance] = {}
        
        # Active teams
        self.teams: Dict[str, HiveTeam] = {}
        
        # Table assignments
        self.table_assignments: Dict[str, Set[str]] = {}  # table_id -> bot_ids
        
        # Initialize pool
        self._initialize_pool()
        
        logger.info(
            f"BotPool initialized: {pool_size} bots, "
            f"max {max_teams} teams"
        )
    
    def _initialize_pool(self) -> None:
        """Initialize bot instances."""
        for i in range(self.pool_size):
            bot_id = f"bot_{uuid4()}"
            self.bots[bot_id] = BotInstance(
                bot_id=bot_id,
                group_hash=self.group_hash
            )
    
    def get_idle_bots(self, count: int = 3) -> List[str]:
        """
        Get idle bots for task assignment.
        
        Args:
            count: Number of bots needed
        
        Returns:
            List of bot IDs (up to count)
        """
        idle_bots = [
            bot_id for bot_id, bot in self.bots.items()
            if bot.status == BotStatus.IDLE and bot.is_active()
        ]
        
        return idle_bots[:count]
    
    def form_team(
        self,
        table_id: str,
        bot_ids: Optional[List[str]] = None
    ) -> Optional[HiveTeam]:
        """
        Form 3-bot HIVE team for table.
        
        Args:
            table_id: Target table ID
            bot_ids: Specific bot IDs (or auto-select)
        
        Returns:
            HiveTeam if successful, None otherwise
        
        EDUCATIONAL NOTE:
            Creates coordinated agent group for research demonstration.
        """
        # Check team limit
        active_teams = [t for t in self.teams.values() if t.active]
        if len(active_teams) >= self.max_teams:
            logger.warning(f"Max teams ({self.max_teams}) reached")
            return None
        
        # Get bots
        if bot_ids is None:
            bot_ids = self.get_idle_bots(count=3)
        
        if len(bot_ids) != 3:
            logger.error(f"Cannot form team: need 3 bots, got {len(bot_ids)}")
            return None
        
        # Verify bots are available
        for bot_id in bot_ids:
            if bot_id not in self.bots:
                logger.error(f"Bot {bot_id} not in pool")
                return None
            
            if self.bots[bot_id].status != BotStatus.IDLE:
                logger.error(f"Bot {bot_id} not idle: {self.bots[bot_id].status}")
                return None
        
        # Create team
        team_id = f"team_{uuid4()}"
        team = HiveTeam(
            team_id=team_id,
            bot_ids=bot_ids,
            table_id=table_id
        )
        
        self.teams[team_id] = team
        
        # Assign bots to table
        for bot_id in bot_ids:
            self.bots[bot_id].assign_table(table_id)
        
        # Track table assignment
        if table_id not in self.table_assignments:
            self.table_assignments[table_id] = set()
        
        self.table_assignments[table_id].update(bot_ids)
        
        logger.info(
            f"Team {team_id[:8]} formed for table {table_id}: "
            f"bots {[b[:8] for b in bot_ids]}"
        )
        
        return team
    
    def disband_team(self, team_id: str) -> bool:
        """
        Disband team and return bots to idle.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if successful
        """
        if team_id not in self.teams:
            logger.warning(f"Team {team_id} not found")
            return False
        
        team = self.teams[team_id]
        
        # Return bots to idle
        for bot_id in team.bot_ids:
            if bot_id in self.bots:
                self.bots[bot_id].leave_table()
        
        # Remove table assignment
        if team.table_id in self.table_assignments:
            for bot_id in team.bot_ids:
                self.table_assignments[team.table_id].discard(bot_id)
            if not self.table_assignments[team.table_id]:
                del self.table_assignments[team.table_id]
        
        # Deactivate team
        team.deactivate()
        
        logger.info(f"Team {team_id[:8]} disbanded")
        
        return True
    
    def get_team_at_table(self, table_id: str) -> Optional[HiveTeam]:
        """
        Get active team at table.
        
        Args:
            table_id: Table identifier
        
        Returns:
            HiveTeam if found
        """
        for team in self.teams.values():
            if team.active and team.table_id == table_id:
                return team
        
        return None
    
    def get_bot_status(self, bot_id: str) -> Optional[BotStatus]:
        """
        Get bot status.
        
        Args:
            bot_id: Bot identifier
        
        Returns:
            BotStatus if found
        """
        if bot_id in self.bots:
            return self.bots[bot_id].status
        
        return None
    
    def record_hand_played(self, bot_id: str) -> None:
        """
        Record hand played by bot.
        
        Args:
            bot_id: Bot identifier
        """
        if bot_id in self.bots:
            self.bots[bot_id].record_hand()
    
    def get_statistics(self) -> dict:
        """
        Get pool statistics.
        
        Returns:
            Statistics dictionary
        """
        status_counts = {}
        for status in BotStatus:
            status_counts[status.value] = sum(
                1 for bot in self.bots.values()
                if bot.status == status
            )
        
        active_teams = [t for t in self.teams.values() if t.active]
        
        total_hands = sum(bot.hands_played for bot in self.bots.values())
        
        return {
            'pool_size': self.pool_size,
            'status_distribution': status_counts,
            'active_teams': len(active_teams),
            'max_teams': self.max_teams,
            'tables_occupied': len(self.table_assignments),
            'total_hands_played': total_hands,
            'teams_formed': len(self.teams)
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Bot Pool Manager - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates multi-agent coordination for RESEARCH ONLY.")
    print("NEVER use in real games without explicit consent.")
    print()
    
    # Create pool
    pool = BotPool(
        group_hash="research_group_001",
        pool_size=10,
        max_teams=3
    )
    
    print("Bot pool initialized:")
    print(f"  Pool size: {pool.pool_size}")
    print(f"  Max teams: {pool.max_teams}")
    print()
    
    # Form team
    team = pool.form_team(table_id="research_table_1")
    
    if team:
        print(f"Team formed: {team.team_id[:8]}")
        print(f"  Bots: {[b[:8] for b in team.bot_ids]}")
        print(f"  Table: {team.table_id}")
        print()
    
    # Statistics
    stats = pool.get_statistics()
    print("Pool statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
