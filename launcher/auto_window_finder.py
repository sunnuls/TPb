"""
Auto Window Finder — Phase 1 of bot_fixes.md.

Automatically discovers poker client windows by title pattern, window class,
or process name.  Once a window is found the module computes an *auto-zoom*
rectangle: it trims the non-client border/title-bar so that subsequent
screen captures get only the client area at maximum size.

Features:
  - Multi-strategy search: title substring, regex, window class, process name
  - Ranked results with match-quality scoring
  - Client-area auto-zoom (strip title-bar / border)
  - DPI-aware coordinate computation
  - Window state helpers: restore from minimized, bring to front
  - Polling watcher: waits for a window to appear (e.g. after launching app)

Usage::

    finder = AutoWindowFinder()
    result = finder.find("PokerStars")
    # result.hwnd, result.title, result.client_rect, ...

    # Wait for window to appear (max 30 s)
    result = finder.wait_for("PokerStars", timeout=30)

    # Auto-zoom rectangle (client area only)
    print(result.zoom_rect)  # (x, y, w, h) in screen coordinates

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform imports (graceful fallback)
# ---------------------------------------------------------------------------

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    WIN32_AVAILABLE = False

try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CTYPES_AVAILABLE = False

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class MatchMethod(Enum):
    """How the window was matched."""
    TITLE_EXACT = "title_exact"
    TITLE_SUBSTRING = "title_substring"
    TITLE_REGEX = "title_regex"
    WINDOW_CLASS = "window_class"
    PROCESS_NAME = "process_name"


@dataclass
class WindowRect:
    """Screen rectangle (absolute coordinates)."""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def area(self) -> int:
        return self.w * self.h

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def __repr__(self) -> str:
        return f"WindowRect(x={self.x}, y={self.y}, w={self.w}, h={self.h})"


@dataclass
class WindowMatch:
    """A matched window with metadata and zoom rectangle.

    Attributes:
        hwnd:        Win32 window handle
        title:       Window title text
        window_class: Win32 window class name
        process_name: Process executable name
        process_id:  Process ID
        full_rect:   Full window rectangle (with border / title-bar)
        client_rect: Client area rectangle (content only)
        zoom_rect:   Auto-zoom rectangle (= client_rect in screen coords)
        match_method: How the window was matched
        score:       Match quality 0.0 – 1.0  (higher = better)
        visible:     Whether the window is visible
        minimized:   Whether the window is minimized
        is_child:    Whether it's a child (sub) window
        parent_hwnd: Parent window handle (if child)
        dpi_scale:   DPI scale factor
    """
    hwnd: int = 0
    title: str = ""
    window_class: str = ""
    process_name: str = ""
    process_id: int = 0
    full_rect: WindowRect = field(default_factory=WindowRect)
    client_rect: WindowRect = field(default_factory=WindowRect)
    zoom_rect: WindowRect = field(default_factory=WindowRect)
    match_method: MatchMethod = MatchMethod.TITLE_SUBSTRING
    score: float = 0.0
    visible: bool = True
    minimized: bool = False
    is_child: bool = False
    parent_hwnd: Optional[int] = None
    dpi_scale: float = 1.0


# ---------------------------------------------------------------------------
# Known poker-room patterns
# ---------------------------------------------------------------------------

KNOWN_POKER_TITLES: Dict[str, List[str]] = {
    "pokerstars": ["PokerStars", "Stars "],
    "888poker": ["888poker", "Pacific Poker"],
    "ggpoker": ["GGPoker", "GG Network"],
    "partypoker": ["partypoker", "PartyPoker"],
    "ignition": ["Ignition", "Bovada"],
    "winamax": ["Winamax"],
    "unibet": ["Unibet"],
}

KNOWN_POKER_CLASSES: List[str] = [
    "PokerStarsTableFrameClass",
    "POKER_TABLE",
    "GGPKRClass",
]

KNOWN_POKER_PROCESSES: List[str] = [
    "pokerstars.exe",
    "888poker.exe",
    "ggpoker.exe",
    "partypoker.exe",
    "ignitioncasino.exe",
]

# ---------------------------------------------------------------------------
# Finder
# ---------------------------------------------------------------------------


class AutoWindowFinder:
    """Discovers poker-client windows on the desktop.

    Searches by title pattern (substring / regex), window class, and/or
    process name.  Returns ranked :class:`WindowMatch` results with an
    auto-zoom rectangle that represents the client area without borders.

    Example::

        finder = AutoWindowFinder()

        # Quick search by keyword
        matches = finder.find_all("PokerStars")

        # Exact best match
        best = finder.find("PokerStars")

        # Wait for window (useful after launching the app)
        match = finder.wait_for("PokerStars", timeout=30)

        # Enumerate all known poker rooms
        all_poker = finder.find_all_poker()
    """

    def __init__(self) -> None:
        self._available = WIN32_AVAILABLE

    # -- public helpers -----------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether Win32 window API is usable."""
        return self._available

    # -- core search --------------------------------------------------------

    def find_all(
        self,
        pattern: str = "",
        *,
        by_class: str = "",
        by_process: str = "",
        visible_only: bool = True,
        min_size: Tuple[int, int] = (200, 150),
    ) -> List[WindowMatch]:
        """Find all windows matching *any* of the supplied criteria.

        Parameters
        ----------
        pattern : str
            Title text — tries exact, substring, then regex.
        by_class : str
            Win32 window class name (substring match).
        by_process : str
            Process executable name (case-insensitive substring).
        visible_only : bool
            Skip invisible windows (default True).
        min_size : (int, int)
            Minimum (width, height) to consider.

        Returns
        -------
        List[WindowMatch]
            Matches sorted by *score* descending.
        """
        if not self._available:
            logger.warning("Win32 API not available — cannot enumerate windows")
            return []

        raw: List[WindowMatch] = []

        def _callback(hwnd: int, _: Any) -> bool:  # noqa: ANN401
            try:
                match = self._evaluate_window(
                    hwnd,
                    pattern=pattern,
                    by_class=by_class,
                    by_process=by_process,
                    visible_only=visible_only,
                    min_size=min_size,
                )
                if match is not None:
                    raw.append(match)
            except Exception:
                pass  # skip problematic windows
            return True  # continue enumeration

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception as exc:
            logger.error("EnumWindows failed: %s", exc)

        raw.sort(key=lambda m: m.score, reverse=True)
        return raw

    def find(
        self,
        pattern: str = "",
        **kwargs: Any,
    ) -> Optional[WindowMatch]:
        """Return the single best match, or ``None``."""
        results = self.find_all(pattern, **kwargs)
        return results[0] if results else None

    def find_all_poker(self, visible_only: bool = True) -> List[WindowMatch]:
        """Search for all known poker-room windows."""
        combined: Dict[int, WindowMatch] = {}

        for _room, titles in KNOWN_POKER_TITLES.items():
            for t in titles:
                for m in self.find_all(t, visible_only=visible_only):
                    if m.hwnd not in combined or m.score > combined[m.hwnd].score:
                        combined[m.hwnd] = m

        for cls in KNOWN_POKER_CLASSES:
            for m in self.find_all("", by_class=cls, visible_only=visible_only):
                if m.hwnd not in combined or m.score > combined[m.hwnd].score:
                    combined[m.hwnd] = m

        for proc in KNOWN_POKER_PROCESSES:
            for m in self.find_all("", by_process=proc, visible_only=visible_only):
                if m.hwnd not in combined or m.score > combined[m.hwnd].score:
                    combined[m.hwnd] = m

        matches = sorted(combined.values(), key=lambda m: m.score, reverse=True)
        return matches

    def wait_for(
        self,
        pattern: str,
        *,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
        **kwargs: Any,
    ) -> Optional[WindowMatch]:
        """Block until a matching window appears or *timeout* expires.

        Returns the first match or ``None`` on timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.find(pattern, **kwargs)
            if result is not None:
                return result
            time.sleep(poll_interval)
        logger.warning("wait_for(%r) timed out after %.1fs", pattern, timeout)
        return None

    # -- window state helpers -----------------------------------------------

    @staticmethod
    def restore_window(hwnd: int) -> bool:
        """Restore a minimized window."""
        if not WIN32_AVAILABLE:
            return False
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception as exc:
            logger.error("restore_window failed: %s", exc)
            return False

    @staticmethod
    def bring_to_front(hwnd: int) -> bool:
        """Bring window to the foreground."""
        if not WIN32_AVAILABLE:
            return False
        try:
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as exc:
            logger.error("bring_to_front failed: %s", exc)
            return False

    @staticmethod
    def set_window_position(
        hwnd: int, x: int, y: int, w: int, h: int
    ) -> bool:
        """Move / resize the window."""
        if not WIN32_AVAILABLE:
            return False
        try:
            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            return True
        except Exception as exc:
            logger.error("set_window_position failed: %s", exc)
            return False

    # -- internal -----------------------------------------------------------

    def _evaluate_window(
        self,
        hwnd: int,
        pattern: str,
        by_class: str,
        by_process: str,
        visible_only: bool,
        min_size: Tuple[int, int],
    ) -> Optional[WindowMatch]:
        """Score a window against the given criteria."""
        # visibility filter
        if visible_only and not win32gui.IsWindowVisible(hwnd):
            return None

        title = win32gui.GetWindowText(hwnd) or ""
        if not title.strip() and not by_class and not by_process:
            return None

        # window class
        try:
            wclass = win32gui.GetClassName(hwnd)
        except Exception:
            wclass = ""

        # process
        pname = ""
        pid = 0
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                import psutil
                pname = psutil.Process(pid).name()
            except Exception:
                pname = ""
        except Exception:
            pass

        # ---- scoring --------------------------------------------------------
        score = 0.0
        method = MatchMethod.TITLE_SUBSTRING

        if pattern:
            low_title = title.lower()
            low_pat = pattern.lower()

            if title == pattern:
                score = max(score, 1.0)
                method = MatchMethod.TITLE_EXACT
            elif low_pat in low_title:
                score = max(score, 0.8)
                method = MatchMethod.TITLE_SUBSTRING
            else:
                try:
                    if re.search(pattern, title, re.IGNORECASE):
                        score = max(score, 0.6)
                        method = MatchMethod.TITLE_REGEX
                except re.error:
                    pass  # invalid regex — skip

        if by_class and by_class.lower() in wclass.lower():
            s = 0.9 if by_class.lower() == wclass.lower() else 0.7
            if s > score:
                score = s
                method = MatchMethod.WINDOW_CLASS

        if by_process and pname and by_process.lower() in pname.lower():
            s = 0.85
            if s > score:
                score = s
                method = MatchMethod.PROCESS_NAME

        if score == 0.0:
            return None

        # ---- geometry -------------------------------------------------------
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        except Exception:
            return None

        fw = right - left
        fh = bottom - top
        if fw < min_size[0] or fh < min_size[1]:
            return None

        full_rect = WindowRect(x=left, y=top, w=fw, h=fh)

        # client area in screen coordinates
        client_rect = self._get_client_screen_rect(hwnd, full_rect)

        minimized = bool(win32gui.IsIconic(hwnd))
        is_child = win32gui.GetParent(hwnd) != 0
        parent = win32gui.GetParent(hwnd) or None

        dpi = self._get_dpi_scale(hwnd)

        return WindowMatch(
            hwnd=hwnd,
            title=title,
            window_class=wclass,
            process_name=pname,
            process_id=pid,
            full_rect=full_rect,
            client_rect=client_rect,
            zoom_rect=client_rect,  # auto-zoom = client area
            match_method=method,
            score=score,
            visible=True,
            minimized=minimized,
            is_child=is_child,
            parent_hwnd=parent,
            dpi_scale=dpi,
        )

    # -- client-area helpers ------------------------------------------------

    @staticmethod
    def _get_client_screen_rect(hwnd: int, full: WindowRect) -> WindowRect:
        """Compute the client-area rectangle in screen coordinates.

        Uses ``ClientToScreen`` + ``GetClientRect`` when available so that
        the title-bar / border is automatically excluded — this is the
        "auto-zoom" feature.
        """
        try:
            # GetClientRect returns (0, 0, cw, ch) — client area size
            cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
            cw = cr - cl
            ch = cb - ct

            # ClientToScreen maps (0,0) of client area to screen coordinates
            sx, sy = win32gui.ClientToScreen(hwnd, (0, 0))

            return WindowRect(x=sx, y=sy, w=cw, h=ch)
        except Exception:
            # Fallback: estimate border by heuristic
            border_x = 8
            border_y = 31  # typical title-bar height
            return WindowRect(
                x=full.x + border_x,
                y=full.y + border_y,
                w=max(1, full.w - 2 * border_x),
                h=max(1, full.h - border_y - border_x),
            )

    @staticmethod
    def _get_dpi_scale(hwnd: int) -> float:
        """Get per-monitor DPI scale factor for the given window."""
        if not CTYPES_AVAILABLE:
            return 1.0
        try:
            # GetDpiForWindow requires Windows 10 1607+
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            return dpi / 96.0 if dpi > 0 else 1.0
        except Exception:
            return 1.0
