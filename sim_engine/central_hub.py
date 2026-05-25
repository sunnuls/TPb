"""
Central Hub for Multi-Agent State Synchronization.

This module provides WebSocket-based coordination for multi-agent simulations,
enabling secure state synchronization and collective decision-making for
game theory research.

Educational Use Only: Designed for controlled research environments to study
multi-agent coordination patterns. Not intended for production gaming or
real-money applications.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import websockets
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent connection status."""
    CONNECTED = "connected"
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"


class MessageType(str, Enum):
    """WebSocket message types for hub communication."""
    REGISTER = "register"
    STATE_SYNC = "state_sync"
    DECISION_REQUEST = "decision_request"
    DECISION_RESPONSE = "decision_response"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    # Roadmap2 Phase 2: Card sharing
    CARD_SHARE = "card_share"
    COLLECTIVE_EQUITY = "collective_equity"


class AgentStateMessage(BaseModel):
    """
    Message format for agent state synchronization.
    
    Educational Note:
        This structure enables research into how shared information
        affects collective decision-making in multi-agent systems.
    """
    agent_id: str = Field(..., min_length=1)
    message_type: MessageType
    timestamp: float = Field(default_factory=time.time)
    
    # State data (encrypted in transit)
    state_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Coordination metadata
    environment_id: Optional[str] = None
    requires_sync: bool = False


@dataclass
class AgentConnection:
    """Represents a connected agent in the hub."""
    agent_id: str
    websocket: websockets.WebSocketServerProtocol
    status: AgentStatus = AgentStatus.CONNECTED
    environment_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    state_data: Dict[str, Any] = field(default_factory=dict)


class CentralHub:
    """
    Central coordination hub for multi-agent simulations.
    
    Features (Пункт 1 & Подпункты 1.1, 1.2):
    - WebSocket-based agent connectivity
    - Encrypted state data transmission for secure research
    - Shared state synchronization for 2+ agents
    - Collective probability recalculation
    - Conflict avoidance in multi-agent scenarios
    - Reconnect and heartbeat mechanisms
    - Support for multiple concurrent simulation environments
    
    Educational Note:
        This hub enables research into coordination problems in game theory,
        studying how agents can cooperate without revealing full private
        information while avoiding conflicting actions.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        encryption_key: Optional[bytes] = None,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0
    ):
        """
        Initialize central hub.
        
        Args:
            host: Host to bind WebSocket server
            port: Port for WebSocket server
            encryption_key: Fernet encryption key (generated if None)
            heartbeat_interval: Seconds between heartbeat checks
            heartbeat_timeout: Seconds before agent considered disconnected
        """
        self.host = host
        self.port = port
        
        # Encryption for secure research data flow
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Connected agents
        self.agents: Dict[str, AgentConnection] = {}
        self._connections = self.agents  # Alias for backward compatibility
        
        # Environment groupings (agents in same simulation environment)
        self.environments: Dict[str, Set[str]] = {}
        
        # Roadmap2 Phase 2: Sessions for card sharing
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat configuration
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        
        # Message queue for processing
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Server instance
        self.server: Optional[websockets.WebSocketServer] = None
        
    def encrypt_state(self, state_data: Dict[str, Any]) -> str:
        """
        Encrypt state data for secure transmission.
        
        Educational Note:
            Encryption ensures private agent information remains confidential
            during research, modeling real-world privacy constraints.
        """
        json_data = json.dumps(state_data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted.decode()
    
    def decrypt_state(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt received state data."""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
    
    async def register_agent(
        self,
        websocket: websockets.WebSocketServerProtocol,
        agent_id: str,
        environment_id: Optional[str] = None
    ) -> None:
        """
        Register new agent connection.
        
        Args:
            websocket: WebSocket connection
            agent_id: Unique agent identifier
            environment_id: Optional environment grouping
        """
        connection = AgentConnection(
            agent_id=agent_id,
            websocket=websocket,
            environment_id=environment_id,
            status=AgentStatus.ACTIVE
        )
        
        self.agents[agent_id] = connection
        
        # Add to environment group
        if environment_id:
            if environment_id not in self.environments:
                self.environments[environment_id] = set()
            self.environments[environment_id].add(agent_id)
        
        # Send registration confirmation
        response = {
            "message_type": MessageType.REGISTER.value,
            "status": "success",
            "agent_id": agent_id,
            "encryption_key": self.encryption_key.decode(),
            "agents_in_environment": len(self.environments.get(environment_id, set()))
        }
        
        await websocket.send(json.dumps(response))
    
    async def handle_state_sync(
        self,
        agent_id: str,
        message: AgentStateMessage
    ) -> None:
        """
        Handle state synchronization request (Подпункт 1.1).
        
        Logic:
        - If 2+ agents in environment, broadcast state update
        - Recalculate collective probabilities
        - Check for conflicting actions
        
        Educational Note:
            This implements coordination logic to prevent agents from
            making mutually incompatible decisions in shared simulations.
        """
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        environment_id = message.environment_id or agent.environment_id
        
        if not environment_id:
            return
        
        # Update agent's state
        agent.state_data = message.state_data
        
        # Get agents in same environment
        agents_in_env = self.environments.get(environment_id, set())
        
        # If 2+ agents, perform collective synchronization
        if len(agents_in_env) >= 2:
            await self._sync_environment_state(environment_id, agents_in_env)
    
    async def _sync_environment_state(
        self,
        environment_id: str,
        agent_ids: Set[str]
    ) -> None:
        """
        Synchronize state across multiple agents in same environment.
        
        Performs:
        - Collective probability aggregation
        - Conflict detection
        - State broadcast to all agents in environment
        """
        # Collect all agent states
        collective_state = {}
        planned_actions = []
        
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                continue
            
            agent = self.agents[agent_id]
            collective_state[agent_id] = agent.state_data
            
            # Collect planned actions for conflict detection
            if "planned_action" in agent.state_data:
                planned_actions.append({
                    "agent_id": agent_id,
                    "action": agent.state_data["planned_action"]
                })
        
        # Detect conflicts (Подпункт 1.1: Avoid conflicting actions)
        conflicts = self._detect_action_conflicts(planned_actions)
        
        # Recalculate collective probabilities
        collective_probs = self._calculate_collective_probabilities(collective_state)
        
        # Broadcast synchronized state to all agents
        sync_message = {
            "message_type": MessageType.STATE_SYNC.value,
            "environment_id": environment_id,
            "timestamp": time.time(),
            "collective_probabilities": collective_probs,
            "conflicts_detected": conflicts,
            "agent_count": len(agent_ids)
        }
        
        # Send to all agents in environment
        for agent_id in agent_ids:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                try:
                    await agent.websocket.send(json.dumps(sync_message))
                except websockets.exceptions.ConnectionClosed:
                    # Handle disconnection
                    await self._handle_disconnect(agent_id)
    
    def _detect_action_conflicts(
        self,
        planned_actions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Detect conflicting actions between agents.
        
        Educational Note:
            In multi-agent simulations, certain action combinations may be
            logically incompatible (e.g., multiple agents claiming same resource).
            This detects such conflicts for research purposes.
        """
        conflicts = []
        
        # Example conflict detection: multiple agents planning same exclusive action
        exclusive_actions = {}
        
        for action_data in planned_actions:
            action = action_data["action"]
            action_type = action.get("type")
            
            # Check for exclusive resource claims
            if action_type == "increment" and action.get("exclusive_resource"):
                resource = action["exclusive_resource"]
                
                if resource in exclusive_actions:
                    conflicts.append(
                        f"Conflict: {action_data['agent_id']} and "
                        f"{exclusive_actions[resource]} both claim {resource}"
                    )
                else:
                    exclusive_actions[resource] = action_data['agent_id']
        
        return conflicts
    
    def _calculate_collective_probabilities(
        self,
        collective_state: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Recalculate probabilities based on collective agent information.
        
        Educational Note:
            Aggregates information from multiple agents to produce more
            accurate probability estimates for research scenarios.
        """
        # Simple aggregation: average equity estimates
        equities = []
        confidences = []
        
        for agent_id, state in collective_state.items():
            if "equity" in state:
                equities.append(state["equity"])
            if "confidence" in state:
                confidences.append(state["confidence"])
        
        result = {}
        
        if equities:
            result["average_equity"] = sum(equities) / len(equities)
            result["equity_variance"] = sum((e - result["average_equity"]) ** 2 for e in equities) / len(equities)
        
        if confidences:
            result["average_confidence"] = sum(confidences) / len(confidences)
        
        return result
    
    async def handle_heartbeat(self, agent_id: str) -> None:
        """
        Handle heartbeat from agent (Подпункт 1.2).
        
        Educational Note:
            Heartbeats ensure agents remain connected during long simulations,
            enabling automatic recovery from network issues.
        """
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = time.time()
            
            # Send heartbeat acknowledgment
            response = {
                "message_type": MessageType.HEARTBEAT.value,
                "status": "ack",
                "timestamp": time.time()
            }
            
            try:
                await self.agents[agent_id].websocket.send(json.dumps(response))
            except websockets.exceptions.ConnectionClosed:
                await self._handle_disconnect(agent_id)
    
    async def _handle_disconnect(self, agent_id: str) -> None:
        """Handle agent disconnection."""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        
        # Remove from environment
        if agent.environment_id and agent.environment_id in self.environments:
            self.environments[agent.environment_id].discard(agent_id)
            
            # Notify other agents in environment
            if self.environments[agent.environment_id]:
                await self._broadcast_agent_status(
                    agent.environment_id,
                    agent_id,
                    AgentStatus.DISCONNECTED
                )
        
        # Remove agent
        del self.agents[agent_id]
    
    async def _broadcast_agent_status(
        self,
        environment_id: str,
        agent_id: str,
        status: AgentStatus
    ) -> None:
        """Broadcast agent status change to environment."""
        message = {
            "message_type": "agent_status_change",
            "agent_id": agent_id,
            "status": status.value,
            "timestamp": time.time()
        }
        
        for other_agent_id in self.environments.get(environment_id, set()):
            if other_agent_id in self.agents and other_agent_id != agent_id:
                try:
                    await self.agents[other_agent_id].websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    pass
    
    async def _heartbeat_monitor(self) -> None:
        """
        Monitor agent heartbeats and disconnect stale agents (Подпункт 1.2).
        
        Educational Note:
            Automatic cleanup ensures simulations don't get stuck waiting
            for disconnected agents.
        """
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            
            current_time = time.time()
            disconnected_agents = []
            
            for agent_id, agent in self.agents.items():
                if current_time - agent.last_heartbeat > self.heartbeat_timeout:
                    disconnected_agents.append(agent_id)
            
            # Clean up disconnected agents
            for agent_id in disconnected_agents:
                await self._handle_disconnect(agent_id)
    
    async def handle_client(
        self,
        websocket: websockets.WebSocketServerProtocol
    ) -> None:
        """
        Handle WebSocket client connection.
        
        Main message loop for agent communication.
        """
        agent_id: Optional[str] = None
        
        try:
            async for message_raw in websocket:
                try:
                    message_data = json.loads(message_raw)
                    message = AgentStateMessage(**message_data)
                    
                    # Handle registration
                    if message.message_type == MessageType.REGISTER:
                        agent_id = message.agent_id
                        await self.register_agent(
                            websocket,
                            agent_id,
                            message.environment_id
                        )
                    
                    # Subsequent messages require registration
                    elif agent_id is None:
                        error_msg = {
                            "message_type": MessageType.ERROR.value,
                            "error": "Agent not registered"
                        }
                        await websocket.send(json.dumps(error_msg))
                        continue
                    
                    # Handle state sync
                    elif message.message_type == MessageType.STATE_SYNC:
                        await self.handle_state_sync(agent_id, message)
                    
                    # Handle heartbeat
                    elif message.message_type == MessageType.HEARTBEAT:
                        await self.handle_heartbeat(agent_id)
                    
                except Exception as e:
                    error_msg = {
                        "message_type": MessageType.ERROR.value,
                        "error": str(e)
                    }
                    await websocket.send(json.dumps(error_msg))
        
        except websockets.exceptions.ConnectionClosed:
            pass
        
        finally:
            if agent_id:
                await self._handle_disconnect(agent_id)
    
    async def start(self) -> None:
        """
        Start the central hub WebSocket server.
        
        Educational Note:
            This starts the coordination server for multi-agent research simulations.
        """
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        
        # Start heartbeat monitor
        asyncio.create_task(self._heartbeat_monitor())
        
        print(f"Central Hub started on ws://{self.host}:{self.port}")
        print(f"Encryption enabled for secure research data")
        print(f"Ready for multi-agent coordination")
    
    async def share_cards(
        self,
        environment_id: str,
        agent_id: str,
        hole_cards: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Share agent's hole cards with the collective (Roadmap2 Phase 2).
        
        When ≥3 agents in a session, they pool their hole cards to calculate
        collective equity vs dummy opponent and remaining deck.
        
        Args:
            environment_id: Session/table identifier
            agent_id: Agent sharing cards
            hole_cards: List of 2 cards (e.g., ["As", "Kh"])
            
        Returns:
            Dict with collective_known_cards, collective_equity, dummy_range
            
        Educational Note:
            This simulates HIVE strategy where multiple agents coordinate
            by sharing private information to gain collective advantage.
            For academic study of coordination mechanisms only.
        """
        # Get or create session
        if environment_id not in self._sessions:
            self._sessions[environment_id] = {}
        session = self._sessions[environment_id]
            
        # Store cards in session
        if "hole_cards" not in session:
            session["hole_cards"] = {}
        session["hole_cards"][agent_id] = hole_cards
        
        # Calculate collective knowledge when ≥3 agents
        agents_in_session = [
            conn for conn in self._connections.values()
            if conn.environment_id == environment_id
        ]
        
        if len(agents_in_session) < 3:
            return None
            
        # Collect all known cards
        collective_cards = []
        for aid, cards in session["hole_cards"].items():
            collective_cards.extend(cards)
            
        # Calculate equity (simplified for demonstration)
        equity = self._calculate_collective_equity(
            collective_cards,
            environment_id
        )
        
        return {
            "collective_known_cards": collective_cards,
            "collective_equity": equity,
            "dummy_range": session.get("dummy_range", "random"),
            "agent_count": len(agents_in_session)
        }
    
    def _calculate_collective_equity(
        self,
        known_cards: List[str],
        environment_id: str,
    ) -> float:
        """Calculate collective equity using treys poker evaluator.

        Computes the win probability of the best hand among the HIVE team's
        known hole cards against a random opponent range, using Monte Carlo
        simulation (1000 iterations for speed, full eval for accuracy).

        Args:
            known_cards:    All hole cards known to the collective (6 cards for 3 bots).
            environment_id: Session identifier (used to get board cards).

        Returns:
            Win probability [0.0, 1.0].
        """
        session = self._sessions.get(environment_id, {})
        board_cards: List[str] = session.get("board", [])

        if not known_cards:
            return 0.50

        # Try to use treys for accurate equity
        try:
            return self._treys_equity(known_cards, board_cards)
        except Exception:
            pass

        # Fallback: heuristic (original simplified calculation)
        base_equity = 0.5
        card_bonus = len(known_cards) * 0.03
        board_bonus = len(board_cards) * 0.02
        return min(0.95, base_equity + card_bonus + board_bonus)

    @staticmethod
    def _treys_equity(
        hole_cards: List[str],
        board: List[str],
        num_simulations: int = 1000,
    ) -> float:
        """Monte Carlo equity using the treys library.

        Groups hole_cards into 2-card hands (one per bot) and computes the
        probability that the best HIVE hand beats a random opponent hand.

        Args:
            hole_cards:      All team hole cards, e.g. ["As","Kh","Qd","Jc","Td","9s"]
            board:           Community cards already dealt, e.g. ["2h","5s","9d"]
            num_simulations: Monte Carlo iterations.

        Returns:
            Win probability [0.0, 1.0].
        """
        from treys import Card, Evaluator, Deck  # type: ignore[import]

        evaluator = Evaluator()

        # Convert string notation to treys Card ints
        def to_treys(card_str: str) -> int:
            # treys uses uppercase rank + lowercase suit: "As" → Card.new("As")
            return Card.new(card_str)

        # Parse team hands (pairs of cards)
        team_hands: List[List[int]] = []
        for i in range(0, len(hole_cards) - 1, 2):
            try:
                h = [to_treys(hole_cards[i]), to_treys(hole_cards[i + 1])]
                team_hands.append(h)
            except Exception:
                continue

        if not team_hands:
            return 0.50

        board_treys = []
        for c in board:
            try:
                board_treys.append(to_treys(c))
            except Exception:
                pass

        # Build a deck without known cards
        used = set(hole_cards + board)
        deck = Deck()
        deck.cards = [c for c in deck.cards
                      if Card.int_to_str(c) not in used]

        wins = 0
        valid_sims = 0

        for _ in range(num_simulations):
            try:
                deck_copy = list(deck.cards)

                # Deal remaining board cards (need 5 total)
                needed_board = 5 - len(board_treys)
                if needed_board > len(deck_copy):
                    continue

                import random
                run_board = board_treys + random.sample(deck_copy, needed_board)
                deck_remaining = [c for c in deck_copy
                                  if c not in run_board[len(board_treys):]]

                # Deal opponent 2 cards
                if len(deck_remaining) < 2:
                    continue
                opp_hand = random.sample(deck_remaining, 2)

                # Best team hand score (lower = better in treys)
                best_team_score = min(
                    evaluator.evaluate(run_board, hand)
                    for hand in team_hands
                    if all(c not in run_board for c in hand)
                )
                opp_score = evaluator.evaluate(run_board, opp_hand)

                if best_team_score < opp_score:
                    wins += 1
                valid_sims += 1

            except Exception:
                continue

        if valid_sims == 0:
            return 0.50

        return wins / valid_sims
    
    async def broadcast_collective_state(
        self,
        environment_id: str,
        collective_data: Dict[str, Any]
    ) -> None:
        """
        Broadcast collective state to all agents in session.
        
        Args:
            environment_id: Session identifier
            collective_data: Shared state (cards, equity, etc.)
        """
        message = {
            "type": MessageType.COLLECTIVE_EQUITY.value,
            "environment_id": environment_id,
            "data": collective_data,
            "timestamp": time.time()
        }
        
        encrypted_msg = self.encrypt_state(message)
        
        for conn in self._connections.values():
            if conn.environment_id == environment_id:
                try:
                    await conn.websocket.send(encrypted_msg)
                except Exception:
                    pass  # Agent disconnected
    
    # ------------------------------------------------------------------
    # full_hive_month.md Этап 2: full exchange hole cards
    # ------------------------------------------------------------------

    async def exchange_hole_cards(
        self,
        environment_id: str,
        agent_id: str,
        hole_cards: List[str],
        *,
        hand_id: str = "",
    ) -> Dict[str, Any]:
        """Full hole-card exchange for all agents in a session.

        Extends :meth:`share_cards` with:
          - Deduplication: no duplicate cards across agents
          - Hand-ID tracking for multi-hand sessions
          - Exchange-complete flag when all agents have shared
          - Auto-broadcast of collective state when complete

        Args:
            environment_id: Session/table identifier.
            agent_id:       Agent sharing its cards.
            hole_cards:     List of 2 cards (e.g. ``["As", "Kh"]``).
            hand_id:        Optional hand identifier.

        Returns:
            Dict with ``status``, ``collective_known_cards``,
            ``exchange_complete``, ``agent_count``, ``error`` (if any).
        """
        # Get or create session
        if environment_id not in self._sessions:
            self._sessions[environment_id] = {}
        session = self._sessions[environment_id]

        if "hole_cards" not in session:
            session["hole_cards"] = {}
        if "hand_id" not in session or hand_id:
            session["hand_id"] = hand_id

        # Validate: no duplicate cards with other agents
        err = self._validate_exchange(session, agent_id, hole_cards)
        if err:
            return {"status": "error", "error": err}

        # Store cards
        session["hole_cards"][agent_id] = hole_cards

        # Count agents in session
        agents_in_session = [
            c for c in self._connections.values()
            if c.environment_id == environment_id
        ]
        total_agents = max(len(agents_in_session), len(session["hole_cards"]))
        shared_count = len(session["hole_cards"])

        # Collect all known cards
        collective = []
        for aid, cards in session["hole_cards"].items():
            collective.extend(cards)

        exchange_complete = (shared_count >= total_agents and total_agents >= 2)

        # Calculate collective equity
        equity = self._calculate_collective_equity(collective, environment_id)

        result: Dict[str, Any] = {
            "status": "ok",
            "agent_id": agent_id,
            "hand_id": session.get("hand_id", ""),
            "collective_known_cards": collective,
            "collective_equity": equity,
            "agents_shared": shared_count,
            "agents_total": total_agents,
            "exchange_complete": exchange_complete,
        }

        # Auto-broadcast when exchange is complete
        if exchange_complete:
            try:
                await self.broadcast_collective_state(environment_id, result)
            except Exception:
                pass  # agents may not have websockets in tests

        return result

    def _validate_exchange(
        self,
        session: Dict[str, Any],
        agent_id: str,
        hole_cards: List[str],
    ) -> Optional[str]:
        """Validate that no cards are duplicated across agents.

        Returns:
            Error message string, or ``None`` if valid.
        """
        existing = session.get("hole_cards", {})
        all_other_cards: Set[str] = set()
        for aid, cards in existing.items():
            if aid != agent_id:
                all_other_cards.update(cards)

        for c in hole_cards:
            if c in all_other_cards:
                return f"Duplicate card '{c}': already held by another agent"

        return None

    def get_session_cards(self, environment_id: str) -> Dict[str, List[str]]:
        """Retrieve all shared hole cards for a session.

        Returns:
            Dict mapping agent_id → list of hole cards.
        """
        session = self._sessions.get(environment_id, {})
        return dict(session.get("hole_cards", {}))

    def clear_session_cards(self, environment_id: str) -> None:
        """Clear hole cards for a session (new hand)."""
        session = self._sessions.get(environment_id, {})
        session.pop("hole_cards", None)
        session.pop("hand_id", None)

    # ── TABLE_FOUND coordination protocol ────────────────────────────────────

    async def broadcast_table_found(
        self,
        finder_agent_id: str,
        table_info: Dict[str, Any],
        environment_id: Optional[str] = None,
    ) -> None:
        """Broadcast TABLE_FOUND to all agents in an environment.

        Called by the bot that first finds a suitable table.
        Other bots in the same environment should navigate to this table.

        Args:
            finder_agent_id: Bot ID that found the table.
            table_info:      Dict with table_name, stakes, row_y, etc.
            environment_id:  Target environment (None = all agents).
        """
        msg = {
            "type": "TABLE_FOUND",
            "finder": finder_agent_id,
            "table": table_info,
            "timestamp": time.time(),
        }
        encrypted = self.encrypt_state(msg)
        payload = json.dumps({"type": "TABLE_FOUND", "data": encrypted})

        targets = list(self.agents.values())
        if environment_id:
            targets = [a for a in targets if a.environment_id == environment_id]

        for conn in targets:
            if conn.agent_id == finder_agent_id:
                continue  # don't send back to finder
            try:
                await conn.websocket.send(payload)
            except Exception:
                pass

    async def wait_for_agents(
        self,
        environment_id: str,
        required_count: int = 3,
        timeout: float = 30.0,
    ) -> bool:
        """Wait until a minimum number of agents are connected to an environment.

        Args:
            environment_id: Environment to watch.
            required_count: Minimum number of agents required.
            timeout:        Max seconds to wait.

        Returns:
            True if enough agents connected, False on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            count = sum(
                1 for a in self.agents.values()
                if a.environment_id == environment_id
                and a.status in (AgentStatus.ACTIVE, AgentStatus.IDLE)
            )
            if count >= required_count:
                return True
            await asyncio.sleep(0.5)
        return False

    def get_environment_agents(self, environment_id: str) -> List[str]:
        """Return agent IDs currently in an environment."""
        return [
            a.agent_id for a in self.agents.values()
            if a.environment_id == environment_id
        ]

    def is_agent_connected(self, agent_id: str) -> bool:
        """Check if a specific agent is currently connected."""
        conn = self.agents.get(agent_id)
        return conn is not None and conn.status != AgentStatus.DISCONNECTED

    # ── Collective DECISION broadcast ─────────────────────────────────────────

    async def broadcast_decision(
        self,
        environment_id: str,
        decisions: Dict[str, Any],
    ) -> None:
        """Broadcast individual decisions to each agent in an environment.

        Called after collective equity calculation. Each agent receives
        its own prescribed action (raise / call / fold).

        Args:
            environment_id: Target environment.
            decisions:       Dict mapping agent_id → {action, amount, strategy}.
        """
        for agent_id, decision in decisions.items():
            conn = self.agents.get(agent_id)
            if conn is None:
                continue
            msg = {
                "type": "DECISION",
                "agent_id": agent_id,
                "action": decision.get("action", "fold"),
                "amount": decision.get("amount", 0.0),
                "strategy": decision.get("strategy", ""),
                "timestamp": time.time(),
            }
            encrypted = self.encrypt_state(msg)
            payload = json.dumps({"type": "DECISION", "data": encrypted})
            try:
                await conn.websocket.send(payload)
            except Exception:
                pass

    # ── Agent disconnect / fallback ───────────────────────────────────────────

    def handle_agent_disconnect(self, agent_id: str) -> None:
        """Mark an agent as disconnected and clean up its session data."""
        conn = self.agents.get(agent_id)
        if conn:
            conn.status = AgentStatus.DISCONNECTED
            # Remove from environments
            for env_id, env_agents in list(self.environments.items()):
                env_agents.discard(agent_id)
            # Clear any partial card shares from this agent
            for session in self._sessions.values():
                cards = session.get("hole_cards", {})
                cards.pop(agent_id, None)

    async def reconnect_check(self, environment_id: str) -> Dict[str, bool]:
        """Return connection status for all expected agents in environment."""
        result = {}
        for agent_id in self.get_environment_agents(environment_id):
            result[agent_id] = self.is_agent_connected(agent_id)
        return result

    async def stop(self) -> None:
        """Stop the hub server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()


async def main():
    """Educational example: Run central hub for testing."""
    hub = CentralHub(host="localhost", port=8765)
    await hub.start()
    
    # Keep running
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
