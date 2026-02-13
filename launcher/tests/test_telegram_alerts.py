"""
Tests for Telegram Alerts — Phase 3 of logs.md.

Core requirement: test 10 alerts.

Tests cover:
  - TelegramSender (dry-run, history, send/fail)
  - AlertRule (level matching, keyword matching, exclude, cooldown)
  - AlertManager (evaluate, rules CRUD, cooldown, rate limit)
  - Message formatting (emoji, Markdown)
  - AlertLoggingHandler (logging → Telegram bridge)
  - 10-alert stress test (core requirement)
  - Edge cases

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import time
import unittest
from typing import Any, Dict

try:
    from launcher.telegram_alerts import (
        TelegramSender,
        SendResult,
        AlertRule,
        AlertManager,
        AlertLoggingHandler,
        default_format_alert,
        SEVERITY_EMOJI,
        LEVEL_PRIORITY,
    )

    MODULE_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rec(
    msg: str = "test",
    level: str = "ERROR",
    logger: str = "bot",
    **extra,
) -> Dict[str, Any]:
    rec = {"ts": "2026-02-10T12:00:00", "level": level, "logger": logger, "msg": msg}
    rec.update(extra)
    return rec


# ---------------------------------------------------------------------------
# Test: TelegramSender (dry-run)
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestTelegramSender(unittest.TestCase):
    """Test sender in dry-run mode."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)

    def test_dry_run_success(self):
        r = self.sender.send_message("Hello")
        self.assertTrue(r.success)

    def test_dry_run_message_id(self):
        r = self.sender.send_message("A")
        self.assertEqual(r.message_id, 1)
        r2 = self.sender.send_message("B")
        self.assertEqual(r2.message_id, 2)

    def test_send_history(self):
        self.sender.send_message("X")
        self.sender.send_message("Y")
        self.assertEqual(len(self.sender.send_history), 2)

    def test_total_sent(self):
        self.sender.send_message("A")
        self.sender.send_message("B")
        self.assertEqual(self.sender.total_sent, 2)
        self.assertEqual(self.sender.total_failed, 0)

    def test_clear_history(self):
        self.sender.send_message("X")
        self.sender.clear_history()
        self.assertEqual(len(self.sender.send_history), 0)

    def test_missing_token_fails(self):
        sender = TelegramSender(bot_token="", chat_id="", dry_run=False)
        r = sender.send_message("test")
        self.assertFalse(r.success)
        self.assertIn("Missing", r.error)

    def test_invalid_url_fails(self):
        sender = TelegramSender(
            bot_token="fake:token",
            chat_id="123",
            dry_run=False,
            timeout=1,
        )
        r = sender.send_message("test")
        self.assertFalse(r.success)


# ---------------------------------------------------------------------------
# Test: AlertRule matching
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestAlertRule(unittest.TestCase):
    """Test alert rule configuration."""

    def test_level_priority(self):
        r = AlertRule(level="ERROR")
        self.assertEqual(r.level_priority, 40)

    def test_level_priority_critical(self):
        r = AlertRule(level="CRITICAL")
        self.assertEqual(r.level_priority, 50)

    def test_defaults(self):
        r = AlertRule()
        self.assertEqual(r.name, "default")
        self.assertTrue(r.enabled)
        self.assertEqual(r.cooldown_s, 60.0)

    def test_keywords_list(self):
        r = AlertRule(keywords=["ban", "blocked"])
        self.assertEqual(len(r.keywords), 2)


# ---------------------------------------------------------------------------
# Test: AlertManager — basic evaluation
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestAlertManagerBasic(unittest.TestCase):
    """Test alert evaluation logic."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)
        self.mgr = AlertManager(self.sender, global_rate_limit=0)

    def test_error_rule_fires_on_error(self):
        self.mgr.add_rule(AlertRule(name="errors", level="ERROR", cooldown_s=0))
        fired = self.mgr.evaluate(_rec("Something failed", level="ERROR"))
        self.assertIn("errors", fired)

    def test_error_rule_ignores_info(self):
        self.mgr.add_rule(AlertRule(name="errors", level="ERROR", cooldown_s=0))
        fired = self.mgr.evaluate(_rec("All good", level="INFO"))
        self.assertEqual(fired, [])

    def test_keyword_match(self):
        self.mgr.add_rule(AlertRule(
            name="ban_alert", level="WARNING", keywords=["ban", "blocked"],
            cooldown_s=0,
        ))
        fired = self.mgr.evaluate(_rec("Bot was banned", level="WARNING"))
        self.assertIn("ban_alert", fired)

    def test_keyword_no_match(self):
        self.mgr.add_rule(AlertRule(
            name="ban_alert", level="WARNING", keywords=["ban"],
            cooldown_s=0,
        ))
        fired = self.mgr.evaluate(_rec("Normal operation", level="WARNING"))
        self.assertEqual(fired, [])

    def test_keyword_case_insensitive(self):
        self.mgr.add_rule(AlertRule(
            name="ban", level="ERROR", keywords=["BAN"],
            cooldown_s=0,
        ))
        fired = self.mgr.evaluate(_rec("bot was banned", level="ERROR"))
        self.assertIn("ban", fired)

    def test_exclude_keywords(self):
        self.mgr.add_rule(AlertRule(
            name="errors", level="ERROR", exclude_keywords=["ignore"],
            cooldown_s=0,
        ))
        fired = self.mgr.evaluate(_rec("Please ignore this error", level="ERROR"))
        self.assertEqual(fired, [])

    def test_disabled_rule_skipped(self):
        self.mgr.add_rule(AlertRule(
            name="off", level="ERROR", enabled=False, cooldown_s=0,
        ))
        fired = self.mgr.evaluate(_rec("Error!", level="ERROR"))
        self.assertEqual(fired, [])

    def test_multiple_rules_can_fire(self):
        self.mgr.add_rule(AlertRule(name="r1", level="ERROR", cooldown_s=0))
        self.mgr.add_rule(AlertRule(name="r2", level="CRITICAL", cooldown_s=0))
        fired = self.mgr.evaluate(_rec("Crash", level="CRITICAL"))
        self.assertIn("r1", fired)  # CRITICAL >= ERROR
        self.assertIn("r2", fired)


# ---------------------------------------------------------------------------
# Test: AlertManager — cooldown
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestCooldown(unittest.TestCase):
    """Test per-rule cooldown."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)
        self.mgr = AlertManager(self.sender, global_rate_limit=0)

    def test_cooldown_blocks_second_alert(self):
        self.mgr.add_rule(AlertRule(name="err", level="ERROR", cooldown_s=60))
        fired1 = self.mgr.evaluate(_rec("Error 1", level="ERROR"))
        fired2 = self.mgr.evaluate(_rec("Error 2", level="ERROR"))
        self.assertEqual(len(fired1), 1)
        self.assertEqual(len(fired2), 0)  # blocked by cooldown

    def test_zero_cooldown_allows_all(self):
        self.mgr.add_rule(AlertRule(name="err", level="ERROR", cooldown_s=0))
        for i in range(5):
            fired = self.mgr.evaluate(_rec(f"Error {i}", level="ERROR"))
            self.assertEqual(len(fired), 1)


# ---------------------------------------------------------------------------
# Test: AlertManager — rate limit
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestRateLimit(unittest.TestCase):
    """Test global rate limiting."""

    def test_rate_limit_caps_alerts(self):
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=3)
        mgr.add_rule(AlertRule(name="err", level="ERROR", cooldown_s=0))

        fired_total = 0
        for i in range(10):
            fired = mgr.evaluate(_rec(f"Error {i}", level="ERROR"))
            fired_total += len(fired)

        # Should be capped at ~3 within the same minute window
        self.assertLessEqual(fired_total, 3)


# ---------------------------------------------------------------------------
# Test: AlertManager — CRUD
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestRuleCRUD(unittest.TestCase):
    """Test rule management."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)
        self.mgr = AlertManager(self.sender)

    def test_add_rule(self):
        self.mgr.add_rule(AlertRule(name="test"))
        self.assertEqual(self.mgr.rule_count, 1)

    def test_remove_rule(self):
        self.mgr.add_rule(AlertRule(name="test"))
        self.assertTrue(self.mgr.remove_rule("test"))
        self.assertEqual(self.mgr.rule_count, 0)

    def test_remove_nonexistent(self):
        self.assertFalse(self.mgr.remove_rule("nope"))

    def test_get_rule(self):
        self.mgr.add_rule(AlertRule(name="ban", level="CRITICAL"))
        r = self.mgr.get_rule("ban")
        self.assertIsNotNone(r)
        self.assertEqual(r.level, "CRITICAL")

    def test_list_rules(self):
        self.mgr.add_rule(AlertRule(name="a"))
        self.mgr.add_rule(AlertRule(name="b"))
        self.assertEqual(set(self.mgr.list_rules()), {"a", "b"})


# ---------------------------------------------------------------------------
# Test: Message formatting
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestFormatting(unittest.TestCase):
    """Test alert message formatting."""

    def test_default_format_has_emoji(self):
        text = default_format_alert(_rec("Error!", level="ERROR"), rule_name="test")
        self.assertIn("❌", text)

    def test_default_format_has_level(self):
        text = default_format_alert(_rec("X", level="CRITICAL"), rule_name="crit")
        self.assertIn("CRITICAL", text)

    def test_default_format_has_message(self):
        text = default_format_alert(_rec("Bot banned"), rule_name="ban")
        self.assertIn("Bot banned", text)

    def test_default_format_has_context(self):
        text = default_format_alert(
            _rec("Error", bot_id="b1", table="NL50"), rule_name="err"
        )
        self.assertIn("bot_id", text)
        self.assertIn("b1", text)

    def test_custom_format_fn(self):
        custom = lambda rec: f"ALERT: {rec['msg']}"
        rule = AlertRule(name="custom", level="ERROR", format_fn=custom, cooldown_s=0)
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=0)
        mgr.add_rule(rule)
        mgr.evaluate(_rec("boom", level="ERROR"))
        # The dry-run sender received it
        self.assertEqual(sender.total_sent, 1)

    def test_severity_emojis_complete(self):
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.assertIn(level, SEVERITY_EMOJI)


# ---------------------------------------------------------------------------
# Test: AlertLoggingHandler
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestAlertLoggingHandler(unittest.TestCase):
    """Test logging.Handler → Telegram bridge."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)
        self.mgr = AlertManager(self.sender, global_rate_limit=0)
        self.mgr.add_rule(AlertRule(name="errors", level="ERROR", cooldown_s=0))
        self.handler = AlertLoggingHandler(self.mgr, level=logging.WARNING)
        self.logger = logging.getLogger("test.alert_handler")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_error_triggers_alert(self):
        self.logger.error("Something failed")
        self.assertGreater(self.sender.total_sent, 0)

    def test_info_does_not_trigger(self):
        self.logger.info("Normal operation")
        self.assertEqual(self.sender.total_sent, 0)

    def test_critical_triggers_alert(self):
        self.logger.critical("Bot banned!")
        self.assertGreater(self.sender.total_sent, 0)


# ---------------------------------------------------------------------------
# Test: Alert history / stats
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestAlertHistory(unittest.TestCase):
    """Test alert log and statistics."""

    def setUp(self):
        self.sender = TelegramSender(dry_run=True)
        self.mgr = AlertManager(self.sender, global_rate_limit=0)
        self.mgr.add_rule(AlertRule(name="err", level="ERROR", cooldown_s=0))

    def test_alert_log_populated(self):
        self.mgr.evaluate(_rec("fail", level="ERROR"))
        self.assertEqual(self.mgr.total_alerts, 1)

    def test_alerts_for_rule(self):
        self.mgr.add_rule(AlertRule(name="ban", level="CRITICAL", cooldown_s=0))
        self.mgr.evaluate(_rec("fail", level="ERROR"))
        self.mgr.evaluate(_rec("banned", level="CRITICAL"))
        err_alerts = self.mgr.alerts_for_rule("err")
        ban_alerts = self.mgr.alerts_for_rule("ban")
        # "err" (level=ERROR) fires on both ERROR and CRITICAL records
        self.assertGreaterEqual(len(err_alerts), 1)
        self.assertGreaterEqual(len(ban_alerts), 1)

    def test_clear_history(self):
        self.mgr.evaluate(_rec("fail", level="ERROR"))
        self.mgr.clear_history()
        self.assertEqual(self.mgr.total_alerts, 0)


# ---------------------------------------------------------------------------
# Test: 10 ALERTS — CORE REQUIREMENT
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestTenAlerts(unittest.TestCase):
    """
    Core requirement from logs.md Phase 3:
    Generate and validate 10 distinct alerts.
    """

    def test_10_alerts_sent(self):
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=0)

        # Add diverse rules
        mgr.add_rule(AlertRule(name="ban", level="CRITICAL", keywords=["ban"], cooldown_s=0))
        mgr.add_rule(AlertRule(name="error", level="ERROR", cooldown_s=0))
        mgr.add_rule(AlertRule(name="timeout", level="WARNING", keywords=["timeout"], cooldown_s=0))
        mgr.add_rule(AlertRule(name="crash", level="CRITICAL", keywords=["crash"], cooldown_s=0))
        mgr.add_rule(AlertRule(name="vision", level="ERROR", keywords=["vision"], cooldown_s=0))

        # 10 distinct alert-triggering records
        records = [
            _rec("Bot was banned on PokerStars", level="CRITICAL", bot_id="b1"),
            _rec("Database connection error", level="ERROR", logger="db"),
            _rec("Connection timeout to lobby", level="WARNING", logger="net"),
            _rec("Application crash in main loop", level="CRITICAL"),
            _rec("Vision detection failed 5 times", level="ERROR", bot_id="b2"),
            _rec("Bot banned from table NL50", level="CRITICAL", table="NL50"),
            _rec("Unexpected error in action executor", level="ERROR"),
            _rec("Session timeout exceeded", level="WARNING", logger="session"),
            _rec("Crash recovery initiated", level="CRITICAL"),
            _rec("Vision OCR returned empty", level="ERROR", bot_id="b3"),
        ]

        fired_total = 0
        for rec in records:
            fired = mgr.evaluate(rec)
            fired_total += len(fired)

        # At least 10 alerts should have fired (some records match multiple rules)
        self.assertGreaterEqual(fired_total, 10,
                                f"Only {fired_total} alerts fired, expected >= 10")

        # Sender should have received them
        self.assertGreaterEqual(sender.total_sent, 10)

        # All successful (dry-run)
        self.assertEqual(sender.total_failed, 0)

    def test_10_alerts_diverse_rules(self):
        """Each of the 5 rules should fire at least once in 10 records."""
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=0)

        rules = [
            AlertRule(name="ban", level="CRITICAL", keywords=["ban"], cooldown_s=0),
            AlertRule(name="error", level="ERROR", cooldown_s=0),
            AlertRule(name="timeout", level="WARNING", keywords=["timeout"], cooldown_s=0),
            AlertRule(name="crash", level="CRITICAL", keywords=["crash"], cooldown_s=0),
            AlertRule(name="vision", level="ERROR", keywords=["vision"], cooldown_s=0),
        ]
        for r in rules:
            mgr.add_rule(r)

        records = [
            _rec("Bot banned", level="CRITICAL"),
            _rec("Generic error", level="ERROR"),
            _rec("Connection timeout", level="WARNING"),
            _rec("App crash", level="CRITICAL"),
            _rec("Vision failure", level="ERROR"),
            _rec("Second ban detected", level="CRITICAL"),
            _rec("Another error", level="ERROR"),
            _rec("Network timeout again", level="WARNING"),
            _rec("System crash", level="CRITICAL"),
            _rec("Vision OCR empty", level="ERROR"),
        ]

        for rec in records:
            mgr.evaluate(rec)

        # Each rule should have fired at least once
        for rule in rules:
            alerts = mgr.alerts_for_rule(rule.name)
            self.assertGreater(len(alerts), 0,
                               f"Rule '{rule.name}' never fired")

    def test_10_alerts_history_complete(self):
        """Alert log should record all 10+ alerts."""
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=0)
        mgr.add_rule(AlertRule(name="all", level="ERROR", cooldown_s=0))

        for i in range(10):
            mgr.evaluate(_rec(f"Error #{i}", level="ERROR"))

        self.assertEqual(mgr.total_alerts, 10)
        self.assertEqual(mgr.successful_alerts, 10)


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


@unittest.skipUnless(MODULE_AVAILABLE, "Requires telegram_alerts")
class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_empty_message(self):
        sender = TelegramSender(dry_run=True)
        r = sender.send_message("")
        self.assertTrue(r.success)

    def test_unicode_message(self):
        sender = TelegramSender(dry_run=True)
        r = sender.send_message("Бот забанен 🚨")
        self.assertTrue(r.success)

    def test_no_rules_no_alerts(self):
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender)
        fired = mgr.evaluate(_rec("Error", level="ERROR"))
        self.assertEqual(fired, [])

    def test_evaluate_empty_record(self):
        sender = TelegramSender(dry_run=True)
        mgr = AlertManager(sender, global_rate_limit=0)
        mgr.add_rule(AlertRule(name="err", level="ERROR", cooldown_s=0))
        fired = mgr.evaluate({})
        self.assertEqual(fired, [])  # empty record → level is "INFO" → below ERROR


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
