"""
Bot Account Binder — Phase 2 of bot_fixes.md.

Associates bot IDs with poker-room nicknames and window handles.
Uses :class:`AutoWindowFinder` for automatic window discovery and
persists bindings to ``config/bot_bindings.json``.

Features:
  - Bind bot_id ↔ nickname ↔ hwnd (window handle)
  - Auto-bind: detect window by nickname in title
  - Re-bind: update hwnd when window restarts
  - Persist bindings to JSON
  - Health-check: verify window is still alive
  - Bulk operations: bind all known accounts at once

Usage::

    binder = BotAccountBinder()
    binder.bind("bot_1", nickname="sunnuls", room="pokerstars")
    binder.auto_bind("bot_1")  # finds window with "sunnuls" in title
    info = binder.get("bot_1")
    print(info.hwnd, info.title)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports (graceful fallback)
# ---------------------------------------------------------------------------

try:
    from launcher.auto_window_finder import (
        AutoWindowFinder,
        WindowMatch,
        WindowRect,
    )
    FINDER_AVAILABLE = True
except Exception:
    FINDER_AVAILABLE = False
    AutoWindowFinder = None  # type: ignore[misc,assignment]

try:
    import win32gui
    WIN32_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    WIN32_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class BindStatus(str, Enum):
    """Binding health status."""
    BOUND = "bound"          # hwnd is set and window is alive
    STALE = "stale"          # hwnd was set but window is gone
    UNBOUND = "unbound"      # no hwnd yet
    ERROR = "error"          # binding failed


@dataclass
class Binding:
    """One bot → account → window binding.

    Attributes:
        bot_id:       Unique bot identifier.
        nickname:     Poker-room screen name.
        room:         Room slug (pokerstars, 888poker, …).
        hwnd:         Win32 window handle (0 = unbound).
        title:        Window title at time of binding.
        process_name: Process executable (e.g. PokerStars.exe).
        client_rect:  Client-area rectangle (x, y, w, h) — auto-zoom.
        status:       Current binding health.
        bound_at:     Timestamp of last successful bind.
        account_id:   Optional link back to ``Account.account_id``.
    """
    bot_id: str = ""
    nickname: str = ""
    room: str = ""
    hwnd: int = 0
    title: str = ""
    process_name: str = ""
    client_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)
    status: BindStatus = BindStatus.UNBOUND
    bound_at: float = 0.0
    account_id: str = ""

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_id": self.bot_id,
            "nickname": self.nickname,
            "room": self.room,
            "hwnd": self.hwnd,
            "title": self.title,
            "process_name": self.process_name,
            "client_rect": list(self.client_rect),
            "status": self.status.value,
            "bound_at": self.bound_at,
            "account_id": self.account_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Binding:
        cr = data.get("client_rect", [0, 0, 0, 0])
        return cls(
            bot_id=data.get("bot_id", ""),
            nickname=data.get("nickname", ""),
            room=data.get("room", ""),
            hwnd=int(data.get("hwnd", 0)),
            title=data.get("title", ""),
            process_name=data.get("process_name", ""),
            client_rect=tuple(cr) if len(cr) == 4 else (0, 0, 0, 0),
            status=BindStatus(data.get("status", "unbound")),
            bound_at=float(data.get("bound_at", 0.0)),
            account_id=data.get("account_id", ""),
        )

    @property
    def is_bound(self) -> bool:
        return self.hwnd != 0 and self.status == BindStatus.BOUND


# ---------------------------------------------------------------------------
# Binder
# ---------------------------------------------------------------------------

DEFAULT_BINDINGS_PATH = Path("config/bot_bindings.json")


class BotAccountBinder:
    """Manages bot ↔ account ↔ window bindings.

    Persists bindings to a JSON file so they survive restarts.
    Uses :class:`AutoWindowFinder` for discovering windows by nickname.

    Parameters
    ----------
    bindings_path : Path | str
        File path for persisted bindings JSON.
    auto_save : bool
        Automatically save after every mutation (default True).
    """

    def __init__(
        self,
        bindings_path: Path | str = DEFAULT_BINDINGS_PATH,
        auto_save: bool = True,
    ) -> None:
        self._path = Path(bindings_path)
        self._auto_save = auto_save
        self._bindings: Dict[str, Binding] = {}
        self._finder: Optional[AutoWindowFinder] = None

        if FINDER_AVAILABLE:
            self._finder = AutoWindowFinder()

        self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        """Load bindings from disk."""
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw.get("bindings", []):
                b = Binding.from_dict(item)
                if b.bot_id:
                    self._bindings[b.bot_id] = b
            logger.info("Loaded %d bindings from %s", len(self._bindings), self._path)
        except Exception as exc:
            logger.error("Failed to load bindings: %s", exc)

    def save(self) -> None:
        """Persist current bindings to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "bindings": [b.to_dict() for b in self._bindings.values()],
            "count": len(self._bindings),
            "saved_at": time.time(),
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Saved %d bindings to %s", len(self._bindings), self._path)

    def _maybe_save(self) -> None:
        if self._auto_save:
            self.save()

    # -- CRUD ---------------------------------------------------------------

    def bind(
        self,
        bot_id: str,
        *,
        nickname: str = "",
        room: str = "",
        hwnd: int = 0,
        account_id: str = "",
    ) -> Binding:
        """Create or update a binding (manual).

        If *hwnd* is provided, immediately resolves window metadata.
        """
        existing = self._bindings.get(bot_id)
        if existing is None:
            existing = Binding(bot_id=bot_id)

        if nickname:
            existing.nickname = nickname
        if room:
            existing.room = room
        if account_id:
            existing.account_id = account_id

        if hwnd:
            self._resolve_hwnd(existing, hwnd)
        else:
            existing.status = BindStatus.UNBOUND

        self._bindings[bot_id] = existing
        self._maybe_save()
        return existing

    def unbind(self, bot_id: str) -> bool:
        """Remove a binding entirely."""
        if bot_id in self._bindings:
            del self._bindings[bot_id]
            self._maybe_save()
            return True
        return False

    def get(self, bot_id: str) -> Optional[Binding]:
        """Get a binding by bot_id."""
        return self._bindings.get(bot_id)

    def list_all(self) -> List[Binding]:
        """Return all bindings."""
        return list(self._bindings.values())

    def list_bound(self) -> List[Binding]:
        """Return only active (hwnd alive) bindings."""
        return [b for b in self._bindings.values() if b.is_bound]

    def list_unbound(self) -> List[Binding]:
        """Return bindings that need a window."""
        return [
            b for b in self._bindings.values()
            if b.status in (BindStatus.UNBOUND, BindStatus.STALE)
        ]

    # -- auto-bind ----------------------------------------------------------

    def auto_bind(self, bot_id: str) -> Optional[Binding]:
        """Auto-discover window for a known bot by its nickname.

        Searches for a visible window whose title contains the
        binding's *nickname*. Updates hwnd + metadata on success.

        Returns the updated ``Binding`` or ``None`` if not found.
        """
        binding = self._bindings.get(bot_id)
        if binding is None:
            logger.warning("auto_bind: no binding for %s", bot_id)
            return None

        if not binding.nickname:
            logger.warning("auto_bind: bot %s has no nickname", bot_id)
            return None

        if self._finder is None or not self._finder.available:
            logger.warning("auto_bind: AutoWindowFinder not available")
            return None

        match = self._finder.find(binding.nickname)
        if match is None:
            logger.info("auto_bind: no window found for nickname '%s'", binding.nickname)
            binding.status = BindStatus.STALE
            self._maybe_save()
            return None

        self._apply_match(binding, match)
        self._maybe_save()
        logger.info(
            "auto_bind: bot %s → hwnd=%d title=%r",
            bot_id, binding.hwnd, binding.title,
        )
        return binding

    def auto_bind_all(self) -> Dict[str, bool]:
        """Try to auto-bind every unbound/stale binding.

        Returns dict of bot_id → success.
        """
        results: Dict[str, bool] = {}
        for b in self.list_unbound():
            result = self.auto_bind(b.bot_id)
            results[b.bot_id] = result is not None and result.is_bound
        return results

    def bind_from_account(
        self,
        bot_id: str,
        account: Any,
        *,
        auto_find: bool = True,
    ) -> Binding:
        """Bind using an ``Account`` model instance.

        Extracts nickname, room, account_id, and optionally window_info.
        If *auto_find* is True and no hwnd is known, calls :meth:`auto_bind`.
        """
        nickname = getattr(account, "nickname", "")
        room = getattr(account, "room", "")
        account_id = getattr(account, "account_id", "")

        # Try to get hwnd from account's window_info
        hwnd = 0
        wi = getattr(account, "window_info", None)
        if wi is not None:
            hwnd = getattr(wi, "hwnd", 0) or 0
            if hwnd == 0:
                wid = getattr(wi, "window_id", None)
                if wid:
                    try:
                        hwnd = int(wid)
                    except (ValueError, TypeError):
                        pass

        binding = self.bind(
            bot_id,
            nickname=nickname,
            room=room,
            hwnd=hwnd,
            account_id=account_id,
        )

        if not binding.is_bound and auto_find:
            self.auto_bind(bot_id)
            binding = self._bindings[bot_id]

        return binding

    # -- health-check -------------------------------------------------------

    def check_health(self, bot_id: str) -> BindStatus:
        """Verify that the bound window is still alive.

        Returns the updated status.
        """
        binding = self._bindings.get(bot_id)
        if binding is None:
            return BindStatus.UNBOUND

        if binding.hwnd == 0:
            binding.status = BindStatus.UNBOUND
            return BindStatus.UNBOUND

        if not WIN32_AVAILABLE:
            return binding.status

        alive = False
        try:
            alive = bool(win32gui.IsWindow(binding.hwnd))
        except Exception:
            pass

        if alive:
            binding.status = BindStatus.BOUND
        else:
            binding.status = BindStatus.STALE
            logger.warning(
                "Window gone for bot %s (hwnd=%d)", bot_id, binding.hwnd
            )

        self._maybe_save()
        return binding.status

    def check_all_health(self) -> Dict[str, BindStatus]:
        """Health-check every binding."""
        return {b.bot_id: self.check_health(b.bot_id) for b in self.list_all()}

    def rebind_stale(self) -> Dict[str, bool]:
        """Attempt to re-bind all stale bindings via auto-bind."""
        stale = [b for b in self._bindings.values() if b.status == BindStatus.STALE]
        results: Dict[str, bool] = {}
        for b in stale:
            result = self.auto_bind(b.bot_id)
            results[b.bot_id] = result is not None and result.is_bound
        return results

    # -- internal helpers ---------------------------------------------------

    def _resolve_hwnd(self, binding: Binding, hwnd: int) -> None:
        """Fill window metadata from hwnd."""
        binding.hwnd = hwnd

        if not WIN32_AVAILABLE:
            binding.status = BindStatus.BOUND
            binding.bound_at = time.time()
            return

        try:
            if not win32gui.IsWindow(hwnd):
                binding.status = BindStatus.STALE
                return
        except Exception:
            binding.status = BindStatus.ERROR
            return

        try:
            binding.title = win32gui.GetWindowText(hwnd)
        except Exception:
            binding.title = ""

        # Use AutoWindowFinder for client rect
        if self._finder and self._finder.available:
            match = self._finder.find(binding.title or "")
            if match and match.hwnd == hwnd:
                self._apply_match(binding, match)
                return

        binding.status = BindStatus.BOUND
        binding.bound_at = time.time()

    def _apply_match(self, binding: Binding, match: WindowMatch) -> None:
        """Copy fields from WindowMatch to Binding."""
        binding.hwnd = match.hwnd
        binding.title = match.title
        binding.process_name = match.process_name
        binding.client_rect = match.client_rect.as_tuple()
        binding.status = BindStatus.BOUND
        binding.bound_at = time.time()
