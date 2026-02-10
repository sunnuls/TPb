"""
Tests for BotIdentification (Roadmap3 Phase 4.2).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from bridge.bot_identification import (
    BotIdentityManager,
    BotIdentity,
    generate_shared_secret,
    calculate_group_hash,
    calculate_instance_hash,
    verify_group_membership,
    verify_instance_hash,
    detect_table_collision
)


class TestBotIdentity:
    """Test BotIdentity dataclass."""
    
    def test_bot_identity_creation(self):
        """Test basic identity creation."""
        identity = BotIdentity(
            bot_id="bot-001",
            shared_secret="test_secret",
            table_id="table_001",
            position=0
        )
        
        assert identity.bot_id == "bot-001"
        assert identity.shared_secret == "test_secret"
        assert identity.table_id == "table_001"
        assert identity.position == 0
        # Hashes should be auto-calculated
        assert len(identity.instance_hash) == 16
        assert len(identity.group_hash) == 16
    
    def test_bot_identity_hash_calculation(self):
        """Test automatic hash calculation."""
        identity = BotIdentity(
            bot_id="bot-001",
            shared_secret="secret123",
            table_id="table_001",
            position=2
        )
        
        # Verify hashes match manual calculation
        expected_group = calculate_group_hash("secret123")
        expected_instance = calculate_instance_hash(
            "bot-001", "table_001", 2, "secret123"
        )
        
        assert identity.group_hash == expected_group
        assert identity.instance_hash == expected_instance


class TestHashFunctions:
    """Test hash generation functions."""
    
    def test_generate_shared_secret(self):
        """Test shared secret generation."""
        secret = generate_shared_secret()
        
        # Should be hex string
        assert isinstance(secret, str)
        assert len(secret) == 64  # 32 bytes = 64 hex chars
        
        # Different calls should produce different secrets
        secret2 = generate_shared_secret()
        assert secret != secret2
    
    def test_calculate_group_hash(self):
        """Test group hash calculation."""
        hash1 = calculate_group_hash("secret123")
        hash2 = calculate_group_hash("secret123")
        hash3 = calculate_group_hash("different")
        
        # Same secret -> same hash
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different secret -> different hash
        assert hash1 != hash3
    
    def test_calculate_instance_hash(self):
        """Test instance hash calculation."""
        hash1 = calculate_instance_hash("bot-001", "table_001", 0, "secret")
        hash2 = calculate_instance_hash("bot-001", "table_001", 0, "secret")
        
        # Same inputs -> same hash
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different position -> different hash
        hash3 = calculate_instance_hash("bot-001", "table_001", 1, "secret")
        assert hash1 != hash3
        
        # Different bot -> different hash
        hash4 = calculate_instance_hash("bot-002", "table_001", 0, "secret")
        assert hash1 != hash4


class TestVerificationFunctions:
    """Test verification functions."""
    
    def test_verify_group_membership(self):
        """Test group membership verification."""
        secret = "shared_secret"
        
        identity1 = BotIdentity(
            bot_id="bot-001",
            shared_secret=secret,
            table_id="table_001",
            position=0
        )
        
        identity2 = BotIdentity(
            bot_id="bot-002",
            shared_secret=secret,
            table_id="table_001",
            position=2
        )
        
        identity3 = BotIdentity(
            bot_id="bot-003",
            shared_secret="different_secret",
            table_id="table_001",
            position=4
        )
        
        # Same secret -> same group
        assert verify_group_membership(identity1, identity2) is True
        
        # Different secret -> different group
        assert verify_group_membership(identity1, identity3) is False
    
    def test_verify_instance_hash(self):
        """Test instance hash verification."""
        bot_id = "bot-001"
        table_id = "table_001"
        position = 0
        secret = "test_secret"
        
        # Calculate valid hash
        valid_hash = calculate_instance_hash(bot_id, table_id, position, secret)
        
        # Verify with correct parameters
        assert verify_instance_hash(
            bot_id, table_id, position, secret, valid_hash
        ) is True
        
        # Verify with wrong position
        assert verify_instance_hash(
            bot_id, table_id, 1, secret, valid_hash
        ) is False
    
    def test_detect_table_collision(self):
        """Test table collision detection."""
        secret = "shared_secret"
        
        # 3 bots at same table with same secret
        identity1 = BotIdentity(
            bot_id="bot-001",
            shared_secret=secret,
            table_id="table_001",
            position=0
        )
        identity2 = BotIdentity(
            bot_id="bot-002",
            shared_secret=secret,
            table_id="table_001",
            position=2
        )
        identity3 = BotIdentity(
            bot_id="bot-003",
            shared_secret=secret,
            table_id="table_001",
            position=4
        )
        
        # Should detect collision (3 bots at same table)
        assert detect_table_collision([identity1, identity2, identity3]) is True
        
        # Only 2 bots -> still collision
        assert detect_table_collision([identity1, identity2]) is True
        
        # Single bot -> no collision
        assert detect_table_collision([identity1]) is False
    
    def test_detect_table_collision_different_tables(self):
        """Test no collision when bots at different tables."""
        secret = "shared_secret"
        
        identity1 = BotIdentity(
            bot_id="bot-001",
            shared_secret=secret,
            table_id="table_001",
            position=0
        )
        identity2 = BotIdentity(
            bot_id="bot-002",
            shared_secret=secret,
            table_id="table_002",  # Different table
            position=2
        )
        
        # Different tables -> no collision
        assert detect_table_collision([identity1, identity2]) is False


class TestBotIdentityManager:
    """Test BotIdentityManager class."""
    
    def test_init(self):
        """Test manager initialization."""
        manager = BotIdentityManager("bot-001", "test_secret")
        
        assert manager.bot_id == "bot-001"
        assert manager.shared_secret == "test_secret"
        assert manager.current_identity is None
        assert len(manager.known_identities) == 0
    
    def test_init_generates_secret(self):
        """Test automatic secret generation."""
        manager = BotIdentityManager("bot-001")
        
        # Should generate secret automatically
        assert manager.shared_secret is not None
        assert len(manager.shared_secret) == 64
    
    def test_join_table(self):
        """Test joining table."""
        manager = BotIdentityManager("bot-001", "secret")
        
        identity = manager.join_table("table_001", 0)
        
        assert identity is not None
        assert identity.bot_id == "bot-001"
        assert identity.table_id == "table_001"
        assert identity.position == 0
        assert manager.current_identity == identity
    
    def test_leave_table(self):
        """Test leaving table."""
        manager = BotIdentityManager("bot-001", "secret")
        
        manager.join_table("table_001", 0)
        assert manager.current_identity is not None
        
        manager.leave_table()
        assert manager.current_identity is None
    
    def test_register_identity(self):
        """Test registering other bot identity."""
        secret = "shared_secret"
        
        manager1 = BotIdentityManager("bot-001", secret)
        manager1.join_table("table_001", 0)
        
        # Create identity from another bot
        identity2 = BotIdentity(
            bot_id="bot-002",
            shared_secret=secret,
            table_id="table_001",
            position=2
        )
        
        # Register identity
        result = manager1.register_identity(identity2)
        
        assert result is True
        assert "bot-002" in manager1.known_identities
    
    def test_register_identity_different_group(self):
        """Test rejecting identity from different group."""
        manager1 = BotIdentityManager("bot-001", "secret1")
        manager1.join_table("table_001", 0)
        
        # Create identity with different secret
        identity2 = BotIdentity(
            bot_id="bot-002",
            shared_secret="secret2",
            table_id="table_001",
            position=2
        )
        
        # Should reject
        result = manager1.register_identity(identity2)
        assert result is False
        assert "bot-002" not in manager1.known_identities
    
    def test_detect_hive_at_table(self):
        """Test HIVE detection at table."""
        secret = "shared_secret"
        
        # Create 3 managers with same secret
        manager1 = BotIdentityManager("bot-001", secret)
        manager2 = BotIdentityManager("bot-002", secret)
        manager3 = BotIdentityManager("bot-003", secret)
        
        # All join same table
        identity1 = manager1.join_table("table_001", 0)
        identity2 = manager2.join_table("table_001", 2)
        identity3 = manager3.join_table("table_001", 4)
        
        # Register each other
        manager1.register_identity(identity2)
        manager1.register_identity(identity3)
        
        # Should detect HIVE (3+ bots)
        hive = manager1.detect_hive_at_table()
        assert hive is not None
        assert len(hive) == 3
    
    def test_detect_hive_insufficient_bots(self):
        """Test no HIVE detection with < 3 bots."""
        secret = "shared_secret"
        
        manager1 = BotIdentityManager("bot-001", secret)
        manager2 = BotIdentityManager("bot-002", secret)
        
        identity1 = manager1.join_table("table_001", 0)
        identity2 = manager2.join_table("table_001", 2)
        
        manager1.register_identity(identity2)
        
        # Only 2 bots -> no HIVE
        hive = manager1.detect_hive_at_table()
        assert hive is None
    
    def test_get_statistics(self):
        """Test statistics collection."""
        manager = BotIdentityManager("bot-001", "secret")
        manager.join_table("table_001", 0)
        
        stats = manager.get_statistics()
        
        assert 'bot_id' in stats
        assert 'group_hash' in stats
        assert stats['at_table'] is True
        assert stats['current_table'] == "table_001"
        assert stats['current_position'] == 0
        assert stats['known_identities'] == 0
        assert stats['hive_active'] is False


class TestHiveIntegration:
    """Integration tests for HIVE detection."""
    
    def test_full_hive_workflow(self):
        """Test complete HIVE detection workflow."""
        # Generate shared secret
        secret = generate_shared_secret()
        
        # Create 3 bots
        bot1 = BotIdentityManager("bot-001", secret)
        bot2 = BotIdentityManager("bot-002", secret)
        bot3 = BotIdentityManager("bot-003", secret)
        
        # All join same table
        table_id = "table_123"
        id1 = bot1.join_table(table_id, 0)
        id2 = bot2.join_table(table_id, 2)
        id3 = bot3.join_table(table_id, 4)
        
        # Bots register each other (simulating network discovery)
        bot1.register_identity(id2)
        bot1.register_identity(id3)
        bot2.register_identity(id1)
        bot2.register_identity(id3)
        bot3.register_identity(id1)
        bot3.register_identity(id2)
        
        # All should detect HIVE
        hive1 = bot1.detect_hive_at_table()
        hive2 = bot2.detect_hive_at_table()
        hive3 = bot3.detect_hive_at_table()
        
        assert hive1 is not None and len(hive1) == 3
        assert hive2 is not None and len(hive2) == 3
        assert hive3 is not None and len(hive3) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
