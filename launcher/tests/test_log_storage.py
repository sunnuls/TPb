"""
Tests for Log Storage — Phase 2 of logs.md.

Tests cover:
  - SQLiteLogStore (insert, batch, query, count, delete, close)
  - ElasticLogStore (init, availability check — no real ES needed)
  - LogRouter (multiplexer, fallback)
  - StoreHandler (bridge structured_logger → LogStore)
  - Query filters (level, logger, contains, since/until, fields)
  - Edge cases

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from launcher.log_storage import (
        LogStore,
        SQLiteLogStore,
        ElasticLogStore,
        LogRouter,
        StoreHandler,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    msg: str = "test",
    level: str = "INFO",
    logger: str = "test",
    **extra,
) -> Dict[str, Any]:
    rec = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "level": level,
        "logger": logger,
        "msg": msg,
    }
    rec.update(extra)
    return rec


# ---------------------------------------------------------------------------
# Test: SQLiteLogStore basics
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestSQLiteBasics(unittest.TestCase):
    """Test SQLite insert, count, query."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = SQLiteLogStore(f"{self.tmpdir}/test.db")

    def tearDown(self):
        self.store.close()

    def test_insert_returns_true(self):
        ok = self.store.insert(_make_record("hello"))
        self.assertTrue(ok)

    def test_count_after_insert(self):
        self.store.insert(_make_record("a"))
        self.store.insert(_make_record("b"))
        self.assertEqual(self.store.count(), 2)

    def test_count_by_level(self):
        self.store.insert(_make_record("ok", level="INFO"))
        self.store.insert(_make_record("err", level="ERROR"))
        self.store.insert(_make_record("err2", level="ERROR"))
        self.assertEqual(self.store.count("INFO"), 1)
        self.assertEqual(self.store.count("ERROR"), 2)

    def test_query_returns_records(self):
        self.store.insert(_make_record("hello world"))
        recs = self.store.query()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["msg"], "hello world")

    def test_insert_batch(self):
        records = [_make_record(f"msg-{i}") for i in range(20)]
        inserted = self.store.insert_batch(records)
        self.assertEqual(inserted, 20)
        self.assertEqual(self.store.count(), 20)

    def test_backend_name(self):
        self.assertEqual(self.store.backend_name, "sqlite")

    def test_is_available(self):
        self.assertTrue(self.store.is_available)

    def test_count_by_level_dict(self):
        self.store.insert(_make_record("a", level="INFO"))
        self.store.insert(_make_record("b", level="ERROR"))
        counts = self.store.count_by_level()
        self.assertEqual(counts["INFO"], 1)
        self.assertEqual(counts["ERROR"], 1)

    def test_table_size(self):
        self.store.insert(_make_record("data"))
        size = self.store.table_size_bytes()
        self.assertGreater(size, 0)


# ---------------------------------------------------------------------------
# Test: SQLite query filters
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestSQLiteQuery(unittest.TestCase):
    """Test SQLite query filtering."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = SQLiteLogStore(f"{self.tmpdir}/query.db")
        # Insert test data
        self.store.insert(_make_record("User logged in", level="INFO", logger="auth"))
        self.store.insert(_make_record("User logged out", level="INFO", logger="auth"))
        self.store.insert(_make_record("Database error", level="ERROR", logger="db"))
        self.store.insert(_make_record("Connection timeout", level="WARNING", logger="net"))
        self.store.insert(_make_record("Bot banned", level="CRITICAL", logger="bot.main", bot_id="b1"))

    def tearDown(self):
        self.store.close()

    def test_query_by_level(self):
        recs = self.store.query(level="ERROR")
        self.assertEqual(len(recs), 1)
        self.assertIn("Database", recs[0]["msg"])

    def test_query_by_logger(self):
        recs = self.store.query(logger_name="auth")
        self.assertEqual(len(recs), 2)

    def test_query_contains(self):
        recs = self.store.query(contains="logged")
        self.assertEqual(len(recs), 2)

    def test_query_contains_case_insensitive(self):
        # SQLite LIKE is case-insensitive for ASCII
        recs = self.store.query(contains="database")
        self.assertEqual(len(recs), 1)

    def test_query_limit(self):
        recs = self.store.query(limit=2)
        self.assertEqual(len(recs), 2)

    def test_query_offset(self):
        all_recs = self.store.query(limit=100)
        offset_recs = self.store.query(limit=2, offset=2)
        self.assertEqual(len(offset_recs), 2)

    def test_query_by_fields(self):
        recs = self.store.query(fields={"bot_id": "b1"})
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["msg"], "Bot banned")

    def test_query_combined_filters(self):
        recs = self.store.query(level="INFO", logger_name="auth")
        self.assertEqual(len(recs), 2)

    def test_query_no_match(self):
        recs = self.store.query(level="DEBUG")
        self.assertEqual(len(recs), 0)


# ---------------------------------------------------------------------------
# Test: SQLite delete / maintenance
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestSQLiteDelete(unittest.TestCase):
    """Test delete and maintenance operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = SQLiteLogStore(f"{self.tmpdir}/del.db")

    def tearDown(self):
        self.store.close()

    def test_delete_older_than(self):
        # Insert record with old timestamp
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        self.store.insert({"ts": old_ts, "level": "INFO", "msg": "old"})
        self.store.insert(_make_record("new"))

        deleted = self.store.delete_older_than(days=5)
        self.assertEqual(deleted, 1)
        self.assertEqual(self.store.count(), 1)

    def test_delete_keeps_recent(self):
        self.store.insert(_make_record("keep me"))
        deleted = self.store.delete_older_than(days=1)
        self.assertEqual(deleted, 0)
        self.assertEqual(self.store.count(), 1)

    def test_vacuum(self):
        for i in range(100):
            self.store.insert(_make_record(f"r-{i}"))
        self.store.delete_older_than(days=0)
        # Should not crash
        self.store.vacuum()


# ---------------------------------------------------------------------------
# Test: ElasticLogStore (no real ES needed)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestElasticLogStore(unittest.TestCase):
    """Test Elasticsearch store init (without running ES)."""

    def test_init(self):
        es = ElasticLogStore(url="http://localhost:9200", index="test")
        self.assertEqual(es.backend_name, "elasticsearch")

    def test_not_available_when_no_server(self):
        es = ElasticLogStore(url="http://localhost:19999", timeout=1)
        self.assertFalse(es.is_available)

    def test_insert_fails_gracefully(self):
        es = ElasticLogStore(url="http://localhost:19999", timeout=1)
        result = es.insert(_make_record("test"))
        self.assertFalse(result)

    def test_query_returns_empty(self):
        es = ElasticLogStore(url="http://localhost:19999", timeout=1)
        recs = es.query(level="ERROR")
        self.assertEqual(recs, [])

    def test_count_returns_zero(self):
        es = ElasticLogStore(url="http://localhost:19999", timeout=1)
        self.assertEqual(es.count(), 0)

    def test_close_no_error(self):
        es = ElasticLogStore()
        es.close()  # should not raise


# ---------------------------------------------------------------------------
# Test: LogRouter
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestLogRouter(unittest.TestCase):
    """Test log routing to multiple stores."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store1 = SQLiteLogStore(f"{self.tmpdir}/s1.db")
        self.store2 = SQLiteLogStore(f"{self.tmpdir}/s2.db")
        self.router = LogRouter([self.store1, self.store2])

    def tearDown(self):
        self.router.close()

    def test_insert_to_both(self):
        self.router.insert(_make_record("routed"))
        self.assertEqual(self.store1.count(), 1)
        self.assertEqual(self.store2.count(), 1)

    def test_batch_to_both(self):
        records = [_make_record(f"b-{i}") for i in range(5)]
        self.router.insert_batch(records)
        self.assertEqual(self.store1.count(), 5)
        self.assertEqual(self.store2.count(), 5)

    def test_query_from_first_available(self):
        self.router.insert(_make_record("find me"))
        recs = self.router.query(contains="find")
        self.assertEqual(len(recs), 1)

    def test_count(self):
        self.router.insert(_make_record("a"))
        self.router.insert(_make_record("b"))
        self.assertEqual(self.router.count(), 2)

    def test_is_available(self):
        self.assertTrue(self.router.is_available)

    def test_backend_name(self):
        self.assertEqual(self.router.backend_name, "router")

    def test_store_count(self):
        self.assertEqual(self.router.store_count, 2)

    def test_list_backends(self):
        backends = self.router.list_backends()
        self.assertEqual(backends, ["sqlite", "sqlite"])

    def test_add_store(self):
        store3 = SQLiteLogStore(f"{self.tmpdir}/s3.db")
        self.router.add_store(store3)
        self.assertEqual(self.router.store_count, 3)
        store3.close()

    def test_remove_store(self):
        # Add an ES store (won't be available but can be added)
        es = ElasticLogStore(url="http://localhost:19999")
        self.router.add_store(es)
        self.assertTrue(self.router.remove_store("elasticsearch"))
        self.assertEqual(self.router.store_count, 2)

    def test_empty_router(self):
        empty = LogRouter()
        self.assertFalse(empty.is_available)
        self.assertFalse(empty.insert(_make_record("x")))
        self.assertEqual(empty.query(), [])


# ---------------------------------------------------------------------------
# Test: StoreHandler (bridge)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestStoreHandler(unittest.TestCase):
    """Test logging.Handler → LogStore bridge."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = SQLiteLogStore(f"{self.tmpdir}/handler.db")
        self.handler = StoreHandler(self.store)
        self.logger = logging.getLogger("test.store_handler")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.store.close()

    def test_logging_writes_to_store(self):
        self.logger.info("Hello from logger")
        self.assertEqual(self.store.count(), 1)
        recs = self.store.query()
        self.assertEqual(recs[0]["msg"], "Hello from logger")

    def test_multiple_levels(self):
        self.logger.debug("D")
        self.logger.info("I")
        self.logger.warning("W")
        self.logger.error("E")
        self.logger.critical("C")
        self.assertEqual(self.store.count(), 5)
        self.assertEqual(self.store.count("ERROR"), 1)
        self.assertEqual(self.store.count("CRITICAL"), 1)

    def test_structured_fields_preserved(self):
        self.logger.info("Test", extra={"ctx_bot_id": "b1"})
        recs = self.store.query()
        self.assertEqual(recs[0]["bot_id"], "b1")


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires log_storage")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_unicode_in_sqlite(self):
        tmpdir = tempfile.mkdtemp()
        store = SQLiteLogStore(f"{tmpdir}/unicode.db")
        store.insert(_make_record("Привет мир 🎲"))
        recs = store.query()
        self.assertIn("Привет", recs[0]["msg"])
        store.close()

    def test_empty_query(self):
        tmpdir = tempfile.mkdtemp()
        store = SQLiteLogStore(f"{tmpdir}/empty.db")
        recs = store.query()
        self.assertEqual(recs, [])
        store.close()

    def test_large_batch(self):
        tmpdir = tempfile.mkdtemp()
        store = SQLiteLogStore(f"{tmpdir}/large.db")
        records = [_make_record(f"bulk-{i}") for i in range(1000)]
        inserted = store.insert_batch(records)
        self.assertEqual(inserted, 1000)
        self.assertEqual(store.count(), 1000)
        store.close()

    def test_creates_parent_dirs(self):
        tmpdir = tempfile.mkdtemp()
        store = SQLiteLogStore(f"{tmpdir}/deep/nested/dir/log.db")
        store.insert(_make_record("nested"))
        self.assertEqual(store.count(), 1)
        store.close()

    def test_since_until_filter(self):
        tmpdir = tempfile.mkdtemp()
        store = SQLiteLogStore(f"{tmpdir}/time.db")
        old = (datetime.now() - timedelta(hours=2)).isoformat()
        now = datetime.now().isoformat()
        store.insert({"ts": old, "level": "INFO", "msg": "old", "logger": "t"})
        store.insert({"ts": now, "level": "INFO", "msg": "new", "logger": "t"})

        cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
        recs = store.query(since=cutoff)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["msg"], "new")
        store.close()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
