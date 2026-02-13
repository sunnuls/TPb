"""
Lobby HTTP Parser — Phase 2 of lobby_scanner.md.

HTTP-based fallback for fetching lobby data when OCR is unavailable or
too slow.  If a poker room exposes a local/remote API (hand history server,
internal REST endpoint, third-party tracker API) this module can pull
structured table data directly.

Pipeline:
  1. Build request (URL, headers, query params)
  2. Send via throttled HTTP client (respects rate-limits)
  3. Parse response (JSON or HTML)
  4. Map to LobbyTable dicts

Features:
  - Configurable endpoint presets (PokerStars, GGPoker, generic)
  - JSON / HTML response parsers
  - Built-in rate-limiter (token-bucket)
  - Retry with exponential back-off
  - Proxy support
  - Request signing / auth headers
  - Graceful degradation on network errors

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import hashlib
import html.parser
import json
import logging
import re
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional deps
# ---------------------------------------------------------------------------

try:
    import httpx

    HTTPX_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    HTTPX_AVAILABLE = False

try:
    import requests as _requests_lib

    REQUESTS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    REQUESTS_AVAILABLE = False


def _http_available() -> bool:
    return HTTPX_AVAILABLE or REQUESTS_AVAILABLE


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class RoomBackend(str, Enum):
    """Supported poker room API backends."""

    POKERSTARS = "pokerstars"
    GGPOKER = "ggpoker"
    WINAMAX = "winamax"
    GENERIC = "generic"


@dataclass
class EndpointConfig:
    """Configuration for a single API endpoint.

    Attributes:
        base_url:    Root URL  (e.g. ``http://127.0.0.1:26652``)
        path:        Path appended to *base_url*  (e.g. ``/api/lobby``)
        method:      HTTP method (GET | POST)
        headers:     Extra headers
        query:       Default query parameters
        body:        Default body (for POST)
        response_format: ``json`` | ``html`` | ``text``
        auth_type:   ``none`` | ``bearer`` | ``basic`` | ``hmac``
        auth_token:  Token / password for auth
    """

    base_url: str = "http://127.0.0.1:26652"
    path: str = "/api/lobby"
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    response_format: str = "json"  # json | html | text
    auth_type: str = "none"  # none | bearer | basic | hmac
    auth_token: str = ""
    timeout_seconds: float = 10.0


# -- Presets ----------------------------------------------------------------

ENDPOINT_PRESETS: Dict[RoomBackend, EndpointConfig] = {
    RoomBackend.POKERSTARS: EndpointConfig(
        base_url="http://127.0.0.1:26652",
        path="/api/lobby/tables",
        method="GET",
        query={"format": "json", "game": "NLHE"},
        response_format="json",
    ),
    RoomBackend.GGPOKER: EndpointConfig(
        base_url="http://127.0.0.1:9090",
        path="/lobby/cashgames",
        method="GET",
        query={"type": "cash"},
        response_format="json",
    ),
    RoomBackend.WINAMAX: EndpointConfig(
        base_url="http://127.0.0.1:20000",
        path="/api/tables",
        method="GET",
        response_format="json",
    ),
    RoomBackend.GENERIC: EndpointConfig(
        base_url="http://127.0.0.1:8080",
        path="/lobby",
        method="GET",
        response_format="json",
    ),
}


@dataclass
class HTTPResponse:
    """Wrapper around an HTTP response for uniform handling."""

    status_code: int = 0
    body: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and self.error is None


@dataclass
class LobbyHTTPResult:
    """Aggregate result of a lobby HTTP fetch + parse cycle."""

    tables: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Optional[HTTPResponse] = None
    backend: RoomBackend = RoomBackend.GENERIC
    parse_errors: List[str] = field(default_factory=list)
    total_time_ms: float = 0.0
    from_cache: bool = False


# ---------------------------------------------------------------------------
# Rate limiter (token-bucket)
# ---------------------------------------------------------------------------


class TokenBucketLimiter:
    """Thread-safe token-bucket rate limiter.

    Parameters:
        rate:       tokens added per second
        capacity:   maximum bucket size
    """

    def __init__(self, rate: float = 2.0, capacity: int = 5):
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Block until a token is available (or *timeout* expires).

        Returns ``True`` if a token was acquired.
        """
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))

    @property
    def tokens(self) -> float:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            return min(self._capacity, self._tokens + elapsed * self._rate)

    def reset(self):
        with self._lock:
            self._tokens = float(self._capacity)
            self._last = time.monotonic()


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _retry_with_backoff(
    fn: Callable[[], HTTPResponse],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
) -> HTTPResponse:
    """Call *fn* up to *max_retries* times with exponential back-off."""
    last_resp = HTTPResponse(error="no attempts made")
    delay = base_delay
    for attempt in range(max_retries + 1):
        resp = fn()
        if resp.ok:
            return resp
        last_resp = resp

        # Don't retry on 4xx client errors (except 429)
        if 400 <= resp.status_code < 500 and resp.status_code != 429:
            return resp

        if attempt < max_retries:
            logger.debug(
                "Retry %d/%d after %.1fs (status=%s err=%s)",
                attempt + 1,
                max_retries,
                delay,
                resp.status_code,
                resp.error,
            )
            time.sleep(delay)
            delay = min(delay * 2, max_delay)

    return last_resp


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------


class _SimpleHTMLTableParser(html.parser.HTMLParser):
    """Minimal HTML table parser — extracts rows from the first <table>."""

    def __init__(self):
        super().__init__()
        self.rows: List[List[str]] = []
        self._current_row: List[str] = []
        self._in_td = False
        self._in_table = False
        self._cell_text = ""

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._current_row = []
        elif tag in ("td", "th") and self._in_table:
            self._in_td = True
            self._cell_text = ""

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in ("td", "th") and self._in_td:
            self._current_row.append(self._cell_text.strip())
            self._in_td = False
        elif tag == "tr" and self._in_table:
            if self._current_row:
                self.rows.append(self._current_row)
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data: str):
        if self._in_td:
            self._cell_text += data


def parse_json_lobby(body: str, backend: RoomBackend) -> Tuple[List[Dict], List[str]]:
    """Parse a JSON lobby response into LobbyTable dicts.

    Returns (tables, errors).
    """
    errors: List[str] = []
    tables: List[Dict] = []

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        return [], [f"JSON decode error: {exc}"]

    # Normalise — the JSON may be a list or have a 'tables' / 'data' key
    items: List[Dict] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("tables", "data", "results", "lobbies", "cashgames", "items"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        if not items and "table_id" in data:
            items = [data]

    for i, raw in enumerate(items):
        try:
            table = _map_json_row(raw, i, backend)
            tables.append(table)
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    return tables, errors


def _map_json_row(raw: Dict, idx: int, backend: RoomBackend) -> Dict:
    """Map a raw JSON dict to a standardised LobbyTable dict."""
    # Try many possible key names — poker rooms vary
    def _get(*keys, default=None):
        for k in keys:
            if k in raw:
                return raw[k]
        return default

    table_id = str(_get("table_id", "id", "tableId", "tid", default=f"http_{idx + 1:03d}"))
    table_name = str(_get("table_name", "name", "tableName", "title", default=f"Table {idx + 1}"))
    game_type = str(_get("game_type", "gameType", "game", "type", default="NLHE"))
    stakes_raw = _get("stakes", "blinds", "limit", "stakes_label", default="0/0")
    stakes = _normalise_stakes(str(stakes_raw))

    occupied = int(_get("players", "playerCount", "occupied_seats",
                        "players_seated", "seated", default=0))
    max_seats = int(_get("max_seats", "maxSeats", "seats", "tableSize", default=9))
    avg_pot = float(_get("avg_pot", "averagePot", "average_pot", "avgPot", default=0.0))
    hhr = int(_get("hands_per_hour", "handsPerHour", "hands_hr", "speed", default=0))
    wait = int(_get("waitlist", "waiting", "wait", "queue", default=0))

    return {
        "table_id": table_id,
        "table_name": table_name,
        "game_type": game_type,
        "stakes": stakes,
        "players_seated": occupied,
        "max_seats": max_seats,
        "avg_pot": avg_pot,
        "hands_per_hour": hhr,
        "waiting": wait,
    }


def parse_html_lobby(body: str) -> Tuple[List[Dict], List[str]]:
    """Parse an HTML response containing a lobby <table>.

    Returns (tables, errors).
    """
    errors: List[str] = []
    parser = _SimpleHTMLTableParser()
    try:
        parser.feed(body)
    except Exception as exc:
        return [], [f"HTML parse error: {exc}"]

    if len(parser.rows) < 2:
        return [], ["HTML table not found or too few rows"]

    # First row = header
    header = [h.lower().strip() for h in parser.rows[0]]
    tables: List[Dict] = []

    for i, row in enumerate(parser.rows[1:]):
        if len(row) != len(header):
            errors.append(f"Row {i}: column count mismatch ({len(row)} vs {len(header)})")
            continue
        raw = dict(zip(header, row))
        try:
            table = _map_html_row(raw, i)
            tables.append(table)
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    return tables, errors


def _map_html_row(raw: Dict, idx: int) -> Dict:
    """Map a header-keyed dict from HTML to a standard LobbyTable dict."""

    def _get(*keys, default=None):
        for k in keys:
            if k in raw:
                return raw[k]
        return default

    table_name = _get("table name", "name", "table", default=f"Table {idx + 1}")
    stakes_raw = _get("stakes", "blinds", "limit", default="0/0")
    stakes = _normalise_stakes(str(stakes_raw))

    players_raw = str(_get("players", "plrs", "seated", default="0/9"))
    occ, mx = _parse_player_string(players_raw)

    avg_raw = _get("avg pot", "average pot", "avgpot", default="0")
    avg_pot = _parse_float(str(avg_raw))

    hhr_raw = _get("h/hr", "hands/hr", "speed", default="0")
    hhr = int(_parse_float(str(hhr_raw)))

    wait_raw = _get("wait", "waitlist", "queue", default="0")
    wait = int(_parse_float(str(wait_raw)))

    return {
        "table_id": f"http_{idx + 1:03d}",
        "table_name": str(table_name),
        "game_type": str(_get("game", "type", "game type", default="NLHE")),
        "stakes": stakes,
        "players_seated": occ,
        "max_seats": mx,
        "avg_pot": avg_pot,
        "hands_per_hour": hhr,
        "waiting": wait,
    }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _normalise_stakes(raw: str) -> str:
    """Normalise various stake formats to 'SB/BB'."""
    cleaned = raw.replace("$", "").replace("€", "").replace("\\", "/")
    cleaned = cleaned.replace("|", "/").strip()
    m = re.search(r"(\d+\.?\d*)\s*/\s*(\d+\.?\d*)", cleaned)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return cleaned


def _parse_player_string(raw: str) -> Tuple[int, int]:
    """Parse '5/9' → (5, 9)."""
    m = re.search(r"(\d+)\s*/\s*(\d+)", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    digits = re.findall(r"\d+", raw)
    if digits:
        return int(digits[0]), 9
    return 0, 9


def _parse_float(raw: str) -> float:
    cleaned = raw.replace("$", "").replace("€", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _apply_auth(
    endpoint: EndpointConfig, headers: Dict[str, str], body_bytes: bytes = b""
) -> Dict[str, str]:
    """Apply auth to headers based on endpoint config."""
    if endpoint.auth_type == "bearer" and endpoint.auth_token:
        headers["Authorization"] = f"Bearer {endpoint.auth_token}"
    elif endpoint.auth_type == "basic" and endpoint.auth_token:
        import base64

        encoded = base64.b64encode(endpoint.auth_token.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif endpoint.auth_type == "hmac" and endpoint.auth_token:
        ts = str(int(time.time()))
        payload = ts.encode() + body_bytes
        sig = hashlib.sha256(endpoint.auth_token.encode() + payload).hexdigest()
        headers["X-Timestamp"] = ts
        headers["X-Signature"] = sig
    return headers


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class LobbyHTTPParser:
    """HTTP-based lobby data fetcher + parser.

    Usage::

        parser = LobbyHTTPParser(backend=RoomBackend.POKERSTARS)
        result = parser.fetch()
        for t in result.tables:
            print(t["table_name"], t["stakes"], t["players_seated"])

    When no live server is available the class returns empty results
    without raising exceptions (graceful degradation for OCR fallback).
    """

    def __init__(
        self,
        backend: RoomBackend = RoomBackend.GENERIC,
        endpoint: Optional[EndpointConfig] = None,
        rate_limit: float = 2.0,          # requests per second
        rate_capacity: int = 5,           # burst capacity
        max_retries: int = 3,
        proxy: Optional[str] = None,      # e.g. "http://user:pass@proxy:8080"
        cache_ttl_seconds: float = 5.0,   # cache responses for N seconds
    ):
        self.backend = backend
        self.endpoint = endpoint or ENDPOINT_PRESETS.get(backend, ENDPOINT_PRESETS[RoomBackend.GENERIC])
        self.max_retries = max_retries
        self.proxy = proxy
        self.cache_ttl = cache_ttl_seconds

        self._limiter = TokenBucketLimiter(rate=rate_limit, capacity=rate_capacity)
        self._cache: Optional[Tuple[float, LobbyHTTPResult]] = None
        self._lock = threading.Lock()

        logger.info(
            "LobbyHTTPParser initialised — backend=%s url=%s proxy=%s",
            backend.value,
            urljoin(self.endpoint.base_url, self.endpoint.path),
            "yes" if proxy else "no",
        )

    # -- public API ----------------------------------------------------------

    def fetch(self, extra_query: Optional[Dict[str, str]] = None) -> LobbyHTTPResult:
        """Fetch and parse lobby data.

        Steps:
          1. Check cache
          2. Acquire rate-limit token
          3. Build request
          4. Send with retry
          5. Parse response
          6. Cache result

        Returns:
            ``LobbyHTTPResult`` with parsed tables (may be empty on error).
        """
        t0 = time.perf_counter()

        # 1. Cache hit?
        cached = self._check_cache()
        if cached is not None:
            cached.total_time_ms = (time.perf_counter() - t0) * 1000
            return cached

        # 2. Rate limit
        if not self._limiter.acquire(timeout=15.0):
            return LobbyHTTPResult(
                backend=self.backend,
                raw_response=HTTPResponse(error="Rate limit timeout"),
                total_time_ms=(time.perf_counter() - t0) * 1000,
            )

        # 3. Build & send
        resp = _retry_with_backoff(
            lambda: self._do_request(extra_query),
            max_retries=self.max_retries,
        )

        # 4. Parse
        tables: List[Dict] = []
        parse_errors: List[str] = []

        if resp.ok:
            tables, parse_errors = self._parse(resp.body)
        else:
            parse_errors.append(
                f"HTTP {resp.status_code}: {resp.error or 'request failed'}"
            )

        result = LobbyHTTPResult(
            tables=tables,
            raw_response=resp,
            backend=self.backend,
            parse_errors=parse_errors,
            total_time_ms=(time.perf_counter() - t0) * 1000,
        )

        # 5. Cache
        if resp.ok:
            self._set_cache(result)

        return result

    def is_available(self) -> bool:
        """Quick health check — try to reach the endpoint.

        Returns ``True`` if the server responds with 2xx within 3 seconds.
        """
        try:
            resp = self._do_request(timeout_override=3.0)
            return resp.ok
        except Exception:
            return False

    @property
    def limiter(self) -> TokenBucketLimiter:
        """Expose the rate limiter for external control."""
        return self._limiter

    # -- internal ------------------------------------------------------------

    def _do_request(
        self,
        extra_query: Optional[Dict[str, str]] = None,
        timeout_override: Optional[float] = None,
    ) -> HTTPResponse:
        """Execute a single HTTP request (no retry)."""
        ep = self.endpoint
        url = urljoin(ep.base_url, ep.path)

        # Query string
        qs = dict(ep.query)
        if extra_query:
            qs.update(extra_query)
        if qs:
            url = url + "?" + urlencode(qs)

        # Headers
        headers = {"Accept": "application/json", "User-Agent": "LobbyHTTPParser/1.0"}
        headers.update(ep.headers)

        # Body
        body_bytes = b""
        if ep.body is not None and ep.method.upper() == "POST":
            body_bytes = json.dumps(ep.body).encode()
            headers["Content-Type"] = "application/json"

        # Auth
        headers = _apply_auth(ep, headers, body_bytes)

        timeout = timeout_override or ep.timeout_seconds

        t0 = time.perf_counter()

        # --- httpx ---
        if HTTPX_AVAILABLE:
            return self._request_httpx(url, ep.method, headers, body_bytes, timeout)

        # --- requests ---
        if REQUESTS_AVAILABLE:
            return self._request_requests(url, ep.method, headers, body_bytes, timeout)

        # --- stdlib fallback ---
        return self._request_urllib(url, ep.method, headers, body_bytes, timeout)

    def _request_httpx(self, url, method, headers, body, timeout) -> HTTPResponse:
        try:
            client_kwargs: Dict[str, Any] = {"timeout": timeout, "follow_redirects": True}
            if self.proxy:
                client_kwargs["proxies"] = {"all://": self.proxy}
            with httpx.Client(**client_kwargs) as client:
                t0 = time.perf_counter()
                if method.upper() == "POST":
                    r = client.post(url, headers=headers, content=body)
                else:
                    r = client.get(url, headers=headers)
                elapsed = (time.perf_counter() - t0) * 1000
                return HTTPResponse(
                    status_code=r.status_code,
                    body=r.text,
                    headers=dict(r.headers),
                    elapsed_ms=elapsed,
                )
        except Exception as exc:
            return HTTPResponse(error=str(exc))

    def _request_requests(self, url, method, headers, body, timeout) -> HTTPResponse:
        try:
            proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
            t0 = time.perf_counter()
            if method.upper() == "POST":
                r = _requests_lib.post(
                    url, headers=headers, data=body, timeout=timeout, proxies=proxies
                )
            else:
                r = _requests_lib.get(
                    url, headers=headers, timeout=timeout, proxies=proxies
                )
            elapsed = (time.perf_counter() - t0) * 1000
            return HTTPResponse(
                status_code=r.status_code,
                body=r.text,
                headers=dict(r.headers),
                elapsed_ms=elapsed,
            )
        except Exception as exc:
            return HTTPResponse(error=str(exc))

    def _request_urllib(self, url, method, headers, body, timeout) -> HTTPResponse:
        """Pure stdlib fallback using ``urllib``."""
        import urllib.request
        import urllib.error

        req = urllib.request.Request(url, method=method.upper(), headers=headers)
        if body:
            req.data = body
        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                elapsed = (time.perf_counter() - t0) * 1000
                return HTTPResponse(
                    status_code=resp.status,
                    body=text,
                    headers=dict(resp.headers),
                    elapsed_ms=elapsed,
                )
        except urllib.error.HTTPError as exc:
            return HTTPResponse(status_code=exc.code, error=str(exc))
        except Exception as exc:
            return HTTPResponse(error=str(exc))

    # -- parsing dispatch ----------------------------------------------------

    def _parse(self, body: str) -> Tuple[List[Dict], List[str]]:
        fmt = self.endpoint.response_format.lower()
        if fmt == "json":
            return parse_json_lobby(body, self.backend)
        elif fmt == "html":
            return parse_html_lobby(body)
        else:
            # Try JSON first, fall back to HTML
            tables, errs = parse_json_lobby(body, self.backend)
            if tables:
                return tables, errs
            return parse_html_lobby(body)

    # -- caching -------------------------------------------------------------

    def _check_cache(self) -> Optional[LobbyHTTPResult]:
        with self._lock:
            if self._cache is None:
                return None
            ts, result = self._cache
            if time.monotonic() - ts > self.cache_ttl:
                self._cache = None
                return None
            return LobbyHTTPResult(
                tables=list(result.tables),
                raw_response=result.raw_response,
                backend=result.backend,
                parse_errors=list(result.parse_errors),
                total_time_ms=result.total_time_ms,
                from_cache=True,
            )

    def _set_cache(self, result: LobbyHTTPResult):
        with self._lock:
            self._cache = (time.monotonic(), result)

    def clear_cache(self):
        with self._lock:
            self._cache = None
