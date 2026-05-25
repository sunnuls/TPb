"""
Session Logger — persists per-bot session records to JSON.

A "session" starts when a bot transitions to an active state (PLAYING /
SEARCHING / SEATED) and ends when it reaches STOPPED / ERROR / IDLE.

Records are appended to  config/session_history.json  and kept up to
MAX_RECORDS = 500 entries.  The file is human-readable and can be opened
in any text editor or imported into a spreadsheet.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_RECORDS = 500
DEFAULT_PATH = Path("config") / "session_history.json"


@dataclass
class SessionRecord:
    """A single bot session."""
    bot_id:     str
    nickname:   str
    started_at: float               # Unix timestamp
    ended_at:   Optional[float] = None
    hands:      int   = 0
    profit:     float = 0.0
    table:      str   = ""
    profile:    str   = ""
    end_reason: str   = ""          # "stopped" | "error" | "emergency" | ""

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def duration_s(self) -> float:
        end = self.ended_at or time.time()
        return max(0.0, end - self.started_at)

    @property
    def duration_str(self) -> str:
        s = int(self.duration_s)
        h, m = divmod(s, 3600)
        m, s = divmod(m, 60)
        if h:
            return f"{h}h {m:02d}m {s:02d}s"
        if m:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    @property
    def started_str(self) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(self.started_at).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @property
    def profit_str(self) -> str:
        sign = "+" if self.profit >= 0 else ""
        return f"{sign}{self.profit:.2f}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SessionRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SessionLogger:
    """
    Append-only session log backed by a JSON file.

    Usage
    -----
    ::
        logger = SessionLogger()
        logger.ensure_started(bot)      # call when bot becomes active
        logger.update(bot)              # call periodically
        logger.record_end(bot_id, reason="stopped")   # on stop
    """

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path     = Path(path)
        self._records: List[SessionRecord] = []
        self._active:  Dict[str, SessionRecord] = {}  # bot_id → open record
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def ensure_started(self, bot) -> None:
        """Open a session for *bot* if one isn't already open."""
        bot_id = getattr(bot, "bot_id", None) or str(id(bot))
        if bot_id in self._active:
            return

        account = getattr(bot, "account", None)
        nick    = (getattr(account, "nickname", None)
                   or getattr(bot, "nickname", bot_id))
        profile = getattr(bot, "profile", "")

        rec = SessionRecord(
            bot_id     = bot_id,
            nickname   = nick,
            started_at = time.time(),
            profile    = profile,
            table      = getattr(bot, "current_table", "") or "",
        )
        self._active[bot_id] = rec
        logger.debug("Session started: %s (%s)", nick, bot_id)

    def update(self, bot) -> None:
        """Refresh live stats (hands, profit, table) for an active session."""
        bot_id = getattr(bot, "bot_id", None) or str(id(bot))
        if bot_id not in self._active:
            return

        rec = self._active[bot_id]
        stats = getattr(bot, "stats", None)
        if stats:
            rec.hands  = getattr(stats, "hands_played", rec.hands)
            rec.profit = getattr(stats, "net_profit",
                          getattr(stats, "total_profit", rec.profit))
            if callable(rec.profit):     # net_profit() method
                try:
                    rec.profit = rec.profit()
                except Exception:
                    rec.profit = 0.0
        rec.table = getattr(bot, "current_table", rec.table) or rec.table

    def record_end(self, bot_id: str, reason: str = "stopped") -> None:
        """Close a session and persist it."""
        if bot_id not in self._active:
            return

        rec = self._active.pop(bot_id)
        rec.ended_at   = time.time()
        rec.end_reason = reason

        self._records.append(rec)
        if len(self._records) > MAX_RECORDS:
            self._records = self._records[-MAX_RECORDS:]

        self._save()
        logger.info(
            "Session ended: %s  %s  hands=%d  profit=%s  duration=%s",
            rec.nickname, reason, rec.hands, rec.profit_str, rec.duration_str,
        )

    def close_all(self, reason: str = "stopped") -> None:
        """Close every open session (call on emergency stop / app close)."""
        for bot_id in list(self._active):
            self.record_end(bot_id, reason)

    def get_history(self, limit: int = 200) -> List[SessionRecord]:
        """Return finished sessions, newest first."""
        return list(reversed(self._records[-limit:]))

    def get_active(self) -> List[SessionRecord]:
        """Return currently open (in-progress) sessions."""
        return list(self._active.values())

    def get_summary(self) -> dict:
        """Return aggregate stats over all finished records."""
        if not self._records:
            return {
                "total_sessions": 0, "total_hands": 0,
                "total_profit": 0.0, "best_session": None,
            }
        total_hands  = sum(r.hands for r in self._records)
        total_profit = sum(r.profit for r in self._records)
        best = max(self._records, key=lambda r: r.profit, default=None)
        return {
            "total_sessions": len(self._records),
            "total_hands":    total_hands,
            "total_profit":   total_profit,
            "best_session":   best,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if self._path.exists():
                with self._path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
                self._records = [SessionRecord.from_dict(d) for d in data]
                logger.debug("Session history loaded: %d records", len(self._records))
        except Exception as exc:
            logger.warning("Could not load session history: %s", exc)
            self._records = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as fh:
                json.dump([r.to_dict() for r in self._records], fh,
                          indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Could not save session history: %s", exc)
