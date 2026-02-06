# Multi-Agent Simulation Orchestrator

**Educational Use Only**: For game theory research in controlled virtual environments.

## Overview

The Simulation Orchestrator manages the launch and coordination of N agents for scalable multi-agent research (Фаза 3, Шаг 3.1).

## Features

### Пункт 1: Agent Launch & Management
- **Launch N Agents**: Spawn multiple agents with unique configurations
- **Docker-like Isolation**: Each agent runs independently for research
- **Unique Configurations**: Strategy profiles, resource levels, skill variance

### Подпункт 1.1: Environment Selection
- **Virtual Lobby Scanning**: Discover available research scenarios
- **Low-Engagement Targeting**: Select environments with exploitable patterns
- **Optimal Placement**: Score-based selection for research objectives

### Подпункт 1.2: Reliability
- **Health Checks**: Monitor agent status and heartbeats
- **Auto-Restart**: Automatic recovery from failures (configurable max attempts)
- **Multiprocessing**: True parallel execution for scalability

### Пункт 2: Network Diversity
- **Proxy Rotation**: Simulate network diversity via virtual IPs
- **Deterministic Assignment**: Each agent gets consistent virtual IP
- **Dynamic Rotation**: Support for IP rotation during sessions

## Usage

### Basic Demo

```bash
# Run simplified demo with 3 agents
python examples/run_orchestrator_demo.py
```

### Full Orchestrator (requires multiprocessing support)

```python
from sim_engine.sim_orchestrator import SimulationOrchestrator

# Create orchestrator
orchestrator = SimulationOrchestrator(
    num_agents=5,
    proxy_enabled=True,
    auto_restart=True,
    max_restarts=3
)

# Start simulation
orchestrator.start()

# Monitor and wait
orchestrator.wait_for_completion()

# Cleanup
orchestrator.stop()
```

### Custom Agent Configuration

```python
from sim_engine.sim_orchestrator import AgentConfig, EnvironmentType

config = AgentConfig(
    agent_id="research_agent_001",
    agent_name="ResearchAgent001",
    strategy_profile="aggressive",  # balanced, conservative, aggressive, exploitative
    resource_level="high",  # low, medium, high
    skill_variance=0.15,
    environment_type=EnvironmentType.RESEARCH_SANDBOX,
    hub_enabled=True,
    hub_url="ws://localhost:8765",
    proxy_enabled=True,
    simulation_mode=True
)
```

## Components

### AgentConfig
Defines individual agent characteristics:
- **Strategy Profile**: Behavioral tendencies (balanced, conservative, aggressive, exploitative)
- **Resource Level**: Initial resource allocation (low, medium, high)
- **Skill Variance**: Decision-making variability (0.0-1.0)
- **Environment Settings**: Target environment type and ID
- **Hub Connectivity**: Central hub for multi-agent coordination
- **Proxy Settings**: Network diversity simulation

### EnvironmentSelector
Manages environment selection logic:
- `scan_available_environments()`: Discover available scenarios
- `select_low_engagement_environment()`: Choose optimal environment

**Selection Strategy**:
1. Filter environments below engagement threshold
2. Score based on:
   - Low engagement (weight: 2.0)
   - Moderate participant count (weight: 0.5)
   - Low variance (weight: -0.3)
3. Select highest scoring environment

### ProxyRotator
Handles proxy rotation for network diversity:
- Generates synthetic virtual IPs (non-routable ranges)
- Deterministic assignment per agent
- Support for dynamic rotation

### SimulationOrchestrator
Main orchestration engine:
- Agent lifecycle management
- Health monitoring
- Auto-restart on failures
- Multiprocessing coordination
- Graceful shutdown

## Architecture

```
SimulationOrchestrator
├── AgentProcess 1 (multiprocessing.Process)
│   ├── AgentConfig (strategy: balanced)
│   ├── Environment: research_sandbox_env_001
│   └── Proxy: 10.0.0.123
├── AgentProcess 2
│   ├── AgentConfig (strategy: aggressive)
│   ├── Environment: research_sandbox_env_002
│   └── Proxy: 172.16.0.45
└── AgentProcess N
    ├── AgentConfig (strategy: exploitative)
    ├── Environment: research_sandbox_env_003
    └── Proxy: 192.168.0.78

Central Hub (ws://localhost:8765)
├── State Synchronization
├── Conflict Detection
└── Collective Probabilities
```

## Testing

16 comprehensive tests covering:
- Agent configuration
- Environment selection logic
- Proxy rotation
- Strategy profile diversity
- Component integration

```bash
# Run tests
python -m pytest sim_engine/tests/test_orchestrator.py -v
```

## Demo Output

```
======================================================================
Multi-Agent Orchestration Demo
Educational Use Only - Game Theory Research
======================================================================

[Orchestrator] Found 4 environments:
  - research_sandbox_env_95be9a5f: engagement=58.31%, participants=2
  - research_sandbox_env_36b6b194: engagement=28.00%, participants=3
  - research_sandbox_env_f798619a: engagement=22.73%, participants=3
  - research_sandbox_env_e66bf28b: engagement=69.36%, participants=6

[Orchestrator] Proxy rotation enabled (30 virtual IPs)

[Orchestrator] Agent agent_001_0ad53b:
  - Strategy: balanced
  - Environment: research_sandbox_env_f798619a
  - Proxy: 192.168.0.172

[agent_001_0ad53b] Started
[agent_001_0ad53b] Hand 1/5 complete
...
[agent_001_0ad53b] Simulation complete

Summary:
  agent_001_0ad53b: 5 hands, status=stopped
  agent_002_bea1c2: 5 hands, status=stopped
  agent_003_ca6337: 5 hands, status=stopped
```

## Configuration Options

### Base Configuration Dictionary
```python
base_config = {
    "hub_enabled": True,
    "hub_url": "ws://localhost:8765",
    "vision_config_path": "coach_app/configs/adapters/generic_sim.yaml",
    "max_hands": 1000,  # Optional limit
    "max_duration_seconds": 3600  # Optional limit (1 hour)
}
```

### Health Check Configuration
- `health_check_interval`: Seconds between checks (default: 30.0)
- `auto_restart`: Enable automatic restart (default: True)
- `max_restarts`: Maximum restart attempts (default: 3)

## Educational Note

This orchestrator is designed exclusively for multi-agent game theory research in controlled virtual environments. It enables:

1. **Scalability**: Launch N agents for large-scale simulations
2. **Diversity**: Heterogeneous agent strategies and behaviors
3. **Coordination**: Central hub for multi-agent state synchronization
4. **Reliability**: Health monitoring and automatic recovery
5. **Realism**: Proxy rotation for network diversity simulation

**Not intended for**:
- Production gaming systems
- Real-money applications
- Automated trading/betting

## Related Components

- **Central Hub** (`sim_engine/central_hub.py`): Multi-agent coordination
- **Decision Engine** (`sim_engine/decision.py`): Agent decision-making
- **Vision System** (`sim_engine/sim_vision.py`): State extraction
- **Hub Client** (`sim_engine/hub_client.py`): Hub connectivity

## Next Steps

See **Шаг 3.2: Variance и Адаптивное Моделирование** for:
- Behavioral variance modules
- Neural network opponent profiling
- Session modeling and anomaly detection
