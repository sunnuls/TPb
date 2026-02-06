@echo off
REM Test script for simulation API endpoints (Windows)
REM Educational Use Only: For game theory research and testing

echo ============================================================
echo Testing Simulation API Endpoints
echo Educational Use Only - Game Theory Research
echo ============================================================
echo.

set BASE_URL=http://localhost:8000

echo --- Test 1: Basic Decision (Top Pair on Flop) ---
curl -X POST "%BASE_URL%/sim/decide" ^
  -H "Content-Type: application/json" ^
  -d "{\"agent_id\": \"agent_001\", \"agent_state\": [\"Ah\", \"Ks\"], \"environment\": [\"Ad\", \"7c\", \"2s\"], \"street\": \"flop\", \"pot_bb\": 12.0, \"to_call_bb\": 0.0, \"position\": \"BTN\", \"resource_bucket\": \"high\", \"use_monte_carlo\": true, \"num_simulations\": 500}"
echo.
echo.

echo --- Test 2: Preflop Decision (Pocket Aces) ---
curl -X POST "%BASE_URL%/sim/decide" ^
  -H "Content-Type: application/json" ^
  -d "{\"agent_id\": \"agent_002\", \"agent_state\": [\"As\", \"Ad\"], \"environment\": [], \"street\": \"preflop\", \"pot_bb\": 1.5, \"to_call_bb\": 0.0, \"position\": \"BTN\", \"resource_bucket\": \"high\"}"
echo.
echo.

echo --- Test 3: Facing Bet (Flush Draw) ---
curl -X POST "%BASE_URL%/sim/decide" ^
  -H "Content-Type: application/json" ^
  -d "{\"agent_id\": \"agent_003\", \"agent_state\": [\"Kh\", \"Qh\"], \"environment\": [\"Ah\", \"7h\", \"2c\"], \"street\": \"flop\", \"pot_bb\": 12.0, \"to_call_bb\": 4.0, \"position\": \"BB\", \"resource_bucket\": \"medium\", \"use_monte_carlo\": true, \"num_simulations\": 1000}"
echo.
echo.

echo --- Test 4: Equity Calculation ---
curl -X POST "%BASE_URL%/sim/equity" ^
  -H "Content-Type: application/json" ^
  -d "{\"hero_hand\": [\"Ah\", \"Kh\"], \"villain_hand\": [\"Qd\", \"Jd\"], \"board\": [\"Kc\", \"7h\", \"2s\"], \"num_simulations\": 1000}"
echo.
echo.

echo ============================================================
echo All tests complete
echo ============================================================
pause
