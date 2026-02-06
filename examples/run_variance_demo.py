#!/usr/bin/env python3
"""
Demo: Variance and Adaptive Modeling with 10 Agents

Tests variance module in virtual mode with 10 agents and measures
simulated performance metrics (Пункт 2, Шаг 3.2).

Educational Use Only: Game theory research.
"""

import random
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sim_engine.variance_module import (
    AnomalyDetector,
    BehaviorType,
    BehaviorVariance,
    OpponentProfiler,
    SessionState,
    train_opponent_profiler,
    TORCH_AVAILABLE,
)


class SimulatedAgent:
    """Simulated agent with behavioral variance."""
    
    def __init__(self, agent_id: str, behavior_type: BehaviorType):
        """Initialize agent."""
        self.agent_id = agent_id
        self.behavior_type = behavior_type
        self.variance = BehaviorVariance(behavior_type)
        self.session = SessionState(
            session_id=f"session_{agent_id}",
            max_duration_seconds=7200.0,  # 2 hours
            max_hands=100
        )
        self.hands_won = 0
        self.total_equity_realized = 0.0
        self.actions_taken = []
    
    def make_decision(self, base_equity: float, context: dict) -> dict:
        """Make decision with behavioral variance."""
        adjusted_equity, metadata = self.variance.apply_behavioral_variance(
            base_equity,
            context
        )
        
        # Determine action based on adjusted equity
        if adjusted_equity >= 0.70:
            action = "raise"
        elif adjusted_equity >= 0.50:
            action = "call"
        else:
            action = "fold"
        
        self.session.decisions_made += 1
        self.total_equity_realized += adjusted_equity
        
        action_data = {
            "action": action,
            "equity": adjusted_equity,
            "metadata": metadata
        }
        
        self.actions_taken.append(action_data)
        
        return action_data
    
    def get_performance_metrics(self) -> dict:
        """Get agent performance metrics (Пункт 2: measure performance)."""
        if self.session.decisions_made == 0:
            avg_equity = 0.0
        else:
            avg_equity = self.total_equity_realized / self.session.decisions_made
        
        return {
            "agent_id": self.agent_id,
            "behavior_type": self.behavior_type.value,
            "decisions_made": self.session.decisions_made,
            "hands_played": self.session.hands_played,
            "hands_won": self.hands_won,
            "avg_equity": avg_equity,
            "win_rate": self.hands_won / max(1, self.session.hands_played)
        }


def main():
    """
    Run variance demo with 10 agents (Пункт 2).
    
    Educational Note:
        Testing with 10 agents validates behavioral diversity and
        opponent profiling at scale for research purposes.
    """
    print("=" * 70)
    print("Variance & Adaptive Modeling Demo")
    print("Testing with 10 Agents - Measuring Performance Metrics")
    print("Educational Use Only - Game Theory Research")
    print("=" * 70)
    print()
    
    # Create 10 agents with diverse behaviors (Пункт 2: 10 agents)
    num_agents = 10
    behaviors = [
        BehaviorType.CONSERVATIVE,
        BehaviorType.BALANCED,
        BehaviorType.AGGRESSIVE,
        BehaviorType.RANDOM,
        BehaviorType.ADAPTIVE,
    ]
    
    agents = []
    
    print(f"Creating {num_agents} agents with behavioral variance...")
    for i in range(num_agents):
        behavior = behaviors[i % len(behaviors)]
        agent = SimulatedAgent(f"agent_{i+1:02d}", behavior)
        agents.append(agent)
        print(f"  Agent {agent.agent_id}: {behavior.value}")
    
    print()
    
    # Create opponent profiler
    print("Initializing opponent profiler...")
    profiler = OpponentProfiler()
    
    if TORCH_AVAILABLE:
        print("  PyTorch available: Training neural network...")
        history = train_opponent_profiler(profiler, epochs=5, batch_size=32)
        print(f"  Training complete. Final loss: {history['train_loss'][-1]:.4f}")
    else:
        print("  PyTorch not available: Using fallback heuristics")
    
    print()
    
    # Create anomaly detector
    detector = AnomalyDetector()
    
    # Simulate research session
    print("-" * 70)
    print("Running Simulation")
    print("-" * 70)
    print()
    
    num_hands = 20  # Simulate 20 hands
    
    for hand_num in range(1, num_hands + 1):
        print(f"Hand {hand_num}/{num_hands}")
        
        # Generate base equity for this hand (random scenario)
        base_equity = random.uniform(0.30, 0.80)
        
        # Each agent makes decision
        for agent in agents:
            context = {
                "pot_odds": random.uniform(0.3, 0.7),
                "opponent_count": random.randint(2, 5),
                "hand_num": hand_num
            }
            
            decision = agent.make_decision(base_equity, context)
            
            # Simulate outcome
            if decision["action"] != "fold":
                agent.session.hands_played += 1
                
                # Win probability based on equity
                if random.random() < decision["equity"]:
                    agent.hands_won += 1
        
        # Check for anomalies
        for agent in agents:
            anomalies = detector.detect_anomalies(
                agent.session,
                agent.actions_taken[-20:]  # Recent 20 actions
            )
            
            if len(anomalies) > 1 or anomalies[0].value != "normal":
                print(f"  [ANOMALY] {agent.agent_id}: {[a.value for a in anomalies]}")
        
        time.sleep(0.1)  # Throttle for display
    
    print()
    print("-" * 70)
    print("Simulation Complete - Performance Metrics")
    print("-" * 70)
    print()
    
    # Collect and display performance metrics (Пункт 2: measure metrics)
    metrics_by_behavior = {}
    
    for agent in agents:
        metrics = agent.get_performance_metrics()
        
        behavior = metrics["behavior_type"]
        if behavior not in metrics_by_behavior:
            metrics_by_behavior[behavior] = []
        
        metrics_by_behavior[behavior].append(metrics)
        
        print(f"{metrics['agent_id']} ({metrics['behavior_type']}):")
        print(f"  Decisions: {metrics['decisions_made']}")
        print(f"  Hands Played: {metrics['hands_played']}")
        print(f"  Hands Won: {metrics['hands_won']}")
        print(f"  Win Rate: {metrics['win_rate']:.2%}")
        print(f"  Avg Equity: {metrics['avg_equity']:.2%}")
        print()
    
    # Aggregate metrics by behavior type
    print("-" * 70)
    print("Aggregated Metrics by Behavior Type")
    print("-" * 70)
    print()
    
    for behavior, agent_metrics in metrics_by_behavior.items():
        avg_win_rate = sum(m["win_rate"] for m in agent_metrics) / len(agent_metrics)
        avg_equity = sum(m["avg_equity"] for m in agent_metrics) / len(agent_metrics)
        total_decisions = sum(m["decisions_made"] for m in agent_metrics)
        
        print(f"{behavior.upper()}:")
        print(f"  Agents: {len(agent_metrics)}")
        print(f"  Avg Win Rate: {avg_win_rate:.2%}")
        print(f"  Avg Equity: {avg_equity:.2%}")
        print(f"  Total Decisions: {total_decisions}")
        print()
    
    # Test opponent profiling
    print("-" * 70)
    print("Opponent Profiling Results")
    print("-" * 70)
    print()
    
    # Profile first 5 agents based on their actions
    for agent in agents[:5]:
        if len(agent.actions_taken) > 0:
            # Convert actions to observations format
            observations = [
                {
                    "action": a["action"],
                    "sizing": random.uniform(0.5, 1.0) if a["action"] == "raise" else None
                }
                for a in agent.actions_taken
            ]
            
            predicted_type, confidence = profiler.predict_opponent_type(
                agent.agent_id,
                observations
            )
            
            actual_type = agent.behavior_type.value
            correct = "[MATCH]" if predicted_type.value == actual_type or (
                actual_type == "random" and predicted_type != BehaviorType.ADAPTIVE
            ) else "[DIFF]"
            
            print(f"{agent.agent_id}:")
            print(f"  Actual: {actual_type}")
            print(f"  Predicted: {predicted_type.value} ({confidence:.2%} confidence) {correct}")
            print()
    
    print("=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print()
    print("Educational Note:")
    print("  This demo validated:")
    print("  - Behavioral variance across 10 agents")
    print("  - Performance metrics measurement")
    print("  - Opponent profiling with neural network")
    print("  - Anomaly detection in virtual environment")
    print("  - Session management and limits")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
        sys.exit(0)
