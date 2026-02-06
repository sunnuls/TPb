#!/usr/bin/env python3
"""
Demo: Complete Simulation Vision Pipeline

Demonstrates full pipeline: input → extract → decide → output
(Пункт 2, Шаг 2.3)

Educational Use Only: For multi-agent game theory research.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sim_engine.decision import AgentContext, generate_simulated_decision
from sim_engine.sim_vision import create_simulation_vision_from_config
from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position


def main():
    """
    Run complete simulation vision pipeline demo.
    
    Educational Note:
        Demonstrates how multi-agent research simulations extract state,
        make decisions, and execute actions with realistic variance.
    """
    print("=" * 70)
    print("Simulation Vision Pipeline Demo")
    print("Educational Use Only - Multi-Agent Research")
    print("=" * 70)
    print()
    
    # Load configuration
    config_path = "coach_app/configs/adapters/generic_sim.yaml"
    
    print(f"Loading configuration: {config_path}")
    
    try:
        extractor, output_sim = create_simulation_vision_from_config(config_path)
        print("[OK] Vision extractor and output simulator initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        return 1
    
    print()
    print("-" * 70)
    print("Step 1: State Extraction (Simulate Input)")
    print("-" * 70)
    
    # Extract state
    state = extractor.extract_full_state()
    
    print(f"[+] Overall Confidence: {state['overall_confidence']:.2%}")
    print(f"[+] Hero Cards: {state['hero_cards']['value']} "
          f"(conf: {state['hero_cards']['confidence']:.2%})")
    print(f"[+] Board Cards: {state['board_cards']['value']} "
          f"(conf: {state['board_cards']['confidence']:.2%})")
    
    if 'stack' in state:
        print(f"[+] Stack: {state['stack']['value']:.1f}bb "
              f"(conf: {state['stack']['confidence']:.2%}, "
              f"fallback: {state['stack']['fallback_used']})")
    
    # Extract agent metrics
    agent_metrics = state['agent_metrics']
    print(f"[+] Agent Position: {agent_metrics['position']}")
    print(f"[+] Resource Bucket: {agent_metrics['resource_bucket']}")
    print(f"[+] Engagement Ratio: {agent_metrics['engagement_ratio']:.2%}")
    print(f"[+] Success Rate: {agent_metrics['success_rate']:.2%}")
    
    print()
    print("-" * 70)
    print("Step 2: Decision Generation")
    print("-" * 70)
    
    # Build context
    context = AgentContext(
        position=Position[agent_metrics['position']],
        resource_bucket=agent_metrics['resource_bucket'],
        opponent_models={},
        session_state={
            'engagement_ratio': agent_metrics['engagement_ratio'],
            'hands_played': agent_metrics['hands_played']
        }
    )
    
    # Generate decision
    decision = generate_simulated_decision(
        agent_state=state['hero_cards']['value'],
        environment=state['board_cards']['value'],
        street=Street.FLOP,
        pot_bb=12.0,
        to_call_bb=0.0,
        context=context,
        use_monte_carlo=True,
        num_simulations=500
    )
    
    print(f"[+] Action: {decision.action}")
    print(f"[+] Sizing: {decision.sizing}bb" if decision.sizing else "[+] Sizing: None")
    print(f"[+] Confidence: {decision.confidence:.2%}")
    print(f"[+] Equity: {decision.equity:.2%}")
    print(f"[+] Line Type: {decision.line_type}")
    print(f"[+] Reasoning: {decision.reasoning.get('line_type', 'N/A')}")
    
    print()
    print("-" * 70)
    print("Step 3: Action Output Simulation (with Variance)")
    print("-" * 70)
    
    # Map decision to action
    from sim_engine.decision import SimulatedActionType
    
    action_map = {
        SimulatedActionType.INCREMENT: "bet_raise",
        SimulatedActionType.HOLD: "check_call",
        SimulatedActionType.DECREMENT: "fold",
        SimulatedActionType.CHECK: "check_call"
    }
    
    action = action_map.get(decision.action, "check_call")
    
    # Simulate output
    output_metadata = output_sim.simulate_action(
        action=action,
        sizing=decision.sizing,
        dry_run=True
    )
    
    print(f"[+] Action to Execute: {output_metadata['action']}")
    print(f"[+] Pre-Action Delay: {output_metadata['pre_delay_seconds']:.2f}s")
    print(f"[+] Mouse Path Waypoints: {output_metadata['path_waypoints']}")
    print(f"[+] Curved Path Enabled: {output_metadata['curved_path_used']}")
    print(f"[+] Total Execution Time: {output_metadata['total_execution_seconds']:.2f}s")
    
    print()
    print("-" * 70)
    print("Multi-Iteration Variance Demo")
    print("-" * 70)
    
    print("\nRunning 5 iterations to show realistic variance...")
    print()
    
    delays = []
    
    for i in range(1, 6):
        # Re-extract (small state variance)
        state_iter = extractor.extract_full_state()
        
        # Re-decide
        context_iter = AgentContext(
            position=Position[state_iter['agent_metrics']['position']],
            resource_bucket=state_iter['agent_metrics']['resource_bucket'],
            opponent_models={},
            session_state={}
        )
        
        decision_iter = generate_simulated_decision(
            agent_state=state_iter['hero_cards']['value'],
            environment=state_iter['board_cards']['value'],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context_iter,
            use_monte_carlo=False
        )
        
        # Output
        output_iter = output_sim.simulate_action(
            action=action_map.get(decision_iter.action, "check_call"),
            dry_run=True
        )
        
        delay = output_iter['pre_delay_seconds']
        delays.append(delay)
        
        print(f"  Iteration {i}: Delay={delay:.2f}s, "
              f"Confidence={state_iter['overall_confidence']:.2%}, "
              f"Action={decision_iter.action}")
    
    print()
    print(f"Delay Variance: {max(delays) - min(delays):.2f}s")
    print(f"Delay Range: {min(delays):.2f}s - {max(delays):.2f}s")
    
    print()
    print("=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print()
    print("Educational Note:")
    print("  This pipeline demonstrates realistic state extraction, decision-making,")
    print("  and action execution with variance for multi-agent game theory research.")
    print("  All components include fallback mechanisms and confidence tracking.")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
