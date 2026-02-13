"""
Tests for full_hive_month.md Этап 2 — Обмен картами и коллюзия.

Validates:
  - CentralHub.exchange_hole_cards() — full exchange with validation
  - CentralHub.get_session_cards() / clear_session_cards()
  - CentralHub._validate_exchange() — duplicate detection
  - CollusionActivator.auto_check_and_activate() — auto-activation at 3 bots
  - CollusionActivator.auto_exchange_cards() — full card exchange on activation
  - Acceptance: 3 bots seated → auto-activate → exchange cards → complete
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

# -- CentralHub imports (graceful) --
try:
    from sim_engine.central_hub import (
        CentralHub,
        AgentConnection,
        AgentStatus,
        MessageType,
    )
    HAS_HUB = True
except Exception:
    HAS_HUB = False

# -- Collusion imports (graceful) --
try:
    from hive.collusion_activation import (
        CollusionActivator,
        CollusionSession,
        CollusionMode,
    )
    from hive.bot_pool import BotPool, BotStatus, HiveTeam
    from hive.card_sharing import CardSharingSystem, TeamCardKnowledge
    HAS_COLLUSION = True
except Exception:
    HAS_COLLUSION = False


# ===================================================================
# CentralHub — full exchange hole cards
# ===================================================================


@unittest.skipUnless(HAS_HUB, "CentralHub not importable")
class TestExchangeHoleCards(unittest.TestCase):
    """CentralHub.exchange_hole_cards()"""

    def setUp(self):
        self.hub = CentralHub(host="localhost", port=0)
        self.env = "table_1"

        # Register 3 fake agents
        for i in range(1, 4):
            ws = MagicMock()
            ws.send = AsyncMock()
            conn = AgentConnection(
                agent_id=f"agent_{i}",
                websocket=ws,
                environment_id=self.env,
                status=AgentStatus.ACTIVE,
            )
            self.hub.agents[f"agent_{i}"] = conn
        self.hub.environments[self.env] = {"agent_1", "agent_2", "agent_3"}

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_single_agent_share(self):
        result = self._run(
            self.hub.exchange_hole_cards(self.env, "agent_1", ["As", "Kh"])
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["agents_shared"], 1)
        self.assertFalse(result["exchange_complete"])

    def test_full_exchange_3_agents(self):
        self._run(self.hub.exchange_hole_cards(self.env, "agent_1", ["As", "Kh"]))
        self._run(self.hub.exchange_hole_cards(self.env, "agent_2", ["Qd", "Jc"]))
        result = self._run(
            self.hub.exchange_hole_cards(self.env, "agent_3", ["Ts", "9h"])
        )
        self.assertTrue(result["exchange_complete"])
        self.assertEqual(len(result["collective_known_cards"]), 6)
        self.assertEqual(result["agents_shared"], 3)

    def test_duplicate_card_rejected(self):
        self._run(self.hub.exchange_hole_cards(self.env, "agent_1", ["As", "Kh"]))
        result = self._run(
            self.hub.exchange_hole_cards(self.env, "agent_2", ["As", "Qd"])
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Duplicate", result["error"])

    def test_same_agent_update(self):
        """Same agent can update their own cards."""
        self._run(self.hub.exchange_hole_cards(self.env, "agent_1", ["As", "Kh"]))
        result = self._run(
            self.hub.exchange_hole_cards(self.env, "agent_1", ["2s", "3h"])
        )
        self.assertEqual(result["status"], "ok")
        cards = self.hub.get_session_cards(self.env)
        self.assertEqual(cards["agent_1"], ["2s", "3h"])

    def test_hand_id_tracked(self):
        result = self._run(
            self.hub.exchange_hole_cards(
                self.env, "agent_1", ["As", "Kh"], hand_id="hand_42"
            )
        )
        self.assertEqual(result["hand_id"], "hand_42")

    def test_collective_equity_present(self):
        self._run(self.hub.exchange_hole_cards(self.env, "agent_1", ["As", "Kh"]))
        self._run(self.hub.exchange_hole_cards(self.env, "agent_2", ["Qd", "Jc"]))
        result = self._run(
            self.hub.exchange_hole_cards(self.env, "agent_3", ["Ts", "9h"])
        )
        self.assertIn("collective_equity", result)
        self.assertGreater(result["collective_equity"], 0.0)


@unittest.skipUnless(HAS_HUB, "CentralHub not importable")
class TestGetSessionCards(unittest.TestCase):
    """get_session_cards / clear_session_cards."""

    def setUp(self):
        self.hub = CentralHub(host="localhost", port=0)
        self.env = "env_x"
        # Register 2 agents
        for i in (1, 2):
            ws = MagicMock()
            ws.send = AsyncMock()
            conn = AgentConnection(
                agent_id=f"a{i}", websocket=ws,
                environment_id=self.env, status=AgentStatus.ACTIVE,
            )
            self.hub.agents[f"a{i}"] = conn
        self.hub.environments[self.env] = {"a1", "a2"}

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_get_session_cards(self):
        self._run(self.hub.exchange_hole_cards(self.env, "a1", ["As", "Kh"]))
        cards = self.hub.get_session_cards(self.env)
        self.assertEqual(cards, {"a1": ["As", "Kh"]})

    def test_clear_session_cards(self):
        self._run(self.hub.exchange_hole_cards(self.env, "a1", ["As", "Kh"]))
        self.hub.clear_session_cards(self.env)
        self.assertEqual(self.hub.get_session_cards(self.env), {})

    def test_get_empty_session(self):
        cards = self.hub.get_session_cards("nonexistent")
        self.assertEqual(cards, {})


# ===================================================================
# CollusionActivator — auto-activation when 3 bots seated
# ===================================================================


@unittest.skipUnless(HAS_COLLUSION, "collusion modules not importable")
class TestAutoCheckAndActivate(unittest.TestCase):
    """auto_check_and_activate() — scan teams, auto-activate."""

    def _make_env(self, pool_size=10, table_id="T1"):
        pool = BotPool(group_hash="test", pool_size=pool_size)
        cs = CardSharingSystem(enable_logging=False)
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=cs,
            require_confirmation=False,
            auto_activate=True,
        )
        return pool, cs, activator

    def test_no_teams(self):
        pool, cs, act = self._make_env()
        result = act.auto_check_and_activate()
        self.assertEqual(len(result), 0)

    def test_team_not_seated(self):
        pool, cs, act = self._make_env()
        team = pool.form_team(table_id="T1")
        self.assertIsNotNone(team)
        # bots are SEATED by form_team, but let's unseat one
        first_bot = team.bot_ids[0]
        pool.bots[first_bot].update_status(BotStatus.IDLE)
        pool.bots[first_bot].current_table = None

        result = act.auto_check_and_activate()
        self.assertEqual(len(result), 0)

    def test_auto_activate_one_team(self):
        pool, cs, act = self._make_env()
        team = pool.form_team(table_id="T1")
        self.assertIsNotNone(team)

        result = act.auto_check_and_activate()
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].is_active())
        self.assertEqual(result[0].team_id, team.team_id)

    def test_auto_activate_multiple_teams(self):
        pool, cs, act = self._make_env(pool_size=20)
        t1 = pool.form_team(table_id="T1")
        t2 = pool.form_team(table_id="T2")
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)

        result = act.auto_check_and_activate()
        self.assertEqual(len(result), 2)

    def test_no_duplicate_activation(self):
        """Already-activated team should not be activated again."""
        pool, cs, act = self._make_env()
        team = pool.form_team(table_id="T1")
        self.assertIsNotNone(team)

        r1 = act.auto_check_and_activate()
        self.assertEqual(len(r1), 1)

        r2 = act.auto_check_and_activate()
        self.assertEqual(len(r2), 0)

    def test_statistics_updated(self):
        pool, cs, act = self._make_env()
        pool.form_team(table_id="T1")
        act.auto_check_and_activate()
        stats = act.get_statistics()
        self.assertEqual(stats["auto_activations"], 1)


# ===================================================================
# CollusionActivator — auto_exchange_cards
# ===================================================================


@unittest.skipUnless(HAS_COLLUSION, "collusion modules not importable")
class TestAutoExchangeCards(unittest.TestCase):
    """auto_exchange_cards() — full card exchange upon activation."""

    def _make_activated(self):
        pool = BotPool(group_hash="test", pool_size=10)
        cs = CardSharingSystem(enable_logging=False)
        act = CollusionActivator(
            bot_pool=pool, card_sharing=cs,
            require_confirmation=False, auto_activate=True,
        )
        team = pool.form_team(table_id="T1")
        activated = act.auto_check_and_activate()
        return pool, cs, act, team, activated

    def test_exchange_returns_true(self):
        pool, cs, act, team, _ = self._make_activated()
        bids = team.bot_ids
        card_map = {
            bids[0]: ["As", "Kh"],
            bids[1]: ["Qd", "Jc"],
            bids[2]: ["Ts", "9h"],
        }
        ok = act.auto_exchange_cards(team.team_id, card_map, hand_id="h1")
        self.assertTrue(ok)

    def test_exchange_creates_knowledge(self):
        pool, cs, act, team, _ = self._make_activated()
        bids = team.bot_ids
        card_map = {
            bids[0]: ["As", "Kh"],
            bids[1]: ["Qd", "Jc"],
            bids[2]: ["Ts", "9h"],
        }
        act.auto_exchange_cards(team.team_id, card_map, hand_id="h1")

        knowledge = cs.get_team_knowledge(team.team_id, "T1", "h1")
        self.assertIsNotNone(knowledge)
        self.assertTrue(knowledge.is_complete(expected_bots=3))
        self.assertEqual(len(knowledge.known_cards), 6)

    def test_exchange_records_shares(self):
        pool, cs, act, team, _ = self._make_activated()
        bids = team.bot_ids
        card_map = {bids[0]: ["As", "Kh"], bids[1]: ["Qd", "Jc"], bids[2]: ["Ts", "9h"]}
        act.auto_exchange_cards(team.team_id, card_map)

        session = act.sessions[team.team_id]
        self.assertEqual(session.shares_exchanged, 3)

    def test_exchange_inactive_session_fails(self):
        pool, cs, act, team, _ = self._make_activated()
        act.deactivate_collusion(team.team_id)

        ok = act.auto_exchange_cards(
            team.team_id,
            {team.bot_ids[0]: ["As", "Kh"]},
        )
        self.assertFalse(ok)

    def test_exchange_unknown_team_fails(self):
        pool, cs, act, team, _ = self._make_activated()
        ok = act.auto_exchange_cards("nonexistent", {})
        self.assertFalse(ok)


# ===================================================================
# Acceptance: full pipeline — seat → activate → exchange → complete
# ===================================================================


@unittest.skipUnless(HAS_COLLUSION, "collusion modules not importable")
class TestAcceptanceFullPipeline(unittest.TestCase):
    """Acceptance: 3 bots seat → auto-activate → card exchange → complete."""

    def test_full_pipeline(self):
        """Complete Этап 2 flow end-to-end."""
        pool = BotPool(group_hash="hive", pool_size=10)
        cs = CardSharingSystem(enable_logging=False)
        act = CollusionActivator(
            bot_pool=pool, card_sharing=cs,
            require_confirmation=False, auto_activate=True,
        )

        # Step 1: form team (seats 3 bots)
        team = pool.form_team(table_id="table_A")
        self.assertIsNotNone(team)
        self.assertEqual(len(team.bot_ids), 3)

        # Step 2: auto-activate
        activated = act.auto_check_and_activate()
        self.assertEqual(len(activated), 1)
        session = activated[0]
        self.assertTrue(session.is_active())
        self.assertEqual(session.mode, CollusionMode.ACTIVE)

        # Step 3: exchange cards
        card_map = {
            team.bot_ids[0]: ["As", "Kh"],
            team.bot_ids[1]: ["Qd", "Jc"],
            team.bot_ids[2]: ["7s", "2d"],
        }
        complete = act.auto_exchange_cards(
            team.team_id, card_map, hand_id="hand_001"
        )
        self.assertTrue(complete)

        # Step 4: verify knowledge
        knowledge = cs.get_team_knowledge(team.team_id, "table_A", "hand_001")
        self.assertIsNotNone(knowledge)
        self.assertTrue(knowledge.is_complete())
        self.assertEqual(
            sorted(knowledge.known_cards),
            sorted(["As", "Kh", "Qd", "Jc", "7s", "2d"]),
        )

        # Step 5: verify stats
        stats = act.get_statistics()
        self.assertEqual(stats["activations_succeeded"], 1)
        self.assertEqual(stats["auto_activations"], 1)
        self.assertEqual(stats["total_shares_exchanged"], 3)

    def test_multiple_teams_pipeline(self):
        """2 teams at different tables — both auto-activate and exchange."""
        pool = BotPool(group_hash="hive", pool_size=20)
        cs = CardSharingSystem(enable_logging=False)
        act = CollusionActivator(
            bot_pool=pool, card_sharing=cs,
            require_confirmation=False, auto_activate=True,
        )

        t1 = pool.form_team(table_id="T1")
        t2 = pool.form_team(table_id="T2")
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)

        activated = act.auto_check_and_activate()
        self.assertEqual(len(activated), 2)

        # Exchange for team 1
        ok1 = act.auto_exchange_cards(
            t1.team_id,
            {t1.bot_ids[0]: ["As", "Kh"], t1.bot_ids[1]: ["Qd", "Jc"],
             t1.bot_ids[2]: ["Ts", "9h"]},
            hand_id="h1",
        )
        self.assertTrue(ok1)

        # Exchange for team 2
        ok2 = act.auto_exchange_cards(
            t2.team_id,
            {t2.bot_ids[0]: ["5s", "4h"], t2.bot_ids[1]: ["8d", "7c"],
             t2.bot_ids[2]: ["Ah", "Kd"]},
            hand_id="h1",
        )
        self.assertTrue(ok2)

        stats = act.get_statistics()
        self.assertEqual(stats["auto_activations"], 2)
        self.assertEqual(stats["total_shares_exchanged"], 6)


if __name__ == "__main__":
    unittest.main()
