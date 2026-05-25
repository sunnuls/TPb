"""
Tests for roadmap11_auto_roi_detection.md Phase 4 — Integration into main cycle.

Validates:
  - BotInstance.auto_detect_roi() pipeline
  - Fallback to relative config when no anchors found
  - Periodic refresh (30s interval, throttle)
  - get_auto_roi_info() / get_auto_roi_zones()
  - to_dict() includes auto_roi
  - LiveRTA._refresh_auto_roi() wiring
"""

from __future__ import annotations

import asyncio
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np

# -------------------------------------------------------------------------
# Import targets
# -------------------------------------------------------------------------

try:
    from launcher.bot_instance import (
        BotInstance,
        BotStatus,
        AUTO_ROI_REFRESH_INTERVAL,
        HAS_ANCHOR_DETECTOR,
    )
    HAS_BOT_INSTANCE = True
except Exception:
    HAS_BOT_INSTANCE = False

try:
    from bridge.vision.anchor_detector import (
        AnchorMatch,
        ROIZone,
        load_config,
    )
    HAS_ANCHOR = True
except Exception:
    HAS_ANCHOR = False

try:
    from coach_app.rta.live_rta import LiveRTA, _AUTO_ROI_REFRESH_SECONDS
    HAS_LIVE_RTA = True
except Exception:
    HAS_LIVE_RTA = False

ROOT = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _make_fake_account():
    """Create a minimal Account-like object for BotInstance."""
    try:
        from launcher.models.account import Account
        acc = Account(nickname="TestBot", room="coinpoker")
        acc.roi_configured = True

        class FakeWin:
            window_id = "99999"
            window_title = "CoinPoker"
            window_type = "desktop_client"
        acc.window_info = FakeWin()
        return acc
    except Exception:
        return None


def _make_fake_anchors(n: int = 3) -> List[AnchorMatch]:
    """Create n fake AnchorMatch objects."""
    return [
        AnchorMatch(
            name=f"anchor_{i}",
            x=100 + i * 50, y=200 + i * 30,
            w=60, h=30,
            confidence=0.85 + i * 0.02,
            zone=f"zone_{i}",
            roi_offsets={f"roi_{i}": {"dx": 10, "dy": 10, "w": 100, "h": 50}},
        )
        for i in range(n)
    ]


def _make_fake_zones(n: int = 4) -> List[ROIZone]:
    return [
        ROIZone(name=f"zone_{i}", x=50 + i * 30, y=100 + i * 20, w=100, h=50,
                source=f"anchor_{i}", confidence=0.8)
        for i in range(n)
    ]


# -------------------------------------------------------------------------
# BotInstance auto-ROI integration
# -------------------------------------------------------------------------

@unittest.skipUnless(HAS_BOT_INSTANCE and HAS_ANCHOR, "dependencies unavailable")
class TestBotInstanceAutoDetectROI(unittest.TestCase):
    """BotInstance.auto_detect_roi() with mocked dependencies."""

    def _make_bot(self):
        bot = BotInstance.__new__(BotInstance)
        bot.bot_id = "test-bot-001"
        bot._auto_roi_zones = []
        bot._auto_roi_anchors = []
        bot._auto_roi_hwnd = None
        bot._auto_roi_last_refresh = 0.0
        bot._screen_capture = None
        return bot

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi")
    @patch("launcher.bot_instance.load_anchor_config")
    @patch("launcher.bot_instance.ScreenCapture", create=True)
    def test_full_pipeline(self, MockSC, mock_cfg, mock_detect):
        """auto_detect_roi: find window → capture → detect → zones."""
        bot = self._make_bot()

        # Mock ScreenCapture
        sc_inst = MagicMock()
        sc_inst.auto_find_window.return_value = 12345
        sc_inst.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        MockSC.return_value = sc_inst

        # Mock config + detection
        mock_cfg.return_value = {"anchors": {}, "derived_zones": {}}
        anchors = _make_fake_anchors(3)
        zones = _make_fake_zones(4)
        mock_detect.return_value = (anchors, zones)

        result = bot.auto_detect_roi(force=True)

        self.assertEqual(len(result), 4)
        self.assertEqual(bot._auto_roi_hwnd, 12345)
        self.assertEqual(len(bot._auto_roi_anchors), 3)

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi")
    @patch("launcher.bot_instance.load_anchor_config")
    @patch("launcher.bot_instance.ScreenCapture", create=True)
    def test_fallback_when_no_anchors(self, MockSC, mock_cfg, mock_detect):
        """Falls back to config percentages when no anchors found."""
        bot = self._make_bot()

        sc_inst = MagicMock()
        sc_inst.auto_find_window.return_value = 12345
        sc_inst.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        MockSC.return_value = sc_inst

        mock_cfg.return_value = load_config()  # real config
        mock_detect.return_value = ([], [])  # no anchors

        result = bot.auto_detect_roi(force=True)

        # Should have fallback zones from config
        self.assertGreater(len(result), 0)
        for z in result:
            self.assertIn("source", z)
            self.assertTrue(z["source"].startswith("fallback_"))
            self.assertEqual(z["confidence"], 0.0)

    def test_throttle_within_interval(self):
        """auto_detect_roi skips when called within refresh interval."""
        bot = self._make_bot()
        bot._auto_roi_last_refresh = time.time()
        bot._auto_roi_zones = [{"name": "cached"}]

        result = bot.auto_detect_roi()  # not forced
        self.assertEqual(result, [{"name": "cached"}])

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    def test_force_ignores_throttle(self):
        """force=True bypasses the throttle check."""
        bot = self._make_bot()
        bot._auto_roi_last_refresh = time.time()

        with patch("launcher.bot_instance.ScreenCapture", create=True) as MockSC:
            sc_inst = MagicMock()
            sc_inst.auto_find_window.return_value = None
            MockSC.return_value = sc_inst

            result = bot.auto_detect_roi(force=True)
            # Should attempt detection (even though window not found)
            sc_inst.auto_find_window.assert_called_once()

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi")
    @patch("launcher.bot_instance.load_anchor_config")
    @patch("launcher.bot_instance.ScreenCapture", create=True)
    def test_no_window_keeps_previous(self, MockSC, mock_cfg, mock_detect):
        """When no window found, previous zones are kept."""
        bot = self._make_bot()
        bot._auto_roi_zones = [{"name": "prev"}]

        sc_inst = MagicMock()
        sc_inst.auto_find_window.return_value = None
        MockSC.return_value = sc_inst

        result = bot.auto_detect_roi(force=True)
        self.assertEqual(result, [{"name": "prev"}])
        mock_detect.assert_not_called()


@unittest.skipUnless(HAS_BOT_INSTANCE and HAS_ANCHOR, "dependencies unavailable")
class TestBotInstanceROIInfo(unittest.TestCase):
    """get_auto_roi_info() and get_auto_roi_zones()."""

    def _make_bot(self):
        bot = BotInstance.__new__(BotInstance)
        bot.bot_id = "test-bot-002"
        bot._auto_roi_zones = [{"name": "board", "x": 100}]
        bot._auto_roi_anchors = _make_fake_anchors(2)
        bot._auto_roi_hwnd = 9999
        bot._auto_roi_last_refresh = 1000.0
        bot._screen_capture = None
        return bot

    def test_get_zones_returns_copy(self):
        bot = self._make_bot()
        zones = bot.get_auto_roi_zones()
        self.assertEqual(len(zones), 1)
        zones.append({"name": "extra"})
        self.assertEqual(len(bot.get_auto_roi_zones()), 1)

    def test_get_info(self):
        bot = self._make_bot()
        info = bot.get_auto_roi_info()
        self.assertEqual(info["hwnd"], 9999)
        self.assertEqual(info["anchor_count"], 2)
        self.assertEqual(info["zone_count"], 1)
        self.assertEqual(info["refresh_interval"], AUTO_ROI_REFRESH_INTERVAL)
        self.assertEqual(len(info["anchors"]), 2)


@unittest.skipUnless(HAS_BOT_INSTANCE and HAS_ANCHOR, "dependencies unavailable")
class TestBotInstanceToDict(unittest.TestCase):
    """to_dict() includes auto_roi section."""

    def test_auto_roi_in_dict(self):
        acc = _make_fake_account()
        if acc is None:
            self.skipTest("Account not importable")

        bot = BotInstance(account=acc)
        d = bot.to_dict()
        self.assertIn("auto_roi", d)
        self.assertIn("hwnd", d["auto_roi"])
        self.assertIn("anchor_count", d["auto_roi"])


@unittest.skipUnless(HAS_BOT_INSTANCE and HAS_ANCHOR, "dependencies unavailable")
class TestFallbackRelativeROI(unittest.TestCase):
    """_fallback_relative_roi() produces zones from config percentages."""

    def test_produces_zones(self):
        bot = BotInstance.__new__(BotInstance)
        bot.bot_id = "fb-test"
        zones = bot._fallback_relative_roi()
        # Each anchor in config has at least 1 roi_offset
        self.assertGreaterEqual(len(zones), 6)  # 6 anchors × ≥1 offset each
        for z in zones:
            self.assertIn("name", z)
            self.assertIn("x", z)
            self.assertIn("y", z)
            self.assertIn("w", z)
            self.assertIn("h", z)
            self.assertGreaterEqual(z["x"], 0)
            self.assertGreaterEqual(z["y"], 0)


@unittest.skipUnless(HAS_BOT_INSTANCE, "BotInstance unavailable")
class TestAutoROIRefreshInterval(unittest.TestCase):
    """AUTO_ROI_REFRESH_INTERVAL is 30 seconds."""

    def test_interval_value(self):
        self.assertEqual(AUTO_ROI_REFRESH_INTERVAL, 30)


# -------------------------------------------------------------------------
# LiveRTA auto-ROI integration
# -------------------------------------------------------------------------

@unittest.skipUnless(HAS_LIVE_RTA, "LiveRTA unavailable")
class TestLiveRTAAutoROI(unittest.TestCase):
    """LiveRTA._refresh_auto_roi() is wired correctly."""

    def test_refresh_interval_constant(self):
        self.assertEqual(_AUTO_ROI_REFRESH_SECONDS, 30)

    def test_has_refresh_method(self):
        self.assertTrue(hasattr(LiveRTA, "_refresh_auto_roi"))

    def test_refresh_no_deps_noop(self):
        """When dependencies are missing, refresh is a no-op."""
        with patch("coach_app.rta.live_rta.HAS_ANCHOR_DETECTOR", False):
            rta = MagicMock(spec=LiveRTA)
            rta._auto_roi_zones = []
            rta._auto_roi_last_refresh = 0.0

            # Call the real method with mocked self
            LiveRTA._refresh_auto_roi(rta, force=True)
            # Should return without side effects


# -------------------------------------------------------------------------
# Acceptance tests
# -------------------------------------------------------------------------

@unittest.skipUnless(HAS_BOT_INSTANCE and HAS_ANCHOR, "dependencies unavailable")
class TestAcceptanceAutoROIPipeline(unittest.TestCase):
    """End-to-end: detect → zones → info → dict."""

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi")
    @patch("launcher.bot_instance.load_anchor_config")
    @patch("launcher.bot_instance.ScreenCapture", create=True)
    def test_full_lifecycle(self, MockSC, mock_cfg, mock_detect):
        acc = _make_fake_account()
        if acc is None:
            self.skipTest("Account not importable")

        bot = BotInstance(account=acc)

        sc_inst = MagicMock()
        sc_inst.auto_find_window.return_value = 55555
        sc_inst.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        MockSC.return_value = sc_inst

        mock_cfg.return_value = {"anchors": {}, "derived_zones": {}}
        anchors = _make_fake_anchors(4)
        zones = _make_fake_zones(5)
        mock_detect.return_value = (anchors, zones)

        # Detect
        result = bot.auto_detect_roi(force=True)
        self.assertEqual(len(result), 5)

        # Info
        info = bot.get_auto_roi_info()
        self.assertEqual(info["hwnd"], 55555)
        self.assertEqual(info["anchor_count"], 4)
        self.assertEqual(info["zone_count"], 5)

        # Dict
        d = bot.to_dict()
        self.assertEqual(d["auto_roi"]["anchor_count"], 4)

    @patch("launcher.bot_instance.HAS_SCREEN_CAPTURE", True)
    @patch("launcher.bot_instance.detect_roi")
    @patch("launcher.bot_instance.load_anchor_config")
    @patch("launcher.bot_instance.ScreenCapture", create=True)
    def test_fallback_then_detect(self, MockSC, mock_cfg, mock_detect):
        """First call → fallback (no anchors), second → real detection."""
        acc = _make_fake_account()
        if acc is None:
            self.skipTest("Account not importable")

        bot = BotInstance(account=acc)

        sc_inst = MagicMock()
        sc_inst.auto_find_window.return_value = 11111
        sc_inst.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
        MockSC.return_value = sc_inst

        mock_cfg.return_value = load_config()
        mock_detect.return_value = ([], [])

        # First: fallback
        result1 = bot.auto_detect_roi(force=True)
        self.assertGreater(len(result1), 0)
        self.assertTrue(all("fallback_" in z.get("source", "") for z in result1))

        # Second: real anchors found
        anchors = _make_fake_anchors(6)
        zones = _make_fake_zones(8)
        mock_detect.return_value = (anchors, zones)

        result2 = bot.auto_detect_roi(force=True)
        self.assertEqual(len(result2), 8)
        self.assertFalse(any("fallback_" in z.get("source", "") for z in result2))


if __name__ == "__main__":
    unittest.main()
