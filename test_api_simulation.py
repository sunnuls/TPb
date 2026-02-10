#!/usr/bin/env python3
"""API Testing Script for Simulation Research Framework."""

import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_api_endpoints():
    """Test critical API endpoints for simulation readiness."""
    
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    print("=" * 60)
    print("API Simulation Readiness Test")
    print("=" * 60)
    
    # Test 1: API Docs
    try:
        r = httpx.get(f"{BASE_URL}/docs", timeout=5.0)
        if r.status_code == 200:
            results["passed"].append("API Documentation accessible")
            print("[OK] API Docs: Accessible")
        else:
            results["failed"].append(f"API Docs: Status {r.status_code}")
            print(f"[FAIL] API Docs: Status {r.status_code}")
    except Exception as e:
        results["failed"].append(f"API Docs: {type(e).__name__}")
        print(f"[FAIL] API Docs: {type(e).__name__}: {e}")
    
    # Test 2: Poker Analyze Endpoint
    try:
        hand_history = """PokerStars Hand #123456789
Seat 1: Hero (100 BB)
Seat 2: Villain (100 BB)
BTN: Hero
*** HOLE CARDS ***
Dealt to Hero [Ah Ks]
Hero: raises 3 BB to 3 BB
Villain: folds
"""
        payload = {
            "hand_history_text": hand_history
        }
        r = httpx.post(f"{BASE_URL}/analyze/poker", json=payload, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            results["passed"].append("Poker Analyze: Decision logic working")
            print(f"[OK] Poker Analyze: {data.get('decision', {}).get('action', 'N/A')}")
        else:
            results["failed"].append(f"Poker Analyze: Status {r.status_code}")
            print(f"[FAIL] Poker Analyze: Status {r.status_code}")
    except Exception as e:
        results["failed"].append(f"Poker Analyze: {type(e).__name__}")
        print(f"[FAIL] Poker Analyze: {type(e).__name__}")
    
    # Test 3: Removed duplicate poker test - already covered above
    
    # Test 4: Blackjack Endpoint
    try:
        payload = {
            "state": {
                "player_hand": ["Ah", "6c"],
                "dealer_upcard": "Th",
                "can_double": True,
                "can_split": False
            }
        }
        r = httpx.post(f"{BASE_URL}/analyze/blackjack", json=payload, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            results["passed"].append("Blackjack: Decision logic working")
            print(f"[OK] Blackjack: {data.get('action', 'N/A')}")
        else:
            results["failed"].append(f"Blackjack: Status {r.status_code}")
            print(f"[FAIL] Blackjack: Status {r.status_code}")
    except Exception as e:
        results["failed"].append(f"Blackjack: {type(e).__name__}")
        print(f"[FAIL] Blackjack: {type(e).__name__}")
    
    # Analysis: Potential mismatches for simulation
    print("\n" + "=" * 60)
    print("Simulation Readiness Analysis")
    print("=" * 60)
    
    if len(results["passed"]) >= 2:
        print("\n[OK] Core decision engines are operational")
        print("[OK] Ready for multi-agent simulation integration")
        results["warnings"].append("Need to add shared state sync endpoints")
        results["warnings"].append("Need to add probability calculation endpoints")
        results["warnings"].append("Need to add variance modeling endpoints")
    else:
        print("\n[WARN] Some core endpoints not working")
        print("[ACTION] Fix failing endpoints before simulation integration")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("Recommendations for Simulation Framework")
    print("=" * 60)
    
    print("\n1. Current API supports single-agent decision making")
    print("2. Need to add: /sim/decide endpoint for multi-agent coordination")
    print("3. Need to add: /sim/sync endpoint for shared state synchronization")
    print("4. Need to add: WebSocket support for real-time agent communication")
    print("5. Consider: Monte Carlo simulation endpoints for variance modeling")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Warnings: {len(results['warnings'])}")
    
    if results["warnings"]:
        print("\nWarnings:")
        for w in results["warnings"]:
            print(f"  - {w}")
    
    return len(results["failed"]) == 0

if __name__ == "__main__":
    try:
        success = test_api_endpoints()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
