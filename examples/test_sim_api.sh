#!/bin/bash
# Test script for simulation API endpoints
# Educational Use Only: For game theory research and testing

echo "============================================================"
echo "Testing Simulation API Endpoints"
echo "Educational Use Only - Game Theory Research"
echo "============================================================"
echo ""

BASE_URL="http://localhost:8000"

echo "--- Test 1: Basic Decision (Top Pair on Flop) ---"
curl -X POST "$BASE_URL/sim/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "agent_state": ["Ah", "Ks"],
    "environment": ["Ad", "7c", "2s"],
    "street": "flop",
    "pot_bb": 12.0,
    "to_call_bb": 0.0,
    "position": "BTN",
    "resource_bucket": "high",
    "use_monte_carlo": true,
    "num_simulations": 500
  }'
echo -e "\n"

echo "--- Test 2: Preflop Decision (Pocket Aces) ---"
curl -X POST "$BASE_URL/sim/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_002",
    "agent_state": ["As", "Ad"],
    "environment": [],
    "street": "preflop",
    "pot_bb": 1.5,
    "to_call_bb": 0.0,
    "position": "BTN",
    "resource_bucket": "high"
  }'
echo -e "\n"

echo "--- Test 3: Facing Bet (Flush Draw) ---"
curl -X POST "$BASE_URL/sim/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_003",
    "agent_state": ["Kh", "Qh"],
    "environment": ["Ah", "7h", "2c"],
    "street": "flop",
    "pot_bb": 12.0,
    "to_call_bb": 4.0,
    "position": "BB",
    "resource_bucket": "medium",
    "use_monte_carlo": true,
    "num_simulations": 1000
  }'
echo -e "\n"

echo "--- Test 4: With Opponent Models ---"
curl -X POST "$BASE_URL/sim/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_004",
    "agent_state": ["Kh", "Qh"],
    "environment": ["Kc", "7h", "2s"],
    "street": "flop",
    "pot_bb": 12.0,
    "to_call_bb": 0.0,
    "position": "BTN",
    "resource_bucket": "high",
    "opponent_models": [
      {
        "name": "tight_player",
        "vpip": 0.15,
        "pfr": 0.12,
        "aggression_factor": 1.8,
        "fold_to_cbet": 0.75
      }
    ]
  }'
echo -e "\n"

echo "--- Test 5: Equity Calculation ---"
curl -X POST "$BASE_URL/sim/equity" \
  -H "Content-Type: application/json" \
  -d '{
    "hero_hand": ["Ah", "Kh"],
    "villain_hand": ["Qd", "Jd"],
    "board": ["Kc", "7h", "2s"],
    "num_simulations": 1000
  }'
echo -e "\n"

echo "============================================================"
echo "All tests complete"
echo "============================================================"
