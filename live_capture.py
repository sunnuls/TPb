#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Live захват окна покер-клиента с автоматическим поиском.

Phase 1 (lobby_scanner.md) — расширен:
- LobbyCaptureScanner: распознавание таблиц лобби (имена столов, ставки, игроки, места)
- Multi-strategy OCR для текстовых полей лобби
- Lobby row detection (horizontal projection + contour analysis)
- Экспорт scan_lobby() для программного использования

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import mss
    HAS_MSS = True
except (ImportError, SyntaxError, Exception):
    HAS_MSS = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except (ImportError, SyntaxError, Exception):
    HAS_PYGETWINDOW = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model for lobby scan results
# ---------------------------------------------------------------------------

@dataclass
class LobbyTable:
    """A single table entry parsed from the lobby."""
    name: str = ""
    stakes: str = ""            # e.g. "$0.01/$0.02"
    game_type: str = ""         # e.g. "NL Hold'em"
    players: int = 0            # current players
    max_players: int = 0        # max seats
    avg_pot: str = ""
    raw_text: str = ""
    row_index: int = 0
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h in image

    @property
    def occupancy(self) -> float:
        if self.max_players > 0:
            return self.players / self.max_players
        return 0.0

    @property
    def is_full(self) -> bool:
        return self.max_players > 0 and self.players >= self.max_players


@dataclass
class LobbyScanResult:
    """Result of scanning the poker lobby."""
    tables: List[LobbyTable] = field(default_factory=list)
    total_rows_detected: int = 0
    ocr_confidence: float = 0.0
    elapsed_ms: float = 0.0
    error: str = ""

    @property
    def table_count(self) -> int:
        return len(self.tables)

    def available_tables(self, min_seats: int = 1) -> List[LobbyTable]:
        """Tables with at least *min_seats* free seats."""
        return [t for t in self.tables
                if t.max_players - t.players >= min_seats]

    def summary(self) -> str:
        lines = [
            f"Lobby: {self.table_count} tables, "
            f"{self.total_rows_detected} rows detected, "
            f"{self.elapsed_ms:.0f}ms",
        ]
        for t in self.tables:
            seats = f"{t.players}/{t.max_players}" if t.max_players else f"{t.players}"
            lines.append(f"  {t.name:30s} {t.stakes:15s} {seats:6s} {t.game_type}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LobbyCaptureScanner — OCR-based lobby scanning
# ---------------------------------------------------------------------------

class LobbyCaptureScanner:
    """
    Scans a poker client lobby screenshot to extract table listings.

    Uses multi-strategy OCR to detect:
    - Table names
    - Stakes (blinds)
    - Player/seat counts (e.g. "6/9")
    - Game type (NL Hold'em, PLO, etc.)
    - Average pot

    Pipeline:
    1. Preprocess (grayscale, CLAHE, threshold)
    2. Detect rows via horizontal projection profile
    3. OCR each row with multi-preprocessing
    4. Parse structured fields from raw text
    """

    # Known game type patterns
    GAME_PATTERNS = [
        r"(?:no[\s-]?limit|nl)\s*(?:hold.?em|holdem)",
        r"(?:pot[\s-]?limit|pl)\s*(?:omaha|omha)",
        r"(?:fixed[\s-]?limit|fl)\s*(?:hold.?em|holdem)",
        r"nl\s*omaha",
        r"rush\s*&?\s*cash",
        r"zoom",
        r"fast[\s-]?fold",
    ]

    # Stakes pattern: $X/$Y or X/Y
    STAKES_RE = re.compile(
        r'\$?([\d,.]+)\s*/\s*\$?([\d,.]+)'
    )

    # Player count: N/M or N of M
    PLAYER_RE = re.compile(
        r'(\d{1,2})\s*/\s*(\d{1,2})'
    )

    def __init__(self, lang: str = "eng"):
        self._lang = lang

    def scan_image(self, image) -> LobbyScanResult:
        """Scan a lobby screenshot.

        Args:
            image: PIL Image, numpy BGR array, or file path (str)

        Returns:
            LobbyScanResult
        """
        t0 = time.perf_counter()
        result = LobbyScanResult()

        if not HAS_CV2 or not HAS_TESSERACT:
            result.error = "cv2 or pytesseract not available"
            return result

        # Convert input to BGR numpy
        img_bgr = self._to_bgr(image)
        if img_bgr is None:
            result.error = "Could not read image"
            return result

        h, w = img_bgr.shape[:2]

        # 1. Detect rows
        rows = self._detect_rows(img_bgr)
        result.total_rows_detected = len(rows)

        if not rows:
            # Fallback: try full-image OCR and split by lines
            rows = self._fallback_rows(img_bgr)
            result.total_rows_detected = len(rows)

        # 2. OCR + parse each row
        confidences = []
        for idx, (ry, rh) in enumerate(rows):
            row_img = img_bgr[ry:ry + rh, 0:w]
            if row_img.size == 0:
                continue
            raw_text, conf = self._ocr_row(row_img)
            if not raw_text.strip():
                continue

            table = self._parse_row_text(raw_text, idx)
            table.bbox = (0, ry, w, rh)
            table.raw_text = raw_text
            result.tables.append(table)
            confidences.append(conf)

        if confidences:
            result.ocr_confidence = sum(confidences) / len(confidences)

        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    # ---- Image conversion ----

    @staticmethod
    def _to_bgr(image) -> Optional[np.ndarray]:
        if isinstance(image, str):
            try:
                return cv2.imread(image)
            except Exception:
                return None
        if isinstance(image, Image.Image):
            arr = np.array(image)
            if len(arr.shape) == 3 and arr.shape[2] == 3:
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            return arr
        if isinstance(image, np.ndarray):
            return image
        return None

    # ---- Row detection ----

    def _detect_rows(self, img_bgr: np.ndarray) -> List[Tuple[int, int]]:
        """Detect table rows using horizontal projection profile."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Edge detection to find row separators
        edges = cv2.Canny(gray, 30, 100)

        # Horizontal projection: sum of edge pixels per row
        proj = np.sum(edges, axis=1).astype(float)

        # Smooth projection
        kernel_size = max(3, h // 100)
        if kernel_size % 2 == 0:
            kernel_size += 1
        proj_smooth = cv2.GaussianBlur(proj.reshape(-1, 1), (1, kernel_size), 0).flatten()

        # Find peaks (row boundaries) — rows are between low-projection regions
        threshold = np.mean(proj_smooth) * 0.3
        in_row = proj_smooth < threshold

        rows = []
        row_start = None
        min_row_h = max(15, h // 50)
        max_row_h = h // 5

        for y in range(h):
            if not in_row[y] and row_start is None:
                row_start = y
            elif in_row[y] and row_start is not None:
                row_h = y - row_start
                if min_row_h <= row_h <= max_row_h:
                    rows.append((row_start, row_h))
                row_start = None

        if row_start is not None:
            row_h = h - row_start
            if min_row_h <= row_h <= max_row_h:
                rows.append((row_start, row_h))

        return rows

    def _fallback_rows(self, img_bgr: np.ndarray) -> List[Tuple[int, int]]:
        """Fallback: divide image into equal-height rows."""
        h, w = img_bgr.shape[:2]
        row_h = max(25, h // 20)
        rows = []
        for y in range(0, h - row_h, row_h):
            rows.append((y, row_h))
        return rows

    # ---- OCR ----

    def _ocr_row(self, row_img: np.ndarray) -> Tuple[str, float]:
        """OCR a single row image, returning (text, confidence 0-1)."""
        gray = cv2.cvtColor(row_img, cv2.COLOR_BGR2GRAY)

        # Try multiple preprocessings
        best_text = ""
        best_conf = 0.0

        for prep in self._preprocess_variants(gray):
            try:
                data = pytesseract.image_to_data(
                    prep, lang=self._lang, output_type=pytesseract.Output.DICT,
                )
                texts = []
                confs = []
                for i, txt in enumerate(data["text"]):
                    c = int(data["conf"][i])
                    if txt.strip() and c > 0:
                        texts.append(txt.strip())
                        confs.append(c)

                text = " ".join(texts)
                conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0

                if len(text) > len(best_text):
                    best_text = text
                    best_conf = conf
            except Exception:
                continue

        return best_text, best_conf

    @staticmethod
    def _preprocess_variants(gray: np.ndarray) -> List[np.ndarray]:
        """Multiple preprocessing strategies for OCR."""
        variants = []
        # 1. Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)
        # 2. CLAHE + Otsu
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        cl = clahe.apply(gray)
        _, cl_otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(cl_otsu)
        # 3. Adaptive
        adapt = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2,
        )
        variants.append(adapt)
        # 4. Scale up 2x + Otsu
        h, w = gray.shape
        scaled = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
        _, sc_otsu = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(sc_otsu)
        return variants

    # ---- Text parsing ----

    def _parse_row_text(self, raw: str, idx: int) -> LobbyTable:
        """Parse structured fields from a raw OCR text line."""
        table = LobbyTable(row_index=idx)

        # Stakes
        m = self.STAKES_RE.search(raw)
        if m:
            table.stakes = f"${m.group(1)}/${m.group(2)}"

        # Player count
        m_p = self.PLAYER_RE.search(raw)
        if m_p:
            table.players = int(m_p.group(1))
            table.max_players = int(m_p.group(2))

        # Game type
        raw_lower = raw.lower()
        for pattern in self.GAME_PATTERNS:
            if re.search(pattern, raw_lower):
                table.game_type = re.search(pattern, raw_lower).group(0).strip()
                break

        # Table name: first continuous word sequence before stakes/numbers
        # heuristic: take the first 1-3 "words" that aren't numbers
        tokens = raw.split()
        name_parts = []
        for tok in tokens:
            if re.match(r'^[\$\d,./]+$', tok):
                break
            if len(tok) > 1:
                name_parts.append(tok)
            if len(name_parts) >= 3:
                break
        if name_parts:
            table.name = " ".join(name_parts)

        return table


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def scan_lobby(image) -> LobbyScanResult:
    """Quick scan a lobby image (PIL, numpy, or path).

    Returns LobbyScanResult with parsed table listings.
    """
    scanner = LobbyCaptureScanner()
    return scanner.scan_image(image)


def find_poker_window(lobby: bool = False):
    """Поиск окна покер-клиента.

    Args:
        lobby: if True, prefer lobby windows (wider title match).
    """
    if not HAS_PYGETWINDOW:
        print("pygetwindow not installed")
        return None

    keywords = ['PokerStars', 'GGPoker', 'PartyPoker', 'Poker', 'Hold', 'Texas']
    if lobby:
        keywords += ['Lobby', 'lobby', 'Кэш', 'Cash', 'Tournament', 'Турнир']

    all_windows = gw.getAllTitles()
    
    print("\n=== Поиск окна покер-клиента ===\n")
    
    for title in all_windows:
        if not title.strip():
            continue
            
        for keyword in keywords:
            if keyword.lower() in title.lower():
                try:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        window = windows[0]
                        if window.width > 300 and window.height > 300:
                            print(f"Найдено: {title}")
                            print(f"Размер: {window.width} x {window.height}")
                            print(f"Позиция: ({window.left}, {window.top})")
                            return window
                except Exception:
                    continue
    
    print("Окно НЕ найдено!")
    print("\nДоступные окна:")
    for i, title in enumerate(all_windows[:15]):
        if title.strip():
            print(f"  {i+1}. {title}")
    return None


def capture_window(window):
    """Захват окна"""
    if not HAS_MSS:
        print("mss not installed")
        return None
    try:
        with mss.mss() as sct:
            monitor = {
                "top": window.top,
                "left": window.left,
                "width": window.width,
                "height": window.height
            }
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
    except Exception as e:
        print(f"Ошибка захвата: {e}")
        return None


def main():
    """Entry-point — supports --lobby flag for lobby scanning mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Poker Capture")
    parser.add_argument("--lobby", action="store_true",
                        help="Lobby scanning mode: OCR table listings")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="Capture interval in seconds (default 3)")
    args = parser.parse_args()

    print("=" * 60)
    if args.lobby:
        print("  LIVE LOBBY SCANNER (OCR)")
    else:
        print("  LIVE POKER WINDOW CAPTURE")
    print("=" * 60)
    
    window = find_poker_window(lobby=args.lobby)
    
    if not window:
        print("\n!!! Откройте покер-клиент и запустите снова !!!")
        input("\nНажмите Enter для выхода...")
        return
    
    lobby_scanner = LobbyCaptureScanner() if args.lobby else None

    print("\n" + "=" * 60)
    mode = "Lobby scan" if args.lobby else "Захват"
    print(f"  {mode} каждые {args.interval} сек.")
    print("  Нажмите Ctrl+C для остановки")
    print("=" * 60 + "\n")
    
    capture_count = 0
    
    try:
        while True:
            img = capture_window(window)
            
            if img:
                capture_count += 1
                timestamp = time.strftime("%H:%M:%S")
                size_str = f"{img.size[0]}x{img.size[1]}"
                
                if args.lobby and lobby_scanner:
                    result = lobby_scanner.scan_image(img)
                    print(f"[{timestamp}] Scan #{capture_count}: "
                          f"{result.table_count} tables, "
                          f"{result.elapsed_ms:.0f}ms, "
                          f"OCR conf={result.ocr_confidence:.0%}")
                    if result.tables:
                        for t in result.tables[:5]:
                            seats = (f"{t.players}/{t.max_players}"
                                     if t.max_players else str(t.players))
                            print(f"    {t.name:25s} {t.stakes:12s} "
                                  f"seats={seats} {t.game_type}")
                else:
                    print(f"[{timestamp}] Захват #{capture_count}: {size_str} px")
                
                # Сохраняем последний кадр
                img.save("last_capture.png")
            else:
                print("Переподключение...")
                time.sleep(1)
                window = find_poker_window(lobby=args.lobby)
                if not window:
                    print("Окно потеряно!")
                    break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\n\nОстановка...\n")
        print(f"Всего захватов: {capture_count}")
        print(f"Последний кадр: last_capture.png")


if __name__ == '__main__':
    main()
