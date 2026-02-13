"""
Telegram Alerts — Phase 3 of logs.md.

Sends real-time alerts to a Telegram chat/channel when critical
events occur (bans, errors, crashes, session limits, etc.).

Features:
  - ``TelegramSender``: HTTP-based Telegram Bot API client (stdlib only)
  - ``AlertRule``: configurable rule (level filter, keyword match, cooldown)
  - ``AlertManager``: evaluates rules against log records, sends alerts
  - Rate-limiting: per-rule cooldown + global rate limit
  - Message formatting: Markdown with severity emoji
  - ``AlertLoggingHandler``: stdlib Handler that auto-triggers alerts
  - Dry-run mode for testing without a real bot token

Usage::

    sender = TelegramSender(bot_token="123:ABC", chat_id="-100123")
    mgr = AlertManager(sender)
    mgr.add_rule(AlertRule(name="ban", level="CRITICAL", keywords=["ban"]))
    mgr.add_rule(AlertRule(name="errors", level="ERROR"))

    # Process a log record
    mgr.evaluate({"level": "CRITICAL", "msg": "Bot banned on PokerStars"})
    # → sends Telegram message

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Telegram sender
# ---------------------------------------------------------------------------


@dataclass
class SendResult:
    """Result of a Telegram send attempt."""
    success: bool = False
    message_id: Optional[int] = None
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class TelegramSender:
    """Sends messages via Telegram Bot API using stdlib HTTP.

    Parameters:
        bot_token:   Telegram bot token (from @BotFather)
        chat_id:     target chat/channel ID (string)
        timeout:     HTTP request timeout (seconds)
        dry_run:     if True, don't actually send — just log
        parse_mode:  message parse mode ("Markdown" or "HTML")
    """

    API_BASE = "https://api.telegram.org/bot{token}"

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        timeout: int = 10,
        dry_run: bool = False,
        parse_mode: str = "Markdown",
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.dry_run = dry_run
        self.parse_mode = parse_mode
        self._send_log: List[SendResult] = []

    def send_message(self, text: str) -> SendResult:
        """Send a text message to the configured chat.

        Args:
            text: message text (Markdown or plain)

        Returns:
            ``SendResult`` with success status.
        """
        if self.dry_run:
            result = SendResult(
                success=True,
                message_id=len(self._send_log) + 1,
            )
            self._send_log.append(result)
            logger.debug(f"[DRY-RUN] Telegram alert: {text[:100]}")
            return result

        if not self.bot_token or not self.chat_id:
            result = SendResult(success=False, error="Missing bot_token or chat_id")
            self._send_log.append(result)
            return result

        url = f"{self.API_BASE.format(token=self.bot_token)}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": True,
        }

        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("ok"):
                    msg_id = body.get("result", {}).get("message_id")
                    result = SendResult(success=True, message_id=msg_id)
                else:
                    result = SendResult(
                        success=False,
                        error=body.get("description", "Unknown error"),
                    )
        except (URLError, OSError) as e:
            result = SendResult(success=False, error=str(e))
        except json.JSONDecodeError as e:
            result = SendResult(success=False, error=f"JSON parse error: {e}")

        self._send_log.append(result)
        return result

    @property
    def send_history(self) -> List[SendResult]:
        return list(self._send_log)

    @property
    def total_sent(self) -> int:
        return sum(1 for r in self._send_log if r.success)

    @property
    def total_failed(self) -> int:
        return sum(1 for r in self._send_log if not r.success)

    def clear_history(self):
        self._send_log.clear()


# ---------------------------------------------------------------------------
# Alert rules
# ---------------------------------------------------------------------------

# Severity levels for filtering
LEVEL_PRIORITY = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


@dataclass
class AlertRule:
    """Defines when to trigger an alert.

    Attributes:
        name:           rule identifier
        level:          minimum log level to trigger (e.g. "ERROR")
        keywords:       trigger if any keyword is in the message (case-insensitive)
        exclude_keywords: don't trigger if any of these are present
        cooldown_s:     minimum seconds between alerts for this rule
        enabled:        is the rule active?
        format_fn:      optional custom message formatter
    """
    name: str = "default"
    level: str = "ERROR"
    keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    cooldown_s: float = 60.0
    enabled: bool = True
    format_fn: Optional[Callable[[Dict[str, Any]], str]] = None

    @property
    def level_priority(self) -> int:
        return LEVEL_PRIORITY.get(self.level, 0)


# ---------------------------------------------------------------------------
# Message formatter
# ---------------------------------------------------------------------------

SEVERITY_EMOJI = {
    "DEBUG": "🔍",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🚨",
}


def default_format_alert(record: Dict[str, Any], rule_name: str = "") -> str:
    """Format a log record as a Telegram alert message.

    Returns Markdown-formatted text.
    """
    level = record.get("level", "INFO")
    emoji = SEVERITY_EMOJI.get(level, "📋")
    msg = record.get("msg", "")
    ts = record.get("ts", "")
    logger_name = record.get("logger", "")

    lines = [
        f"{emoji} *{level}*  `{rule_name}`",
        "",
        f"```",
        f"{msg}",
        f"```",
    ]

    # Add context fields
    context_keys = [k for k in record if k not in ("ts", "level", "logger", "msg")]
    if context_keys:
        ctx_lines = [f"  {k}: {record[k]}" for k in context_keys[:8]]
        lines.append("")
        lines.append("*Context:*")
        lines.extend(ctx_lines)

    lines.append("")
    lines.append(f"_{ts}_ | `{logger_name}`")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alert manager
# ---------------------------------------------------------------------------


class AlertManager:
    """Evaluates log records against rules and sends alerts.

    Features:
      - Multiple rules with different triggers
      - Per-rule cooldown (no spam)
      - Global rate limit
      - Alert history

    Parameters:
        sender:             TelegramSender instance
        global_rate_limit:  max alerts per minute (0 = unlimited)
    """

    def __init__(
        self,
        sender: TelegramSender,
        global_rate_limit: int = 10,
    ):
        self._sender = sender
        self._rules: Dict[str, AlertRule] = {}
        self._last_fire: Dict[str, float] = {}   # rule_name → timestamp
        self._global_rate = global_rate_limit
        self._global_window: List[float] = []     # timestamps of recent alerts
        self._alert_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    # -- Rule management -----------------------------------------------------

    def add_rule(self, rule: AlertRule):
        """Register an alert rule."""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def get_rule(self, name: str) -> Optional[AlertRule]:
        return self._rules.get(name)

    def list_rules(self) -> List[str]:
        return list(self._rules.keys())

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    # -- Evaluation ----------------------------------------------------------

    def evaluate(self, record: Dict[str, Any]) -> List[str]:
        """Evaluate a log record against all rules.

        Returns list of rule names that fired (sent alerts).
        """
        fired: List[str] = []

        for name, rule in self._rules.items():
            if not rule.enabled:
                continue

            if self._matches(record, rule):
                if self._can_fire(name, rule):
                    text = self._format(record, rule)
                    result = self._sender.send_message(text)

                    with self._lock:
                        self._last_fire[name] = time.time()
                        self._global_window.append(time.time())
                        self._alert_log.append({
                            "rule": name,
                            "record": record,
                            "success": result.success,
                            "timestamp": time.time(),
                        })

                    fired.append(name)

        return fired

    def _matches(self, record: Dict[str, Any], rule: AlertRule) -> bool:
        """Check if a record matches a rule."""
        # Level check
        rec_level = record.get("level", "INFO")
        rec_priority = LEVEL_PRIORITY.get(rec_level, 0)
        if rec_priority < rule.level_priority:
            return False

        msg = record.get("msg", "").lower()

        # Exclude keywords
        for kw in rule.exclude_keywords:
            if kw.lower() in msg:
                return False

        # Keyword match (if keywords are specified)
        if rule.keywords:
            return any(kw.lower() in msg for kw in rule.keywords)

        # No keywords = match on level alone
        return True

    def _can_fire(self, rule_name: str, rule: AlertRule) -> bool:
        """Check cooldown and rate limits."""
        now = time.time()

        # Per-rule cooldown
        last = self._last_fire.get(rule_name, 0)
        if (now - last) < rule.cooldown_s:
            return False

        # Global rate limit
        if self._global_rate > 0:
            with self._lock:
                # Clean old entries (> 60s)
                self._global_window = [
                    t for t in self._global_window if (now - t) < 60
                ]
                if len(self._global_window) >= self._global_rate:
                    return False

        return True

    def _format(self, record: Dict[str, Any], rule: AlertRule) -> str:
        """Format the alert message."""
        if rule.format_fn:
            return rule.format_fn(record)
        return default_format_alert(record, rule_name=rule.name)

    # -- History / stats -----------------------------------------------------

    @property
    def alert_log(self) -> List[Dict[str, Any]]:
        return list(self._alert_log)

    @property
    def total_alerts(self) -> int:
        return len(self._alert_log)

    @property
    def successful_alerts(self) -> int:
        return sum(1 for a in self._alert_log if a.get("success"))

    def alerts_for_rule(self, name: str) -> List[Dict[str, Any]]:
        return [a for a in self._alert_log if a.get("rule") == name]

    def clear_history(self):
        self._alert_log.clear()
        self._global_window.clear()
        self._last_fire.clear()


# ---------------------------------------------------------------------------
# Logging handler bridge
# ---------------------------------------------------------------------------


class AlertLoggingHandler(logging.Handler):
    """stdlib logging.Handler that auto-triggers Telegram alerts.

    Bridges Python's logging framework with ``AlertManager``.

    Usage::

        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender)
        mgr.add_rule(AlertRule(name="errors", level="ERROR"))

        handler = AlertLoggingHandler(mgr)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, manager: AlertManager, level: int = logging.WARNING):
        super().__init__(level=level)
        self._manager = manager
        # Use StructuredFormatter to get JSON records
        try:
            from launcher.structured_logger import StructuredFormatter
            self.setFormatter(StructuredFormatter())
        except ImportError:
            pass

    def emit(self, record: logging.LogRecord):
        try:
            if self.formatter:
                formatted = self.format(record)
                parsed = json.loads(formatted)
            else:
                parsed = {
                    "ts": "",
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                }
            self._manager.evaluate(parsed)
        except Exception:
            pass  # never crash on logging
