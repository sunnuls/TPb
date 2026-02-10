"""
Tests for ExternalHubClient (Roadmap3 Phase 4.1).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest

from bridge.external_hub_client import (
    ExternalHubClient,
    HubConnection,
    MessageType,
    WEBSOCKETS_AVAILABLE,
    CRYPTOGRAPHY_AVAILABLE
)
from bridge.bot_identification import BotIdentityManager


class TestHubConnection:
    """Test HubConnection dataclass."""
    
    def test_hub_connection_creation(self):
        """Test basic connection creation."""
        conn = HubConnection(
            hub_url="ws://localhost:8765",
            agent_id="bot-001",
            environment_id="table_001",
            connected=True
        )
        
        assert conn.hub_url == "ws://localhost:8765"
        assert conn.agent_id == "bot-001"
        assert conn.environment_id == "table_001"
        assert conn.connected is True
        assert conn.encryption_key is None
        assert conn.websocket is None


class TestExternalHubClient:
    """Test ExternalHubClient basic functionality."""
    
    def test_init(self):
        """Test client initialization."""
        bot_identity = BotIdentityManager("bot-001", "secret")
        client = ExternalHubClient(
            hub_host="localhost",
            hub_port=8765,
            bot_identity=bot_identity
        )
        
        assert client.hub_host == "localhost"
        assert client.hub_port == 8765
        assert client.hub_url == "ws://localhost:8765"
        assert client.bot_identity == bot_identity
        assert client.connection is None
        assert client.messages_sent == 0
        assert client.messages_received == 0
    
    def test_init_default_values(self):
        """Test default initialization values."""
        bot_identity = BotIdentityManager("bot-001")
        client = ExternalHubClient(bot_identity=bot_identity)
        
        assert client.hub_host == "localhost"
        assert client.hub_port == 8765
        assert client.heartbeat_interval == 30.0
    
    def test_register_message_handler(self):
        """Test message handler registration."""
        bot_identity = BotIdentityManager("bot-001")
        client = ExternalHubClient(bot_identity=bot_identity)
        
        def handler(message):
            pass
        
        client.register_message_handler(MessageType.STATE_UPDATE, handler)
        
        assert MessageType.STATE_UPDATE.value in client.message_handlers
        assert client.message_handlers[MessageType.STATE_UPDATE.value] == handler
    
    def test_get_statistics(self):
        """Test statistics collection."""
        bot_identity = BotIdentityManager("bot-001")
        client = ExternalHubClient(
            hub_host="test-host",
            hub_port=9999,
            bot_identity=bot_identity
        )
        
        stats = client.get_statistics()
        
        assert stats['hub_url'] == "ws://test-host:9999"
        assert stats['connected'] is False
        assert stats['agent_id'] is None
        assert stats['environment_id'] is None
        assert stats['messages_sent'] == 0
        assert stats['messages_received'] == 0
        assert stats['reconnect_count'] == 0
        assert 'encryption_enabled' in stats
        assert 'websockets_available' in stats
        assert 'cryptography_available' in stats


class TestMessageTypes:
    """Test MessageType enum."""
    
    def test_message_type_values(self):
        """Test message type enum values."""
        assert MessageType.REGISTER.value == "register"
        assert MessageType.STATE_UPDATE.value == "state_update"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.DISCONNECT.value == "disconnect"
        assert MessageType.CARD_SHARE.value == "card_share"
        assert MessageType.COLLECTIVE_EQUITY.value == "collective_equity"


class TestDependencies:
    """Test dependency checking."""
    
    def test_websockets_availability(self):
        """Test websockets availability flag."""
        # Just check the flag exists
        assert isinstance(WEBSOCKETS_AVAILABLE, bool)
    
    def test_cryptography_availability(self):
        """Test cryptography availability flag."""
        # Just check the flag exists
        assert isinstance(CRYPTOGRAPHY_AVAILABLE, bool)


class TestClientIntegration:
    """Integration tests for hub client."""
    
    def test_client_without_websockets(self):
        """Test client behavior without websockets."""
        bot_identity = BotIdentityManager("bot-001")
        client = ExternalHubClient(bot_identity=bot_identity)
        
        # Should initialize even without websockets
        assert client is not None
        
        stats = client.get_statistics()
        assert 'websockets_available' in stats
    
    def test_multiple_clients(self):
        """Test creating multiple client instances."""
        bot1 = BotIdentityManager("bot-001", "secret")
        bot2 = BotIdentityManager("bot-002", "secret")
        bot3 = BotIdentityManager("bot-003", "secret")
        
        client1 = ExternalHubClient(bot_identity=bot1)
        client2 = ExternalHubClient(bot_identity=bot2)
        client3 = ExternalHubClient(bot_identity=bot3)
        
        # All should have unique bot IDs
        stats1 = client1.get_statistics()
        stats2 = client2.get_statistics()
        stats3 = client3.get_statistics()
        
        assert stats1['agent_id'] is None  # Not connected
        assert stats2['agent_id'] is None
        assert stats3['agent_id'] is None
        
        # But identities should be different
        assert client1.bot_identity.bot_id != client2.bot_identity.bot_id
        assert client2.bot_identity.bot_id != client3.bot_identity.bot_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
