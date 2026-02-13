"""
Tests for full_hive_month.md Этап 3 — Манипуляции 3vs1 и клики.

Validates:
  - ManipulationEngine.decide_enhanced() — street-aware escalation
  - Coordinated trap strategy
  - Isolation strategy
  - Dynamic aggression factor (opponent_fold_pct)
  - Statistics tracking per strategy
  - RealActionExecutor new methods:
    click_game_mode, click_table_from_list, scroll_table_list,
    click_join_button, execute_manipulation_action
  - Acceptance: full 3vs1 decision pipeline
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

# -- Manipulation imports --
try:
    from hive.manipulation_logic import (
        ManipulationEngine,
        ManipulationStrategy,
        ManipulationContext,
        ManipulationDecision,
    )
    from sim_engine.collective_decision import (
        ActionType,
        CollectiveState,
    )
    HAS_MANIP = True
except Exception:
    HAS_MANIP = False

# -- RealActionExecutor imports --
try:
    from bridge.action.real_executor import (
        RealActionExecutor,
        RiskLevel,
        ActionCoordinates,
        ExecutionLog,
        ExecutionResult,
    )
    from bridge.safety import SafetyFramework, SafetyMode, SafetyConfig
    HAS_EXECUTOR = True
except Exception:
    HAS_EXECUTOR = False


# ===================================================================
# Helper: create ManipulationContext
# ===================================================================

def _ctx(
    equity: float = 0.70,
    street: str = "flop",
    opponent_in: bool = True,
    to_call: float = 0.0,
    can_raise: bool = True,
    pot: float = 100.0,
    teammates: int = 2,
) -> "ManipulationContext":
    state = CollectiveState(
        collective_cards=["As", "Kh", "Qd", "Jc", "Ts", "9h"],
        collective_equity=equity,
        agent_count=3,
        pot_size=pot,
    )
    return ManipulationContext(
        collective_state=state,
        acting_bot_id="bot_1",
        teammates_in_hand=[f"bot_{i}" for i in range(2, 2 + teammates)],
        opponent_in_hand=opponent_in,
        pot_size=pot,
        to_call=to_call,
        can_raise=can_raise,
        street=street,
        team_id="team_001",
    )


# ===================================================================
# ManipulationEngine.decide_enhanced
# ===================================================================


@unittest.skipUnless(HAS_MANIP, "manipulation_logic not importable")
class TestDecideEnhanced(unittest.TestCase):
    """decide_enhanced() — street-aware escalation."""

    def setUp(self):
        self.engine = ManipulationEngine(
            aggressive_threshold=0.65,
            fold_threshold=0.40,
            enable_manipulation=True,
        )

    def test_high_equity_aggressive(self):
        """Equity > 65% → aggressive squeeze."""
        ctx = _ctx(equity=0.70, street="flop", opponent_in=True)
        d = self.engine.decide_enhanced(ctx)
        self.assertIn(d.strategy, (
            ManipulationStrategy.AGGRESSIVE_SQUEEZE,
            ManipulationStrategy.COORDINATED_TRAP,
        ))
        self.assertIn(d.action, (ActionType.RAISE, ActionType.CALL, ActionType.CHECK))

    def test_very_high_equity_river_escalation(self):
        """Equity=75% + river → street multiplier makes aggressive."""
        ctx = _ctx(equity=0.52, street="river", opponent_in=True, can_raise=True)
        # 0.52 * 1.5 (river) = 0.78 → > 0.75 → aggressive squeeze
        d = self.engine.decide_enhanced(ctx)
        self.assertEqual(d.strategy, ManipulationStrategy.AGGRESSIVE_SQUEEZE)

    def test_trap_on_turn(self):
        """High equity + turn + to_call=0 → coordinated trap (check).
        Use equity 0.56 so adjusted = 0.56*1.2 = 0.672 (>0.65 but <0.75).
        """
        ctx = _ctx(equity=0.56, street="turn", opponent_in=True, to_call=0.0, can_raise=True)
        d = self.engine.decide_enhanced(ctx)
        self.assertEqual(d.strategy, ManipulationStrategy.COORDINATED_TRAP)
        self.assertEqual(d.action, ActionType.CHECK)
        self.assertIn("TRAP", d.coordination_signal)

    def test_low_equity_fold(self):
        """Equity < 40% → controlled fold."""
        ctx = _ctx(equity=0.30, street="flop", opponent_in=True, to_call=50.0)
        d = self.engine.decide_enhanced(ctx)
        self.assertEqual(d.strategy, ManipulationStrategy.CONTROLLED_FOLD)

    def test_medium_equity_pot_building(self):
        """Equity 45% (medium) → pot building."""
        ctx = _ctx(equity=0.45, street="flop", opponent_in=True)
        d = self.engine.decide_enhanced(ctx)
        self.assertEqual(d.strategy, ManipulationStrategy.POT_BUILDING)

    def test_isolation_when_opponent_folds_often(self):
        """Equity 58% + opponent_fold_pct > 60% → isolation."""
        ctx = _ctx(equity=0.58, street="flop", opponent_in=True)
        d = self.engine.decide_enhanced(ctx, opponent_fold_pct=0.70)
        self.assertEqual(d.strategy, ManipulationStrategy.ISOLATION)

    def test_disabled_returns_conservative(self):
        engine = ManipulationEngine(enable_manipulation=False)
        ctx = _ctx(equity=0.80)
        d = engine.decide_enhanced(ctx)
        self.assertIn("Conservative", d.reasoning)

    def test_street_multiplier_values(self):
        self.assertAlmostEqual(self.engine._street_multiplier("preflop"), 0.8)
        self.assertAlmostEqual(self.engine._street_multiplier("flop"), 1.0)
        self.assertAlmostEqual(self.engine._street_multiplier("turn"), 1.2)
        self.assertAlmostEqual(self.engine._street_multiplier("river"), 1.5)
        self.assertAlmostEqual(self.engine._street_multiplier("unknown"), 1.0)


@unittest.skipUnless(HAS_MANIP, "manipulation_logic not importable")
class TestCoordinatedTrap(unittest.TestCase):
    """_coordinated_trap() strategy."""

    def setUp(self):
        self.engine = ManipulationEngine(
            aggressive_threshold=0.65,
            enable_manipulation=True,
        )

    def test_trap_check_first_to_act(self):
        ctx = _ctx(equity=0.70, to_call=0.0, can_raise=True)
        d = self.engine._coordinated_trap(ctx)
        self.assertEqual(d.action, ActionType.CHECK)
        self.assertEqual(d.coordination_signal, "TRAP_CHECK")

    def test_trap_raise_after_bet(self):
        ctx = _ctx(equity=0.70, to_call=50.0, can_raise=True, pot=100.0)
        d = self.engine._coordinated_trap(ctx)
        self.assertEqual(d.action, ActionType.RAISE)
        self.assertEqual(d.amount, 200.0)  # 2x pot
        self.assertEqual(d.coordination_signal, "TRAP_RAISE")

    def test_trap_call_fallback(self):
        ctx = _ctx(equity=0.70, to_call=50.0, can_raise=False)
        d = self.engine._coordinated_trap(ctx)
        self.assertEqual(d.action, ActionType.CALL)


@unittest.skipUnless(HAS_MANIP, "manipulation_logic not importable")
class TestIsolation(unittest.TestCase):
    """_isolation() strategy."""

    def setUp(self):
        self.engine = ManipulationEngine(
            aggressive_threshold=0.65,
            enable_manipulation=True,
        )

    def test_isolation_raise(self):
        ctx = _ctx(equity=0.60, opponent_in=True, teammates=2, can_raise=True, pot=100.0)
        d = self.engine._isolation(ctx)
        self.assertEqual(d.strategy, ManipulationStrategy.ISOLATION)
        self.assertEqual(d.action, ActionType.RAISE)
        self.assertAlmostEqual(d.amount, 120.0)

    def test_isolation_no_opponent_fallback(self):
        ctx = _ctx(equity=0.60, opponent_in=False, teammates=2)
        d = self.engine._isolation(ctx)
        # Falls back to pot building
        self.assertEqual(d.strategy, ManipulationStrategy.POT_BUILDING)


# ===================================================================
# Statistics tracking
# ===================================================================


@unittest.skipUnless(HAS_MANIP, "manipulation_logic not importable")
class TestManipulationStats(unittest.TestCase):
    """Statistics tracking per strategy."""

    def test_stats_after_decisions(self):
        engine = ManipulationEngine(enable_manipulation=True)
        # Make several decisions
        engine.decide_enhanced(_ctx(equity=0.80, street="flop", opponent_in=True))
        engine.decide_enhanced(_ctx(equity=0.30, street="flop", opponent_in=True, to_call=50.0))
        engine.decide_enhanced(_ctx(equity=0.45, street="flop", opponent_in=True))

        stats = engine.get_statistics()
        self.assertEqual(stats["decisions_count"], 3)
        self.assertIsInstance(stats["strategy_counts"], dict)
        total_strat = sum(stats["strategy_counts"].values())
        self.assertEqual(total_strat, 3)


# ===================================================================
# RealActionExecutor new methods (Этап 3)
# ===================================================================


@unittest.skipUnless(HAS_EXECUTOR, "real_executor not importable")
class TestExecutorNewMethods(unittest.TestCase):
    """New click methods: game_mode, table_from_list, join, manipulation."""

    def _make_executor(self):
        """Create executor in UNSAFE mode with mocked pyautogui."""
        cfg = SafetyConfig()
        cfg.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=cfg)
        return RealActionExecutor(
            safety=safety,
            max_risk_level=RiskLevel.HIGH,
            humanization_enabled=False,
        )

    @patch("bridge.action.real_executor.pyautogui")
    @patch("bridge.action.real_executor.PYAUTOGUI_AVAILABLE", True)
    def test_click_game_mode(self, mock_pag):
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        executor = self._make_executor()
        log = executor.click_game_mode(100, 50, mode_name="PLO", image_offset=(10, 20))
        self.assertEqual(log.result, ExecutionResult.SUCCESS)
        self.assertEqual(log.coordinates.button_x, 110)
        self.assertEqual(log.coordinates.button_y, 70)

    @patch("bridge.action.real_executor.pyautogui")
    @patch("bridge.action.real_executor.PYAUTOGUI_AVAILABLE", True)
    def test_click_table_from_list(self, mock_pag):
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        executor = self._make_executor()
        log = executor.click_table_from_list(
            row_index=3,
            list_x=400,
            first_row_y=200,
            row_height=24,
            image_offset=(0, 0),
        )
        self.assertEqual(log.result, ExecutionResult.SUCCESS)
        # y = 200 + 3*24 + 12 = 284
        self.assertEqual(log.coordinates.button_y, 284)

    @patch("bridge.action.real_executor.pyautogui")
    @patch("bridge.action.real_executor.PYAUTOGUI_AVAILABLE", True)
    def test_scroll_table_list(self, mock_pag):
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        executor = self._make_executor()
        log = executor.scroll_table_list(direction="down", amount=5)
        self.assertEqual(log.result, ExecutionResult.SUCCESS)
        mock_pag.scroll.assert_called_once_with(-5)

    @patch("bridge.action.real_executor.pyautogui")
    @patch("bridge.action.real_executor.PYAUTOGUI_AVAILABLE", True)
    def test_click_join_button(self, mock_pag):
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        executor = self._make_executor()
        log = executor.click_join_button(500, 600, image_offset=(10, 10))
        self.assertEqual(log.result, ExecutionResult.SUCCESS)
        self.assertEqual(log.coordinates.button_x, 510)
        self.assertEqual(log.coordinates.button_y, 610)

    @patch("bridge.action.real_executor.pyautogui")
    @patch("bridge.action.real_executor.PYAUTOGUI_AVAILABLE", True)
    def test_execute_manipulation_action(self, mock_pag):
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.FAILSAFE = True
        mock_pag.PAUSE = 0.1
        executor = self._make_executor()
        coords = ActionCoordinates(button_x=300, button_y=400)
        log = executor.execute_manipulation_action(
            action_type="raise",
            coordinates=coords,
            amount=50.0,
            strategy="aggressive_squeeze",
        )
        self.assertEqual(log.result, ExecutionResult.SUCCESS)
        self.assertEqual(log.action_type, "raise")


# ===================================================================
# Acceptance: full 3vs1 decision pipeline
# ===================================================================


@unittest.skipUnless(HAS_MANIP, "manipulation_logic not importable")
class TestAcceptance3vs1Pipeline(unittest.TestCase):
    """Acceptance: full 3vs1 decision pipeline across streets."""

    def test_full_hand_escalation(self):
        """Simulate a full hand: preflop → flop → turn → river.

        Equity stays constant at 70%, but aggression increases with streets.
        """
        engine = ManipulationEngine(
            aggressive_threshold=0.65,
            fold_threshold=0.40,
            enable_manipulation=True,
        )

        streets = ["preflop", "flop", "turn", "river"]
        amounts = []

        for street in streets:
            ctx = _ctx(equity=0.70, street=street, opponent_in=True, pot=100.0)
            d = engine.decide_enhanced(ctx)
            amounts.append(d.amount)

        # River amount should be >= flop amount (street escalation)
        # Filter out None values (e.g., check/call decisions)
        valid = [(s, a) for s, a in zip(streets, amounts) if a is not None]
        if len(valid) >= 2:
            # Last valid amount should be >= first valid amount
            self.assertGreaterEqual(valid[-1][1], valid[0][1])

        stats = engine.get_statistics()
        self.assertEqual(stats["decisions_count"], 4)

    def test_three_bots_different_equity(self):
        """3 bots at same table, different equities → different strategies."""
        engine = ManipulationEngine(
            aggressive_threshold=0.65,
            fold_threshold=0.40,
            enable_manipulation=True,
        )

        equities = [0.80, 0.50, 0.25]
        expected_strategies = [
            ManipulationStrategy.AGGRESSIVE_SQUEEZE,
            ManipulationStrategy.POT_BUILDING,
            ManipulationStrategy.CONTROLLED_FOLD,
        ]

        for eq, expected_strat in zip(equities, expected_strategies):
            ctx = _ctx(equity=eq, street="flop", opponent_in=True, to_call=30.0)
            d = engine.decide_enhanced(ctx)
            self.assertEqual(d.strategy, expected_strat,
                             f"equity={eq} expected {expected_strat.value}, got {d.strategy.value}")

    def test_trap_then_squeeze(self):
        """Turn: check (trap), then opponent bets → raise.
        Use equity 0.56 so adjusted = 0.56*1.2 = 0.672 (trap range).
        """
        engine = ManipulationEngine(
            aggressive_threshold=0.65,
            enable_manipulation=True,
        )

        # Step 1: first to act on turn, adjusted equity in trap range → trap check
        ctx1 = _ctx(equity=0.56, street="turn", opponent_in=True, to_call=0.0, can_raise=True)
        d1 = engine.decide_enhanced(ctx1)
        self.assertEqual(d1.strategy, ManipulationStrategy.COORDINATED_TRAP)
        self.assertEqual(d1.action, ActionType.CHECK)

        # Step 2: opponent bet 50 → now we raise (aggressive squeeze, since to_call>0)
        ctx2 = _ctx(equity=0.56, street="turn", opponent_in=True, to_call=50.0, can_raise=True)
        d2 = engine.decide_enhanced(ctx2)
        self.assertIn(d2.action, (ActionType.RAISE, ActionType.CALL))


if __name__ == "__main__":
    unittest.main()
