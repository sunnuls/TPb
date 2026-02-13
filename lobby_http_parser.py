#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
lobby_http_parser.py — Unified lobby data fetcher (Phase 2, lobby_scanner.md).

Provides a single entry-point for lobby data with automatic fallback chain:

  1. HTTP API  — fastest, structured data (if poker room exposes local API)
  2. OCR scan  — screenshot-based fallback (LobbyCaptureScanner from Phase 1)

The module bridges the HTTP parser from ``launcher/vision/lobby_http_parser.py``
and the OCR scanner from ``live_capture.py`` into one coherent interface.

Usage::

    from lobby_http_parser import LobbyFetcher, FetchStrategy
    fetcher = LobbyFetcher(strategy=FetchStrategy.AUTO)
    result = fetcher.fetch()
    for t in result.tables:
        print(t.name, t.stakes, t.players, t.max_players)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Imports (graceful)
# ---------------------------------------------------------------------------

# HTTP backend
try:
    from launcher.vision.lobby_http_parser import (
        LobbyHTTPParser,
        LobbyHTTPResult,
        RoomBackend,
        EndpointConfig,
        TokenBucketLimiter,
        HTTPResponse,
        parse_json_lobby,
        parse_html_lobby,
        _normalise_stakes,
        _parse_player_string,
    )
    HAS_HTTP_BACKEND = True
except (ImportError, SyntaxError, Exception):
    HAS_HTTP_BACKEND = False

# OCR backend
try:
    from live_capture import (
        LobbyCaptureScanner,
        LobbyScanResult,
        LobbyTable as OCRLobbyTable,
        scan_lobby,
    )
    HAS_OCR_BACKEND = True
except (ImportError, SyntaxError, Exception):
    HAS_OCR_BACKEND = False


# ---------------------------------------------------------------------------
# Unified data model
# ---------------------------------------------------------------------------

class FetchStrategy(str, Enum):
    """Strategy for lobby data retrieval."""
    HTTP_ONLY = "http_only"
    OCR_ONLY = "ocr_only"
    AUTO = "auto"            # HTTP first, OCR fallback
    HTTP_THEN_OCR = "http_then_ocr"   # same as AUTO
    OCR_THEN_HTTP = "ocr_then_http"   # OCR first, HTTP fallback


@dataclass
class UnifiedTable:
    """Unified table entry combining HTTP and OCR data."""
    table_id: str = ""
    name: str = ""
    stakes: str = ""
    game_type: str = ""
    players: int = 0
    max_players: int = 0
    avg_pot: float = 0.0
    hands_per_hour: int = 0
    waiting: int = 0
    source: str = ""        # "http" or "ocr"
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def occupancy(self) -> float:
        return self.players / self.max_players if self.max_players > 0 else 0.0

    @property
    def is_full(self) -> bool:
        return self.max_players > 0 and self.players >= self.max_players

    @property
    def free_seats(self) -> int:
        return max(0, self.max_players - self.players)

    @classmethod
    def from_http_dict(cls, d: Dict[str, Any]) -> "UnifiedTable":
        """Create from HTTP parser dict."""
        return cls(
            table_id=str(d.get("table_id", "")),
            name=str(d.get("table_name", "")),
            stakes=str(d.get("stakes", "")),
            game_type=str(d.get("game_type", "")),
            players=int(d.get("players_seated", 0)),
            max_players=int(d.get("max_seats", 9)),
            avg_pot=float(d.get("avg_pot", 0.0)),
            hands_per_hour=int(d.get("hands_per_hour", 0)),
            waiting=int(d.get("waiting", 0)),
            source="http",
            raw=d,
        )

    @classmethod
    def from_ocr_table(cls, t, idx: int = 0) -> "UnifiedTable":
        """Create from OCR LobbyTable."""
        return cls(
            table_id=f"ocr_{idx:03d}",
            name=getattr(t, "name", ""),
            stakes=getattr(t, "stakes", ""),
            game_type=getattr(t, "game_type", ""),
            players=getattr(t, "players", 0),
            max_players=getattr(t, "max_players", 0),
            avg_pot=0.0,
            source="ocr",
            raw={"raw_text": getattr(t, "raw_text", "")},
        )


@dataclass
class UnifiedFetchResult:
    """Result of a unified lobby fetch."""
    tables: List[UnifiedTable] = field(default_factory=list)
    strategy_used: str = ""     # which strategy actually produced data
    http_tried: bool = False
    http_ok: bool = False
    ocr_tried: bool = False
    ocr_ok: bool = False
    elapsed_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def ok(self) -> bool:
        return len(self.tables) > 0

    def available_tables(self, min_seats: int = 1) -> List[UnifiedTable]:
        """Tables with at least *min_seats* free."""
        return [t for t in self.tables if t.free_seats >= min_seats]

    def summary(self) -> str:
        lines = [
            f"Lobby fetch: {self.table_count} tables via {self.strategy_used} "
            f"({self.elapsed_ms:.0f}ms)",
        ]
        if self.errors:
            lines.append(f"  Errors: {'; '.join(self.errors)}")
        for t in self.tables:
            seats = f"{t.players}/{t.max_players}" if t.max_players else str(t.players)
            lines.append(
                f"  [{t.source:4s}] {t.name:25s} {t.stakes:14s} "
                f"{seats:6s} {t.game_type}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LobbyFetcher — unified facade
# ---------------------------------------------------------------------------

class LobbyFetcher:
    """Unified lobby fetcher with HTTP and OCR backends.

    Args:
        strategy: FetchStrategy controlling backend order
        http_backend: RoomBackend enum (default GENERIC)
        http_endpoint: Optional custom EndpointConfig
        http_proxy: Optional proxy URL
        ocr_lang: Tesseract language for OCR backend
    """

    def __init__(
        self,
        strategy: FetchStrategy = FetchStrategy.AUTO,
        http_backend: str = "generic",
        http_endpoint: Optional[Any] = None,
        http_proxy: Optional[str] = None,
        ocr_lang: str = "eng",
    ):
        self.strategy = strategy
        self._http_parser: Optional[Any] = None
        self._ocr_scanner: Optional[Any] = None

        # Init HTTP backend
        if HAS_HTTP_BACKEND and strategy not in (FetchStrategy.OCR_ONLY,):
            try:
                backend = RoomBackend(http_backend)
            except ValueError:
                backend = RoomBackend.GENERIC
            self._http_parser = LobbyHTTPParser(
                backend=backend,
                endpoint=http_endpoint,
                proxy=http_proxy,
            )

        # Init OCR backend
        if HAS_OCR_BACKEND and strategy not in (FetchStrategy.HTTP_ONLY,):
            self._ocr_scanner = LobbyCaptureScanner(lang=ocr_lang)

    @property
    def has_http(self) -> bool:
        return self._http_parser is not None

    @property
    def has_ocr(self) -> bool:
        return self._ocr_scanner is not None

    def fetch(
        self,
        image=None,
        extra_query: Optional[Dict[str, str]] = None,
    ) -> UnifiedFetchResult:
        """Fetch lobby data according to the configured strategy.

        Args:
            image: For OCR — PIL Image, numpy array, or file path.
                   If None and OCR is needed, returns empty OCR result.
            extra_query: Extra HTTP query parameters.

        Returns:
            UnifiedFetchResult
        """
        t0 = time.perf_counter()
        result = UnifiedFetchResult()

        if self.strategy in (FetchStrategy.AUTO, FetchStrategy.HTTP_THEN_OCR):
            # Try HTTP first
            self._try_http(result, extra_query)
            if not result.ok and image is not None:
                self._try_ocr(result, image)
        elif self.strategy == FetchStrategy.OCR_THEN_HTTP:
            # Try OCR first
            if image is not None:
                self._try_ocr(result, image)
            if not result.ok:
                self._try_http(result, extra_query)
        elif self.strategy == FetchStrategy.HTTP_ONLY:
            self._try_http(result, extra_query)
        elif self.strategy == FetchStrategy.OCR_ONLY:
            if image is not None:
                self._try_ocr(result, image)
            else:
                result.errors.append("OCR_ONLY but no image provided")

        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def fetch_http(
        self, extra_query: Optional[Dict[str, str]] = None
    ) -> UnifiedFetchResult:
        """Fetch via HTTP only."""
        t0 = time.perf_counter()
        result = UnifiedFetchResult()
        self._try_http(result, extra_query)
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def fetch_ocr(self, image) -> UnifiedFetchResult:
        """Fetch via OCR only."""
        t0 = time.perf_counter()
        result = UnifiedFetchResult()
        self._try_ocr(result, image)
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        return result

    def is_http_available(self) -> bool:
        """Quick check if the HTTP endpoint is reachable."""
        if self._http_parser is None:
            return False
        try:
            return self._http_parser.is_available()
        except Exception:
            return False

    # -- Internal backends --

    def _try_http(self, result: UnifiedFetchResult,
                  extra_query: Optional[Dict[str, str]] = None):
        """Attempt HTTP fetch and populate result."""
        result.http_tried = True
        if self._http_parser is None:
            result.errors.append("HTTP backend not available")
            return

        try:
            http_result = self._http_parser.fetch(extra_query=extra_query)
            if http_result.tables:
                result.tables = [
                    UnifiedTable.from_http_dict(d) for d in http_result.tables
                ]
                result.strategy_used = "http"
                result.http_ok = True
            else:
                errs = http_result.parse_errors or []
                if http_result.raw_response and http_result.raw_response.error:
                    errs.append(http_result.raw_response.error)
                result.errors.extend(errs or ["HTTP returned no tables"])
        except Exception as exc:
            result.errors.append(f"HTTP error: {exc}")

    def _try_ocr(self, result: UnifiedFetchResult, image):
        """Attempt OCR scan and populate result."""
        result.ocr_tried = True
        if self._ocr_scanner is None:
            result.errors.append("OCR backend not available")
            return

        try:
            ocr_result = self._ocr_scanner.scan_image(image)
            if ocr_result.tables:
                result.tables = [
                    UnifiedTable.from_ocr_table(t, i)
                    for i, t in enumerate(ocr_result.tables)
                ]
                result.strategy_used = "ocr"
                result.ocr_ok = True
            else:
                if ocr_result.error:
                    result.errors.append(f"OCR: {ocr_result.error}")
                else:
                    result.errors.append("OCR found no tables")
        except Exception as exc:
            result.errors.append(f"OCR error: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Lobby HTTP Parser — unified fetch")
    parser.add_argument("--strategy", choices=[s.value for s in FetchStrategy],
                        default="auto", help="Fetch strategy")
    parser.add_argument("--backend", default="generic",
                        help="HTTP backend: pokerstars, ggpoker, winamax, generic")
    parser.add_argument("--proxy", default=None, help="Proxy URL")
    parser.add_argument("--image", default=None, help="Lobby screenshot for OCR")

    args = parser.parse_args()

    fetcher = LobbyFetcher(
        strategy=FetchStrategy(args.strategy),
        http_backend=args.backend,
        http_proxy=args.proxy,
    )

    image_input = args.image
    result = fetcher.fetch(image=image_input)

    print(result.summary())
    if not result.ok:
        print("\nNo tables found. Ensure the poker client is running or provide a screenshot.")
