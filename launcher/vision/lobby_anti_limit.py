"""
Lobby Anti-Limit Module — Phase 3 of lobby_scanner.md.

Orchestrates lobby scanning with rate-limit protection:
  - Adaptive delay between scans (jitter + back-off on errors)
  - Proxy rotation pool
  - Dual-source fallback: OCR → HTTP → OCR (round-robin on failure)
  - Per-source rate counters & circuit breaker
  - 100-scan stress-test harness

Pipeline:
  1. Pick source (OCR or HTTP) based on health / round-robin
  2. Apply delay (base + jitter + back-off)
  3. Rotate proxy (if HTTP)
  4. Execute scan
  5. Record metrics (success/fail, latency)
  6. If fail → trip circuit breaker → switch source

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ScanSource(str, Enum):
    """Available lobby data sources."""
    OCR = "ocr"
    HTTP = "http"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # normal — requests flow through
    OPEN = "open"            # tripped — all requests rejected
    HALF_OPEN = "half_open"  # testing — one request allowed


@dataclass
class ScanMetric:
    """Single scan measurement."""
    source: ScanSource
    success: bool
    latency_ms: float
    tables_found: int = 0
    error: Optional[str] = None
    proxy_used: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ScanStats:
    """Aggregate stats across a scanning session."""
    total_scans: int = 0
    successful: int = 0
    failed: int = 0
    total_tables: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    source_counts: Dict[str, int] = field(default_factory=dict)
    proxy_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successful / max(self.total_scans, 1)

    def record(self, metric: ScanMetric):
        self.total_scans += 1
        if metric.success:
            self.successful += 1
            self.total_tables += metric.tables_found
        else:
            self.failed += 1
            if metric.error:
                self.errors.append(metric.error)

        # Latency
        self.avg_latency_ms = (
            (self.avg_latency_ms * (self.total_scans - 1) + metric.latency_ms)
            / self.total_scans
        )
        self.max_latency_ms = max(self.max_latency_ms, metric.latency_ms)

        # Source
        src = metric.source.value
        self.source_counts[src] = self.source_counts.get(src, 0) + 1

        # Proxy
        if metric.proxy_used:
            self.proxy_counts[metric.proxy_used] = (
                self.proxy_counts.get(metric.proxy_used, 0) + 1
            )


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Per-source circuit breaker.

    After *failure_threshold* consecutive failures the circuit opens.
    After *recovery_timeout* seconds it transitions to half-open and
    allows a single probe request.  If that succeeds → closed; else → open.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def allow_request(self) -> bool:
        s = self.state
        return s in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self):
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED

    def record_failure(self):
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()
            if self._consecutive_failures >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self):
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED
            self._last_failure_time = 0.0


# ---------------------------------------------------------------------------
# Proxy pool
# ---------------------------------------------------------------------------


class ProxyPool:
    """Rotating proxy pool with health tracking.

    Proxies that fail consecutively are temporarily excluded.
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        max_failures: int = 3,
        cooldown: float = 60.0,
    ):
        self._proxies = list(proxies) if proxies else []
        self._max_failures = max_failures
        self._cooldown = cooldown

        # Track failures: proxy → (consecutive_failures, last_failure_time)
        self._health: Dict[str, Tuple[int, float]] = {}
        self._index = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return len(self._proxies)

    @property
    def available(self) -> List[str]:
        """Proxies not currently in cooldown."""
        now = time.monotonic()
        with self._lock:
            return [
                p for p in self._proxies
                if self._is_healthy(p, now)
            ]

    def next(self) -> Optional[str]:
        """Get next healthy proxy (round-robin). Returns None if pool empty."""
        if not self._proxies:
            return None

        now = time.monotonic()
        with self._lock:
            for _ in range(len(self._proxies)):
                proxy = self._proxies[self._index % len(self._proxies)]
                self._index += 1
                if self._is_healthy(proxy, now):
                    return proxy

        return None  # All proxies in cooldown

    def report_success(self, proxy: str):
        with self._lock:
            self._health.pop(proxy, None)

    def report_failure(self, proxy: str):
        with self._lock:
            fails, _ = self._health.get(proxy, (0, 0.0))
            self._health[proxy] = (fails + 1, time.monotonic())

    def add(self, proxy: str):
        with self._lock:
            if proxy not in self._proxies:
                self._proxies.append(proxy)

    def remove(self, proxy: str):
        with self._lock:
            if proxy in self._proxies:
                self._proxies.remove(proxy)
                self._health.pop(proxy, None)

    def reset(self):
        with self._lock:
            self._health.clear()
            self._index = 0

    def _is_healthy(self, proxy: str, now: float) -> bool:
        if proxy not in self._health:
            return True
        fails, last_t = self._health[proxy]
        if fails >= self._max_failures:
            if now - last_t < self._cooldown:
                return False
            # Cooldown expired → allow retry
        return True


# ---------------------------------------------------------------------------
# Delay strategy
# ---------------------------------------------------------------------------


class AdaptiveDelay:
    """Adaptive delay with jitter and error back-off.

    Parameters:
        base_delay:   minimum delay between requests (seconds)
        max_delay:    ceiling after back-off (seconds)
        jitter_frac:  random jitter as fraction of base (0.0–1.0)
        backoff_mult: multiplier applied per consecutive error
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        jitter_frac: float = 0.3,
        backoff_mult: float = 1.5,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_frac = jitter_frac
        self.backoff_mult = backoff_mult

        self._consecutive_errors = 0
        self._lock = threading.Lock()

    def wait(self):
        """Sleep for the computed delay."""
        delay = self.current_delay()
        if delay > 0:
            time.sleep(delay)

    def current_delay(self) -> float:
        """Compute current delay without sleeping."""
        with self._lock:
            delay = self.base_delay * (self.backoff_mult ** self._consecutive_errors)
            delay = min(delay, self.max_delay)
            jitter = random.uniform(-self.jitter_frac, self.jitter_frac) * delay
            return max(0, delay + jitter)

    def record_success(self):
        with self._lock:
            self._consecutive_errors = max(0, self._consecutive_errors - 1)

    def record_error(self):
        with self._lock:
            self._consecutive_errors += 1

    def reset(self):
        with self._lock:
            self._consecutive_errors = 0

    @property
    def consecutive_errors(self) -> int:
        with self._lock:
            return self._consecutive_errors


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


# Type alias for scan functions.  A scan function takes optional proxy
# and returns (tables: List[dict], error: Optional[str]).
ScanFn = Callable[[Optional[str]], Tuple[List[Dict[str, Any]], Optional[str]]]


class LobbyAntiLimit:
    """Anti-rate-limit orchestrator for lobby scanning.

    Combines:
      - Dual source (OCR / HTTP) with automatic failover
      - Per-source circuit breakers
      - Proxy rotation (HTTP only)
      - Adaptive delay with jitter + back-off
      - Session-wide stats tracking

    Usage::

        anti = LobbyAntiLimit(
            ocr_fn=my_ocr_scan,
            http_fn=my_http_scan,
            proxies=["http://p1:8080", "http://p2:8080"],
        )
        tables, metric = anti.scan()         # single scan
        stats = anti.run_batch(100)          # 100 consecutive scans
        print(stats.success_rate)

    The ``ocr_fn`` / ``http_fn`` callables must accept an optional proxy
    string and return ``(tables_list, error_or_None)``.
    """

    def __init__(
        self,
        ocr_fn: Optional[ScanFn] = None,
        http_fn: Optional[ScanFn] = None,
        proxies: Optional[List[str]] = None,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        jitter_frac: float = 0.3,
        backoff_mult: float = 1.5,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0,
        preferred_source: ScanSource = ScanSource.OCR,
    ):
        self._sources: Dict[ScanSource, Optional[ScanFn]] = {
            ScanSource.OCR: ocr_fn,
            ScanSource.HTTP: http_fn,
        }
        self._preferred = preferred_source

        # Per-source circuit breakers
        self._breakers: Dict[ScanSource, CircuitBreaker] = {
            src: CircuitBreaker(circuit_failure_threshold, circuit_recovery_timeout)
            for src in ScanSource
        }

        self._proxy_pool = ProxyPool(proxies)
        self._delay = AdaptiveDelay(base_delay, max_delay, jitter_frac, backoff_mult)
        self._stats = ScanStats()
        self._lock = threading.Lock()

        logger.info(
            "LobbyAntiLimit initialised — sources=%s, proxies=%d, base_delay=%.1fs",
            [s.value for s, fn in self._sources.items() if fn],
            self._proxy_pool.size,
            base_delay,
        )

    # -- public API ----------------------------------------------------------

    def scan(self, apply_delay: bool = True) -> Tuple[List[Dict], ScanMetric]:
        """Execute a single lobby scan with anti-limit protections.

        Returns (tables, metric).
        """
        if apply_delay:
            self._delay.wait()

        # Pick source
        source = self._pick_source()
        fn = self._sources.get(source)
        if fn is None:
            # Fallback to alternate source
            source = self._alternate(source)
            fn = self._sources.get(source)

        if fn is None:
            metric = ScanMetric(
                source=source,
                success=False,
                latency_ms=0,
                error="No scan function configured",
            )
            self._stats.record(metric)
            return [], metric

        # Pick proxy (HTTP only)
        proxy = self._proxy_pool.next() if source == ScanSource.HTTP else None

        # Execute
        t0 = time.perf_counter()
        try:
            tables, error = fn(proxy)
            latency = (time.perf_counter() - t0) * 1000
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            tables, error = [], str(exc)

        success = error is None and tables is not None

        metric = ScanMetric(
            source=source,
            success=success,
            latency_ms=latency,
            tables_found=len(tables) if tables else 0,
            error=error,
            proxy_used=proxy,
        )

        # Update health trackers
        if success:
            self._breakers[source].record_success()
            self._delay.record_success()
            if proxy:
                self._proxy_pool.report_success(proxy)
        else:
            self._breakers[source].record_failure()
            self._delay.record_error()
            if proxy:
                self._proxy_pool.report_failure(proxy)

        self._stats.record(metric)
        return tables or [], metric

    def run_batch(
        self,
        count: int = 100,
        on_scan: Optional[Callable[[int, ScanMetric], None]] = None,
    ) -> ScanStats:
        """Run *count* consecutive scans and collect stats.

        Args:
            count:   number of scans
            on_scan: optional callback ``(scan_index, metric)`` after each scan
        """
        self._stats = ScanStats()

        for i in range(count):
            tables, metric = self.scan(apply_delay=(i > 0))
            if on_scan:
                on_scan(i, metric)

        return self._stats

    @property
    def stats(self) -> ScanStats:
        return self._stats

    @property
    def proxy_pool(self) -> ProxyPool:
        return self._proxy_pool

    @property
    def delay(self) -> AdaptiveDelay:
        return self._delay

    def reset(self):
        """Reset all counters, breakers, proxy health."""
        self._stats = ScanStats()
        self._delay.reset()
        self._proxy_pool.reset()
        for b in self._breakers.values():
            b.reset()

    # -- internal ------------------------------------------------------------

    def _pick_source(self) -> ScanSource:
        """Pick the best available source."""
        # Preferred source if healthy
        if (
            self._sources.get(self._preferred)
            and self._breakers[self._preferred].allow_request()
        ):
            return self._preferred

        # Try alternate
        alt = self._alternate(self._preferred)
        if self._sources.get(alt) and self._breakers[alt].allow_request():
            return alt

        # Both tripped — force preferred (it might be half-open soon)
        return self._preferred

    def _alternate(self, source: ScanSource) -> ScanSource:
        return ScanSource.HTTP if source == ScanSource.OCR else ScanSource.OCR
