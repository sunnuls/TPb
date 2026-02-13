#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bot_monitor.py — Monitoring + Auto-restart для масштабирования 100+ ботов.

Phase 3 of scaling.md.

Компоненты:
- BotHealth: состояние здоровья одного бота (heartbeat, errors, uptime)
- HealthStatus: enum статусов (HEALTHY, DEGRADED, DEAD, RESTARTING)
- MonitorConfig: конфигурация мониторинга (thresholds, intervals)
- BotMonitor: центральный монитор — heartbeats, проверка, auto-restart
- RestartPolicy: стратегии рестарта (immediate, backoff, circuit_breaker)
- AlertSink: куда отправлять алерты (log, callback, queue)
- MonitorStats: агрегированная статистика по флоту

Pipeline:
  1. Каждый бот отправляет heartbeat → BotMonitor
  2. BotMonitor периодически проверяет все боты
  3. Если бот не heartbeat > threshold → пометить DEAD
  4. Если бот DEAD → auto-restart по RestartPolicy
  5. Если рестарт не помог → circuit breaker → алерт
  6. Статистика: uptime, restarts, fleet health

Usage::

    monitor = BotMonitor(config=MonitorConfig(
        heartbeat_timeout=30.0,
        check_interval=10.0,
        max_restarts=5,
    ))
    monitor.register("bot_1", restart_fn=lambda: start_bot("bot_1"))
    monitor.heartbeat("bot_1")
    monitor.start()

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    """Bot health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"       # responding but with errors
    DEAD = "dead"               # no heartbeat
    RESTARTING = "restarting"   # restart in progress
    STOPPED = "stopped"         # intentionally stopped


class RestartStrategy(str, Enum):
    """How to handle restarts."""
    IMMEDIATE = "immediate"     # restart right away
    BACKOFF = "backoff"         # exponential backoff between restarts
    CIRCUIT_BREAKER = "circuit_breaker"  # stop after N failures


class AlertLevel(str, Enum):
    """Alert severity."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class BotHealth:
    """Health tracking for a single bot."""
    bot_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    last_heartbeat: float = 0.0
    last_check: float = 0.0
    start_time: float = 0.0
    error_count: int = 0
    consecutive_errors: int = 0
    restart_count: int = 0
    last_restart: float = 0.0
    last_error: str = ""
    restart_fn: Optional[Callable] = field(default=None, repr=False)

    @property
    def uptime(self) -> float:
        """Uptime in seconds since last start."""
        if self.start_time <= 0:
            return 0.0
        return time.monotonic() - self.start_time

    @property
    def time_since_heartbeat(self) -> float:
        """Seconds since last heartbeat."""
        if self.last_heartbeat <= 0:
            return float("inf")
        return time.monotonic() - self.last_heartbeat

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "status": self.status.value,
            "uptime": round(self.uptime, 1),
            "time_since_heartbeat": round(self.time_since_heartbeat, 1),
            "error_count": self.error_count,
            "restart_count": self.restart_count,
            "last_error": self.last_error,
        }


@dataclass
class MonitorConfig:
    """Configuration for BotMonitor."""
    heartbeat_timeout: float = 30.0       # seconds w/o heartbeat → DEAD
    degraded_error_threshold: int = 3     # consecutive errors → DEGRADED
    check_interval: float = 10.0          # seconds between health checks
    max_restarts: int = 5                 # max restarts per bot (0=unlimited)
    restart_cooldown: float = 10.0        # min seconds between restarts
    backoff_base: float = 5.0             # initial backoff delay
    backoff_max: float = 300.0            # max backoff delay
    backoff_multiplier: float = 2.0       # backoff growth factor
    restart_strategy: RestartStrategy = RestartStrategy.BACKOFF
    auto_restart: bool = True             # enable auto-restart


@dataclass
class Alert:
    """An alert event."""
    level: AlertLevel
    bot_id: str
    message: str
    timestamp: float = field(default_factory=time.time)

    def __str__(self):
        return f"[{self.level.value.upper()}] {self.bot_id}: {self.message}"


@dataclass
class MonitorStats:
    """Aggregate fleet statistics."""
    total_bots: int = 0
    healthy: int = 0
    degraded: int = 0
    dead: int = 0
    restarting: int = 0
    stopped: int = 0
    total_restarts: int = 0
    total_errors: int = 0
    fleet_uptime_avg: float = 0.0

    @property
    def fleet_health(self) -> float:
        """Percentage of healthy + degraded bots."""
        if self.total_bots == 0:
            return 1.0
        return (self.healthy + self.degraded) / self.total_bots

    def summary(self) -> str:
        return (
            f"Fleet: {self.healthy}/{self.total_bots} healthy, "
            f"{self.degraded} degraded, {self.dead} dead, "
            f"{self.restarting} restarting, {self.stopped} stopped | "
            f"Restarts: {self.total_restarts}, Errors: {self.total_errors} | "
            f"Health: {self.fleet_health:.0%}"
        )


# ---------------------------------------------------------------------------
# BotMonitor — core
# ---------------------------------------------------------------------------

class BotMonitor:
    """Centralized health monitor and auto-restart manager.

    Thread-safe. Can run background checking loop or be polled manually.
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self._config = config or MonitorConfig()
        self._lock = threading.RLock()
        self._bots: Dict[str, BotHealth] = {}
        self._alerts: List[Alert] = []
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        self._check_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # -- Config --

    @property
    def config(self) -> MonitorConfig:
        return self._config

    # -- Registration --

    def register(
        self,
        bot_id: str,
        restart_fn: Optional[Callable] = None,
    ):
        """Register a bot for monitoring.

        Args:
            bot_id: Unique bot identifier.
            restart_fn: Callable to invoke to restart this bot.
                        Signature: () -> bool (True=success).
        """
        now = time.monotonic()
        with self._lock:
            if bot_id not in self._bots:
                self._bots[bot_id] = BotHealth(
                    bot_id=bot_id,
                    status=HealthStatus.HEALTHY,
                    last_heartbeat=now,
                    start_time=now,
                    restart_fn=restart_fn,
                )
                logger.debug("Bot registered: %s", bot_id)

    def unregister(self, bot_id: str):
        """Remove bot from monitoring."""
        with self._lock:
            self._bots.pop(bot_id, None)

    @property
    def bot_count(self) -> int:
        with self._lock:
            return len(self._bots)

    # -- Heartbeat --

    def heartbeat(self, bot_id: str):
        """Record heartbeat from a bot."""
        with self._lock:
            bot = self._bots.get(bot_id)
            if bot:
                bot.last_heartbeat = time.monotonic()
                if bot.status == HealthStatus.DEGRADED:
                    bot.consecutive_errors = 0
                    bot.status = HealthStatus.HEALTHY

    def report_error(self, bot_id: str, error: str = ""):
        """Report error from a bot."""
        with self._lock:
            bot = self._bots.get(bot_id)
            if not bot:
                return
            bot.error_count += 1
            bot.consecutive_errors += 1
            bot.last_error = error
            bot.last_heartbeat = time.monotonic()  # still alive

            if bot.consecutive_errors >= self._config.degraded_error_threshold:
                if bot.status == HealthStatus.HEALTHY:
                    bot.status = HealthStatus.DEGRADED
                    self._emit_alert(AlertLevel.WARNING, bot_id,
                                     f"Degraded after {bot.consecutive_errors} errors: {error}")

    def report_success(self, bot_id: str):
        """Report successful operation — resets consecutive errors."""
        with self._lock:
            bot = self._bots.get(bot_id)
            if bot:
                bot.consecutive_errors = 0
                bot.last_heartbeat = time.monotonic()
                if bot.status == HealthStatus.DEGRADED:
                    bot.status = HealthStatus.HEALTHY

    # -- Health checking --

    def check_all(self) -> List[str]:
        """Check all bots and return list of bot_ids that were restarted.

        Should be called periodically (or use start() for background loop).
        """
        restarted: List[str] = []
        now = time.monotonic()

        with self._lock:
            bots_snapshot = list(self._bots.values())

        for bot in bots_snapshot:
            if bot.status == HealthStatus.STOPPED:
                continue

            bot.last_check = now

            # Check heartbeat timeout
            if bot.time_since_heartbeat > self._config.heartbeat_timeout:
                if bot.status not in (HealthStatus.DEAD, HealthStatus.RESTARTING):
                    with self._lock:
                        bot.status = HealthStatus.DEAD
                    self._emit_alert(AlertLevel.CRITICAL, bot.bot_id,
                                     f"Dead — no heartbeat for {bot.time_since_heartbeat:.0f}s")

            # Auto-restart dead bots
            if bot.status == HealthStatus.DEAD and self._config.auto_restart:
                if self._should_restart(bot):
                    success = self._do_restart(bot)
                    if success:
                        restarted.append(bot.bot_id)

        return restarted

    def _should_restart(self, bot: BotHealth) -> bool:
        """Check if bot should be restarted based on policy."""
        cfg = self._config
        strategy = cfg.restart_strategy

        # Max restarts check
        if cfg.max_restarts > 0 and bot.restart_count >= cfg.max_restarts:
            if bot.status != HealthStatus.STOPPED:
                with self._lock:
                    bot.status = HealthStatus.STOPPED
                self._emit_alert(AlertLevel.CRITICAL, bot.bot_id,
                                 f"Stopped — max restarts ({cfg.max_restarts}) reached")
            return False

        # Cooldown check
        if bot.last_restart > 0:
            elapsed = time.monotonic() - bot.last_restart

            if strategy == RestartStrategy.IMMEDIATE:
                if elapsed < cfg.restart_cooldown:
                    return False

            elif strategy == RestartStrategy.BACKOFF:
                delay = min(
                    cfg.backoff_base * (cfg.backoff_multiplier ** bot.restart_count),
                    cfg.backoff_max,
                )
                if elapsed < delay:
                    return False

            elif strategy == RestartStrategy.CIRCUIT_BREAKER:
                if bot.restart_count >= cfg.max_restarts:
                    return False
                if elapsed < cfg.restart_cooldown:
                    return False

        return True

    def _do_restart(self, bot: BotHealth) -> bool:
        """Execute restart for a bot."""
        with self._lock:
            bot.status = HealthStatus.RESTARTING
            bot.restart_count += 1
            bot.last_restart = time.monotonic()

        restart_fn = bot.restart_fn
        success = False

        if restart_fn:
            try:
                result = restart_fn()
                success = bool(result) if result is not None else True
            except Exception as e:
                success = False
                self._emit_alert(AlertLevel.CRITICAL, bot.bot_id,
                                 f"Restart failed: {e}")
        else:
            # No restart function — simulate success
            success = True

        with self._lock:
            if success:
                bot.status = HealthStatus.HEALTHY
                bot.consecutive_errors = 0
                bot.last_heartbeat = time.monotonic()
                bot.start_time = time.monotonic()
                self._emit_alert(AlertLevel.INFO, bot.bot_id,
                                 f"Restarted successfully (attempt #{bot.restart_count})")
            else:
                bot.status = HealthStatus.DEAD

        return success

    # -- Manual control --

    def stop_bot(self, bot_id: str):
        """Manually stop a bot (no auto-restart)."""
        with self._lock:
            bot = self._bots.get(bot_id)
            if bot:
                bot.status = HealthStatus.STOPPED

    def reset_bot(self, bot_id: str):
        """Reset a bot's health counters."""
        with self._lock:
            bot = self._bots.get(bot_id)
            if bot:
                bot.error_count = 0
                bot.consecutive_errors = 0
                bot.restart_count = 0
                bot.status = HealthStatus.HEALTHY
                bot.last_heartbeat = time.monotonic()
                bot.start_time = time.monotonic()

    # -- Background loop --

    def start(self, interval: Optional[float] = None):
        """Start background health-check loop."""
        if self._check_thread and self._check_thread.is_alive():
            return
        self._stop_event.clear()
        iv = interval or self._config.check_interval
        self._check_thread = threading.Thread(
            target=self._check_loop,
            args=(iv,),
            daemon=True,
            name="bot-monitor",
        )
        self._check_thread.start()
        logger.info("BotMonitor started (interval=%ss)", iv)

    def stop(self):
        """Stop background loop."""
        self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=5)

    def _check_loop(self, interval: float):
        while not self._stop_event.is_set():
            try:
                self.check_all()
            except Exception as e:
                logger.error("Monitor check error: %s", e)
            self._stop_event.wait(interval)

    # -- Alerts --

    def on_alert(self, callback: Callable[[Alert], None]):
        """Register alert callback."""
        self._alert_callbacks.append(callback)

    def _emit_alert(self, level: AlertLevel, bot_id: str, message: str):
        alert = Alert(level=level, bot_id=bot_id, message=message)
        self._alerts.append(alert)
        logger.log(
            logging.CRITICAL if level == AlertLevel.CRITICAL
            else logging.WARNING if level == AlertLevel.WARNING
            else logging.INFO,
            "ALERT: %s", alert,
        )
        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception:
                pass

    @property
    def alerts(self) -> List[Alert]:
        return list(self._alerts)

    def clear_alerts(self):
        self._alerts.clear()

    # -- Statistics --

    def get_stats(self) -> MonitorStats:
        """Aggregate fleet statistics."""
        with self._lock:
            bots = list(self._bots.values())

        stats = MonitorStats(total_bots=len(bots))
        total_uptime = 0.0

        for bot in bots:
            if bot.status == HealthStatus.HEALTHY:
                stats.healthy += 1
            elif bot.status == HealthStatus.DEGRADED:
                stats.degraded += 1
            elif bot.status == HealthStatus.DEAD:
                stats.dead += 1
            elif bot.status == HealthStatus.RESTARTING:
                stats.restarting += 1
            elif bot.status == HealthStatus.STOPPED:
                stats.stopped += 1

            stats.total_restarts += bot.restart_count
            stats.total_errors += bot.error_count
            total_uptime += bot.uptime

        if len(bots) > 0:
            stats.fleet_uptime_avg = total_uptime / len(bots)

        return stats

    def get_bot_health(self, bot_id: str) -> Optional[BotHealth]:
        with self._lock:
            return self._bots.get(bot_id)

    def get_all_health(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [bot.to_dict() for bot in self._bots.values()]
