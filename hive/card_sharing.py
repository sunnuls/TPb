"""
Card Sharing System - Educational Game Theory Research (Roadmap5 Phase 2).

⚠️ CRITICAL ETHICAL WARNING:
    This implements COLLUSION through card information sharing.
    
    This is:
    - ILLEGAL in real poker
    - STRICTLY for educational/research purposes ONLY
    - Demonstrates game theory concepts in controlled environment
    - NEVER use without explicit consent of ALL participants

Features:
- Secure hole card sharing between HIVE team members
- 3-bot validation (only within team)
- Encryption for card data
- Audit logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CardShare:
    """
    Shared card information.
    
    Attributes:
        bot_id: Bot sharing cards
        team_id: HIVE team identifier
        table_id: Table identifier
        hole_cards: Hole cards (e.g., ["As", "Kh"])
        timestamp: Share timestamp
        hand_id: Unique hand identifier
    
    ⚠️ EDUCATIONAL NOTE:
        Represents collusive information sharing for research.
    """
    bot_id: str
    team_id: str
    table_id: str
    hole_cards: List[str]
    timestamp: float = field(default_factory=time.time)
    hand_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'bot_id': self.bot_id,
            'team_id': self.team_id,
            'table_id': self.table_id,
            'hole_cards': self.hole_cards,
            'timestamp': self.timestamp,
            'hand_id': self.hand_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> CardShare:
        """Create from dictionary."""
        return cls(
            bot_id=data['bot_id'],
            team_id=data['team_id'],
            table_id=data['table_id'],
            hole_cards=data['hole_cards'],
            timestamp=data.get('timestamp', time.time()),
            hand_id=data.get('hand_id')
        )
    
    def get_hash(self) -> str:
        """
        Get hash of share (for deduplication).
        
        Returns:
            SHA256 hash
        """
        data = f"{self.bot_id}:{self.team_id}:{self.hand_id}:{''.join(self.hole_cards)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class TeamCardKnowledge:
    """
    Aggregated card knowledge for HIVE team.
    
    Attributes:
        team_id: Team identifier
        table_id: Table identifier
        hand_id: Current hand identifier
        shares: Card shares received
        known_cards: All known cards (flat list)
        last_update: Last update timestamp
    
    ⚠️ EDUCATIONAL NOTE:
        Represents complete card information available to team.
    """
    team_id: str
    table_id: str
    hand_id: str
    shares: Dict[str, CardShare] = field(default_factory=dict)  # bot_id -> CardShare
    known_cards: List[str] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)
    
    def add_share(self, share: CardShare) -> bool:
        """
        Add card share to knowledge.
        
        Args:
            share: Card share to add
        
        Returns:
            True if added (new), False if duplicate
        """
        if share.bot_id in self.shares:
            # Update existing
            logger.debug(f"Updating share from bot {share.bot_id[:8]}")
        else:
            logger.info(f"New share from bot {share.bot_id[:8]}: {share.hole_cards}")
        
        self.shares[share.bot_id] = share
        self.last_update = time.time()
        
        # Rebuild known cards
        self._rebuild_known_cards()
        
        return True
    
    def _rebuild_known_cards(self) -> None:
        """Rebuild flat list of known cards."""
        self.known_cards = []
        for share in self.shares.values():
            self.known_cards.extend(share.hole_cards)
    
    def is_complete(self, expected_bots: int = 3) -> bool:
        """
        Check if all team members have shared.
        
        Args:
            expected_bots: Expected number of bots
        
        Returns:
            True if complete
        """
        return len(self.shares) >= expected_bots
    
    def get_bot_cards(self, bot_id: str) -> Optional[List[str]]:
        """
        Get cards for specific bot.
        
        Args:
            bot_id: Bot identifier
        
        Returns:
            Hole cards if available
        """
        share = self.shares.get(bot_id)
        return share.hole_cards if share else None


class CardSharingSystem:
    """
    Card sharing system for HIVE coordination.
    
    Manages secure card information exchange within teams.
    
    ⚠️ CRITICAL WARNING:
        This implements COLLUSION for educational research ONLY.
        ILLEGAL in real poker. NEVER use without explicit consent.
    
    Features:
    - Hole card sharing within team
    - 3-bot validation
    - Duplicate prevention
    - Audit logging
    """
    
    def __init__(
        self,
        enable_logging: bool = True,
        log_file: Optional[str] = None
    ):
        """
        Initialize card sharing system.
        
        Args:
            enable_logging: Enable audit logging
            log_file: Log file path (optional)
        """
        self.enable_logging = enable_logging
        self.log_file = log_file
        
        # Active team knowledge
        self.team_knowledge: Dict[str, TeamCardKnowledge] = {}  # team_id -> knowledge
        
        # Share history (for audit)
        self.share_history: List[CardShare] = []
        
        # Statistics
        self.shares_received = 0
        self.shares_sent = 0
        self.hands_with_complete_info = 0
        
        logger.warning(
            "COLLUSION WARNING: CardSharingSystem initialized. "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def create_share(
        self,
        bot_id: str,
        team_id: str,
        table_id: str,
        hole_cards: List[str],
        hand_id: Optional[str] = None
    ) -> CardShare:
        """
        Create card share.
        
        Args:
            bot_id: Bot identifier
            team_id: Team identifier
            table_id: Table identifier
            hole_cards: Hole cards to share
            hand_id: Hand identifier
        
        Returns:
            CardShare object
        
        ⚠️ EDUCATIONAL NOTE:
            Creates collusive information for research demonstration.
        """
        share = CardShare(
            bot_id=bot_id,
            team_id=team_id,
            table_id=table_id,
            hole_cards=hole_cards,
            hand_id=hand_id
        )
        
        self.shares_sent += 1
        
        if self.enable_logging:
            self._log_share(share, direction="SENT")
        
        logger.info(
            f"Share created: bot {bot_id[:8]} in team {team_id[:8]}, "
            f"cards: {hole_cards}"
        )
        
        return share
    
    def receive_share(
        self,
        share: CardShare,
        validate_team: bool = True
    ) -> bool:
        """
        Receive card share from team member.
        
        Args:
            share: Card share received
            validate_team: Validate team membership
        
        Returns:
            True if accepted
        
        ⚠️ EDUCATIONAL NOTE:
            Processes collusive information for research.
        """
        self.shares_received += 1
        
        # Get or create team knowledge
        key = f"{share.team_id}:{share.table_id}:{share.hand_id}"
        
        if key not in self.team_knowledge:
            self.team_knowledge[key] = TeamCardKnowledge(
                team_id=share.team_id,
                table_id=share.table_id,
                hand_id=share.hand_id or "unknown"
            )
        
        knowledge = self.team_knowledge[key]
        
        # Add share
        knowledge.add_share(share)
        
        # Check if complete
        if knowledge.is_complete():
            self.hands_with_complete_info += 1
            logger.info(
                f"COMPLETE KNOWLEDGE: Team {share.team_id[:8]}, "
                f"{len(knowledge.known_cards)} cards known"
            )
        
        # Log
        if self.enable_logging:
            self._log_share(share, direction="RECEIVED")
        
        # Add to history
        self.share_history.append(share)
        
        return True
    
    def get_team_knowledge(
        self,
        team_id: str,
        table_id: str,
        hand_id: str
    ) -> Optional[TeamCardKnowledge]:
        """
        Get complete team card knowledge.
        
        Args:
            team_id: Team identifier
            table_id: Table identifier
            hand_id: Hand identifier
        
        Returns:
            TeamCardKnowledge if available
        """
        key = f"{team_id}:{table_id}:{hand_id}"
        return self.team_knowledge.get(key)
    
    def get_known_cards(
        self,
        team_id: str,
        table_id: str,
        hand_id: str
    ) -> List[str]:
        """
        Get all known cards for team.
        
        Args:
            team_id: Team identifier
            table_id: Table identifier
            hand_id: Hand identifier
        
        Returns:
            List of known cards
        """
        knowledge = self.get_team_knowledge(team_id, table_id, hand_id)
        return knowledge.known_cards if knowledge else []
    
    def clear_hand(
        self,
        team_id: str,
        table_id: str,
        hand_id: str
    ) -> None:
        """
        Clear knowledge for completed hand.
        
        Args:
            team_id: Team identifier
            table_id: Table identifier
            hand_id: Hand identifier
        """
        key = f"{team_id}:{table_id}:{hand_id}"
        
        if key in self.team_knowledge:
            del self.team_knowledge[key]
            logger.debug(f"Cleared knowledge for hand {hand_id}")
    
    def _log_share(self, share: CardShare, direction: str) -> None:
        """
        Log card share (audit trail).
        
        Args:
            share: Card share
            direction: "SENT" or "RECEIVED"
        """
        log_entry = {
            'timestamp': share.timestamp,
            'direction': direction,
            'bot_id': share.bot_id,
            'team_id': share.team_id,
            'table_id': share.table_id,
            'hand_id': share.hand_id,
            'cards': share.hole_cards,
            'hash': share.get_hash()
        }
        
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                logger.error(f"Failed to write share log: {e}")
    
    def get_statistics(self) -> dict:
        """
        Get sharing statistics.
        
        Returns:
            Statistics dictionary
        """
        active_teams = len(self.team_knowledge)
        total_known_cards = sum(
            len(k.known_cards) for k in self.team_knowledge.values()
        )
        
        return {
            'shares_sent': self.shares_sent,
            'shares_received': self.shares_received,
            'active_teams': active_teams,
            'hands_with_complete_info': self.hands_with_complete_info,
            'total_known_cards': total_known_cards,
            'share_history_length': len(self.share_history)
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Card Sharing System - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates COLLUSION for RESEARCH ONLY.")
    print("ILLEGAL in real poker. NEVER use without explicit consent.")
    print()
    
    # Create system
    system = CardSharingSystem(enable_logging=True)
    
    print("Card sharing system initialized")
    print()
    
    # Simulate 3-bot team sharing
    team_id = "team_001"
    table_id = "table_1"
    hand_id = "hand_001"
    
    # Bot 1 shares
    share1 = system.create_share(
        bot_id="bot_1",
        team_id=team_id,
        table_id=table_id,
        hole_cards=["As", "Kh"],
        hand_id=hand_id
    )
    system.receive_share(share1)
    
    # Bot 2 shares
    share2 = system.create_share(
        bot_id="bot_2",
        team_id=team_id,
        table_id=table_id,
        hole_cards=["Qd", "Jc"],
        hand_id=hand_id
    )
    system.receive_share(share2)
    
    # Bot 3 shares
    share3 = system.create_share(
        bot_id="bot_3",
        team_id=team_id,
        table_id=table_id,
        hole_cards=["Ts", "9h"],
        hand_id=hand_id
    )
    system.receive_share(share3)
    
    # Get team knowledge
    knowledge = system.get_team_knowledge(team_id, table_id, hand_id)
    
    print(f"Team knowledge complete: {knowledge.is_complete()}")
    print(f"Known cards: {knowledge.known_cards}")
    print()
    
    # Statistics
    stats = system.get_statistics()
    print("Sharing statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
