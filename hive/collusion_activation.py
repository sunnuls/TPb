"""
Collusion Activation System - Educational Game Theory Research (Roadmap5 Phase 2).
Extended: full_hive_month.md Этап 2 — auto-activation when 3 bots seated.

⚠️ CRITICAL ETHICAL WARNING:
    This activates COLLUSION mode for coordinated teams.
    
    This is:
    - ILLEGAL in real poker
    - STRICTLY for educational/research purposes ONLY
    - Demonstrates game theory concepts in controlled environment
    - NEVER use without explicit consent of ALL participants

Features:
- Activation after all 3 bots seated
- Safety validation
- Mode switching
- Audit logging
- **Этап 2**: auto_check_and_activate() — scan tables, auto-activate when 3 bots seated
- **Этап 2**: auto_exchange_cards() — trigger card exchange upon activation
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from hive.bot_pool import BotPool, BotStatus, HiveTeam
from hive.card_sharing import CardSharingSystem

logger = logging.getLogger(__name__)


class CollusionMode(str, Enum):
    """Collusion operational modes."""
    INACTIVE = "inactive"      # No collusion
    PENDING = "pending"        # Waiting for full team
    ACTIVE = "active"          # Full collusion active
    SUSPENDED = "suspended"    # Temporarily suspended


@dataclass
class CollusionSession:
    """
    Active collusion session.
    
    Attributes:
        team_id: HIVE team identifier
        table_id: Table identifier
        bot_ids: Bot identifiers in team
        mode: Current collusion mode
        activation_time: When collusion activated
        hands_played: Hands played with collusion
        shares_exchanged: Card shares exchanged
    
    ⚠️ EDUCATIONAL NOTE:
        Represents active coordinated cheating session for research.
    """
    team_id: str
    table_id: str
    bot_ids: List[str]
    mode: CollusionMode = CollusionMode.PENDING
    activation_time: Optional[float] = None
    hands_played: int = 0
    shares_exchanged: int = 0
    
    def activate(self) -> None:
        """Activate collusion mode."""
        self.mode = CollusionMode.ACTIVE
        self.activation_time = time.time()
        logger.critical(
            f"COLLUSION ACTIVATED: Team {self.team_id[:8]} at table {self.table_id}"
        )
    
    def suspend(self) -> None:
        """Suspend collusion mode."""
        self.mode = CollusionMode.SUSPENDED
        logger.warning(f"Collusion suspended for team {self.team_id[:8]}")
    
    def deactivate(self) -> None:
        """Deactivate collusion mode."""
        self.mode = CollusionMode.INACTIVE
        logger.info(f"Collusion deactivated for team {self.team_id[:8]}")
    
    def is_active(self) -> bool:
        """Check if collusion is active."""
        return self.mode == CollusionMode.ACTIVE
    
    def record_hand(self) -> None:
        """Record hand played."""
        self.hands_played += 1
    
    def record_share(self) -> None:
        """Record card share."""
        self.shares_exchanged += 1
    
    def get_duration(self) -> Optional[float]:
        """
        Get session duration.
        
        Returns:
            Duration in seconds, or None if not activated
        """
        if self.activation_time:
            return time.time() - self.activation_time
        return None


class CollusionActivator:
    """
    Collusion activation manager.
    
    Manages activation and coordination of collusion mode for HIVE teams.
    
    ⚠️ CRITICAL WARNING:
        This enables COORDINATED CHEATING for educational research ONLY.
        ILLEGAL in real poker. NEVER use without explicit consent.
    
    Features:
    - Automatic activation after team seated
    - Safety validation
    - Mode management
    - Statistics tracking
    """
    
    def __init__(
        self,
        bot_pool: BotPool,
        card_sharing: CardSharingSystem,
        require_confirmation: bool = True,
        auto_activate: bool = False
    ):
        """
        Initialize collusion activator.
        
        Args:
            bot_pool: Bot pool manager
            card_sharing: Card sharing system
            require_confirmation: Require manual confirmation
            auto_activate: Auto-activate after seating
        """
        self.bot_pool = bot_pool
        self.card_sharing = card_sharing
        self.require_confirmation = require_confirmation
        self.auto_activate = auto_activate
        
        # Active sessions
        self.sessions: Dict[str, CollusionSession] = {}  # team_id -> session
        
        # Statistics
        self.activations_attempted = 0
        self.activations_succeeded = 0
        self.activations_failed = 0
        
        logger.critical(
            "COLLUSION ACTIVATOR INITIALIZED - "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def check_team_ready(self, team: HiveTeam) -> bool:
        """
        Check if team is ready for collusion activation.
        
        Args:
            team: HIVE team
        
        Returns:
            True if ready
        """
        # Must be active
        if not team.active:
            return False
        
        # All bots must be seated
        for bot_id in team.bot_ids:
            bot = self.bot_pool.bots.get(bot_id)
            if not bot or not bot.current_table:
                return False
        
        return True
    
    def activate_collusion(
        self,
        team: HiveTeam,
        force: bool = False
    ) -> bool:
        """
        Activate collusion mode for team.
        
        Args:
            team: HIVE team
            force: Force activation without confirmation
        
        Returns:
            True if activated
        
        ⚠️ EDUCATIONAL NOTE:
            Activates coordinated cheating for research demonstration.
        """
        self.activations_attempted += 1
        
        # Validate team ready
        if not force and not self.check_team_ready(team):
            logger.error(f"Team {team.team_id[:8]} not ready for collusion")
            self.activations_failed += 1
            return False
        
        # Require confirmation (safety)
        if self.require_confirmation and not force:
            logger.warning(
                f"Collusion activation requires manual confirmation "
                f"for team {team.team_id[:8]}"
            )
            self.activations_failed += 1
            return False
        
        # Create session
        session = CollusionSession(
            team_id=team.team_id,
            table_id=team.table_id,
            bot_ids=team.bot_ids
        )
        
        # Activate
        session.activate()
        
        # Store
        self.sessions[team.team_id] = session
        
        self.activations_succeeded += 1
        
        logger.critical(
            f"COLLUSION MODE ACTIVE: Team {team.team_id[:8]}, "
            f"table {team.table_id}, "
            f"bots: {[b[:8] for b in team.bot_ids]}"
        )
        
        return True
    
    def deactivate_collusion(self, team_id: str) -> bool:
        """
        Deactivate collusion for team.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if deactivated
        """
        if team_id not in self.sessions:
            logger.warning(f"No active session for team {team_id}")
            return False
        
        session = self.sessions[team_id]
        session.deactivate()
        
        logger.info(
            f"Collusion deactivated: Team {team_id[:8]}, "
            f"duration: {session.get_duration():.1f}s, "
            f"hands: {session.hands_played}, "
            f"shares: {session.shares_exchanged}"
        )
        
        # Remove session
        del self.sessions[team_id]
        
        return True
    
    def suspend_collusion(self, team_id: str) -> bool:
        """
        Temporarily suspend collusion.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if suspended
        """
        if team_id not in self.sessions:
            return False
        
        self.sessions[team_id].suspend()
        return True
    
    def resume_collusion(self, team_id: str) -> bool:
        """
        Resume suspended collusion.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if resumed
        """
        if team_id not in self.sessions:
            return False
        
        session = self.sessions[team_id]
        if session.mode == CollusionMode.SUSPENDED:
            session.mode = CollusionMode.ACTIVE
            logger.info(f"Collusion resumed for team {team_id[:8]}")
            return True
        
        return False
    
    def is_collusion_active(self, team_id: str) -> bool:
        """
        Check if collusion is active for team.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if active
        """
        session = self.sessions.get(team_id)
        return session.is_active() if session else False
    
    def record_hand_played(self, team_id: str) -> None:
        """
        Record hand played with collusion.
        
        Args:
            team_id: Team identifier
        """
        if team_id in self.sessions:
            self.sessions[team_id].record_hand()
    
    def record_card_share(self, team_id: str) -> None:
        """
        Record card share.
        
        Args:
            team_id: Team identifier
        """
        if team_id in self.sessions:
            self.sessions[team_id].record_share()
    
    def get_active_sessions(self) -> List[CollusionSession]:
        """
        Get all active sessions.
        
        Returns:
            List of active sessions
        """
        return [
            session for session in self.sessions.values()
            if session.is_active()
        ]
    
    def get_statistics(self) -> dict:
        """
        Get activation statistics.
        
        Returns:
            Statistics dictionary
        """
        active_count = len(self.get_active_sessions())
        
        total_hands = sum(s.hands_played for s in self.sessions.values())
        total_shares = sum(s.shares_exchanged for s in self.sessions.values())
        
        success_rate = 0.0
        if self.activations_attempted > 0:
            success_rate = (
                self.activations_succeeded / self.activations_attempted * 100
            )
        
        return {
            'activations_attempted': self.activations_attempted,
            'activations_succeeded': self.activations_succeeded,
            'activations_failed': self.activations_failed,
            'success_rate': success_rate,
            'active_sessions': active_count,
            'total_sessions': len(self.sessions),
            'total_hands_played': total_hands,
            'total_shares_exchanged': total_shares,
            'require_confirmation': self.require_confirmation,
            'auto_activate': self.auto_activate,
            'auto_activations': getattr(self, '_auto_activations', 0),
        }

    # ------------------------------------------------------------------
    # full_hive_month.md Этап 2: auto-activation when 3 bots seated
    # ------------------------------------------------------------------

    def auto_check_and_activate(self) -> List[CollusionSession]:
        """Scan all teams and auto-activate collusion when 3 bots are seated.

        Iterates through every team in the bot pool. For each active team
        that has all 3 bots seated at the same table and has no existing
        session, auto-activates collusion.

        Returns:
            List of newly activated :class:`CollusionSession` objects.
        """
        if not hasattr(self, '_auto_activations'):
            self._auto_activations = 0

        newly_activated: List[CollusionSession] = []

        for team in self.bot_pool.teams.values():
            if not team.active:
                continue

            # Skip if session already exists
            if team.team_id in self.sessions:
                continue

            # Check all 3 bots seated at the same table
            if not self._all_bots_seated(team):
                continue

            # Force-activate (bypass confirmation for auto mode)
            ok = self.activate_collusion(team, force=True)
            if ok:
                self._auto_activations += 1
                session = self.sessions.get(team.team_id)
                if session:
                    newly_activated.append(session)
                    logger.critical(
                        "AUTO-ACTIVATED collusion for team %s at table %s",
                        team.team_id[:8], team.table_id,
                    )

        return newly_activated

    def _all_bots_seated(self, team: "HiveTeam") -> bool:
        """Check if all bots in a team are seated at the team's table."""
        for bot_id in team.bot_ids:
            bot = self.bot_pool.bots.get(bot_id)
            if not bot:
                return False
            if bot.current_table != team.table_id:
                return False
            if bot.status not in (BotStatus.SEATED, BotStatus.PLAYING):
                return False
        return True

    def auto_exchange_cards(
        self,
        team_id: str,
        card_map: Dict[str, List[str]],
        *,
        hand_id: str = "",
    ) -> bool:
        """Trigger full card exchange for an active collusion session.

        Args:
            team_id:  Team identifier.
            card_map: Mapping ``bot_id → [card1, card2]``.
            hand_id:  Optional hand identifier.

        Returns:
            True if all shares were received and exchange is complete.
        """
        session = self.sessions.get(team_id)
        if not session or not session.is_active():
            logger.warning("auto_exchange_cards: no active session for %s", team_id)
            return False

        table_id = session.table_id
        shares_ok = 0

        for bot_id, hole_cards in card_map.items():
            if bot_id not in session.bot_ids:
                logger.warning("Bot %s not in team %s — skipping", bot_id, team_id)
                continue

            share = self.card_sharing.create_share(
                bot_id=bot_id,
                team_id=team_id,
                table_id=table_id,
                hole_cards=hole_cards,
                hand_id=hand_id,
            )
            self.card_sharing.receive_share(share)
            session.record_share()
            shares_ok += 1

        # Check completeness
        knowledge = self.card_sharing.get_team_knowledge(
            team_id, table_id, hand_id,
        )
        complete = knowledge.is_complete(expected_bots=len(session.bot_ids)) if knowledge else False

        if complete:
            logger.info(
                "Full exchange complete for team %s: %d cards known",
                team_id[:8], len(knowledge.known_cards),
            )

        return complete


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Collusion Activation - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates COLLUSION activation for RESEARCH ONLY.")
    print("ILLEGAL in real poker. NEVER use without explicit consent.")
    print()
    
    from hive.bot_pool import BotPool
    from hive.card_sharing import CardSharingSystem
    
    # Create components
    bot_pool = BotPool(group_hash="research", pool_size=10)
    card_sharing = CardSharingSystem()
    
    activator = CollusionActivator(
        bot_pool=bot_pool,
        card_sharing=card_sharing,
        require_confirmation=False,  # For demo
        auto_activate=True
    )
    
    print("Collusion activator initialized")
    print()
    
    # Form team
    team = bot_pool.form_team(table_id="research_table_1")
    
    if team:
        print(f"Team formed: {team.team_id[:8]}")
        print(f"  Bots: {[b[:8] for b in team.bot_ids]}")
        print()
        
        # Check ready
        ready = activator.check_team_ready(team)
        print(f"Team ready for collusion: {ready}")
        print()
        
        # Activate collusion
        if ready:
            activated = activator.activate_collusion(team, force=True)
            
            if activated:
                print(f"COLLUSION ACTIVATED for team {team.team_id[:8]}")
                print()
                
                # Check status
                active = activator.is_collusion_active(team.team_id)
                print(f"Collusion active: {active}")
                print()
    
    # Statistics
    stats = activator.get_statistics()
    print("Activation statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
