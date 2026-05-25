"""
Tests for roadmap13 Phase 4 — Integration in bot_manager + bot_instance.
Auto-ROI pipeline: auto_find_window → find_anchors → calculate_all_roi.
Periodic refresh (25s), fallback.
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from launcher.bot_instance import (
    AUTO_ROI_REFRESH_INTERVAL,
    BotInstance,
    BotStatus,
)
from launcher.bot_manager import BotManager


def _fake_detect_roi(image, config=None, **kw):
    """Produce fake anchors + zones for testing."""
    from bridge.vision.anchor_detector import AnchorMatch, ROIZone
    anchors = [
        AnchorMatch(name="btn_fold", x=200, y=520, w=60, h=30, confidence=0.9, zone="action_buttons"),
        AnchorMatch(name="logo_coinpoker", x=10, y=5, w=40, h=20, confidence=0.85, zone="top_header"),
    ]
    zones = [
        ROIZone(name="hero_cards", x=100, y=440, w=120, h=80, source="btn_fold", confidence=0.9),
        ROIZone(name="board_center", x=210, y=255, w=350, h=80, source="logo_coinpoker", confidence=0.85),
    ]
    return anchors, zones


class TestBotInstanceAutoROI(unittest.TestCase):
    """Tests for BotInstance auto-ROI detection."""

    def _make_bot(self):
        return BotInstance(bot_id="test-bot-001")

    @patch("launcher.bot_instance.HAS_ANCHOR_DETECTOR", True)
    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi", side_effect=_fake_detect_roi)
    @patch("launcher.bot_instance.load_anchor_config", return_value={"anchors": {}, "derived_zones": {}})
    def test_auto_detect_roi_pipeline(self, mock_cfg, mock_det):
        bot = self._make_bot()
        mock_sc = MagicMock()
        mock_sc.auto_find_window.return_value = 12345
        bot._screen_capture = mock_sc

        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        with patch.object(bot, "_capture_window_image", return_value=fake_img):
            zones = bot.auto_detect_roi(force=True)

        self.assertGreater(len(zones), 0)
        self.assertEqual(bot._auto_roi_hwnd, 12345)

    @patch("launcher.bot_instance.HAS_ANCHOR_DETECTOR", True)
    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi", return_value=([], []))
    @patch("launcher.bot_instance.load_anchor_config", return_value={"anchors": {}, "derived_zones": {}})
    def test_fallback_when_no_anchors(self, mock_cfg, mock_det):
        bot = self._make_bot()
        mock_sc = MagicMock()
        mock_sc.auto_find_window.return_value = 12345
        bot._screen_capture = mock_sc

        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        with patch.object(bot, "_capture_window_image", return_value=fake_img), \
             patch.object(bot, "_fallback_relative_roi", return_value=[{"name": "fallback_zone"}]) as mock_fb:
            zones = bot.auto_detect_roi(force=True)
            mock_fb.assert_called_once()
            self.assertGreater(len(zones), 0)

    @patch("launcher.bot_instance.HAS_ANCHOR_DETECTOR", True)
    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    def test_throttling(self):
        bot = self._make_bot()
        bot._auto_roi_last_refresh = time.time()
        bot._auto_roi_zones = [{"name": "cached"}]
        zones = bot.auto_detect_roi(force=False)
        self.assertEqual(zones, [{"name": "cached"}])

    @patch("launcher.bot_instance.HAS_ANCHOR_DETECTOR", False)
    def test_no_anchor_detector(self):
        bot = self._make_bot()
        zones = bot.auto_detect_roi(force=True)
        self.assertEqual(zones, [])

    def test_refresh_interval_is_25(self):
        self.assertEqual(AUTO_ROI_REFRESH_INTERVAL, 25)

    def test_get_auto_roi_info(self):
        bot = self._make_bot()
        info = bot.get_auto_roi_info()
        self.assertIn("hwnd", info)
        self.assertIn("anchor_count", info)
        self.assertIn("zone_count", info)
        self.assertIn("refresh_interval", info)
        self.assertEqual(info["refresh_interval"], 25)

    def test_get_auto_roi_zones(self):
        bot = self._make_bot()
        bot._auto_roi_zones = [{"name": "test"}]
        zones = bot.get_auto_roi_zones()
        self.assertEqual(len(zones), 1)

    def test_to_dict_includes_auto_roi(self):
        bot = self._make_bot()
        d = bot.to_dict()
        self.assertIn("auto_roi", d)
        self.assertIn("zone_count", d["auto_roi"])

    def test_fallback_relative_roi_produces_zones(self):
        bot = self._make_bot()
        zones = bot._fallback_relative_roi()
        self.assertIsInstance(zones, list)
        self.assertGreater(len(zones), 0)
        for z in zones:
            self.assertIn("name", z)
            self.assertIn("x", z)
            self.assertIn("y", z)

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", False)
    def test_no_screen_capture(self):
        bot = self._make_bot()
        result = bot._auto_find_window_for_roi()
        self.assertIsNone(result)


class TestBotManagerAutoROI(unittest.TestCase):
    """Tests for BotManager auto-ROI orchestration."""

    def _make_manager_with_bot(self):
        from launcher.models.account import Account, WindowInfo, WindowType
        from launcher.models.roi_config import ROIConfig

        mgr = BotManager()
        acct = Account(nickname="TestBot", room="pokerstars")
        acct.window_info = WindowInfo(
            window_id="12345",
            window_title="PokerStars",
            window_type=WindowType.DESKTOP_CLIENT,
        )
        acct.roi_configured = True
        roi = ROIConfig(account_id=acct.account_id)
        bot = mgr.create_bot(acct, roi)
        return mgr, bot

    def test_trigger_auto_roi_single(self):
        mgr, bot = self._make_manager_with_bot()
        with patch.object(bot, "auto_detect_roi", return_value=[{"name": "z"}]) as mock_roi:
            zones = mgr.trigger_auto_roi(bot.bot_id, force=True)
            mock_roi.assert_called_once_with(force=True)
            self.assertEqual(len(zones), 1)

    def test_trigger_auto_roi_nonexistent_bot(self):
        mgr = BotManager()
        zones = mgr.trigger_auto_roi("nonexistent")
        self.assertEqual(zones, [])

    def test_trigger_auto_roi_all(self):
        mgr, bot = self._make_manager_with_bot()
        bot.status = BotStatus.PLAYING
        with patch.object(bot, "auto_detect_roi", return_value=[{"name": "z1"}, {"name": "z2"}]):
            results = mgr.trigger_auto_roi_all(force=True)
            self.assertIn(bot.bot_id, results)
            self.assertEqual(results[bot.bot_id], 2)

    def test_get_roi_summary(self):
        mgr, bot = self._make_manager_with_bot()
        summary = mgr.get_roi_summary()
        self.assertIn(bot.bot_id, summary)
        self.assertIn("zone_count", summary[bot.bot_id])

    def test_has_auto_roi_refresh_loop(self):
        mgr = BotManager()
        self.assertTrue(hasattr(mgr, "_auto_roi_refresh_loop_all"))
        import asyncio
        self.assertTrue(asyncio.iscoroutinefunction(mgr._auto_roi_refresh_loop_all))


if __name__ == "__main__":
    unittest.main()
