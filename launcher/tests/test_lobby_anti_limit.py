"""
Tests for LobbyAntiLimit — Phase 3 of lobby_scanner.md.

Tests cover:
  - AdaptiveDelay (base, jitter, backoff, reset)
  - ProxyPool (rotation, health tracking, cooldown, add/remove)
  - CircuitBreaker (closed → open → half-open → closed)
  - LobbyAntiLimit orchestrator (source selection, failover, metrics)
  - ScanStats recording
  - 100-scan stress test (no errors)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import threading
import time
import unittest
from typing import Dict, List, Optional, Tuple, Any

try:
    from launcher.vision.lobby_anti_limit import (
        LobbyAntiLimit,
        ScanSource,
        ScanMetric,
        ScanStats,
        CircuitBreaker,
        CircuitState,
        ProxyPool,
        AdaptiveDelay,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Mock scan functions
# ---------------------------------------------------------------------------


def make_ok_scan(tables: int = 5):
    """Return a scan function that always succeeds."""
    call_count = [0]

    def fn(proxy: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        call_count[0] += 1
        return [{"table_id": f"t{i}"} for i in range(tables)], None

    fn.call_count = call_count  # type: ignore[attr-defined]
    return fn


def make_fail_scan(error: str = "connection refused"):
    """Return a scan function that always fails."""
    call_count = [0]

    def fn(proxy: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        call_count[0] += 1
        return [], error

    fn.call_count = call_count  # type: ignore[attr-defined]
    return fn


def make_flaky_scan(fail_every: int = 3, tables: int = 5):
    """Return a scan function that fails every N calls."""
    call_count = [0]

    def fn(proxy: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
        call_count[0] += 1
        if call_count[0] % fail_every == 0:
            return [], "intermittent error"
        return [{"table_id": f"t{i}"} for i in range(tables)], None

    fn.call_count = call_count  # type: ignore[attr-defined]
    return fn


# ---------------------------------------------------------------------------
# Test: AdaptiveDelay
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestAdaptiveDelay(unittest.TestCase):
    """Test adaptive delay with jitter and backoff."""

    def test_base_delay(self):
        d = AdaptiveDelay(base_delay=1.0, jitter_frac=0.0, backoff_mult=1.0)
        self.assertAlmostEqual(d.current_delay(), 1.0, places=1)

    def test_jitter_range(self):
        d = AdaptiveDelay(base_delay=1.0, jitter_frac=0.5, backoff_mult=1.0)
        delays = [d.current_delay() for _ in range(100)]
        self.assertTrue(all(0.4 <= x <= 1.6 for x in delays),
                        f"Delay out of range: min={min(delays):.2f} max={max(delays):.2f}")

    def test_backoff_on_error(self):
        d = AdaptiveDelay(base_delay=1.0, max_delay=100.0, jitter_frac=0.0, backoff_mult=2.0)
        self.assertAlmostEqual(d.current_delay(), 1.0, places=1)
        d.record_error()
        self.assertAlmostEqual(d.current_delay(), 2.0, places=1)
        d.record_error()
        self.assertAlmostEqual(d.current_delay(), 4.0, places=1)

    def test_backoff_cap(self):
        d = AdaptiveDelay(base_delay=1.0, max_delay=5.0, jitter_frac=0.0, backoff_mult=2.0)
        for _ in range(10):
            d.record_error()
        self.assertLessEqual(d.current_delay(), 5.0)

    def test_success_reduces_backoff(self):
        d = AdaptiveDelay(base_delay=1.0, max_delay=100.0, jitter_frac=0.0, backoff_mult=2.0)
        d.record_error()
        d.record_error()
        d.record_success()
        self.assertAlmostEqual(d.current_delay(), 2.0, places=1)

    def test_reset(self):
        d = AdaptiveDelay(base_delay=1.0, jitter_frac=0.0, backoff_mult=2.0)
        for _ in range(5):
            d.record_error()
        d.reset()
        self.assertAlmostEqual(d.current_delay(), 1.0, places=1)

    def test_wait_actually_sleeps(self):
        d = AdaptiveDelay(base_delay=0.05, jitter_frac=0.0)
        t0 = time.monotonic()
        d.wait()
        elapsed = time.monotonic() - t0
        self.assertGreaterEqual(elapsed, 0.04)


# ---------------------------------------------------------------------------
# Test: ProxyPool
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestProxyPool(unittest.TestCase):
    """Test proxy rotation and health tracking."""

    def test_round_robin(self):
        pool = ProxyPool(["p1", "p2", "p3"])
        seen = [pool.next() for _ in range(6)]
        self.assertEqual(seen, ["p1", "p2", "p3", "p1", "p2", "p3"])

    def test_empty_pool(self):
        pool = ProxyPool()
        self.assertIsNone(pool.next())
        self.assertEqual(pool.size, 0)

    def test_failure_cooldown(self):
        pool = ProxyPool(["p1", "p2"], max_failures=2, cooldown=0.1)
        pool.report_failure("p1")
        pool.report_failure("p1")
        # p1 should be in cooldown
        results = {pool.next() for _ in range(5)}
        self.assertNotIn("p1", results)

        time.sleep(0.15)
        # After cooldown, p1 should be available again
        avail = pool.available
        self.assertIn("p1", avail)

    def test_success_clears_failures(self):
        pool = ProxyPool(["p1"], max_failures=2, cooldown=60.0)
        pool.report_failure("p1")
        pool.report_success("p1")
        # Should still be healthy
        self.assertEqual(pool.next(), "p1")

    def test_add_remove(self):
        pool = ProxyPool(["p1"])
        self.assertEqual(pool.size, 1)
        pool.add("p2")
        self.assertEqual(pool.size, 2)
        pool.remove("p1")
        self.assertEqual(pool.size, 1)
        self.assertEqual(pool.next(), "p2")

    def test_add_duplicate(self):
        pool = ProxyPool(["p1"])
        pool.add("p1")
        self.assertEqual(pool.size, 1)

    def test_reset(self):
        pool = ProxyPool(["p1", "p2"], max_failures=1)
        pool.report_failure("p1")
        pool.reset()
        self.assertEqual(len(pool.available), 2)

    def test_all_unhealthy_returns_none(self):
        pool = ProxyPool(["p1"], max_failures=1, cooldown=60.0)
        pool.report_failure("p1")
        self.assertIsNone(pool.next())


# ---------------------------------------------------------------------------
# Test: CircuitBreaker
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker state machine."""

    def test_starts_closed(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.1)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.allow_request())

    def test_success_closes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        # Half open
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_failure_in_half_open_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        # Half open → fail again
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)


# ---------------------------------------------------------------------------
# Test: ScanStats
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestScanStats(unittest.TestCase):
    """Test stats recording."""

    def test_empty_stats(self):
        s = ScanStats()
        self.assertEqual(s.total_scans, 0)
        self.assertAlmostEqual(s.success_rate, 0.0)

    def test_record_success(self):
        s = ScanStats()
        m = ScanMetric(ScanSource.OCR, True, 50.0, tables_found=5)
        s.record(m)
        self.assertEqual(s.total_scans, 1)
        self.assertEqual(s.successful, 1)
        self.assertEqual(s.total_tables, 5)
        self.assertAlmostEqual(s.success_rate, 1.0)

    def test_record_failure(self):
        s = ScanStats()
        m = ScanMetric(ScanSource.HTTP, False, 100.0, error="timeout")
        s.record(m)
        self.assertEqual(s.failed, 1)
        self.assertAlmostEqual(s.success_rate, 0.0)
        self.assertIn("timeout", s.errors)

    def test_avg_latency(self):
        s = ScanStats()
        s.record(ScanMetric(ScanSource.OCR, True, 10.0))
        s.record(ScanMetric(ScanSource.OCR, True, 30.0))
        self.assertAlmostEqual(s.avg_latency_ms, 20.0)

    def test_source_counts(self):
        s = ScanStats()
        s.record(ScanMetric(ScanSource.OCR, True, 10.0))
        s.record(ScanMetric(ScanSource.HTTP, True, 10.0))
        s.record(ScanMetric(ScanSource.OCR, True, 10.0))
        self.assertEqual(s.source_counts["ocr"], 2)
        self.assertEqual(s.source_counts["http"], 1)

    def test_proxy_counts(self):
        s = ScanStats()
        s.record(ScanMetric(ScanSource.HTTP, True, 10.0, proxy_used="p1"))
        s.record(ScanMetric(ScanSource.HTTP, True, 10.0, proxy_used="p1"))
        s.record(ScanMetric(ScanSource.HTTP, True, 10.0, proxy_used="p2"))
        self.assertEqual(s.proxy_counts["p1"], 2)
        self.assertEqual(s.proxy_counts["p2"], 1)


# ---------------------------------------------------------------------------
# Test: LobbyAntiLimit — single scans
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestAntiLimitSingle(unittest.TestCase):
    """Test single scan orchestration."""

    def test_ocr_scan_success(self):
        ocr = make_ok_scan(5)
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)
        tables, metric = anti.scan(apply_delay=False)
        self.assertEqual(len(tables), 5)
        self.assertTrue(metric.success)
        self.assertEqual(metric.source, ScanSource.OCR)

    def test_http_scan_success(self):
        http = make_ok_scan(3)
        anti = LobbyAntiLimit(
            http_fn=http, preferred_source=ScanSource.HTTP, base_delay=0
        )
        tables, metric = anti.scan(apply_delay=False)
        self.assertEqual(len(tables), 3)
        self.assertEqual(metric.source, ScanSource.HTTP)

    def test_failover_ocr_to_http(self):
        """OCR fails → should fall back to HTTP."""
        ocr = make_fail_scan()
        http = make_ok_scan(4)
        anti = LobbyAntiLimit(
            ocr_fn=ocr, http_fn=http, base_delay=0,
            circuit_failure_threshold=1,
        )
        # First scan — OCR fails
        _, m1 = anti.scan(apply_delay=False)
        self.assertFalse(m1.success)

        # Second scan — circuit tripped, should try HTTP
        tables, m2 = anti.scan(apply_delay=False)
        self.assertEqual(m2.source, ScanSource.HTTP)
        self.assertTrue(m2.success)
        self.assertEqual(len(tables), 4)

    def test_no_functions_configured(self):
        """No scan functions → graceful empty result."""
        anti = LobbyAntiLimit(base_delay=0)
        tables, metric = anti.scan(apply_delay=False)
        self.assertEqual(len(tables), 0)
        self.assertFalse(metric.success)
        self.assertIsNotNone(metric.error)

    def test_proxy_passed_to_http(self):
        """HTTP source should receive proxy from pool."""
        received_proxies = []

        def http_fn(proxy=None):
            received_proxies.append(proxy)
            return [{"id": "1"}], None

        anti = LobbyAntiLimit(
            http_fn=http_fn,
            proxies=["http://p1:8080"],
            preferred_source=ScanSource.HTTP,
            base_delay=0,
        )
        anti.scan(apply_delay=False)
        self.assertEqual(received_proxies, ["http://p1:8080"])

    def test_exception_in_scan_fn(self):
        """Exception in scan function → caught and recorded as error."""
        def bad_fn(proxy=None):
            raise RuntimeError("kaboom")

        anti = LobbyAntiLimit(ocr_fn=bad_fn, base_delay=0)
        tables, metric = anti.scan(apply_delay=False)
        self.assertEqual(len(tables), 0)
        self.assertFalse(metric.success)
        self.assertIn("kaboom", metric.error)


# ---------------------------------------------------------------------------
# Test: LobbyAntiLimit — batch
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestAntiLimitBatch(unittest.TestCase):
    """Test batch scan execution."""

    def test_batch_10(self):
        ocr = make_ok_scan(5)
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)
        stats = anti.run_batch(10)
        self.assertEqual(stats.total_scans, 10)
        self.assertEqual(stats.successful, 10)
        self.assertAlmostEqual(stats.success_rate, 1.0)

    def test_batch_callback(self):
        ocr = make_ok_scan(3)
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)
        collected = []

        def on_scan(idx, metric):
            collected.append((idx, metric.success))

        anti.run_batch(5, on_scan=on_scan)
        self.assertEqual(len(collected), 5)
        self.assertTrue(all(ok for _, ok in collected))

    def test_batch_with_flaky_source(self):
        """Flaky source — should handle errors gracefully."""
        flaky = make_flaky_scan(fail_every=4, tables=5)
        anti = LobbyAntiLimit(ocr_fn=flaky, base_delay=0)
        stats = anti.run_batch(20)
        self.assertEqual(stats.total_scans, 20)
        self.assertGreater(stats.successful, 0)
        self.assertGreater(stats.failed, 0)

    def test_reset_clears_stats(self):
        ocr = make_ok_scan()
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)
        anti.run_batch(5)
        self.assertEqual(anti.stats.total_scans, 5)
        anti.reset()
        self.assertEqual(anti.stats.total_scans, 0)


# ---------------------------------------------------------------------------
# Test: 100-scan stress test
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestStress100Scans(unittest.TestCase):
    """
    Core requirement from lobby_scanner.md Phase 3:
    Run 100 consecutive scans without errors.
    """

    def test_100_scans_no_errors(self):
        """100 scans with a reliable source → 0 errors."""
        ocr = make_ok_scan(8)
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)

        stats = anti.run_batch(100)

        self.assertEqual(stats.total_scans, 100)
        self.assertEqual(stats.successful, 100)
        self.assertEqual(stats.failed, 0)
        self.assertEqual(len(stats.errors), 0)
        self.assertAlmostEqual(stats.success_rate, 1.0)
        self.assertEqual(stats.total_tables, 800)  # 100 × 8

    def test_100_scans_with_failover(self):
        """100 scans: OCR is flaky, HTTP is reliable → near-100% success."""
        flaky_ocr = make_flaky_scan(fail_every=5, tables=5)
        reliable_http = make_ok_scan(5)

        anti = LobbyAntiLimit(
            ocr_fn=flaky_ocr,
            http_fn=reliable_http,
            base_delay=0,
            circuit_failure_threshold=2,
            circuit_recovery_timeout=0.01,
        )

        stats = anti.run_batch(100)

        self.assertEqual(stats.total_scans, 100)
        # With failover, most scans should succeed
        # (a few might fail when OCR fails and breaker hasn't yet switched)
        self.assertGreaterEqual(stats.success_rate, 0.80,
                                f"Success rate {stats.success_rate:.2%} < 80%")

    def test_100_scans_with_proxy_rotation(self):
        """100 scans with proxy rotation → all proxies used."""
        proxies = [f"http://p{i}:8080" for i in range(4)]
        http = make_ok_scan(3)

        anti = LobbyAntiLimit(
            http_fn=http,
            proxies=proxies,
            preferred_source=ScanSource.HTTP,
            base_delay=0,
        )

        stats = anti.run_batch(100)

        self.assertEqual(stats.total_scans, 100)
        self.assertEqual(stats.successful, 100)

        # All proxies should have been used at least once
        for p in proxies:
            self.assertIn(p, stats.proxy_counts,
                          f"Proxy {p} was never used")
            self.assertGreater(stats.proxy_counts[p], 0)

    def test_100_scans_with_delay(self):
        """100 scans with minimal delay — verify delay is applied."""
        ocr = make_ok_scan(2)
        anti = LobbyAntiLimit(
            ocr_fn=ocr,
            base_delay=0.001,  # 1ms — fast but non-zero
            jitter_frac=0.0,
        )

        t0 = time.monotonic()
        stats = anti.run_batch(100)
        elapsed = time.monotonic() - t0

        self.assertEqual(stats.total_scans, 100)
        self.assertEqual(stats.successful, 100)
        # With 99 delays of ≥1ms each, total should be > 50ms
        self.assertGreater(elapsed, 0.05)

    def test_100_scans_metrics_integrity(self):
        """Verify stats counters are consistent after 100 scans."""
        flaky = make_flaky_scan(fail_every=10, tables=5)
        anti = LobbyAntiLimit(ocr_fn=flaky, base_delay=0)

        stats = anti.run_batch(100)

        self.assertEqual(stats.total_scans, stats.successful + stats.failed)
        self.assertEqual(stats.total_scans, 100)
        self.assertGreater(stats.avg_latency_ms, 0)
        self.assertGreaterEqual(stats.max_latency_ms, stats.avg_latency_ms)


# ---------------------------------------------------------------------------
# Test: Thread safety
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires lobby_anti_limit")
class TestThreadSafety(unittest.TestCase):
    """Verify concurrent scan calls do not corrupt state."""

    def test_concurrent_scans(self):
        ocr = make_ok_scan(3)
        anti = LobbyAntiLimit(ocr_fn=ocr, base_delay=0)

        results = []

        def worker():
            for _ in range(10):
                tables, metric = anti.scan(apply_delay=False)
                results.append(metric.success)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 40)
        self.assertTrue(all(results))
        self.assertEqual(anti.stats.total_scans, 40)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
