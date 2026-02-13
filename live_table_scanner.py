#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
live_table_scanner.py — Lobby scanner с anti-rate-limit и proxy rotation.

Phase 3 of lobby_scanner.md + full_hive_month.md Этап 1.

Features:
- Configurable delay between scans (fixed, jitter, exponential back-off)
- Proxy rotation (round-robin, random, weighted)
- Scan loop with automatic retry & error tracking
- Integration with LobbyFetcher (HTTP + OCR fallback)
- Graceful degradation: if proxy fails → direct, if HTTP fails → OCR
- Stats: success rate, avg latency, errors per proxy
- **Этап 1**: Full scan with player/seat OCR extraction per table
- **Этап 1**: Table filtering by player count for auto-fill targeting

Usage::

    scanner = LiveTableScanner(
        proxies=["http://p1:8080", "http://p2:8080"],
        delay_base=2.0,
        delay_jitter=0.5,
    )
    results = scanner.scan_loop(count=100)
    print(scanner.stats.summary())

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Imports (graceful)
# ---------------------------------------------------------------------------

try:
    from lobby_http_parser import (
        LobbyFetcher,
        FetchStrategy,
        UnifiedFetchResult,
        UnifiedTable,
    )
    HAS_FETCHER = True
except (ImportError, SyntaxError, Exception):
    HAS_FETCHER = False


# ---------------------------------------------------------------------------
# Delay strategies
# ---------------------------------------------------------------------------

class DelayStrategy(str, Enum):
    """Delay strategy between consecutive scans."""
    FIXED = "fixed"              # constant delay
    JITTER = "jitter"            # base ± random jitter
    EXPONENTIAL = "exponential"  # exponential back-off on errors
    ADAPTIVE = "adaptive"        # increase delay if errors detected


@dataclass
class DelayConfig:
    """Configuration for scan delays."""
    strategy: DelayStrategy = DelayStrategy.JITTER
    base_seconds: float = 2.0       # base delay
    jitter_seconds: float = 0.5     # random ±jitter range
    max_seconds: float = 30.0       # max delay (for exponential/adaptive)
    min_seconds: float = 0.5        # minimum delay
    backoff_factor: float = 1.5     # multiplier for exponential
    cooldown_after_errors: int = 3  # switch to exponential after N consecutive errors


class DelayController:
    """Manages inter-scan delays with adaptive strategies."""

    def __init__(self, config: DelayConfig | None = None):
        self.config = config or DelayConfig()
        self._consecutive_errors = 0
        self._current_delay = self.config.base_seconds

    def wait(self) -> float:
        """Wait according to current strategy. Returns actual wait time."""
        delay = self._compute_delay()
        delay = max(self.config.min_seconds, min(delay, self.config.max_seconds))
        if delay > 0:
            time.sleep(delay)
        return delay

    def compute_delay(self) -> float:
        """Compute delay without waiting (for testing/preview)."""
        delay = self._compute_delay()
        return max(self.config.min_seconds, min(delay, self.config.max_seconds))

    def report_success(self):
        """Report a successful scan — may reduce delay."""
        self._consecutive_errors = 0
        if self.config.strategy == DelayStrategy.ADAPTIVE:
            # Slowly reduce back to base
            self._current_delay = max(
                self.config.base_seconds,
                self._current_delay * 0.8,
            )

    def report_error(self):
        """Report a failed scan — may increase delay."""
        self._consecutive_errors += 1
        if (self.config.strategy == DelayStrategy.ADAPTIVE or
                self._consecutive_errors >= self.config.cooldown_after_errors):
            self._current_delay = min(
                self._current_delay * self.config.backoff_factor,
                self.config.max_seconds,
            )

    def reset(self):
        """Reset to initial state."""
        self._consecutive_errors = 0
        self._current_delay = self.config.base_seconds

    def _compute_delay(self) -> float:
        cfg = self.config
        strategy = cfg.strategy

        # If too many consecutive errors, force exponential regardless
        if self._consecutive_errors >= cfg.cooldown_after_errors:
            return self._current_delay

        if strategy == DelayStrategy.FIXED:
            return cfg.base_seconds

        elif strategy == DelayStrategy.JITTER:
            jitter = random.uniform(-cfg.jitter_seconds, cfg.jitter_seconds)
            return cfg.base_seconds + jitter

        elif strategy == DelayStrategy.EXPONENTIAL:
            return self._current_delay

        elif strategy == DelayStrategy.ADAPTIVE:
            jitter = random.uniform(-cfg.jitter_seconds, cfg.jitter_seconds)
            return self._current_delay + jitter

        return cfg.base_seconds


# ---------------------------------------------------------------------------
# Proxy rotation
# ---------------------------------------------------------------------------

class ProxyRotationMode(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    FAILOVER = "failover"    # use first, rotate only on failure


@dataclass
class ProxyConfig:
    """Proxy rotation configuration."""
    proxies: List[str] = field(default_factory=list)
    mode: ProxyRotationMode = ProxyRotationMode.ROUND_ROBIN
    max_failures_per_proxy: int = 5   # disable proxy after N failures
    retry_disabled_after: float = 300.0  # re-enable disabled proxies after N seconds


class ProxyRotator:
    """Manages proxy rotation with failure tracking."""

    def __init__(self, config: ProxyConfig | None = None):
        self.config = config or ProxyConfig()
        self._index = 0
        self._failures: Dict[str, int] = {}
        self._disabled: Dict[str, float] = {}  # proxy → time disabled

    @property
    def proxy_count(self) -> int:
        return len(self.config.proxies)

    @property
    def active_proxies(self) -> List[str]:
        """Proxies that are not disabled."""
        now = time.monotonic()
        result = []
        for p in self.config.proxies:
            if p in self._disabled:
                if now - self._disabled[p] > self.config.retry_disabled_after:
                    del self._disabled[p]
                    self._failures[p] = 0
                else:
                    continue
            result.append(p)
        return result

    def next_proxy(self) -> Optional[str]:
        """Get the next proxy according to rotation mode.

        Returns None if no proxies configured or all disabled.
        """
        active = self.active_proxies
        if not active:
            return None

        mode = self.config.mode

        if mode == ProxyRotationMode.ROUND_ROBIN:
            self._index = self._index % len(active)
            proxy = active[self._index]
            self._index += 1
            return proxy

        elif mode == ProxyRotationMode.RANDOM:
            return random.choice(active)

        elif mode == ProxyRotationMode.FAILOVER:
            return active[0]

        return active[0] if active else None

    def report_success(self, proxy: str):
        """Report successful use of proxy."""
        self._failures[proxy] = 0

    def report_failure(self, proxy: str):
        """Report failed use of proxy — may disable it."""
        self._failures[proxy] = self._failures.get(proxy, 0) + 1
        if self._failures[proxy] >= self.config.max_failures_per_proxy:
            self._disabled[proxy] = time.monotonic()
            logger.warning("Proxy disabled: %s (too many failures)", proxy)

    def reset(self):
        """Reset all failure counts and re-enable all proxies."""
        self._index = 0
        self._failures.clear()
        self._disabled.clear()


# ---------------------------------------------------------------------------
# Scan statistics
# ---------------------------------------------------------------------------

@dataclass
class ScanStats:
    """Accumulated statistics across scan loop iterations."""
    total_scans: int = 0
    successful_scans: int = 0
    failed_scans: int = 0
    total_tables_found: int = 0
    total_elapsed_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    per_proxy_success: Dict[str, int] = field(default_factory=dict)
    per_proxy_fail: Dict[str, int] = field(default_factory=dict)
    strategy_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        return self.successful_scans / self.total_scans if self.total_scans > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_elapsed_ms / self.total_scans if self.total_scans > 0 else 0.0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def summary(self) -> str:
        lines = [
            f"Scan Stats: {self.total_scans} scans",
            f"  Success: {self.successful_scans} ({self.success_rate:.0%})",
            f"  Failed: {self.failed_scans}",
            f"  Tables found: {self.total_tables_found}",
            f"  Avg latency: {self.avg_latency_ms:.0f}ms",
        ]
        if self.strategy_counts:
            lines.append(f"  Strategies: {self.strategy_counts}")
        if self.per_proxy_success or self.per_proxy_fail:
            lines.append("  Per-proxy:")
            all_proxies = set(self.per_proxy_success) | set(self.per_proxy_fail)
            for p in sorted(all_proxies):
                s = self.per_proxy_success.get(p, 0)
                f = self.per_proxy_fail.get(p, 0)
                lines.append(f"    {p}: ok={s} fail={f}")
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for e in self.errors[:10]:
                lines.append(f"    - {e}")
            if len(self.errors) > 10:
                lines.append(f"    ... and {len(self.errors) - 10} more")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Seat / player info (full_hive_month.md Этап 1)
# ---------------------------------------------------------------------------

@dataclass
class SeatInfo:
    """Player/seat information for a table.

    Attributes:
        table_name:   Name/ID of the table.
        stakes:       Stakes string.
        total_seats:  Maximum seats at the table.
        occupied:     Number of currently occupied seats.
        human_count:  Estimated human players (occupied minus known bots).
        bot_count:    Number of our bots already at this table.
        is_target:    Whether this table is eligible for auto-fill.
        raw_text:     Raw OCR line for debugging.
    """
    table_name: str = ""
    stakes: str = ""
    total_seats: int = 0
    occupied: int = 0
    human_count: int = 0
    bot_count: int = 0
    is_target: bool = False
    raw_text: str = ""

    @property
    def free_seats(self) -> int:
        return max(0, self.total_seats - self.occupied)

    @property
    def fill_slots(self) -> int:
        """How many bots can still be placed here."""
        return max(0, self.total_seats - self.occupied - self.bot_count)


# ---------------------------------------------------------------------------
# LiveTableScanner — main orchestrator
# ---------------------------------------------------------------------------

class LiveTableScanner:
    """
    Orchestrates lobby scanning with delay, proxy rotation, and retries.

    Integrates:
    - LobbyFetcher (Phase 2) for HTTP + OCR data retrieval
    - DelayController for anti-rate-limit pauses
    - ProxyRotator for proxy management
    - ScanStats for metrics

    The scanner can run a fixed number of scans (scan_loop) or run
    continuously (scan_continuous) until stopped.
    """

    def __init__(
        self,
        proxies: List[str] | None = None,
        proxy_mode: str = "round_robin",
        delay_base: float = 2.0,
        delay_jitter: float = 0.5,
        delay_strategy: str = "jitter",
        delay_max: float = 30.0,
        fetch_strategy: str = "auto",
        http_backend: str = "generic",
        ocr_lang: str = "eng",
        max_failures_per_proxy: int = 5,
    ):
        # Delay
        self.delay = DelayController(DelayConfig(
            strategy=DelayStrategy(delay_strategy),
            base_seconds=delay_base,
            jitter_seconds=delay_jitter,
            max_seconds=delay_max,
        ))

        # Proxy
        proxy_list = proxies or []
        self.proxy_rotator = ProxyRotator(ProxyConfig(
            proxies=proxy_list,
            mode=ProxyRotationMode(proxy_mode),
            max_failures_per_proxy=max_failures_per_proxy,
        ))

        # Fetch strategy
        self._fetch_strategy = FetchStrategy(fetch_strategy) if HAS_FETCHER else None
        self._http_backend = http_backend
        self._ocr_lang = ocr_lang

        # Stats
        self.stats = ScanStats()

        # State
        self._stop_requested = False

    def _make_fetcher(self, proxy: Optional[str] = None) -> Optional[Any]:
        """Create a LobbyFetcher with the current proxy."""
        if not HAS_FETCHER:
            return None
        return LobbyFetcher(
            strategy=self._fetch_strategy,
            http_backend=self._http_backend,
            http_proxy=proxy,
            ocr_lang=self._ocr_lang,
        )

    def scan_once(
        self,
        image=None,
        extra_query: Optional[Dict[str, str]] = None,
    ) -> UnifiedFetchResult | Dict:
        """Perform a single scan with proxy rotation.

        Returns UnifiedFetchResult (or dict stub if fetcher unavailable).
        """
        proxy = self.proxy_rotator.next_proxy()
        fetcher = self._make_fetcher(proxy=proxy)

        if fetcher is None:
            # Stub result when fetcher not available
            self.stats.total_scans += 1
            self.stats.failed_scans += 1
            self.stats.errors.append("LobbyFetcher not available")
            return {"tables": [], "error": "LobbyFetcher not available"}

        t0 = time.perf_counter()
        try:
            result = fetcher.fetch(image=image, extra_query=extra_query)
        except Exception as exc:
            result = UnifiedFetchResult(errors=[str(exc)])

        elapsed = (time.perf_counter() - t0) * 1000
        self.stats.total_scans += 1
        self.stats.total_elapsed_ms += elapsed

        proxy_key = proxy or "direct"

        if result.ok:
            self.stats.successful_scans += 1
            self.stats.total_tables_found += result.table_count
            self.delay.report_success()
            if proxy:
                self.proxy_rotator.report_success(proxy)
            self.stats.per_proxy_success[proxy_key] = (
                self.stats.per_proxy_success.get(proxy_key, 0) + 1
            )
            if hasattr(result, 'strategy_used'):
                s = result.strategy_used or "unknown"
                self.stats.strategy_counts[s] = self.stats.strategy_counts.get(s, 0) + 1
        else:
            self.stats.failed_scans += 1
            errs = result.errors if hasattr(result, 'errors') else []
            for e in errs:
                self.stats.errors.append(e)
            self.delay.report_error()
            if proxy:
                self.proxy_rotator.report_failure(proxy)
            self.stats.per_proxy_fail[proxy_key] = (
                self.stats.per_proxy_fail.get(proxy_key, 0) + 1
            )

        return result

    def scan_loop(
        self,
        count: int = 100,
        image=None,
        extra_query: Optional[Dict[str, str]] = None,
        skip_delay: bool = False,
        on_result: Optional[Callable] = None,
    ) -> List:
        """Run *count* scans with delays between them.

        Args:
            count: number of scans
            image: for OCR backend
            extra_query: extra HTTP query params
            skip_delay: if True, skip inter-scan delays (for testing)
            on_result: optional callback(index, result)

        Returns:
            List of results.
        """
        self._stop_requested = False
        results = []

        for i in range(count):
            if self._stop_requested:
                logger.info("Scan loop stopped at iteration %d", i)
                break

            result = self.scan_once(image=image, extra_query=extra_query)
            results.append(result)

            if on_result:
                try:
                    on_result(i, result)
                except Exception:
                    pass

            # Inter-scan delay (skip between last and first)
            if not skip_delay and i < count - 1:
                self.delay.wait()

        return results

    def stop(self):
        """Request stop of the current scan loop."""
        self._stop_requested = True

    def reset_stats(self):
        """Reset statistics."""
        self.stats = ScanStats()
        self.delay.reset()
        self.proxy_rotator.reset()

    # ------------------------------------------------------------------
    # Этап 1: full scan with player/seat extraction
    # ------------------------------------------------------------------

    def scan_with_seats(
        self,
        image=None,
        extra_query: Optional[Dict[str, str]] = None,
        known_bot_nicks: Optional[List[str]] = None,
    ) -> List[SeatInfo]:
        """Scan lobby and return enriched seat information per table.

        Combines scan_once() result with player/seat parsing.

        Args:
            image:           For OCR backend.
            extra_query:     Extra HTTP query params.
            known_bot_nicks: List of our bot nicknames to exclude from
                             human count.

        Returns:
            List of :class:`SeatInfo` objects.
        """
        result = self.scan_once(image=image, extra_query=extra_query)
        bot_nicks = set(n.lower() for n in (known_bot_nicks or []))

        seats: List[SeatInfo] = []

        # Handle dict stub (fetcher unavailable)
        if isinstance(result, dict):
            return seats

        for table in getattr(result, "tables", []):
            si = SeatInfo(
                table_name=getattr(table, "name", ""),
                stakes=getattr(table, "stakes", ""),
                total_seats=getattr(table, "max_players", 0),
                occupied=getattr(table, "players", 0),
                raw_text=getattr(table, "raw_text", ""),
            )

            # Estimate bot vs human split
            player_names = getattr(table, "player_names", [])
            if player_names:
                bots = sum(1 for n in player_names if n.lower() in bot_nicks)
                si.bot_count = bots
                si.human_count = si.occupied - bots
            else:
                si.human_count = si.occupied
                si.bot_count = 0

            seats.append(si)

        return seats

    def find_targets(
        self,
        seats: List[SeatInfo],
        min_humans: int = 1,
        max_humans: int = 3,
        min_free: int = 3,
        max_table_size: int = 9,
    ) -> List[SeatInfo]:
        """Filter tables eligible for auto-fill (3 bots join).

        A table is a target when:
          - It has between *min_humans* and *max_humans* human players.
          - It has at least *min_free* free seats (to fit our bots).
          - Total seats ≤ *max_table_size*.

        Args:
            seats:          List from :meth:`scan_with_seats`.
            min_humans:     Minimum human players at the table.
            max_humans:     Maximum human players at the table.
            min_free:       Minimum free seats required.
            max_table_size: Maximum table size to consider.

        Returns:
            Filtered list with ``is_target=True``.
        """
        targets: List[SeatInfo] = []
        for s in seats:
            if s.total_seats > max_table_size:
                continue
            if not (min_humans <= s.human_count <= max_humans):
                continue
            if s.free_seats < min_free:
                continue
            s.is_target = True
            targets.append(s)

        logger.info("find_targets: %d/%d tables eligible", len(targets), len(seats))
        return targets


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Live Table Scanner — anti-limit + proxy")
    parser.add_argument("--count", type=int, default=10, help="Number of scans")
    parser.add_argument("--delay", type=float, default=2.0, help="Base delay (seconds)")
    parser.add_argument("--jitter", type=float, default=0.5, help="Delay jitter (seconds)")
    parser.add_argument("--proxy", nargs="*", default=[], help="Proxy URLs")
    parser.add_argument("--proxy-mode", default="round_robin",
                        choices=["round_robin", "random", "failover"])
    parser.add_argument("--strategy", default="auto",
                        choices=["auto", "http_only", "ocr_only"])
    parser.add_argument("--image", default=None, help="Lobby screenshot for OCR")
    parser.add_argument("--skip-delay", action="store_true", help="Skip delays (testing)")

    args = parser.parse_args()

    scanner = LiveTableScanner(
        proxies=args.proxy,
        proxy_mode=args.proxy_mode,
        delay_base=args.delay,
        delay_jitter=args.jitter,
        fetch_strategy=args.strategy,
    )

    print(f"Starting {args.count} scans...")
    results = scanner.scan_loop(
        count=args.count,
        image=args.image,
        skip_delay=args.skip_delay,
    )

    print(f"\n{scanner.stats.summary()}")
