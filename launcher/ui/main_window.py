"""
Main Window — HIVE Launcher Application.

Tab layout:
  1. Accounts     — account list, window capture, ROI setup
  2. Live View    — real-time bot vision preview
  3. Bot Control  — start/stop bots, active-bot table
  4. Settings     — global strategy / timing / HIVE settings
  5. Logs         — colour-coded log viewer

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import asyncio
import logging
import sys

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QStatusBar,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False
    print("WARNING: PyQt6 not available — install with: pip install PyQt6")

from launcher.config_manager import ConfigManager
from launcher.models.roi_config import ROIConfig
from launcher.bot_manager import BotManager
from launcher.bot_settings import BotSettings, BotSettingsManager
from launcher.log_handler import setup_launcher_logging

# Optional HIVE backend modules — graceful fallback if missing
try:
    from launcher.lobby_scanner import LobbyScanner
    from launcher.auto_seating import AutoSeatingManager
    _HAS_AUTO_SEATING = True
except Exception:
    _HAS_AUTO_SEATING = False

try:
    from launcher.collusion_coordinator import CollusionCoordinator
    _HAS_COLLUSION = True
except Exception:
    _HAS_COLLUSION = False

if PYQT6_AVAILABLE:
    from launcher.ui.accounts_tab import AccountsTab
    from launcher.ui.bots_control_tab import BotsControlTab
    from launcher.ui.live_view_tab import LiveViewTab
    from launcher.ui.settings_tab import SettingsTab
    from launcher.ui.logs_tab import LogsTab

logger = logging.getLogger(__name__)


if PYQT6_AVAILABLE:
    class MainWindow(QMainWindow):
        """
        Main launcher window.

        Features
        --------
        - Tabbed interface (5 tabs)
        - Dark theme (applied by theme.py at app level)
        - Status bar with live bot/account counts
        - Emergency Stop always accessible from menu
        - System tray integration (optional)

        ⚠️ EDUCATIONAL NOTE:
            Interface for coordinated bot management research.
        """

        def __init__(self) -> None:
            super().__init__()

            self.setWindowTitle("HIVE Launcher  —  Educational Research")
            self.setGeometry(80, 80, 1400, 860)
            self.setMinimumSize(1100, 700)

            # Set by main.py after tray is created
            self._tray_manager = None

            # For change-detection in _update_status (tray notifications)
            self._prev_active_bots = 0
            self._prev_error_bots  = 0
            self._prev_hands       = 0

            # Session logger
            try:
                from launcher.session_log import SessionLogger
                self._session_logger = SessionLogger()
            except Exception as exc:
                logger.debug("SessionLogger not available: %s", exc)
                self._session_logger = None

            # Logging
            self.log_handler = setup_launcher_logging(use_qt=True)

            # Managers
            self.config_manager   = ConfigManager()
            self.settings_manager = BotSettingsManager()
            self.bot_manager      = BotManager()

            # Optional HIVE backend
            self.lobby_scanner        = LobbyScanner()          if _HAS_AUTO_SEATING else None
            # Stage 1: allow 1 bot; Stage 2 HIVE still supports up to 3
            self.auto_seating_manager = AutoSeatingManager(
                bot_manager=self.bot_manager,
                lobby_scanner=self.lobby_scanner,
                min_team_size=1,
                max_team_size=3,
                join_stagger_seconds=8.0,
            ) if _HAS_AUTO_SEATING else None
            self.collusion_coordinator = (
                CollusionCoordinator(enable_real_actions=False)
                if _HAS_COLLUSION else None
            )
            # Wire collusion coordinator into bot manager for HIVE card sharing
            if self.collusion_coordinator is not None:
                self.bot_manager.set_collusion_coordinator(self.collusion_coordinator)

            # Data
            self.accounts        = self.config_manager.load_accounts()
            self.global_settings = self.settings_manager.load_global_settings()

            logger.info("Loaded %d accounts", len(self.accounts))
            logger.info("Global preset: %s", self.global_settings.preset.value)
            logger.info(
                "HIVE backend: auto_seating=%s  collusion=%s",
                _HAS_AUTO_SEATING, _HAS_COLLUSION,
            )

            # Build UI
            self._setup_ui()
            self._setup_menubar()
            self._setup_statusbar()

            # Wire up status timer
            self._status_timer = QTimer(self)
            self._status_timer.timeout.connect(self._update_status)
            self._status_timer.start(1000)

            # Global emergency-stop hotkey: Ctrl+Shift+E
            try:
                from PyQt6.QtGui import QKeySequence, QShortcut
                self._emergency_shortcut = QShortcut(
                    QKeySequence("Ctrl+Shift+E"), self
                )
                self._emergency_shortcut.activated.connect(self._on_emergency_stop)
                logger.info("Emergency-stop hotkey registered: Ctrl+Shift+E")
            except Exception as exc:
                logger.debug("Could not register emergency hotkey: %s", exc)

            # Warning banner in UI is sufficient — no blocking dialog

        # ── UI Construction ───────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)

            layout = QVBoxLayout(central)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # ── Status banner ─────────────────────────────────────────────
            banner = QLabel("HIVE — Multi-Bot Poker Network")
            banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            banner.setStyleSheet(
                "background-color: #1e2433; color: #c8d0e0; "
                "font-size: 11pt; font-weight: bold; "
                "padding: 6px; letter-spacing: 0.5px;"
            )
            layout.addWidget(banner)

            # ── Tab widget ─────────────────────────────────────────────────
            self.tabs = QTabWidget()
            self.tabs.setTabPosition(QTabWidget.TabPosition.North)
            self.tabs.setDocumentMode(True)
            layout.addWidget(self.tabs)

            self._create_tabs()

        def _create_tabs(self) -> None:
            # ── 1. Accounts ────────────────────────────────────────────────
            self.accounts_tab = AccountsTab()
            self.accounts_tab.account_added.connect(self._on_account_added)
            self.accounts_tab.account_removed.connect(self._on_account_removed)
            self.accounts_tab.roi_configured.connect(self._on_roi_configured)
            self.accounts_tab.accounts = self.accounts
            self.accounts_tab._update_table()
            self.tabs.addTab(self.accounts_tab, "  Accounts  ")

            # ── 2. Live View ───────────────────────────────────────────────
            self.live_view_tab = LiveViewTab()
            self.live_view_tab.set_accounts(self.accounts)
            self.live_view_tab.set_bot_manager(self.bot_manager)
            self.tabs.addTab(self.live_view_tab, "  Live View  ")

            # ── 3. Bot Control ─────────────────────────────────────────────
            self.bots_control_tab = BotsControlTab(
                bot_manager=self.bot_manager,
                collusion_coordinator=self.collusion_coordinator,
                auto_seating_manager=self.auto_seating_manager,
            )
            self.bots_control_tab.set_accounts(self.accounts)
            self.bots_control_tab.emergency_stop_requested.connect(
                self._on_emergency_stop
            )
            self.tabs.addTab(self.bots_control_tab, "  Bot Control  ")

            # ── 4. Settings ────────────────────────────────────────────────
            self.settings_tab = SettingsTab(settings=self.global_settings)
            self.settings_tab.settings_changed.connect(self._on_settings_changed)
            self.settings_tab.live_mode_changed.connect(self._on_live_mode_changed)
            self.tabs.addTab(self.settings_tab, "  Settings  ")

            # ── 5. Logs ────────────────────────────────────────────────────
            self.logs_tab = LogsTab()
            self.logs_tab.load_initial_logs()
            self.tabs.addTab(self.logs_tab, "  Logs  ")

            # Wire session logger to BotsControlTab
            if self._session_logger is not None:
                self.bots_control_tab.set_session_logger(self._session_logger)

            # Give lobby scanner the HWND of already-loaded accounts
            self._sync_lobby_hwnd()

            # Style tab icons (text only, no icons needed)
            self._style_tabs()

        def _style_tabs(self) -> None:
            from PyQt6.QtGui import QColor
            # Live View tab — blue accent
            self.tabs.tabBar().setTabTextColor(1, QColor("#4a9eff"))
            # Bot Control — slight orange when HIVE active (set dynamically elsewhere)
            self.tabs.tabBar().setTabTextColor(2, QColor("#e8eaf0"))

        # ── Menu bar ──────────────────────────────────────────────────────────

        def _setup_menubar(self) -> None:
            bar = self.menuBar()

            # File
            file_menu = bar.addMenu("&File")

            export_action = QAction("&Export Logs…", self)
            export_action.triggered.connect(self._export_logs)
            file_menu.addAction(export_action)

            file_menu.addSeparator()

            exit_action = QAction("E&xit", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

            # Bots
            bots_menu = bar.addMenu("&Bots")

            start_all_action = QAction("Start All Bots", self)
            start_all_action.setShortcut("Ctrl+R")
            start_all_action.triggered.connect(self._start_all_bots)
            bots_menu.addAction(start_all_action)

            stop_all_action = QAction("Stop All Bots", self)
            stop_all_action.setShortcut("Ctrl+T")
            stop_all_action.triggered.connect(self._stop_all_bots)
            bots_menu.addAction(stop_all_action)

            bots_menu.addSeparator()

            emergency_action = QAction("🚨 EMERGENCY STOP", self)
            emergency_action.setShortcut("Ctrl+Shift+X")
            emergency_action.triggered.connect(self._on_emergency_stop)
            bots_menu.addAction(emergency_action)

            # Help
            help_menu = bar.addMenu("&Help")

            about_action = QAction("&About", self)
            about_action.triggered.connect(self._show_about)
            help_menu.addAction(about_action)

        # ── Status bar ─────────────────────────────────────────────────────────

        def _setup_statusbar(self) -> None:
            self.statusbar = QStatusBar()
            self.setStatusBar(self.statusbar)
            self.statusbar.setStyleSheet(
                "QStatusBar { font-size: 9pt; }"
                "QStatusBar::item { border: none; }"
            )

            self.status_accounts = QLabel("Accounts: 0 / 0")
            self.status_bots     = QLabel("Bots: 0 / 0")
            self.status_hands    = QLabel("Hands: 0")
            self.status_tables   = QLabel("Tables: 0")
            self.status_hive     = QLabel("HIVE: 0")
            self.status_hive.setStyleSheet("color: #9b59b6; font-weight: bold; padding: 0 4px;")

            self.status_mode = QLabel("● Dry-run")
            self.status_mode.setStyleSheet(
                "color: #3ddc84; font-weight: bold; padding: 0 8px;"
            )

            for widget in (
                self.status_accounts, _status_separator(),
                self.status_bots,     _status_separator(),
                self.status_hands,    _status_separator(),
                self.status_tables,   _status_separator(),
                self.status_hive,
            ):
                self.statusbar.addWidget(widget)

            self.statusbar.addPermanentWidget(self.status_mode)

        def _update_status(self) -> None:
            # Keep lobby scanner HWND in sync (window may be captured after startup)
            self._sync_lobby_hwnd()

            total = len(self.accounts)
            ready = sum(1 for a in self.accounts if a.is_ready_to_run())
            self.status_accounts.setText(f"Accounts: {ready}/{total}")

            stats  = self.bot_manager.get_statistics()
            active = stats.get("active_bots", 0)
            all_b  = stats.get("total_bots", 0)
            hands  = stats.get("hands_played", 0)
            tables = stats.get("active_tables", 0)
            self.status_bots.setText(f"Bots: {active}/{all_b}")
            self.status_hands.setText(f"Hands: {hands:,}")
            self.status_tables.setText(f"Tables: {tables}")

            # HIVE sessions
            hive_count = 0
            if self.collusion_coordinator and hasattr(
                self.collusion_coordinator, "get_active_sessions"
            ):
                try:
                    hive_count = len(self.collusion_coordinator.get_active_sessions())
                except Exception:
                    pass
            self.status_hive.setText(f"HIVE: {hive_count}")
            self.status_hive.setStyleSheet(
                ("color: #9b59b6; font-weight: bold; padding: 0 4px;"
                 if hive_count == 0 else
                 "color: #e040fb; font-weight: bold; padding: 0 4px;"
                 "  background: #2d1040; border-radius: 3px;")
            )

            # Mode badge
            live = getattr(self.global_settings, "enable_collusion", False)
            if live and active > 0:
                mode_text  = "● LIVE"
                mode_color = "#ff4c4c"
            elif active > 0:
                mode_text  = "● Running"
                mode_color = "#3ddc84"
            else:
                mode_text  = "● Dry-run"
                mode_color = "#5a7a5a"
            self.status_mode.setText(mode_text)
            self.status_mode.setStyleSheet(
                f"color: {mode_color}; font-weight: bold; padding: 0 8px;"
            )

            # Tab accent: Bot Control tab gets orange badge when bots are active
            from PyQt6.QtGui import QColor
            if active > 0:
                self.tabs.tabBar().setTabTextColor(2, QColor("#f0a500"))
            else:
                self.tabs.tabBar().setTabTextColor(2, QColor("#e8eaf0"))

            # ── Tray tooltip ─────────────────────────────────────────────────
            cur_hands  = stats.get("hands_played", 0)
            cur_errors = stats.get("bots_by_status", {}).get("error", 0)

            if self._tray_manager is not None:
                try:
                    self._tray_manager.update_status(
                        active_bots=active,
                        total_bots=all_b,
                        hands=cur_hands,
                        hive_sessions=hive_count,
                    )
                except Exception:
                    pass

            # ── Tray / status-bar notifications on state changes ──────────────
            self._fire_status_notifications(
                active, cur_errors, cur_hands,
            )
            self._prev_active_bots = active
            self._prev_error_bots  = cur_errors
            self._prev_hands       = cur_hands

        def _fire_status_notifications(
            self,
            active: int,
            errors: int,
            hands: int,
        ) -> None:
            """Emit tray balloon + statusbar message on interesting state changes."""
            prev_active = self._prev_active_bots
            prev_errors = self._prev_error_bots

            def _notify(title: str, msg: str, duration: int = 3500) -> None:
                self.statusbar.showMessage(msg, duration)
                if self._tray_manager:
                    try:
                        self._tray_manager.show_notification(title, msg, duration)
                    except Exception:
                        pass

            # Bots started (count went up)
            if active > prev_active:
                delta = active - prev_active
                _notify(
                    "Bot Started",
                    f"{delta} bot{'s' if delta > 1 else ''} now running "
                    f"(active: {active})",
                )
                # Record sessions for newly active bots
                if self._session_logger:
                    try:
                        for bot in self.bot_manager.get_active_bots():
                            self._session_logger.ensure_started(bot)
                    except Exception:
                        pass

            # Bots stopped (count went down, no error increase)
            elif active < prev_active and errors <= prev_errors:
                delta = prev_active - active
                _notify(
                    "Bots Stopped",
                    f"{delta} bot{'s' if delta > 1 else ''} stopped "
                    f"(active: {active})",
                )

            # Errors increased
            if errors > prev_errors:
                new_errors = errors - prev_errors
                _notify(
                    "Bot Error",
                    f"{new_errors} bot error{'s' if new_errors > 1 else ''} detected!",
                    duration=6000,
                )

        # ── Signal handlers ───────────────────────────────────────────────────

        def _on_account_added(self, account) -> None:
            self.accounts.append(account)
            self.config_manager.save_accounts(self.accounts)
            # Propagate to Live View / Bot Control
            self.live_view_tab.set_accounts(self.accounts)
            self.bots_control_tab.set_accounts(self.accounts)
            self._sync_lobby_hwnd()
            logger.info("Account added: %s", account.nickname)

        def _on_account_removed(self, account_id: str) -> None:
            self.accounts = [a for a in self.accounts if a.account_id != account_id]
            self.config_manager.save_accounts(self.accounts)
            self.config_manager.delete_roi_config(account_id)
            self.live_view_tab.set_accounts(self.accounts)
            self.bots_control_tab.set_accounts(self.accounts)
            logger.info("Account removed: %s", account_id)

        def _on_roi_configured(self, account_id: str, zones: list) -> None:
            account = next((a for a in self.accounts if a.account_id == account_id), None)
            if not account:
                return

            roi_config = ROIConfig(account_id=account_id)
            for zone in zones:
                roi_config.add_zone(zone)

            self.config_manager.save_roi_config(account_id, roi_config)
            self.config_manager.save_accounts(self.accounts)
            logger.info("ROI configured for %s: %d zones", account.nickname, len(zones))

            # Pass HWND to lobby scanner for real table data
            self._sync_lobby_hwnd()

            if account.is_ready_to_run():
                existing = self.bot_manager.get_bot_by_account(account_id)
                if not existing:
                    self.bot_manager.create_bot(account, roi_config)
                    logger.info("Bot created for %s", account.nickname)

        def _sync_lobby_hwnd(self) -> None:
            """Give lobby scanner the HWND of the first account with a captured window."""
            if not self.lobby_scanner:
                return
            for acc in self.accounts:
                if acc.window_info and acc.window_info.hwnd:
                    self.lobby_scanner.set_hwnd(acc.window_info.hwnd)
                    return

        def _on_live_mode_changed(self, live: bool) -> None:
            """Propagate LIVE/DRY-RUN toggle to bot_manager and status banner."""
            mode_name = "LIVE" if live else "DRY-RUN"
            logger.info("Execution mode switched to %s", mode_name)

            # Update collusion coordinator real-action flag
            if self.collusion_coordinator and hasattr(
                self.collusion_coordinator, "set_real_actions"
            ):
                try:
                    self.collusion_coordinator.set_real_actions(live)
                except Exception:
                    pass

            # Propagate to all managed bots
            if hasattr(self.bot_manager, "set_live_mode"):
                try:
                    self.bot_manager.set_live_mode(live)
                except Exception:
                    pass

            # Update Bot Control mode banner
            if hasattr(self.bots_control_tab, "set_live_mode"):
                self.bots_control_tab.set_live_mode(live)

            # Update status bar mode indicator immediately
            if live:
                self.status_mode.setText("🔴 LIVE")
                self.status_mode.setStyleSheet(
                    "color: #ff4c4c; font-weight: bold; padding: 0 8px;"
                    "background: #3a0000; border-radius: 3px;"
                )
                self.statusbar.showMessage(
                    "⚠️  LIVE MODE ACTIVATED — real mouse/keyboard input enabled", 5000
                )
            else:
                self.status_mode.setText("🔵 DRY-RUN")
                self.status_mode.setStyleSheet(
                    "color: #6ab4ff; font-weight: bold; padding: 0 8px;"
                )
                self.statusbar.showMessage("DRY-RUN mode restored — bots simulate only", 3000)

        def _on_settings_changed(self, settings: BotSettings) -> None:
            self.global_settings = settings
            self.settings_manager.save_global_settings(settings)

            # Propagate to all running bots
            updated = self.bot_manager.update_all_bot_settings(settings)

            logger.info(
                "Global settings saved: %s  aggression=%d  equity=%.0f%%  "
                "→ pushed to %d bot(s)",
                settings.preset.value,
                settings.aggression_level,
                settings.equity_threshold * 100,
                updated,
            )

        def _on_emergency_stop(self) -> None:
            reply = QMessageBox.critical(
                self,
                "EMERGENCY STOP",
                "Immediately stop ALL bots?\n\n"
                "• All bot instances will be halted.\n"
                "• Active collusion sessions will be closed.\n"
                "• Unsaved game state will be lost.\n\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            logger.critical("EMERGENCY STOP activated by user")

            # Force SafetyFramework back to DRY-RUN on emergency
            try:
                from bridge.safety import SafetyFramework, SafetyMode
                SafetyFramework.get_instance().config.mode = SafetyMode.DRY_RUN
            except Exception:
                pass

            # Reset Settings tab to DRY-RUN
            if hasattr(self, "settings_tab"):
                try:
                    self.settings_tab.dry_run_radio.setChecked(True)
                    self.settings_tab._apply_mode_to_safety(False)
                except Exception:
                    pass

            # Close all session records
            if self._session_logger:
                try:
                    self._session_logger.close_all(reason="emergency")
                except Exception:
                    pass

            async def _stop():
                # Stop auto-seating loop first
                if self.auto_seating_manager:
                    try:
                        await self.auto_seating_manager.stop()
                    except Exception as exc:
                        logger.error("Auto-seating stop error: %s", exc)
                self.bot_manager.stop_all()

            try:
                asyncio.run(_stop())
            except Exception as exc:
                logger.error("Emergency stop error: %s", exc)

            QMessageBox.information(
                self, "Emergency Stop", "All bots have been stopped."
            )

        # ── Menu actions ──────────────────────────────────────────────────────

        def _start_all_bots(self) -> None:
            self.tabs.setCurrentIndex(2)   # switch to Bot Control
            self.bots_control_tab.start_all_bots()

        def _stop_all_bots(self) -> None:
            self.tabs.setCurrentIndex(2)
            self.bots_control_tab.stop_all_bots()

        def _export_logs(self) -> None:
            self.tabs.setCurrentIndex(4)
            if hasattr(self.logs_tab, "export_logs"):
                self.logs_tab.export_logs()

        # ── Startup dialog ────────────────────────────────────────────────────

        def _show_startup_warning(self) -> None:
            """Optional welcome dialog — no longer blocks launch."""
            return

        def _show_about(self) -> None:
            QMessageBox.about(
                self,
                "About HIVE Launcher",
                "HIVE Launcher  v2.0\n\n"
                "Multi-bot poker coordination & vision platform.\n\n"
                "Tabs: Accounts · Live View · Bot Control · Settings · Logs",
            )

        # ── Close ─────────────────────────────────────────────────────────────

        def closeEvent(self, event) -> None:
            self.config_manager.save_accounts(self.accounts)
            logger.info("Launcher closed — configuration saved")
            event.accept()


def _status_separator() -> QLabel:
    sep = QLabel("|")
    sep.setStyleSheet("color: #3d4255; padding: 0 4px;")
    return sep


def main() -> int:
    if not PYQT6_AVAILABLE:
        print("ERROR: PyQt6 not available — install with: pip install PyQt6")
        return 1

    from launcher.ui.theme import apply_dark_theme

    app = QApplication(sys.argv)
    apply_dark_theme(app)
    app.setApplicationName("HIVE Launcher")
    app.setApplicationVersion("2.0")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
