"""
Multi-Agent Simulation Orchestrator.

This module manages the launch and coordination of N agents for scalable
multi-agent game theory research (Фаза 3, Шаг 3.1).

Educational Use Only: Designed for controlled research environments to study
multi-agent coordination, emergent behaviors, and strategic interactions.
Not intended for production gaming or real-money applications.
"""

from __future__ import annotations

import multiprocessing as mp
import random
import signal
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent lifecycle status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"
    RESTARTING = "restarting"


class EnvironmentType(str, Enum):
    """Virtual environment types for research."""
    POKER_CASH = "poker_cash"
    POKER_TOURNAMENT = "poker_tournament"
    RESEARCH_SANDBOX = "research_sandbox"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """
    Configuration for individual agent instance (Пункт 1).
    
    Educational Note:
        Each agent has unique configuration to study behavioral diversity
        and strategic adaptation in multi-agent research scenarios.
    """
    agent_id: str
    agent_name: str
    
    # Agent characteristics
    strategy_profile: str = "balanced"  # balanced, conservative, aggressive, exploitative
    resource_level: str = "medium"  # low, medium, high
    skill_variance: float = 0.1  # Variance in decision-making
    
    # Environment
    environment_type: EnvironmentType = EnvironmentType.RESEARCH_SANDBOX
    environment_id: Optional[str] = None
    
    # Hub connectivity
    hub_enabled: bool = True
    hub_url: str = "ws://localhost:8765"
    
    # Vision config
    vision_config_path: str = "coach_app/configs/adapters/generic_sim.yaml"
    
    # Simulation mode
    simulation_mode: bool = True
    continuous: bool = True
    
    # Proxy settings (Пункт 2)
    proxy_enabled: bool = False
    proxy_rotation: bool = False
    
    # Session limits
    max_hands: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "strategy_profile": self.strategy_profile,
            "resource_level": self.resource_level,
            "skill_variance": self.skill_variance,
            "environment_type": self.environment_type.value,
            "environment_id": self.environment_id,
            "hub_enabled": self.hub_enabled,
            "hub_url": self.hub_url,
            "vision_config_path": self.vision_config_path,
            "simulation_mode": self.simulation_mode,
            "continuous": self.continuous,
            "proxy_enabled": self.proxy_enabled,
            "proxy_rotation": self.proxy_rotation,
            "max_hands": self.max_hands,
            "max_duration_seconds": self.max_duration_seconds
        }


@dataclass
class AgentProcess:
    """
    Running agent process information (Подпункт 1.2: health checks).
    
    Educational Note:
        Process tracking enables health monitoring and automatic recovery
        for long-running multi-agent research simulations.
    """
    agent_id: str
    config: AgentConfig
    process: mp.Process
    status: AgentStatus = AgentStatus.INITIALIZING
    start_time: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    restart_count: int = 0
    hands_played: int = 0
    errors: List[str] = field(default_factory=list)


class EnvironmentSelector:
    """
    Virtual environment selection logic (Подпункт 1.1).
    
    Educational Note:
        Environment selection algorithms enable research into agent
        placement strategies, opponent selection, and lobby dynamics
        in multi-agent game theory studies.
    """
    
    @staticmethod
    def scan_available_environments(
        environment_type: EnvironmentType
    ) -> List[Dict[str, Any]]:
        """
        Scan for available virtual environments (Подпункт 1.1).
        
        In real implementation, this would:
        - Query virtual lobby API
        - Detect active scenarios
        - Analyze participant engagement levels
        
        For research simulation, generates synthetic environment data.
        
        Args:
            environment_type: Type of environment to scan for
        
        Returns:
            List of available environment metadata
            
        Educational Note:
            Scanning enables agents to dynamically select optimal research
            scenarios based on engagement levels and strategic objectives.
        """
        # Synthetic environment data for research
        environments = []
        
        num_envs = random.randint(3, 8)
        
        for i in range(num_envs):
            env_id = f"{environment_type.value}_env_{uuid.uuid4().hex[:8]}"
            
            # Simulate engagement metrics
            engagement_level = random.uniform(0.2, 0.9)
            participant_count = random.randint(2, 9)
            
            environments.append({
                "environment_id": env_id,
                "environment_type": environment_type.value,
                "engagement_level": engagement_level,
                "participant_count": participant_count,
                "avg_skill_level": random.uniform(0.3, 0.8),
                "variance": random.uniform(0.05, 0.25),
                "available_seats": max(0, 9 - participant_count)
            })
        
        return environments
    
    @staticmethod
    def select_low_engagement_environment(
        environments: List[Dict[str, Any]],
        target_engagement: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Select environment with low-engagement participants (Подпункт 1.1).
        
        Strategy: Target environments where participants show lower engagement,
        which may indicate exploitable patterns for research purposes.
        
        Args:
            environments: List of available environments
            target_engagement: Target engagement threshold
        
        Returns:
            Selected environment or None
            
        Educational Note:
            Low-engagement scenarios enable research into exploitation
            strategies and adaptation against passive opponents.
        """
        # Filter to environments below engagement threshold
        low_engagement = [
            env for env in environments
            if env["engagement_level"] < target_engagement
            and env["available_seats"] > 0
        ]
        
        if not low_engagement:
            # Fallback: select least engaged
            if environments:
                return min(environments, key=lambda e: e["engagement_level"])
            return None
        
        # Select environment with optimal characteristics
        # Prefer: low engagement + moderate participant count
        scored = []
        for env in low_engagement:
            score = (
                (target_engagement - env["engagement_level"]) * 2.0  # Lower engagement better
                + (env["participant_count"] / 9.0) * 0.5  # Some opponents needed
                - env["variance"] * 0.3  # Lower variance = more predictable
            )
            scored.append((score, env))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]


class ProxyRotator:
    """
    Proxy rotation for network diversity simulation (Пункт 2).
    
    Educational Note:
        Proxy rotation simulates network diversity to study detection
        resistance and distributed agent coordination in research contexts.
    """
    
    def __init__(self, enabled: bool = False):
        """
        Initialize proxy rotator.
        
        Args:
            enabled: Whether proxy rotation is enabled
        """
        self.enabled = enabled
        self.virtual_ips: List[str] = []
        
        if enabled:
            # Generate synthetic virtual IPs for research
            self._generate_virtual_ips()
    
    def _generate_virtual_ips(self) -> None:
        """Generate synthetic virtual IP addresses."""
        # Synthetic IPs for research (non-routable ranges)
        base_ranges = [
            "10.0.0.",
            "172.16.0.",
            "192.168.0."
        ]
        
        for base in base_ranges:
            for i in range(10):
                ip = f"{base}{random.randint(1, 254)}"
                self.virtual_ips.append(ip)
    
    def get_proxy_for_agent(self, agent_id: str) -> Optional[str]:
        """
        Get virtual proxy IP for agent (Пункт 2).
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Virtual IP or None if disabled
            
        Educational Note:
            Each agent gets a unique virtual IP to simulate network
            diversity in multi-agent research scenarios.
        """
        if not self.enabled or not self.virtual_ips:
            return None
        
        # Deterministic selection based on agent_id for consistency
        import hashlib
        hash_val = int(hashlib.md5(agent_id.encode()).hexdigest(), 16)
        index = hash_val % len(self.virtual_ips)
        
        return self.virtual_ips[index]
    
    def rotate_proxy(self, agent_id: str) -> Optional[str]:
        """
        Rotate to new proxy for agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            New virtual IP
        """
        if not self.enabled or not self.virtual_ips:
            return None
        
        # Random rotation
        return random.choice(self.virtual_ips)


class SimulationOrchestrator:
    """
    Multi-Agent Simulation Orchestrator (Пункт 1, Фаза 3, Шаг 3.1).
    
    Features:
    - Launch N agents with unique configurations
    - Environment selection and assignment
    - Health monitoring and auto-restart (Подпункт 1.2)
    - Multiprocessing для parallel simulations
    - Proxy rotation для network diversity (Пункт 2)
    
    Educational Note:
        This orchestrator enables scalable multi-agent research by managing
        agent lifecycles, environment selection, and coordination at scale.
        Designed for studying emergent behaviors, strategic interactions,
        and coordination patterns in controlled virtual environments.
    """
    
    def __init__(
        self,
        num_agents: int = 3,
        base_config: Optional[Dict[str, Any]] = None,
        proxy_enabled: bool = False,
        health_check_interval: float = 30.0,
        auto_restart: bool = True,
        max_restarts: int = 3
    ):
        """
        Initialize simulation orchestrator.
        
        Args:
            num_agents: Number of agents to launch
            base_config: Base configuration template
            proxy_enabled: Enable proxy rotation (Пункт 2)
            health_check_interval: Seconds between health checks
            auto_restart: Enable automatic restart on failure
            max_restarts: Maximum restart attempts per agent
        """
        self.num_agents = num_agents
        self.base_config = base_config or {}
        self.health_check_interval = health_check_interval
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts
        
        # Agent processes
        self.agents: Dict[str, AgentProcess] = {}
        
        # Components
        self.env_selector = EnvironmentSelector()
        self.proxy_rotator = ProxyRotator(enabled=proxy_enabled)
        
        # Orchestrator state
        self.running = False
        self.start_time: Optional[float] = None
        
        # Multiprocessing manager for shared state
        self.manager = mp.Manager()
        self.shared_state = self.manager.dict()
    
    def generate_agent_configs(self) -> List[AgentConfig]:
        """
        Generate unique configurations for N agents (Пункт 1).
        
        Returns:
            List of agent configurations
            
        Educational Note:
            Diverse agent configurations enable research into heterogeneous
            multi-agent systems and behavioral variance effects.
        """
        configs = []
        
        # Strategy profiles for diversity
        strategies = ["balanced", "conservative", "aggressive", "exploitative"]
        resource_levels = ["low", "medium", "high"]
        
        for i in range(self.num_agents):
            agent_id = f"agent_{i+1:03d}_{uuid.uuid4().hex[:6]}"
            
            # Distribute strategies
            strategy = strategies[i % len(strategies)]
            resource = resource_levels[i % len(resource_levels)]
            
            config = AgentConfig(
                agent_id=agent_id,
                agent_name=f"ResearchAgent_{i+1:03d}",
                strategy_profile=strategy,
                resource_level=resource,
                skill_variance=random.uniform(0.05, 0.20),
                environment_type=EnvironmentType.RESEARCH_SANDBOX,
                hub_enabled=self.base_config.get("hub_enabled", True),
                hub_url=self.base_config.get("hub_url", "ws://localhost:8765"),
                vision_config_path=self.base_config.get(
                    "vision_config_path",
                    "coach_app/configs/adapters/generic_sim.yaml"
                ),
                simulation_mode=True,
                continuous=True,
                proxy_enabled=self.proxy_rotator.enabled,
                proxy_rotation=self.proxy_rotator.enabled,
                max_hands=self.base_config.get("max_hands"),
                max_duration_seconds=self.base_config.get("max_duration_seconds")
            )
            
            configs.append(config)
        
        return configs
    
    def assign_environments(
        self,
        configs: List[AgentConfig]
    ) -> List[AgentConfig]:
        """
        Assign agents to environments (Подпункт 1.1).
        
        Args:
            configs: Agent configurations
        
        Returns:
            Configurations with assigned environments
            
        Educational Note:
            Environment assignment strategies affect agent interactions
            and emergent behaviors in multi-agent research.
        """
        # Scan available environments
        environments = self.env_selector.scan_available_environments(
            EnvironmentType.RESEARCH_SANDBOX
        )
        
        print(f"[Orchestrator] Found {len(environments)} available environments")
        
        for config in configs:
            # Select low-engagement environment
            selected_env = self.env_selector.select_low_engagement_environment(
                environments
            )
            
            if selected_env:
                config.environment_id = selected_env["environment_id"]
                print(f"[Orchestrator] Assigned {config.agent_id} to "
                      f"{selected_env['environment_id']} "
                      f"(engagement: {selected_env['engagement_level']:.2%})")
            else:
                print(f"[Orchestrator] No suitable environment for {config.agent_id}")
        
        return configs
    
    def launch_agent(
        self,
        config: AgentConfig
    ) -> mp.Process:
        """
        Launch single agent process (Подпункт 1.2: multiprocessing).
        
        Args:
            config: Agent configuration
        
        Returns:
            Agent process
            
        Educational Note:
            Multiprocessing enables true parallel execution of agents
            for scalable research simulations.
        """
        # Get proxy if enabled
        if config.proxy_enabled:
            proxy_ip = self.proxy_rotator.get_proxy_for_agent(config.agent_id)
            print(f"[Orchestrator] Agent {config.agent_id} assigned proxy: {proxy_ip}")
        
        # Create process
        process = mp.Process(
            target=self._agent_worker,
            args=(config, self.shared_state),
            name=config.agent_name
        )
        
        process.start()
        
        return process
    
    @staticmethod
    def _agent_worker(
        config: AgentConfig,
        shared_state: Any
    ) -> None:
        """
        Agent worker process (runs in separate process).
        
        Args:
            config: Agent configuration
            shared_state: Shared state dictionary
            
        Educational Note:
            Each agent runs independently in research simulation,
            enabling true parallel multi-agent execution.
        """
        agent_id = config.agent_id
        
        # Initialize shared state
        shared_state[agent_id] = {
            "status": AgentStatus.RUNNING.value,
            "hands_played": 0,
            "last_update": time.time()
        }
        
        try:
            print(f"[{agent_id}] Starting simulation")
            print(f"[{agent_id}] Strategy: {config.strategy_profile}")
            print(f"[{agent_id}] Environment: {config.environment_id}")
            
            # Simulation loop
            iteration = 0
            max_iterations = 10  # Limited for demo
            
            while iteration < max_iterations:
                iteration += 1
                
                # Simulate agent activity
                time.sleep(random.uniform(1.0, 3.0))
                
                # Update shared state
                shared_state[agent_id] = {
                    "status": AgentStatus.RUNNING.value,
                    "hands_played": iteration,
                    "last_update": time.time()
                }
                
                print(f"[{agent_id}] Iteration {iteration} complete")
            
            print(f"[{agent_id}] Simulation complete")
            shared_state[agent_id]["status"] = AgentStatus.STOPPED.value
            
        except Exception as e:
            print(f"[{agent_id}] ERROR: {e}")
            shared_state[agent_id]["status"] = AgentStatus.ERROR.value
    
    def start(self) -> None:
        """
        Start orchestrator and launch all agents (Пункт 1).
        
        Educational Note:
            Orchestrated launch enables synchronized start of multi-agent
            research simulations with proper initialization.
        """
        if self.running:
            print("[Orchestrator] Already running")
            return
        
        print("=" * 70)
        print("Multi-Agent Simulation Orchestrator")
        print("Educational Use Only - Game Theory Research")
        print("=" * 70)
        print()
        
        self.running = True
        self.start_time = time.time()
        
        # Generate configurations
        print(f"[Orchestrator] Generating configurations for {self.num_agents} agents")
        configs = self.generate_agent_configs()
        
        # Assign environments
        print(f"[Orchestrator] Assigning environments...")
        configs = self.assign_environments(configs)
        
        print()
        print(f"[Orchestrator] Launching {len(configs)} agents...")
        print()
        
        # Launch agents
        for config in configs:
            process = self.launch_agent(config)
            
            agent_proc = AgentProcess(
                agent_id=config.agent_id,
                config=config,
                process=process,
                status=AgentStatus.RUNNING
            )
            
            self.agents[config.agent_id] = agent_proc
            
            time.sleep(0.5)  # Stagger launches
        
        print()
        print(f"[Orchestrator] All agents launched")
        print()
    
    def monitor_health(self) -> None:
        """
        Monitor agent health (Подпункт 1.2: health checks).
        
        Educational Note:
            Health monitoring ensures simulation reliability and enables
            automatic recovery from failures in long-running research.
        """
        print("[Orchestrator] Starting health monitoring...")
        
        while self.running:
            time.sleep(self.health_check_interval)
            
            for agent_id, agent_proc in list(self.agents.items()):
                # Check process alive
                if not agent_proc.process.is_alive():
                    print(f"[Orchestrator] Agent {agent_id} process died")
                    
                    # Auto-restart if enabled
                    if self.auto_restart and agent_proc.restart_count < self.max_restarts:
                        print(f"[Orchestrator] Restarting {agent_id} "
                              f"(attempt {agent_proc.restart_count + 1}/{self.max_restarts})")
                        
                        # Restart
                        new_process = self.launch_agent(agent_proc.config)
                        agent_proc.process = new_process
                        agent_proc.restart_count += 1
                        agent_proc.status = AgentStatus.RESTARTING
                    else:
                        agent_proc.status = AgentStatus.ERROR
                        print(f"[Orchestrator] Agent {agent_id} max restarts exceeded")
                
                # Check shared state
                if agent_id in self.shared_state:
                    state = self.shared_state[agent_id]
                    agent_proc.hands_played = state.get("hands_played", 0)
                    
                    # Check for timeout
                    last_update = state.get("last_update", 0)
                    if time.time() - last_update > self.health_check_interval * 2:
                        print(f"[Orchestrator] Agent {agent_id} heartbeat timeout")
    
    def stop(self) -> None:
        """Stop orchestrator and all agents."""
        print()
        print("[Orchestrator] Stopping all agents...")
        
        self.running = False
        
        for agent_id, agent_proc in self.agents.items():
            if agent_proc.process.is_alive():
                agent_proc.process.terminate()
                agent_proc.process.join(timeout=5.0)
                
                if agent_proc.process.is_alive():
                    agent_proc.process.kill()
            
            print(f"[Orchestrator] Agent {agent_id} stopped "
                  f"(hands: {agent_proc.hands_played}, restarts: {agent_proc.restart_count})")
        
        print("[Orchestrator] All agents stopped")
    
    def wait_for_completion(self) -> None:
        """Wait for all agents to complete."""
        for agent_id, agent_proc in self.agents.items():
            agent_proc.process.join()
            print(f"[Orchestrator] Agent {agent_id} completed")


def main():
    """Educational demo: Run orchestrator with multiple agents."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Multi-Agent Simulation Orchestrator (Educational Research)"
    )
    parser.add_argument("--agents", type=int, default=3,
                        help="Number of agents to launch")
    parser.add_argument("--proxy", action="store_true",
                        help="Enable proxy rotation")
    parser.add_argument("--no-restart", action="store_true",
                        help="Disable auto-restart")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = SimulationOrchestrator(
        num_agents=args.agents,
        proxy_enabled=args.proxy,
        auto_restart=not args.no_restart
    )
    
    # Handle SIGINT gracefully
    def signal_handler(sig, frame):
        print("\n[Orchestrator] Received interrupt signal")
        orchestrator.stop()
        raise SystemExit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start
    orchestrator.start()
    
    # Wait for completion
    orchestrator.wait_for_completion()
    
    print()
    print("=" * 70)
    print("Simulation Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
