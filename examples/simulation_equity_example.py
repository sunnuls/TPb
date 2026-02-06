#!/usr/bin/env python3
"""
Example: Simulated Equity Calculation for Multi-Agent Game Theory Research

This example demonstrates probability calculations for educational simulations
using Monte Carlo methods. Shows how agents can estimate their equity against
opponent models in virtual environments.

Educational Use Only: For game theory research and controlled simulations.
"""

from coach_app.engine import (
    calculate_monte_carlo_equity,
    calculate_equity_vs_specific_hand,
    Range,
)


def example_basic_equity_calculation():
    """
    Example 1: Calculate equity for agent with top pair vs opponent range.
    
    Scenario:
    - Agent state (hero): Ah Ks (Ace-King suited hearts)
    - Environment (board): Ad 7c 2s (flop with top pair for hero)
    - Opponent model: Estimated range based on preflop action
    """
    print("=" * 60)
    print("Example 1: Basic Equity Calculation")
    print("=" * 60)
    
    # Agent's hole cards
    agent_state = ["Ah", "Ks"]
    
    # Observed environment (community cards)
    environment = ["Ad", "7c", "2s"]
    
    # Opponent range model (estimated from their actions)
    # For example: Opponent raised preflop from CO position
    # Estimated range: Premium pairs, strong broadway, suited connectors
    opponent_model = Range(
        hands={
            # Premium pairs
            "AA": 0.9,  # 90% of the time (unlikely given Ad on board)
            "KK": 1.0,
            "QQ": 1.0,
            "JJ": 0.8,
            "TT": 0.7,
            
            # Strong broadway
            "AKs": 0.95,
            "AKo": 0.85,
            "AQs": 0.90,
            "AQo": 0.70,
            "KQs": 0.75,
            
            # Suited connectors
            "JTs": 0.60,
            "T9s": 0.50,
            "98s": 0.40,
        },
        metadata={
            "position": "CO",
            "action": "raise",
            "stack_bucket": "100bb"
        }
    )
    
    print(f"\nAgent State: {agent_state}")
    print(f"Environment: {environment}")
    print(f"Opponent Model: {opponent_model.describe(limit=5)}")
    
    # Calculate simulated equity
    print("\nRunning Monte Carlo simulation (1000 iterations)...")
    
    result = calculate_monte_carlo_equity(
        hero_hand=agent_state,
        opponent_range=opponent_model,
        board=environment,
        num_simulations=1000
    )
    
    print(f"\n--- Equity Results ---")
    print(f"Equity: {result.equity:.1%}")
    print(f"Win: {result.win_count} ({result.win_count/result.total_simulations:.1%})")
    print(f"Tie: {result.tie_count} ({result.tie_count/result.total_simulations:.1%})")
    print(f"Lose: {result.lose_count} ({result.lose_count/result.total_simulations:.1%})")
    print(f"Simulations: {result.total_simulations}")
    print(f"Confidence: {result.confidence:.1%}")
    
    # Decision making based on equity
    print(f"\n--- Simulation Decision Analysis ---")
    if result.equity >= 0.65:
        print("Strong hand: Agent should bet/raise for value")
    elif result.equity >= 0.50:
        print("Marginal hand: Agent should call or make small bet")
    else:
        print("Weak hand: Agent should check/fold")


def example_specific_matchup():
    """
    Example 2: Calculate equity for specific hand matchup.
    
    Useful for analyzing known opponent cards (e.g., in research scenarios
    where both hands are revealed for educational purposes).
    """
    print("\n\n" + "=" * 60)
    print("Example 2: Specific Hand Matchup")
    print("=" * 60)
    
    # Agent 1 state
    agent1_cards = ["Ah", "Kh"]
    
    # Agent 2 state (known for simulation analysis)
    agent2_cards = ["Qd", "Jd"]
    
    # Environment (flop)
    environment = ["Kc", "7h", "2h"]
    
    print(f"\nAgent 1: {agent1_cards} (pair of Kings + flush draw)")
    print(f"Agent 2: {agent2_cards} (high card Queen)")
    print(f"Environment: {environment}")
    
    print("\nRunning simulation...")
    
    result = calculate_equity_vs_specific_hand(
        hero_hand=agent1_cards,
        opponent_hand=agent2_cards,
        board=environment,
        num_simulations=1000
    )
    
    print(f"\n--- Agent 1 Equity vs Agent 2 ---")
    print(f"Equity: {result.equity:.1%}")
    print(f"Win: {result.win_count}")
    print(f"Tie: {result.tie_count}")
    print(f"Lose: {result.lose_count}")


def example_preflop_equity():
    """
    Example 3: Preflop equity calculation (no board cards yet).
    
    Demonstrates equity calculation before any community cards are dealt.
    """
    print("\n\n" + "=" * 60)
    print("Example 3: Preflop Equity")
    print("=" * 60)
    
    # Agent state preflop
    agent_state = ["As", "Ad"]  # Pocket Aces
    
    # Opponent range (calling preflop raise)
    opponent_model = Range(
        hands={
            "KK": 1.0,
            "QQ": 1.0,
            "JJ": 1.0,
            "TT": 0.9,
            "99": 0.8,
            "AKs": 0.95,
            "AKo": 0.85,
            "AQs": 0.90,
            "KQs": 0.70,
        },
        metadata={"action": "call_3bet"}
    )
    
    print(f"\nAgent State: {agent_state} (Pocket Aces)")
    print(f"Opponent Model: {opponent_model.describe(limit=5)}")
    print(f"Environment: [] (preflop)")
    
    print("\nRunning preflop equity simulation...")
    
    result = calculate_monte_carlo_equity(
        hero_hand=agent_state,
        opponent_range=opponent_model,
        board=[],  # No board cards yet
        num_simulations=1000
    )
    
    print(f"\n--- Preflop Equity ---")
    print(f"Equity: {result.equity:.1%}")
    print(f"Note: Aces typically have ~80-85% equity preflop vs single opponent")


def example_draw_scenario():
    """
    Example 4: Equity calculation with drawing hand.
    
    Demonstrates equity for flush draw scenario.
    """
    print("\n\n" + "=" * 60)
    print("Example 4: Draw Scenario (Flush Draw)")
    print("=" * 60)
    
    # Agent with flush draw
    agent_state = ["Kh", "Qh"]
    
    # Environment (flop with 2 hearts)
    environment = ["Ah", "7h", "2c"]
    
    # Opponent likely has pair or better
    opponent_model = Range(
        hands={
            "AA": 0.8,
            "77": 1.0,
            "22": 1.0,
            "A7s": 0.9,
            "A2s": 0.8,
            "KK": 0.7,
            "QQ": 0.7,
        },
        metadata={"action": "cbet_flop"}
    )
    
    print(f"\nAgent State: {agent_state} (flush draw)")
    print(f"Environment: {environment} (2 hearts on board)")
    print(f"Opponent Model: {opponent_model.describe(limit=5)}")
    
    print("\nRunning simulation...")
    
    result = calculate_monte_carlo_equity(
        hero_hand=agent_state,
        opponent_range=opponent_model,
        board=environment,
        num_simulations=1000
    )
    
    print(f"\n--- Draw Equity ---")
    print(f"Equity: {result.equity:.1%}")
    print(f"Note: Flush draw typically has ~35% equity on flop")
    
    # Pot odds analysis
    pot_bb = 12.0
    to_call = 4.0
    pot_odds = to_call / (pot_bb + to_call)
    
    print(f"\n--- Pot Odds Analysis ---")
    print(f"Pot: {pot_bb} BB")
    print(f"To Call: {to_call} BB")
    print(f"Pot Odds: {pot_odds:.1%}")
    print(f"Equity: {result.equity:.1%}")
    
    if result.equity > pot_odds:
        print("Decision: CALL (equity > pot odds)")
    else:
        print("Decision: FOLD (equity < pot odds)")


def example_error_handling():
    """
    Example 5: Demonstrate input validation and error handling.
    
    Shows how the simulation engine rejects inconsistent states.
    """
    print("\n\n" + "=" * 60)
    print("Example 5: Input Validation & Error Handling")
    print("=" * 60)
    
    print("\n--- Test 1: Invalid card format ---")
    try:
        result = calculate_monte_carlo_equity(
            hero_hand=["Ah", "Zz"],  # Invalid rank 'Z'
            opponent_range=Range(hands={"AA": 1.0}),
            board=["Ad", "7c", "2s"],
            num_simulations=100
        )
    except ValueError as e:
        print(f"✓ Caught error: {e}")
    
    print("\n--- Test 2: Duplicate cards ---")
    try:
        result = calculate_monte_carlo_equity(
            hero_hand=["Ah", "As"],
            opponent_range=Range(hands={"AA": 1.0}),
            board=["Ah", "7c", "2s"],  # Ah already in hero hand
            num_simulations=100
        )
    except ValueError as e:
        print(f"✓ Caught error: {e}")
    
    print("\n--- Test 3: Wrong number of hole cards ---")
    try:
        result = calculate_monte_carlo_equity(
            hero_hand=["Ah"],  # Only 1 card
            opponent_range=Range(hands={"AA": 1.0}),
            board=["Ad", "7c", "2s"],
            num_simulations=100
        )
    except ValueError as e:
        print(f"✓ Caught error: {e}")
    
    print("\n--- Test 4: Too many board cards ---")
    try:
        result = calculate_monte_carlo_equity(
            hero_hand=["Ah", "Ks"],
            opponent_range=Range(hands={"AA": 1.0}),
            board=["Ad", "7c", "2s", "Jh", "9d", "8c"],  # 6 cards
            num_simulations=100
        )
    except ValueError as e:
        print(f"✓ Caught error: {e}")
    
    print("\n--- Test 5: Empty opponent range ---")
    try:
        result = calculate_monte_carlo_equity(
            hero_hand=["Ah", "Ks"],
            opponent_range=Range(hands={}),  # Empty range
            board=["Ad", "7c", "2s"],
            num_simulations=100
        )
    except ValueError as e:
        print(f"✓ Caught error: {e}")
    
    print("\n✓ All validation tests passed!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SIMULATION EQUITY CALCULATOR EXAMPLES")
    print("Educational Use Only: Game Theory Research")
    print("=" * 60)
    
    # Run all examples
    example_basic_equity_calculation()
    example_specific_matchup()
    example_preflop_equity()
    example_draw_scenario()
    example_error_handling()
    
    print("\n\n" + "=" * 60)
    print("Examples Complete")
    print("=" * 60)
    print("\nNote: These simulations use deterministic heuristics for")
    print("educational purposes. For production use, integrate with")
    print("libraries like 'treys' or 'pokerkit' for accurate evaluations.")
