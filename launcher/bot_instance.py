"""
Bot Instance - Launcher Application.

roadmap13 Phase 4: auto_find_window → find_anchors (multi-scale) → calculate_all_roi.
Periodic anchor refresh every 25 seconds, fallback to relative config ROI.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig
from launcher.bot_settings import BotSettings

# Mouse guard — pauses bot when human takes mouse control
try:
    from launcher.mouse_guard import MouseGuard
    HAS_MOUSE_GUARD = True
except Exception:
    HAS_MOUSE_GUARD = False

# Human timing — anti-detection delay engine
try:
    from bridge.timing.human_timing import HumanTiming, make_timing
    HAS_HUMAN_TIMING = True
except Exception:
    HAS_HUMAN_TIMING = False

# Graceful import of profile manager (settings.md Phase 1)
try:
    from launcher.bot_profile_manager import BotProfileManager, BotProfile
    HAS_PROFILE_MANAGER = True
except (ImportError, Exception):
    HAS_PROFILE_MANAGER = False

# Graceful import of account binder (account_binding.md Phase 2)
try:
    from launcher.bot_account_binder import (
        BotAccountBinder,
        Binding,
        BindStatus,
    )
    HAS_ACCOUNT_BINDER = True
except (ImportError, Exception):
    HAS_ACCOUNT_BINDER = False

# Graceful import of auto-ROI detection (roadmap11 Phase 4)
try:
    from bridge.screen_capture import ScreenCapture
    HAS_SCREEN_CAPTURE = True
except (ImportError, Exception):
    HAS_SCREEN_CAPTURE = False

try:
    from bridge.vision.anchor_detector import (
        find_anchors,
        calculate_all_roi,
        calculate_relative_roi,
        detect_roi,
        load_config as load_anchor_config,
        AnchorMatch,
        ROIZone as AnchorROIZone,
    )
    HAS_ANCHOR_DETECTOR = True
except (ImportError, Exception):
    HAS_ANCHOR_DETECTOR = False

logger = logging.getLogger(__name__)

# Auto-ROI refresh interval (seconds) — roadmap13: 20-30s
AUTO_ROI_REFRESH_INTERVAL = 25


class BotStatus(str, Enum):
    """Bot operational status."""
    IDLE = "idle"
    STARTING = "starting"
    SEARCHING = "searching"
    SEATED = "seated"
    PLAYING = "playing"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class BotStatistics:
    """
    Bot statistics.
    
    Attributes:
        hands_played: Number of hands played
        pot_won: Total pot won
        pot_lost: Total pot lost
        vision_errors: Number of vision errors
        decisions_made: Number of decisions made
        actions_executed: Number of actions executed
        uptime_seconds: Total uptime in seconds
    """
    hands_played: int = 0
    pot_won: float = 0.0
    pot_lost: float = 0.0
    vision_errors: int = 0
    decisions_made: int = 0
    actions_executed: int = 0
    uptime_seconds: float = 0.0
    
    def net_profit(self) -> float:
        """Calculate net profit."""
        return self.pot_won - self.pot_lost


@dataclass
class BotInstance:
    """
    Single bot instance.
    
    Attributes:
        bot_id: Unique bot identifier
        account: Associated account
        roi_config: ROI configuration
        status: Current status
        current_table: Current table name
        stack: Current stack size
        collective_edge: Current collective edge (if in HIVE)
        stats: Bot statistics
        start_time: Start timestamp
        error_message: Last error message
    
    ⚠️ EDUCATIONAL NOTE:
        Represents single bot instance for coordinated operation.
    """
    bot_id: str = field(default_factory=lambda: str(uuid4()))
    account: Optional[Account] = None
    roi_config: Optional[ROIConfig] = None
    settings: BotSettings = field(default_factory=BotSettings)
    status: BotStatus = BotStatus.IDLE
    current_table: str = ""
    stack: float = 0.0
    collective_edge: float = 0.0
    stats: BotStatistics = field(default_factory=BotStatistics)
    start_time: Optional[float] = None
    error_message: str = ""

    # Per-bot profile (settings.md Phase 2)
    profile_name: str = ""
    _profile: Optional[Any] = field(default=None, repr=False)
    _profile_manager: Optional[Any] = field(default=None, repr=False)

    # Account binding (account_binding.md Phase 2)
    _binding: Optional[Any] = field(default=None, repr=False)
    _binder: Optional[Any] = field(default=None, repr=False)

    # Auto-ROI detection (roadmap11 Phase 4)
    _auto_roi_zones: list = field(default_factory=list, repr=False)
    _auto_roi_anchors: list = field(default_factory=list, repr=False)
    _auto_roi_hwnd: Optional[int] = field(default=None, repr=False)
    _auto_roi_last_refresh: float = 0.0
    _screen_capture: Optional[Any] = field(default=None, repr=False)

    # Internal state
    _running: bool = False
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _roi_refresh_task: Optional[asyncio.Task] = field(default=None, repr=False)
    _bot_thread: Optional[threading.Thread] = field(default=None, repr=False)
    _bot_loop: Optional[asyncio.AbstractEventLoop] = field(default=None, repr=False)

    # Live play components (Phase 3–6)
    _lobby_scanner: Optional[Any] = field(default=None, repr=False)
    _nav_manager: Optional[Any] = field(default=None, repr=False)
    _state_bridge: Optional[Any] = field(default=None, repr=False)
    _decision_engine: Optional[Any] = field(default=None, repr=False)
    _action_executor: Optional[Any] = field(default=None, repr=False)
    _collusion_coordinator: Optional[Any] = field(default=None, repr=False)
    _mouse_guard: Optional[Any] = field(default=None, repr=False)
    _human_paused: bool = False
    _human_timer: Optional[Any] = field(default=None, repr=False)
    _live_mode: bool = False
    _vision_error_count: int = 0
    _hands_this_session: int = 0
    _current_hand_id: str = ""
    _last_turn_time: float = 0.0
    _reconnect_attempts: int = 0
    _ps_table_hwnd: Optional[int] = field(default=None, repr=False)
    _cp_table_hwnd: Optional[int] = field(default=None, repr=False)
    
    def is_active(self) -> bool:
        """Check if bot is active."""
        return self.status in [
            BotStatus.STARTING,
            BotStatus.SEARCHING,
            BotStatus.SEATED,
            BotStatus.PLAYING
        ]
    
    def can_start(self) -> bool:
        """Check if bot can be started (from IDLE or STOPPED state)."""
        if self.status not in (BotStatus.IDLE, BotStatus.STOPPED) or self.account is None:
            return False
        # Allow start if window is captured (ROI optional — runs in test mode)
        return (
            self.account.window_info.is_captured() and
            not self.account.bot_running and
            self.account.status.value != "error"
        )

    # -- Per-bot profile loading (settings.md Phase 2) -----------------------

    def load_profile(
        self,
        profile_name: str,
        manager: Optional[Any] = None,
    ) -> bool:
        """Load a named profile and apply its settings.

        Args:
            profile_name: Profile key (e.g. "shark", "tag").
            manager: Optional BotProfileManager instance.
                     If not provided, uses self._profile_manager or creates
                     a default one from ``config/bot_profiles.json``.

        Returns:
            True if profile was loaded successfully.
        """
        if not HAS_PROFILE_MANAGER:
            logger.warning("BotProfileManager not available — cannot load profile")
            return False

        mgr = manager or self._profile_manager
        if mgr is None:
            mgr = BotProfileManager()
            self._profile_manager = mgr

        profile = mgr.get_profile(profile_name)
        if profile is None:
            logger.warning("Profile '%s' not found", profile_name)
            return False

        settings = mgr.profile_to_settings(profile_name)
        if settings is None:
            return False

        self.settings = settings
        self.profile_name = profile_name
        self._profile = profile
        mgr.set_active_profile(self.bot_id, profile_name)

        logger.info(
            "Bot %s loaded profile '%s' (aggression=%d, equity=%.2f)",
            self.bot_id[:8], profile_name,
            settings.aggression_level, settings.equity_threshold,
        )
        return True

    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different profile on the fly.

        Same as load_profile but logs the transition.
        """
        old = self.profile_name or "(none)"
        ok = self.load_profile(profile_name)
        if ok:
            logger.info("Bot %s switched profile: %s → %s",
                        self.bot_id[:8], old, profile_name)
        return ok

    def get_profile(self) -> Optional[Any]:
        """Return the currently loaded BotProfile (or None)."""
        return self._profile

    def get_profile_dict(self) -> Dict[str, Any]:
        """Return current profile as dict (for UI / API)."""
        if self._profile and hasattr(self._profile, "to_dict"):
            return self._profile.to_dict()
        return {}

    # -- Account binding (account_binding.md Phase 2) -------------------------

    def load_binding(
        self,
        binder: Optional[Any] = None,
        *,
        auto_bind: bool = True,
    ) -> bool:
        """Load account binding at startup.

        Looks up or creates a binding for this bot in the
        :class:`BotAccountBinder`. If *auto_bind* is True, also tries
        to discover the window automatically by nickname.

        Args:
            binder: Optional BotAccountBinder instance.
                    If not provided, uses self._binder or creates a default.
            auto_bind: Attempt window auto-discovery.

        Returns:
            True if a binding is associated (even if window not yet found).
        """
        if not HAS_ACCOUNT_BINDER:
            logger.warning("BotAccountBinder not available — cannot load binding")
            return False

        mgr = binder or self._binder
        if mgr is None:
            mgr = BotAccountBinder(auto_save=False)
            self._binder = mgr

        nickname = self.account.nickname if self.account else ""
        room = self.account.room if self.account else ""
        account_id = self.account.account_id if self.account else ""

        # Use bind_from_account if we have an account object
        if self.account is not None:
            binding = mgr.bind_from_account(
                self.bot_id,
                self.account,
                auto_find=auto_bind,
            )
        else:
            binding = mgr.bind(
                self.bot_id,
                nickname=nickname,
                room=room,
                account_id=account_id,
            )
            if auto_bind:
                mgr.auto_bind(self.bot_id)
                binding = mgr.get(self.bot_id) or binding

        self._binding = binding
        self._binder = mgr
        logger.info(
            "Bot %s binding loaded: nickname=%r window=%r status=%s",
            self.bot_id[:8],
            binding.nickname,
            binding.title or "(none)",
            binding.status.value,
        )
        return True

    def get_binding(self) -> Optional[Any]:
        """Return the current Binding or None."""
        return self._binding

    def get_binding_dict(self) -> Dict[str, Any]:
        """Return current binding as dict (for UI / API)."""
        if self._binding and hasattr(self._binding, "to_dict"):
            return self._binding.to_dict()
        return {}

    def check_binding_health(self) -> Optional[str]:
        """Check if bound window is still alive.

        Returns status string or None if no binder.
        """
        if not HAS_ACCOUNT_BINDER or self._binder is None:
            return None
        status = self._binder.check_health(self.bot_id)
        if self._binding:
            self._binding = self._binder.get(self.bot_id) or self._binding
        return status.value if hasattr(status, "value") else str(status)

    def rebind_window(self) -> bool:
        """Try to re-discover the window (e.g. after poker client restart)."""
        if not HAS_ACCOUNT_BINDER or self._binder is None:
            return False
        result = self._binder.auto_bind(self.bot_id)
        if result:
            self._binding = result
        return result is not None and result.is_bound

    # -- Auto-ROI detection (roadmap11 Phase 4) --------------------------------

    def auto_detect_roi(
        self,
        *,
        keywords: Optional[list] = None,
        process_names: Optional[list] = None,
        force: bool = False,
    ) -> list:
        """Auto-detect ROI zones via anchor template matching.

        Pipeline:
          1. ``auto_find_window()`` → find poker client HWND
          2. Capture screenshot from the found window
          3. ``find_anchors(image)`` → locate anchors via template matching
          4. ``calculate_relative_roi(anchors)`` → derive ROI zones
          5. If anchors not found → fallback to relative config percentages

        Args:
            keywords:      Title keywords (defaults to ScreenCapture.POKER_TITLE_KEYWORDS).
            process_names: Process names (defaults to ScreenCapture.POKER_PROCESS_NAMES).
            force:         Force refresh even if interval hasn't elapsed.

        Returns:
            List of ROIZone dicts (from anchor_detector).
        """
        if not HAS_ANCHOR_DETECTOR:
            logger.warning("anchor_detector not available — cannot auto-detect ROI")
            return self._auto_roi_zones

        # Throttle: skip if refreshed recently (unless forced)
        now = time.time()
        if not force and (now - self._auto_roi_last_refresh) < AUTO_ROI_REFRESH_INTERVAL:
            return self._auto_roi_zones

        # Step 1: find the poker window
        hwnd = self._auto_find_window_for_roi(keywords, process_names)
        if hwnd is None:
            logger.warning("auto_detect_roi: no window found — keeping previous zones")
            return self._auto_roi_zones

        # Step 2: capture screenshot
        image = self._capture_window_image(hwnd)
        if image is None:
            logger.warning("auto_detect_roi: capture failed — keeping previous zones")
            return self._auto_roi_zones

        # Step 3+4: detect anchors → compute ROI
        try:
            cfg = load_anchor_config()
        except Exception as exc:
            logger.warning("auto_detect_roi: config load failed: %s", exc)
            return self._fallback_relative_roi()

        anchors, zones = detect_roi(image, config=cfg)

        if not anchors:
            logger.info("auto_detect_roi: no anchors found — using fallback")
            zones_list = self._fallback_relative_roi()
        else:
            zones_list = [z.to_dict() if hasattr(z, "to_dict") else z for z in zones]
            for a in anchors:
                logger.info(
                    "Anchor '%s' found at (%d, %d) conf=%.3f",
                    a.name, a.x, a.y, a.confidence,
                )
            logger.info(
                "auto_detect_roi: %d anchors, %d zones computed",
                len(anchors), len(zones),
            )

        self._auto_roi_anchors = anchors
        self._auto_roi_zones = zones_list
        self._auto_roi_hwnd = hwnd
        self._auto_roi_last_refresh = now

        return zones_list

    def _auto_find_window_for_roi(
        self,
        keywords: Optional[list] = None,
        process_names: Optional[list] = None,
    ) -> Optional[int]:
        """Find poker window HWND using ScreenCapture."""
        if not HAS_SCREEN_CAPTURE:
            logger.debug("ScreenCapture not available")
            return None

        try:
            if self._screen_capture is None:
                self._screen_capture = ScreenCapture()

            hwnd = self._screen_capture.auto_find_window(
                keywords=keywords,
                process_names=process_names,
                save_config=True,
            )
            return hwnd
        except Exception as exc:
            logger.warning("auto_find_window failed: %s", exc)
            return None

    def _capture_window_image(self, hwnd: int):
        """Capture a screenshot from HWND and return as numpy array (or None)."""
        if self._screen_capture is None:
            return None
        try:
            import cv2
            import numpy as np
            # Prefer capture_full_window (correct API)
            img = self._screen_capture.capture_full_window(hwnd=hwnd)
            if img is None:
                return None
            if hasattr(img, "shape"):
                return img
            if hasattr(img, "convert"):
                return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.warning("capture_window_image failed: %s", exc)
        return None

    def _fallback_relative_roi(self) -> list:
        """Fallback: compute ROI from config-based relative percentages.

        Uses the ``relative`` coordinates in ``anchor_templates.yaml``
        to place zones without actual template matching.
        """
        try:
            cfg = load_anchor_config()
        except Exception:
            return []

        fallback_zones = []
        # Use a default 800x600 window if no window captured
        w, h = 800, 600

        for name, anchor_cfg in cfg.get("anchors", {}).items():
            rel = anchor_cfg.get("relative", {})
            roi_offsets = anchor_cfg.get("roi_offsets", {})

            # Anchor center from relative coords
            ax = int((rel.get("x_min", 0) + rel.get("x_max", 0)) / 2 * w)
            ay = int((rel.get("y_min", 0) + rel.get("y_max", 0)) / 2 * h)

            for roi_name, offsets in roi_offsets.items():
                dx = offsets.get("dx", 0)
                dy = offsets.get("dy", 0)
                rw = offsets.get("w", 100)
                rh = offsets.get("h", 50)

                rx = max(0, min(ax + dx, w - rw))
                ry = max(0, min(ay + dy, h - rh))

                fallback_zones.append({
                    "name": roi_name,
                    "x": rx, "y": ry,
                    "w": rw, "h": rh,
                    "source": f"fallback_{name}",
                    "confidence": 0.0,
                })

        logger.info("Fallback ROI: %d zones from config percentages", len(fallback_zones))
        return fallback_zones

    def get_auto_roi_zones(self) -> list:
        """Return current auto-detected ROI zones."""
        return list(self._auto_roi_zones)

    def get_auto_roi_info(self) -> Dict[str, Any]:
        """Return auto-ROI status info for UI/API."""
        return {
            "hwnd": self._auto_roi_hwnd,
            "anchor_count": len(self._auto_roi_anchors),
            "zone_count": len(self._auto_roi_zones),
            "last_refresh": self._auto_roi_last_refresh,
            "refresh_interval": AUTO_ROI_REFRESH_INTERVAL,
            "anchors": [
                {"name": a.name, "x": a.x, "y": a.y, "confidence": round(a.confidence, 3)}
                for a in self._auto_roi_anchors
                if hasattr(a, "name")
            ],
        }

    async def _auto_roi_refresh_loop(self):
        """Background task: refresh anchor detection every 30 seconds."""
        while self._running:
            try:
                self.auto_detect_roi()
            except Exception as exc:
                logger.warning("auto_roi_refresh error: %s", exc)
            await asyncio.sleep(AUTO_ROI_REFRESH_INTERVAL)

    def start(self):
        """Start bot — launches a dedicated thread with its own asyncio event loop."""
        if not self.can_start():
            logger.error("Bot %s cannot start (status=%s)", self.bot_id[:8], self.status.value)
            return

        nick = self.account.nickname if self.account else self.bot_id[:8]
        logger.info("Starting bot %s (%s)…", self.bot_id[:8], nick)

        self._running   = True
        self.status     = BotStatus.STARTING
        self.start_time = time.time()

        # Clear any lingering stop flag from a previous run
        if self._nav_manager is not None:
            try:
                self._nav_manager.reset_stop()
            except Exception:
                pass

        # Auto-detect ROI synchronously before spawning thread
        if HAS_ANCHOR_DETECTOR:
            try:
                self.auto_detect_roi(force=True)
                logger.info(
                    "Bot %s auto-ROI: %d zones", self.bot_id[:8], len(self._auto_roi_zones)
                )
            except Exception as exc:
                logger.warning("Auto-ROI failed at start: %s", exc)

        # Register with global MouseGuard (shared across all bots)
        if HAS_MOUSE_GUARD:
            try:
                guard = MouseGuard.get_global()
                guard.register_pause_callback(self._on_mouse_pause)
                guard.register_resume_callback(self._on_mouse_resume)
                if not guard._running:
                    guard.start()
                self._mouse_guard = guard
            except Exception as exc:
                logger.warning("MouseGuard init failed: %s", exc)

        # Spawn dedicated thread — avoids Qt/asyncio event loop conflicts
        self._bot_thread = threading.Thread(
            target=self._thread_run,
            name=f"bot-{nick[:12]}",
            daemon=True,
        )
        self._bot_thread.start()
        logger.info("Bot %s thread started", self.bot_id[:8])

    def _thread_run(self) -> None:
        """Thread target: create a private asyncio event loop and run the bot."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._bot_loop = loop
        try:
            loop.run_until_complete(self._run_loop())
        except Exception as exc:
            logger.error("Bot %s thread error: %s", self.bot_id[:8], exc)
        finally:
            # Clean up the loop
            try:
                pending = asyncio.all_tasks(loop)
                for t in pending:
                    t.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            loop.close()
            self._bot_loop = None
            logger.info("Bot %s thread finished", self.bot_id[:8])

    def stop(self):
        """Stop the bot — signals the loop to exit and waits for the thread."""
        nick = self.account.nickname if self.account else self.bot_id[:8]
        logger.info("Stopping bot %s (%s)…", self.bot_id[:8], nick)

        self._running = False

        # Abort any in-flight navigation immediately (stops pyautogui clicks)
        if self._nav_manager is not None:
            try:
                self._nav_manager.request_stop()
            except Exception:
                pass

        # Cancel the run-loop task if we can reach it
        if self._bot_loop and not self._bot_loop.is_closed():
            try:
                self._bot_loop.call_soon_threadsafe(self._bot_loop.stop)
            except Exception:
                pass

        # Wait for the thread (non-blocking — give it 5 s)
        if self._bot_thread and self._bot_thread.is_alive():
            self._bot_thread.join(timeout=5)

        self.status = BotStatus.STOPPED
        if self.start_time:
            self.stats.uptime_seconds = time.time() - self.start_time
        if self.account:
            self.account.bot_running = False
    
    def set_live_mode(self, live: bool) -> None:
        """Enable or disable LIVE (real-click) mode."""
        self._live_mode = live
        logger.info("Bot %s live_mode=%s", self.bot_id[:8], live)
        if self._nav_manager is not None:
            self._nav_manager.dry_run = not live
            # Switching to DRY-RUN mid-navigation must abort in-flight clicks
            if not live:
                try:
                    self._nav_manager.request_stop()
                except Exception:
                    pass
        # Keep StateBridge in sync so it uses real capture in LIVE mode
        if self._state_bridge is not None:
            if self._state_bridge.dry_run != (not live):
                self._state_bridge.dry_run = not live
                # Propagate to child extractors
                for attr in ("card_extractor", "numeric_parser", "metadata_extractor"):
                    extractor = getattr(self._state_bridge, attr, None)
                    if extractor is not None:
                        try:
                            extractor.dry_run = not live
                        except Exception:
                            pass
                logger.info(
                    "Bot %s: StateBridge dry_run=%s", self.bot_id[:8], not live
                )

    def set_lobby_scanner(self, scanner: Any) -> None:
        self._lobby_scanner = scanner

    def set_nav_manager(self, nav: Any) -> None:
        self._nav_manager = nav

    def set_collusion_coordinator(self, coordinator: Any) -> None:
        """Attach shared CollusionCoordinator for HIVE card sharing."""
        self._collusion_coordinator = coordinator

    def _on_mouse_pause(self) -> None:
        """Called by MouseGuard when human moves the mouse."""
        if not self._human_paused:
            self._human_paused = True
            nick = self.account.nickname if self.account else self.bot_id[:8]
            logger.info("[%s] PAUSED — human mouse input detected", nick)

    def _on_mouse_resume(self) -> None:
        """Called by MouseGuard when pause period expires."""
        if self._human_paused:
            self._human_paused = False
            nick = self.account.nickname if self.account else self.bot_id[:8]
            logger.info("[%s] RESUMED — human pause expired", nick)

    def _should_intentional_fold(self) -> bool:
        """Return True if this action should be a deliberate intentional fold.

        Behavioral divergence: randomly fold good hands at a low rate to
        avoid statistical patterns that link accounts together.
        """
        import random
        rate = 0.04  # default 4%
        if self._profile is not None:
            try:
                div = self._profile.divergence if hasattr(self._profile, "divergence") else {}
                if not div and hasattr(self._profile, "__dict__"):
                    div = getattr(self._profile, "__dict__", {}).get("divergence", {})
                if isinstance(div, dict):
                    rate = float(div.get("intentional_loss_rate", rate))
            except Exception:
                pass
        return random.random() < rate

    async def _run_loop(self):
        """Full bot loop: SEARCHING → JOIN → PLAYING → recovery."""
        nick = self.account.nickname if self.account else self.bot_id[:8]
        try:
            logger.info(
                "[%s] ▶ Bot started (live=%s) — entering SEARCHING loop",
                nick, self._live_mode,
            )
            self.status = BotStatus.SEARCHING
            self._vision_error_count = 0
            self._hands_this_session = 0

            # Lazy-init all live components
            self._init_live_components()

            # ── Check: is a PS table already open? Skip lobby search. ─────────
            if self._live_mode and self._get_room_for_account() == "pokerstars":
                try:
                    from bridge.vision.pokerstars_extractor import find_ps_table_hwnds
                    existing = find_ps_table_hwnds()
                    if existing:
                        hwnd_existing = sorted(existing, reverse=True)[0]
                        logger.info(
                            "[%s] PS table already open (hwnd=%d) — skipping lobby search",
                            nick, hwnd_existing,
                        )
                        self._ps_table_hwnd = hwnd_existing
                        if self._state_bridge is not None:
                            self._state_bridge._hwnd = hwnd_existing
                        try:
                            import win32gui, win32con
                            win32gui.ShowWindow(hwnd_existing, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd_existing)
                        except Exception:
                            pass
                        self.current_table = "PS_Table_existing"
                        self.status = BotStatus.PLAYING
                        self._last_turn_time = time.time()
                except Exception as exc:
                    logger.debug("[%s] existing table check: %s", nick, exc)

            _roi_refresh_counter = 0

            while self._running:
                try:
                    await asyncio.sleep(0.2)
                    if self.start_time:
                        self.stats.uptime_seconds = time.time() - self.start_time

                    # Human mouse takeover — pause all bot actions
                    if self._human_paused:
                        await asyncio.sleep(0.5)
                        continue

                    # Session safety limits
                    if not self._check_session_limits():
                        logger.info("[%s] Session limit reached — stopping", nick)
                        break

                    if self.status == BotStatus.SEARCHING:
                        await self._searching_step()
                    elif self.status == BotStatus.SEATED:
                        await self._seated_step()
                    elif self.status == BotStatus.PLAYING:
                        await self._game_step()
                    elif self.status in (BotStatus.STOPPED, BotStatus.ERROR):
                        break

                    # Periodic ROI refresh every ~25 s (replaces create_task approach)
                    _roi_refresh_counter += 1
                    if _roi_refresh_counter >= 125 and HAS_ANCHOR_DETECTOR:
                        _roi_refresh_counter = 0
                        try:
                            self.auto_detect_roi()
                        except Exception:
                            pass

                except asyncio.CancelledError:
                    raise   # propagate cancel upward
                except Exception as step_exc:
                    logger.error(
                        "[%s] Step error (status=%s): %s",
                        nick, self.status.value, step_exc,
                    )
                    await asyncio.sleep(3)  # pause before retry

        except asyncio.CancelledError:
            logger.info("[%s] Bot loop cancelled by external request", nick)
        except Exception as exc:
            logger.error("[%s] Bot loop fatal error: %s", nick, exc, exc_info=True)
            self.status = BotStatus.ERROR
            self.error_message = str(exc)
        finally:
            logger.info(
                "[%s] ■ Bot loop exited (status=%s, hands=%d)",
                nick, self.status.value, self._hands_this_session,
            )

    # ── Phase 3: Component initialisation ────────────────────────────────────

    def _init_live_components(self) -> None:
        """Lazily initialise lobby scanner, nav manager, state bridge, executor."""
        hwnd = (
            self.account.window_info.hwnd
            if self.account and self.account.window_info
            else None
        )

        room = self._get_room_for_account()

        # Auto-detect poker client window if not yet captured
        if not hwnd:
            try:
                from bridge.screen_capture import ScreenCapture
                _sc = ScreenCapture()
                keywords = ["PokerStars", "Stars "] if room == "pokerstars" else ["CoinPoker"]
                hwnd = _sc.auto_find_window(keywords=keywords)
                if hwnd and self.account and self.account.window_info:
                    self.account.window_info.hwnd = hwnd
                    nick = self.account.nickname if self.account else self.bot_id[:8]
                    logger.info(
                        "[%s] Auto-detected %s hwnd=%d", nick, room, hwnd
                    )
            except Exception as _e:
                pass

        # Lobby scanner
        if self._lobby_scanner is None:
            try:
                from launcher.lobby_scanner import LobbyScanner
                self._lobby_scanner = LobbyScanner(room=room)
                if hwnd:
                    self._lobby_scanner.set_hwnd(hwnd)
                    self._lobby_scanner.set_room(room)
            except Exception as exc:
                logger.debug("LobbyScanner init failed: %s", exc)

        # Navigation manager
        if self._nav_manager is None:
            try:
                from launcher.navigation_manager import NavigationManager
                self._nav_manager = NavigationManager(
                    hwnd=hwnd,
                    dry_run=not self._live_mode,
                )
            except Exception as exc:
                logger.debug("NavigationManager init failed: %s", exc)

        # State bridge (Phase 4)
        if self._state_bridge is None:
            try:
                from bridge.state_bridge import StateBridge
                from bridge.safety import SafetyFramework, SafetyMode
                fw = SafetyFramework.get_instance()
                is_live = fw.config.mode == SafetyMode.UNSAFE
                self._state_bridge = StateBridge(
                    dry_run=not is_live,
                    hwnd=hwnd,
                    roi_zones=self._auto_roi_zones,
                )
            except Exception as exc:
                logger.debug("StateBridge init failed: %s", exc)

        # Decision engine (Phase 5) — only needed in LIVE mode
        if self._decision_engine is None and self._live_mode:
            try:
                from sim_engine.collective_decision import CollectiveDecisionEngine
                self._decision_engine = CollectiveDecisionEngine()
                logger.info("Bot %s: CollectiveDecisionEngine ready", self.bot_id[:8])
            except Exception as exc:
                logger.debug("DecisionEngine init failed: %s", exc)

        # Action executor (Phase 5) — only in LIVE/UNSAFE mode
        if self._action_executor is None and self._live_mode:
            try:
                from bridge.safety import SafetyFramework, SafetyMode
                from bridge.action.real_executor import RealActionExecutor, RiskLevel
                fw = SafetyFramework.get_instance()
                if fw.config.mode == SafetyMode.UNSAFE:
                    self._action_executor = RealActionExecutor(
                        safety=fw,
                        max_risk_level=RiskLevel.MEDIUM,
                        humanization_enabled=True,
                    )
                    logger.info("Bot %s: RealActionExecutor ready (LIVE)", self.bot_id[:8])
            except Exception as exc:
                logger.debug("RealActionExecutor init: %s", exc)

    # ── Phase 3: SEARCHING step ───────────────────────────────────────────────

    def _get_room_for_account(self) -> str:
        """Return the poker room for this account ('pokerstars' or 'coinpoker')."""
        if self.account and hasattr(self.account, 'room'):
            room = (self.account.room or "").lower()
            if room:
                return room
        return "coinpoker"

    def _get_ps_lobby_hwnd_fresh(self) -> Optional[int]:
        """Find the PokerStars LOBBY window HWND reliably.

        Searches by: process PokerStars.exe + class #32770 + large window size
        + title containing 'Лобби' or 'Lobby'.  Returns None if not found.
        """
        try:
            import win32gui
            import win32process
            import psutil

            ps_pids: set = set()
            for proc in psutil.process_iter(['pid', 'name']):
                if 'pokerstars' in (proc.info.get('name') or '').lower():
                    ps_pids.add(proc.info['pid'])

            if not ps_pids:
                return None

            candidates = []

            def _cb(h, _):
                try:
                    if not win32gui.IsWindowVisible(h):
                        return True
                    _, pid = win32process.GetWindowThreadProcessId(h)
                    if pid not in ps_pids:
                        return True
                    title = win32gui.GetWindowText(h)
                    cls = win32gui.GetClassName(h)
                    rect = win32gui.GetWindowRect(h)
                    w = rect[2] - rect[0]
                    hh = rect[3] - rect[1]
                    title_l = title.lower()
                    # Must be large (lobby) and title matches
                    if w > 600 and hh > 400 and (
                        'лобби' in title_l or 'lobby' in title_l
                    ):
                        candidates.append((h, title, rect))
                except Exception:
                    pass
                return True

            win32gui.EnumWindows(_cb, None)

            if candidates:
                hwnd, title, rect = candidates[0]
                logger.info(
                    "PS lobby HWND fresh lookup: hwnd=%d title=%r rect=%s",
                    hwnd, title, rect,
                )
                return hwnd
        except Exception as exc:
            logger.debug("_get_ps_lobby_hwnd_fresh error: %s", exc)
        return None

    async def _searching_step(self) -> None:
        """Scan the real poker lobby and join the best table."""
        nick = self.account.nickname if self.account else self.bot_id[:8]
        room = self._get_room_for_account()
        hwnd = (
            self.account.window_info.hwnd
            if self.account and self.account.window_info
            else None
        )

        # For PokerStars: always do a fresh HWND lookup to avoid stale handles
        if room == "pokerstars":
            fresh = self._get_ps_lobby_hwnd_fresh()
            if fresh:
                if fresh != hwnd:
                    logger.info(
                        "[%s] PS lobby HWND updated: %s → %d",
                        nick, hwnd, fresh,
                    )
                hwnd = fresh
                if self.account and self.account.window_info:
                    self.account.window_info.hwnd = hwnd
                if self._nav_manager is not None:
                    self._nav_manager.hwnd = hwnd
                if self._lobby_scanner is not None:
                    self._lobby_scanner.set_hwnd(hwnd)

        # Auto-find poker client window if HWND is still not set
        if not hwnd:
            try:
                from bridge.screen_capture import ScreenCapture
                _sc = ScreenCapture()
                if room == "pokerstars":
                    keywords = ["PokerStars", "Stars "]
                else:
                    keywords = ["CoinPoker"]
                hwnd = _sc.auto_find_window(keywords=keywords)
                if hwnd and self.account and self.account.window_info:
                    self.account.window_info.hwnd = hwnd
                    logger.info(
                        "[%s] Auto-detected %s hwnd=%d", nick, room, hwnd
                    )
            except Exception as _e:
                logger.debug("[%s] Auto-find window failed: %s", nick, _e)

        if self._lobby_scanner is None:
            logger.warning("[%s] No lobby scanner — waiting 5s", nick)
            await asyncio.sleep(5)
            return

        # Pass room and HWND to scanner
        if hwnd:
            self._lobby_scanner.set_hwnd(hwnd)
        self._lobby_scanner.set_room(room)

        # ── Real OCR scan ─────────────────────────────────────────────────────
        snapshot = None
        try:
            snapshot = self._lobby_scanner.scan_lobby()
        except Exception as exc:
            logger.warning("[%s] Lobby scan error: %s", nick, exc)

        total = snapshot.total_tables if snapshot else 0

        if total == 0:
            if hwnd:
                logger.info(
                    "[%s] Scanning %s lobby (hwnd=%d)… 0 tables parsed. "
                    "Ensure lobby list is visible. Retrying in 5s…",
                    nick, room.upper(), hwnd,
                )
            else:
                logger.info(
                    "[%s] No %s window captured. "
                    "Go to Accounts tab → Find window first. Retrying in 5s…",
                    nick, room.upper(),
                )
            await asyncio.sleep(5)
            return

        logger.info("[%s] Lobby (%s): %d tables scanned", nick, room, total)

        # ── Auto-read balance from the PS lobby header ─────────────────────────
        balance = getattr(self.account, 'balance', 0.0) if self.account else 0.0
        if room == "pokerstars" and hwnd:
            try:
                live_balance = self._lobby_scanner.read_ps_balance(hwnd)
                if live_balance > 0:
                    if abs(live_balance - balance) > 1:
                        logger.info(
                            "[%s] Balance updated: %.0f → %.0f chips",
                            nick, balance, live_balance,
                        )
                    balance = live_balance
                    if self.account is not None:
                        self.account.balance = live_balance
                else:
                    logger.warning(
                        "[%s] Balance OCR returned 0 — will pick cheapest table as fallback",
                        nick,
                    )
            except Exception as exc:
                logger.warning("[%s] balance read error: %s", nick, exc)

        # ── Find best opportunity (bankroll check) ─────────────────────────────
        table = snapshot.find_best_opportunity(
            min_humans=0, max_humans=9, min_seats=1, balance=balance
        )

        if table is None:
            if balance > 0:
                logger.info(
                    "[%s] %d tables scanned but none affordable (balance=%.0f) — retrying in 10s…",
                    nick, total, balance,
                )
            else:
                logger.info(
                    "[%s] %d tables found but none match criteria — retrying in 5s…",
                    nick, total,
                )
            await asyncio.sleep(5)
            return

        logger.info(
            "[%s] ★ Target table: '%s'  blinds=%s  buyin_min=%.0f  "
            "balance=%.0f  players=%d/%d  row_y=%d",
            nick, table.table_name, table.stakes, table.buyin_min,
            balance, table.players_seated, table.max_seats, table.row_y_coordinate,
        )
        self.current_table = table.table_name

        # ── Attempt join ──────────────────────────────────────────────────────
        # Suppress MouseGuard before bringing window to front + clicking
        if HAS_MOUSE_GUARD:
            try:
                MouseGuard.get_global().suppress(10.0)
            except Exception:
                pass

        # Bring the lobby window to the foreground before clicking
        if hwnd:
            try:
                import win32gui
                win32gui.ShowWindow(hwnd, 9)   # SW_RESTORE
                win32gui.SetForegroundWindow(hwnd)
                await asyncio.sleep(0.3)
            except Exception:
                pass

        join_ok = False
        if self._nav_manager is not None and hwnd:
            try:
                result = await self._nav_manager.join_table(table, hwnd)
                status_val = result.status.value if hasattr(result.status, 'value') else str(result.status)
                logger.info("[%s] join_table → %s: %s", nick, status_val.upper(), result.message)

                # Pick up balance observed from the buy-in dialog (most reliable source)
                observed_bal = getattr(self._nav_manager, 'last_observed_balance', 0.0)
                if observed_bal > 0 and self.account is not None:
                    if abs(observed_bal - self.account.balance) > 1:
                        logger.info(
                            "[%s] Balance updated from dialog: %.0f → %.0f chips",
                            nick, self.account.balance, observed_bal,
                        )
                    self.account.balance = observed_bal

                if status_val in ("seated", "table_found", "dry_run"):
                    join_ok = True
                else:
                    logger.info("[%s] join failed (%s) — back to SEARCHING", nick, status_val)
                    await asyncio.sleep(3)
            except Exception as exc:
                logger.warning("[%s] join_table error: %s", nick, exc)
                await asyncio.sleep(3)
        elif not hwnd:
            logger.info(
                "[%s] Table '%s' found but no HWND — go to Accounts tab to capture window",
                nick, table.table_name,
            )
            await asyncio.sleep(2)

        if join_ok:
            # Reset seated timer and transition to SEATED (→ PLAYING after window detected)
            self._seated_since = 0.0  # type: ignore[attr-defined]
            self.status = BotStatus.SEATED
            logger.info("[%s] → SEATED, waiting for table window…", nick)
        else:
            self.status = BotStatus.SEARCHING
            self.current_table = ""

    # ── Phase 4: SEATED → PLAYING transition ─────────────────────────────────

    async def _seated_step(self) -> None:
        """Wait until bot is seated at the table and ready to play.

        DRY_RUN: jump straight to _dry_run_game_step simulation.
        LIVE:     wait for PS table window (HWND), then confirm state is readable.
        Timeout:  if not seated within 20 s, go back to SEARCHING.
        """
        await asyncio.sleep(1.0)
        nick = self.account.nickname if self.account else self.bot_id[:8]

        # Always sync live_mode from SafetyFramework (covers the case where mode was
        # changed in Settings AFTER the bot was already started / initialized)
        try:
            from bridge.safety import SafetyFramework, SafetyMode
            fw = SafetyFramework.get_instance()
            actual_live = fw.config.mode == SafetyMode.UNSAFE
            if actual_live != self._live_mode:
                logger.info(
                    "[%s] live_mode synced from SafetyFramework: %s → %s",
                    nick, self._live_mode, actual_live,
                )
                self.set_live_mode(actual_live)
        except Exception:
            pass

        # DRY_RUN mode: still find the table window and focus it, but skip real clicks
        if not self._live_mode:
            room = self._get_room_for_account()
            if room == "coinpoker" and not getattr(self, '_cp_table_hwnd', None):
                await self._wait_for_cp_table_window()
            # Focus the table window so lobby doesn't stay on top
            cp_hwnd = getattr(self, '_cp_table_hwnd', None)
            if cp_hwnd:
                try:
                    import win32gui, win32con
                    win32gui.ShowWindow(cp_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(cp_hwnd)
                except Exception:
                    pass
            logger.info("[%s] DRY_RUN: simulating hand at '%s'", nick, self.current_table)
            self.status = BotStatus.PLAYING
            return

        room = self._get_room_for_account()

        # Track how long we've been SEATED
        if not hasattr(self, '_seated_since') or self._seated_since == 0:
            self._seated_since = time.time()  # type: ignore[attr-defined]

        seated_elapsed = time.time() - getattr(self, '_seated_since', time.time())

        # Timeout: if SEATED > 45 s without getting to a table, retry
        if seated_elapsed > 45.0:
            logger.warning(
                "[%s] SEATED timeout (%.0fs) — no table window detected, back to SEARCHING",
                nick, seated_elapsed,
            )
            self._seated_since = 0  # type: ignore[attr-defined]
            self.status = BotStatus.SEARCHING
            self.current_table = ""
            await asyncio.sleep(2)
            return

        # PokerStars: wait for the table window to appear after buy-in click
        if room == "pokerstars":
            await self._wait_for_ps_table_window()
            # Only proceed to PLAYING if the table window was found
            if not getattr(self, '_ps_table_hwnd', None):
                # Not found yet — stay SEATED, will retry next iteration
                await asyncio.sleep(1.0)
                return

        # CoinPoker: find the new table window and click Take Seat
        elif room == "coinpoker":
            await self._wait_for_cp_table_window()
            if not getattr(self, '_cp_table_hwnd', None):
                await asyncio.sleep(1.0)
                return

        # LIVE: verify window is still alive
        if not self._is_window_alive():
            logger.warning("[%s] Window lost during SEATED — back to SEARCHING", nick)
            self._seated_since = 0  # type: ignore[attr-defined]
            self._cp_table_hwnd = None
            self.status = BotStatus.SEARCHING
            self.current_table = ""
            await asyncio.sleep(3)
            return

        # Transition to PLAYING
        self._seated_since = 0  # type: ignore[attr-defined]
        self.status = BotStatus.PLAYING
        self._last_turn_time = time.time()
        logger.info("[%s] → PLAYING at '%s' (room=%s)", nick, self.current_table, room)

    async def _wait_for_ps_table_window(self) -> None:
        """Wait for a new PokerStars table window to open and update HWND."""
        import asyncio
        nick = self.account.nickname if self.account else self.bot_id[:8]
        try:
            from bridge.vision.pokerstars_extractor import find_ps_table_hwnds
        except Exception as exc:
            logger.debug("[%s] PS table finder unavailable: %s", nick, exc)
            return

        known = set(find_ps_table_hwnds())
        logger.info("[%s] Waiting for PS table window (known=%d)…", nick, len(known))

        # If a table is already open right now (e.g. user manually joined),
        # use it immediately instead of waiting for a NEW one to appear.
        if known and not getattr(self, '_ps_table_hwnd', None):
            table_hwnd = sorted(known, reverse=True)[0]
            logger.info("[%s] Using already-open PS table hwnd=%d", nick, table_hwnd)
            self._ps_table_hwnd = table_hwnd
            if self._state_bridge is not None:
                self._state_bridge._hwnd = table_hwnd
            try:
                import win32gui, win32con
                win32gui.ShowWindow(table_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(table_hwnd)
                win32gui.BringWindowToTop(table_hwnd)
            except Exception as exc:
                logger.debug("[%s] SetForegroundWindow failed: %s", nick, exc)
            return

        for _attempt in range(20):
            await asyncio.sleep(0.8)
            current = set(find_ps_table_hwnds())
            new_hwnds = current - known
            if new_hwnds:
                table_hwnd = sorted(new_hwnds, reverse=True)[0]
                logger.info("[%s] PS table window detected: hwnd=%d", nick, table_hwnd)
                self._ps_table_hwnd = table_hwnd
                if self._state_bridge is not None:
                    self._state_bridge._hwnd = table_hwnd
                try:
                    import win32gui, win32con
                    win32gui.ShowWindow(table_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(table_hwnd)
                    win32gui.BringWindowToTop(table_hwnd)
                    logger.info("[%s] Table window hwnd=%d brought to foreground", nick, table_hwnd)
                except Exception as exc:
                    logger.debug("[%s] SetForegroundWindow failed: %s", nick, exc)
                return

        logger.warning("[%s] PS table window not detected within timeout", nick)

    async def _wait_for_cp_table_window(self) -> None:
        """Wait for a new CoinPoker table window, bring it to front, click Take Seat.

        Detection strategy: find any new visible window from the same process
        as the lobby window (by PID), excluding the lobby itself.
        Table window title is game-specific (e.g. "NL ₮2,000 4 Max I - NL Hold'em…")
        and does NOT contain "CoinPoker", so we match by process PID.
        """
        nick = self.account.nickname if self.account else self.bot_id[:8]
        lobby_hwnd = (
            self.account.window_info.hwnd
            if self.account and self.account.window_info
            else None
        )

        try:
            import win32gui
            import win32con
            import win32process
        except ImportError:
            logger.warning("[%s] win32gui not available — cannot find table window", nick)
            return

        # Get the PID of the CoinPoker lobby process
        lobby_pid = None
        if lobby_hwnd:
            try:
                _, lobby_pid = win32process.GetWindowThreadProcessId(lobby_hwnd)
            except Exception:
                pass

        def _enum_table_hwnds() -> list:
            """Return visible windows belonging to CoinPoker process, excluding lobby."""
            results = []
            def _cb(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return
                if hwnd == lobby_hwnd:
                    return
                try:
                    # Match by process PID
                    if lobby_pid:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid != lobby_pid:
                            return
                    else:
                        # Fallback: match by title containing poker keywords
                        title = win32gui.GetWindowText(hwnd).lower()
                        if not any(k in title for k in (
                            "hold'em", "holdem", "nl ", "pl ", "omaha",
                            "max", "blinds", "ante", "coinpoker",
                        )):
                            return
                    # Exclude tiny/invisible windows (< 200px wide)
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    if w < 200:
                        return
                    results.append(hwnd)
                except Exception:
                    pass
            win32gui.EnumWindows(_cb, None)
            return results

        # Snapshot windows known BEFORE waiting
        known = set(_enum_table_hwnds())
        if lobby_hwnd:
            known.add(lobby_hwnd)

        logger.info(
            "[%s] Waiting for CoinPoker table window (lobby_pid=%s, known=%d)…",
            nick, lobby_pid, len(known),
        )

        for _attempt in range(30):        # up to ~24 s
            await asyncio.sleep(0.8)
            current = set(_enum_table_hwnds())
            new_hwnds = current - known
            if new_hwnds:
                table_hwnd = sorted(new_hwnds, reverse=True)[0]
                title = win32gui.GetWindowText(table_hwnd)
                self._cp_table_hwnd = table_hwnd
                if self._state_bridge is not None:
                    try:
                        self._state_bridge._hwnd = table_hwnd
                    except Exception:
                        pass
                logger.info(
                    "[%s] Table window detected hwnd=%d title='%s'",
                    nick, table_hwnd, title,
                )
                # Bring to front
                try:
                    win32gui.ShowWindow(table_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(table_hwnd)
                except Exception as exc:
                    logger.debug("[%s] SetForegroundWindow: %s", nick, exc)

                await asyncio.sleep(0.6)
                await self._click_cp_take_seat(table_hwnd)
                return

        # Last resort: if still SEATED but a table window exists from the same process,
        # use that even if it was "known" before (handles re-entry after disconnect)
        all_cp = _enum_table_hwnds()
        for hwnd in sorted(all_cp, reverse=True):
            if hwnd == lobby_hwnd:
                continue
            title = win32gui.GetWindowText(hwnd)
            logger.info(
                "[%s] Using existing table window hwnd=%d title='%s'",
                nick, hwnd, title,
            )
            self._cp_table_hwnd = hwnd
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            await asyncio.sleep(0.5)
            await self._click_cp_take_seat(hwnd)
            return

        logger.warning("[%s] CoinPoker table window not detected within timeout", nick)

    async def _click_cp_take_seat(self, hwnd: int) -> None:
        """Find and click a 'Take Seat' button in the CoinPoker table window.

        Strategy:
        1. Minimize lobby so it can't intercept the click.
        2. Capture screenshot of the TABLE window only.
        3. Use OCR to find 'Take Seat' / 'Seat' text and click it.
        4. Fall back to fixed candidate positions if OCR fails.
        """
        nick = self.account.nickname if self.account else self.bot_id[:8]
        lobby_hwnd = (
            self.account.window_info.hwnd
            if self.account and self.account.window_info
            else None
        )

        try:
            import win32gui, win32con
            import pyautogui

            rect = win32gui.GetWindowRect(hwnd)
            win_x, win_y = rect[0], rect[1]
            win_w = rect[2] - rect[0]
            win_h = rect[3] - rect[1]

            if HAS_MOUSE_GUARD:
                try:
                    MouseGuard.get_global().suppress(10.0)
                except Exception:
                    pass

            # ── Step 1: Minimize lobby ────────────────────────────────────────
            if lobby_hwnd and lobby_hwnd != hwnd:
                try:
                    win32gui.ShowWindow(lobby_hwnd, win32con.SW_MINIMIZE)
                    await asyncio.sleep(0.4)
                except Exception:
                    pass

            # ── Step 2: Bring table window to front ───────────────────────────
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            await asyncio.sleep(0.6)

            # ── Step 3: Capture table window and find Take Seat via OCR ──────
            click_x, click_y = None, None
            try:
                import numpy as np
                from launcher.vision.window_capturer import WindowCapturer
                capturer = WindowCapturer()
                img = capturer.capture_window(hwnd)
                if img is not None:
                    try:
                        import pytesseract
                        data = pytesseract.image_to_data(
                            img,
                            config="--psm 11",
                            output_type=pytesseract.Output.DICT,
                        )
                        keywords = {"TAKE", "SEAT", "Take", "Seat"}
                        for i, txt in enumerate(data.get("text", [])):
                            if txt.strip() in keywords and int(data["conf"][i]) > 30:
                                bx = data["left"][i] + data["width"][i] // 2
                                by = data["top"][i] + data["height"][i] // 2
                                click_x = win_x + bx
                                click_y = win_y + by
                                logger.info(
                                    "[%s] OCR found '%s' at table-rel (%d,%d) → screen (%d,%d)",
                                    nick, txt.strip(), bx, by, click_x, click_y,
                                )
                                break
                    except Exception as ocr_exc:
                        logger.debug("[%s] OCR error: %s", nick, ocr_exc)
            except Exception as cap_exc:
                logger.debug("[%s] Capture error: %s", nick, cap_exc)

            # ── Step 4: Fall back to candidate positions ──────────────────────
            if click_x is None:
                # Typical CoinPoker 4-max table seat positions (relative fractions)
                candidates = [
                    (0.25, 0.75),   # bottom-left
                    (0.65, 0.75),   # bottom-right
                    (0.18, 0.22),   # top-left
                    (0.75, 0.22),   # top-right
                    (0.50, 0.85),   # bottom-center
                ]
                fx, fy = candidates[0]
                click_x = win_x + int(win_w * fx)
                click_y = win_y + int(win_h * fy)
                logger.info(
                    "[%s] Take Seat fallback at screen (%d,%d) win=%dx%d",
                    nick, click_x, click_y, win_w, win_h,
                )

            # ── Step 5: Click ─────────────────────────────────────────────────
            if HAS_MOUSE_GUARD:
                try:
                    MouseGuard.get_global().suppress(4.0)
                except Exception:
                    pass

            pyautogui.moveTo(click_x, click_y, duration=0.25)
            await asyncio.sleep(0.15)
            pyautogui.click(click_x, click_y)
            await asyncio.sleep(0.5)
            logger.info("[%s] Take Seat click done", nick)

        except Exception as exc:
            logger.warning("[%s] _click_cp_take_seat error: %s", nick, exc)
        finally:
            # ── Always restore lobby and keep table focused ───────────────────
            try:
                import win32gui as _wg, win32con as _wc
                if lobby_hwnd and lobby_hwnd != hwnd:
                    _wg.ShowWindow(lobby_hwnd, _wc.SW_RESTORE)
                if HAS_MOUSE_GUARD:
                    MouseGuard.get_global().suppress(2.0)
                _wg.SetForegroundWindow(hwnd)
            except Exception:
                pass

    # ── Phase 4: Game state reading ───────────────────────────────────────────

    def _direct_turn_check_ps(self) -> bool:
        """Bypass StateBridge: directly capture PS table and look for red action buttons.

        This is a fallback used when StateBridge.is_bots_turn returns False, to guard
        against dry_run sync failures or _extract_ps_state exceptions that are invisible
        in HIVE Launcher logs (bridge.* logger is filtered out).

        Returns True and updates button cache if action buttons are found on screen.
        """
        hwnd = getattr(self, "_ps_table_hwnd", None)
        if not hwnd:
            return False
        try:
            import win32gui
            import pyautogui
            import numpy as np
            import cv2

            if not win32gui.IsWindow(hwnd):
                return False
            rect = win32gui.GetWindowRect(hwnd)
            wx, wy = rect[0], rect[1]
            ww, wh = rect[2] - rect[0], rect[3] - rect[1]
            if ww < 200 or wh < 200:
                return False

            win32gui.SetForegroundWindow(hwnd)
            import time as _t; _t.sleep(0.15)

            pil = pyautogui.screenshot(region=(wx, wy, ww, wh))
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

            from bridge.vision.pokerstars_extractor import (
                _has_red_buttons_in_bottom,
                detect_action_buttons,
                update_button_cache,
            )

            if _has_red_buttons_in_bottom(img):
                buttons = detect_action_buttons(img)
                if buttons:
                    update_button_cache(buttons)
                    logger.info(
                        "Bot %s: direct visual — buttons found: %s",
                        self.bot_id[:8], list(buttons.keys()),
                    )
                    return True
                # Red blobs exist but OCR didn't name them — still our turn
                logger.info("Bot %s: direct visual — red buttons detected (no OCR names)", self.bot_id[:8])
                return True
        except Exception as exc:
            logger.debug("_direct_turn_check_ps error: %s", exc)
        return False

    def _get_live_state(self) -> Optional[Any]:
        """Read table state from StateBridge."""
        if self._state_bridge is None:
            return None
        try:
            room = self._get_room_for_account()
            # Use TABLE window HWND (PS or CP table), not lobby
            hwnd = self._get_active_table_hwnd()
            if hasattr(self._state_bridge, "get_live_table_state"):
                return self._state_bridge.get_live_table_state(
                    table_id=self.bot_id,
                    room=room,
                    hwnd=hwnd,
                )
            elif hasattr(self._state_bridge, "get_table_state"):
                return self._state_bridge.get_table_state()
        except Exception as exc:
            self._vision_error_count += 1
            self.stats.vision_errors += 1
            logger.debug("get_live_state error: %s", exc)
        return None

    # ── Phase 5: PLAYING step — full game loop ────────────────────────────────

    async def _game_step(self) -> None:
        """Single game loop iteration: read state → decide → act."""
        await asyncio.sleep(0.5)

        if not self._live_mode:
            await self._dry_run_game_step()
            return

        # ── Phase 7: window-alive check ───────────────────────────────────────
        if not self._is_window_alive():
            self._reconnect_attempts += 1
            logger.warning(
                "Bot %s: window lost (attempt %d/3) — waiting to reconnect…",
                self.bot_id[:8], self._reconnect_attempts,
            )
            if self._reconnect_attempts >= 3:
                logger.error("Bot %s: window lost after 3 attempts — back to SEARCHING",
                             self.bot_id[:8])
                self._reconnect_attempts = 0
                self.status = BotStatus.SEARCHING
                self.current_table = ""
            await asyncio.sleep(5)
            return

        self._reconnect_attempts = 0

        # ── Check table window is still open (CoinPoker) ─────────────────────
        cp_hwnd = getattr(self, "_cp_table_hwnd", None)
        if cp_hwnd:
            try:
                import win32gui
                if not win32gui.IsWindow(cp_hwnd):
                    logger.info(
                        "Bot %s: CoinPoker table window closed — back to SEARCHING",
                        self.bot_id[:8],
                    )
                    self._cp_table_hwnd = None
                    self.status = BotStatus.SEARCHING
                    self.current_table = ""
                    return
            except Exception:
                pass

        # ── Check table window is still open (PokerStars) ─────────────────────
        ps_hwnd = getattr(self, "_ps_table_hwnd", None)
        if ps_hwnd:
            try:
                import win32gui
                if not win32gui.IsWindow(ps_hwnd):
                    logger.info(
                        "Bot %s: PokerStars table window closed — back to SEARCHING",
                        self.bot_id[:8],
                    )
                    self._ps_table_hwnd = None
                    self.status = BotStatus.SEARCHING
                    self.current_table = ""
                    return
            except Exception:
                pass

        # ── Phase 7: stuck-turn timeout (>60 s) → auto-fold ──────────────────
        TURN_TIMEOUT = 60.0
        if (self._last_turn_time and
                time.time() - self._last_turn_time > TURN_TIMEOUT and
                self._action_executor is not None):
            logger.warning(
                "Bot %s: turn timeout (>%ds) — auto-folding",
                self.bot_id[:8], int(TURN_TIMEOUT),
            )
            await self._emergency_fold()
            self._last_turn_time = time.time()
            return

        # --- LIVE path ---
        state = self._get_live_state()
        if state is None:
            # Don't abandon a table we're sitting at — give it more time
            table_hwnd = getattr(self, "_cp_table_hwnd", None) or getattr(self, "_ps_table_hwnd", None)
            error_limit = 30 if table_hwnd else 5
            if self._vision_error_count >= error_limit:
                logger.warning(
                    "Bot %s: too many vision errors (%d), returning to SEARCHING",
                    self.bot_id[:8], self._vision_error_count,
                )
                self._vision_error_count = 0
                self._cp_table_hwnd = None
                self.status = BotStatus.SEARCHING
                self.current_table = ""
            return

        self._vision_error_count = 0

        # ── Phase 6: HIVE card sharing ────────────────────────────────────────
        hero_cards = []
        if hasattr(state, "get_hero_cards"):
            try:
                hero_cards = state.get_hero_cards() or []
            except Exception:
                pass

        known_opp_cards: list = []
        if hero_cards and self._collusion_coordinator is not None:
            try:
                import uuid
                hand_num = getattr(state, "hand_number", 0)
                if not self._current_hand_id or hand_num != getattr(self, "_last_hand_num", -1):
                    self._current_hand_id = str(uuid.uuid4())[:8]
                    self._last_hand_num = hand_num  # type: ignore[attr-defined]

                table_id = self.current_table or "table_unknown"
                result = self._collusion_coordinator.coordinate_hand(
                    bot_id=self.bot_id,
                    table_id=table_id,
                    hand_id=self._current_hand_id,
                    hole_cards=hero_cards,
                )
                if result and result.get("is_complete"):
                    known_opp_cards = [
                        c for c in result.get("known_cards", [])
                        if c not in hero_cards
                    ]
            except Exception as exc:
                logger.debug("HIVE card share error: %s", exc)

        # Check if it's our turn
        is_our_turn = getattr(state, "is_bots_turn", False)

        # Log state so it's visible in HIVE Launcher (bridge.* logs are filtered there)
        room = self._get_room_for_account()
        if room == "pokerstars":
            hero_cards_log = []
            try:
                hero_cards_log = state.players[0].hole_cards if state.players else []
            except Exception:
                pass
            logger.info(
                "Bot %s: PS state turn=%s hero=%s pot=%.0f",
                self.bot_id[:8], is_our_turn, hero_cards_log,
                getattr(state, "pot", 0),
            )

        # Fallback: if StateBridge says not our turn, do a direct visual check
        # (guards against dry_run sync failures invisible in HIVE Launcher)
        if not is_our_turn and room == "pokerstars":
            is_our_turn = self._direct_turn_check_ps()
            if is_our_turn:
                try:
                    state.is_bots_turn = True
                except Exception:
                    pass

        if not is_our_turn:
            await asyncio.sleep(0.5)
            return

        # Our turn confirmed — reset turn timer
        self._last_turn_time = time.time()

        # Get decision
        try:
            decision = self._make_decision(state, room, known_opp_cards)
        except Exception as exc:
            logger.debug("decision engine error: %s", exc)
            return

        if decision is None:
            return

        # Behavioral divergence: intentional fold to avoid account linking
        if self._should_intentional_fold():
            decision_action = getattr(decision, "action", None)
            action_str_check = str(getattr(decision_action, "value", decision_action)).lower()
            if action_str_check not in ("fold",):
                logger.debug(
                    "Bot %s: intentional fold (behavioral divergence)", self.bot_id[:8]
                )
                # Replace decision with fold
                try:
                    from sim_engine.collective_decision import ActionType, CollectiveDecision, LineType
                    decision = CollectiveDecision(
                        action=ActionType.FOLD,
                        line_type=LineType.PASSIVE,
                        reasoning="intentional_divergence",
                        confidence=1.0,
                    )
                except Exception:
                    pass

        # Execute action
        if self._action_executor is None:
            return
        try:
            from bridge.action.real_executor import ActionCoordinates

            action_type = getattr(decision, "action", None)
            action_str  = str(getattr(action_type, "value", action_type)).lower()
            amount      = getattr(decision, "bet_size", None) or getattr(decision, "amount", 0.0)
            xy          = self._get_action_coords(action_type)

            # Apply human-like timing delay before action (anti-detection)
            if HAS_HUMAN_TIMING:
                if self._human_timer is None:
                    profile = self.profile_name or "default"
                    self._human_timer = make_timing(profile)
                equity = getattr(decision, "confidence", 0.5)
                is_first = (self._current_hand_action_count == 0)
                delay = self._human_timer.pre_action_delay(
                    hand_equity=equity,
                    action=action_str,
                    is_first_action=is_first,
                )
                await asyncio.sleep(delay)

            if xy is None:
                logger.debug("No coords for action %s — skipping", action_str)
                return

            # For PS raise/bet: need to enter amount in bet field
            if room == "pokerstars" and action_str in ("raise", "bet") and amount:
                await self._execute_ps_bet(action_str, xy, amount)
            else:
                coords = ActionCoordinates(button_x=xy[0], button_y=xy[1])
                result = self._action_executor.execute_action(
                    action_type=action_str,
                    coordinates=coords,
                    amount=None,
                )
                logger.info(
                    "Bot %s: executed %s → %s",
                    self.bot_id[:8], action_str, result.result.value,
                )

            self.stats.actions_executed += 1
            self.stats.decisions_made += 1

            if action_str in ("fold", "check"):
                self._hands_this_session += 1
                self.stats.hands_played += 1
                logger.info(
                    "Bot %s: hand #%d (session) / #%d (total) completed",
                    self.bot_id[:8], self._hands_this_session, self.stats.hands_played,
                )

        except Exception as exc:
            logger.warning("action execution error: %s", exc)

    def _make_decision(self, state: Any, room: str, known_opp_cards: list) -> Optional[Any]:
        """Make a decision using PokerAI (PS) or CollectiveDecisionEngine (other)."""
        # PokerStars: use the strong PokerAI engine
        if room == "pokerstars":
            try:
                from sim_engine.poker_ai import PokerAI, Position as AIPos
                ai = PokerAI(bluff_frequency=0.25)
                (hero_cards, board, pot, hero_stack,
                 to_call, street, position) = PokerAI.from_table_state(state)
                logger.info(
                    "Bot %s: PokerAI decide — cards=%s board=%s pot=%.0f "
                    "stack=%.0f to_call=%.0f pos=%s street=%s",
                    self.bot_id[:8], hero_cards, board, pot,
                    hero_stack, to_call, position.value, street,
                )
                decision = ai.decide(
                    hero_cards=hero_cards,
                    board=board,
                    pot=pot,
                    hero_stack=hero_stack,
                    to_call=to_call,
                    position=position,
                    street=street,
                    legal_actions=["fold", "check", "call", "bet", "raise"],
                )
                logger.info(
                    "Bot %s: PokerAI → %s amount=%.0f (%.0f%%) %s",
                    self.bot_id[:8], decision.action.value, decision.amount,
                    decision.confidence * 100, decision.reasoning[:60],
                )
                return decision
            except Exception as exc:
                logger.warning("PokerAI decision failed: %s", exc)
                return None

        # Other rooms: collective decision engine
        if self._decision_engine is None:
            return None
        collective_state = None
        if hasattr(state, "to_collective_state"):
            try:
                collective_state = state.to_collective_state()
            except Exception:
                pass
        if collective_state is not None and hasattr(self._decision_engine, "decide"):
            return self._decision_engine.decide(
                collective_state,
                known_opponent_cards=known_opp_cards or None,
            )
        if hasattr(self._decision_engine, "get_decision"):
            return self._decision_engine.get_decision(state)
        return None

    async def _execute_ps_bet(
        self,
        action_str: str,
        button_xy: tuple,
        amount: float,
    ) -> None:
        """Click raise/bet button on PS, then type the amount and confirm."""
        import asyncio
        try:
            import pyautogui as pag
        except ImportError:
            logger.warning("pyautogui not available for PS bet")
            return
        try:
            # 1. Click the raise/bet button
            logger.info("PS %s: clicking button at %s", action_str, button_xy)
            pag.moveTo(button_xy[0], button_xy[1], duration=0.2)
            await asyncio.sleep(0.15)
            pag.click(*button_xy)
            await asyncio.sleep(0.4)

            # 2. Find and type into the bet amount field
            bet_field_xy = self._get_ps_action_coords("bet_amount_field")
            if bet_field_xy:
                pag.click(*bet_field_xy)
                await asyncio.sleep(0.15)
            pag.hotkey("ctrl", "a")
            await asyncio.sleep(0.1)
            pag.typewrite(str(int(amount)), interval=0.04)
            await asyncio.sleep(0.2)
            pag.press("enter")
            logger.info("PS %s: typed amount=%.0f and confirmed", action_str, amount)
        except Exception as exc:
            logger.warning("_execute_ps_bet error: %s", exc)

    async def _dry_run_game_step(self) -> None:
        """Simulate a realistic poker hand in DRY-RUN mode with full visible logging."""
        import random

        nick  = self.account.nickname if self.account else self.bot_id[:8]
        table = self.current_table or "Unknown Table"

        # Simulate card deal
        suits   = ["♠", "♥", "♦", "♣"]
        ranks   = ["2","3","4","5","6","7","8","9","T","J","Q","K","A"]
        hand    = [f"{random.choice(ranks)}{random.choice(suits)}" for _ in range(2)]
        board   = [f"{random.choice(ranks)}{random.choice(suits)}" for _ in range(3)]

        logger.info("[%s] ── New hand at '%s' ──────────────────────────", nick, table)
        logger.info("[%s] Hole cards dealt: %s %s", nick, hand[0], hand[1])

        await asyncio.sleep(random.uniform(0.8, 1.5))

        # Street decisions
        streets = [
            ("PREFLOP", []),
            ("FLOP",    board),
            ("TURN",    board + [f"{random.choice(ranks)}{random.choice(suits)}"]),
            ("RIVER",   board + [f"{random.choice(ranks)}{random.choice(suits)}",
                                  f"{random.choice(ranks)}{random.choice(suits)}"]),
        ]

        pot  = round(random.uniform(1.0, 5.0), 2)
        won  = False

        for street_name, community in streets:
            board_str = " ".join(community) if community else "(no community)"
            logger.info(
                "[%s] %s — Board: %s  |  Pot: $%.2f",
                nick, street_name, board_str, pot,
            )

            # Equity-based decision simulation
            equity = random.uniform(0.25, 0.85)
            if equity >= 0.65:
                amount = round(pot * random.uniform(0.5, 1.0), 2)
                action = f"RAISE ${amount:.2f}"
                pot   += amount
            elif equity >= 0.45:
                action = "CALL"
                pot   += round(pot * 0.2, 2)
            else:
                action = "FOLD"
                logger.info("[%s] → %s  (equity=%.0f%%)", nick, action, equity * 100)
                self.stats.decisions_made += 1
                self._hands_this_session  += 1
                self.stats.hands_played   += 1
                self.stats.pot_lost       += pot * 0.5
                await asyncio.sleep(random.uniform(0.3, 0.8))
                break

            logger.info("[%s] → %s  (equity=%.0f%%)", nick, action, equity * 100)
            self.stats.decisions_made += 1
            await asyncio.sleep(random.uniform(0.8, 2.0))
        else:
            # Reached showdown
            won = random.random() < 0.55
            if won:
                logger.info("[%s] ★ SHOWDOWN — WON pot $%.2f!", nick, pot)
                self.stats.pot_won  += pot
                self.stack          += pot * 0.5
                self.collective_edge = round(min(self.collective_edge + 0.5, 10.0), 2)
            else:
                logger.info("[%s] SHOWDOWN — lost pot $%.2f", nick, pot)
                self.stats.pot_lost  += pot * 0.5
                self.collective_edge = round(max(self.collective_edge - 0.2, 0.0), 2)
            self._hands_this_session += 1
            self.stats.hands_played  += 1

        await asyncio.sleep(random.uniform(0.5, 1.5))

        # After N hands, leave table and look for a new one
        if self._hands_this_session % 8 == 0 and self._hands_this_session > 0:
            logger.info(
                "[%s] Played %d hands at '%s' — leaving to find next table",
                nick, self._hands_this_session, table,
            )
            self.status        = BotStatus.SEARCHING
            self.current_table = ""
            await asyncio.sleep(2)

    def _get_action_coords(self, action_type: Any) -> Optional[tuple]:
        """Return screen-relative pixel coordinates for fold/call/raise buttons.

        For PokerStars: loads button ROIs from pokerstars.yaml and converts
        to absolute screen coordinates using the table window position.
        For other rooms: falls back to auto-detected ROI zones.
        """
        if action_type is None:
            return None
        action_str = str(getattr(action_type, "value", action_type)).lower()
        zone_map = {
            "fold":  "fold_button",
            "call":  "call_button",
            "check": "check_button",
            "raise": "raise_button",
            "bet":   "raise_button",  # PS uses raise_button ROI for both bet and raise
        }
        zone_name = zone_map.get(action_str)
        if not zone_name:
            return None

        room = self._get_room_for_account()

        # ── PokerStars: use pokerstars.yaml ROIs + PS table HWND ─────────────
        if room == "pokerstars":
            return self._get_ps_action_coords(zone_name)

        # ── Fallback: auto-detected ROI zones (CoinPoker) ────────────────────
        if not self._auto_roi_zones:
            return None
        for z in self._auto_roi_zones:
            name = z.get("name", "") if isinstance(z, dict) else getattr(z, "name", "")
            if zone_name in str(name).lower():
                x = z.get("x", 0) if isinstance(z, dict) else getattr(z, "x", 0)
                y = z.get("y", 0) if isinstance(z, dict) else getattr(z, "y", 0)
                w = z.get("w", 50) if isinstance(z, dict) else getattr(z, "w", 50)
                h = z.get("h", 25) if isinstance(z, dict) else getattr(z, "h", 25)
                return (x + w // 2, y + h // 2)
        return None

    def _get_ps_action_coords(self, roi_name: str) -> Optional[tuple]:
        """Compute absolute screen coordinates for a PS button ROI.

        Priority:
          1. Dynamically detected button positions from the latest frame
             (via detect_action_buttons / get_cached_buttons).
          2. pokerstars.yaml ROI fallback (used when cache is empty).
        """
        # Map YAML roi_name → canonical action name used in button cache
        _ROI_TO_ACTION = {
            "fold_button":  "fold",
            "check_button": "check",
            "call_button":  "call",
            "raise_button": "raise",
        }
        action_key = _ROI_TO_ACTION.get(roi_name, roi_name)

        table_hwnd = getattr(self, "_ps_table_hwnd", None)
        win_x, win_y = 0, 0
        if table_hwnd:
            try:
                import win32gui
                rect = win32gui.GetWindowRect(table_hwnd)
                win_x, win_y = rect[0], rect[1]
            except Exception:
                pass

        # 1. Dynamic detection from last captured frame
        try:
            from bridge.vision.pokerstars_extractor import get_cached_buttons
            cached = get_cached_buttons()
            if action_key in cached:
                img_x, img_y = cached[action_key]
                abs_x = win_x + img_x
                abs_y = win_y + img_y
                logger.info(
                    "_get_ps_action_coords: %s → dynamic (%d,%d)",
                    action_key, abs_x, abs_y,
                )
                return (abs_x, abs_y)
            # Safe cross-action aliases (same button in PS for both names)
            _aliases = {
                "bet":   ["raise"],   # PS uses same button for bet and raise
                "raise": ["bet"],     # same
                "call":  ["check"],   # in 2-button layouts leftmost = check = call
            }
            for alt in _aliases.get(action_key, []):
                if alt in cached:
                    img_x, img_y = cached[alt]
                    logger.info(
                        "_get_ps_action_coords: %s → alias '%s' (%d,%d)",
                        action_key, alt, win_x + img_x, win_y + img_y,
                    )
                    return (win_x + img_x, win_y + img_y)
        except Exception as exc:
            logger.debug("dynamic coords lookup error: %s", exc)

        # 2. Fallback: pokerstars.yaml ROI (absolute coords for calibrated window)
        try:
            import yaml, os
            yaml_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config", "rooms", "pokerstars.yaml",
            )
            with open(yaml_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            roi = cfg.get("rois", {}).get(roi_name)
            if not roi:
                return None

            rx, ry, rw, rh = (
                roi.get("x", 0), roi.get("y", 0),
                roi.get("width", 50), roi.get("height", 30),
            )
            abs_x = win_x + rx + rw // 2
            abs_y = win_y + ry + rh // 2
            logger.debug(
                "_get_ps_action_coords: %s → yaml (%d,%d)",
                roi_name, abs_x, abs_y,
            )
            return (abs_x, abs_y)
        except Exception as exc:
            logger.debug("_get_ps_action_coords(%s) error: %s", roi_name, exc)
            return None

    # ── Phase 7: window liveness + emergency fold ────────────────────────────

    def _get_active_table_hwnd(self) -> Optional[int]:
        """Return the active TABLE window HWND (PS or CP table, not lobby)."""
        hwnd = getattr(self, "_ps_table_hwnd", None) or getattr(self, "_cp_table_hwnd", None)
        if not hwnd:
            hwnd = (
                self.account.window_info.hwnd
                if self.account and self.account.window_info
                else None
            )
        return hwnd

    def _is_window_alive(self) -> bool:
        """Return True if the bot's poker window still exists."""
        hwnd = self._get_active_table_hwnd()
        if not hwnd:
            return True  # No HWND configured — assume alive (dry-run)
        try:
            import ctypes
            return bool(ctypes.windll.user32.IsWindow(hwnd))
        except Exception:
            return True  # Can't check — assume alive

    async def _emergency_fold(self) -> None:
        """Execute fold action as timeout recovery (Phase 7)."""
        try:
            from bridge.action.real_executor import ActionCoordinates
            fold_xy = self._get_action_coords("fold")
            if fold_xy and self._action_executor:
                coords = ActionCoordinates(button_x=fold_xy[0], button_y=fold_xy[1])
                self._action_executor.execute_action(
                    action_type="fold",
                    coordinates=coords,
                )
                logger.info("Bot %s: emergency fold executed", self.bot_id[:8])
        except Exception as exc:
            logger.warning("emergency_fold failed: %s", exc)

    # ── Safety: session limits ────────────────────────────────────────────────

    def _check_session_limits(self) -> bool:
        """Return False if a session limit has been reached."""
        try:
            from bridge.safety import SafetyFramework
            fw = SafetyFramework.get_instance()
            if not fw.check_safety():
                self.error_message = "Safety limit reached"
                self.status = BotStatus.STOPPED
                return False
            if fw.config.max_hands_per_session and \
               self._hands_this_session >= fw.config.max_hands_per_session:
                logger.info(
                    "Bot %s: max hands/session reached (%d)",
                    self.bot_id[:8], self._hands_this_session,
                )
                self.status = BotStatus.STOPPED
                return False
        except Exception:
            pass
        return True
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'bot_id': self.bot_id,
            'account_id': self.account.account_id if self.account else None,
            'nickname': self.account.nickname if self.account else "N/A",
            'status': self.status.value,
            'current_table': self.current_table,
            'stack': self.stack,
            'collective_edge': self.collective_edge,
            'profile_name': self.profile_name,
            'binding': self.get_binding_dict(),
            'auto_roi': self.get_auto_roi_info(),
            'settings': self.settings.to_dict(),
            'stats': {
                'hands_played': self.stats.hands_played,
                'pot_won': self.stats.pot_won,
                'pot_lost': self.stats.pot_lost,
                'net_profit': self.stats.net_profit(),
                'vision_errors': self.stats.vision_errors,
                'decisions_made': self.stats.decisions_made,
                'actions_executed': self.stats.actions_executed,
                'uptime_seconds': self.stats.uptime_seconds
            },
            'error_message': self.error_message
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Bot Instance - Educational Research")
    print("=" * 60)
    print()
    
    # Create account and ROI
    from launcher.models.account import Account, WindowInfo, WindowType
    from launcher.models.roi_config import ROIConfig, ROIZone
    
    account = Account(nickname="TestBot001", room="pokerstars")
    account.window_info = WindowInfo(
        window_id="12345",
        window_title="PokerStars",
        window_type=WindowType.DESKTOP_CLIENT
    )
    account.roi_configured = True
    
    roi_config = ROIConfig(account_id=account.account_id)
    roi_config.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi_config.add_zone(ROIZone("pot", 500, 100, 100, 30))
    
    # Create bot instance
    bot = BotInstance(
        account=account,
        roi_config=roi_config
    )
    
    print(f"Bot instance created:")
    print(f"  ID: {bot.bot_id[:8]}...")
    print(f"  Account: {bot.account.nickname}")
    print(f"  Status: {bot.status.value}")
    print(f"  Can start: {bot.can_start()}")
    print()
    
    # Simulate stats
    bot.stats.hands_played = 50
    bot.stats.pot_won = 125.50
    bot.stats.pot_lost = 75.25
    bot.stats.decisions_made = 150
    
    print(f"Simulated statistics:")
    print(f"  Hands played: {bot.stats.hands_played}")
    print(f"  Net profit: ${bot.stats.net_profit():.2f}")
    print(f"  Decisions made: {bot.stats.decisions_made}")
    print()
    
    # Convert to dict
    data = bot.to_dict()
    print(f"Bot as dict: {len(data)} fields")
    print()
    
    print("=" * 60)
    print("Bot instance demonstration complete")
    print("=" * 60)
