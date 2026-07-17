"""
Lobby Scanner - Launcher Application (Roadmap6 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Scan poker lobby for tables
- OCR/ROI based table detection
- Filter by human count and seats
- Prioritize opportunities
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import time

logger = logging.getLogger(__name__)


@dataclass
class LobbyTable:
    """
    Lobby table information.
    
    Attributes:
        table_id: Unique table identifier
        table_name: Table name
        game_type: Game type (NLHE, PLO, etc.)
        stakes: Stakes (e.g., "0.25/0.50")
        players_seated: Number of players currently seated
        max_seats: Maximum seats at table
        human_count: Estimated human player count
        avg_pot: Average pot size
        hands_per_hour: Hands per hour
        waiting: Number of players waiting
        row_y_coordinate: Y pixel of the table row in the lobby window (for clicking)
        lets_play_btn_x: X pixel of the "LET'S PLAY" / "Играть" button (0 = unknown)
        buyin_min: Minimum buy-in chips (0 = unknown)
        buyin_max: Maximum buy-in chips (0 = unknown)
        room: Poker room identifier ("coinpoker", "pokerstars", etc.)
    """
    table_id: str
    table_name: str
    game_type: str = "NLHE"
    stakes: str = "0.25/0.50"
    players_seated: int = 0
    max_seats: int = 9
    human_count: int = 0
    avg_pot: float = 0.0
    hands_per_hour: int = 0
    waiting: int = 0
    row_y_coordinate: int = 0
    lets_play_btn_x: int = 0
    buyin_min: float = 0.0
    buyin_max: float = 0.0
    room: str = "unknown"
    
    def seats_available(self) -> int:
        """Get available seats."""
        return self.max_seats - self.players_seated
    
    def is_suitable_for_hive(self) -> bool:
        """
        Check if table is suitable for HIVE deployment.
        
        Requirements:
        - 1-3 human players
        - 3+ seats available
        
        Returns:
            True if suitable
        """
        return (
            1 <= self.human_count <= 3 and
            self.seats_available() >= 3
        )
    
    def priority_score(self) -> float:
        """
        Calculate priority score for HIVE deployment.
        
        Higher score = better opportunity.
        
        Factors:
        - Fewer humans = higher priority
        - More open seats = higher priority
        - Higher stakes = higher priority
        
        Returns:
            Priority score (0-100)
        """
        if not self.is_suitable_for_hive():
            return 0.0
        
        # Base score
        score = 50.0
        
        # Fewer humans bonus (1 human is best)
        if self.human_count == 1:
            score += 30.0
        elif self.human_count == 2:
            score += 20.0
        elif self.human_count == 3:
            score += 10.0
        
        # More open seats bonus
        open_seats = self.seats_available()
        score += min(open_seats * 2.0, 20.0)
        
        return min(score, 100.0)


@dataclass
class LobbySnapshot:
    """
    Snapshot of lobby state.
    
    Attributes:
        timestamp: Snapshot timestamp
        tables: List of tables in lobby
        total_tables: Total number of tables
    """
    timestamp: float = field(default_factory=time.time)
    tables: List[LobbyTable] = field(default_factory=list)
    total_tables: int = 0
    
    def get_hive_opportunities(self) -> List[LobbyTable]:
        """Get tables suitable for HIVE deployment, sorted by priority."""
        suitable = [t for t in self.tables if t.is_suitable_for_hive()]
        return sorted(suitable, key=lambda t: t.priority_score(), reverse=True)

    def find_best_opportunity(
        self,
        min_humans: int = 0,
        max_humans: int = 9,
        min_seats: int = 1,
        balance: float = 0.0,
    ) -> Optional["LobbyTable"]:
        """Return the best table to join.

        Picks tables with a valid row_y_coordinate so the navigator
        can actually click them.  If ``balance`` > 0, filters out tables
        where the minimum buy-in exceeds the available balance.
        """
        clickable = [t for t in self.tables if t.row_y_coordinate > 0]
        if not clickable:
            clickable = list(self.tables)
        if not clickable:
            return None

        # ── Exclude tables with unknown buy-in (buyin_min=0 means OCR failed)
        # These are dangerous: we don't know their cost so we must skip them.
        known_cost = [t for t in clickable if t.buyin_min > 0]
        if known_cost:
            clickable = known_cost
        else:
            # Every table has unknown cost — can't make a safe decision
            logger.warning(
                "find_best_opportunity: all %d tables have buyin_min=0 (parse failed)",
                len(clickable),
            )
            return None

        # ── Bankroll filter ───────────────────────────────────────────────────
        if balance > 0:
            affordable = [t for t in clickable if t.buyin_min <= balance]
            if affordable:
                clickable = affordable
            else:
                cheapest = min(t.buyin_min for t in clickable)
                logger.warning(
                    "find_best_opportunity: no affordable tables "
                    "(balance=%.0f, cheapest buyin_min=%.0f)",
                    balance, cheapest,
                )
                return None
        else:
            # Balance unknown — be very conservative: pick only the 3 cheapest tables
            sorted_cheap = sorted(clickable, key=lambda t: t.buyin_min)
            clickable = sorted_cheap[:3]
            logger.info(
                "find_best_opportunity: balance unknown — restricted to 3 cheapest "
                "(buyin_min: %s)",
                [round(t.buyin_min) for t in clickable],
            )

        # Prefer tables with at least 1 player seated (not empty)
        occupied = [t for t in clickable if t.players_seated >= 1]
        pool = occupied if occupied else clickable

        # Sort: cheapest first, then fewest seated players
        return sorted(pool, key=lambda t: (t.buyin_min, t.players_seated))[0]


class LobbyScanner:
    """
    Lobby scanner for finding table opportunities.
    
    Features:
    - Capture lobby window
    - OCR table information
    - Filter by criteria
    - Prioritize opportunities
    
    ⚠️ EDUCATIONAL NOTE:
        Scans lobby to find targets for coordinated bot deployment.
    """
    
    def __init__(self, lobby_window_id: Optional[str] = None, room: str = "coinpoker"):
        """
        Initialize lobby scanner.
        
        Args:
            lobby_window_id: Lobby window handle (for capture)
            room: Poker room identifier ("coinpoker" or "pokerstars")
        """
        self.lobby_window_id  = lobby_window_id
        self._hwnd: Optional[int] = None
        self._room: str = room.lower()
        self._last_snapshot: Optional[LobbySnapshot] = None
        
        logger.info("Lobby scanner initialized")
        logger.info("Lobby scanner initialized")
    
    def scan_lobby(self) -> LobbySnapshot:
        """Scan lobby — try real capture first, fall back to cache."""
        logger.info("Scanning lobby...")
        if self._hwnd:
            if self._room == "pokerstars":
                snapshot = self._scan_pokerstars_window(self._hwnd)
            else:
                snapshot = self._scan_coinpoker_window(self._hwnd)
            if snapshot.total_tables > 0:
                self._last_snapshot = snapshot
                return snapshot
        # Return cached snapshot if available
        if self._last_snapshot and self._last_snapshot.total_tables > 0:
            return self._last_snapshot
        return LobbySnapshot(tables=[], total_tables=0)

    def set_hwnd(self, hwnd: int) -> None:
        """Set the poker client window handle for real scanning."""
        self._hwnd = hwnd

    def set_room(self, room: str) -> None:
        """Set the room type: 'pokerstars' or 'coinpoker'."""
        self._room = room.lower()

    def read_ps_balance(self, hwnd: int) -> float:
        """Read the chip balance from the PokerStars lobby header.

        Uses pyautogui.screenshot on the window rect so the capture works
        even when ScreenCapture.capture_full_window fails.  Tries several
        OCR configs and crop regions to be as robust as possible.

        Returns 0.0 only if every strategy fails.
        """
        try:
            import re
            import cv2
            import numpy as np
            import pyautogui

            # Get lobby window screen rect
            try:
                import win32gui
                rect   = win32gui.GetWindowRect(hwnd)
                scr_x, scr_y = rect[0], rect[1]
                win_w  = rect[2] - rect[0]
                win_h  = rect[3] - rect[1]
            except Exception:
                scr_x, scr_y, win_w, win_h = 0, 0, 1024, 768

            # Balance is shown in the top-right corner of the lobby header.
            # On a ~1000px wide window it occupies roughly x: 55–80%, y: 4–12%.
            crop_x = scr_x + int(win_w * 0.50)
            crop_y = scr_y + int(win_h * 0.03)
            crop_w = int(win_w * 0.35)
            crop_h = int(win_h * 0.10)

            shot = pyautogui.screenshot(region=(crop_x, crop_y, crop_w, crop_h))
            roi  = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

            # Try multiple preprocessing + OCR config combos
            results: list[float] = []
            try:
                import pytesseract
            except ImportError:
                return 0.0

            for scale in (3, 2):
                big  = cv2.resize(roi, (roi.shape[1] * scale, roi.shape[0] * scale),
                                  interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

                for thresh_val in (160, 200, 128):
                    _, th = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)

                    for psm in ("7", "6", "11"):
                        for cfg_extra in ("", " -c tessedit_char_whitelist=0123456789 "):
                            try:
                                text = pytesseract.image_to_string(
                                    th,
                                    config=f"--psm {psm}{cfg_extra}",
                                )
                                # Match numbers with optional space/comma thousands sep
                                for m in re.finditer(r'\b(\d[\d\s,]{0,9}\d)\b', text):
                                    raw = re.sub(r'[\s,]', '', m.group(1))
                                    try:
                                        val = float(raw)
                                        # Valid PS chip balance: 100 … 100M
                                        if 100 <= val <= 100_000_000:
                                            results.append(val)
                                    except ValueError:
                                        pass
                            except Exception:
                                pass

            if results:
                # Pick the most common value; if tied, take the largest
                from collections import Counter
                best = Counter(results).most_common(1)[0][0]
                logger.info("PS balance OCR → %.0f chips", best)
                return best

        except Exception as exc:
            logger.debug("read_ps_balance error: %s", exc)
        return 0.0

    def _scan_coinpoker_window(self, hwnd: int) -> LobbySnapshot:
        """Parse real CoinPoker lobby via UIElement detection + OCR."""
        try:
            from bridge.screen_capture import ScreenCapture
            import cv2
            import numpy as np

            sc  = ScreenCapture()
            img = sc.capture_full_window(hwnd=hwnd)
            if img is None:
                return LobbySnapshot(tables=[], total_tables=0)

            if hasattr(img, "convert"):
                img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

            h, w = img.shape[:2]

            # ── Primary path: UIElement-based row grouping ────────────────────
            tables = self._scan_via_ui_elements(img, w, h)
            if tables:
                logger.info("CoinPoker scan: %d tables via UIElement groups", len(tables))
                return LobbySnapshot(tables=tables, total_tables=len(tables),
                                     timestamp=time.time())

            # ── Fallback: raw pytesseract OCR on cropped region ────────────────
            tables = self._scan_via_raw_ocr(img, w, h)
            logger.info("CoinPoker scan (OCR fallback): %d tables", len(tables))
            return LobbySnapshot(tables=tables, total_tables=len(tables),
                                 timestamp=time.time())

        except Exception as exc:
            logger.warning("CoinPoker window scan failed: %s", exc)
            return LobbySnapshot(tables=[], total_tables=0)

    # ── PokerStars-specific scanner ───────────────────────────────────────────

    def _sort_ps_lobby_by_stakes(self, hwnd: int) -> None:
        """Click the 'Ставки' column header to sort lobby by stakes ascending.

        Called once before each scan so cheap tables appear at the top.
        Safe to call repeatedly — clicking a sorted column cycles the order.
        We track whether we already sorted to avoid re-clicking on every scan.
        """
        try:
            import win32gui
            import pyautogui
            rect = win32gui.GetWindowRect(hwnd)
            win_x, win_y = rect[0], rect[1]
            win_w = rect[2] - rect[0]
            win_h = rect[3] - rect[1]
            if win_w < 200 or win_h < 200:
                return
            # "Ставки" column header is at ~26% from left, ~43% from top
            hdr_x = win_x + int(win_w * 0.26)
            hdr_y = win_y + int(win_h * 0.43)
            logger.info("Clicking 'Ставки' header to sort lobby (%d, %d)", hdr_x, hdr_y)
            pyautogui.click(hdr_x, hdr_y)
            time.sleep(0.5)
        except Exception as exc:
            logger.debug("_sort_ps_lobby_by_stakes error: %s", exc)

    def _capture_ps_lobby(self, hwnd: int):
        """Capture PS lobby window as BGR ndarray.

        Brings PS lobby to foreground first, then uses pyautogui.screenshot
        (actual screen pixels) which works for Flutter-based PS windows.
        Falls back to ScreenCapture.capture_full_window if pyautogui unavailable.
        """
        import cv2
        import numpy as np
        try:
            import win32gui
            import win32con
            import pyautogui

            # Bring PS lobby to front so pyautogui captures its pixels
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.4)
            except Exception:
                pass

            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w > 100 and h > 100:
                shot = pyautogui.screenshot(region=(x, y, w, h))
                img = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
                logger.debug(
                    "_capture_ps_lobby: screen capture %dx%d at (%d,%d) mean=%.1f",
                    w, h, x, y, float(img.mean()),
                )
                return img
        except Exception as exc:
            logger.debug("_capture_ps_lobby pyautogui failed: %s", exc)

        # Fallback: ScreenCapture (PrintWindow)
        try:
            from bridge.screen_capture import ScreenCapture
            sc = ScreenCapture()
            img = sc.capture_full_window(hwnd=hwnd)
            if img is not None:
                if hasattr(img, "convert"):
                    img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
                return img
        except Exception as exc:
            logger.debug("_capture_ps_lobby fallback failed: %s", exc)
        return None

    def _scan_pokerstars_window(self, hwnd: int) -> LobbySnapshot:
        """Parse PokerStars lobby: OCR rows from the cash-game table list."""
        try:
            import cv2
            import numpy as np

            # Sort lobby by stakes (cheapest first) so OCR picks affordable tables
            if not getattr(self, '_lobby_sorted', False):
                self._sort_ps_lobby_by_stakes(hwnd)
                self._lobby_sorted = True  # sort once per session

            img = self._capture_ps_lobby(hwnd)
            if img is None:
                return LobbySnapshot(tables=[], total_tables=0)

            h, w = img.shape[:2]

            # Primary: UIElement grouping
            tables = self._scan_ps_via_ui_elements(img, w, h)
            if tables:
                logger.info("PS scan: %d tables via UIElement groups", len(tables))
                return LobbySnapshot(tables=tables, total_tables=len(tables),
                                     timestamp=time.time())

            # Fallback: raw OCR
            tables = self._scan_ps_via_raw_ocr(img, w, h)
            logger.info("PS scan (OCR fallback): %d tables", len(tables))
            return LobbySnapshot(tables=tables, total_tables=len(tables),
                                 timestamp=time.time())

        except Exception as exc:
            logger.warning("PokerStars lobby scan failed: %s", exc)
            return LobbySnapshot(tables=[], total_tables=0)

    def _scan_ps_via_ui_elements(self, img, img_w: int, img_h: int) -> list:
        """UIElement-based PokerStars lobby table scanner."""
        try:
            from launcher.vision.auto_ui_detector import AutoUIDetector
            import re

            detector = AutoUIDetector()
            if not detector.available:
                return []

            # PS lobby: table list starts below navigation + filter bar (~42%),
            # ends above status bar (~95%). Left 75% is the table list area.
            crop_y0 = int(img_h * 0.42)
            crop_y1 = int(img_h * 0.95)
            crop_x1 = int(img_w * 0.75)
            roi = img[crop_y0:crop_y1, 0:crop_x1]

            elements = detector.detect_ui_elements(roi)
            if not elements:
                return []

            # Group by Y proximity ±8 px
            rows: dict = {}
            for el in elements:
                cx, cy = el.get_center()
                placed = False
                for ry in list(rows.keys()):
                    if abs(cy - ry) <= 8:
                        rows[ry].append(el)
                        placed = True
                        break
                if not placed:
                    rows[cy] = [el]

            return self._parse_ps_rows(rows, img_w, img_h, crop_y0)

        except Exception as exc:
            logger.debug("PS UIElement scan failed: %s", exc)
            return []

    def _scan_ps_via_raw_ocr(self, img, img_w: int, img_h: int) -> list:
        """Pytesseract OCR fallback for PokerStars lobby."""
        try:
            import cv2
            import pytesseract

            # PS lobby: table rows start below navigation + filter bar (~42%)
            crop_y0 = int(img_h * 0.42)
            crop_y1 = int(img_h * 0.95)
            crop_x1 = int(img_w * 0.75)
            roi = img[crop_y0:crop_y1, 0:crop_x1]

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            data = pytesseract.image_to_data(
                bw,
                config="--psm 6 --oem 1",
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            logger.debug("PS OCR unavailable: %s", exc)
            return []

        # Build word list
        import re
        words = []
        for i, txt in enumerate(data.get("text", [])):
            txt = txt.strip()
            if not txt:
                continue
            conf = int(data.get("conf", [0] * len(data["text"]))[i])
            if conf < 20:
                continue
            x = data["left"][i] // 2
            y = crop_y0 + data["top"][i] // 2
            words.append((txt, x, y))

        # Group into rows
        rows: dict = {}
        for txt, x, y in words:
            placed = False
            for ry in list(rows.keys()):
                if abs(y - ry) <= 6:
                    rows[ry].append((txt, x))
                    placed = True
                    break
            if not placed:
                rows[y] = [(txt, x)]

        # Filter out rows from the top navigation area before parsing
        min_y = int(img_h * 0.40)
        rows_for_parse = {
            ry: [type('E', (), {'text': t, 'bbox': (x, ry, 0, 0), 'get_center': lambda self=None, _x=x, _y=ry: (_x, _y)})()
                 for t, x in ws]
            for ry, ws in rows.items()
            if ry >= min_y
        }
        return self._parse_ps_rows(rows_for_parse, img_w, img_h, 0)

    def _parse_ps_rows(self, rows: dict, img_w: int, img_h: int, crop_y0: int) -> list:
        """
        Parse grouped lobby rows from PokerStars into LobbyTable objects.

        PS lobby columns (Russian client):
          Игра | Ставки | Игроки (seated/max) | Ср. банк | ...
        Blinds format: "100/200"  "50 000/100 000"  "1 000/2 000"
        Players format: "4" (green dot) or just a digit at right side
        Game type keyword: "Холдем" / "Hold'em" / "Омаха" / "Omaha"
        """
        import re

        # PS blinds: digits with optional space-thousand separator, slash separator
        # e.g. "100/200"  "50 000/100 000"  "1 000/2 000"  "25/50"
        # Limit each side to max 9 digits to avoid OCR column-merging artefacts
        blinds_pat = re.compile(
            r'(\d[\d ]{0,8})\s*/\s*(\d[\d ]{0,8})'
        )
        players_pat = re.compile(r'^(\d{1,2})$')
        skip_kws = {
            "игра", "ставки", "игроки", "ср", "банк", "zoom", "турнир",
            "все", "избранные", "кэш", "холдем холдем", "casino",
            "game", "stakes", "players", "avg", "pot", "tournament",
            "all", "favorites", "cash",
        }
        game_kws = {
            "холдем": "NLHE", "hold'em": "NLHE", "holdem": "NLHE",
            "омаха": "PLO", "omaha": "PLO",
        }

        tables = []
        seen: set = set()

        for row_y in sorted(rows.keys()):
            row_els = rows[row_y]
            # Sort by X for left-to-right reading
            try:
                row_els_sorted = sorted(row_els, key=lambda e: e.bbox[0])
            except Exception:
                row_els_sorted = row_els
            row_text = " ".join(
                e.text for e in row_els_sorted if getattr(e, 'text', '')
            ).strip()

            if not row_text:
                continue
            low = row_text.lower()
            if any(kw in low for kw in skip_kws):
                continue

            # Must contain blinds-like pattern
            blinds_m = blinds_pat.search(row_text)
            if not blinds_m:
                continue

            def _parse_ps_number(s: str) -> float:
                """Parse PS number with Russian abbreviations.
                '50 000' → 50000.0
                '1 тыс' / '1тыс' → 1000.0
                '5 млн' / '5млн' → 5000000.0
                """
                s = s.strip().lower()
                # Handle abbreviations BEFORE stripping spaces
                mult = 1.0
                if 'млн' in s or 'mln' in s or 'млрд' in s:
                    mult = 1_000_000.0
                    s = re.sub(r'(млн|mln|млрд)', '', s)
                elif 'тыс' in s or 'тыc' in s or 'k' in s:
                    mult = 1_000.0
                    s = re.sub(r'(тыс|тыc|k)', '', s)
                cleaned = re.sub(r'[^\d.,]', '', s).replace(',', '.')
                try:
                    return float(cleaned) * mult
                except ValueError:
                    return 0.0

            sb_f = _parse_ps_number(blinds_m.group(1))
            bb_f = _parse_ps_number(blinds_m.group(2))

            if sb_f == 0 and bb_f == 0:
                continue

            # Sanity: reject OCR artefacts (BB > 10M or SB/BB ratio wrong)
            if bb_f > 10_000_000:
                continue
            if sb_f > 0 and bb_f > 0:
                ratio = bb_f / sb_f
                if ratio < 1.5 or ratio > 3.0:  # normal is 2:1
                    continue

            stakes_str = f"{sb_f:.2f}/{bb_f:.2f}"

            # Game type
            game_type = "NLHE"
            for kw, gt in game_kws.items():
                if kw in low:
                    game_type = gt
                    break

            # Player count — look for a standalone 1-2-digit number after blinds
            after_blinds = row_text[blinds_m.end():].strip()
            seated = 0
            max_seats = 9
            for tok in after_blinds.split():
                tok_clean = re.sub(r'[^\d]', '', tok)
                if tok_clean and 1 <= int(tok_clean) <= 9:
                    seated = int(tok_clean)
                    break

            # Table name: text before blinds
            name_raw = row_text[:blinds_m.start()].strip()
            # Strip leading junk (hearts, icons, etc.)
            name_str = re.sub(r'^[^\w]+', '', name_raw).strip()
            if not name_str:
                name_str = f"PS_Table_{row_y}"
            # Limit length
            name_str = " ".join(name_str.split()[:5])

            # PS NL cash buy-in ranges: standard minimum is 40 BB, max is 100 BB
            # Example: 1000/2000 → min=80 000, max=200 000 (matches PS dialog)
            buyin_min = round(bb_f * 40, 2)
            buyin_max = round(bb_f * 100, 2)

            tid = f"ps_{row_y}_{sb_f}_{bb_f}"
            if tid in seen:
                continue
            seen.add(tid)

            abs_y = crop_y0 + row_y

            # Guard: skip rows that map to the top 40% of the window (navigation area)
            if img_h > 0 and abs_y < int(img_h * 0.40):
                logger.debug("PS skip nav row at abs_y=%d (< 40%% of %d)", abs_y, img_h)
                continue

            tables.append(LobbyTable(
                table_id=tid,
                table_name=name_str,
                game_type=game_type,
                stakes=stakes_str,
                players_seated=seated,
                max_seats=max_seats,
                human_count=max(0, min(seated, max_seats)),
                hands_per_hour=60,
                row_y_coordinate=abs_y,
                lets_play_btn_x=int(img_w * 0.82),  # "Играть" button right side
                buyin_min=buyin_min,
                buyin_max=buyin_max,
                room="pokerstars",
            ))

            logger.debug(
                "PS row y=%d: '%s' %s seated=%d buyin=%.0f-%.0f",
                abs_y, name_str, stakes_str, seated, buyin_min, buyin_max,
            )

        logger.info("PS OCR parsed %d tables from %d rows", len(tables), len(rows))
        return tables

    # ── CoinPoker UIElement scanner ───────────────────────────────────────────

    def _scan_via_ui_elements(self, img, img_w: int, img_h: int) -> list:
        """Group UIElements by Y-row and parse each row as a lobby table entry."""
        try:
            from launcher.vision.auto_ui_detector import AutoUIDetector
            import re

            detector = AutoUIDetector()
            if not detector.available:
                return []

            # Crop to table list area (exclude ads right 22%, top header 22%)
            crop_y0 = int(img_h * 0.22)
            crop_y1 = int(img_h * 0.93)
            crop_x1 = int(img_w * 0.78)
            roi = img[crop_y0:crop_y1, 0:crop_x1]

            elements = detector.detect_ui_elements(roi)
            if not elements:
                return []

            # Group elements into rows by Y-center (tolerance ±8 px)
            rows: dict = {}  # representative_y → [UIElement]
            for el in elements:
                cx, cy = el.get_center()
                placed = False
                for ry in list(rows.keys()):
                    if abs(cy - ry) <= 8:
                        rows[ry].append(el)
                        placed = True
                        break
                if not placed:
                    rows[cy] = [el]

            tables = []
            seen_ids: set = set()
            stakes_pat = re.compile(r'\$?([\d,]+\.?\d*)\s*/\s*\$?([\d,]+\.?\d*)')
            seats_pat  = re.compile(r'(\d+)\s*/\s*(\d+)')
            skip_kws   = ("game", "blinds", "seats", "wait", "let's play",
                          "tournaments", "sportsbook", "casino", "buy-in", "name",
                          "type", "action")
            game_types = {"hold'em": "NLHE", "holdem": "NLHE", "nlhe": "NLHE",
                          "omaha": "PLO", "plo": "PLO"}

            for row_cy in sorted(rows.keys()):
                row_els = rows[row_cy]
                # Merge text from all elements in this row
                row_text = " ".join(
                    el.text for el in sorted(row_els, key=lambda e: e.bbox[0])
                    if el.text
                ).strip()

                if not row_text:
                    continue
                low = row_text.lower()
                if any(kw in low for kw in skip_kws):
                    continue

                stakes_m = stakes_pat.search(row_text)
                if not stakes_m:
                    continue

                sb = stakes_m.group(1).replace(",", "")
                bb = stakes_m.group(2).replace(",", "")
                try:
                    stakes_str = f"{float(sb):.2f}/{float(bb):.2f}"
                except ValueError:
                    stakes_str = f"{sb}/{bb}"

                game_type = "NLHE"
                for kw, gt in game_types.items():
                    if kw in low:
                        game_type = gt
                        break

                seats_m   = seats_pat.search(row_text)
                seated    = int(seats_m.group(1)) if seats_m else 1
                max_seats = int(seats_m.group(2)) if seats_m else 6

                # Name: first token before stakes
                name_tok = row_text.split()[0] if row_text.split() else "Table"
                tid = f"cp_el_{row_cy}_{sb}_{bb}"
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)

                # Absolute Y in window (add back crop offset)
                abs_y = crop_y0 + row_cy

                tables.append(LobbyTable(
                    table_id=tid,
                    table_name=name_tok,
                    game_type=game_type,
                    stakes=stakes_str,
                    players_seated=seated,
                    max_seats=max_seats,
                    human_count=max(1, min(seated, 2)),
                    hands_per_hour=60,
                    row_y_coordinate=abs_y,
                    lets_play_btn_x=int(img_w * 0.85),  # typical button column
                    room="coinpoker",
                ))

            return tables
        except Exception as exc:
            logger.debug("UIElement-based scan failed: %s", exc)
            return []

    def _scan_via_raw_ocr(self, img, img_w: int, img_h: int) -> list:
        """Pytesseract OCR on the lobby area — tracks per-row Y coordinates."""
        try:
            import cv2
            import pytesseract

            # Crop: exclude top nav bar (~18%), bottom padding (~7%), ads right (~22%)
            crop_y0 = int(img_h * 0.18)
            crop_y1 = int(img_h * 0.93)
            crop_x1 = int(img_w * 0.78)
            roi = img[crop_y0:crop_y1, 0:crop_x1]

            # Pre-process for better OCR
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # image_to_data gives per-word bounding boxes
            data = pytesseract.image_to_data(
                bw,
                config="--psm 6 --oem 1",
                output_type=pytesseract.Output.DICT,
            )
        except Exception as ocr_exc:
            logger.debug("OCR not available: %s", ocr_exc)
            return []

        return self._parse_ocr_data(data, img_w, img_h, crop_y0, scale=2.0)

    def _parse_ocr_data(
        self,
        data: dict,
        img_w: int,
        img_h: int,
        crop_y0: int,
        scale: float = 2.0,
    ) -> list:
        """Group pytesseract word-level data into table rows and parse them."""
        import re

        # Build word list: (text, x, y_abs, conf)
        words = []
        for i, txt in enumerate(data.get("text", [])):
            txt = txt.strip()
            if not txt:
                continue
            conf = int(data.get("conf", [0] * len(data["text"]))[i])
            if conf < 20:
                continue
            x    = data["left"][i] // int(scale)
            y    = data["top"][i]  // int(scale)
            y_abs = crop_y0 + y
            words.append((txt, x, y_abs, conf))

        if not words:
            return []

        # Group into rows by Y proximity (±6 px after scaling)
        rows: dict = {}
        for txt, x, y_abs, conf in words:
            placed = False
            for ry in list(rows.keys()):
                if abs(y_abs - ry) <= 6:
                    rows[ry].append((txt, x))
                    placed = True
                    break
            if not placed:
                rows[y_abs] = [(txt, x)]

        # Currency-agnostic stakes regex: handles $, ¥, €, £, or nothing
        # Matches e.g. "¥0.05/¥0.10"  "0.25/0.50"  "$1.00/$2.00"
        stakes_pat = re.compile(
            r'[¥$€£]?([\d,]+\.?\d*)\s*/\s*[¥$€£]?(\d[\d,.]*)',
        )
        seats_pat  = re.compile(r'(\d+)\s*/\s*(\d+)')
        skip_kws   = {"game", "blinds", "seats", "wait", "play", "tournament",
                      "sportsbook", "casino", "buy-in", "name", "type",
                      "action", "balance", "lobby", "coinpoker"}
        game_kws   = {"hold'em": "NLHE", "holdem": "NLHE", "nlhe": "NLHE",
                      "omaha": "PLO", "plo": "PLO"}

        tables = []
        seen: set = set()

        for row_y in sorted(rows.keys()):
            row_words = sorted(rows[row_y], key=lambda w: w[1])  # sort by X
            row_text  = " ".join(w[0] for w in row_words)
            low       = row_text.lower()

            if any(kw in low for kw in skip_kws):
                continue

            stakes_m = stakes_pat.search(row_text)
            if not stakes_m:
                continue

            # Clean up OCR artefacts in numbers (¥ → nothing, comma → .)
            def clean_num(s: str) -> str:
                return s.replace(",", ".").replace("¥", "").replace("$", "").replace("€", "").replace("£", "")

            sb_raw = clean_num(stakes_m.group(1))
            bb_raw = clean_num(stakes_m.group(2))
            # Handle OCR reading "¥0.05" as "70.05" or "F0.10"
            sb_raw = re.sub(r'^[^0-9]', '', sb_raw)
            bb_raw = re.sub(r'^[^0-9]', '', bb_raw)
            try:
                sb_f = float(sb_raw) if sb_raw else 0.0
                bb_f = float(bb_raw) if bb_raw else 0.0
                stakes_str = f"{sb_f:.2f}/{bb_f:.2f}"
            except ValueError:
                stakes_str = f"{sb_raw}/{bb_raw}"

            if sb_f == 0 and bb_f == 0:
                continue

            game_type = "NLHE"
            for kw, gt in game_kws.items():
                if kw in low:
                    game_type = gt
                    break

            # Seats — find pair like "2/6" or "4/4"
            # Avoid matching stakes again: look after stakes position
            seats_region = row_text[stakes_m.end():]
            seats_m      = seats_pat.search(seats_region)
            if seats_m:
                seated    = int(seats_m.group(1))
                max_seats = int(seats_m.group(2))
            else:
                seated    = 1
                max_seats = 6

            # Table name — first token(s) before the stakes
            name_part = row_text[:stakes_m.start()].strip().split()
            name_str  = " ".join(name_part[:4]) if name_part else f"Table@{row_y}"
            # Clean up OCR junk at start
            name_str  = re.sub(r'^[^A-Za-z0-9]+', '', name_str).strip() or f"Table@{row_y}"

            tid = f"cp_{row_y}_{sb_raw}_{bb_raw}"
            if tid in seen:
                continue
            seen.add(tid)

            tables.append(LobbyTable(
                table_id=tid,
                table_name=name_str,
                game_type=game_type,
                stakes=stakes_str,
                players_seated=seated,
                max_seats=max_seats,
                human_count=max(0, min(seated, max_seats)),
                hands_per_hour=60,
                row_y_coordinate=row_y,
                lets_play_btn_x=int(img_w * 0.92),
                room="coinpoker",
            ))

            logger.debug(
                "Lobby row y=%d: '%s' %s %d/%d",
                row_y, name_str, stakes_str, seated, max_seats,
            )

        logger.info("Lobby OCR parsed %d tables from %d rows", len(tables), len(rows))
        return tables
    
    def find_best_opportunity(
        self,
        min_humans: int = 1,
        max_humans: int = 3,
        min_seats: int = 3
    ) -> Optional[LobbyTable]:
        """
        Find best table opportunity.
        
        Args:
            min_humans: Minimum human count
            max_humans: Maximum human count
            min_seats: Minimum available seats
        
        Returns:
            Best table if found
        """
        snapshot = self.scan_lobby()
        opportunities = snapshot.get_hive_opportunities()
        
        # Filter by criteria
        filtered = [
            t for t in opportunities
            if min_humans <= t.human_count <= max_humans
            and t.seats_available() >= min_seats
        ]
        
        if not filtered:
            logger.debug("No suitable opportunities found")
            return None
        
        best = filtered[0]
        logger.info(
            f"Best opportunity: {best.table_name} "
            f"({best.human_count} humans, {best.seats_available()} seats)"
        )
        
        return best
    
    def simulate_lobby_data(self, num_tables: int = 10) -> LobbySnapshot:
        """Return deterministic simulated lobby data (fixed seed — no random changes)."""
        import random
        rng = random.Random(42)   # fixed seed → same tables every call

        # Realistic CoinPoker-style table names
        _names  = ["NL $10 4 Max", "NL $25 4 Max", "NL $50 4 Max",
                   "NL $100 4 Max", "NL $200 4 Max", "NL $500 4 Max",
                   "NL $1,000", "NL $5,000", "PLO $25 4 Max", "PLO $50 4 Max",
                   "PLO $100 6 Max", "PLO $200 6 Max"]
        _types  = ["NLHE", "NLHE", "NLHE", "NLHE", "NLHE", "NLHE",
                   "NLHE", "NLHE", "PLO",  "PLO",  "PLO",  "PLO"]
        _stakes = ["0.05/0.10", "0.10/0.25", "0.25/0.50",
                   "0.50/1.00", "1.00/2.00", "2.50/5.00",
                   "5.00/10.00", "25.00/50.00",
                   "0.10/0.25", "0.25/0.50", "0.50/1.00", "1.00/2.00"]
        
        tables = []
        for i in range(min(num_tables, len(_names))):
            max_seats      = rng.choice([4, 6, 9])
            players_seated = rng.randint(1, max_seats - 1)
            human_count    = rng.randint(1, min(3, players_seated))
            avg_pot        = float(_stakes[i].split("/")[1]) * rng.uniform(3, 12)
            tables.append(LobbyTable(
                table_id       = f"sim_{i+1:03d}",
                table_name     = _names[i],
                game_type      = _types[i],
                stakes         = _stakes[i],
                players_seated = players_seated,
                max_seats      = max_seats,
                human_count    = human_count,
                avg_pot        = round(avg_pot, 2),
                hands_per_hour = rng.randint(55, 95),
            ))

        snapshot = LobbySnapshot(tables=tables, total_tables=len(tables))
        logger.info("Simulated %d tables (deterministic)", len(tables))
        return snapshot


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Lobby Scanner - Educational Research")
    print("=" * 60)
    print()
    
    # Create scanner
    scanner = LobbyScanner()
    
    print("Lobby scanner created")
    print()
    
    # Simulate lobby data
    print("Simulating lobby data (10 tables)...")
    snapshot = scanner.simulate_lobby_data(10)
    
    print(f"Total tables: {snapshot.total_tables}")
    print()
    
    # Find opportunities
    opportunities = snapshot.get_hive_opportunities()
    
    print(f"HIVE opportunities: {len(opportunities)}")
    if opportunities:
        print("\nTop 3 opportunities:")
        for i, table in enumerate(opportunities[:3], 1):
            print(f"  {i}. {table.table_name}")
            print(f"     Humans: {table.human_count}, Seats: {table.seats_available()}")
            print(f"     Priority: {table.priority_score():.1f}")
            print(f"     Stakes: {table.stakes}")
    
    print()
    
    # Find best opportunity
    print("Finding best opportunity...")
    best = scanner.find_best_opportunity()
    
    if best:
        print(f"Best table: {best.table_name}")
        print(f"  Humans: {best.human_count}")
        print(f"  Available seats: {best.seats_available()}")
        print(f"  Priority score: {best.priority_score():.1f}")
    else:
        print("  No suitable opportunities found")
    
    print()
    print("=" * 60)
    print("Lobby scanner demonstration complete")
    print("=" * 60)
