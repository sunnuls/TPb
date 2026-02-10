"""
Bot Identification Module (Roadmap3 Phase 4.2).

Enables multiple bot instances to identify each other at the same table
using shared secret + position hash mechanism.

Key Features:
- Shared secret validation (3 instances share same secret)
- Position-based hashing (unique ID per seat)
- Table instance detection (know when at same table)
- Collision-resistant identification

EDUCATIONAL USE ONLY: For HCI research prototype studying multi-agent coordination.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BotIdentity:
    """
    Identity information for a bot instance.
    
    Attributes:
        bot_id: Unique bot identifier (UUID)
        shared_secret: Shared secret for group identification
        table_id: Current table identifier
        position: Seat position at table (0-5 for 6-max)
        instance_hash: Unique hash for this bot instance
        group_hash: Hash identifying the HIVE group
    """
    bot_id: str
    shared_secret: str
    table_id: str = ""
    position: int = -1
    instance_hash: str = ""
    group_hash: str = ""
    
    def __post_init__(self):
        """Calculate hashes if not provided."""
        if not self.instance_hash and self.table_id and self.position >= 0:
            self.instance_hash = calculate_instance_hash(
                self.bot_id,
                self.table_id,
                self.position,
                self.shared_secret
            )
        
        if not self.group_hash and self.shared_secret:
            self.group_hash = calculate_group_hash(self.shared_secret)


def generate_shared_secret(length: int = 32) -> str:
    """
    Generate a new shared secret for HIVE group.
    
    Args:
        length: Length of secret in bytes
    
    Returns:
        Hex-encoded shared secret
    
    EDUCATIONAL NOTE:
        All 3 bot instances in a HIVE group must use the same shared secret.
        This secret is used for group identification and coordination.
    """
    return secrets.token_hex(length)


def calculate_group_hash(shared_secret: str) -> str:
    """
    Calculate group hash from shared secret.
    
    Args:
        shared_secret: Shared secret for the group
    
    Returns:
        SHA256 hash of the shared secret
    
    EDUCATIONAL NOTE:
        Group hash identifies all bots in the same HIVE group.
        Bots with matching group hashes belong to same coordination group.
    """
    hasher = hashlib.sha256()
    hasher.update(shared_secret.encode('utf-8'))
    return hasher.hexdigest()[:16]  # First 16 chars for brevity


def calculate_instance_hash(
    bot_id: str,
    table_id: str,
    position: int,
    shared_secret: str
) -> str:
    """
    Calculate unique instance hash for a bot at specific table position.
    
    Args:
        bot_id: Unique bot identifier
        table_id: Table identifier
        position: Seat position (0-5)
        shared_secret: Shared secret for verification
    
    Returns:
        SHA256 hash uniquely identifying this instance
    
    EDUCATIONAL NOTE:
        Instance hash = H(bot_id || table_id || position || shared_secret)
        This ensures each bot at a specific seat has unique identifier,
        while still being verifiable by other bots with same shared_secret.
    """
    hasher = hashlib.sha256()
    hasher.update(bot_id.encode('utf-8'))
    hasher.update(table_id.encode('utf-8'))
    hasher.update(str(position).encode('utf-8'))
    hasher.update(shared_secret.encode('utf-8'))
    return hasher.hexdigest()[:16]  # First 16 chars for brevity


def verify_group_membership(
    identity1: BotIdentity,
    identity2: BotIdentity
) -> bool:
    """
    Verify if two bot identities belong to same HIVE group.
    
    Args:
        identity1: First bot identity
        identity2: Second bot identity
    
    Returns:
        True if both belong to same group (matching group_hash)
    
    EDUCATIONAL NOTE:
        Verifies group membership by comparing group hashes.
        Does NOT require revealing actual shared_secret to each other.
    """
    return (
        identity1.group_hash == identity2.group_hash and
        len(identity1.group_hash) > 0
    )


def verify_instance_hash(
    bot_id: str,
    table_id: str,
    position: int,
    shared_secret: str,
    claimed_hash: str
) -> bool:
    """
    Verify an instance hash is correct for given parameters.
    
    Args:
        bot_id: Bot identifier to verify
        table_id: Table identifier
        position: Claimed seat position
        shared_secret: Shared secret for verification
        claimed_hash: Hash to verify
    
    Returns:
        True if hash matches calculated hash
    
    EDUCATIONAL NOTE:
        Allows other bots to verify identity without trusting claimed values.
    """
    calculated = calculate_instance_hash(bot_id, table_id, position, shared_secret)
    return calculated == claimed_hash


def detect_table_collision(identities: list[BotIdentity]) -> bool:
    """
    Detect if multiple bots from same group are at same table.
    
    Args:
        identities: List of bot identities to check
    
    Returns:
        True if 2+ bots with same group_hash at same table_id
    
    EDUCATIONAL NOTE:
        This is the core detection mechanism for HIVE coordination.
        When 3 bots detect they're at same table, they activate coordination.
    """
    # Group by group_hash and table_id
    groups: dict[tuple[str, str], list[BotIdentity]] = {}
    
    for identity in identities:
        if not identity.group_hash or not identity.table_id:
            continue
        
        key = (identity.group_hash, identity.table_id)
        if key not in groups:
            groups[key] = []
        groups[key].append(identity)
    
    # Check if any group has 2+ bots at same table
    for (group_hash, table_id), bots in groups.items():
        if len(bots) >= 2:
            logger.info(
                f"HIVE detected: {len(bots)} bots from group {group_hash[:8]}... "
                f"at table {table_id}"
            )
            return True
    
    return False


class BotIdentityManager:
    """
    Manages bot identity and group coordination detection.
    
    EDUCATIONAL NOTE:
        This class handles:
        1. Bot identity generation
        2. Group membership verification
        3. Table collision detection (when HIVE activates)
        4. Identity updates when changing tables/positions
    """
    
    def __init__(
        self,
        bot_id: str,
        shared_secret: Optional[str] = None
    ):
        """
        Initialize identity manager.
        
        Args:
            bot_id: Unique bot identifier (UUID recommended)
            shared_secret: Shared secret for group (generates new if None)
        """
        self.bot_id = bot_id
        self.shared_secret = shared_secret or generate_shared_secret()
        self.current_identity: Optional[BotIdentity] = None
        
        # Known identities (other bots we've seen)
        self.known_identities: dict[str, BotIdentity] = {}
        
        logger.info(
            f"BotIdentityManager initialized: bot_id={bot_id[:8]}..., "
            f"group_hash={calculate_group_hash(self.shared_secret)}"
        )
    
    def join_table(self, table_id: str, position: int) -> BotIdentity:
        """
        Update identity when joining a table.
        
        Args:
            table_id: Table identifier
            position: Seat position (0-5)
        
        Returns:
            Updated BotIdentity
        
        EDUCATIONAL NOTE:
            Called when bot sits down at a table.
            Calculates new instance_hash for this table/position.
        """
        self.current_identity = BotIdentity(
            bot_id=self.bot_id,
            shared_secret=self.shared_secret,
            table_id=table_id,
            position=position
        )
        
        logger.info(
            f"Joined table {table_id} at position {position}, "
            f"instance_hash={self.current_identity.instance_hash}"
        )
        
        return self.current_identity
    
    def leave_table(self) -> None:
        """
        Clear identity when leaving table.
        
        EDUCATIONAL NOTE:
            Called when bot leaves table.
            Clears current table/position information.
        """
        if self.current_identity:
            logger.info(f"Left table {self.current_identity.table_id}")
        
        self.current_identity = None
    
    def register_identity(self, identity: BotIdentity) -> bool:
        """
        Register identity of another bot.
        
        Args:
            identity: Identity to register
        
        Returns:
            True if identity is valid and from same group
        
        EDUCATIONAL NOTE:
            Called when receiving identity announcement from another bot.
            Verifies group membership before storing.
        """
        if not self.current_identity:
            logger.warning("Cannot register identity - not at table")
            return False
        
        # Verify group membership
        if not verify_group_membership(self.current_identity, identity):
            logger.warning(
                f"Identity rejected - different group: "
                f"{identity.bot_id[:8]}..."
            )
            return False
        
        # Store identity
        self.known_identities[identity.bot_id] = identity
        
        logger.info(
            f"Registered identity: bot_id={identity.bot_id[:8]}..., "
            f"table={identity.table_id}, position={identity.position}"
        )
        
        return True
    
    def detect_hive_at_table(self) -> Optional[list[BotIdentity]]:
        """
        Detect if HIVE group is active at current table.
        
        Returns:
            List of bot identities at same table (including self) if HIVE detected,
            None otherwise
        
        EDUCATIONAL NOTE:
            Returns list of bots when 3+ bots from same group are at same table.
            This triggers HIVE coordination mode.
        """
        if not self.current_identity:
            return None
        
        # Get all bots at same table with same group
        hive_bots = [self.current_identity]
        
        for identity in self.known_identities.values():
            if (identity.table_id == self.current_identity.table_id and
                identity.group_hash == self.current_identity.group_hash):
                hive_bots.append(identity)
        
        # Need 3+ bots for HIVE
        if len(hive_bots) >= 3:
            logger.info(
                f"HIVE ACTIVE: {len(hive_bots)} bots at table "
                f"{self.current_identity.table_id}"
            )
            return hive_bots
        
        return None
    
    def get_statistics(self) -> dict:
        """Get identity manager statistics."""
        return {
            'bot_id': self.bot_id[:8] + "...",
            'group_hash': calculate_group_hash(self.shared_secret),
            'at_table': self.current_identity is not None,
            'current_table': self.current_identity.table_id if self.current_identity else None,
            'current_position': self.current_identity.position if self.current_identity else None,
            'known_identities': len(self.known_identities),
            'hive_active': self.detect_hive_at_table() is not None
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Bot Identification - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Generate shared secret for HIVE group
    shared_secret = generate_shared_secret()
    print(f"Generated shared secret: {shared_secret[:16]}...")
    print(f"Group hash: {calculate_group_hash(shared_secret)}")
    print()
    
    # Create 3 bots with same shared secret
    bot1 = BotIdentityManager("bot-001", shared_secret)
    bot2 = BotIdentityManager("bot-002", shared_secret)
    bot3 = BotIdentityManager("bot-003", shared_secret)
    
    # All bots join same table
    table_id = "table_123"
    identity1 = bot1.join_table(table_id, position=0)
    identity2 = bot2.join_table(table_id, position=2)
    identity3 = bot3.join_table(table_id, position=4)
    
    print("Bot Identities:")
    print(f"  Bot 1: position={identity1.position}, hash={identity1.instance_hash}")
    print(f"  Bot 2: position={identity2.position}, hash={identity2.instance_hash}")
    print(f"  Bot 3: position={identity3.position}, hash={identity3.instance_hash}")
    print()
    
    # Bots register each other
    bot1.register_identity(identity2)
    bot1.register_identity(identity3)
    bot2.register_identity(identity1)
    bot2.register_identity(identity3)
    bot3.register_identity(identity1)
    bot3.register_identity(identity2)
    
    # Detect HIVE
    hive = bot1.detect_hive_at_table()
    if hive:
        print("=" * 60)
        print("HIVE DETECTED!")
        print("=" * 60)
        print(f"Bots in HIVE: {len(hive)}")
        for bot in hive:
            print(f"  Bot {bot.bot_id[:8]}... at position {bot.position}")
        print()
    
    # Statistics
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    stats = bot1.get_statistics()
    print(f"Bot ID: {stats['bot_id']}")
    print(f"Group hash: {stats['group_hash']}")
    print(f"At table: {stats['at_table']}")
    print(f"Current table: {stats['current_table']}")
    print(f"Known identities: {stats['known_identities']}")
    print(f"HIVE active: {stats['hive_active']}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - Identity Management")
    print("=" * 60)
