# API Reference: Hub & Decision Modules

> Internal API documentation for the Central Hub coordination system
> and the multi-agent Decision engine.
>
> ⚠️ **EDUCATIONAL RESEARCH ONLY.**

---

## Table of Contents

1. [Architecture Overview](#architecture)
2. [Central Hub API](#central-hub)
3. [Hub Client API](#hub-client)
4. [External Hub Client API](#external-hub-client)
5. [Decision Engine API](#decision-engine)
6. [Collective Decision API](#collective-decision)
7. [WebSocket Protocol](#websocket-protocol)
8. [Data Models](#data-models)
9. [Integration Examples](#examples)
10. [Auto-generated Docs (pdoc)](#pdoc)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CentralHub                                │
│  sim_engine/central_hub.py                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ WebSocket    │  │ Encryption   │  │ State Synchronization │  │
│  │ Server       │  │ (Fernet)     │  │ + Conflict Detection  │  │
│  └──────┬──────┘  └──────────────┘  └───────────────────────┘  │
│         │                                                        │
│    ws://host:port                                                │
└─────────┬───────────────────────────────────────────────────────┘
          │
    ┌─────┴─────────────────────┐
    │                           │
┌───▼──────────┐     ┌─────────▼──────────┐
│  HubClient   │     │ ExternalHubClient  │
│  (sim_engine │     │ (bridge module)    │
│  /hub_client)│     │ /external_hub_     │
│              │     │  client)           │
└───┬──────────┘     └──────┬─────────────┘
    │                       │
    ▼                       ▼
┌──────────────┐     ┌────────────────────┐
│ Decision     │     │ CollectiveDecision │
│ Engine       │     │ Engine             │
│ (sim_engine  │     │ (sim_engine        │
│ /decision)   │     │ /collective_       │
│              │     │  decision)         │
└──────────────┘     └────────────────────┘
```

---

## Central Hub API

**Module:** `sim_engine.central_hub`

The `CentralHub` is a WebSocket-based coordination server for multi-agent
simulations.

### CentralHub

```python
class CentralHub:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        encryption_key: Optional[bytes] = None,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0,
    )
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | `"localhost"` | Host to bind WebSocket server |
| `port` | `int` | `8765` | Port for WebSocket server |
| `encryption_key` | `bytes \| None` | `None` | Fernet key (auto-generated if None) |
| `heartbeat_interval` | `float` | `30.0` | Seconds between heartbeat checks |
| `heartbeat_timeout` | `float` | `90.0` | Seconds before disconnect |

### Methods

#### `start() → None` (async)

Start the WebSocket server and heartbeat monitor.

```python
hub = CentralHub(host="localhost", port=8765)
await hub.start()
# Hub is now accepting connections at ws://localhost:8765
```

#### `stop() → None` (async)

Gracefully shut down the hub server.

```python
await hub.stop()
```

#### `register_agent(websocket, agent_id, environment_id) → None` (async)

Register a new agent connection.

| Parameter | Type | Description |
|---|---|---|
| `websocket` | `WebSocketServerProtocol` | WebSocket connection |
| `agent_id` | `str` | Unique agent identifier |
| `environment_id` | `str \| None` | Environment/table group |

#### `handle_state_sync(agent_id, message) → None` (async)

Process state synchronization request. When 2+ agents share an environment,
broadcasts collective state to all members.

| Parameter | Type | Description |
|---|---|---|
| `agent_id` | `str` | Sending agent's ID |
| `message` | `AgentStateMessage` | State data + metadata |

**Sync logic:**
1. Update agent's stored state
2. If ≥2 agents in environment → aggregate collective state
3. Detect conflicting actions
4. Calculate collective probabilities
5. Broadcast sync message to all agents

#### `share_cards(environment_id, agent_id, hole_cards) → Dict | None` (async)

Share agent's hole cards with the HIVE collective.

| Parameter | Type | Description |
|---|---|---|
| `environment_id` | `str` | Session/table ID |
| `agent_id` | `str` | Agent sharing cards |
| `hole_cards` | `List[str]` | Cards, e.g. `["As", "Kh"]` |

**Returns:** `None` if < 3 agents, otherwise:

```python
{
    "collective_known_cards": ["As", "Kh", "Qd", "Jc", "Ts", "9h"],
    "collective_equity": 0.68,
    "dummy_range": "random",
    "agent_count": 3
}
```

#### `encrypt_state(state_data) → str`

Encrypt state dictionary with Fernet for secure transmission.

#### `decrypt_state(encrypted_data) → Dict`

Decrypt received state data.

#### `broadcast_collective_state(environment_id, collective_data) → None` (async)

Send encrypted collective state to all agents in an environment.

### Properties

| Property | Type | Description |
|---|---|---|
| `agents` | `Dict[str, AgentConnection]` | Connected agents |
| `environments` | `Dict[str, Set[str]]` | Environment → agent groups |
| `encryption_key` | `bytes` | Fernet encryption key |

---

## Hub Client API

**Module:** `sim_engine.hub_client`

WebSocket client for connecting agents to the Central Hub.

### HubConfig

```python
@dataclass
class HubConfig:
    enabled: bool = False
    hub_url: str = "ws://localhost:8765"
    agent_id: Optional[str] = None
    environment_id: str = "research_env_1"
    timeout: float = 5.0
    heartbeat_interval: float = 30.0
```

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | `bool` | `False` | Enable hub connectivity |
| `hub_url` | `str` | `"ws://localhost:8765"` | Hub server URL |
| `agent_id` | `str \| None` | `None` | Agent identifier |
| `environment_id` | `str` | `"research_env_1"` | Environment group |
| `timeout` | `float` | `5.0` | Connection timeout (seconds) |
| `heartbeat_interval` | `float` | `30.0` | Heartbeat interval (seconds) |

### HubClient

```python
class HubClient:
    def __init__(self, config: HubConfig)
```

#### `connect() → bool` (async)

Connect to hub, register agent, start heartbeat.

```python
config = HubConfig(enabled=True, agent_id="bot_1")
client = HubClient(config)
connected = await client.connect()
```

#### `sync_state(state_data) → Dict | None` (async)

Send state to hub and receive synchronized collective state.

```python
result = await client.sync_state({
    "equity": 0.65,
    "planned_action": {"type": "increment", "sizing": 4.5}
})
```

#### `send_heartbeat() → None` (async)

Send manual heartbeat (automatic heartbeat runs in background).

#### `disconnect() → None` (async)

Gracefully disconnect from hub.

---

## External Hub Client API

**Module:** `bridge.external_hub_client`

Connects bridge instances to the Central Hub for cross-process coordination.

### HubConnection

```python
@dataclass
class HubConnection:
    hub_url: str
    agent_id: str
    environment_id: str
    connected: bool = False
    encryption_key: Optional[bytes] = None
    websocket: Optional[Any] = None
```

### ExternalHubClient

Inherits similar interface to `HubClient` but integrated with Bridge's
`SafetyFramework` and `BotIdentityManager`.

**Key difference:** Uses `bridge.bot_identification` for agent IDs and
`bridge.safety` for safety checks before forwarding decisions.

---

## Decision Engine API

**Module:** `sim_engine.decision`

The core decision engine for individual agents.

### SimulatedActionType (Enum)

| Value | Poker Mapping | Description |
|---|---|---|
| `INCREMENT` | bet / raise | Aggressive: increase commitment |
| `HOLD` | call | Defensive: maintain commitment |
| `DECREMENT` | fold | Exit: reduce to zero |
| `CHECK` | check | Neutral: no change |

### LineType (Enum)

| Value | Description | Equity Trigger |
|---|---|---|
| `PROACTIVE` | Initiative-taking, aggressive | ≥ 60% equity |
| `REACTIVE` | Defensive, responsive | 42%–60% equity |
| `EXPLOITATIVE` | Opponent-specific adaptation | 30%–42% with opponent data |
| `BALANCED` | Mixed strategy | Default fallback |

### SimulationDecision

```python
@dataclass
class SimulationDecision:
    action: SimulatedActionType
    sizing: float | None
    confidence: float        # 0.0–1.0
    equity: float            # 0.0–1.0
    line_type: LineType
    reasoning: dict[str, Any]
```

**Validation rules:**
- `confidence` must be in [0, 1]
- `equity` must be in [0, 1]
- `sizing` cannot be negative
- `INCREMENT` requires non-None sizing
- `DECREMENT` / `CHECK` must have sizing = None or 0

### AgentContext

```python
@dataclass
class AgentContext:
    position: Position | str           # Agent's seat position
    resource_bucket: str               # "high" / "medium" / "low"
    opponent_models: dict[str, dict]   # opponent_id → stats
    session_state: dict[str, Any]      # session metrics
```

### generate_simulated_decision()

Main decision function. Combines Range Model v0, Monte Carlo equity,
and strategic line logic.

```python
def generate_simulated_decision(
    agent_state: list[str],       # Hero's hole cards ["Ah", "Ks"]
    environment: list[str],       # Board cards ["Ad", "7c", "2s"]
    street: Street,               # PREFLOP / FLOP / TURN / RIVER
    pot_bb: float,                # Current pot in big blinds
    to_call_bb: float,            # Amount to call in BB
    context: AgentContext,        # Position, opponents, session
    *,
    use_monte_carlo: bool = True,
    num_simulations: int = 1000,
    probability_threshold: float = 0.6,
) -> SimulationDecision
```

**Algorithm:**

1. **Estimate opponent range** — from opponent models (VPIP/PFR) or defaults
2. **Calculate equity** — Monte Carlo (1000 sims) or heuristic fallback
3. **Determine line** — Proactive / Reactive / Exploitative / Balanced
4. **Select action** — based on equity vs pot odds + line type
5. **Calculate sizing** — 33%–150% pot based on line + street

**Example:**

```python
from sim_engine.decision import generate_simulated_decision, AgentContext
from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position

context = AgentContext(
    position=Position.BTN,
    resource_bucket="high",
    opponent_models={"villain1": {"vpip": 0.28, "pfr": 0.22}},
    session_state={"hands_played": 50, "bb_won": 15.5},
)

decision = generate_simulated_decision(
    agent_state=["Ah", "Ks"],
    environment=["Ad", "7c", "2s"],
    street=Street.FLOP,
    pot_bb=12.0,
    to_call_bb=0.0,
    context=context,
)

print(decision.action)      # SimulatedActionType.INCREMENT
print(decision.sizing)      # 8.16 (68% pot)
print(decision.confidence)  # 0.85
print(decision.equity)      # 0.72
print(decision.line_type)   # LineType.PROACTIVE
print(decision.reasoning)   # {"equity_source": "monte_carlo", ...}
```

### Sizing Table

| Line Type | Equity | Street | Sizing Range |
|---|---|---|---|
| Proactive | ≥ 75% | Flop | 85–100% pot |
| Proactive | 60–75% | Flop | 60–75% pot |
| Reactive | Any | Any | 40–60% pot |
| Exploitative | Any | Any | 50–70% pot |
| Balanced | Any | Any | 50–70% pot |

Street multipliers: Preflop ×1.0, Flop ×1.0, Turn ×1.15, River ×1.25.

---

## Collective Decision API

**Module:** `sim_engine.collective_decision`

HIVE group decision-making based on pooled information.

### CollectiveState

```python
@dataclass
class CollectiveState:
    collective_cards: List[str]    # All known hole cards
    collective_equity: float       # Group win probability
    agent_count: int               # Number of HIVE agents
    pot_size: float = 0.0          # Current pot (BB)
    stack_sizes: Dict[str, float]  # agent_id → stack
    board: List[str] = []          # Community cards
    dummy_range: str = "random"    # Opponent range estimate
```

### CollectiveDecision

```python
@dataclass
class CollectiveDecision:
    action: ActionType        # FOLD / CHECK / CALL / BET / RAISE / ALL_IN
    line_type: LineType       # AGGRESSIVE / PROTECTIVE / PASSIVE
    bet_size: Optional[float] # Size in BB or pot fraction
    reasoning: str            # Decision explanation
    confidence: float         # 0.0–1.0
```

### CollectiveDecisionEngine

```python
class CollectiveDecisionEngine:
    def __init__(
        self,
        aggressive_threshold: float = 0.65,
        protective_threshold: float = 0.45,
        enable_full_collusion: bool = False,
    )
```

| Parameter | Default | Description |
|---|---|---|
| `aggressive_threshold` | `0.65` | Equity for aggressive line |
| `protective_threshold` | `0.45` | Min equity for protective line |
| `enable_full_collusion` | `False` | Full card sharing mode |

#### `decide(state: CollectiveState) → CollectiveDecision`

Core decision method.

**Decision logic:**
- `equity ≥ 0.65` → **Aggressive**: BET/RAISE/ALL_IN
- `0.45 ≤ equity < 0.65` → **Protective**: CHECK/CALL
- `equity < 0.45` → **Passive**: FOLD

```python
from sim_engine.collective_decision import (
    CollectiveDecisionEngine,
    CollectiveState,
)

engine = CollectiveDecisionEngine(aggressive_threshold=0.65)

state = CollectiveState(
    collective_cards=["As", "Kh", "Qd", "Jc", "Ts", "9h"],
    collective_equity=0.72,
    agent_count=3,
    pot_size=24.0,
    board=["Ad", "7c", "2s"],
)

decision = engine.decide(state)
print(decision.action)     # ActionType.RAISE
print(decision.line_type)  # LineType.AGGRESSIVE
print(decision.bet_size)   # 16.8 (70% pot)
print(decision.confidence) # 0.82
```

---

## WebSocket Protocol

### Message Format

All messages are JSON objects with a `message_type` field.

### Message Types

| Type | Direction | Description |
|---|---|---|
| `register` | Client → Hub | Agent registration |
| `state_sync` | Bidirectional | State synchronization |
| `decision_request` | Client → Hub | Request collective decision |
| `decision_response` | Hub → Client | Collective decision result |
| `heartbeat` | Bidirectional | Keep-alive ping/pong |
| `card_share` | Client → Hub | Share hole cards |
| `collective_equity` | Hub → Client | Broadcast collective equity |
| `error` | Hub → Client | Error notification |

### Registration Flow

```
Client                          Hub
  │                              │
  │── register ─────────────────►│
  │   {agent_id, environment_id} │
  │                              │
  │◄── register response ───────│
  │   {status, encryption_key,   │
  │    agents_in_environment}    │
```

### State Sync Flow

```
Client A                  Hub                   Client B
  │                        │                        │
  │── state_sync ─────────►│                        │
  │   {equity: 0.65,       │                        │
  │    planned_action}     │                        │
  │                        │── state_sync ─────────►│
  │                        │   {collective_probs,   │
  │◄── state_sync ────────│    conflicts, count}   │
  │   {collective_probs,   │                        │
  │    conflicts, count}   │                        │
```

### Card Sharing Flow

```
Agent 1        Agent 2        Agent 3        Hub
  │              │              │              │
  │── card_share ─────────────────────────────►│
  │  ["As","Kh"] │              │              │
  │              │── card_share ──────────────►│
  │              │  ["Qd","Jc"] │              │
  │              │              │── card_share►│
  │              │              │  ["Ts","9h"] │
  │              │              │              │
  │◄── collective_equity ─────────────────────│
  │  {cards: 6,  │              │     equity:  │
  │   eq: 0.72}  │              │     0.72     │
  │              │◄── collective_equity ───────│
  │              │              │◄── coll_eq ──│
```

### Heartbeat

```
Client                          Hub
  │                              │
  │── heartbeat ────────────────►│
  │   {agent_id}                 │
  │                              │
  │◄── heartbeat ack ───────────│
  │   {status: "ack", ts}       │
```

Timeout: Agent disconnected after 90s without heartbeat.

---

## Data Models

### AgentStateMessage (Pydantic)

```python
class AgentStateMessage(BaseModel):
    agent_id: str               # Min length 1
    message_type: MessageType   # Enum
    timestamp: float            # Auto-set to time.time()
    state_data: Dict[str, Any]  # Encrypted in transit
    environment_id: Optional[str]
    requires_sync: bool = False
```

### AgentConnection

```python
@dataclass
class AgentConnection:
    agent_id: str
    websocket: WebSocketServerProtocol
    status: AgentStatus          # CONNECTED / ACTIVE / IDLE / DISCONNECTED
    environment_id: Optional[str]
    last_heartbeat: float
    state_data: Dict[str, Any]
```

### ActionType (Collective)

```python
class ActionType(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
```

### LineType (Collective)

```python
class LineType(str, Enum):
    AGGRESSIVE = "aggressive"    # equity ≥ 65%
    PROTECTIVE = "protective"    # 45% ≤ equity < 65%
    PASSIVE = "passive"          # equity < 45%
```

---

## Integration Examples

### Full Hub + Decision Pipeline

```python
import asyncio
from sim_engine.central_hub import CentralHub
from sim_engine.hub_client import HubClient, HubConfig
from sim_engine.decision import generate_simulated_decision, AgentContext
from sim_engine.collective_decision import CollectiveDecisionEngine, CollectiveState
from coach_app.schemas.common import Street

async def run_simulation():
    # 1. Start hub
    hub = CentralHub(host="localhost", port=8765)
    await hub.start()

    # 2. Connect agents
    configs = [
        HubConfig(enabled=True, agent_id=f"bot_{i}", environment_id="table_1")
        for i in range(3)
    ]
    clients = [HubClient(cfg) for cfg in configs]
    for client in clients:
        await client.connect()

    # 3. Each agent generates individual decision
    context = AgentContext(
        position="BTN",
        resource_bucket="high",
        opponent_models={},
        session_state={},
    )

    decisions = []
    for i, client in enumerate(clients):
        decision = generate_simulated_decision(
            agent_state=["Ah", "Ks"],
            environment=["Ad", "7c", "2s"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
        )
        decisions.append(decision)

        # Sync state with hub
        await client.sync_state({
            "equity": decision.equity,
            "planned_action": {"type": decision.action.value},
        })

    # 4. Share cards for collective decision
    cards_sets = [["As", "Kh"], ["Qd", "Jc"], ["Ts", "9h"]]
    for i, cards in enumerate(cards_sets):
        result = await hub.share_cards("table_1", f"bot_{i}", cards)

    # 5. Collective decision
    engine = CollectiveDecisionEngine()
    collective_state = CollectiveState(
        collective_cards=["As", "Kh", "Qd", "Jc", "Ts", "9h"],
        collective_equity=result["collective_equity"],
        agent_count=3,
        pot_size=12.0,
        board=["Ad", "7c", "2s"],
    )
    collective = engine.decide(collective_state)
    print(f"Collective: {collective.action} ({collective.line_type})")

    # 6. Cleanup
    for client in clients:
        await client.disconnect()
    await hub.stop()

asyncio.run(run_simulation())
```

### Bridge Integration

```python
from bridge.external_hub_client import ExternalHubClient, HubConnection

conn = HubConnection(
    hub_url="ws://192.168.1.100:8765",
    agent_id="bridge_bot_1",
    environment_id="table_nl50",
)
client = ExternalHubClient(conn)
await client.connect()

# Share state from bridge's vision pipeline
await client.sync_state({
    "hero_cards": ["Ah", "Ks"],
    "board": ["Ad", "7c", "2s"],
    "pot": 12.0,
    "equity": 0.72,
})
```

---

## Auto-generated Docs (pdoc)

API docs can be auto-generated using `pdoc`:

### Generate HTML docs

```bash
# Hub module
pdoc sim_engine.central_hub sim_engine.hub_client -o docs/html/hub/

# Decision module
pdoc sim_engine.decision sim_engine.collective_decision -o docs/html/decision/

# All sim_engine modules
pdoc sim_engine -o docs/html/sim_engine/

# Launcher modules
pdoc launcher.structured_logger launcher.log_storage launcher.telegram_alerts -o docs/html/launcher/
pdoc launcher.bot_profile_manager launcher.bot_config_loader launcher.ab_testing -o docs/html/launcher/
```

### Live preview

```bash
pdoc sim_engine.central_hub sim_engine.decision --port 8080
# Open http://localhost:8080 in browser
```

### Generate Markdown

```bash
pdoc sim_engine.central_hub -d markdown > docs/generated/central_hub.md
```

> **Note:** Some modules (e.g., `launcher.vision`) may fail to generate docs
> if optional dependencies (torch, PyQt6) are not installed. Use the
> individual module commands above to skip problematic imports.
