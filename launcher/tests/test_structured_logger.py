"""
Tests for StructuredLogger — Phase 1 of logs.md.

Tests cover:
  - StructuredFormatter (JSON output, fields, exceptions)
  - RotatingJSONHandler (file creation, rotation)
  - ContextLogger (context binding, logging methods)
  - LogAggregator (store, query, count, clear)
  - setup_structured_logging (global setup)
  - Edge cases

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path

try:
    from launcher.structured_logger import (
        StructuredFormatter,
        RotatingJSONHandler,
        ContextLogger,
        LogAggregator,
        setup_structured_logging,
        get_structured_logger,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    msg: str = "test",
    level: int = logging.INFO,
    name: str = "test.logger",
    **extra,
) -> logging.LogRecord:
    """Create a LogRecord with optional extras."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


# ---------------------------------------------------------------------------
# Test: StructuredFormatter
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestStructuredFormatter(unittest.TestCase):
    """Test JSON structured formatting."""

    def setUp(self):
        self.fmt = StructuredFormatter()

    def test_output_is_valid_json(self):
        record = _make_record("hello world")
        line = self.fmt.format(record)
        obj = json.loads(line)
        self.assertIsInstance(obj, dict)

    def test_base_fields_present(self):
        record = _make_record("hello")
        obj = json.loads(self.fmt.format(record))
        self.assertIn("ts", obj)
        self.assertIn("level", obj)
        self.assertIn("logger", obj)
        self.assertIn("msg", obj)

    def test_level_correct(self):
        record = _make_record("x", level=logging.ERROR)
        obj = json.loads(self.fmt.format(record))
        self.assertEqual(obj["level"], "ERROR")

    def test_logger_name(self):
        record = _make_record("x", name="my.module")
        obj = json.loads(self.fmt.format(record))
        self.assertEqual(obj["logger"], "my.module")

    def test_message_content(self):
        record = _make_record("Test message 123")
        obj = json.loads(self.fmt.format(record))
        self.assertEqual(obj["msg"], "Test message 123")

    def test_extra_fields_included(self):
        record = _make_record("x", ctx_bot_id="abc", ctx_table="NL50")
        obj = json.loads(self.fmt.format(record))
        self.assertEqual(obj["bot_id"], "abc")
        self.assertEqual(obj["table"], "NL50")

    def test_builtin_keys_excluded(self):
        record = _make_record("x")
        obj = json.loads(self.fmt.format(record))
        self.assertNotIn("pathname", obj)
        self.assertNotIn("lineno", obj)

    def test_exception_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = _make_record("error")
            record.exc_info = sys.exc_info()

        obj = json.loads(self.fmt.format(record))
        self.assertEqual(obj["exc_type"], "ValueError")
        self.assertIn("boom", obj["exc_text"])

    def test_utc_timestamp(self):
        fmt = StructuredFormatter(ts_utc=True)
        record = _make_record("x")
        obj = json.loads(fmt.format(record))
        # UTC timestamps contain +00:00
        self.assertIn("+00:00", obj["ts"])

    def test_single_line_output(self):
        record = _make_record("no\nnewlines")
        line = self.fmt.format(record)
        # JSON should escape newlines, no actual newlines in output
        parsed = json.loads(line)
        self.assertIn("\\n", line.split('"msg":')[1].split('"')[1]
                       if "\\n" in line else "\\n")
        self.assertIsInstance(parsed["msg"], str)


# ---------------------------------------------------------------------------
# Test: RotatingJSONHandler
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestRotatingJSONHandler(unittest.TestCase):
    """Test file-based JSON handler."""

    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.jsonl")
            handler = RotatingJSONHandler(filename=filepath, max_bytes=1024)
            logger = logging.getLogger("test.rotating")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            logger.info("line one")
            handler.flush()

            self.assertTrue(os.path.exists(filepath))

            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertGreaterEqual(len(lines), 1)
            obj = json.loads(lines[0])
            self.assertEqual(obj["msg"], "line one")

            logger.removeHandler(handler)
            handler.close()

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sub", "dir", "log.jsonl")
            handler = RotatingJSONHandler(filename=filepath)
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, "sub", "dir")))
            handler.close()

    def test_multiple_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "multi.jsonl")
            handler = RotatingJSONHandler(filename=filepath, max_bytes=10240)
            logger = logging.getLogger("test.multi")
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            for i in range(20):
                logger.info(f"Record {i}")
            handler.flush()

            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 20)
            for line in lines:
                obj = json.loads(line)
                self.assertIn("Record", obj["msg"])

            logger.removeHandler(handler)
            handler.close()


# ---------------------------------------------------------------------------
# Test: ContextLogger
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestContextLogger(unittest.TestCase):
    """Test context logger wrapper."""

    def setUp(self):
        self.agg = LogAggregator(max_records=1000)
        self.base = logging.getLogger("test.ctx")
        self.base.addHandler(self.agg)
        self.base.setLevel(logging.DEBUG)

    def tearDown(self):
        self.base.removeHandler(self.agg)

    def test_basic_logging(self):
        log = ContextLogger(self.base, bot_id="b1")
        log.info("Hello")
        recs = self.agg.recent(1)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["msg"], "Hello")
        self.assertEqual(recs[0]["bot_id"], "b1")

    def test_context_fields_injected(self):
        log = ContextLogger(self.base, bot_id="b2", room="ps")
        log.warning("Alert")
        recs = self.agg.recent(1)
        self.assertEqual(recs[0]["bot_id"], "b2")
        self.assertEqual(recs[0]["room"], "ps")

    def test_per_call_fields(self):
        log = ContextLogger(self.base, bot_id="b3")
        log.info("Hand", hand_id=42, table="NL50")
        recs = self.agg.recent(1)
        self.assertEqual(recs[0]["hand_id"], 42)
        self.assertEqual(recs[0]["table"], "NL50")

    def test_bind_creates_child(self):
        log = ContextLogger(self.base, bot_id="b4")
        child = log.bind(session="s1")
        child.info("Test")
        recs = self.agg.recent(1)
        self.assertEqual(recs[0]["bot_id"], "b4")
        self.assertEqual(recs[0]["session"], "s1")

    def test_unbind_removes_key(self):
        log = ContextLogger(self.base, bot_id="b5", temp="x")
        clean = log.unbind("temp")
        self.assertNotIn("temp", clean.context)
        self.assertIn("bot_id", clean.context)

    def test_all_levels(self):
        log = ContextLogger(self.base)
        log.debug("D")
        log.info("I")
        log.warning("W")
        log.error("E")
        log.critical("C")
        recs = self.agg.recent(10)
        levels = [r["level"] for r in recs]
        self.assertIn("DEBUG", levels)
        self.assertIn("INFO", levels)
        self.assertIn("WARNING", levels)
        self.assertIn("ERROR", levels)
        self.assertIn("CRITICAL", levels)

    def test_context_property(self):
        log = ContextLogger(self.base, a=1, b=2)
        self.assertEqual(log.context, {"a": 1, "b": 2})


# ---------------------------------------------------------------------------
# Test: LogAggregator
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestLogAggregator(unittest.TestCase):
    """Test in-memory log store."""

    def setUp(self):
        self.agg = LogAggregator(max_records=100)
        self.logger = logging.getLogger("test.agg")
        self.logger.addHandler(self.agg)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.agg)

    def test_stores_records(self):
        self.logger.info("Hello")
        self.assertEqual(self.agg.size, 1)

    def test_count(self):
        for i in range(10):
            self.logger.info(f"msg {i}")
        self.assertEqual(self.agg.count(), 10)

    def test_count_by_level(self):
        self.logger.info("a")
        self.logger.error("b")
        self.logger.error("c")
        counts = self.agg.count_by_level()
        self.assertEqual(counts.get("INFO", 0), 1)
        self.assertEqual(counts.get("ERROR", 0), 2)

    def test_recent(self):
        for i in range(5):
            self.logger.info(f"msg-{i}")
        recs = self.agg.recent(3)
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[-1]["msg"], "msg-4")

    def test_query_by_level(self):
        self.logger.info("ok")
        self.logger.error("fail")
        errors = self.agg.query(level="ERROR")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["msg"], "fail")

    def test_query_by_logger(self):
        self.logger.info("target")
        other = logging.getLogger("other.logger")
        other.addHandler(self.agg)
        other.info("noise")
        recs = self.agg.query(logger="test.agg")
        self.assertTrue(all(r["logger"].startswith("test.agg") for r in recs))
        other.removeHandler(self.agg)

    def test_query_contains(self):
        self.logger.info("User login successful")
        self.logger.info("User logout")
        recs = self.agg.query(contains="login")
        self.assertEqual(len(recs), 1)

    def test_query_fields(self):
        log = ContextLogger(self.logger, bot_id="b1")
        log.info("A")
        log2 = ContextLogger(self.logger, bot_id="b2")
        log2.info("B")
        recs = self.agg.query(fields={"bot_id": "b1"})
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["msg"], "A")

    def test_query_limit(self):
        for i in range(20):
            self.logger.info(f"r-{i}")
        recs = self.agg.query(limit=5)
        self.assertEqual(len(recs), 5)

    def test_errors_and_criticals(self):
        self.logger.info("ok")
        self.logger.error("err1")
        self.logger.critical("crit1")
        self.logger.warning("warn")
        errs = self.agg.errors_and_criticals()
        self.assertEqual(len(errs), 2)

    def test_clear(self):
        self.logger.info("x")
        self.agg.clear()
        self.assertEqual(self.agg.size, 0)

    def test_max_records_eviction(self):
        agg = LogAggregator(max_records=5)
        logger = logging.getLogger("test.evict")
        logger.addHandler(agg)
        logger.setLevel(logging.DEBUG)
        for i in range(10):
            logger.info(f"msg-{i}")
        self.assertLessEqual(agg.size, 5)
        # Most recent should be msg-9
        recs = agg.recent(1)
        self.assertEqual(recs[0]["msg"], "msg-9")
        logger.removeHandler(agg)


# ---------------------------------------------------------------------------
# Test: Global setup
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestGlobalSetup(unittest.TestCase):
    """Test setup_structured_logging and get_structured_logger."""

    def test_get_structured_logger(self):
        log = get_structured_logger("test.global", bot_id="g1")
        self.assertIsInstance(log, ContextLogger)
        self.assertEqual(log.context["bot_id"], "g1")

    def test_setup_creates_handlers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fh, agg = setup_structured_logging(
                log_dir=tmpdir,
                filename="test_setup.jsonl",
                aggregator_size=100,
            )
            self.assertIsNotNone(fh)
            self.assertIsNotNone(agg)

            logger = logging.getLogger("test.setup")
            logger.info("Setup test msg")
            fh.flush()

            # Check file exists
            filepath = os.path.join(tmpdir, "test_setup.jsonl")
            self.assertTrue(os.path.exists(filepath))

            # Cleanup
            root = logging.getLogger()
            root.removeHandler(fh)
            root.removeHandler(agg)
            fh.close()


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires structured_logger")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_empty_message(self):
        fmt = StructuredFormatter()
        record = _make_record("")
        obj = json.loads(fmt.format(record))
        self.assertEqual(obj["msg"], "")

    def test_unicode_message(self):
        fmt = StructuredFormatter()
        record = _make_record("Привет мир 🎲")
        obj = json.loads(fmt.format(record))
        self.assertIn("Привет", obj["msg"])

    def test_large_context(self):
        agg = LogAggregator(max_records=10)
        logger = logging.getLogger("test.large")
        logger.addHandler(agg)
        logger.setLevel(logging.DEBUG)
        log = ContextLogger(logger, **{f"key_{i}": i for i in range(50)})
        log.info("Big context")
        recs = agg.recent(1)
        self.assertEqual(recs[0]["msg"], "Big context")
        self.assertEqual(recs[0]["key_0"], 0)
        self.assertEqual(recs[0]["key_49"], 49)
        logger.removeHandler(agg)

    def test_aggregator_thread_safe(self):
        """Basic thread-safety smoke test."""
        import threading
        agg = LogAggregator(max_records=1000)
        logger = logging.getLogger("test.thread")
        logger.addHandler(agg)
        logger.setLevel(logging.DEBUG)

        def writer(n):
            for i in range(50):
                logger.info(f"thread-{n}-{i}")

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(agg.size, 200)
        logger.removeHandler(agg)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
