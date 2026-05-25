#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for lobby_scanner.md — Phase 2: HTTP fallback.

Covers:
- UnifiedTable data model (from_http_dict, from_ocr_table)
- UnifiedFetchResult properties & filtering
- FetchStrategy enum
- LobbyFetcher — strategy-based routing
- LobbyFetcher — HTTP-only, OCR-only, AUTO fallback
- Integration with launcher/vision/lobby_http_parser.py parsers
- Token-bucket rate limiter
- JSON and HTML lobby parsers
"""
from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lobby_http_parser import (
    FetchStrategy,
    UnifiedTable,
    UnifiedFetchResult,
    LobbyFetcher,
    HAS_HTTP_BACKEND,
    HAS_OCR_BACKEND,
)

# Try importing internals from launcher backend
try:
    from launcher.vision.lobby_http_parser import (
        TokenBucketLimiter,
        HTTPResponse,
        LobbyHTTPResult,
        parse_json_lobby,
        parse_html_lobby,
        RoomBackend,
        EndpointConfig,
        _normalise_stakes,
        _parse_player_string,
        _retry_with_backoff,
        _apply_auth,
        _SimpleHTMLTableParser,
    )
    _HAS_INTERNALS = True
except (ImportError, SyntaxError, Exception):
    _HAS_INTERNALS = False


# ===========================================================================
# Test UnifiedTable
# ===========================================================================

class TestUnifiedTable(unittest.TestCase):
    """UnifiedTable data model."""

    def test_from_http_dict(self):
        d = {
            "table_id": "t1",
            "table_name": "Mercury",
            "stakes": "0.01/0.02",
            "game_type": "NLHE",
            "players_seated": 5,
            "max_seats": 9,
            "avg_pot": 1.23,
            "hands_per_hour": 60,
            "waiting": 2,
        }
        t = UnifiedTable.from_http_dict(d)
        self.assertEqual(t.table_id, "t1")
        self.assertEqual(t.name, "Mercury")
        self.assertEqual(t.players, 5)
        self.assertEqual(t.max_players, 9)
        self.assertEqual(t.source, "http")
        self.assertAlmostEqual(t.occupancy, 5 / 9, places=3)
        self.assertFalse(t.is_full)
        self.assertEqual(t.free_seats, 4)

    def test_from_http_dict_full_table(self):
        d = {"players_seated": 9, "max_seats": 9, "table_name": "Full"}
        t = UnifiedTable.from_http_dict(d)
        self.assertTrue(t.is_full)
        self.assertEqual(t.free_seats, 0)

    def test_from_ocr_table(self):
        """Create from an OCR LobbyTable-like object."""
        mock_t = MagicMock()
        mock_t.name = "Venus"
        mock_t.stakes = "$0.05/$0.10"
        mock_t.game_type = "NL Hold'em"
        mock_t.players = 4
        mock_t.max_players = 6
        mock_t.raw_text = "Venus $0.05/$0.10 4/6"

        t = UnifiedTable.from_ocr_table(mock_t, idx=3)
        self.assertEqual(t.table_id, "ocr_003")
        self.assertEqual(t.name, "Venus")
        self.assertEqual(t.source, "ocr")
        self.assertEqual(t.free_seats, 2)

    def test_defaults(self):
        t = UnifiedTable()
        self.assertEqual(t.occupancy, 0.0)
        self.assertFalse(t.is_full)
        self.assertEqual(t.free_seats, 0)


# ===========================================================================
# Test UnifiedFetchResult
# ===========================================================================

class TestUnifiedFetchResult(unittest.TestCase):
    """UnifiedFetchResult properties and methods."""

    def _make_result(self) -> UnifiedFetchResult:
        return UnifiedFetchResult(
            tables=[
                UnifiedTable(name="A", players=3, max_players=6, source="http"),
                UnifiedTable(name="B", players=6, max_players=6, source="http"),
                UnifiedTable(name="C", players=0, max_players=9, source="ocr"),
            ],
            strategy_used="auto",
            http_tried=True,
            http_ok=True,
            elapsed_ms=50.0,
        )

    def test_table_count(self):
        self.assertEqual(self._make_result().table_count, 3)

    def test_ok(self):
        self.assertTrue(self._make_result().ok)
        self.assertFalse(UnifiedFetchResult().ok)

    def test_available_tables(self):
        r = self._make_result()
        avail = r.available_tables(min_seats=1)
        names = [t.name for t in avail]
        self.assertIn("A", names)
        self.assertIn("C", names)
        self.assertNotIn("B", names)

    def test_summary(self):
        s = self._make_result().summary()
        self.assertIn("3 tables", s)
        self.assertIn("auto", s)


# ===========================================================================
# Test FetchStrategy enum
# ===========================================================================

class TestFetchStrategy(unittest.TestCase):
    def test_values(self):
        self.assertEqual(FetchStrategy.AUTO, "auto")
        self.assertEqual(FetchStrategy.HTTP_ONLY, "http_only")
        self.assertEqual(FetchStrategy.OCR_ONLY, "ocr_only")
        self.assertEqual(FetchStrategy.HTTP_THEN_OCR, "http_then_ocr")
        self.assertEqual(FetchStrategy.OCR_THEN_HTTP, "ocr_then_http")

    def test_from_string(self):
        self.assertEqual(FetchStrategy("auto"), FetchStrategy.AUTO)


# ===========================================================================
# Test LobbyFetcher — strategy routing
# ===========================================================================

class TestLobbyFetcherStrategy(unittest.TestCase):
    """Test LobbyFetcher picks correct backends based on strategy."""

    def test_auto_strategy_has_both(self):
        fetcher = LobbyFetcher(strategy=FetchStrategy.AUTO)
        # At minimum one backend should be present
        self.assertTrue(fetcher.has_http or fetcher.has_ocr)

    def test_ocr_only_no_http(self):
        fetcher = LobbyFetcher(strategy=FetchStrategy.OCR_ONLY)
        self.assertIsNone(fetcher._http_parser)

    def test_http_only_no_ocr(self):
        fetcher = LobbyFetcher(strategy=FetchStrategy.HTTP_ONLY)
        self.assertIsNone(fetcher._ocr_scanner)

    def test_fetch_ocr_only_no_image(self):
        """OCR_ONLY without image → error."""
        fetcher = LobbyFetcher(strategy=FetchStrategy.OCR_ONLY)
        result = fetcher.fetch(image=None)
        self.assertFalse(result.ok)
        self.assertTrue(any("no image" in e.lower() or "not available" in e.lower()
                            for e in result.errors))

    @unittest.skipUnless(HAS_OCR_BACKEND, "OCR backend not available")
    def test_fetch_ocr_method(self):
        """fetch_ocr with a mock image → exercises OCR path."""
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not available")

        fetcher = LobbyFetcher(strategy=FetchStrategy.OCR_ONLY)
        img = np.full((200, 400, 3), 40, dtype=np.uint8)
        result = fetcher.fetch_ocr(img)
        self.assertIsInstance(result, UnifiedFetchResult)
        self.assertTrue(result.ocr_tried)

    def test_fetch_http_method(self):
        """fetch_http exercises HTTP path (will fail without server)."""
        fetcher = LobbyFetcher(strategy=FetchStrategy.HTTP_ONLY)
        result = fetcher.fetch_http()
        self.assertIsInstance(result, UnifiedFetchResult)
        self.assertTrue(result.http_tried)


# ===========================================================================
# Test LobbyFetcher with mocked backends
# ===========================================================================

class TestLobbyFetcherMocked(unittest.TestCase):
    """Test LobbyFetcher with mocked HTTP and OCR backends."""

    def _make_fetcher(self) -> LobbyFetcher:
        fetcher = LobbyFetcher(strategy=FetchStrategy.AUTO)
        return fetcher

    def test_http_success_skips_ocr(self):
        """When HTTP succeeds, OCR should not be tried."""
        fetcher = self._make_fetcher()

        # Mock HTTP parser
        mock_http = MagicMock()
        mock_http_result = MagicMock()
        mock_http_result.tables = [
            {"table_id": "1", "table_name": "T1", "stakes": "1/2",
             "game_type": "NLHE", "players_seated": 5, "max_seats": 9,
             "avg_pot": 0, "hands_per_hour": 0, "waiting": 0}
        ]
        mock_http_result.parse_errors = []
        mock_http_result.raw_response = MagicMock(error=None)
        mock_http.fetch.return_value = mock_http_result
        fetcher._http_parser = mock_http

        result = fetcher.fetch()
        self.assertTrue(result.ok)
        self.assertTrue(result.http_ok)
        self.assertFalse(result.ocr_tried)
        self.assertEqual(result.tables[0].source, "http")

    def test_http_fails_falls_back_to_ocr(self):
        """When HTTP fails and image provided, OCR is tried."""
        fetcher = self._make_fetcher()

        # Mock HTTP parser — fails
        mock_http = MagicMock()
        mock_http_result = MagicMock()
        mock_http_result.tables = []
        mock_http_result.parse_errors = ["server down"]
        mock_http_result.raw_response = MagicMock(error="connection refused")
        mock_http.fetch.return_value = mock_http_result
        fetcher._http_parser = mock_http

        # Mock OCR scanner — succeeds
        mock_ocr = MagicMock()
        mock_ocr_result = MagicMock()
        mock_ocr_table = MagicMock()
        mock_ocr_table.name = "OcrTable"
        mock_ocr_table.stakes = "$1/$2"
        mock_ocr_table.game_type = "NL"
        mock_ocr_table.players = 3
        mock_ocr_table.max_players = 6
        mock_ocr_table.raw_text = "OcrTable $1/$2 3/6"
        mock_ocr_result.tables = [mock_ocr_table]
        mock_ocr_result.error = ""
        mock_ocr.scan_image.return_value = mock_ocr_result
        fetcher._ocr_scanner = mock_ocr

        result = fetcher.fetch(image="fake_image.png")
        self.assertTrue(result.ok)
        self.assertTrue(result.ocr_ok)
        self.assertEqual(result.strategy_used, "ocr")
        self.assertEqual(result.tables[0].name, "OcrTable")

    def test_ocr_then_http_strategy(self):
        """OCR_THEN_HTTP: OCR tried first."""
        fetcher = LobbyFetcher(strategy=FetchStrategy.OCR_THEN_HTTP)

        # Mock OCR — succeeds
        mock_ocr = MagicMock()
        mock_ocr_result = MagicMock()
        t = MagicMock()
        t.name = "OcrFirst"
        t.stakes = "$0.5/$1"
        t.game_type = "NL"
        t.players = 2
        t.max_players = 6
        t.raw_text = "OcrFirst"
        mock_ocr_result.tables = [t]
        mock_ocr_result.error = ""
        mock_ocr.scan_image.return_value = mock_ocr_result
        fetcher._ocr_scanner = mock_ocr

        result = fetcher.fetch(image="img.png")
        self.assertTrue(result.ocr_tried)
        self.assertTrue(result.ocr_ok)
        self.assertFalse(result.http_tried)
        self.assertEqual(result.strategy_used, "ocr")


# ===========================================================================
# Test launcher/vision internals (JSON/HTML parsers, rate limiter)
# ===========================================================================

@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestHTTPBackendInternals(unittest.TestCase):
    """Test the underlying HTTP parser components."""

    def test_parse_json_list(self):
        body = json.dumps([
            {"table_name": "A", "stakes": "1/2", "players": 5, "max_seats": 9},
            {"table_name": "B", "stakes": "2/5", "players": 3, "max_seats": 6},
        ])
        tables, errors = parse_json_lobby(body, RoomBackend.GENERIC)
        self.assertEqual(len(tables), 2)
        self.assertEqual(errors, [])
        self.assertEqual(tables[0]["table_name"], "A")

    def test_parse_json_dict_with_tables_key(self):
        body = json.dumps({"tables": [
            {"name": "X", "blinds": "0.5/1", "playerCount": 4, "maxSeats": 6}
        ]})
        tables, errors = parse_json_lobby(body, RoomBackend.POKERSTARS)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["table_name"], "X")

    def test_parse_json_invalid(self):
        tables, errors = parse_json_lobby("not json!", RoomBackend.GENERIC)
        self.assertEqual(tables, [])
        self.assertTrue(len(errors) > 0)

    def test_parse_html_table(self):
        html = """
        <table>
            <tr><th>Table Name</th><th>Stakes</th><th>Players</th></tr>
            <tr><td>Alpha</td><td>$1/$2</td><td>5/9</td></tr>
            <tr><td>Beta</td><td>$2/$5</td><td>3/6</td></tr>
        </table>
        """
        tables, errors = parse_html_lobby(html)
        self.assertEqual(len(tables), 2)
        self.assertEqual(tables[0]["table_name"], "Alpha")

    def test_parse_html_no_table(self):
        tables, errors = parse_html_lobby("<p>No table here</p>")
        self.assertEqual(tables, [])

    def test_normalise_stakes(self):
        self.assertEqual(_normalise_stakes("$0.01/$0.02"), "0.01/0.02")
        self.assertEqual(_normalise_stakes("1|2"), "1/2")

    def test_parse_player_string(self):
        self.assertEqual(_parse_player_string("5/9"), (5, 9))
        self.assertEqual(_parse_player_string("3"), (3, 9))


@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestTokenBucketLimiter(unittest.TestCase):
    """Test rate limiter."""

    def test_acquire_immediately(self):
        limiter = TokenBucketLimiter(rate=10.0, capacity=5)
        self.assertTrue(limiter.acquire(timeout=0.1))

    def test_acquire_drains_capacity(self):
        limiter = TokenBucketLimiter(rate=0.1, capacity=3)
        for _ in range(3):
            self.assertTrue(limiter.acquire(timeout=0.01))
        # 4th should fail quickly (rate is low)
        self.assertFalse(limiter.acquire(timeout=0.05))

    def test_tokens_property(self):
        limiter = TokenBucketLimiter(rate=10.0, capacity=5)
        self.assertGreater(limiter.tokens, 0)

    def test_reset(self):
        limiter = TokenBucketLimiter(rate=0.1, capacity=2)
        limiter.acquire(timeout=0.01)
        limiter.acquire(timeout=0.01)
        limiter.reset()
        self.assertTrue(limiter.acquire(timeout=0.01))


@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestRetryWithBackoff(unittest.TestCase):
    """Test retry helper."""

    def test_immediate_success(self):
        fn = lambda: HTTPResponse(status_code=200, body="{}")
        resp = _retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        self.assertTrue(resp.ok)

    def test_retries_on_500(self):
        call_count = [0]

        def fn():
            call_count[0] += 1
            if call_count[0] < 3:
                return HTTPResponse(status_code=500, error="server error")
            return HTTPResponse(status_code=200, body="{}")

        resp = _retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        self.assertTrue(resp.ok)
        self.assertEqual(call_count[0], 3)

    def test_no_retry_on_404(self):
        call_count = [0]

        def fn():
            call_count[0] += 1
            return HTTPResponse(status_code=404, error="not found")

        resp = _retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        self.assertFalse(resp.ok)
        self.assertEqual(call_count[0], 1)  # No retries for 4xx (except 429)


@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestApplyAuth(unittest.TestCase):
    """Test auth header generation."""

    def test_bearer_auth(self):
        ep = EndpointConfig(auth_type="bearer", auth_token="mytoken123")
        headers = _apply_auth(ep, {})
        self.assertEqual(headers["Authorization"], "Bearer mytoken123")

    def test_basic_auth(self):
        ep = EndpointConfig(auth_type="basic", auth_token="user:pass")
        headers = _apply_auth(ep, {})
        self.assertTrue(headers["Authorization"].startswith("Basic "))

    def test_hmac_auth(self):
        ep = EndpointConfig(auth_type="hmac", auth_token="secret")
        headers = _apply_auth(ep, {})
        self.assertIn("X-Timestamp", headers)
        self.assertIn("X-Signature", headers)

    def test_no_auth(self):
        ep = EndpointConfig(auth_type="none")
        headers = _apply_auth(ep, {"X-Existing": "val"})
        self.assertNotIn("Authorization", headers)
        self.assertEqual(headers["X-Existing"], "val")


@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestHTMLTableParser(unittest.TestCase):
    """Test the minimal HTML table parser."""

    def test_simple_table(self):
        html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        p = _SimpleHTMLTableParser()
        p.feed(html)
        self.assertEqual(len(p.rows), 2)
        self.assertEqual(p.rows[1], ["1", "2"])

    def test_no_table(self):
        p = _SimpleHTMLTableParser()
        p.feed("<div>nothing</div>")
        self.assertEqual(len(p.rows), 0)

    def test_multiple_rows(self):
        html = """<table>
            <tr><th>H1</th></tr>
            <tr><td>R1</td></tr>
            <tr><td>R2</td></tr>
            <tr><td>R3</td></tr>
        </table>"""
        p = _SimpleHTMLTableParser()
        p.feed(html)
        self.assertEqual(len(p.rows), 4)


# ===========================================================================
# Test HTTPResponse data model
# ===========================================================================

@unittest.skipUnless(_HAS_INTERNALS, "launcher.vision.lobby_http_parser not importable")
class TestHTTPResponse(unittest.TestCase):
    def test_ok_200(self):
        r = HTTPResponse(status_code=200, body="{}")
        self.assertTrue(r.ok)

    def test_not_ok_error(self):
        r = HTTPResponse(status_code=200, error="something wrong")
        self.assertFalse(r.ok)

    def test_not_ok_500(self):
        r = HTTPResponse(status_code=500)
        self.assertFalse(r.ok)


if __name__ == "__main__":
    unittest.main()
