#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for lobby_scanner.md — Phase 3: Anti-limit & proxy rotation.

Covers:
- DelayController (strategies: fixed, jitter, exponential, adaptive)
- ProxyRotator (round-robin, random, failover, disabling)
- ScanStats (metrics, summary)
- LiveTableScanner (scan_once, scan_loop, proxy integration)
- 100 scans without errors (key acceptance test)
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_table_scanner import (
    DelayStrategy,
    DelayConfig,
    DelayController,
    ProxyRotationMode,
    ProxyConfig,
    ProxyRotator,
    ScanStats,
    LiveTableScanner,
    HAS_FETCHER,
)


# ===========================================================================
# Test DelayController
# ===========================================================================

class TestDelayConfig(unittest.TestCase):
    """DelayConfig defaults."""

    def test_defaults(self):
        cfg = DelayConfig()
        self.assertEqual(cfg.strategy, DelayStrategy.JITTER)
        self.assertGreater(cfg.base_seconds, 0)
        self.assertGreater(cfg.max_seconds, cfg.base_seconds)


class TestDelayControllerFixed(unittest.TestCase):
    """Fixed delay strategy."""

    def test_fixed_delay(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.FIXED,
            base_seconds=1.0,
        ))
        delay = ctrl.compute_delay()
        self.assertAlmostEqual(delay, 1.0, places=1)

    def test_fixed_unchanged_after_success(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.FIXED,
            base_seconds=2.0,
        ))
        ctrl.report_success()
        self.assertAlmostEqual(ctrl.compute_delay(), 2.0, places=1)


class TestDelayControllerJitter(unittest.TestCase):
    """Jitter delay strategy."""

    def test_jitter_range(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.JITTER,
            base_seconds=2.0,
            jitter_seconds=0.5,
        ))
        delays = [ctrl.compute_delay() for _ in range(50)]
        self.assertTrue(all(1.5 <= d <= 2.5 for d in delays))
        # Should have some variation
        self.assertGreater(max(delays) - min(delays), 0.01)


class TestDelayControllerExponential(unittest.TestCase):
    """Exponential back-off on errors."""

    def test_increases_on_errors(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.EXPONENTIAL,
            base_seconds=1.0,
            backoff_factor=2.0,
            cooldown_after_errors=1,
            max_seconds=30.0,
        ))
        d0 = ctrl.compute_delay()
        ctrl.report_error()
        d1 = ctrl.compute_delay()
        self.assertGreater(d1, d0)

    def test_capped_at_max(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.EXPONENTIAL,
            base_seconds=1.0,
            backoff_factor=10.0,
            cooldown_after_errors=1,
            max_seconds=5.0,
        ))
        for _ in range(20):
            ctrl.report_error()
        self.assertLessEqual(ctrl.compute_delay(), 5.0)


class TestDelayControllerAdaptive(unittest.TestCase):
    """Adaptive strategy: increases on errors, decreases on success."""

    def test_adaptive_decrease_on_success(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.ADAPTIVE,
            base_seconds=1.0,
            jitter_seconds=0.0,
            cooldown_after_errors=2,
            max_seconds=30.0,
        ))
        # Push delay up
        ctrl.report_error()
        ctrl.report_error()
        ctrl.report_error()
        high = ctrl.compute_delay()

        # Success should reduce
        ctrl.report_success()
        ctrl.report_success()
        low = ctrl.compute_delay()
        self.assertLessEqual(low, high)

    def test_reset(self):
        ctrl = DelayController(DelayConfig(base_seconds=2.0))
        ctrl.report_error()
        ctrl.report_error()
        ctrl.reset()
        self.assertAlmostEqual(ctrl._current_delay, 2.0)


class TestDelayControllerWait(unittest.TestCase):
    """Test actual wait (with very short times)."""

    def test_wait_returns_positive(self):
        ctrl = DelayController(DelayConfig(
            strategy=DelayStrategy.FIXED,
            base_seconds=0.01,
            min_seconds=0.01,
        ))
        t0 = time.perf_counter()
        actual = ctrl.wait()
        elapsed = time.perf_counter() - t0
        self.assertGreater(actual, 0)
        self.assertGreater(elapsed, 0.005)


# ===========================================================================
# Test ProxyRotator
# ===========================================================================

class TestProxyRotatorRoundRobin(unittest.TestCase):
    """Round-robin rotation."""

    def test_cycles_through(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["A", "B", "C"],
            mode=ProxyRotationMode.ROUND_ROBIN,
        ))
        sequence = [pr.next_proxy() for _ in range(6)]
        self.assertEqual(sequence, ["A", "B", "C", "A", "B", "C"])

    def test_empty_proxies(self):
        pr = ProxyRotator(ProxyConfig(proxies=[]))
        self.assertIsNone(pr.next_proxy())

    def test_proxy_count(self):
        pr = ProxyRotator(ProxyConfig(proxies=["X", "Y"]))
        self.assertEqual(pr.proxy_count, 2)


class TestProxyRotatorRandom(unittest.TestCase):
    """Random selection."""

    def test_returns_from_list(self):
        proxies = ["A", "B", "C"]
        pr = ProxyRotator(ProxyConfig(
            proxies=proxies,
            mode=ProxyRotationMode.RANDOM,
        ))
        for _ in range(20):
            self.assertIn(pr.next_proxy(), proxies)


class TestProxyRotatorFailover(unittest.TestCase):
    """Failover: always first, rotate on failure."""

    def test_always_first(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["primary", "backup"],
            mode=ProxyRotationMode.FAILOVER,
        ))
        for _ in range(5):
            self.assertEqual(pr.next_proxy(), "primary")

    def test_failover_to_backup(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["primary", "backup"],
            mode=ProxyRotationMode.FAILOVER,
            max_failures_per_proxy=2,
        ))
        pr.report_failure("primary")
        pr.report_failure("primary")
        # primary now disabled
        self.assertEqual(pr.next_proxy(), "backup")


class TestProxyRotatorDisabling(unittest.TestCase):
    """Proxy disabling after max failures."""

    def test_disables_after_max_failures(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["A", "B"],
            mode=ProxyRotationMode.ROUND_ROBIN,
            max_failures_per_proxy=3,
        ))
        for _ in range(3):
            pr.report_failure("A")
        active = pr.active_proxies
        self.assertNotIn("A", active)
        self.assertIn("B", active)

    def test_success_resets_failure_count(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["A"],
            max_failures_per_proxy=3,
        ))
        pr.report_failure("A")
        pr.report_failure("A")
        pr.report_success("A")
        pr.report_failure("A")
        # Should NOT be disabled (count reset by success)
        self.assertIn("A", pr.active_proxies)

    def test_reset_clears_all(self):
        pr = ProxyRotator(ProxyConfig(
            proxies=["A", "B"],
            max_failures_per_proxy=1,
        ))
        pr.report_failure("A")
        pr.report_failure("B")
        pr.reset()
        self.assertEqual(len(pr.active_proxies), 2)


# ===========================================================================
# Test ScanStats
# ===========================================================================

class TestScanStats(unittest.TestCase):

    def test_defaults(self):
        s = ScanStats()
        self.assertEqual(s.success_rate, 0.0)
        self.assertEqual(s.avg_latency_ms, 0.0)
        self.assertEqual(s.error_count, 0)

    def test_success_rate(self):
        s = ScanStats(total_scans=10, successful_scans=8)
        self.assertAlmostEqual(s.success_rate, 0.8)

    def test_avg_latency(self):
        s = ScanStats(total_scans=4, total_elapsed_ms=400.0)
        self.assertAlmostEqual(s.avg_latency_ms, 100.0)

    def test_summary_includes_key_info(self):
        s = ScanStats(
            total_scans=5,
            successful_scans=4,
            failed_scans=1,
            total_tables_found=20,
        )
        summary = s.summary()
        self.assertIn("5 scans", summary)
        self.assertIn("4", summary)
        self.assertIn("20", summary)


# ===========================================================================
# Test LiveTableScanner
# ===========================================================================

class TestLiveTableScannerInit(unittest.TestCase):
    """LiveTableScanner initialization."""

    def test_default_init(self):
        scanner = LiveTableScanner()
        self.assertEqual(scanner.stats.total_scans, 0)
        self.assertEqual(scanner.proxy_rotator.proxy_count, 0)

    def test_init_with_proxies(self):
        scanner = LiveTableScanner(proxies=["http://p1:8080", "http://p2:8080"])
        self.assertEqual(scanner.proxy_rotator.proxy_count, 2)

    def test_init_with_custom_delay(self):
        scanner = LiveTableScanner(delay_base=5.0, delay_jitter=1.0)
        self.assertAlmostEqual(scanner.delay.config.base_seconds, 5.0)


class TestLiveTableScannerScanOnce(unittest.TestCase):
    """scan_once with mocked fetcher."""

    def _make_scanner(self, proxies=None) -> LiveTableScanner:
        return LiveTableScanner(
            proxies=proxies or [],
            delay_strategy="fixed",
            delay_base=0.01,
        )

    def test_scan_once_success_mocked(self):
        """Mocked fetcher returns tables → success."""
        scanner = self._make_scanner()

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 3
        mock_result.tables = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            result = scanner.scan_once()

        self.assertEqual(scanner.stats.total_scans, 1)
        self.assertEqual(scanner.stats.successful_scans, 1)
        self.assertEqual(scanner.stats.total_tables_found, 3)

    def test_scan_once_failure_mocked(self):
        """Mocked fetcher returns empty → failure."""
        scanner = self._make_scanner()

        mock_result = MagicMock()
        mock_result.ok = False
        mock_result.table_count = 0
        mock_result.tables = []
        mock_result.errors = ["connection refused"]
        mock_result.strategy_used = ""

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            result = scanner.scan_once()

        self.assertEqual(scanner.stats.failed_scans, 1)

    def test_scan_once_with_proxy(self):
        """Proxy is passed to fetcher."""
        scanner = self._make_scanner(proxies=["http://proxy1:8080"])

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 1
        mock_result.tables = [MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher) as mk:
            scanner.scan_once()
            mk.assert_called_once_with(proxy="http://proxy1:8080")


class TestLiveTableScannerScanLoop(unittest.TestCase):
    """scan_loop tests."""

    def _make_scanner(self) -> LiveTableScanner:
        return LiveTableScanner(
            delay_strategy="fixed",
            delay_base=0.001,
        )

    def test_scan_loop_count(self):
        """scan_loop executes exactly N scans."""
        scanner = self._make_scanner()

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 2
        mock_result.tables = [MagicMock(), MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            results = scanner.scan_loop(count=10, skip_delay=True)

        self.assertEqual(len(results), 10)
        self.assertEqual(scanner.stats.total_scans, 10)

    def test_scan_loop_callback(self):
        """on_result callback is called for each scan."""
        scanner = self._make_scanner()
        callback_calls = []

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 1
        mock_result.tables = [MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "ocr"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            scanner.scan_loop(
                count=5,
                skip_delay=True,
                on_result=lambda i, r: callback_calls.append(i),
            )

        self.assertEqual(callback_calls, [0, 1, 2, 3, 4])

    def test_scan_loop_stop(self):
        """stop() interrupts scan_loop."""
        scanner = self._make_scanner()

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 1
        mock_result.tables = [MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        def stop_after_3(i, r):
            if i >= 2:
                scanner.stop()

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            results = scanner.scan_loop(
                count=100,
                skip_delay=True,
                on_result=stop_after_3,
            )

        self.assertLessEqual(len(results), 4)  # stops shortly after index 2

    def test_reset_stats(self):
        scanner = self._make_scanner()
        scanner.stats.total_scans = 50
        scanner.stats.successful_scans = 40
        scanner.reset_stats()
        self.assertEqual(scanner.stats.total_scans, 0)


# ===========================================================================
# KEY ACCEPTANCE TEST: 100 scans without errors
# ===========================================================================

class TestHundredScansWithoutErrors(unittest.TestCase):
    """
    Acceptance test from lobby_scanner.md Phase 3:
    100 scans without errors.

    Uses mocked backends to simulate consistent operation.
    """

    def test_100_scans_all_success(self):
        """100 consecutive scans — all must succeed, 0 errors."""
        scanner = LiveTableScanner(
            proxies=["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"],
            proxy_mode="round_robin",
            delay_strategy="jitter",
            delay_base=0.001,
            delay_jitter=0.0005,
        )

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 5
        mock_result.tables = [MagicMock() for _ in range(5)]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            results = scanner.scan_loop(count=100, skip_delay=True)

        # Assertions
        self.assertEqual(len(results), 100)
        self.assertEqual(scanner.stats.total_scans, 100)
        self.assertEqual(scanner.stats.successful_scans, 100)
        self.assertEqual(scanner.stats.failed_scans, 0)
        self.assertEqual(scanner.stats.error_count, 0)
        self.assertAlmostEqual(scanner.stats.success_rate, 1.0)
        self.assertEqual(scanner.stats.total_tables_found, 500)  # 100 × 5

    def test_100_scans_with_proxy_rotation(self):
        """100 scans rotate through 3 proxies evenly."""
        scanner = LiveTableScanner(
            proxies=["http://A:80", "http://B:80", "http://C:80"],
            proxy_mode="round_robin",
            delay_base=0.001,
        )

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 2
        mock_result.tables = [MagicMock(), MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "http"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            scanner.scan_loop(count=100, skip_delay=True)

        # Each proxy should have been used ~33 times
        for proxy_key in ["http://A:80", "http://B:80", "http://C:80"]:
            count = scanner.stats.per_proxy_success.get(proxy_key, 0)
            self.assertGreaterEqual(count, 30)
            self.assertLessEqual(count, 40)

    def test_100_scans_no_proxy_direct(self):
        """100 scans without proxies (direct) — all succeed."""
        scanner = LiveTableScanner(
            proxies=[],
            delay_base=0.001,
        )

        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.table_count = 3
        mock_result.tables = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.errors = []
        mock_result.strategy_used = "ocr"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            results = scanner.scan_loop(count=100, skip_delay=True)

        self.assertEqual(len(results), 100)
        self.assertEqual(scanner.stats.successful_scans, 100)
        self.assertEqual(scanner.stats.failed_scans, 0)
        self.assertEqual(scanner.stats.per_proxy_success.get("direct", 0), 100)

    def test_100_scans_mixed_with_recovery(self):
        """100 scans where some fail but scanner recovers."""
        scanner = LiveTableScanner(
            proxies=["http://flaky:80"],
            delay_strategy="adaptive",
            delay_base=0.001,
            delay_jitter=0.0,
        )

        call_count = [0]

        def make_result(*args, **kwargs):
            call_count[0] += 1
            mock_r = MagicMock()
            # Fail every 10th scan
            if call_count[0] % 10 == 0:
                mock_r.ok = False
                mock_r.table_count = 0
                mock_r.tables = []
                mock_r.errors = ["timeout"]
                mock_r.strategy_used = ""
            else:
                mock_r.ok = True
                mock_r.table_count = 2
                mock_r.tables = [MagicMock(), MagicMock()]
                mock_r.errors = []
                mock_r.strategy_used = "http"
            return mock_r

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.side_effect = make_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            results = scanner.scan_loop(count=100, skip_delay=True)

        self.assertEqual(len(results), 100)
        self.assertEqual(scanner.stats.total_scans, 100)
        # 10 failures out of 100
        self.assertEqual(scanner.stats.failed_scans, 10)
        self.assertEqual(scanner.stats.successful_scans, 90)
        # Success rate should be 90%
        self.assertAlmostEqual(scanner.stats.success_rate, 0.9)


# ===========================================================================
# Test proxy + delay integration
# ===========================================================================

class TestProxyDelayIntegration(unittest.TestCase):
    """Test that delay increases when proxy fails."""

    def test_delay_increases_on_proxy_failure(self):
        scanner = LiveTableScanner(
            proxies=["http://bad:80"],
            delay_strategy="adaptive",
            delay_base=1.0,
            delay_jitter=0.0,
        )

        initial_delay = scanner.delay.compute_delay()

        mock_result = MagicMock()
        mock_result.ok = False
        mock_result.table_count = 0
        mock_result.tables = []
        mock_result.errors = ["fail"]
        mock_result.strategy_used = ""

        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = mock_result

        with patch.object(scanner, '_make_fetcher', return_value=mock_fetcher):
            for _ in range(5):
                scanner.scan_once()

        final_delay = scanner.delay.compute_delay()
        self.assertGreater(final_delay, initial_delay)


if __name__ == "__main__":
    unittest.main()
