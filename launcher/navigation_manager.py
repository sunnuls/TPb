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
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    AUTOGUI_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SyntaxError):
    AUTOGUI_AVAILABLE = False

try:
    import win32gui
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
