#!/usr/bin/env python3
"""
Demo: Multi-Agent Coordination with Central Hub

This script demonstrates the central hub coordinating 3 simulated agents
for game theory research (Подпункт 1.2, Шаг 2.2).

Educational Use Only: For research into multi-agent coordination problems.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sim_engine.central_hub import CentralHub
from sim_engine.hub_client import HubClient, HubConfig


async def simulated_agent(agent_id: str, environment_id: str, hub_url: str):
    """
    Simulate an agent making decisions with hub coordination.
    
    Educational Note:
        This simulates a research agent that queries the hub before
        taking actions to avoid conflicts with other agents.
    """
    config = HubConfig(
        enabled=True,
        hub_url=hub_url,
        agent_id=agent_id,
        environment_id=environment_id,
        heartbeat_interval=10.0
    )
    
    client = HubClient(config)
    
    print(f"[{agent_id}] Connecting to hub...")
    connected = await client.connect()
    
    if not connected:
        print(f"[{agent_id}] Failed to connect")
        return
    
    print(f"[{agent_id}] Connected successfully!")
    
    # Simulate decision-making loop
    for i in range(3):
        await asyncio.sleep(2.0)
        
        # Query hub before action
        planned_action = {
            "type": "increment",
            "sizing": 12.0 * (i + 1),
            "iteration": i
        }
        
        state_data = {
            "equity": 0.60 + (i * 0.05),
            "confidence": 0.80,
            "position": "BTN"
        }
        
        print(f"[{agent_id}] Querying hub for action approval...")
        response = await client.query_hub_before_action(planned_action, state_data)
        
        if response["proceed"]:
            print(f"[{agent_id}] [OK] Action approved by hub")
            if response.get("collective_probabilities"):
                avg_eq = response["collective_probabilities"].get("average_equity")
                if avg_eq:
                    print(f"[{agent_id}]   Collective avg equity: {avg_eq:.2%}")
        else:
            print(f"[{agent_id}] [BLOCKED] Action blocked by hub")
            conflicts = response.get("conflicts_detected", [])
            for conflict in conflicts:
                print(f"[{agent_id}]   {conflict}")
        
        print()
    
    print(f"[{agent_id}] Disconnecting...")
    await client.disconnect()


async def main():
    """
    Main demo: Start hub and coordinate 3 agents.
    
    Educational Note:
        Demonstrates how multiple research agents coordinate through
        the central hub to avoid conflicts and share information.
    """
    print("=" * 70)
    print("Multi-Agent Coordination Demo")
    print("Educational Use Only - Game Theory Research")
    print("=" * 70)
    print()
    
    # Start central hub
    hub = CentralHub(host="localhost", port=8765)
    asyncio.create_task(hub.start())
    
    # Wait for hub to start
    await asyncio.sleep(1.0)
    
    print("Hub started. Launching 3 simulated agents...")
    print()
    
    # Launch 3 agents
    agents = [
        simulated_agent(f"agent_{i}", "demo_env", "ws://localhost:8765")
        for i in range(1, 4)
    ]
    
    # Run all agents concurrently
    await asyncio.gather(*agents)
    
    print()
    print("=" * 70)
    print("Demo Complete")
    print("All agents coordinated successfully through central hub")
    print("=" * 70)
    
    # Cleanup
    await hub.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        sys.exit(0)
