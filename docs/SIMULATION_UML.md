# Multi-Agent Simulation Framework - UML Diagrams
## Architecture Flow and Component Interactions

**Version:** 1.0  
**Date:** 2026-02-05  
**Companion Document:** SIMULATION_SPEC.md

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "Simulation Orchestrator Layer"
        Orch[Simulation Orchestrator]
        Config[Configuration Manager]
        Metrics[Metrics Collector]
    end
    
    subgraph "Agent Layer"
        A1[Agent 1]
        A2[Agent 2]
        AN[Agent N]
    end
    
    subgraph "Central Hub Layer"
        Hub[Central Hub<br/>WebSocket Server]
        Redis[(Redis<br/>State Cache)]
        Queue[Event Queue]
    end
    
    subgraph "Decision Engine Layer"
        Decision[Decision Engine]
        Range[Range Model v0]
        Lines[Postflop Lines v2]
        Equity[Equity Calculator<br/>Monte Carlo]
    end
    
    subgraph "Vision/Input Layer"
        Vision[Vision Adapter]
        YOLO[YOLO Detector]
        OCR[Tesseract OCR]
        Fallback[Fallback Models]
    end
    
    subgraph "Virtual Environment Layer"
        Table1[Virtual Table 1]
        Table2[Virtual Table 2]
        TableN[Virtual Table N]
    end
    
    Orch --> Config
    Orch --> Metrics
    Orch --> A1
    Orch --> A2
    Orch --> AN
    
    A1 <--> Hub
    A2 <--> Hub
    AN <--> Hub
    
    Hub <--> Redis
    Hub --> Queue
    
    A1 --> Decision
    Decision --> Range
    Decision --> Lines
    Decision --> Equity
    
    A1 --> Vision
    Vision --> YOLO
    Vision --> OCR
    Vision --> Fallback
    
    A1 --> Table1
    A2 --> Table2
    AN --> TableN
    
    Vision --> Table1
    Vision --> Table2
    Vision --> TableN
    
    style Hub fill:#4a90e2,color:#fff
    style Decision fill:#50c878,color:#fff
    style Orch fill:#ff6b6b,color:#fff
```

---

## 2. Agent Lifecycle Sequence

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Agent as Agent
    participant Hub as Central Hub
    participant Vision as Vision Adapter
    participant Engine as Decision Engine
    participant Table as Virtual Table
    
    Orch->>Agent: launch(profile="human_like")
    Agent->>Agent: initialize(config)
    Agent->>Hub: connect_websocket()
    Hub-->>Agent: connection_established
    
    Agent->>Vision: discover_tables()
    Vision-->>Agent: available_tables[]
    
    Agent->>Table: join_table(table_id)
    Table-->>Agent: seat_assigned(seat=2)
    
    Agent->>Hub: subscribe(table_id)
    Hub-->>Agent: subscription_confirmed
    
    loop Every Hand
        Vision->>Table: capture_screenshot()
        Table-->>Vision: screenshot
        Vision->>Vision: extract_state()
        Vision-->>Agent: game_state
        
        Agent->>Hub: sync_state(state)
        Hub->>Hub: validate_state()
        Hub-->>Agent: canonical_state
        
        Agent->>Engine: calculate_decision(state)
        Engine->>Engine: estimate_equity()
        Engine->>Engine: select_line()
        Engine-->>Agent: decision + reasoning
        
        Agent->>Agent: apply_variance()
        Agent->>Agent: wait_timing_delay()
        
        Agent->>Table: execute_action(action)
        Table-->>Agent: action_confirmed
        
        Agent->>Hub: broadcast_action(action)
        Hub-->>Agent: state_updated
    end
    
    Agent->>Table: leave_table()
    Agent->>Hub: disconnect()
    Orch->>Agent: shutdown()
```

---

## 3. State Synchronization Flow

```mermaid
sequenceDiagram
    participant A1 as Agent 1
    participant A2 as Agent 2
    participant Hub as Central Hub
    participant Redis as Redis Cache
    
    Note over A1,Redis: Agent 1 observes state change
    
    A1->>Hub: sync_request(state_v42)
    Hub->>Redis: get_canonical_state(table_id)
    Redis-->>Hub: canonical_state_v42
    
    Hub->>Hub: compare_states()
    
    alt States Match
        Hub->>Redis: update_state(merged_v43)
        Hub->>A1: sync_ok(canonical_v43)
        Hub->>A2: broadcast(state_update_v43)
        A2->>A2: update_local_state()
    else Conflict Detected
        Hub->>Hub: resolve_conflict()
        Hub->>A1: sync_error(conflicts)
        A1->>A1: request_full_sync()
        A1->>Hub: sync_request(full)
        Hub-->>A1: canonical_state_v43
    end
    
    Note over A1,Redis: Both agents now have v43
```

---

## 4. Decision Engine Component Diagram

```mermaid
graph LR
    subgraph "Decision Engine Core"
        Input[Game State Input]
        Preflop[Preflop Module]
        Postflop[Postflop Module]
        Output[Decision Output]
    end
    
    subgraph "Range Model v0"
        RangePresets[Range Presets]
        RangeCalc[Range Calculator]
        RangeWeight[Weight Normalization]
    end
    
    subgraph "Postflop Line Logic v2"
        HandCat[Hand Categorization]
        BoardTex[Board Texture Analysis]
        LineSelect[Line Selection]
        Sizing[Sizing Heuristic]
    end
    
    subgraph "Equity & Probability"
        MC[Monte Carlo Simulator]
        Heuristic[Deterministic Heuristic]
        Cache[Equity Cache]
    end
    
    Input --> Preflop
    Input --> Postflop
    
    Preflop --> RangePresets
    RangePresets --> RangeCalc
    RangeCalc --> RangeWeight
    RangeWeight --> Output
    
    Postflop --> HandCat
    Postflop --> BoardTex
    HandCat --> LineSelect
    BoardTex --> LineSelect
    LineSelect --> Sizing
    Sizing --> Output
    
    Postflop --> MC
    Postflop --> Heuristic
    MC --> Cache
    Heuristic --> Cache
    Cache --> Output
    
    style Input fill:#e3f2fd
    style Output fill:#c8e6c9
    style MC fill:#fff3e0
```

---

## 5. Conflict Resolution State Machine

```mermaid
stateDiagram-v2
    [*] --> Listening: Agent connected
    
    Listening --> ActionRequested: Agent wants to act
    ActionRequested --> CheckingConflicts: Submit to hub
    
    CheckingConflicts --> NoConflict: Only action in window
    CheckingConflicts --> ConflictDetected: Multiple actions
    
    NoConflict --> ActionApproved: Proceed
    
    ConflictDetected --> TimestampCheck: Compare timestamps
    TimestampCheck --> EarlierWins: Time diff > 100ms
    TimestampCheck --> SeatPriority: Time diff < 100ms
    
    SeatPriority --> ApplyPriority: Use seat order
    ApplyPriority --> ActionApproved: Winner selected
    
    EarlierWins --> ActionApproved: Winner selected
    
    ActionApproved --> BroadcastUpdate: Notify all agents
    BroadcastUpdate --> Listening: Return to listening
    
    ActionApproved --> [*]: Action completed
```

---

## 6. Vision Input Pipeline

```mermaid
graph TB
    subgraph "Capture Layer"
        Screen[Screenshot Capture<br/>MSS/PyAutoGUI]
    end
    
    subgraph "ROI Detection"
        AutoROI[Auto ROI Detection]
        Cache[ROI Cache]
        Calibrate[Re-calibration]
    end
    
    subgraph "Primary Extraction"
        YOLO[YOLO Card Detection]
        OCR[Tesseract OCR<br/>Numbers/Text]
        Template[Template Matching<br/>UI Elements]
    end
    
    subgraph "Fallback Chain"
        Secondary[Secondary YOLO Model]
        Heuristic[Heuristic Extraction]
        Manual[Manual Override]
    end
    
    subgraph "Validation"
        Confidence[Confidence Scoring]
        Sanitize[Data Sanitization]
        Format[State Formatting]
    end
    
    subgraph "Output"
        State[Game State Object]
        Metadata[Confidence Metadata]
    end
    
    Screen --> AutoROI
    AutoROI --> Cache
    AutoROI --> YOLO
    AutoROI --> OCR
    AutoROI --> Template
    
    Cache -.-> Calibrate
    Calibrate -.-> AutoROI
    
    YOLO --> Confidence
    OCR --> Confidence
    Template --> Confidence
    
    Confidence -->|conf < 0.7| Secondary
    Secondary -->|still low| Heuristic
    Heuristic -->|failed| Manual
    
    Confidence -->|conf >= 0.7| Sanitize
    Sanitize --> Format
    Format --> State
    Format --> Metadata
    
    style Confidence fill:#ffeb3b
    style State fill:#4caf50,color:#fff
```

---

## 7. Variance Model Application Flow

```mermaid
flowchart TD
    Start([Decision from Engine]) --> Profile{Agent Profile?}
    
    Profile -->|Conservative| Conservative[Conservative Model]
    Profile -->|Aggressive| Aggressive[Aggressive Model]
    Profile -->|Adaptive| Adaptive[Adaptive Model]
    
    Conservative --> TightenThresh[Tighten Thresholds<br/>+5% equity required]
    Aggressive --> LoosenThresh[Loosen Thresholds<br/>-5% equity required]
    Adaptive --> CheckSession[Check Session Results]
    
    CheckSession --> Tilting{Losing Session?}
    Tilting -->|Yes| MoreAggr[Increase Aggression<br/>Tilt Mode]
    Tilting -->|No| OpponentAdj[Opponent Exploitation]
    
    TightenThresh --> ActionRand[Apply Action Randomness]
    LoosenThresh --> ActionRand
    MoreAggr --> ActionRand
    OpponentAdj --> ActionRand
    
    ActionRand --> RandomRoll{Random < threshold?}
    RandomRoll -->|Yes| SubOptimal[Choose Alternative Action]
    RandomRoll -->|No| Optimal[Keep Optimal Action]
    
    SubOptimal --> Timing[Calculate Timing Delay]
    Optimal --> Timing
    
    Timing --> Complexity{Decision Complexity?}
    Complexity -->|Trivial| Short[0.1-0.5s]
    Complexity -->|Simple| Medium[0.5-1.5s]
    Complexity -->|Complex| Long[1.5-3.0s]
    
    Short --> Jitter[Add Random Jitter]
    Medium --> Jitter
    Long --> Jitter
    
    Jitter --> Wait[Wait Delay]
    Wait --> Execute([Execute Action])
    
    style Start fill:#e1f5fe
    style Execute fill:#c8e6c9
    style RandomRoll fill:#fff9c4
    style Tilting fill:#ffccbc
```

---

## 8. Multi-Agent Orchestration Architecture

```mermaid
graph TB
    subgraph "Orchestrator Core"
        Main[Main Controller]
        Scheduler[Agent Scheduler]
        Monitor[Health Monitor]
        Logger[Event Logger]
    end
    
    subgraph "Agent Pool"
        direction LR
        Pool[Agent Pool Manager]
        A1[Agent 1]
        A2[Agent 2]
        A3[Agent 3]
        AN[Agent N]
    end
    
    subgraph "Environment Manager"
        Scanner[Table Scanner]
        Assign[Seat Assignment]
        Tracker[Session Tracker]
    end
    
    subgraph "Metrics & Monitoring"
        Prometheus[Prometheus Exporter]
        Grafana[Grafana Dashboard]
        Alerts[Alert Manager]
    end
    
    subgraph "Deployment"
        Docker[Docker Containers]
        K8s[Kubernetes Pods]
        Cloud[Cloud Instances]
    end
    
    Main --> Scheduler
    Main --> Monitor
    Main --> Logger
    
    Scheduler --> Pool
    Pool --> A1
    Pool --> A2
    Pool --> A3
    Pool --> AN
    
    Scanner --> Assign
    Assign --> Tracker
    
    A1 --> Scanner
    A2 --> Scanner
    AN --> Scanner
    
    Monitor --> Prometheus
    Prometheus --> Grafana
    Grafana --> Alerts
    
    Main --> Docker
    Docker --> K8s
    K8s --> Cloud
    
    style Main fill:#ff6b6b,color:#fff
    style Prometheus fill:#e76e55,color:#fff
    style Docker fill:#0db7ed,color:#fff
```

---

## 9. WebSocket Communication Protocol

```mermaid
sequenceDiagram
    participant Agent
    participant WS as WebSocket Client
    participant Hub as Central Hub
    participant Redis
    
    Agent->>WS: connect(hub_url)
    WS->>Hub: TLS handshake
    Hub-->>WS: connection_accepted
    
    loop Heartbeat Every 30s
        WS->>Hub: heartbeat
        Hub-->>WS: heartbeat_ack
    end
    
    Agent->>WS: subscribe(table_id)
    WS->>Hub: {type: "subscribe", table_id: "042"}
    Hub->>Redis: add_subscriber(agent, table)
    Hub-->>WS: subscription_confirmed
    
    Note over Agent,Redis: Agent ready to receive events
    
    Hub->>Redis: get_table_subscribers("042")
    Redis-->>Hub: [agent_007, agent_012]
    
    Hub->>WS: broadcast(state_update)
    WS-->>Agent: on_message(state_update)
    Agent->>Agent: handle_state_update()
    
    Agent->>WS: send(action_intent)
    WS->>Hub: {type: "action_request", ...}
    Hub->>Hub: check_conflicts()
    Hub-->>WS: action_approved
    WS-->>Agent: on_message(approved)
    
    alt Connection Lost
        WS->>WS: detect_disconnect()
        WS->>WS: exponential_backoff()
        WS->>Hub: reconnect()
        Hub-->>WS: reconnection_success
        WS->>Agent: notify_reconnected()
    end
    
    Agent->>WS: disconnect()
    WS->>Hub: close_connection
    Hub->>Redis: remove_subscriber()
```

---

## 10. Data Flow: Vision Input → Coordinated Action

```mermaid
flowchart LR
    subgraph "Input Stage"
        V1[Virtual Table<br/>Screenshot]
        V2[Vision Adapter]
        V3[State Extraction]
    end
    
    subgraph "Synchronization Stage"
        S1[Agent Local State]
        S2[Central Hub]
        S3[Canonical State]
        S4[Conflict Check]
    end
    
    subgraph "Decision Stage"
        D1[Opponent Models]
        D2[Decision Engine]
        D3[Equity Calculation]
        D4[Line Selection]
    end
    
    subgraph "Coordination Stage"
        C1[Action Intent]
        C2[Hub Validation]
        C3[Multi-Agent Sync]
        C4[Approval]
    end
    
    subgraph "Execution Stage"
        E1[Variance Applied]
        E2[Timing Delay]
        E3[Action Execution]
        E4[Confirmation]
    end
    
    V1 --> V2 --> V3 --> S1
    
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 -->|OK| D1
    S4 -->|Conflict| S2
    
    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> C1
    
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 -->|Approved| E1
    C4 -->|Denied| C1
    
    E1 --> E2 --> E3 --> E4
    
    E4 --> S2
    
    style V1 fill:#e3f2fd
    style S3 fill:#fff9c4
    style D4 fill:#c8e6c9
    style C4 fill:#ffccbc
    style E4 fill:#b39ddb
```

---

## 11. Class Diagram: Core Components

```mermaid
classDiagram
    class SimulationOrchestrator {
        +max_agents: int
        +agent_pool: list~Agent~
        +environment_manager: EnvironmentManager
        +launch_agents(count, profile) list~AgentID~
        +assign_to_environment(agent, env) bool
        +collect_metrics() SimulationMetrics
        +shutdown_gracefully() None
    }
    
    class Agent {
        +agent_id: str
        +profile: AgentProfile
        +state: AgentState
        +hub_client: WebSocketClient
        +vision_adapter: VisionAdapter
        +decision_engine: DecisionEngine
        +join_table(table_id, hub) None
        +sync_state(state) None
        +make_decision(state) Decision
        +execute_action(action) None
    }
    
    class AgentProfile {
        +name: str
        +variance_model: str
        +decision_threshold: float
        +timing_variance_s: tuple
        +action_randomness: float
        +session_duration_minutes: int
    }
    
    class CentralHub {
        +host: str
        +port: int
        +connections: dict
        +redis_client: Redis
        +start() None
        +broadcast_to_table(table_id, event) None
        +handle_sync_request(message) None
        +resolve_conflict(actions) Action
    }
    
    class DecisionEngine {
        +range_model: RangeModel
        +postflop_logic: PostflopLogic
        +equity_calculator: EquityCalculator
        +calculate_decision(state) Decision
        +estimate_opponent_range(action) Range
    }
    
    class RangeModel {
        +hands: dict~str, float~
        +metadata: dict
        +normalize() Range
        +merge(other) Range
        +contains(hand) bool
        +weight(hand) float
    }
    
    class VisionAdapter {
        +mode: str
        +roi_cache: dict
        +yolo_model: YOLODetector
        +ocr_engine: TesseractOCR
        +detect_rois(screenshot, table_id) dict
        +extract_state(screenshot) tuple
    }
    
    class VarianceModel {
        <<interface>>
        +adjust_action(action, equity) Action
        +get_timing_delay(complexity) float
        +apply_randomness(action, alternatives) Action
    }
    
    class ConservativeBehavior {
        +adjust_action(action, equity) Action
    }
    
    class AggressiveBehavior {
        +adjust_action(action, equity) Action
    }
    
    class AdaptiveBehavior {
        +session_results: list
        +tilt_threshold: float
        +adjust_action(action, context) Action
    }
    
    SimulationOrchestrator "1" --> "*" Agent : manages
    Agent "1" --> "1" AgentProfile : has
    Agent "1" --> "1" CentralHub : connects to
    Agent "1" --> "1" DecisionEngine : uses
    Agent "1" --> "1" VisionAdapter : uses
    Agent "1" --> "1" VarianceModel : applies
    
    DecisionEngine "1" --> "1" RangeModel : uses
    
    VarianceModel <|.. ConservativeBehavior : implements
    VarianceModel <|.. AggressiveBehavior : implements
    VarianceModel <|.. AdaptiveBehavior : implements
    
    CentralHub "1" --> "*" Agent : coordinates
```

---

## 12. Deployment Architecture

```mermaid
graph TB
    subgraph "Cloud Infrastructure AWS/GCP"
        subgraph "Kubernetes Cluster"
            subgraph "Agent Pods"
                AP1[Agent Pod 1-20]
                AP2[Agent Pod 21-40]
                APN[Agent Pod N]
            end
            
            subgraph "Hub Service"
                Hub[Central Hub<br/>Load Balanced]
            end
            
            subgraph "Data Layer"
                Redis[(Redis Cluster<br/>State Cache)]
                Postgres[(PostgreSQL<br/>Metrics & Logs)]
            end
        end
        
        subgraph "Monitoring Stack"
            Prom[Prometheus<br/>Metrics]
            Graf[Grafana<br/>Dashboards]
            Alert[AlertManager<br/>Notifications]
        end
        
        subgraph "Storage"
            S3[S3/GCS<br/>Simulation Results]
            Logs[CloudWatch/Stackdriver<br/>Logs]
        end
    end
    
    subgraph "External Services"
        Vision[Vision API<br/>Optional External]
    end
    
    AP1 --> Hub
    AP2 --> Hub
    APN --> Hub
    
    Hub --> Redis
    Hub --> Postgres
    
    AP1 --> Prom
    Hub --> Prom
    Redis --> Prom
    
    Prom --> Graf
    Graf --> Alert
    
    Hub --> S3
    AP1 --> Logs
    
    AP1 -.->|Optional| Vision
    
    style Hub fill:#4a90e2,color:#fff
    style Redis fill:#dc382d,color:#fff
    style Prom fill:#e76e55,color:#fff
```

---

## Appendix: Legend and Conventions

### Diagram Types
- **Sequence Diagrams:** Show temporal flow of messages between components
- **State Machines:** Represent state transitions and decision logic
- **Flowcharts:** Illustrate algorithmic processes and data transformations
- **Component Diagrams:** Display static structure and relationships
- **Architecture Diagrams:** High-level system organization

### Color Coding
- 🔵 **Blue:** Core infrastructure (Hub, Orchestrator)
- 🟢 **Green:** Decision/output stages
- 🟡 **Yellow:** Validation/checking stages
- 🟠 **Orange:** Monitoring/metrics
- 🔴 **Red:** Critical/error paths
- ⚪ **Gray:** External systems

### Notation
- `→` Synchronous call
- `-->` Response/return
- `-.->` Optional/conditional
- `⇄` Bidirectional communication
- `[*]` Terminal state

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-05  
**Companion:** SIMULATION_SPEC.md  
**Tools Used:** Mermaid (mermaid.js)

**Viewing Instructions:**
- These diagrams use Mermaid syntax
- View in GitHub, GitLab, or Mermaid Live Editor
- VS Code: Install "Markdown Preview Mermaid Support" extension
- Obsidian: Native Mermaid support

**Educational Use Only**
