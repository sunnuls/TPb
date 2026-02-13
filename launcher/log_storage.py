"""
Log Storage — Phase 2 of logs.md.

External storage backends for structured logs:
  1. **SQLiteLogStore** — file-based DB (zero dependencies, always available)
  2. **ElasticLogStore** — Elasticsearch / ELK stack (HTTP API)

Both implement the same ``LogStore`` interface so callers can
switch backends transparently.  A ``LogRouter`` multiplexes logs
to multiple stores simultaneously.

Usage::

    # SQLite (always works)
    store = SQLiteLogStore("logs/bot_logs.db")
    store.insert({"ts": "...", "level": "INFO", "msg": "Hello"})
    results = store.query(level="ERROR", limit=50)

    # Elasticsearch (if available)
    es = ElasticLogStore(url="http://localhost:9200", index="bot-logs")
    es.insert(record)

    # Router: write to both
    router = LogRouter([store, es])
    router.insert(record)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LogStore(ABC):
    """Abstract interface for log storage backends."""

    @abstractmethod
    def insert(self, record: Dict[str, Any]) -> bool:
        """Insert a single log record. Returns True on success."""
        ...

    @abstractmethod
    def insert_batch(self, records: List[Dict[str, Any]]) -> int:
        """Insert multiple records. Returns count inserted."""
        ...

    @abstractmethod
    def query(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        contains: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query stored records."""
        ...

    @abstractmethod
    def count(self, level: Optional[str] = None) -> int:
        """Count records, optionally filtered by level."""
        ...

    @abstractmethod
    def delete_older_than(self, days: int) -> int:
        """Delete records older than N days. Returns count deleted."""
        ...

    @abstractmethod
    def close(self):
        """Release resources."""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------


class SQLiteLogStore(LogStore):
    """File-based log storage using SQLite.

    Zero external dependencies.  Stores JSON records in a single table
    with indexed columns for fast filtering.

    Parameters:
        db_path:        path to SQLite database file
        table_name:     table name for log records
        wal_mode:       use WAL journal mode (better concurrency)
    """

    def __init__(
        self,
        db_path: str = "logs/bot_logs.db",
        table_name: str = "logs",
        wal_mode: bool = True,
    ):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._table = table_name
        self._lock = threading.Lock()

        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        if wal_mode:
            self._conn.execute("PRAGMA journal_mode=WAL")

        self._create_table()

    def _create_table(self):
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                ts      TEXT NOT NULL,
                level   TEXT NOT NULL DEFAULT 'INFO',
                logger  TEXT DEFAULT '',
                msg     TEXT DEFAULT '',
                data    TEXT DEFAULT '{{}}'
            )
        """)
        # Indexes for common queries
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self._table}_ts
            ON {self._table}(ts)
        """)
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self._table}_level
            ON {self._table}(level)
        """)
        self._conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self._table}_logger
            ON {self._table}(logger)
        """)
        self._conn.commit()

    # -- LogStore interface --------------------------------------------------

    def insert(self, record: Dict[str, Any]) -> bool:
        ts = record.get("ts", datetime.now().isoformat())
        level = record.get("level", "INFO")
        logger_name = record.get("logger", "")
        msg = record.get("msg", "")
        # Store the full record as JSON in the data column
        data = json.dumps(record, default=str, ensure_ascii=False)

        with self._lock:
            self._conn.execute(
                f"INSERT INTO {self._table} (ts, level, logger, msg, data) "
                f"VALUES (?, ?, ?, ?, ?)",
                (ts, level, logger_name, msg, data),
            )
            self._conn.commit()
        return True

    def insert_batch(self, records: List[Dict[str, Any]]) -> int:
        rows = []
        for rec in records:
            ts = rec.get("ts", datetime.now().isoformat())
            level = rec.get("level", "INFO")
            logger_name = rec.get("logger", "")
            msg = rec.get("msg", "")
            data = json.dumps(rec, default=str, ensure_ascii=False)
            rows.append((ts, level, logger_name, msg, data))

        with self._lock:
            self._conn.executemany(
                f"INSERT INTO {self._table} (ts, level, logger, msg, data) "
                f"VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            self._conn.commit()
        return len(rows)

    def query(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        contains: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        if level:
            clauses.append("level = ?")
            params.append(level)
        if logger_name:
            clauses.append("logger LIKE ?")
            params.append(f"{logger_name}%")
        if contains:
            clauses.append("msg LIKE ?")
            params.append(f"%{contains}%")
        if since:
            clauses.append("ts >= ?")
            params.append(since)
        if until:
            clauses.append("ts <= ?")
            params.append(until)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        sql = (
            f"SELECT data FROM {self._table} {where} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall()

        results = []
        for row in rows:
            try:
                rec = json.loads(row["data"])
                # Post-filter on arbitrary fields
                if fields:
                    if all(rec.get(k) == v for k, v in fields.items()):
                        results.append(rec)
                else:
                    results.append(rec)
            except (json.JSONDecodeError, KeyError):
                pass

        return results

    def count(self, level: Optional[str] = None) -> int:
        if level:
            sql = f"SELECT COUNT(*) FROM {self._table} WHERE level = ?"
            params: tuple = (level,)
        else:
            sql = f"SELECT COUNT(*) FROM {self._table}"
            params = ()

        with self._lock:
            cursor = self._conn.execute(sql, params)
            return cursor.fetchone()[0]

    def delete_older_than(self, days: int) -> int:
        cutoff = datetime.now()
        # Compute cutoff date
        from datetime import timedelta
        cutoff = (cutoff - timedelta(days=days)).isoformat()

        with self._lock:
            cursor = self._conn.execute(
                f"DELETE FROM {self._table} WHERE ts < ?", (cutoff,)
            )
            self._conn.commit()
            return cursor.rowcount

    def close(self):
        with self._lock:
            self._conn.close()

    @property
    def backend_name(self) -> str:
        return "sqlite"

    @property
    def is_available(self) -> bool:
        return True

    # -- Extra SQLite-specific methods ---------------------------------------

    def vacuum(self):
        """Reclaim disk space after deletes."""
        with self._lock:
            self._conn.execute("VACUUM")

    def table_size_bytes(self) -> int:
        """Return the database file size in bytes."""
        if self._path.exists():
            return self._path.stat().st_size
        return 0

    def count_by_level(self) -> Dict[str, int]:
        """Return {level: count}."""
        with self._lock:
            cursor = self._conn.execute(
                f"SELECT level, COUNT(*) as cnt FROM {self._table} GROUP BY level"
            )
            return {row["level"]: row["cnt"] for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# Elasticsearch backend
# ---------------------------------------------------------------------------


class ElasticLogStore(LogStore):
    """Elasticsearch / ELK log storage via HTTP API.

    Uses only stdlib ``urllib`` — no ``elasticsearch-py`` dependency.

    Parameters:
        url:        Elasticsearch base URL (e.g. http://localhost:9200)
        index:      index name (e.g. "bot-logs")
        auth:       optional (username, password) tuple
        timeout:    HTTP request timeout (seconds)
    """

    def __init__(
        self,
        url: str = "http://localhost:9200",
        index: str = "bot-logs",
        auth: Optional[Tuple[str, str]] = None,
        timeout: int = 5,
    ):
        self._url = url.rstrip("/")
        self._index = index
        self._auth = auth
        self._timeout = timeout
        self._available: Optional[bool] = None

    # -- HTTP helpers --------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make an HTTP request to Elasticsearch."""
        url = f"{self._url}/{path}"
        data = json.dumps(body).encode("utf-8") if body else None

        req = Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")

        if self._auth:
            import base64
            creds = base64.b64encode(
                f"{self._auth[0]}:{self._auth[1]}".encode()
            ).decode()
            req.add_header("Authorization", f"Basic {creds}")

        try:
            with urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError) as e:
            logger.debug(f"Elasticsearch request failed: {e}")
            return None

    def _check_available(self) -> bool:
        """Ping Elasticsearch to check availability."""
        result = self._request("GET", "")
        return result is not None and "version" in result

    # -- LogStore interface --------------------------------------------------

    def insert(self, record: Dict[str, Any]) -> bool:
        path = f"{self._index}/_doc"
        result = self._request("POST", path, body=record)
        return result is not None and result.get("result") in ("created", "updated")

    def insert_batch(self, records: List[Dict[str, Any]]) -> int:
        """Bulk insert using Elasticsearch _bulk API."""
        if not records:
            return 0

        # Build NDJSON bulk body
        lines = []
        for rec in records:
            lines.append(json.dumps({"index": {"_index": self._index}}))
            lines.append(json.dumps(rec, default=str))
        bulk_body = "\n".join(lines) + "\n"

        url = f"{self._url}/_bulk"
        data = bulk_body.encode("utf-8")

        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-ndjson")

        if self._auth:
            import base64
            creds = base64.b64encode(
                f"{self._auth[0]}:{self._auth[1]}".encode()
            ).decode()
            req.add_header("Authorization", f"Basic {creds}")

        try:
            with urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errors"):
                    return sum(
                        1 for item in result.get("items", [])
                        if item.get("index", {}).get("status", 0) in (200, 201)
                    )
                return len(records)
        except (URLError, OSError):
            return 0

    def query(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        contains: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        must: List[Dict] = []

        if level:
            must.append({"term": {"level": level}})
        if logger_name:
            must.append({"prefix": {"logger": logger_name}})
        if contains:
            must.append({"match": {"msg": contains}})
        if since or until:
            range_q: Dict[str, str] = {}
            if since:
                range_q["gte"] = since
            if until:
                range_q["lte"] = until
            must.append({"range": {"ts": range_q}})
        if fields:
            for k, v in fields.items():
                must.append({"term": {k: v}})

        body = {
            "query": {"bool": {"must": must}} if must else {"match_all": {}},
            "sort": [{"ts": "desc"}],
            "from": offset,
            "size": limit,
        }

        result = self._request("POST", f"{self._index}/_search", body=body)
        if result is None:
            return []

        hits = result.get("hits", {}).get("hits", [])
        return [h["_source"] for h in hits]

    def count(self, level: Optional[str] = None) -> int:
        if level:
            body = {"query": {"term": {"level": level}}}
        else:
            body = {"query": {"match_all": {}}}

        result = self._request("POST", f"{self._index}/_count", body=body)
        if result is None:
            return 0
        return result.get("count", 0)

    def delete_older_than(self, days: int) -> int:
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        body = {
            "query": {"range": {"ts": {"lt": cutoff}}},
        }
        result = self._request(
            "POST", f"{self._index}/_delete_by_query", body=body
        )
        if result is None:
            return 0
        return result.get("deleted", 0)

    def close(self):
        pass  # HTTP is stateless

    @property
    def backend_name(self) -> str:
        return "elasticsearch"

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_available()
        return self._available

    def refresh_index(self) -> bool:
        """Force Elasticsearch to refresh the index (for testing)."""
        result = self._request("POST", f"{self._index}/_refresh")
        return result is not None


# ---------------------------------------------------------------------------
# Log router (multiplexer)
# ---------------------------------------------------------------------------


class LogRouter(LogStore):
    """Routes log records to multiple stores simultaneously.

    If one store fails, others still receive the record.

    Parameters:
        stores:  list of LogStore backends
    """

    def __init__(self, stores: Optional[List[LogStore]] = None):
        self._stores: List[LogStore] = stores or []

    def add_store(self, store: LogStore):
        self._stores.append(store)

    def remove_store(self, backend_name: str) -> bool:
        before = len(self._stores)
        self._stores = [s for s in self._stores if s.backend_name != backend_name]
        return len(self._stores) < before

    @property
    def store_count(self) -> int:
        return len(self._stores)

    def list_backends(self) -> List[str]:
        return [s.backend_name for s in self._stores]

    # -- LogStore interface --------------------------------------------------

    def insert(self, record: Dict[str, Any]) -> bool:
        ok = False
        for store in self._stores:
            try:
                if store.insert(record):
                    ok = True
            except Exception as e:
                logger.debug(f"Store {store.backend_name} insert failed: {e}")
        return ok

    def insert_batch(self, records: List[Dict[str, Any]]) -> int:
        best = 0
        for store in self._stores:
            try:
                n = store.insert_batch(records)
                best = max(best, n)
            except Exception as e:
                logger.debug(f"Store {store.backend_name} batch failed: {e}")
        return best

    def query(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        contains: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        # Query from first available store
        for store in self._stores:
            try:
                if store.is_available:
                    return store.query(
                        level=level,
                        logger_name=logger_name,
                        contains=contains,
                        since=since,
                        until=until,
                        fields=fields,
                        limit=limit,
                        offset=offset,
                    )
            except Exception:
                continue
        return []

    def count(self, level: Optional[str] = None) -> int:
        for store in self._stores:
            try:
                if store.is_available:
                    return store.count(level)
            except Exception:
                continue
        return 0

    def delete_older_than(self, days: int) -> int:
        total = 0
        for store in self._stores:
            try:
                total += store.delete_older_than(days)
            except Exception:
                pass
        return total

    def close(self):
        for store in self._stores:
            try:
                store.close()
            except Exception:
                pass

    @property
    def backend_name(self) -> str:
        return "router"

    @property
    def is_available(self) -> bool:
        return any(s.is_available for s in self._stores)


# ---------------------------------------------------------------------------
# Logging handler that writes to LogStore
# ---------------------------------------------------------------------------


class StoreHandler(logging.Handler):
    """stdlib logging.Handler that forwards records to a LogStore.

    Bridges the structured_logger with external storage.

    Usage::

        store = SQLiteLogStore("logs/app.db")
        handler = StoreHandler(store)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, store: LogStore, level: int = logging.DEBUG):
        super().__init__(level=level)
        self._store = store
        from launcher.structured_logger import StructuredFormatter
        self.setFormatter(StructuredFormatter())

    def emit(self, record: logging.LogRecord):
        try:
            formatted = self.format(record)
            parsed = json.loads(formatted)
            self._store.insert(parsed)
        except Exception:
            pass  # never crash on logging
