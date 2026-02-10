"""
External Hub Client Module (Roadmap3 Phase 4.1).

WebSocket client for connecting bridge instances to external CentralHub.
Enables multi-bot coordination across different machine/process instances.

Key Features:
- WebSocket connection to sim_engine/central_hub.py
- Fernet encryption for secure state transmission
- Agent registration and environment grouping
- Shared state synchronization
- Reconnection handling

EDUCATIONAL USE ONLY: For HCI research prototype studying distributed coordination.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

# Try to import websockets (optional dependency for Phase 4)
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except (ImportError, ModuleNotFoundError, AttributeError, SyntaxError):
    WEBSOCKETS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("websockets not available - install with: pip install websockets")

# Try to import cryptography (optional dependency for Phase 4)
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except (ImportError, ModuleNotFoundError, AttributeError, SyntaxError):
    CRYPTOGRAPHY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("cryptography not available - install with: pip install cryptography")

from bridge.bot_identification import BotIdentityManager
from bridge.safety import SafetyFramework

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Message types for hub communication (matches central_hub.py)."""
    REGISTER = "register"
    STATE_UPDATE = "state_update"
    HEARTBEAT = "heartbeat"
    DISCONNECT = "disconnect"
    CARD_SHARE = "card_share"
    COLLECTIVE_EQUITY = "collective_equity"


@dataclass
class HubConnection:
    """
    Connection state to external hub.
    
    Attributes:
        hub_url: WebSocket URL (ws://host:port)
        agent_id: Bot identifier
        environment_id: Table/environment identifier
        connected: Connection status
        encryption_key: Fernet encryption key
        websocket: WebSocket connection (if connected)
    """
    hub_url: str
    agent_id: str
    environment_id: str
    connected: bool = False
    encryption_key: Optional[bytes] = None
    websocket: Optional[Any] = None  # websockets.WebSocketClientProtocol


class ExternalHubClient:
    """
    WebSocket client for connecting to external CentralHub.
    
    Connects bridge instances to sim_engine/central_hub.py server
    for multi-bot coordination.
    
    Protocol (compatible with central_hub.py):
    1. Connect to WebSocket at ws://host:port
    2. Send REGISTER message with agent_id and environment_id
    3. Receive encryption_key in registration response
    4. Send/receive encrypted STATE_UPDATE messages
    5. Send periodic HEARTBEAT messages
    6. Handle CARD_SHARE and COLLECTIVE_EQUITY messages
    
    EDUCATIONAL NOTE:
        This enables distributed HIVE coordination where each bot
        runs in separate process/machine but coordinates through
        central hub for collective decision-making.
    """
    
    def __init__(
        self,
        hub_host: str = "localhost",
        hub_port: int = 8765,
        bot_identity: Optional[BotIdentityManager] = None,
        safety: Optional[SafetyFramework] = None,
        heartbeat_interval: float = 30.0
    ):
        """
        Initialize hub client.
        
        Args:
            hub_host: Hub server hostname/IP
            hub_port: Hub server port
            bot_identity: Bot identity manager
            safety: Safety framework instance
            heartbeat_interval: Seconds between heartbeats
        """
        self.hub_host = hub_host
        self.hub_port = hub_port
        self.hub_url = f"ws://{hub_host}:{hub_port}"
        
        self.bot_identity = bot_identity
        self.safety = safety or SafetyFramework.get_instance()
        self.heartbeat_interval = heartbeat_interval
        
        # Connection state
        self.connection: Optional[HubConnection] = None
        self.cipher: Optional[Any] = None  # Fernet cipher
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.reconnect_count = 0
        
        # Check dependencies
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not available - hub client disabled")
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.error("cryptography library not available - encryption disabled")
        
        logger.info(
            f"ExternalHubClient initialized: "
            f"hub={self.hub_url}, bot_id={bot_identity.bot_id[:8] if bot_identity else 'none'}..."
        )
    
    async def connect(
        self,
        environment_id: str,
        timeout: float = 10.0
    ) -> bool:
        """
        Connect to external hub and register agent.
        
        Args:
            environment_id: Table/environment identifier
            timeout: Connection timeout in seconds
        
        Returns:
            True if connection successful
        
        EDUCATIONAL NOTE:
            Establishes WebSocket connection and performs agent registration.
            Receives encryption key from hub for secure communication.
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot connect - websockets not available")
            return False
        
        if not self.bot_identity:
            logger.error("Cannot connect - no bot identity")
            return False
        
        # Log decision
        self.safety.log_decision({
            'action': 'hub_connect',
            'reason': f"Connecting to hub at {self.hub_url}",
            'allowed': True
        })
        
        try:
            # Connect to WebSocket
            logger.info(f"Connecting to hub at {self.hub_url}...")
            websocket = await asyncio.wait_for(
                websockets.connect(self.hub_url),
                timeout=timeout
            )
            
            # Send registration message
            register_msg = {
                "message_type": MessageType.REGISTER.value,
                "agent_id": self.bot_identity.bot_id,
                "environment_id": environment_id
            }
            
            await websocket.send(json.dumps(register_msg))
            logger.info(f"Sent registration: agent_id={self.bot_identity.bot_id[:8]}...")
            
            # Receive registration response
            response_data = await asyncio.wait_for(
                websocket.recv(),
                timeout=timeout
            )
            response = json.loads(response_data)
            
            if response.get("status") != "success":
                logger.error(f"Registration failed: {response}")
                await websocket.close()
                return False
            
            # Extract encryption key
            encryption_key = response.get("encryption_key")
            if encryption_key and CRYPTOGRAPHY_AVAILABLE:
                self.cipher = Fernet(encryption_key.encode())
                logger.info("Encryption enabled")
            else:
                logger.warning("Encryption not available - messages unencrypted")
            
            # Store connection
            self.connection = HubConnection(
                hub_url=self.hub_url,
                agent_id=self.bot_identity.bot_id,
                environment_id=environment_id,
                connected=True,
                encryption_key=encryption_key.encode() if encryption_key else None,
                websocket=websocket
            )
            
            logger.info(
                f"Connected to hub: agents_in_environment="
                f"{response.get('agents_in_environment', 0)}"
            )
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            return False
    
    async def disconnect(self) -> None:
        """
        Disconnect from hub gracefully.
        
        EDUCATIONAL NOTE:
            Sends DISCONNECT message before closing WebSocket.
        """
        if not self.connection or not self.connection.connected:
            return
        
        try:
            # Send disconnect message
            disconnect_msg = {
                "message_type": MessageType.DISCONNECT.value,
                "agent_id": self.connection.agent_id
            }
            
            await self.connection.websocket.send(json.dumps(disconnect_msg))
            await self.connection.websocket.close()
            
            logger.info("Disconnected from hub")
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
        
        finally:
            self.connection.connected = False
            self.connection.websocket = None
    
    async def send_state_update(self, state_data: Dict[str, Any]) -> bool:
        """
        Send state update to hub.
        
        Args:
            state_data: State information to share with other agents
        
        Returns:
            True if sent successfully
        
        EDUCATIONAL NOTE:
            Encrypts state data before transmission if cipher available.
            Used to share partial information with coordinating agents.
        """
        if not self.connection or not self.connection.connected:
            logger.warning("Cannot send state - not connected")
            return False
        
        try:
            # Prepare message
            message = {
                "message_type": MessageType.STATE_UPDATE.value,
                "agent_id": self.connection.agent_id,
                "environment_id": self.connection.environment_id,
                "timestamp": state_data.get("timestamp", 0.0)
            }
            
            # Encrypt state data if cipher available
            if self.cipher and CRYPTOGRAPHY_AVAILABLE:
                encrypted = self.cipher.encrypt(
                    json.dumps(state_data).encode()
                )
                message["encrypted_state"] = encrypted.decode()
            else:
                message["state"] = state_data
            
            # Send message
            await self.connection.websocket.send(json.dumps(message))
            self.messages_sent += 1
            
            logger.debug(f"Sent state update: {len(state_data)} fields")
            return True
            
        except Exception as e:
            logger.error(f"Send state error: {e}")
            return False
    
    async def send_heartbeat(self) -> bool:
        """
        Send heartbeat to hub.
        
        Returns:
            True if sent successfully
        
        EDUCATIONAL NOTE:
            Keeps connection alive and notifies hub of agent health.
        """
        if not self.connection or not self.connection.connected:
            return False
        
        try:
            heartbeat_msg = {
                "message_type": MessageType.HEARTBEAT.value,
                "agent_id": self.connection.agent_id
            }
            
            await self.connection.websocket.send(json.dumps(heartbeat_msg))
            logger.debug("Sent heartbeat")
            return True
            
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive message from hub.
        
        Args:
            timeout: Receive timeout in seconds
        
        Returns:
            Received message dict or None
        
        EDUCATIONAL NOTE:
            Receives and decrypts messages from hub.
            Handles STATE_UPDATE, CARD_SHARE, COLLECTIVE_EQUITY messages.
        """
        if not self.connection or not self.connection.connected:
            return None
        
        try:
            # Receive message
            if timeout:
                message_data = await asyncio.wait_for(
                    self.connection.websocket.recv(),
                    timeout=timeout
                )
            else:
                message_data = await self.connection.websocket.recv()
            
            message = json.loads(message_data)
            self.messages_received += 1
            
            # Decrypt if encrypted
            if "encrypted_state" in message and self.cipher and CRYPTOGRAPHY_AVAILABLE:
                decrypted = self.cipher.decrypt(
                    message["encrypted_state"].encode()
                )
                message["state"] = json.loads(decrypted.decode())
                del message["encrypted_state"]
            
            logger.debug(f"Received message: type={message.get('message_type')}")
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Receive message error: {e}")
            return None
    
    async def run_heartbeat_loop(self) -> None:
        """
        Run periodic heartbeat loop.
        
        EDUCATIONAL NOTE:
            Sends heartbeats at regular intervals to maintain connection.
        """
        while self.connection and self.connection.connected:
            await self.send_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)
    
    def register_message_handler(
        self,
        message_type: MessageType,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register handler for specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Callback function for this message type
        
        EDUCATIONAL NOTE:
            Allows customization of message handling for different
            coordination scenarios.
        """
        self.message_handlers[message_type.value] = handler
        logger.info(f"Registered handler for {message_type.value}")
    
    def get_statistics(self) -> dict:
        """Get hub client statistics."""
        return {
            'hub_url': self.hub_url,
            'connected': self.connection.connected if self.connection else False,
            'agent_id': self.connection.agent_id[:8] + "..." if self.connection else None,
            'environment_id': self.connection.environment_id if self.connection else None,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'reconnect_count': self.reconnect_count,
            'encryption_enabled': self.cipher is not None,
            'websockets_available': WEBSOCKETS_AVAILABLE,
            'cryptography_available': CRYPTOGRAPHY_AVAILABLE
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("External Hub Client - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Check dependencies
    print("Dependency Check:")
    print(f"  websockets: {'[OK] Available' if WEBSOCKETS_AVAILABLE else '[NO] Not available'}")
    print(f"  cryptography: {'[OK] Available' if CRYPTOGRAPHY_AVAILABLE else '[NO] Not available'}")
    print()
    
    if not WEBSOCKETS_AVAILABLE or not CRYPTOGRAPHY_AVAILABLE:
        print("[INFO] Some dependencies not available")
        print("       Install with: pip install websockets cryptography")
        print()
        print("=" * 60)
        print("Demo mode - showing client configuration")
        print("=" * 60)
        print()
        
        # Show configuration example
        from bridge.bot_identification import BotIdentityManager
        
        bot_identity = BotIdentityManager("bot-demo-001")
        client = ExternalHubClient(
            hub_host="localhost",
            hub_port=8765,
            bot_identity=bot_identity
        )
        
        stats = client.get_statistics()
        print("Client Configuration:")
        print(f"  Hub URL: {stats['hub_url']}")
        print(f"  Bot ID: {stats['agent_id']}")
        print(f"  Connected: {stats['connected']}")
        print(f"  Websockets: {stats['websockets_available']}")
        print(f"  Cryptography: {stats['cryptography_available']}")
        print()
    
    print("=" * 60)
    print("Educational HCI Research - Hub Client")
    print("=" * 60)
    print()
    print("[NOTE] To test full connection:")
    print("  1. Start central hub: python -m sim_engine.central_hub")
    print("  2. Run this client with websockets + cryptography installed")
    print()
