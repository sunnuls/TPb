"""
Structured Logger — Phase 1 of logs.md.

JSON-based structured logging that outputs machine-parseable log records
to files and/or stdout.  Every log entry is a single JSON line containing:
  - timestamp (ISO-8601)
  - level
  - logger name
  - message
  - arbitrary context fields (bot_id, action, table, etc.)

Features:
  - ``StructuredFormatter``: stdlib Formatter that emits JSON lines
  - ``RotatingJSONHandler``: file handler with size-based rotation
  - ``ContextLogger``: wrapper that auto-injects context fields
  - ``LogAggregator``: collect & query structured log records in-memory
  - ``setup_structured_logging()``: one-call global setup

Usage::

    logger = get_structured_logger("bot.engine", bot_id="abc123")
    logger.info("Hand started", hand_id=42, table="NL50")
    # → {"ts":"2026-02-10T12:00:00","level":"INFO","logger":"bot.engine",
    #    "msg":"Hand started","bot_id":"abc123","hand_id":42,"table":"NL50"}

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Each record contains at minimum:
        ``ts``, ``level``, ``logger``, ``msg``

    Extra context is merged from:
      1. ``record.__dict__`` (any extras passed via ``extra={...}``)
      2. Keys starting with ``ctx_`` are stripped of the prefix.

    Parameters:
        include_exc:   include exception info (as ``exc_text``)
        include_stack: include stack info
        ts_utc:        use UTC timestamps (default: local)
        extra_keys:    whitelist of extra keys to include (None = all)
    """

    # Keys that belong to the standard LogRecord and should be excluded
    _BUILTIN_KEYS = frozenset({
        "name", "msg", "args", "created", "relativeCreated",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "filename", "module", "pathname", "thread", "threadName",
        "process", "processName", "msecs", "levelname", "levelno",
        "message", "taskName",
    })

    def __init__(
        self,
        include_exc: bool = True,
        include_stack: bool = False,
        ts_utc: bool = False,
        extra_keys: Optional[Sequence[str]] = None,
    ):
        super().__init__()
        self.include_exc = include_exc
        self.include_stack = include_stack
        self.ts_utc = ts_utc
        self.extra_keys = set(extra_keys) if extra_keys else None

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp
        if self.ts_utc:
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(record.created)
        ts = dt.isoformat(timespec="milliseconds")

        # Base fields
        obj: Dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Extra context fields
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                obj[key[4:]] = value
            elif key not in self._BUILTIN_KEYS and not key.startswith("_"):
                if self.extra_keys is None or key in self.extra_keys:
                    obj[key] = value

        # Exception
        if self.include_exc and record.exc_info and record.exc_info[0]:
            obj["exc_type"] = record.exc_info[0].__name__
            obj["exc_text"] = self.formatException(record.exc_info)

        # Stack
        if self.include_stack and record.stack_info:
            obj["stack"] = record.stack_info

        return json.dumps(obj, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Rotating JSON file handler
# ---------------------------------------------------------------------------


class RotatingJSONHandler(RotatingFileHandler):
    """RotatingFileHandler pre-configured for JSON structured logs.

    Parameters:
        filename:       log file path
        max_bytes:      max file size before rotation (default 10 MB)
        backup_count:   number of rotated files to keep
        encoding:       file encoding
    """

    def __init__(
        self,
        filename: str = "logs/structured.jsonl",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        encoding: str = "utf-8",
    ):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(
            filename=str(path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
        )
        self.setFormatter(StructuredFormatter())


# ---------------------------------------------------------------------------
# Context logger (wrapper)
# ---------------------------------------------------------------------------


class ContextLogger:
    """Logger wrapper that automatically injects context fields.

    Usage::

        log = ContextLogger(logging.getLogger("bot"), bot_id="abc")
        log.info("Started", table="NL50")
        # → {"bot_id":"abc","table":"NL50","msg":"Started",...}
    """

    def __init__(
        self,
        logger: logging.Logger,
        **context: Any,
    ):
        self._logger = logger
        self._context: Dict[str, Any] = dict(context)

    def bind(self, **kwargs: Any) -> ContextLogger:
        """Return a new ContextLogger with additional context."""
        merged = {**self._context, **kwargs}
        return ContextLogger(self._logger, **merged)

    def unbind(self, *keys: str) -> ContextLogger:
        """Return a new ContextLogger without the specified keys."""
        ctx = {k: v for k, v in self._context.items() if k not in keys}
        return ContextLogger(self._logger, **ctx)

    @property
    def context(self) -> Dict[str, Any]:
        return dict(self._context)

    def _make_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        extra = {}
        for k, v in self._context.items():
            extra[f"ctx_{k}"] = v
        for k, v in kwargs.items():
            extra[f"ctx_{k}"] = v
        return extra

    # -- logging methods -----------------------------------------------------

    def debug(self, msg: str, **kwargs: Any):
        self._logger.debug(msg, extra=self._make_extra(kwargs))

    def info(self, msg: str, **kwargs: Any):
        self._logger.info(msg, extra=self._make_extra(kwargs))

    def warning(self, msg: str, **kwargs: Any):
        self._logger.warning(msg, extra=self._make_extra(kwargs))

    def error(self, msg: str, **kwargs: Any):
        self._logger.error(msg, extra=self._make_extra(kwargs))

    def critical(self, msg: str, **kwargs: Any):
        self._logger.critical(msg, extra=self._make_extra(kwargs))

    def exception(self, msg: str, **kwargs: Any):
        self._logger.exception(msg, extra=self._make_extra(kwargs))


# ---------------------------------------------------------------------------
# In-memory log aggregator
# ---------------------------------------------------------------------------


class LogAggregator(logging.Handler):
    """In-memory structured log store with query capabilities.

    Stores parsed JSON records for filtering, counting, and retrieval.
    Thread-safe.

    Parameters:
        max_records:  maximum records to keep (FIFO eviction)
    """

    def __init__(self, max_records: int = 50_000, level: int = logging.DEBUG):
        super().__init__(level=level)
        self.max_records = max_records
        self._records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.setFormatter(StructuredFormatter())

    def emit(self, record: logging.LogRecord):
        try:
            formatted = self.format(record)
            parsed = json.loads(formatted)
            with self._lock:
                self._records.append(parsed)
                if len(self._records) > self.max_records:
                    self._records = self._records[-self.max_records:]
        except Exception:
            pass  # never crash on logging

    # -- query API -----------------------------------------------------------

    def query(
        self,
        level: Optional[str] = None,
        logger: Optional[str] = None,
        contains: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query stored records.

        Args:
            level:    filter by level (e.g. "ERROR")
            logger:   filter by logger name prefix
            contains: message substring filter
            fields:   exact-match on context fields
            limit:    max results (most recent first)

        Returns:
            List of matching JSON records.
        """
        with self._lock:
            results = list(reversed(self._records))

        filtered = []
        for rec in results:
            if level and rec.get("level") != level:
                continue
            if logger and not rec.get("logger", "").startswith(logger):
                continue
            if contains and contains.lower() not in rec.get("msg", "").lower():
                continue
            if fields:
                if not all(rec.get(k) == v for k, v in fields.items()):
                    continue
            filtered.append(rec)
            if len(filtered) >= limit:
                break

        return filtered

    def count(self, level: Optional[str] = None) -> int:
        """Count records, optionally filtered by level."""
        with self._lock:
            if level is None:
                return len(self._records)
            return sum(1 for r in self._records if r.get("level") == level)

    def count_by_level(self) -> Dict[str, int]:
        """Return {level: count}."""
        with self._lock:
            counts: Dict[str, int] = {}
            for r in self._records:
                lv = r.get("level", "UNKNOWN")
                counts[lv] = counts.get(lv, 0) + 1
        return counts

    def recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get most recent n records."""
        with self._lock:
            return list(self._records[-n:])

    def errors(self, n: int = 50) -> List[Dict[str, Any]]:
        """Shortcut: last n ERROR/CRITICAL records."""
        return self.query(level=None, limit=n * 2)  # pre-filter below
        # Actually let's do it properly:

    def errors_and_criticals(self, n: int = 50) -> List[Dict[str, Any]]:
        """Last n ERROR + CRITICAL records."""
        with self._lock:
            errs = [
                r for r in reversed(self._records)
                if r.get("level") in ("ERROR", "CRITICAL")
            ]
        return errs[:n]

    def clear(self):
        with self._lock:
            self._records.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._records)


# ---------------------------------------------------------------------------
# Global setup
# ---------------------------------------------------------------------------

_structured_handler: Optional[RotatingJSONHandler] = None
_aggregator: Optional[LogAggregator] = None


def setup_structured_logging(
    log_dir: str = "logs",
    filename: str = "structured.jsonl",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console_json: bool = False,
    level: int = logging.DEBUG,
    aggregator_size: int = 50_000,
) -> Tuple[RotatingJSONHandler, LogAggregator]:
    """One-call global structured logging setup.

    Adds a ``RotatingJSONHandler`` and a ``LogAggregator`` to the
    root logger.

    Args:
        log_dir:         directory for log files
        filename:        JSON log filename
        max_bytes:       rotation size
        backup_count:    rotated files to keep
        console_json:    also print JSON to stdout?
        level:           minimum level
        aggregator_size: max in-memory records

    Returns:
        (file_handler, aggregator)
    """
    global _structured_handler, _aggregator

    root = logging.getLogger()
    root.setLevel(level)

    # File handler
    filepath = os.path.join(log_dir, filename)
    fh = RotatingJSONHandler(
        filename=filepath,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    fh.setLevel(level)
    root.addHandler(fh)
    _structured_handler = fh

    # Aggregator
    agg = LogAggregator(max_records=aggregator_size, level=level)
    root.addHandler(agg)
    _aggregator = agg

    # Console JSON (optional)
    if console_json:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(level)
        sh.setFormatter(StructuredFormatter())
        root.addHandler(sh)

    return fh, agg


def get_structured_logger(name: str, **context: Any) -> ContextLogger:
    """Get a ``ContextLogger`` with structured output.

    Args:
        name:     logger name (e.g. "bot.engine")
        context:  default context fields

    Returns:
        ``ContextLogger`` wrapping the named logger.
    """
    return ContextLogger(logging.getLogger(name), **context)


def get_aggregator() -> Optional[LogAggregator]:
    """Get the global LogAggregator (if setup_structured_logging was called)."""
    return _aggregator
