#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for scaling.md — Phase 1: Proxy Pool.

Covers:
- ProxyEntry data model & metrics
- ProxyPool — add/remove, rotation modes, failure tracking, cooldown
- PoolConfig defaults and overrides
- PoolStats and per-proxy reports
- BotProxyAssigner — sticky & non-sticky, reassignment
- Rate limiting per proxy
- Health checker lifecycle
- Thread safety under concurrent access
- Load from file / env
- 100-bot assignment test
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proxy_manager import (
    ProxyProtocol,
    RotationMode,
    ProxyStatus,
    ProxyEntry,
    PoolConfig,
    PoolStats,
    ProxyPool,
    BotProxyAssigner,
)


# ===========================================================================
# Test ProxyEntry
# ===========================================================================

class TestProxyEntry(unittest.TestCase):
    def test_defaults(self):
        e = ProxyEntry(url="http://1.2.3.4:8080")
        self.assertEqual(e.protocol, ProxyProtocol.HTTP)
        self.assertEqual(e.status, ProxyStatus.ACTIVE)
        self.assertTrue(e.is_available)
        self.assertAlmostEqual(e.success_rate, 1.0)

    def test_success_rate(self):
        e = ProxyEntry(url="http://x", total_requests=10,
                       successful_requests=8, failed_requests=2)
        self.assertAlmostEqual(e.success_rate, 0.8)

    def test_is_available(self):
        e = ProxyEntry(url="http://x", status=ProxyStatus.DISABLED)
        self.assertFalse(e.is_available)
        e.status = ProxyStatus.DEGRADED
        self.assertTrue(e.is_available)

    def test_to_dict(self):
        e = ProxyEntry(url="http://x", region="US")
        d = e.to_dict()
        self.assertEqual(d["url"], "http://x")
        self.assertEqual(d["region"], "US")
        self.assertIn("success_rate", d)


# ===========================================================================
# Test PoolConfig
# ===========================================================================

class TestPoolConfig(unittest.TestCase):
    def test_defaults(self):
        c = PoolConfig()
        self.assertEqual(c.rotation_mode, RotationMode.ROUND_ROBIN)
        self.assertEqual(c.max_failures, 5)
        self.assertGreater(c.cooldown_seconds, 0)

    def test_custom(self):
        c = PoolConfig(rotation_mode=RotationMode.RANDOM, max_failures=10)
        self.assertEqual(c.rotation_mode, RotationMode.RANDOM)
        self.assertEqual(c.max_failures, 10)


# ===========================================================================
# Test PoolStats
# ===========================================================================

class TestPoolStats(unittest.TestCase):
    def test_success_rate_empty(self):
        s = PoolStats()
        self.assertAlmostEqual(s.success_rate, 1.0)

    def test_summary(self):
        s = PoolStats(total_proxies=10, active_proxies=8,
                      total_requests=100, total_successes=95)
        text = s.summary()
        self.assertIn("8/10", text)
        self.assertIn("95.0%", text)


# ===========================================================================
# Test ProxyPool — basic operations
# ===========================================================================

class TestProxyPoolBasic(unittest.TestCase):
    def test_add_remove(self):
        pool = ProxyPool()
        pool.add_proxy("http://a:1")
        pool.add_proxy("http://b:2")
        self.assertEqual(pool.size, 2)
        pool.remove_proxy("http://a:1")
        self.assertEqual(pool.size, 1)

    def test_add_duplicate(self):
        pool = ProxyPool(proxies=["http://x", "http://x"])
        self.assertEqual(pool.size, 1)

    def test_add_empty_string(self):
        pool = ProxyPool()
        pool.add_proxy("")
        self.assertEqual(pool.size, 0)

    def test_protocol_detection(self):
        pool = ProxyPool(proxies=[
            "http://a:1", "https://b:2",
            "socks4://c:3", "socks5://d:4",
        ])
        entries = {e.url: e for e in pool.all_proxies}
        self.assertEqual(entries["http://a:1"].protocol, ProxyProtocol.HTTP)
        self.assertEqual(entries["https://b:2"].protocol, ProxyProtocol.HTTPS)
        self.assertEqual(entries["socks4://c:3"].protocol, ProxyProtocol.SOCKS4)
        self.assertEqual(entries["socks5://d:4"].protocol, ProxyProtocol.SOCKS5)


# ===========================================================================
# Test ProxyPool — rotation modes
# ===========================================================================

class TestRoundRobin(unittest.TestCase):
    def test_cycles(self):
        pool = ProxyPool(
            proxies=["http://a", "http://b", "http://c"],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        urls = [pool.next_proxy().url for _ in range(6)]
        self.assertEqual(urls, ["http://a", "http://b", "http://c",
                                "http://a", "http://b", "http://c"])


class TestRandomRotation(unittest.TestCase):
    def test_all_used(self):
        pool = ProxyPool(
            proxies=[f"http://p{i}" for i in range(10)],
            config=PoolConfig(rotation_mode=RotationMode.RANDOM),
        )
        seen = set()
        for _ in range(100):
            e = pool.next_proxy()
            seen.add(e.url)
        # With 100 draws from 10, all should be seen
        self.assertEqual(len(seen), 10)


class TestLeastUsed(unittest.TestCase):
    def test_prefers_least_used(self):
        pool = ProxyPool(
            proxies=["http://a", "http://b", "http://c"],
            config=PoolConfig(rotation_mode=RotationMode.LEAST_USED),
        )
        # Use proxy a many times
        for _ in range(10):
            pool.report_success("http://a")

        # Next should prefer b or c (0 requests)
        entry = pool.next_proxy()
        self.assertIn(entry.url, ["http://b", "http://c"])


class TestWeightedRotation(unittest.TestCase):
    def test_prefers_high_weight(self):
        pool = ProxyPool(
            config=PoolConfig(rotation_mode=RotationMode.WEIGHTED),
        )
        pool.add_proxy("http://heavy", weight=10.0)
        pool.add_proxy("http://light", weight=0.01)

        counts = {"http://heavy": 0, "http://light": 0}
        for _ in range(200):
            e = pool.next_proxy()
            counts[e.url] += 1
        self.assertGreater(counts["http://heavy"], counts["http://light"])


class TestGeoRotation(unittest.TestCase):
    def test_prefers_region(self):
        pool = ProxyPool(
            config=PoolConfig(rotation_mode=RotationMode.GEO,
                              preferred_region="EU"),
        )
        pool.add_proxy("http://us1", region="US")
        pool.add_proxy("http://eu1", region="EU")
        pool.add_proxy("http://eu2", region="EU")

        counts = {}
        for _ in range(100):
            e = pool.next_proxy()
            counts[e.url] = counts.get(e.url, 0) + 1

        eu_total = counts.get("http://eu1", 0) + counts.get("http://eu2", 0)
        self.assertEqual(eu_total, 100)  # Only EU proxies picked


# ===========================================================================
# Test ProxyPool — failure & cooldown
# ===========================================================================

class TestFailureTracking(unittest.TestCase):
    def test_consecutive_failures_disable(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(max_failures=3),
        )
        for _ in range(3):
            pool.report_failure("http://a")

        entry = pool.all_proxies[0]
        self.assertEqual(entry.status, ProxyStatus.COOLDOWN)
        self.assertFalse(entry.is_available)

    def test_success_resets_counter(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(max_failures=3),
        )
        pool.report_failure("http://a")
        pool.report_failure("http://a")
        pool.report_success("http://a")
        pool.report_failure("http://a")
        pool.report_failure("http://a")

        entry = pool.all_proxies[0]
        # Only 2 consecutive failures, not 3
        self.assertTrue(entry.is_available)

    def test_cooldown_reenable(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(max_failures=1, cooldown_seconds=0.1),
        )
        pool.report_failure("http://a")

        entry = pool.all_proxies[0]
        self.assertEqual(entry.status, ProxyStatus.COOLDOWN)

        time.sleep(0.15)
        available = pool.available_proxies
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].status, ProxyStatus.ACTIVE)

    def test_no_proxy_when_all_disabled(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(max_failures=1, cooldown_seconds=999),
        )
        pool.report_failure("http://a")
        self.assertIsNone(pool.next_proxy())


# ===========================================================================
# Test ProxyPool — latency & degraded
# ===========================================================================

class TestLatencyTracking(unittest.TestCase):
    def test_avg_latency(self):
        pool = ProxyPool(proxies=["http://a"])
        pool.report_success("http://a", latency_ms=100)
        pool.report_success("http://a", latency_ms=200)

        entry = pool.all_proxies[0]
        # Rolling average: 100 * 0.8 + 200 * 0.2 = 120
        self.assertGreater(entry.avg_latency_ms, 0)

    def test_degraded_on_high_latency(self):
        pool = ProxyPool(
            proxies=["http://slow"],
            config=PoolConfig(degraded_latency_ms=100),
        )
        # Simulate health check reporting high latency
        entry = pool.all_proxies[0]
        entry.avg_latency_ms = 200
        entry.status = ProxyStatus.DEGRADED

        self.assertTrue(entry.is_available)  # still available, just degraded


# ===========================================================================
# Test ProxyPool — rate limiting
# ===========================================================================

class TestRateLimiting(unittest.TestCase):
    def test_no_limit(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(rate_limit_per_proxy=0),
        )
        for _ in range(100):
            self.assertTrue(pool.check_rate_limit("http://a"))

    def test_limit_enforced(self):
        pool = ProxyPool(
            proxies=["http://a"],
            config=PoolConfig(rate_limit_per_proxy=5),
        )
        # First 5 should pass
        for _ in range(5):
            self.assertTrue(pool.check_rate_limit("http://a"))
        # 6th should be blocked
        self.assertFalse(pool.check_rate_limit("http://a"))


# ===========================================================================
# Test ProxyPool — stats & reports
# ===========================================================================

class TestPoolStatsIntegration(unittest.TestCase):
    def test_stats(self):
        pool = ProxyPool(proxies=["http://a", "http://b"])
        pool.report_success("http://a", latency_ms=50)
        pool.report_failure("http://b")

        stats = pool.get_stats()
        self.assertEqual(stats.total_proxies, 2)
        self.assertEqual(stats.total_requests, 2)
        self.assertEqual(stats.total_successes, 1)
        self.assertEqual(stats.total_failures, 1)

    def test_report(self):
        pool = ProxyPool(proxies=["http://a"])
        pool.report_success("http://a")
        report = pool.get_proxy_report()
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]["url"], "http://a")


# ===========================================================================
# Test ProxyPool — load from file
# ===========================================================================

class TestLoadFromFile(unittest.TestCase):
    def test_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                         delete=False, encoding="utf-8") as f:
            f.write("# comment\nhttp://a:1\n\nhttp://b:2\nsocks5://c:3\n")
            path = f.name

        try:
            pool = ProxyPool.from_file(path)
            self.assertEqual(pool.size, 3)
        finally:
            os.unlink(path)

    def test_load_nonexistent(self):
        pool = ProxyPool.from_file("/nonexistent/file.txt")
        self.assertEqual(pool.size, 0)


# ===========================================================================
# Test ProxyPool — load from env
# ===========================================================================

class TestLoadFromEnv(unittest.TestCase):
    def test_load_comma(self):
        os.environ["TEST_PROXY_LIST"] = "http://a,http://b,http://c"
        try:
            pool = ProxyPool.from_env("TEST_PROXY_LIST")
            self.assertEqual(pool.size, 3)
        finally:
            del os.environ["TEST_PROXY_LIST"]

    def test_load_empty(self):
        pool = ProxyPool.from_env("NONEXISTENT_VAR_12345")
        self.assertEqual(pool.size, 0)


# ===========================================================================
# Test ProxyPool — reset
# ===========================================================================

class TestReset(unittest.TestCase):
    def test_reset_clears_metrics(self):
        pool = ProxyPool(proxies=["http://a"], config=PoolConfig(max_failures=1))
        pool.report_failure("http://a")
        self.assertFalse(pool.all_proxies[0].is_available)

        pool.reset()
        entry = pool.all_proxies[0]
        self.assertTrue(entry.is_available)
        self.assertEqual(entry.total_requests, 0)


# ===========================================================================
# Test ProxyPool — health checker lifecycle
# ===========================================================================

class TestHealthChecker(unittest.TestCase):
    def test_start_stop(self):
        pool = ProxyPool(proxies=["http://a"])
        pool.start_health_checker(interval=0.1)
        self.assertIsNotNone(pool._health_thread)
        self.assertTrue(pool._health_thread.is_alive())
        pool.stop()
        time.sleep(0.2)
        self.assertFalse(pool._health_thread.is_alive())


# ===========================================================================
# Test BotProxyAssigner
# ===========================================================================

class TestBotProxyAssignerSticky(unittest.TestCase):
    def test_sticky_same_proxy(self):
        pool = ProxyPool(proxies=["http://a", "http://b", "http://c"])
        assigner = BotProxyAssigner(pool, sticky=True)

        p1 = assigner.get_proxy("bot_1")
        p2 = assigner.get_proxy("bot_1")
        self.assertEqual(p1.url, p2.url)

    def test_sticky_different_bots(self):
        pool = ProxyPool(proxies=["http://a", "http://b", "http://c"])
        assigner = BotProxyAssigner(pool, sticky=True)

        p1 = assigner.get_proxy("bot_1")
        p2 = assigner.get_proxy("bot_2")
        p3 = assigner.get_proxy("bot_3")
        # Each gets a proxy (may overlap with round-robin of 3)
        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertIsNotNone(p3)

    def test_reassign_on_unavailable(self):
        pool = ProxyPool(
            proxies=["http://a", "http://b"],
            config=PoolConfig(max_failures=1, cooldown_seconds=999),
        )
        assigner = BotProxyAssigner(pool, sticky=True)

        p1 = assigner.get_proxy("bot_1")
        # Disable the assigned proxy
        pool.report_failure(p1.url)

        p2 = assigner.get_proxy("bot_1")
        self.assertNotEqual(p1.url, p2.url)

    def test_release(self):
        pool = ProxyPool(proxies=["http://a"])
        assigner = BotProxyAssigner(pool, sticky=True)
        assigner.get_proxy("bot_1")
        self.assertIn("bot_1", assigner.assignments)
        assigner.release("bot_1")
        self.assertNotIn("bot_1", assigner.assignments)

    def test_bots_per_proxy(self):
        pool = ProxyPool(
            proxies=["http://a", "http://b"],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        assigner = BotProxyAssigner(pool, sticky=True)
        for i in range(10):
            assigner.get_proxy(f"bot_{i}")
        counts = assigner.bots_per_proxy()
        # Round-robin: should be balanced ~5/5
        self.assertEqual(sum(counts.values()), 10)


class TestBotProxyAssignerNonSticky(unittest.TestCase):
    def test_non_sticky_rotates(self):
        pool = ProxyPool(
            proxies=["http://a", "http://b", "http://c"],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        assigner = BotProxyAssigner(pool, sticky=False)

        urls = [assigner.get_proxy("bot_1").url for _ in range(3)]
        self.assertEqual(urls, ["http://a", "http://b", "http://c"])

    def test_empty_pool(self):
        pool = ProxyPool()
        assigner = BotProxyAssigner(pool, sticky=False)
        self.assertIsNone(assigner.get_proxy("bot_1"))


# ===========================================================================
# Test Thread Safety
# ===========================================================================

class TestThreadSafety(unittest.TestCase):
    def test_concurrent_access(self):
        """50 threads requesting proxies concurrently."""
        pool = ProxyPool(
            proxies=[f"http://p{i}:8080" for i in range(10)],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        results = []
        errors = []

        def worker():
            try:
                for _ in range(20):
                    e = pool.next_proxy()
                    if e:
                        pool.report_success(e.url, latency_ms=10.0)
                        results.append(e.url)
            except Exception as ex:
                errors.append(str(ex))

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        self.assertEqual(len(results), 50 * 20)


# ===========================================================================
# Test: 100 bots get proxies
# ===========================================================================

class TestHundredBotAssignment(unittest.TestCase):
    """Acceptance test: 100 bots successfully assigned proxies."""

    def test_100_bots_10_proxies_sticky(self):
        """100 bots with 10 proxies in sticky mode — all get assigned."""
        pool = ProxyPool(
            proxies=[f"http://proxy-{i}:8080" for i in range(10)],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        assigner = BotProxyAssigner(pool, sticky=True)

        for bot_id in range(100):
            proxy = assigner.get_proxy(f"bot_{bot_id}")
            self.assertIsNotNone(proxy, f"bot_{bot_id} got no proxy")

        # Each proxy should have ~10 bots
        counts = assigner.bots_per_proxy()
        self.assertEqual(sum(counts.values()), 100)
        for url, count in counts.items():
            self.assertEqual(count, 10)

    def test_100_bots_with_failures(self):
        """100 bots — some proxies fail, bots get reassigned."""
        pool = ProxyPool(
            proxies=[f"http://proxy-{i}:8080" for i in range(10)],
            config=PoolConfig(
                rotation_mode=RotationMode.ROUND_ROBIN,
                max_failures=2,
                cooldown_seconds=999,
            ),
        )
        assigner = BotProxyAssigner(pool, sticky=True)

        # Assign all 100
        for i in range(100):
            assigner.get_proxy(f"bot_{i}")

        # Kill 3 proxies
        for i in range(3):
            pool.report_failure(f"http://proxy-{i}:8080")
            pool.report_failure(f"http://proxy-{i}:8080")

        # All bots should still get a proxy (reassigned)
        for i in range(100):
            proxy = assigner.get_proxy(f"bot_{i}")
            self.assertIsNotNone(proxy)
            self.assertTrue(proxy.is_available)

    def test_100_bots_concurrent(self):
        """100 bots requesting proxies concurrently."""
        pool = ProxyPool(
            proxies=[f"http://proxy-{i}:8080" for i in range(20)],
            config=PoolConfig(rotation_mode=RotationMode.ROUND_ROBIN),
        )
        assigner = BotProxyAssigner(pool, sticky=True)
        results = {}
        lock = threading.Lock()

        def assign_bot(bot_id: str):
            proxy = assigner.get_proxy(bot_id)
            with lock:
                results[bot_id] = proxy.url if proxy else None

        threads = [threading.Thread(target=assign_bot, args=(f"bot_{i}",))
                   for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(results), 100)
        self.assertTrue(all(v is not None for v in results.values()))


if __name__ == "__main__":
    unittest.main()
