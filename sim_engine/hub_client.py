"""
Hub Client for Multi-Agent Coordination Integration.

This module provides connectivity between LiveRTA agents and the Central Hub
for multi-agent game theory research simulations.

Educational Use Only: Designed for coordinating multiple simulation agents
in research environments. Not for production or real-money applications.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import websockets

from sim_engine.central_hub import AgentStateMessage, MessageType


@dataclass
class HubConfig:
    """
    Configuration for Hub connectivity (Пункт 2, Шаг 2.2).
    
    Educational Note:
        This configuration enables agents to connect to the central hub
        for coordinated multi-agent research simulations.
    """
    enabled: bool = False
    hub_url: str = "ws://localhost:8765"
    agent_id: Optional[str] = None
    environment_id: str = "research_env_1"
    timeout: float = 5.0
    heartbeat_interval: float = 30.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HubConfig":
        """Create config from dictionary."""
        return cls(
            enabled=bool(data.get("enabled", False)),
            hub_url=str(data.get("hub_url", "ws://localhost:8765")),
            agent_id=data.get("agent_id"),
            environment_id=str(data.get("environment_id", "research_env_1")),
            timeout=float(data.get("timeout", 5.0)),
            heartbeat_interval=float(data.get("heartbeat_interval", 30.0))
        )


class HubClient:
    """
    WebSocket client for connecting to Central Hub.
    
    Features (Пункт 2):
    - Async connection to central hub
    - State synchronization queries
    - Automatic heartbeat
    - Decision coordination before actions
    
    Educational Note:
        This client allows research agents to query the hub before making
        decisions, enabling coordinated multi-agent behavior studies.
    """
    
    def __init__(self, config: HubConfig):
        """
        Initialize hub client.
        
        Args:
            config: Hub configuration
        """
        self.config = config
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.encryption_key: Optional[str] = None
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        
        # Received messages queue
        self._message_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self) -> bool:
        """
        Connect to central hub and register agent.
        
        Returns:
            True if connection successful
            
        Educational Note:
            Establishes WebSocket connection for multi-agent coordination.
        """
        if not self.config.enabled:
            return False
        
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.config.hub_url),
                timeout=self.config.timeout
            )
            
            # Register with hub
            register_msg = AgentStateMessage(
                agent_id=self.config.agent_id or f"agent_{int(time.time())}",
                message_type=MessageType.REGISTER,
                environment_id=self.config.environment_id
            )
            
            await self.websocket.send(register_msg.model_dump_json())
            
            # Wait for registration confirmation
            response_raw = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=self.config.timeout
            )
            
            response = json.loads(response_raw)
            
            if response.get("status") == "success":
                self.connected = True
                self.encryption_key = response.get("encryption_key")
                
                # Start background tasks
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._receive_task = asyncio.create_task(self._receive_loop())
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Hub connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from hub."""
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close websocket
        if self.websocket:
            await self.websocket.close()
        
        self.connected = False
    
    async def query_hub_before_action(
        self,
        planned_action: Dict[str, Any],
        state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query hub before taking action (Пункт 2: agents query hub before action).
        
        This is the main integration point where agents coordinate with the hub
        before making decisions in multi-agent simulations.
        
        Args:
            planned_action: The action agent plans to take
            state_data: Current agent state (equity, confidence, etc.)
        
        Returns:
            Hub response with coordination info:
            - conflicts_detected: List of conflicts if any
            - collective_probabilities: Aggregated probabilities
            - proceed: Whether agent should proceed with action
            
        Educational Note:
            This coordination mechanism allows agents to avoid conflicting
            actions and benefit from collective information in research sims.
        """
        if not self.connected or not self.websocket:
            # Hub not connected, proceed without coordination
            return {
                "proceed": True,
                "conflicts_detected": [],
                "collective_probabilities": {},
                "note": "hub_not_connected"
            }
        
        try:
            # Send state sync with planned action
            sync_msg = AgentStateMessage(
                agent_id=self.config.agent_id or "unknown",
                message_type=MessageType.STATE_SYNC,
                environment_id=self.config.environment_id,
                state_data={
                    **state_data,
                    "planned_action": planned_action
                },
                requires_sync=True
            )
            
            await self.websocket.send(sync_msg.model_dump_json())
            
            # Wait for sync response (with timeout)
            try:
                response = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=2.0
                )
                
                # Check for conflicts
                conflicts = response.get("conflicts_detected", [])
                collective_probs = response.get("collective_probabilities", {})
                
                # Determine if should proceed
                has_conflicts = len(conflicts) > 0
                
                return {
                    "proceed": not has_conflicts,
                    "conflicts_detected": conflicts,
                    "collective_probabilities": collective_probs,
                    "agent_count": response.get("agent_count", 1)
                }
                
            except asyncio.TimeoutError:
                # No response from hub, proceed anyway
                return {
                    "proceed": True,
                    "conflicts_detected": [],
                    "collective_probabilities": {},
                    "note": "hub_timeout"
                }
        
        except Exception as e:
            print(f"Hub query error: {e}")
            return {
                "proceed": True,
                "conflicts_detected": [],
                "collective_probabilities": {},
                "note": f"error:{e}"
            }
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to hub."""
        while self.connected and self.websocket:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                heartbeat_msg = AgentStateMessage(
                    agent_id=self.config.agent_id or "unknown",
                    message_type=MessageType.HEARTBEAT
                )
                
                await self.websocket.send(heartbeat_msg.model_dump_json())
                
            except asyncio.CancelledError:
                break
            except Exception:
                break
    
    async def _receive_loop(self) -> None:
        """Receive messages from hub."""
        while self.connected and self.websocket:
            try:
                msg_raw = await self.websocket.recv()
                message = json.loads(msg_raw)
                
                # Filter relevant messages
                msg_type = message.get("message_type")
                
                if msg_type == MessageType.STATE_SYNC.value:
                    # Queue sync messages for query_hub_before_action
                    await self._message_queue.put(message)
                
                elif msg_type == MessageType.HEARTBEAT.value:
                    # Heartbeat ack, ignore
                    pass
                
                elif msg_type == "agent_status_change":
                    # Other agent status changed
                    print(f"Agent {message.get('agent_id')} status: {message.get('status')}")
                
            except asyncio.CancelledError:
                break
            except Exception:
                break


def create_hub_client_from_config(config_dict: Dict[str, Any]) -> Optional[HubClient]:
    """
    Factory function to create HubClient from config dictionary.
    
    This is the main entry point for LiveRTA integration (Пункт 2).
    
    Args:
        config_dict: Dictionary with hub configuration keys:
            - enabled: bool
            - hub_url: str (e.g., "ws://localhost:8765")
            - agent_id: str (optional, auto-generated if None)
            - environment_id: str
            - timeout: float
            - heartbeat_interval: float
    
    Returns:
        HubClient instance if enabled, None otherwise
        
    Example config (in LiveRTA YAML):
        ```yaml
        hub:
          enabled: true
          hub_url: "ws://localhost:8765"
          agent_id: "research_agent_1"
          environment_id: "poker_sim_env"
          timeout: 5.0
          heartbeat_interval: 30.0
        ```
    
    Educational Note:
        This enables multi-agent coordination in simulation research
        by connecting LiveRTA instances to the central hub.
    """
    hub_config = HubConfig.from_dict(config_dict)
    
    if not hub_config.enabled:
        return None
    
    return HubClient(hub_config)
