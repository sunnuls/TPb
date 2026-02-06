#!/usr/bin/env python3
"""
Demo: Multi-Agent Orchestrator

Simplified demo of multi-agent orchestration (Фаза 3, Шаг 3.1)
without full multiprocessing for compatibility.

Educational Use Only: Game theory research.
"""

import random
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sim_engine.sim_orchestrator import (
    AgentConfig,
    AgentStatus,
    EnvironmentSelector,
    EnvironmentType,
    ProxyRotator,
)


class ThreadedAgent:
    """Simple threaded agent for demo."""
    
    def __init__(self, config: AgentConfig):
        """Initialize agent."""
        self.config = config
        self.status = AgentStatus.RUNNING
        self.hands_played = 0
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
    
    def start(self) -> None:
        """Start agent thread."""
        self.thread = threading.Thread(
            target=self._run,
            name=self.config.agent_name
        )
        self.thread.daemon = True
        self.thread.start()
    
    def _run(self) -> None:
        """Agent simulation loop."""
        agent_id = self.config.agent_id
        
        print(f"[{agent_id}] Started")
        print(f"[{agent_id}]   Strategy: {self.config.strategy_profile}")
        print(f"[{agent_id}]   Resource: {self.config.resource_level}")
        print(f"[{agent_id}]   Environment: {self.config.environment_id}")
        
        # Simulate research activity
        max_hands = 5
        
        while not self.stop_flag.is_set() and self.hands_played < max_hands:
            time.sleep(random.uniform(1.0, 2.0))
            self.hands_played += 1
            
            print(f"[{agent_id}] Hand {self.hands_played}/{max_hands} complete")
        
        self.status = AgentStatus.STOPPED
        print(f"[{agent_id}] Simulation complete")
    
    def stop(self) -> None:
        """Stop agent."""
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=2.0)


def main():
    """Run orchestrator demo."""
    print("=" * 70)
    print("Multi-Agent Orchestration Demo")
    print("Educational Use Only - Game Theory Research")
    print("=" * 70)
    print()
    
    num_agents = 3
    
    # Create environment selector
    env_selector = EnvironmentSelector()
    
    # Scan environments
    print(f"[Orchestrator] Scanning available environments...")
    environments = env_selector.scan_available_environments(
        EnvironmentType.RESEARCH_SANDBOX
    )
    
    print(f"[Orchestrator] Found {len(environments)} environments:")
    for env in environments:
        print(f"  - {env['environment_id']}: "
              f"engagement={env['engagement_level']:.2%}, "
              f"participants={env['participant_count']}")
    
    print()
    
    # Create proxy rotator
    proxy_rotator = ProxyRotator(enabled=True)
    print(f"[Orchestrator] Proxy rotation enabled "
          f"({len(proxy_rotator.virtual_ips)} virtual IPs)")
    print()
    
    # Generate agent configs
    print(f"[Orchestrator] Generating configurations for {num_agents} agents...")
    
    strategies = ["balanced", "conservative", "aggressive"]
    resources = ["low", "medium", "high"]
    
    agents = []
    
    for i in range(num_agents):
        agent_id = f"agent_{i+1:03d}_{uuid.uuid4().hex[:6]}"
        
        # Select environment
        selected_env = env_selector.select_low_engagement_environment(
            environments,
            target_engagement=0.5
        )
        
        # Get proxy
        proxy_ip = proxy_rotator.get_proxy_for_agent(agent_id)
        
        config = AgentConfig(
            agent_id=agent_id,
            agent_name=f"ResearchAgent_{i+1:03d}",
            strategy_profile=strategies[i % len(strategies)],
            resource_level=resources[i % len(resources)],
            skill_variance=random.uniform(0.05, 0.20),
            environment_type=EnvironmentType.RESEARCH_SANDBOX,
            environment_id=selected_env["environment_id"] if selected_env else None,
            hub_enabled=True,
            hub_url="ws://localhost:8765",
            simulation_mode=True,
            continuous=True,
            proxy_enabled=True
        )
        
        print(f"[Orchestrator] Agent {agent_id}:")
        print(f"  - Strategy: {config.strategy_profile}")
        print(f"  - Environment: {config.environment_id}")
        print(f"  - Proxy: {proxy_ip}")
        
        agent = ThreadedAgent(config)
        agents.append(agent)
    
    print()
    print("-" * 70)
    print(f"[Orchestrator] Launching {len(agents)} agents...")
    print("-" * 70)
    print()
    
    # Launch agents
    for agent in agents:
        agent.start()
        time.sleep(0.3)  # Stagger launches
    
    print()
    print("[Orchestrator] All agents launched. Monitoring...")
    print()
    
    # Monitor health
    try:
        while any(a.status == AgentStatus.RUNNING for a in agents):
            time.sleep(2.0)
            
            # Health check
            for agent in agents:
                if agent.status == AgentStatus.RUNNING:
                    status_icon = "[RUNNING]"
                elif agent.status == AgentStatus.STOPPED:
                    status_icon = "[STOPPED]"
                else:
                    status_icon = "[ERROR]"
                
                print(f"{status_icon} {agent.config.agent_id}: "
                      f"{agent.hands_played} hands played")
            
            print()
    
    except KeyboardInterrupt:
        print("\n[Orchestrator] Received interrupt signal")
    
    # Stop all
    print()
    print("[Orchestrator] Stopping all agents...")
    
    for agent in agents:
        agent.stop()
    
    print()
    print("=" * 70)
    print("Orchestration Complete")
    print("=" * 70)
    print()
    print("Summary:")
    for agent in agents:
        print(f"  {agent.config.agent_id}: "
              f"{agent.hands_played} hands, "
              f"status={agent.status.value}")
    
    print()
    print("Educational Note:")
    print("  This demo shows multi-agent orchestration with:")
    print("  - Environment selection (low-engagement targeting)")
    print("  - Proxy rotation (network diversity simulation)")
    print("  - Health monitoring (status tracking)")
    print("  - Graceful shutdown")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
        sys.exit(0)
