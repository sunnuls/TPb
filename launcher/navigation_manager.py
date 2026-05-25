"""
Navigation Manager — Phase 4 of bot_fixes.md.

High-level navigation from lobby to table, combining:
  - Window discovery (``AutoWindowFinder``)
  - Screen capture (``ScreenCapture`` / ``WindowCapturer``)
  - OCR text recognition (``pytesseract``)
  - Mouse / keyboard actions (``pyautogui``)

Navigation pipeline::

    1. Detect current screen (lobby / table / unknown)
    2. If lobby → find matching table → click "Join"
    3. If table → already seated, return success
    4. If unknown → scroll / switch tabs to find lobby

Features:
  - Screen-type detection via OCR keywords
  - Table list scanning: reads table names, stakes, player counts
  - Scrolling through lobby pages
  - Click-to-join with confirmation detection
  - Retry / timeout / error handling
  - Dry-run mode (no real clicks)

Usage::

    nav = NavigationManager(hwnd=12345)
    result = nav.navigate_to_table(
        stakes="NL50",
        min_players=3,
        max_players=6,
    )
    print(result.status)  # NavStatus.SEATED

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies (graceful fallback)
# ---------------------------------------------------------------------------

try:
    import cv2
    CV2_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TESSERACT_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False   # Disable corner-abort to prevent FailSafeException
    pyautogui.PAUSE = 0.15
    AUTOGUI_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SyntaxError):
    AUTOGUI_AVAILABLE = False

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    WIN32_AVAILABLE = False

try:
    from launcher.auto_window_finder import AutoWindowFinder
    FINDER_AVAILABLE = True
except Exception:
    FINDER_AVAILABLE = False

try:
    from launcher.vision.window_capturer import WindowCapturer
    CAPTURER_AVAILABLE = True
except Exception:
    CAPTURER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ScreenType(Enum):
    """Detected screen / UI state."""
    LOBBY = "lobby"
    TABLE = "table"
    LOGIN = "login"
    POPUP = "popup"
    UNKNOWN = "unknown"


class NavStatus(Enum):
    """Navigation result status."""
    SEATED = "seated"           # successfully sitting at a table
    TABLE_FOUND = "table_found" # table found but not yet joined
    LOBBY = "lobby"             # still in lobby (no match)
    SCROLLED = "scrolled"       # scrolled for more tables
    TIMEOUT = "timeout"
    ERROR = "error"
    DRY_RUN = "dry_run"


@dataclass
class TableEntry:
    """A table row parsed from the lobby list.

    Attributes:
        name:       Table name / ID.
        stakes:     Stakes string (e.g. "NL50", "$0.25/$0.50").
        players:    Current players seated.
        max_players: Maximum seats.
        game_type:  Game type string (Hold'em, Omaha, …).
        bbox:       Bounding box of the row in the screenshot (y1, y2).
        raw_text:   Raw OCR text for debugging.
    """
    name: str = ""
    stakes: str = ""
    players: int = 0
    max_players: int = 0
    game_type: str = ""
    bbox: Tuple[int, int] = (0, 0)
    raw_text: str = ""


@dataclass
class NavResult:
    """Result of a navigation attempt.

    Attributes:
        status:      Outcome status.
        screen_type: Detected screen at the end.
        table:       The table that was joined (if any).
        message:     Human-readable description.
        elapsed:     Time spent (seconds).
        attempts:    Number of attempts / scrolls made.
    """
    status: NavStatus = NavStatus.ERROR
    screen_type: ScreenType = ScreenType.UNKNOWN
    table: Optional[TableEntry] = None
    message: str = ""
    elapsed: float = 0.0
    attempts: int = 0


# ---------------------------------------------------------------------------
# Keyword dictionaries for screen detection
# ---------------------------------------------------------------------------

LOBBY_KEYWORDS = [
    "lobby", "лобби", "cash game", "кэш", "tournament", "турнир",
    "ring game", "sit & go", "sit and go", "spin", "buy-in",
    "stakes", "ставки", "players", "игроки", "tables", "столы",
    "join", "присоединиться", "open", "открыть",
]

TABLE_KEYWORDS = [
    "fold", "call", "raise", "check", "all-in", "allin",
    "фолд", "колл", "рейз", "чек", "олл-ин",
    "pot", "банк", "dealer", "дилер", "seat",
]

LOGIN_KEYWORDS = [
    "login", "log in", "sign in", "password", "пароль",
    "username", "email", "войти", "вход",
]

POPUP_KEYWORDS = [
    "ok", "cancel", "отмена", "close", "закрыть",
    "accept", "принять", "agree", "confirm",
]


# ---------------------------------------------------------------------------
# Navigation Manager
# ---------------------------------------------------------------------------


class NavigationManager:
    """Orchestrates navigation from lobby to a poker table.

    Parameters
    ----------
    hwnd : int | None
        Window handle of the poker client.
    dry_run : bool
        If True, never performs real clicks or keyboard input.
    capture_fn : callable | None
        Custom capture function ``(hwnd) → np.ndarray``.
        If ``None``, uses ``WindowCapturer``.
    click_fn : callable | None
        Custom click function ``(x, y) → None``.
        If ``None``, uses ``pyautogui.click``.
    """

    def __init__(
        self,
        hwnd: Optional[int] = None,
        dry_run: bool = False,
        capture_fn: Optional[Callable] = None,
        click_fn: Optional[Callable] = None,
    ) -> None:
        self.hwnd = hwnd
        self.dry_run = dry_run

        self._capture_fn = capture_fn
        self._click_fn = click_fn

        self._capturer: Optional[Any] = None
        if CAPTURER_AVAILABLE and not capture_fn:
            self._capturer = WindowCapturer()

        # Stop flag — set by bot.stop() or mode switch to abort in-flight navigation
        self._stop_requested: bool = False
        # Balance observed from the buy-in dialog (updated on each attempt)
        self.last_observed_balance: float = 0.0

    def request_stop(self) -> None:
        """Signal that all in-flight navigation should abort immediately."""
        self._stop_requested = True

    def reset_stop(self) -> None:
        """Clear the stop flag so navigation can proceed again."""
        self._stop_requested = False

    def _check_stop(self) -> bool:
        """Return True if navigation has been aborted."""
        return self._stop_requested

    # ------------------------------------------------------------------
    # Screen capture
    # ------------------------------------------------------------------

    def capture(self) -> Optional[np.ndarray]:
        """Capture the current window screenshot (BGR numpy array)."""
        if self._capture_fn:
            return self._capture_fn(self.hwnd)

        if self._capturer and self._capturer.available and self.hwnd:
            return self._capturer.capture_window_by_hwnd(self.hwnd, include_border=False)

        return None

    # ------------------------------------------------------------------
    # OCR helpers
    # ------------------------------------------------------------------

    @staticmethod
    def ocr_full(image: np.ndarray) -> str:
        """Run OCR on the full image and return lowercased text."""
        if not TESSERACT_AVAILABLE or not CV2_AVAILABLE:
            return ""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config="--psm 6")
            return text.lower()
        except Exception as exc:
            logger.debug("ocr_full error: %s", exc)
            return ""

    @staticmethod
    def ocr_region(
        image: np.ndarray,
        x: int, y: int, w: int, h: int,
    ) -> str:
        """OCR a sub-region of the image."""
        if not TESSERACT_AVAILABLE or not CV2_AVAILABLE:
            return ""
        try:
            region = image[y:y + h, x:x + w]
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config="--psm 7")
            return text.strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Screen detection
    # ------------------------------------------------------------------

    def detect_screen(self, image: Optional[np.ndarray] = None) -> ScreenType:
        """Determine what screen is currently displayed.

        Captures a screenshot (if not provided), runs OCR, and matches
        keywords to decide: lobby / table / login / popup / unknown.
        """
        if image is None:
            image = self.capture()
        if image is None:
            return ScreenType.UNKNOWN

        text = self.ocr_full(image)
        if not text:
            return ScreenType.UNKNOWN

        scores: Dict[ScreenType, int] = {
            ScreenType.LOBBY: 0,
            ScreenType.TABLE: 0,
            ScreenType.LOGIN: 0,
            ScreenType.POPUP: 0,
        }

        for kw in LOBBY_KEYWORDS:
            if kw in text:
                scores[ScreenType.LOBBY] += 1
        for kw in TABLE_KEYWORDS:
            if kw in text:
                scores[ScreenType.TABLE] += 1
        for kw in LOGIN_KEYWORDS:
            if kw in text:
                scores[ScreenType.LOGIN] += 1
        for kw in POPUP_KEYWORDS:
            if kw in text:
                scores[ScreenType.POPUP] += 1

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] == 0:
            return ScreenType.UNKNOWN
        return best

    # ------------------------------------------------------------------
    # Table list scanning
    # ------------------------------------------------------------------

    def scan_lobby_tables(
        self,
        image: Optional[np.ndarray] = None,
    ) -> List[TableEntry]:
        """Parse the lobby table list from a screenshot.

        Uses horizontal projection to find text rows, then OCR on each row
        to extract table info.
        """
        if image is None:
            image = self.capture()
        if image is None:
            return []
        if not CV2_AVAILABLE or not TESSERACT_AVAILABLE:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Horizontal projection — find rows of text
        row_proj = np.mean(gray, axis=1)
        # Rows with lots of content have lower mean (dark text on light bg)
        # or higher mean (light text on dark bg). Use a threshold.
        median_val = np.median(row_proj)

        rows: List[Tuple[int, int]] = []
        in_row = False
        row_start = 0
        min_row_h = 15
        max_row_h = 80

        for y_idx in range(h):
            is_content = abs(row_proj[y_idx] - median_val) > 15
            if is_content and not in_row:
                row_start = y_idx
                in_row = True
            elif not is_content and in_row:
                rh = y_idx - row_start
                if min_row_h <= rh <= max_row_h:
                    rows.append((row_start, y_idx))
                in_row = False

        # Close last row
        if in_row:
            rh = h - row_start
            if min_row_h <= rh <= max_row_h:
                rows.append((row_start, h))

        # OCR each row
        tables: List[TableEntry] = []
        for y1, y2 in rows:
            region = image[y1:y2, 0:w]
            try:
                row_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(row_gray, config="--psm 7").strip()
            except Exception:
                text = ""

            if not text or len(text) < 3:
                continue

            entry = self._parse_table_row(text, y1, y2)
            if entry is not None:
                tables.append(entry)

        logger.info("scan_lobby_tables: found %d rows, parsed %d tables",
                     len(rows), len(tables))
        return tables

    @staticmethod
    def _parse_table_row(text: str, y1: int, y2: int) -> Optional[TableEntry]:
        """Parse a single OCR row into a TableEntry.

        Heuristic parsing — tries to extract stakes, player count.
        """
        entry = TableEntry(raw_text=text, bbox=(y1, y2))

        # Try to find stakes pattern: NL50, $0.25/$0.50, 100/200, etc.
        stakes_match = re.search(
            r'(NL|PL|FL)?\s*\$?[\d]+[/.][\d]+\s*/?\s*\$?[\d]*[.]?[\d]*',
            text, re.IGNORECASE,
        )
        if stakes_match:
            entry.stakes = stakes_match.group().strip()

        # Try to find player count: "3/6", "5 / 9", "2/6"
        players_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
        if players_match:
            try:
                entry.players = int(players_match.group(1))
                entry.max_players = int(players_match.group(2))
            except ValueError:
                pass

        # Table name: take the first word(s) before numbers
        name_match = re.match(r'^([A-Za-zА-Яа-я\s\-]+)', text)
        if name_match:
            entry.name = name_match.group(1).strip()

        # Game type detection
        text_low = text.lower()
        for gtype in ["hold'em", "холдем", "omaha", "омаха", "plo", "stud"]:
            if gtype in text_low:
                entry.game_type = gtype
                break

        # Only return if we found something useful
        if entry.stakes or entry.players > 0 or entry.name:
            return entry
        return None

    # ------------------------------------------------------------------
    # Table matching
    # ------------------------------------------------------------------

    @staticmethod
    def match_table(
        tables: List[TableEntry],
        stakes: str = "",
        min_players: int = 0,
        max_players: int = 99,
        game_type: str = "",
    ) -> Optional[TableEntry]:
        """Find the first table matching the given criteria.

        Args:
            tables:      List of parsed table entries.
            stakes:      Stakes filter (substring match, case-insensitive).
            min_players: Minimum current players.
            max_players: Maximum current players (to avoid full tables).
            game_type:   Game type filter (substring).

        Returns:
            Best matching ``TableEntry`` or ``None``.
        """
        for t in tables:
            if stakes and stakes.lower() not in t.stakes.lower():
                continue
            if t.players < min_players:
                continue
            if t.players > max_players:
                continue
            if game_type and game_type.lower() not in t.game_type.lower():
                continue
            return t
        return None

    # ------------------------------------------------------------------
    # Click / scroll actions
    # ------------------------------------------------------------------

    def click_at(self, x: int, y: int) -> bool:
        """Click at screen coordinates (or log in dry-run)."""
        if self.dry_run:
            logger.info("[DRY-RUN] click at (%d, %d)", x, y)
            return True

        if not AUTOGUI_AVAILABLE:
            logger.warning("pyautogui not available — cannot click")
            return False

        try:
            pyautogui.click(x, y)
            return True
        except Exception as exc:
            logger.error("click_at failed: %s", exc)
            return False

    def click_table_row(
        self,
        table: TableEntry,
        image_offset: Tuple[int, int] = (0, 0),
    ) -> bool:
        """Click the center of a table row in the lobby.

        Args:
            table:        The ``TableEntry`` to click.
            image_offset: (x, y) offset of the captured image in screen coords.
                          Typically the client-area origin.

        Returns:
            True if click was sent.
        """
        y_center = (table.bbox[0] + table.bbox[1]) // 2
        # Click in the middle of the row horizontally
        x_center = 400  # approximate center of lobby list

        abs_x = image_offset[0] + x_center
        abs_y = image_offset[1] + y_center

        logger.info("Clicking table '%s' at (%d, %d)", table.name, abs_x, abs_y)
        return self.click_at(abs_x, abs_y)

    def scroll_lobby(self, direction: str = "down", amount: int = 3) -> bool:
        """Scroll the lobby list.

        Args:
            direction: "down" or "up".
            amount:    Number of scroll steps.

        Returns:
            True if scroll was performed.
        """
        if self.dry_run:
            logger.info("[DRY-RUN] scroll %s x%d", direction, amount)
            return True

        if not AUTOGUI_AVAILABLE:
            logger.warning("pyautogui not available — cannot scroll")
            return False

        try:
            clicks = amount if direction == "up" else -amount
            pyautogui.scroll(clicks)
            return True
        except Exception as exc:
            logger.error("scroll_lobby failed: %s", exc)
            return False

    def click_join_button(self, image: Optional[np.ndarray] = None) -> bool:
        """Find and click a "Join" / "Open" / "Sit" button.

        Scans the screenshot for join-related text and clicks its center.
        """
        if image is None:
            image = self.capture()
        if image is None:
            return False
        if not CV2_AVAILABLE or not TESSERACT_AVAILABLE:
            return False

        try:
            # OCR with bounding boxes
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        except Exception:
            return False

        join_words = {"join", "open", "sit", "play", "присоединиться", "играть", "сесть"}

        for i, word in enumerate(data.get("text", [])):
            if word.lower().strip() in join_words:
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                logger.info("Found join button '%s' at (%d, %d)", word, x, y)
                return self.click_at(x, y)

        logger.info("No join button found")
        return False

    # ------------------------------------------------------------------
    # High-level: lobby → table pipeline
    # ------------------------------------------------------------------

    def navigate_to_table(
        self,
        stakes: str = "",
        min_players: int = 1,
        max_players: int = 9,
        game_type: str = "",
        timeout: float = 60.0,
        max_scrolls: int = 10,
        scroll_delay: float = 1.5,
    ) -> NavResult:
        """Full navigation pipeline: lobby → find table → join.

        Steps:
          1. Detect current screen
          2. If already at table → return SEATED
          3. If lobby → scan tables → match → click → confirm
          4. If no match → scroll and retry
          5. Repeat until timeout

        Args:
            stakes:       Stakes filter (e.g. "NL50").
            min_players:  Min players for selection.
            max_players:  Max players (avoid full).
            game_type:    Game type filter.
            timeout:      Max time in seconds.
            max_scrolls:  Max scroll attempts.
            scroll_delay: Seconds to wait after each scroll.

        Returns:
            NavResult with status, table info, timing.
        """
        t0 = time.monotonic()
        attempts = 0

        if self.dry_run:
            return NavResult(
                status=NavStatus.DRY_RUN,
                screen_type=ScreenType.UNKNOWN,
                message="Dry-run mode — no real navigation",
                elapsed=0.0,
            )

        for scroll_i in range(max_scrolls + 1):
            elapsed = time.monotonic() - t0
            if elapsed > timeout:
                return NavResult(
                    status=NavStatus.TIMEOUT,
                    message=f"Timeout after {elapsed:.1f}s",
                    elapsed=elapsed,
                    attempts=attempts,
                )

            attempts += 1

            # 1. Capture
            image = self.capture()
            if image is None:
                time.sleep(1.0)
                continue

            # 2. Detect screen
            screen = self.detect_screen(image)

            if screen == ScreenType.TABLE:
                return NavResult(
                    status=NavStatus.SEATED,
                    screen_type=ScreenType.TABLE,
                    message="Already at a table",
                    elapsed=time.monotonic() - t0,
                    attempts=attempts,
                )

            if screen == ScreenType.POPUP:
                # Try to close popup
                self.click_join_button(image)
                time.sleep(1.0)
                continue

            # 3. Scan lobby tables
            tables = self.scan_lobby_tables(image)

            # 4. Match
            match = self.match_table(
                tables,
                stakes=stakes,
                min_players=min_players,
                max_players=max_players,
                game_type=game_type,
            )

            if match is not None:
                # Click the table row
                self.click_table_row(match)
                time.sleep(1.0)

                # Try to click join button
                image2 = self.capture()
                if image2 is not None:
                    self.click_join_button(image2)

                time.sleep(2.0)

                # Verify we're at the table
                image3 = self.capture()
                new_screen = self.detect_screen(image3)

                if new_screen == ScreenType.TABLE:
                    return NavResult(
                        status=NavStatus.SEATED,
                        screen_type=ScreenType.TABLE,
                        table=match,
                        message=f"Seated at '{match.name}' ({match.stakes})",
                        elapsed=time.monotonic() - t0,
                        attempts=attempts,
                    )
                else:
                    return NavResult(
                        status=NavStatus.TABLE_FOUND,
                        screen_type=new_screen,
                        table=match,
                        message=f"Table found but join unconfirmed",
                        elapsed=time.monotonic() - t0,
                        attempts=attempts,
                    )

            # 5. No match → scroll
            if scroll_i < max_scrolls:
                logger.info("No matching table found, scrolling down…")
                self.scroll_lobby(direction="down", amount=3)
                time.sleep(scroll_delay)

        return NavResult(
            status=NavStatus.LOBBY,
            screen_type=ScreenType.LOBBY,
            message=f"No matching table after {max_scrolls} scrolls",
            elapsed=time.monotonic() - t0,
            attempts=attempts,
        )

    # ── High-level entry for bot_instance (Phase 3) ──────────────────────────

    async def join_table(self, table, hwnd: int) -> NavResult:
        """Click on a LobbyTable row and then press LET'S PLAY / JOIN.

        Lobby navigation clicks are performed regardless of dry_run setting.
        Only actual game actions (fold/call/raise) require LIVE mode.

        Args:
            table:  A ``LobbyTable`` dataclass (from lobby_scanner).
            hwnd:   CoinPoker window HWND.

        Returns:
            NavResult with SEATED / TABLE_FOUND / DRY_RUN / ERROR.
        """
        import asyncio

        t0 = time.monotonic()
        table_name = getattr(table, "table_name", "?")
        stakes     = getattr(table, "stakes", "?")
        row_y      = getattr(table, "row_y_coordinate", 0)

        try:
            # 1. Get absolute window position on screen
            win_x, win_y, win_w, win_h = 0, 0, 800, 600
            if WIN32_AVAILABLE and hwnd:
                try:
                    rect   = win32gui.GetWindowRect(hwnd)
                    win_x  = rect[0]
                    win_y  = rect[1]
                    win_w  = rect[2] - rect[0]
                    win_h  = rect[3] - rect[1]
                    logger.debug(
                        "join_table: hwnd=%d rect=(%d,%d) %dx%d",
                        hwnd, win_x, win_y, win_w, win_h,
                    )
                except Exception as e:
                    logger.warning("GetWindowRect failed for hwnd=%d: %s", hwnd, e)

            logger.info(
                "join_table: window at (%d,%d) size %dx%d, row_y=%d, table='%s' %s",
                win_x, win_y, win_w, win_h, row_y, table_name, stakes,
            )

            # ── Move off-screen window back onto the primary display ──────────
            if WIN32_AVAILABLE and hwnd and (win_x < -1000 or win_y < -1000 or win_x > 8000 or win_y > 8000):
                try:
                    # NOTE: do NOT re-import win32gui here — it would shadow the
                    # module-level import and cause UnboundLocalError earlier in
                    # the function (Python treats any local import as local throughout).
                    logger.info("Window is off-screen (%d,%d) — moving to (0,0)", win_x, win_y)
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 50, 50, win_w, win_h,
                                         win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                    time.sleep(0.4)
                    rect = win32gui.GetWindowRect(hwnd)
                    win_x, win_y = rect[0], rect[1]
                    win_w = rect[2] - rect[0]
                    win_h = rect[3] - rect[1]
                    logger.info("Window moved to (%d,%d)", win_x, win_y)
                except Exception as _mv_exc:
                    logger.warning("Could not move off-screen window: %s", _mv_exc)

            if not AUTOGUI_AVAILABLE:
                logger.warning("pyautogui not available — cannot click")
                return NavResult(
                    status=NavStatus.ERROR,
                    message="pyautogui not installed",
                    elapsed=time.monotonic() - t0,
                )

            if row_y == 0:
                logger.warning("row_y=0 — cannot locate table row to click")
                return NavResult(
                    status=NavStatus.ERROR,
                    message="row_y=0: table row position unknown",
                    elapsed=time.monotonic() - t0,
                )

            # Safety: row_y must be in the lower 55% of the window
            # (top 45% is navigation/tabs — clicking there opens Casino/Sports/etc.)
            if win_h > 0 and row_y < int(win_h * 0.45):
                logger.warning(
                    "row_y=%d is in top 45%% of window (h=%d) — likely nav bar, skipping",
                    row_y, win_h,
                )
                return NavResult(
                    status=NavStatus.ERROR,
                    message=f"row_y={row_y} is in navigation area (< 45% of window height)",
                    elapsed=time.monotonic() - t0,
                )

            # 2. Bring PS window to foreground, then click the table row.
            # The table list occupies the LEFT ~35% of the lobby window.
            # The right ~50% is the info/action panel ("Играть", "Наблюдать").
            # Using win_w // 4 (~25%) keeps the click firmly in the list columns.
            click_x = win_x + win_w // 4
            click_y = win_y + row_y
            logger.info("Clicking table row at screen (%d, %d)", click_x, click_y)

            # Safety: reject obviously wrong coordinates
            # (window at 0,0 with default size means HWND was invalid)
            if win_x == 0 and win_y == 0 and win_w <= 800 and win_h <= 600:
                logger.error(
                    "join_table: window coords look like defaults (0,0,%dx%d) — "
                    "HWND is likely wrong, aborting to prevent clicking wrong app",
                    win_w, win_h,
                )
                return NavResult(
                    status=NavStatus.ERROR,
                    message="invalid window coords — bad HWND",
                    elapsed=time.monotonic() - t0,
                )

            # Abort immediately if stop was requested
            if self._check_stop():
                logger.info("join_table: aborted before row click (stop requested)")
                return NavResult(status=NavStatus.ERROR, message="aborted", elapsed=time.monotonic() - t0)

            # Focus the window first — unfocused clicks only focus, don't register
            self._focus_window(hwnd)
            await asyncio.sleep(0.4)  # give PS time to come to front

            # Suppress MouseGuard for the entire join sequence
            try:
                from launcher.mouse_guard import MouseGuard
                MouseGuard.get_global().suppress(8.0)
            except Exception:
                pass

            pyautogui.moveTo(click_x, click_y, duration=0.3)
            await asyncio.sleep(0.3)
            # Use win32-level click for reliability (works even when not fully focused)
            self._win32_click(click_x, click_y)
            await asyncio.sleep(0.3)
            pyautogui.click(click_x, click_y)  # second click confirms selection
            await asyncio.sleep(1.2)

            # 3. Click "Играть" / "Play" button on the right panel
            #    For PS, after selecting a row the right panel shows "Играть" button
            room = getattr(table, "room", "unknown")
            lets_play_x = getattr(table, "lets_play_btn_x", 0)
            ocr_clicked = False

            if self._check_stop():
                logger.info("join_table: aborted before Играть click (stop requested)")
                return NavResult(status=NavStatus.ERROR, message="aborted", elapsed=time.monotonic() - t0)

            await asyncio.sleep(0.5)
            image = self.capture()
            if image is not None:
                ocr_clicked = self._click_lets_play(image, win_x, win_y)

            if not ocr_clicked and lets_play_x > 0:
                if self._check_stop():
                    logger.info("join_table: aborted before direct Играть click (stop requested)")
                    return NavResult(status=NavStatus.ERROR, message="aborted", elapsed=time.monotonic() - t0)
                btn_screen_x = win_x + lets_play_x
                btn_screen_y = win_y + row_y
                logger.info("'Играть' via direct coord (%d, %d)", btn_screen_x, btn_screen_y)
                pyautogui.moveTo(btn_screen_x, btn_screen_y, duration=0.2)
                await asyncio.sleep(0.2)
                self._win32_click(btn_screen_x, btn_screen_y)
                await asyncio.sleep(0.15)
                pyautogui.click(btn_screen_x, btn_screen_y)
                ocr_clicked = True

            if not ocr_clicked:
                if self._check_stop():
                    logger.info("join_table: aborted before double-click (stop requested)")
                    return NavResult(status=NavStatus.ERROR, message="aborted", elapsed=time.monotonic() - t0)
                # Last resort: double-click the row
                logger.info("Double-clicking row to trigger join…")
                pyautogui.doubleClick(click_x, click_y)
                await asyncio.sleep(1.0)
                image2 = self.capture()
                if image2 is not None:
                    self._click_lets_play(image2, win_x, win_y)

            # ── PokerStars: handle buy-in dialog after "Играть" click ─────────
            if room == "pokerstars":
                if self._check_stop():
                    logger.info("join_table: aborted before buy-in dialog (stop requested)")
                    return NavResult(status=NavStatus.ERROR, message="aborted", elapsed=time.monotonic() - t0)
                await asyncio.sleep(1.5)
                buyin_handled = await self.handle_buyin_dialog(hwnd, strategy="max")
                logger.info("PS buy-in dialog handled=%s", buyin_handled)
                await asyncio.sleep(2.0)

            await asyncio.sleep(1.5)
            image_final = self.capture()
            if image_final is not None and self.detect_screen(image_final) == ScreenType.TABLE:
                logger.info("Seated at table '%s'", table_name)
                return NavResult(
                    status=NavStatus.SEATED,
                    screen_type=ScreenType.TABLE,
                    message=f"Seated at '{table_name}'",
                    elapsed=time.monotonic() - t0,
                )

            return NavResult(
                status=NavStatus.TABLE_FOUND,
                message=f"Join attempted for '{table_name}'",
                elapsed=time.monotonic() - t0,
            )

        except Exception as exc:
            # pyautogui.FailSafeException (mouse moved to corner) — log and recover
            if "FailSafe" in type(exc).__name__ or "failsafe" in str(exc).lower():
                logger.warning("join_table: pyautogui FailSafe triggered — recovering")
                return NavResult(status=NavStatus.ERROR, message="FailSafe triggered",
                                 elapsed=time.monotonic() - t0)
            logger.error("join_table error: %s", exc, exc_info=True)
            return NavResult(status=NavStatus.ERROR, message=str(exc),
                             elapsed=time.monotonic() - t0)

    def _click_lets_play(self, image: "np.ndarray", win_x: int, win_y: int) -> bool:
        """Find and click the LET'S PLAY / Играть / JOIN button in the lobby.

        NOTE: "SEAT" is intentionally excluded — it matches the lobby's
        'Seats' filter tab and causes false-positive clicks there.
        Only buttons in the lower 55% of the window are considered to avoid
        navigation tabs at the top.
        """
        if not TESSERACT_AVAILABLE or not CV2_AVAILABLE:
            return False
        try:
            import pytesseract
            data = pytesseract.image_to_data(
                image,
                config="--psm 11 -l rus+eng",
                output_type=pytesseract.Output.DICT,
            )
            # "SEAT" removed — causes false clicks on lobby 'Seats' filter tab
            play_kws = {
                "LET'S PLAY", "LETS PLAY", "LET'S", "PLAY",
                "JOIN", "ИГРАТЬ", "ИГРАТ",
            }
            img_h = image.shape[0] if hasattr(image, "shape") else 9999
            # Only look in the bottom 55% of the lobby (skip nav tabs at top)
            min_y = int(img_h * 0.35)

            for i, txt in enumerate(data.get("text", [])):
                txt = (txt or "").strip()
                if not txt:
                    continue
                by = data["top"][i]
                if by < min_y:
                    continue   # skip navigation area
                txt_up = txt.upper()
                if txt_up in play_kws or any(kw in txt_up for kw in play_kws):
                    bx = data["left"][i]
                    bw = data["width"][i]
                    bh = data["height"][i]
                    cx = win_x + bx + bw // 2
                    cy = win_y + by + bh // 2
                    logger.info("Clicking '%s' button at screen (%d, %d)", txt, cx, cy)
                    self._focus_window(self.hwnd)
                    self._win32_click(cx, cy)
                    import time as _t; _t.sleep(0.1)
                    if AUTOGUI_AVAILABLE:
                        pyautogui.click(cx, cy)
                    return True
        except Exception as exc:
            logger.debug("_click_lets_play error: %s", exc)
        return False

    # ── Phase 2: PokerStars Buy-in Dialog Handler ─────────────────────────────

    async def handle_buyin_dialog(
        self,
        hwnd: int,
        strategy: str = "max",
        custom_amount: float = 0.0,
        timeout: float = 15.0,
    ) -> bool:
        """Detect and handle the PokerStars buy-in dialog.

        Returns True if the dialog was handled (OK pressed).
        Returns False if:
          - dialog not found
          - stop was requested
          - insufficient funds (Отмена clicked instead, balance stored in
            self.last_observed_balance for the caller to pick it up)
        """
        import asyncio

        if not AUTOGUI_AVAILABLE:
            logger.warning("handle_buyin_dialog: pyautogui not available")
            return False

        t0 = time.monotonic()

        # ── Wait for dialog to appear ─────────────────────────────────────────
        dialog_region = None
        while time.monotonic() - t0 < timeout:
            dialog_region = self._locate_buyin_dialog_on_screen()
            if dialog_region is not None:
                break
            await asyncio.sleep(0.4)

        if dialog_region is None:
            logger.warning("handle_buyin_dialog: dialog not found on screen within %.1fs", timeout)
            return False

        if self._check_stop():
            logger.info("handle_buyin_dialog: aborted after dialog detected (stop requested)")
            return False

        dlg_x, dlg_y, dlg_w, dlg_h = dialog_region

        import pyautogui as pag
        import cv2, numpy as np

        # ── Strategy A: HWND-based interaction (most reliable) ───────────────
        # Flutter buttons have no text — OCR can't find them.
        # Use child HWND enumeration to locate buttons by position.
        dialog_hwnd = self._find_buyin_dialog_hwnd()
        if dialog_hwnd is not None:
            logger.info("Using HWND-based buy-in interaction (dialog hwnd=%d)", dialog_hwnd)

            # Check insufficient funds via OCR before clicking anything
            await asyncio.sleep(0.3)
            try:
                full_shot = pag.screenshot()
                full_img = cv2.cvtColor(np.array(full_shot), cv2.COLOR_RGB2BGR)
                available_balance = self._read_balance_fullscreen(full_img)
                if available_balance > 0:
                    self.last_observed_balance = available_balance
                    logger.info("Balance from full-screen OCR: %.0f chips", available_balance)
                insufficient = self._fullscreen_has_insufficient_funds(full_img)
            except Exception as exc:
                logger.debug("Balance read error: %s", exc)
                available_balance = 0.0
                insufficient = False

            if insufficient:
                logger.warning("Insufficient funds — clicking Cancel")
                controls = self._analyze_buyin_dialog_children(dialog_hwnd)
                if 'cancel_btn' in controls:
                    cx, cy = controls['cancel_btn']
                    self._win32_click(cx, cy)
                    await asyncio.sleep(0.1)
                    pag.click(cx, cy)
                return False

            if self._check_stop():
                logger.info("handle_buyin_dialog: aborted before HWND click (stop requested)")
                return False

            hwnd_ok = await self._handle_buyin_via_hwnd(dialog_hwnd, strategy, custom_amount)
            if hwnd_ok:
                return True
            logger.warning("HWND-based buy-in failed, falling back to legacy approach")

        # ── Strategy B: Legacy OCR / position-based fallback ─────────────────
        await asyncio.sleep(0.3)
        full_shot = pag.screenshot()
        full_img  = cv2.cvtColor(np.array(full_shot), cv2.COLOR_RGB2BGR)

        available_balance = self._read_balance_fullscreen(full_img)
        if available_balance > 0:
            logger.info("Balance from full-screen OCR: %.0f chips", available_balance)
            self.last_observed_balance = available_balance

        insufficient = self._fullscreen_has_insufficient_funds(full_img)

        shot = pag.screenshot(region=(dlg_x, dlg_y, dlg_w, dlg_h))
        dlg_img = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

        if available_balance <= 0:
            available_balance = self._read_balance_from_dialog(dlg_img)
            if available_balance > 0:
                logger.info("Balance from dialog OCR: %.0f chips", available_balance)
                self.last_observed_balance = available_balance

        if not insufficient:
            insufficient = self._ok_button_is_grey(dlg_img)

        if insufficient:
            logger.warning(
                "Insufficient funds (balance=%.0f) — clicking Отмена",
                available_balance,
            )
            await self._click_cancel_button(dlg_x, dlg_y, dlg_w, dlg_h, pag)
            return False

        logger.info("Buy-in dialog fallback at (%d,%d) %dx%d strategy='%s' balance=%.0f",
                    dlg_x, dlg_y, dlg_w, dlg_h, strategy, available_balance)

        max_clicked = self._handle_buyin_via_ocr(dlg_img, dlg_x, dlg_y, strategy, custom_amount)

        if not max_clicked:
            if strategy == "max":
                mx = dlg_x + int(dlg_w * 0.80)
                my = dlg_y + int(dlg_h * 0.55)
                logger.info("Clicking Макс by position (%d, %d)", mx, my)
                self._win32_click(mx, my)
                await asyncio.sleep(0.15)
                pag.click(mx, my)
            elif strategy == "min":
                mx = dlg_x + int(dlg_w * 0.20)
                my = dlg_y + int(dlg_h * 0.55)
                self._win32_click(mx, my)
                await asyncio.sleep(0.15)
                pag.click(mx, my)

        await asyncio.sleep(0.3)

        if self._check_stop():
            logger.info("handle_buyin_dialog: aborted before OK click (stop requested)")
            return False

        shot2 = pag.screenshot(region=(dlg_x, dlg_y, dlg_w, dlg_h))
        dlg_img2 = cv2.cvtColor(np.array(shot2), cv2.COLOR_RGB2BGR)

        ok_pt = self._find_green_button(dlg_img2)
        if ok_pt is not None:
            ok_x = dlg_x + ok_pt[0]
            ok_y = dlg_y + ok_pt[1]
            logger.info("Green OK button detected at screen (%d, %d)", ok_x, ok_y)
            self._win32_click(ok_x, ok_y)
            await asyncio.sleep(0.15)
            pag.click(ok_x, ok_y)
            return True

        ok_clicked = self._click_buyin_ok(dlg_img2, dlg_x, dlg_y)
        if ok_clicked:
            return True

        # Last resort: right-bottom quadrant of dialog = OK button
        ok_x = dlg_x + int(dlg_w * 0.70)
        ok_y = dlg_y + int(dlg_h * 0.87)
        logger.info("OK last-resort position (%d, %d)", ok_x, ok_y)
        self._win32_click(ok_x, ok_y)
        await asyncio.sleep(0.15)
        pag.click(ok_x, ok_y)
        await asyncio.sleep(0.2)
        pag.press("enter")
        return True

    def _read_balance_fullscreen(self, full_img: "np.ndarray") -> float:
        """Scan the full screen for 'Доступно условных фишек: X' text.

        Works on the complete screenshot so it doesn't depend on correct
        dialog region detection.  Returns 0.0 if not found.
        """
        if not TESSERACT_AVAILABLE:
            return 0.0
        try:
            import pytesseract, re, cv2, numpy as np

            # Only look at the top-right and center portions (where the dialog is)
            h, w = full_img.shape[:2]
            # Dialog appears somewhere in the middle 60% of the screen
            roi = full_img[int(h * 0.1):int(h * 0.9), int(w * 0.2):int(w * 0.9)]

            data = pytesseract.image_to_data(
                roi,
                config="--psm 11 -l rus+eng",
                output_type=pytesseract.Output.DICT,
            )
            texts = [t or "" for t in data.get("text", [])]
            tops  = data.get("top", [])
            lefts = data.get("left", [])

            # Find "Доступно" keyword row
            avail_y = None
            for i, t in enumerate(texts):
                if re.match(r'доступ', t.lower()):
                    avail_y = tops[i]
                    break

            if avail_y is None:
                return 0.0

            # Collect all numbers on that line (±25 px)
            candidates = []
            for i, t in enumerate(texts):
                if abs(tops[i] - avail_y) > 25:
                    continue
                clean = re.sub(r'[\s,.]', '', t)
                if re.fullmatch(r'\d{3,9}', clean):
                    try:
                        val = float(clean)
                        if 100 <= val <= 100_000_000:
                            candidates.append((lefts[i], val))
                    except ValueError:
                        pass

            if candidates:
                _, val = max(candidates, key=lambda x: x[0])
                return val
        except Exception as exc:
            logger.debug("_read_balance_fullscreen: %s", exc)
        return 0.0

    def _fullscreen_has_insufficient_funds(self, full_img: "np.ndarray") -> bool:
        """Check if 'недостаточно' / 'insufficient' appears anywhere on screen."""
        if not TESSERACT_AVAILABLE:
            return False
        try:
            import pytesseract, cv2, numpy as np
            h, w = full_img.shape[:2]
            # Check center portion of screen where dialog appears
            roi = full_img[int(h * 0.1):int(h * 0.9), int(w * 0.2):int(w * 0.9)]
            text = pytesseract.image_to_string(roi, config="--psm 11 -l rus+eng").lower()
            return any(kw in text for kw in (
                "недостаточно", "insufficient", "недостат",
            ))
        except Exception:
            return False

    def _read_balance_from_dialog(self, dlg_img: "np.ndarray") -> float:
        """OCR the 'Доступно условных фишек: X' line from the buy-in dialog.

        The dialog is a known layout:
          "Доступно условных фишек:   30 001"
        We use word-level OCR to find the number that appears on the SAME
        LINE as any word starting with "доступ" (available).
        """
        if not TESSERACT_AVAILABLE:
            return 0.0
        try:
            import pytesseract, re, cv2, numpy as np

            # Use word-level data so we know y-positions of each word
            data = pytesseract.image_to_data(
                dlg_img,
                config="--psm 6 -l rus+eng",
                output_type=pytesseract.Output.DICT,
            )
            texts = [t or "" for t in data.get("text", [])]
            tops  = data.get("top", [])
            lefts = data.get("left", [])

            # Find the y-band of the "Доступно" row
            avail_y = None
            for i, t in enumerate(texts):
                if re.match(r'доступ', t.lower()):
                    avail_y = tops[i]
                    break

            if avail_y is None:
                return 0.0

            # Find the rightmost plausible number on the same line (±15 px)
            y_tol = 20
            candidates = []
            for i, t in enumerate(texts):
                if abs(tops[i] - avail_y) > y_tol:
                    continue
                clean = re.sub(r'[\s,.]', '', t)
                if re.fullmatch(r'\d{3,9}', clean):
                    try:
                        val = float(clean)
                        if 100 <= val <= 100_000_000:
                            candidates.append((lefts[i], val))
                    except ValueError:
                        pass

            if candidates:
                # Rightmost number on the line is the balance
                _, val = max(candidates, key=lambda x: x[0])
                return val

        except Exception as exc:
            logger.debug("_read_balance_from_dialog: %s", exc)
        return 0.0

    def _dialog_has_insufficient_funds(self, dlg_img: "np.ndarray") -> bool:
        """Return True if the buy-in dialog shows insufficient funds warning.

        Detects the warning text AND checks if the OK button area is grey
        (disabled) rather than green, as a visual fallback.
        """
        if not TESSERACT_AVAILABLE:
            return self._ok_button_is_grey(dlg_img)
        try:
            import pytesseract
            text = pytesseract.image_to_string(
                dlg_img, config="--psm 6 -l rus+eng"
            ).lower()
            insufficient_kws = (
                "недостаточно",    # "insufficient" in Russian
                "insufficient",
                "cannot afford",
                "not enough",
                "недостат",        # partial match for OCR errors
            )
            if any(kw in text for kw in insufficient_kws):
                return True
        except Exception:
            pass
        # Visual fallback: if the OK button area has no green pixels, it's disabled
        return self._ok_button_is_grey(dlg_img)

    def _ok_button_is_grey(self, dlg_img: "np.ndarray") -> bool:
        """Return True if the OK button area (bottom-left quarter) has no green pixels.

        PS OK button is bright green when enabled, grey when disabled.
        """
        try:
            import cv2, numpy as np
            h, w = dlg_img.shape[:2]
            # OK button is in the lower-left portion of the dialog
            ok_roi = dlg_img[int(h * 0.75):h, 0:int(w * 0.55)]
            hsv = cv2.cvtColor(ok_roi, cv2.COLOR_BGR2HSV)
            lo = np.array([45, 60, 80])
            hi = np.array([100, 255, 255])
            green_px = int(cv2.countNonZero(cv2.inRange(hsv, lo, hi)))
            logger.debug("OK button green pixels: %d", green_px)
            return green_px < 200   # fewer than 200 green pixels → button is grey
        except Exception:
            return False

    async def _click_cancel_button(
        self,
        dlg_x: int, dlg_y: int, dlg_w: int, dlg_h: int,
        pag: "Any",
    ) -> None:
        """Find and click the Отмена / Cancel button anywhere on screen.

        Uses full-screen word-level OCR so it works regardless of dialog
        position or window handle issues.
        """
        import asyncio
        if TESSERACT_AVAILABLE and CV2_AVAILABLE:
            try:
                import pytesseract, cv2, numpy as np
                # Full-screen screenshot — most reliable
                shot = pag.screenshot()
                img  = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
                data = pytesseract.image_to_data(
                    img, config="--psm 11 -l rus+eng",
                    output_type=pytesseract.Output.DICT,
                )
                cancel_kws = {"отмена", "отменить", "cancel", "закрыть", "close"}
                for i, txt in enumerate(data.get("text", [])):
                    low = (txt or "").lower().strip()
                    if low in cancel_kws:
                        # Screen coordinates directly
                        cx = data["left"][i] + data["width"][i] // 2
                        cy = data["top"][i]  + data["height"][i] // 2
                        logger.info("Clicking Отмена at screen (%d, %d)", cx, cy)
                        self._win32_click(cx, cy)
                        await asyncio.sleep(0.1)
                        pag.click(cx, cy)
                        return
            except Exception as exc:
                logger.debug("_click_cancel_button: %s", exc)

        # Fallback: press Escape (always cancels PS dialog)
        logger.info("Cancel fallback: pressing Escape")
        try:
            pag.press("escape")
        except Exception:
            pass

    def _find_ps_lobby_hwnd(self) -> "Optional[int]":
        """Find the PokerStars lobby window HWND by title search."""
        if not WIN32_AVAILABLE:
            return None
        _LOBBY_TITLES = ("лобби pokerstars", "pokerstars lobby", "лобби pokerstar")
        found = []

        def _cb(h, _):
            try:
                if not win32gui.IsWindowVisible(h):
                    return True
                title = win32gui.GetWindowText(h).lower()
                rect = win32gui.GetWindowRect(h)
                w = rect[2] - rect[0]
                hh = rect[3] - rect[1]
                # Lobby is large (>500x400), not the buy-in dialog
                if any(t in title for t in _LOBBY_TITLES) and w > 500 and hh > 400:
                    found.append(h)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_cb, None)
        except Exception:
            pass
        return found[0] if found else None

    def _find_buyin_dialog_hwnd(self) -> "Optional[int]":
        """Find the PokerStars buy-in dialog HWND.

        Search order (most reliable first):
        1. Title matches known buy-in dialog titles ('Бай-ин', 'Buy-In', 'Buy In', etc.)
           belonging to the PS process.
        2. Class '#32770' + dialog-sized (200–700 × 100–650) belonging to PS process.
        3. Same class/size check from any process (last resort).
        """
        if not WIN32_AVAILABLE:
            return None

        # Known buy-in dialog title substrings (Russian and English PS clients)
        _BUYIN_TITLES = ("бай-ин", "buy-in", "buy in", "buyin", "бай ин",
                         "купить фишки", "buy chips")

        ps_pid = 0
        if self.hwnd:
            try:
                import win32process
                _, ps_pid = win32process.GetWindowThreadProcessId(self.hwnd)
            except Exception:
                pass

        by_title: list[int] = []
        by_class: list[int] = []

        def _cb(h: int, _: object) -> bool:
            try:
                if not win32gui.IsWindowVisible(h):
                    return True
                if h == self.hwnd:
                    return True

                title = win32gui.GetWindowText(h).lower()
                cls = win32gui.GetClassName(h)
                rect = win32gui.GetWindowRect(h)
                w = rect[2] - rect[0]
                hh = rect[3] - rect[1]

                # Get process id for this window
                try:
                    import win32process as _wp
                    _, pid = _wp.GetWindowThreadProcessId(h)
                    is_ps = (ps_pid != 0 and pid == ps_pid)
                except Exception:
                    is_ps = False

                # --- Strategy 1: match by title (most reliable) ---
                if any(t in title for t in _BUYIN_TITLES):
                    if is_ps:
                        by_title.insert(0, h)
                    else:
                        by_title.append(h)
                    return True

                # --- Strategy 2: class + size + PS process ---
                if cls in ("#32770", "PokerStarsDialogClass") and \
                        200 <= w <= 700 and 100 <= hh <= 650:
                    if is_ps:
                        by_class.insert(0, h)
                    else:
                        by_class.append(h)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_cb, None)
        except Exception:
            pass

        for hwnd_dlg in (by_title + by_class):
            try:
                rect = win32gui.GetWindowRect(hwnd_dlg)
                logger.info(
                    "Buy-in dialog found: hwnd=%d title=%r cls=%s size=%dx%d",
                    hwnd_dlg,
                    win32gui.GetWindowText(hwnd_dlg),
                    win32gui.GetClassName(hwnd_dlg),
                    rect[2] - rect[0],
                    rect[3] - rect[1],
                )
                return hwnd_dlg
            except Exception:
                continue

        return None

    def _locate_buyin_dialog_on_screen(self) -> "Optional[tuple[int,int,int,int]]":
        """Find the PS buy-in dialog on screen.

        Delegates to _find_buyin_dialog_hwnd() which uses title-based search
        as the primary strategy, then focuses the window and returns its rect.
        """
        if not WIN32_AVAILABLE:
            return None

        hwnd_dlg = self._find_buyin_dialog_hwnd()
        if hwnd_dlg is None:
            return None

        try:
            self._focus_window(hwnd_dlg)
            rect = win32gui.GetWindowRect(hwnd_dlg)
            return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
        except Exception:
            return None

    def _analyze_buyin_dialog_children(self, dialog_hwnd: int) -> dict:
        """Enumerate child windows of the buy-in dialog and identify key controls.

        Returns a dict with keys:
          'edit'     → (cx, cy) center of the amount input field
          'max_btn'  → (cx, cy) center of the MAX button
          'min_btn'  → (cx, cy) center of the MIN button
          'ok_btn'   → (cx, cy) center of the OK/Сесть/Войти button
          'cancel_btn' → (cx, cy) center of the Cancel/Отмена button
        All coordinates are absolute screen coordinates.
        """
        if not WIN32_AVAILABLE:
            return {}

        try:
            dlg_rect = win32gui.GetWindowRect(dialog_hwnd)
        except Exception:
            return {}

        dlg_x, dlg_y, dlg_x2, dlg_y2 = dlg_rect
        dlg_w = dlg_x2 - dlg_x
        dlg_h = dlg_y2 - dlg_y
        if dlg_w <= 0 or dlg_h <= 0:
            return {}

        children = []
        def _cb(h, _):
            try:
                cls = win32gui.GetClassName(h)
                rect = win32gui.GetWindowRect(h)
                w = rect[2] - rect[0]
                hh = rect[3] - rect[1]
                if w <= 0 or hh <= 0:
                    return True
                cx = (rect[0] + rect[2]) // 2
                cy = (rect[1] + rect[3]) // 2
                # Relative position within dialog (0.0–1.0)
                rel_x = (cx - dlg_x) / dlg_w
                rel_y = (cy - dlg_y) / dlg_h
                children.append({
                    'hwnd': h, 'cls': cls,
                    'rect': rect, 'cx': cx, 'cy': cy,
                    'rel_x': rel_x, 'rel_y': rel_y,
                    'w': w, 'h': hh,
                })
            except Exception:
                pass
            return True

        try:
            win32gui.EnumChildWindows(dialog_hwnd, _cb, None)
        except Exception:
            pass

        result = {}

        # ── Edit field (standard Windows Edit class) ──────────────────────────
        edit_ctrls = [c for c in children if c['cls'] == 'Edit']
        if edit_ctrls:
            e = edit_ctrls[0]
            result['edit'] = (e['cx'], e['cy'])
            result['edit_hwnd'] = e['hwnd']

        # ── Flutter buttons ───────────────────────────────────────────────────
        flutter_btns = [c for c in children
                        if 'Flutter' in c['cls'] and 'Button' in c['cls']]

        # The slider row buttons are in the rel_y ≈ 0.45–0.65 band
        # MAX is rightmost there, MIN is leftmost
        slider_row = [b for b in flutter_btns
                      if 0.40 <= b['rel_y'] <= 0.68]
        if slider_row:
            slider_row_sorted = sorted(slider_row, key=lambda b: b['cx'])
            result['min_btn'] = (slider_row_sorted[0]['cx'],
                                 slider_row_sorted[0]['cy'])
            result['max_btn'] = (slider_row_sorted[-1]['cx'],
                                 slider_row_sorted[-1]['cy'])

        # The confirm row buttons are in the rel_y ≈ 0.70–0.98 band.
        # Filter out tiny buttons (< 20px wide) — icon-only helpers.
        confirm_row = [b for b in flutter_btns
                       if 0.70 <= b['rel_y'] <= 0.98 and b['w'] >= 20]

        if confirm_row:
            # First try to identify buttons by their Win32 text (most reliable).
            _OK_KW     = ('ok', 'ок', 'играть', 'сесть', 'войти', 'enter', 'play')
            _CANCEL_KW = ('cancel', 'отмена', 'закрыть', 'close', 'нет', 'no')
            ok_by_text     = None
            cancel_by_text = None
            for btn in confirm_row:
                try:
                    txt = win32gui.GetWindowText(btn['hwnd']).strip().lower()
                except Exception:
                    txt = ''
                if txt and any(kw in txt for kw in _OK_KW):
                    ok_by_text = btn
                elif txt and any(kw in txt for kw in _CANCEL_KW):
                    cancel_by_text = btn

            confirm_sorted = sorted(confirm_row, key=lambda b: b['cx'])

            if ok_by_text:
                result['ok_btn'] = (ok_by_text['cx'], ok_by_text['cy'])
            else:
                # In PokerStars "ОК" is the LEFT button, "Отмена" is RIGHT.
                result['ok_btn'] = (confirm_sorted[0]['cx'],
                                    confirm_sorted[0]['cy'])

            if cancel_by_text:
                result['cancel_btn'] = (cancel_by_text['cx'], cancel_by_text['cy'])
            else:
                result['cancel_btn'] = (confirm_sorted[-1]['cx'],
                                        confirm_sorted[-1]['cy'])

        logger.info(
            "_analyze_buyin_dialog_children: found %d children → keys=%s",
            len(children), list(result.keys()),
        )
        return result

    async def _handle_buyin_via_hwnd(
        self,
        dialog_hwnd: int,
        strategy: str,
        custom_amount: float,
    ) -> bool:
        """Interact with the buy-in dialog directly using child HWND positions.

        This bypasses OCR entirely — works even when Flutter buttons have no text.
        Returns True if OK was clicked successfully.
        """
        import asyncio
        try:
            import pyautogui as pag
        except ImportError:
            return False

        controls = self._analyze_buyin_dialog_children(dialog_hwnd)
        if not controls:
            logger.warning("_handle_buyin_via_hwnd: no controls found in dialog")
            return False

        await asyncio.sleep(0.2)

        # ── Step 1: set the buy-in amount ────────────────────────────────────
        if strategy == "max" and 'max_btn' in controls:
            mx, my = controls['max_btn']
            logger.info("Clicking MAX button at (%d, %d)", mx, my)
            self._win32_click(mx, my)
            await asyncio.sleep(0.2)
            pag.click(mx, my)
            await asyncio.sleep(0.3)

        elif strategy == "min" and 'min_btn' in controls:
            mx, my = controls['min_btn']
            logger.info("Clicking MIN button at (%d, %d)", mx, my)
            self._win32_click(mx, my)
            await asyncio.sleep(0.2)
            pag.click(mx, my)
            await asyncio.sleep(0.3)

        elif strategy == "custom" and custom_amount > 0 and 'edit' in controls:
            ex, ey = controls['edit']
            logger.info("Entering custom amount %.0f in Edit at (%d, %d)",
                        custom_amount, ex, ey)
            # Triple-click to select all, then type
            pag.click(ex, ey)
            await asyncio.sleep(0.1)
            pag.hotkey('ctrl', 'a')
            await asyncio.sleep(0.1)
            pag.typewrite(str(int(custom_amount)), interval=0.07)
            await asyncio.sleep(0.2)

        elif 'max_btn' in controls:
            # Default to MAX if strategy not matched
            mx, my = controls['max_btn']
            logger.info("Default MAX button at (%d, %d)", mx, my)
            self._win32_click(mx, my)
            await asyncio.sleep(0.2)
            pag.click(mx, my)
            await asyncio.sleep(0.3)

        # ── Step 2: click OK / Сесть / Войти ────────────────────────────────
        if 'ok_btn' not in controls:
            logger.warning("_handle_buyin_via_hwnd: OK button not found")
            return False

        ok_x, ok_y = controls['ok_btn']
        logger.info("Clicking OK button at (%d, %d)", ok_x, ok_y)
        await asyncio.sleep(0.3)
        self._win32_click(ok_x, ok_y)
        await asyncio.sleep(0.15)
        pag.click(ok_x, ok_y)
        return True

    def _find_green_button(self, img: "np.ndarray") -> "Optional[tuple[int,int]]":
        """Return the centre pixel of the largest green button in *img* (local coords)."""
        try:
            import cv2, numpy as np
            hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lo = np.array([55, 80, 120])
            hi = np.array([95, 255, 255])
            mask = cv2.inRange(hsv, lo, hi)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                    np.ones((5, 5), np.uint8))
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            for c in sorted(cnts, key=cv2.contourArea, reverse=True):
                if cv2.contourArea(c) < 300:
                    break
                bx, by, bw, bh = cv2.boundingRect(c)
                return (bx + bw // 2, by + bh // 2)
        except Exception as exc:
            logger.debug("_find_green_button error: %s", exc)
        return None

    def _capture_hwnd(self, hwnd: int) -> "Optional[np.ndarray]":
        """Capture a specific window by HWND and return as BGR ndarray."""
        try:
            import pyautogui as pag
            import numpy as np
            import cv2
            rect = win32gui.GetWindowRect(hwnd)
            x, y, x2, y2 = rect
            w, h = x2 - x, y2 - y
            if w > 0 and h > 0:
                shot = pag.screenshot(region=(x, y, w, h))
                return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.debug("_capture_hwnd(%d) error: %s", hwnd, exc)
        return None

    def _dialog_present(self, image: "np.ndarray") -> bool:
        """Return True if a buy-in dialog appears to be present in *image*."""
        if not TESSERACT_AVAILABLE:
            return False
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, config="--psm 11").lower()
            keywords = ("buy", "бай", "buy-in", "бай-ин", "buyin", "buy in",
                        "available", "доступно", "min", "мин", "max", "макс")
            return sum(kw in text for kw in keywords) >= 2
        except Exception:
            return False

    def _handle_buyin_via_ocr(
        self,
        image: "np.ndarray",
        win_x: int,
        win_y: int,
        strategy: str,
        custom_amount: float,
    ) -> bool:
        """Use OCR word positions to find and click Min/Max/amount field."""
        if not TESSERACT_AVAILABLE or not AUTOGUI_AVAILABLE:
            return False
        try:
            import pytesseract
            import pyautogui as pag

            data = pytesseract.image_to_data(
                image, config="--psm 11", output_type=pytesseract.Output.DICT
            )
            texts = data.get("text", [])

            # Keywords for Min and Max buttons (EN + RU)
            max_kws = {"max", "макс", "maximum"}
            min_kws = {"min", "мин", "minimum"}
            ok_kws  = {"ok", "ок", "confirm", "играть", "play", "sit", "join"}

            target_kws = max_kws if strategy == "max" else min_kws

            # Find amount input field centre (look for a number that looks like buyin)
            amount_field = None

            for i, txt in enumerate(texts):
                low = (txt or "").lower().strip()
                if not low:
                    continue
                bx = data["left"][i]
                by = data["top"][i]
                bw = data["width"][i]
                bh = data["height"][i]
                cx = win_x + bx + bw // 2
                cy = win_y + by + bh // 2

                if strategy in ("max", "min") and low in target_kws:
                    logger.info("Clicking '%s' button at screen (%d, %d)", txt, cx, cy)
                    pag.moveTo(cx, cy, duration=0.2)
                    self._win32_click(cx, cy)
                    import time as _t; _t.sleep(0.1)
                    pag.click(cx, cy)
                    return True

                if strategy == "custom" and re.match(r'^\d[\d\s,\.]+$', low):
                    # Likely the amount input field
                    amount_field = (cx, cy)

            if strategy == "custom" and custom_amount > 0:
                if amount_field:
                    pag.click(*amount_field)
                    import time as _t; _t.sleep(0.1)
                pag.hotkey("ctrl", "a")
                pag.typewrite(str(int(custom_amount)), interval=0.05)
                return True

        except Exception as exc:
            logger.debug("_handle_buyin_via_ocr error: %s", exc)
        return False

    # ── Window focus + reliable click helpers ────────────────────────────────

    def _focus_window(self, hwnd: int) -> None:
        """Bring the window to the foreground so clicks register properly."""
        if not WIN32_AVAILABLE or not hwnd:
            return
        try:
            import win32gui, win32con
            # Restore if minimized
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # Move off-screen window back to visible area
            rect = win32gui.GetWindowRect(hwnd)
            wx, wy, ww, wh = rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]
            if wx < -500 or wy < -500 or wx > 8000 or wy > 6000:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 50, 50, ww, wh,
                                      win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            logger.debug("Window hwnd=%d brought to foreground", hwnd)
        except Exception as exc:
            logger.debug("_focus_window error: %s", exc)

    def _win32_click(self, x: int, y: int) -> None:
        """Send a real WM_LBUTTONDOWN/UP pair via win32api for reliable clicking.

        This works even when pyautogui.click sometimes fails because the window
        wasn't fully focused yet.
        """
        # Suppress MouseGuard so bot-initiated cursor movement isn't mistaken for human
        try:
            from launcher.mouse_guard import MouseGuard
            MouseGuard.get_global().suppress(1.5)
        except Exception:
            pass
        try:
            import win32api, win32con
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            import time as _t; _t.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            logger.debug("win32_click at (%d, %d)", x, y)
        except Exception as exc:
            logger.debug("_win32_click error: %s — falling back to pyautogui", exc)
            if AUTOGUI_AVAILABLE:
                pyautogui.click(x, y)

    def _click_buyin_ok(self, image: "np.ndarray", win_x: int, win_y: int) -> bool:
        """Click the OK / Играть / Confirm button in the buy-in dialog.

        win_x/win_y are the screen coordinates of the TOP-LEFT corner of the
        captured dialog window (NOT the lobby window).
        """
        if not TESSERACT_AVAILABLE or not AUTOGUI_AVAILABLE:
            return False
        try:
            import pytesseract
            import pyautogui as pag

            # Try rus+eng first, fall back to eng only
            for lang in ("rus+eng", "eng"):
                try:
                    data = pytesseract.image_to_data(
                        image,
                        config=f"--psm 11 -l {lang}",
                        output_type=pytesseract.Output.DICT,
                    )
                    break
                except Exception:
                    data = {}

            ok_kws = {"ok", "ок", "confirm", "играть", "play", "sit", "join", "seat"}
            for i, txt in enumerate(data.get("text", [])):
                low = (txt or "").lower().strip()
                if not low:
                    continue
                if low in ok_kws or any(kw in low for kw in ok_kws):
                    bx = data["left"][i]
                    by = data["top"][i]
                    bw = data["width"][i]
                    bh = data["height"][i]
                    # Coordinates are relative to captured image → add dialog screen origin
                    cx = win_x + bx + bw // 2
                    cy = win_y + by + bh // 2
                    logger.info("Clicking OK/Играть '%s' at screen (%d, %d)", txt, cx, cy)
                    pag.moveTo(cx, cy, duration=0.2)
                    self._win32_click(cx, cy)
                    import time as _t; _t.sleep(0.12)
                    pag.click(cx, cy)
                    return True
        except Exception as exc:
            logger.debug("_click_buyin_ok error: %s", exc)
        return False
