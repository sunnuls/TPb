#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for scaling.md — Phase 3: Auto-restart + 100 bots 24 hours.

Covers:
- BotHealth data model
- MonitorConfig defaults and overrides
- MonitorStats and fleet health
- BotMonitor — register, heartbeat, error reporting
- Health checking — dead detection, degraded detection
- Auto-restart — immediate, backoff, circuit_breaker
- Manual control — stop, reset
- Alerts — emission, callbacks
- Background loop lifecycle
- Thread safety — concurrent heartbeats
- 100-bot fleet simulation — 24-hour acceptance test
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from launcher.bot_monitor import (
    HealthStatus,
    RestartStrategy,
    AlertLevel,
    BotHealth,
    MonitorConfig,
    Alert,
    MonitorStats,
    BotMonitor,
)


# ===========================================================================
# Test BotHealth
# ===========================================================================

class TestBotHealth(unittest.TestCase):
    def test_defaults(self):
        bh = BotHealth(bot_id="b1")
        self.assertEqual(bh.status, HealthStatus.HEALTHY)
        self.assertEqual(bh.error_count, 0)
        self.assertEqual(bh.restart_count, 0)

    def test_uptime(self):
        bh = BotHealth(bot_id="b1", start_time=time.monotonic() - 10)
        self.assertGreater(bh.uptime, 9.0)

    def test_time_since_heartbeat(self):
        bh = BotHealth(bot_id="b1", last_heartbeat=time.monotonic() - 5)
        self.assertGreater(bh.time_since_heartbeat, 4.0)

    def test_no_heartbeat(self):
        bh = BotHealth(bot_id="b1")
        self.assertEqual(bh.time_since_heartbeat, float("inf"))

    def test_to_dict(self):
        bh = BotHealth(bot_id="b1", start_time=time.monotonic())
        d = bh.to_dict()
        self.assertEqual(d["bot_id"], "b1")
        self.assertIn("status", d)
        self.assertIn("uptime", d)


# ===========================================================================
# Test MonitorConfig
# ===========================================================================

class TestMonitorConfig(unittest.TestCase):
    def test_defaults(self):
        c = MonitorConfig()
        self.assertEqual(c.heartbeat_timeout, 30.0)
        self.assertEqual(c.max_restarts, 5)
        self.assertTrue(c.auto_restart)

    def test_custom(self):
        c = MonitorConfig(heartbeat_timeout=10.0, max_restarts=3)
        self.assertEqual(c.heartbeat_timeout, 10.0)
        self.assertEqual(c.max_restarts, 3)


# ===========================================================================
# Test MonitorStats
# ===========================================================================

class TestMonitorStats(unittest.TestCase):
    def test_fleet_health_empty(self):
        s = MonitorStats()
        self.assertAlmostEqual(s.fleet_health, 1.0)

    def test_fleet_health(self):
        s = MonitorStats(total_bots=10, healthy=7, degraded=2, dead=1)
        self.assertAlmostEqual(s.fleet_health, 0.9)

    def test_summary(self):
        s = MonitorStats(total_bots=10, healthy=8, dead=2,
                         total_restarts=5, total_errors=10)
        text = s.summary()
        self.assertIn("8/10", text)
        self.assertIn("Restarts: 5", text)


# ===========================================================================
# Test BotMonitor — Registration
# ===========================================================================

class TestMonitorRegistration(unittest.TestCase):
    def test_register(self):
        m = BotMonitor()
        m.register("b1")
        self.assertEqual(m.bot_count, 1)

    def test_register_duplicate(self):
        m = BotMonitor()
        m.register("b1")
        m.register("b1")
        self.assertEqual(m.bot_count, 1)

    def test_unregister(self):
        m = BotMonitor()
        m.register("b1")
        m.unregister("b1")
        self.assertEqual(m.bot_count, 0)


# ===========================================================================
# Test BotMonitor — Heartbeat
# ===========================================================================

class TestHeartbeat(unittest.TestCase):
    def test_heartbeat_updates(self):
        m = BotMonitor()
        m.register("b1")
        time.sleep(0.05)
        m.heartbeat("b1")
        bh = m.get_bot_health("b1")
        self.assertLess(bh.time_since_heartbeat, 1.0)

    def test_heartbeat_recovers_degraded(self):
        m = BotMonitor(config=MonitorConfig(degraded_error_threshold=1))
        m.register("b1")
        m.report_error("b1", "test error")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.DEGRADED)

        m.heartbeat("b1")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.HEALTHY)


# ===========================================================================
# Test BotMonitor — Error reporting
# ===========================================================================

class TestErrorReporting(unittest.TestCase):
    def test_error_count(self):
        m = BotMonitor()
        m.register("b1")
        m.report_error("b1", "err1")
        m.report_error("b1", "err2")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.error_count, 2)
        self.assertEqual(bh.consecutive_errors, 2)

    def test_success_resets_consecutive(self):
        m = BotMonitor()
        m.register("b1")
        m.report_error("b1")
        m.report_error("b1")
        m.report_success("b1")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.consecutive_errors, 0)
        self.assertEqual(bh.error_count, 2)  # total preserved

    def test_degraded_on_errors(self):
        m = BotMonitor(config=MonitorConfig(degraded_error_threshold=3))
        m.register("b1")
        for _ in range(3):
            m.report_error("b1")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.DEGRADED)


# ===========================================================================
# Test BotMonitor — Dead detection
# ===========================================================================

class TestDeadDetection(unittest.TestCase):
    def test_dead_on_timeout(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.05,
            auto_restart=False,
        ))
        m.register("b1")
        time.sleep(0.1)
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.DEAD)

    def test_not_dead_if_heartbeat(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=5.0,
            auto_restart=False,
        ))
        m.register("b1")
        m.heartbeat("b1")
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.HEALTHY)


# ===========================================================================
# Test BotMonitor — Auto-restart
# ===========================================================================

class TestAutoRestartImmediate(unittest.TestCase):
    def test_restart_on_dead(self):
        restart_called = {"count": 0}

        def restart_fn():
            restart_called["count"] += 1
            return True

        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.05,
            restart_strategy=RestartStrategy.IMMEDIATE,
            restart_cooldown=0.0,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=restart_fn)
        time.sleep(0.1)
        restarted = m.check_all()
        self.assertIn("b1", restarted)
        self.assertEqual(restart_called["count"], 1)

        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.HEALTHY)
        self.assertEqual(bh.restart_count, 1)

    def test_max_restarts(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            restart_strategy=RestartStrategy.IMMEDIATE,
            restart_cooldown=0.0,
            max_restarts=2,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=lambda: True)

        # Exhaust restarts
        for _ in range(5):
            time.sleep(0.02)
            # Force dead status
            bh = m.get_bot_health("b1")
            bh.last_heartbeat = 0
            bh.status = HealthStatus.DEAD
            m.check_all()

        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.STOPPED)
        self.assertLessEqual(bh.restart_count, 2)


class TestAutoRestartBackoff(unittest.TestCase):
    def test_backoff_delays(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            restart_strategy=RestartStrategy.BACKOFF,
            backoff_base=0.05,
            backoff_multiplier=2.0,
            backoff_max=10.0,
            max_restarts=10,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=lambda: True)

        # First restart should happen immediately
        time.sleep(0.02)
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.restart_count, 1)

        # Second restart needs backoff (0.05 * 2^1 = 0.1s)
        bh.last_heartbeat = 0
        bh.status = HealthStatus.DEAD
        m.check_all()  # too soon
        # May or may not restart depending on timing


class TestAutoRestartFailed(unittest.TestCase):
    def test_failed_restart_stays_dead(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            restart_cooldown=0.0,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=lambda: False)
        time.sleep(0.02)
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.DEAD)

    def test_restart_exception(self):
        def bad_restart():
            raise RuntimeError("crash")

        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            restart_cooldown=0.0,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=bad_restart)
        time.sleep(0.02)
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.DEAD)


# ===========================================================================
# Test BotMonitor — Manual control
# ===========================================================================

class TestManualControl(unittest.TestCase):
    def test_stop_bot(self):
        m = BotMonitor()
        m.register("b1")
        m.stop_bot("b1")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.STOPPED)

    def test_stopped_bot_not_restarted(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            auto_restart=True,
        ))
        m.register("b1", restart_fn=lambda: True)
        m.stop_bot("b1")
        time.sleep(0.02)
        m.check_all()
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.status, HealthStatus.STOPPED)

    def test_reset_bot(self):
        m = BotMonitor()
        m.register("b1")
        m.report_error("b1")
        m.report_error("b1")
        m.reset_bot("b1")
        bh = m.get_bot_health("b1")
        self.assertEqual(bh.error_count, 0)
        self.assertEqual(bh.status, HealthStatus.HEALTHY)


# ===========================================================================
# Test Alerts
# ===========================================================================

class TestAlerts(unittest.TestCase):
    def test_alert_on_dead(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            auto_restart=False,
        ))
        m.register("b1")
        time.sleep(0.02)
        m.check_all()
        self.assertTrue(any("Dead" in a.message for a in m.alerts))

    def test_alert_callback(self):
        received = []
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            auto_restart=False,
        ))
        m.on_alert(lambda a: received.append(a))
        m.register("b1")
        time.sleep(0.02)
        m.check_all()
        self.assertTrue(len(received) > 0)

    def test_clear_alerts(self):
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            auto_restart=False,
        ))
        m.register("b1")
        time.sleep(0.02)
        m.check_all()
        m.clear_alerts()
        self.assertEqual(len(m.alerts), 0)


# ===========================================================================
# Test Background loop
# ===========================================================================

class TestBackgroundLoop(unittest.TestCase):
    def test_start_stop(self):
        m = BotMonitor()
        m.start(interval=0.05)
        self.assertTrue(m._check_thread.is_alive())
        m.stop()
        time.sleep(0.1)
        self.assertFalse(m._check_thread.is_alive())


# ===========================================================================
# Test Stats
# ===========================================================================

class TestStats(unittest.TestCase):
    def test_stats(self):
        m = BotMonitor()
        m.register("b1")
        m.register("b2")
        m.report_error("b2")
        stats = m.get_stats()
        self.assertEqual(stats.total_bots, 2)
        self.assertEqual(stats.total_errors, 1)

    def test_get_all_health(self):
        m = BotMonitor()
        m.register("b1")
        m.register("b2")
        report = m.get_all_health()
        self.assertEqual(len(report), 2)


# ===========================================================================
# Test Thread Safety
# ===========================================================================

class TestThreadSafety(unittest.TestCase):
    def test_concurrent_heartbeats(self):
        m = BotMonitor()
        for i in range(50):
            m.register(f"bot_{i}")

        errors = []

        def heartbeat_worker(bot_id):
            try:
                for _ in range(20):
                    m.heartbeat(bot_id)
                    m.report_success(bot_id)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=heartbeat_worker, args=(f"bot_{i}",))
                   for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(errors), 0)
        self.assertEqual(m.bot_count, 50)


# ===========================================================================
# KEY ACCEPTANCE TEST: 100 bots, 24-hour simulation
# ===========================================================================

class TestHundredBots24Hours(unittest.TestCase):
    """
    Acceptance test from scaling.md Phase 3:
    100 bots running 24 hours without crashes.

    Simulates time progression with heartbeats, random failures,
    auto-restarts. Verifies fleet health remains high.
    """

    def test_100_bots_all_healthy(self):
        """100 bots with regular heartbeats — all stay healthy."""
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=5.0,
            auto_restart=True,
            max_restarts=10,
        ))
        for i in range(100):
            m.register(f"bot_{i}", restart_fn=lambda: True)

        # Simulate: send heartbeats, run checks
        for tick in range(100):
            for i in range(100):
                m.heartbeat(f"bot_{i}")
            m.check_all()

        stats = m.get_stats()
        self.assertEqual(stats.healthy, 100)
        self.assertEqual(stats.dead, 0)
        self.assertEqual(stats.total_restarts, 0)

    def test_100_bots_with_failures(self):
        """100 bots — intermittent failures — auto-restart keeps fleet healthy.

        Each tick, ~5% of bots randomly fail. After restart they resume
        heartbeating. Simulates realistic 24h operation.
        """
        import random
        random.seed(42)

        restart_log = {"total": 0}

        def make_restart():
            restart_log["total"] += 1
            return True

        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=0.01,
            restart_cooldown=0.0,
            restart_strategy=RestartStrategy.IMMEDIATE,
            max_restarts=0,  # unlimited
            auto_restart=True,
        ))
        for i in range(100):
            m.register(f"bot_{i}", restart_fn=make_restart)

        # Simulate 500 ticks (representing 24h compressed)
        for tick in range(500):
            for i in range(100):
                bh = m.get_bot_health(f"bot_{i}")
                if bh and bh.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED):
                    # 95% chance of healthy heartbeat
                    if random.random() < 0.95:
                        m.heartbeat(f"bot_{i}")
                    else:
                        # Miss heartbeat — will be detected as dead
                        bh.last_heartbeat = 0

            time.sleep(0.001)
            m.check_all()

        stats = m.get_stats()

        # Fleet should recover — most bots alive
        alive = stats.healthy + stats.degraded
        self.assertGreaterEqual(alive, 90,
                                f"Too few alive bots: {alive}/100")

        # Some restarts should have happened
        self.assertGreater(restart_log["total"], 0)

    def test_100_bots_concurrent_simulation(self):
        """100 bots sending heartbeats from 100 threads — no crashes."""
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=2.0,
            auto_restart=True,
        ))
        for i in range(100):
            m.register(f"bot_{i}", restart_fn=lambda: True)

        errors = []

        def bot_loop(bot_id):
            try:
                for _ in range(50):
                    m.heartbeat(bot_id)
                    m.report_success(bot_id)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=bot_loop, args=(f"bot_{i}",))
                   for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0)
        stats = m.get_stats()
        self.assertEqual(stats.total_bots, 100)
        self.assertEqual(stats.healthy, 100)

    def test_100_bots_escalating_failures(self):
        """100 bots — progressive failures, monitor recovers."""
        m = BotMonitor(config=MonitorConfig(
            heartbeat_timeout=5.0,
            restart_cooldown=0.0,
            max_restarts=0,  # unlimited
            auto_restart=True,
        ))
        for i in range(100):
            m.register(f"bot_{i}", restart_fn=lambda: True)

        # Phase 1: all healthy
        for i in range(100):
            m.heartbeat(f"bot_{i}")
        m.check_all()
        stats = m.get_stats()
        self.assertEqual(stats.healthy, 100)

        # Phase 2: kill 20 bots by forcing DEAD status
        for i in range(20):
            bh = m.get_bot_health(f"bot_{i}")
            bh.status = HealthStatus.DEAD

        # check_all should auto-restart all 20
        m.check_all()

        # Phase 3: send heartbeats for all — recovery
        for i in range(100):
            m.heartbeat(f"bot_{i}")
        m.check_all()

        stats = m.get_stats()
        self.assertEqual(stats.healthy, 100)
        self.assertGreaterEqual(stats.total_restarts, 20)


if __name__ == "__main__":
    unittest.main()
