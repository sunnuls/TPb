#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
proxy_manager.py — Централизованный Proxy Pool для масштабирования 100+ ботов.

Phase 1 of scaling.md.

Возможности:
- Пул прокси с загрузкой из файла / списка / ENV
- Thread-safe ротация (round-robin, random, least-used, weighted, geo)
- Health checking — периодическая проверка живости прокси
- Per-bot assignment — закрепление прокси за конкретным ботом
- Load balancing — распределение нагрузки (sticky / round-robin)
- Auto-disable / auto-reenable с cooldown
- Rate limiting per proxy (requests/sec)
- Statistics: usage count, latency, failure rate per proxy
- Поддержка HTTP, SOCKS4, SOCKS5 (через url scheme)

Architecture:
- ProxyPool — глобальный пул (singleton-ready)
- ProxyEntry — дата-класс одного прокси с метриками
- ProxyHealthChecker — фоновый thread для проверки
- BotProxyAssigner — маппинг bot_id → proxy

Usage::

    pool = ProxyPool.from_file("proxies.txt")
    pool.start_health_checker(interval=60)

    # Per-bot assignment
    assigner = BotProxyAssigner(pool, sticky=True)
    proxy = assigner.get_proxy("bot_42")

    # After request
    pool.report_success(proxy.url)
    # or
    pool.report_failure(proxy.url)

    pool.stop()

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Optional: httpx / requests / urllib for health checks
try:
    import httpx  # type: ignore
    _HAS_HTTPX = True
except (ImportError, Exception):
    _HAS_HTTPX = False

try:
    import requests as _requests_mod  # type: ignore
    _HAS_REQUESTS = True
except (ImportError, Exception):
    _HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProxyProtocol(str, Enum):
    """Supported proxy protocols."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class RotationMode(str, Enum):
    """Proxy rotation strategy."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    WEIGHTED = "weighted"       # prefer lower-latency proxies
    GEO = "geo"                 # prefer proxies from specific region


class ProxyStatus(str, Enum):
    """Health status of a proxy."""
    ACTIVE = "active"
    DEGRADED = "degraded"       # responding but slow
    DISABLED = "disabled"       # too many failures
    COOLDOWN = "cooldown"       # temporarily disabled, will re-enable


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ProxyEntry:
    """Single proxy with its metadata and metrics."""
    url: str
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    region: str = ""
    weight: float = 1.0             # for weighted rotation

    # Runtime metrics
    status: ProxyStatus = ProxyStatus.ACTIVE
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    disabled_at: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def is_available(self) -> bool:
        return self.status in (ProxyStatus.ACTIVE, ProxyStatus.DEGRADED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "protocol": self.protocol.value,
            "region": self.region,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class PoolConfig:
    """Configuration for ProxyPool."""
    rotation_mode: RotationMode = RotationMode.ROUND_ROBIN
    max_failures: int = 5                 # disable after N consecutive failures
    cooldown_seconds: float = 300.0       # re-enable after N seconds
    degraded_latency_ms: float = 5000.0   # mark as degraded above this latency
    health_check_url: str = "https://httpbin.org/ip"
    health_check_timeout: float = 10.0
    health_check_interval: float = 60.0
    rate_limit_per_proxy: float = 0.0     # max req/sec per proxy (0=unlimited)
    preferred_region: str = ""            # for GEO mode


@dataclass
class PoolStats:
    """Aggregate statistics for the entire pool."""
    total_proxies: int = 0
    active_proxies: int = 0
    disabled_proxies: int = 0
    cooldown_proxies: int = 0
    degraded_proxies: int = 0
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.total_successes / self.total_requests

    def summary(self) -> str:
        return (
            f"Pool: {self.active_proxies}/{self.total_proxies} active, "
            f"{self.disabled_proxies} disabled, {self.cooldown_proxies} cooldown | "
            f"Requests: {self.total_requests} "
            f"(success={self.success_rate:.1%}) "
            f"avg_latency={self.avg_latency_ms:.0f}ms"
        )


# ---------------------------------------------------------------------------
# ProxyPool — core
# ---------------------------------------------------------------------------

class ProxyPool:
    """Centralized thread-safe proxy pool for 100+ bots.

    Manages a collection of proxy entries with automatic rotation,
    health checking, failure tracking, and load balancing.
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        config: Optional[PoolConfig] = None,
    ):
        self._config = config or PoolConfig()
        self._lock = threading.RLock()
        self._entries: Dict[str, ProxyEntry] = {}
        self._rr_index = 0
        self._health_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._rate_timestamps: Dict[str, List[float]] = {}

        if proxies:
            for url in proxies:
                self.add_proxy(url)

    # -- Factory methods --

    @classmethod
    def from_file(cls, path: str | Path, config: Optional[PoolConfig] = None) -> "ProxyPool":
        """Load proxies from text file (one per line, # comments)."""
        p = Path(path)
        proxies: List[str] = []
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        pool = cls(proxies=proxies, config=config)
        logger.info("Loaded %d proxies from %s", len(proxies), path)
        return pool

    @classmethod
    def from_env(cls, var: str = "PROXY_LIST", config: Optional[PoolConfig] = None) -> "ProxyPool":
        """Load proxies from environment variable (comma or newline separated)."""
        raw = os.environ.get(var, "")
        proxies = [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]
        pool = cls(proxies=proxies, config=config)
        logger.info("Loaded %d proxies from env %s", len(proxies), var)
        return pool

    # -- Config --

    @property
    def config(self) -> PoolConfig:
        return self._config

    # -- Proxy management --

    def add_proxy(self, url: str, region: str = "", weight: float = 1.0):
        """Add a proxy to the pool."""
        url = url.strip()
        if not url:
            return
        protocol = self._detect_protocol(url)
        with self._lock:
            if url not in self._entries:
                self._entries[url] = ProxyEntry(
                    url=url,
                    protocol=protocol,
                    region=region,
                    weight=weight,
                )
                logger.debug("Proxy added: %s (%s)", url, protocol.value)

    def remove_proxy(self, url: str):
        """Remove a proxy from the pool."""
        with self._lock:
            self._entries.pop(url, None)

    @property
    def size(self) -> int:
        """Total number of proxies in pool."""
        with self._lock:
            return len(self._entries)

    @property
    def all_proxies(self) -> List[ProxyEntry]:
        """All proxy entries."""
        with self._lock:
            return list(self._entries.values())

    @property
    def available_proxies(self) -> List[ProxyEntry]:
        """Only proxies that are available (active or degraded)."""
        self._check_cooldowns()
        with self._lock:
            return [e for e in self._entries.values() if e.is_available]

    # -- Rotation --

    def next_proxy(self) -> Optional[ProxyEntry]:
        """Get the next proxy according to rotation mode.

        Thread-safe. Returns None if no proxies are available.
        """
        available = self.available_proxies
        if not available:
            return None

        mode = self._config.rotation_mode
        with self._lock:
            return self._select(available, mode)

    def _select(self, available: List[ProxyEntry], mode: RotationMode) -> ProxyEntry:
        if mode == RotationMode.ROUND_ROBIN:
            self._rr_index = self._rr_index % len(available)
            entry = available[self._rr_index]
            self._rr_index += 1
            return entry

        elif mode == RotationMode.RANDOM:
            return random.choice(available)

        elif mode == RotationMode.LEAST_USED:
            return min(available, key=lambda e: e.total_requests)

        elif mode == RotationMode.WEIGHTED:
            # Higher weight + lower latency = more likely
            weights = []
            for e in available:
                latency_factor = max(0.1, 1.0 - e.avg_latency_ms / 10000.0)
                w = e.weight * e.success_rate * latency_factor
                weights.append(max(0.01, w))
            total = sum(weights)
            r = random.uniform(0, total)
            cumulative = 0.0
            for e, w in zip(available, weights):
                cumulative += w
                if r <= cumulative:
                    return e
            return available[-1]

        elif mode == RotationMode.GEO:
            preferred = self._config.preferred_region.lower()
            if preferred:
                geo_match = [e for e in available if e.region.lower() == preferred]
                if geo_match:
                    return random.choice(geo_match)
            return random.choice(available)

        return available[0]

    # -- Reporting --

    def report_success(self, url: str, latency_ms: float = 0.0):
        """Report successful request through proxy."""
        with self._lock:
            entry = self._entries.get(url)
            if not entry:
                return
            entry.total_requests += 1
            entry.successful_requests += 1
            entry.consecutive_failures = 0
            entry.last_used = time.monotonic()
            entry.last_success = time.monotonic()

            # Update rolling average latency
            if latency_ms > 0:
                if entry.avg_latency_ms == 0:
                    entry.avg_latency_ms = latency_ms
                else:
                    entry.avg_latency_ms = entry.avg_latency_ms * 0.8 + latency_ms * 0.2

            # Check if was degraded but now OK
            if entry.status == ProxyStatus.DEGRADED and entry.avg_latency_ms < self._config.degraded_latency_ms:
                entry.status = ProxyStatus.ACTIVE

    def report_failure(self, url: str):
        """Report failed request through proxy."""
        with self._lock:
            entry = self._entries.get(url)
            if not entry:
                return
            entry.total_requests += 1
            entry.failed_requests += 1
            entry.consecutive_failures += 1
            entry.last_used = time.monotonic()
            entry.last_failure = time.monotonic()

            # Disable if too many failures
            if entry.consecutive_failures >= self._config.max_failures:
                entry.status = ProxyStatus.COOLDOWN
                entry.disabled_at = time.monotonic()
                logger.warning("Proxy in cooldown: %s (%d consecutive failures)",
                               url, entry.consecutive_failures)

    # -- Rate limiting --

    def check_rate_limit(self, url: str) -> bool:
        """Check if proxy is within rate limit. Returns True if OK."""
        limit = self._config.rate_limit_per_proxy
        if limit <= 0:
            return True
        now = time.monotonic()
        window = 1.0  # 1 second window
        with self._lock:
            timestamps = self._rate_timestamps.setdefault(url, [])
            # Remove old timestamps
            timestamps[:] = [t for t in timestamps if now - t < window]
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True

    # -- Cooldown management --

    def _check_cooldowns(self):
        """Re-enable proxies that have cooled down."""
        now = time.monotonic()
        cooldown = self._config.cooldown_seconds
        with self._lock:
            for entry in self._entries.values():
                if entry.status == ProxyStatus.COOLDOWN:
                    if now - entry.disabled_at >= cooldown:
                        entry.status = ProxyStatus.ACTIVE
                        entry.consecutive_failures = 0
                        logger.info("Proxy re-enabled: %s", entry.url)

    # -- Health checking --

    def start_health_checker(self, interval: Optional[float] = None):
        """Start background health check thread."""
        if self._health_thread and self._health_thread.is_alive():
            return
        self._stop_event.clear()
        iv = interval or self._config.health_check_interval
        self._health_thread = threading.Thread(
            target=self._health_loop,
            args=(iv,),
            daemon=True,
            name="proxy-health",
        )
        self._health_thread.start()
        logger.info("Health checker started (interval=%ss)", iv)

    def stop(self):
        """Stop health checker thread."""
        self._stop_event.set()
        if self._health_thread:
            self._health_thread.join(timeout=5)

    def _health_loop(self, interval: float):
        while not self._stop_event.is_set():
            self.check_all_health()
            self._stop_event.wait(interval)

    def check_all_health(self):
        """Run health check on all proxies (synchronous)."""
        proxies_snapshot = self.all_proxies
        for entry in proxies_snapshot:
            if self._stop_event.is_set():
                break
            self._health_check_one(entry)

    def _health_check_one(self, entry: ProxyEntry):
        """Check single proxy health."""
        url = entry.url
        check_url = self._config.health_check_url
        timeout = self._config.health_check_timeout

        start = time.monotonic()
        ok = False

        try:
            if _HAS_HTTPX:
                resp = httpx.get(
                    check_url,
                    proxies={entry.protocol.value: url},
                    timeout=timeout,
                )
                ok = resp.status_code == 200
            elif _HAS_REQUESTS:
                resp = _requests_mod.get(
                    check_url,
                    proxies={entry.protocol.value: url},
                    timeout=timeout,
                )
                ok = resp.status_code == 200
            else:
                # No HTTP library — assume proxy is OK
                ok = True
        except Exception:
            ok = False

        latency_ms = (time.monotonic() - start) * 1000

        with self._lock:
            if ok:
                self.report_success(url, latency_ms)
                if latency_ms > self._config.degraded_latency_ms:
                    entry.status = ProxyStatus.DEGRADED
            else:
                self.report_failure(url)

    # -- Statistics --

    def get_stats(self) -> PoolStats:
        """Get aggregate pool statistics."""
        with self._lock:
            entries = list(self._entries.values())

        stats = PoolStats(total_proxies=len(entries))
        total_latency = 0.0
        latency_count = 0

        for e in entries:
            if e.status == ProxyStatus.ACTIVE:
                stats.active_proxies += 1
            elif e.status == ProxyStatus.DISABLED:
                stats.disabled_proxies += 1
            elif e.status == ProxyStatus.COOLDOWN:
                stats.cooldown_proxies += 1
            elif e.status == ProxyStatus.DEGRADED:
                stats.degraded_proxies += 1

            stats.total_requests += e.total_requests
            stats.total_successes += e.successful_requests
            stats.total_failures += e.failed_requests

            if e.avg_latency_ms > 0:
                total_latency += e.avg_latency_ms
                latency_count += 1

        if latency_count > 0:
            stats.avg_latency_ms = total_latency / latency_count

        return stats

    def get_proxy_report(self) -> List[Dict[str, Any]]:
        """Get per-proxy report."""
        with self._lock:
            return [e.to_dict() for e in self._entries.values()]

    # -- Helpers --

    @staticmethod
    def _detect_protocol(url: str) -> ProxyProtocol:
        lower = url.lower()
        if lower.startswith("socks5"):
            return ProxyProtocol.SOCKS5
        elif lower.startswith("socks4"):
            return ProxyProtocol.SOCKS4
        elif lower.startswith("https"):
            return ProxyProtocol.HTTPS
        return ProxyProtocol.HTTP

    def reset(self):
        """Reset all metrics and re-enable all proxies."""
        with self._lock:
            for entry in self._entries.values():
                entry.status = ProxyStatus.ACTIVE
                entry.total_requests = 0
                entry.successful_requests = 0
                entry.failed_requests = 0
                entry.consecutive_failures = 0
                entry.avg_latency_ms = 0.0
                entry.disabled_at = 0.0
            self._rr_index = 0
            self._rate_timestamps.clear()


# ---------------------------------------------------------------------------
# BotProxyAssigner — per-bot proxy mapping
# ---------------------------------------------------------------------------

class BotProxyAssigner:
    """Assigns proxies to bots with optional sticky (persistent) assignment.

    In sticky mode, each bot always gets the same proxy (unless it fails).
    In non-sticky mode, a new proxy is fetched from pool each time.
    """

    def __init__(self, pool: ProxyPool, sticky: bool = True):
        self._pool = pool
        self._sticky = sticky
        self._assignments: Dict[str, str] = {}  # bot_id → proxy_url
        self._lock = threading.Lock()

    @property
    def pool(self) -> ProxyPool:
        return self._pool

    @property
    def sticky(self) -> bool:
        return self._sticky

    @property
    def assignments(self) -> Dict[str, str]:
        """Current bot → proxy mapping (copy)."""
        with self._lock:
            return dict(self._assignments)

    def get_proxy(self, bot_id: str) -> Optional[ProxyEntry]:
        """Get proxy for a specific bot.

        In sticky mode: returns same proxy each time (or reassigns if unavailable).
        In non-sticky mode: fetches next from pool rotation.
        """
        if not self._sticky:
            return self._pool.next_proxy()

        with self._lock:
            assigned_url = self._assignments.get(bot_id)

        if assigned_url:
            # Check if assigned proxy is still available
            entry = self._find_entry(assigned_url)
            if entry and entry.is_available:
                return entry
            # Proxy no longer available — reassign
            logger.info("Reassigning proxy for bot %s (previous unavailable)", bot_id)

        # Assign new proxy
        entry = self._pool.next_proxy()
        if entry:
            with self._lock:
                self._assignments[bot_id] = entry.url
        return entry

    def release(self, bot_id: str):
        """Release proxy assignment for a bot."""
        with self._lock:
            self._assignments.pop(bot_id, None)

    def release_all(self):
        """Release all assignments."""
        with self._lock:
            self._assignments.clear()

    def reassign(self, bot_id: str) -> Optional[ProxyEntry]:
        """Force reassignment for a bot."""
        self.release(bot_id)
        return self.get_proxy(bot_id)

    def bots_per_proxy(self) -> Dict[str, int]:
        """Count of bots assigned to each proxy."""
        with self._lock:
            counts: Dict[str, int] = {}
            for proxy_url in self._assignments.values():
                counts[proxy_url] = counts.get(proxy_url, 0) + 1
            return counts

    def _find_entry(self, url: str) -> Optional[ProxyEntry]:
        entries = self._pool.all_proxies
        for e in entries:
            if e.url == url:
                return e
        return None
