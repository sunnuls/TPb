"""Test imports to find memory error."""

print("1. Importing basic modules...")
from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position
print("   OK: schemas imported")

print("2. Importing engine...")
try:
    from coach_app.engine import Range
    print("   OK: Range imported")
except Exception as e:
    print(f"   FAIL: Range - {e}")

try:
    from coach_app.engine import calculate_monte_carlo_equity
    print("   OK: calculate_monte_carlo_equity imported")
except Exception as e:
    print(f"   FAIL: calculate_monte_carlo_equity - {e}")

try:
    from coach_app.engine import recommend_postflop
    print("   OK: recommend_postflop imported")
except Exception as e:
    print(f"   FAIL: recommend_postflop - {e}")

try:
    from coach_app.engine import recommend_preflop
    print("   OK: recommend_preflop imported")
except Exception as e:
    print(f"   FAIL: recommend_preflop - {e}")

print("\n3. Testing calculate_monte_carlo_equity...")
try:
    equity = calculate_monte_carlo_equity(["Ah", "Kh"], ["Ad", "7c", "2s"], num_simulations=10)
    print(f"   OK: equity = {equity:.2%}")
except Exception as e:
    print(f"   FAIL: {type(e).__name__}: {e}")

print("\nAll import tests complete!")
