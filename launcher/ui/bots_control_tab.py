"""
Bots Control Tab — three sub-tabs:
  1. Active Bots  — live table (№ Nickname Status Table Stack Edge Uptime Profile Action)
  2. Lobby        — table scanner + HIVE deployment
  3. HIVE Sessions — active collusion sessions / deployments

Top strip: ToggleSwitch (LIVE/STOP) + HIVE launch + Emergency Stop.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import logging
from typing import List, Optional

try:
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve,
        pyqtSignal, pyqtProperty, QRectF,
    )
    from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont
    from PyQt6.QtWidgets import (
        QComboBox, QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QMessageBox, QPushButton,
        QTableWidget, QTableWidgetItem, QTabWidget,
        QVBoxLayout, QWidget, QSizePolicy,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.account import Account
from launcher.bot_instance import BotStatus
from launcher.ui.theme import COLORS
from launcher.ui.lobby_panel import LobbyPanel
from launcher.ui.hive_sessions_widget import HiveSessionsWidget
from launcher.ui.session_history_widget import SessionHistoryWidget

logger = logging.getLogger(__name__)

_STATUS_COLORS = {
    BotStatus.IDLE:      COLORS["text_secondary"],
    BotStatus.STARTING:  COLORS["accent_orange"],
    BotStatus.SEARCHING: COLORS["accent_blue"],
    BotStatus.SEATED:    COLORS["accent_purple"],
    BotStatus.PLAYING:   COLORS["accent_green"],
    BotStatus.ERROR:     COLORS["accent_red"],
    BotStatus.STOPPED:   "#505570",
}


def _item(text: str, color: Optional[str] = None) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if color:
        it.setForeground(QColor(color))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


if PYQT_AVAILABLE:
    class BotToggleSwitch(QWidget):
        """
        Combined Start/Stop toggle switch.

        Visual design:
          - OFF state: left half dark, right half red  [● STOP]
          - ON  state: left half green, right half dark [LIVE ●]
          - Smooth animation between states.

        Signals:
          toggled(bool): emitted with new state when user clicks.
        """

        toggled = pyqtSignal(bool)

        _TRACK_ON_COLOR   = QColor("#1a4a1a")
        _TRACK_OFF_COLOR  = QColor("#3a0a0a")
        _KNOB_ON_COLOR    = QColor("#3ddc84")   # green
        _KNOB_OFF_COLOR   = QColor("#ff5555")   # red
        _LABEL_ON         = "LIVE"
        _LABEL_OFF        = "STOP"
        _MIN_W, _MIN_H    = 120, 36

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._checked: bool = False
            self._knob_x_frac: float = 0.0   # 0.0 = left (OFF), 1.0 = right (ON)

            self._anim = QPropertyAnimation(self, b"knob_pos", self)
            self._anim.setDuration(180)
            self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

            self.setMinimumSize(self._MIN_W, self._MIN_H)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip("Click to toggle all bots ON / OFF")

        # -- property for animation ------------------------------------------

        def _get_knob_pos(self) -> float:
            return self._knob_x_frac

        def _set_knob_pos(self, v: float) -> None:
            self._knob_x_frac = max(0.0, min(1.0, v))
            self.update()

        knob_pos = pyqtProperty(float, _get_knob_pos, _set_knob_pos)

        # -- public API -------------------------------------------------------

        def is_on(self) -> bool:
            return self._checked

        def set_state(self, on: bool, animate: bool = True) -> None:
            """Set switch state programmatically without emitting toggled."""
            self._checked = on
            target = 1.0 if on else 0.0
            if animate:
                self._anim.stop()
                self._anim.setStartValue(self._knob_x_frac)
                self._anim.setEndValue(target)
                self._anim.start()
            else:
                self._knob_x_frac = target
                self.update()

        # -- events ----------------------------------------------------------

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._checked = not self._checked
                self.set_state(self._checked, animate=True)
                self.toggled.emit(self._checked)

        def paintEvent(self, event) -> None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            r    = h / 2
            pad  = 3

            # Track
            track_color = self._TRACK_ON_COLOR if self._checked else self._TRACK_OFF_COLOR
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(track_color))
            p.drawRoundedRect(0, 0, w, h, r, r)

            # Border
            border_color = self._KNOB_ON_COLOR if self._checked else self._KNOB_OFF_COLOR
            p.setPen(QPen(border_color, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, w - 2, h - 2, r - 1, r - 1)

            # Knob
            knob_diam   = h - pad * 2
            max_knob_x  = w - knob_diam - pad
            knob_x      = pad + self._knob_x_frac * max_knob_x

            knob_color = self._KNOB_ON_COLOR if self._checked else self._KNOB_OFF_COLOR
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(knob_color))
            p.drawEllipse(QRectF(knob_x, pad, knob_diam, knob_diam))

            # Label
            label = self._LABEL_ON if self._checked else self._LABEL_OFF
            label_color = self._KNOB_ON_COLOR if self._checked else self._KNOB_OFF_COLOR
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QPen(label_color))

            # Place label on the opposite side from the knob
            if self._checked:
                text_rect = QRectF(pad, 0, max_knob_x - pad, h)
            else:
                text_rect = QRectF(knob_x + knob_diam + pad, 0,
                                   w - knob_x - knob_diam - pad * 2, h)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

            p.end()


    class BotsControlTab(QWidget):
        """
        Bot control tab with 3 inner sub-tabs.

        Signals
        -------
        emergency_stop_requested  — relayed to MainWindow
        """

        emergency_stop_requested = pyqtSignal()

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            bot_manager=None,
            collusion_coordinator=None,
            auto_seating_manager=None,
        ) -> None:
            super().__init__(parent)

            self.accounts: List[Account]  = []
            self._bot_manager             = bot_manager
            self._collusion_coordinator   = collusion_coordinator
            self._auto_seating_manager    = auto_seating_manager

            self._setup_ui()

            self._refresh_timer = QTimer(self)
            self._refresh_timer.timeout.connect(self._refresh_bots_table)
            self._refresh_timer.start(1000)

        # ── Public API ────────────────────────────────────────────────────────

        def set_accounts(self, accounts: List[Account]) -> None:
            self.accounts = accounts
            self._update_combos()
            # Forward to lobby panel so it can use real CoinPoker HWND
            if hasattr(self, "lobby_panel"):
                self.lobby_panel.set_accounts(accounts)

        def set_bot_manager(self, m) -> None:
            self._bot_manager = m
            self.lobby_panel.set_bot_manager(m)
            self.hive_sessions.set_bot_manager(m)

        def set_collusion_coordinator(self, c) -> None:
            self._collusion_coordinator = c
            self.hive_sessions.set_collusion_coordinator(c)

        def set_auto_seating_manager(self, m) -> None:
            self._auto_seating_manager = m
            self.lobby_panel.set_auto_seating_manager(m)
            self.hive_sessions.set_auto_seating_manager(m)

        def set_session_logger(self, session_logger) -> None:
            self.session_history.set_session_logger(session_logger)

        def set_live_mode(self, live: bool) -> None:
            """Update mode banner to reflect DRY-RUN vs LIVE state."""
            if live:
                self._mode_banner.setText(
                    "🔴  LIVE MODE — bots send REAL mouse/keyboard input to CoinPoker. "
                    "Switch to DRY-RUN in Settings to stop real actions."
                )
                self._mode_banner.setStyleSheet(
                    "background:#3a0000; color:#ff6b6b; border:1px solid #800000;"
                    " border-radius:4px; padding:5px 10px; font-size:9pt; font-weight:bold;"
                )
            else:
                self._mode_banner.setText(
                    "🔵  DRY-RUN MODE — bots simulate actions only, NO real table interaction. "
                    "Status SEARCHING = bot is active and looking for a table."
                )
                self._mode_banner.setStyleSheet(
                    "background:#0d2240; color:#6ab4ff; border:1px solid #1a4080;"
                    " border-radius:4px; padding:5px 10px; font-size:9pt;"
                )

        def start_all_bots(self) -> None:
            self._on_start_single()
            self.all_toggle.set_state(True)

        def stop_all_bots(self) -> None:
            self._on_stop_selected()
            self.all_toggle.set_state(False)

        # ── UI setup ──────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(6)

            # ── Top strip: title + quick-start + emergency stop ────────────────
            root.addWidget(self._build_top_strip())

            # ── DRY-RUN / mode banner ─────────────────────────────────────────
            self._mode_banner = QLabel(
                "🔵  DRY-RUN MODE — bots simulate actions only, NO real table interaction. "
                "Status SEARCHING = bot is active and looking for a table."
            )
            self._mode_banner.setWordWrap(True)
            self._mode_banner.setStyleSheet(
                "background:#0d2240; color:#6ab4ff; border:1px solid #1a4080;"
                " border-radius:4px; padding:5px 10px; font-size:9pt;"
            )
            root.addWidget(self._mode_banner)

            # ── Inner tab widget ──────────────────────────────────────────────
            self.inner_tabs = QTabWidget()
            self.inner_tabs.setTabPosition(QTabWidget.TabPosition.North)

            # Tab 1: Active Bots
            self.inner_tabs.addTab(self._build_active_bots_panel(), "Active Bots")

            # Tab 2: Lobby Scanner
            self.lobby_panel = LobbyPanel(
                bot_manager=self._bot_manager,
                auto_seating_manager=self._auto_seating_manager,
            )
            self.inner_tabs.addTab(self.lobby_panel, "Lobby Scanner")

            # Tab 3: HIVE Sessions
            self.hive_sessions = HiveSessionsWidget(
                bot_manager=self._bot_manager,
                collusion_coordinator=self._collusion_coordinator,
                auto_seating_manager=self._auto_seating_manager,
            )
            self.inner_tabs.addTab(self.hive_sessions, "HIVE Sessions")

            # Tab 4: Session History
            self.session_history = SessionHistoryWidget()
            self.inner_tabs.addTab(self.session_history, "History")

            root.addWidget(self.inner_tabs, stretch=1)

        def _build_top_strip(self) -> QWidget:
            strip = QWidget()
            layout = QHBoxLayout(strip)
            layout.setContentsMargins(0, 0, 0, 4)
            layout.setSpacing(10)

            # Title
            title = QLabel("Bot Control")
            title.setProperty("class", "header")
            layout.addWidget(title)

            layout.addSpacing(20)

            # Account selector + toggle switch
            layout.addWidget(QLabel("bot(s) —"))

            self.single_bot_combo = QComboBox()
            self.single_bot_combo.setMinimumWidth(160)
            self.single_bot_combo.setPlaceholderText("Select account…")
            layout.addWidget(self.single_bot_combo)

            # Single combined Start/Stop toggle switch
            layout.addSpacing(8)
            self.all_toggle = BotToggleSwitch()
            self.all_toggle.setToolTip(
                "Toggle bot:\n  GREEN (LIVE) = bot running\n  RED (STOP) = bot stopped"
            )
            self.all_toggle.toggled.connect(self._on_toggle_all)
            layout.addWidget(self.all_toggle)
            layout.addSpacing(8)

            layout.addStretch()

            # HIVE quick-launch (3 bots)
            layout.addWidget(QLabel("HIVE:"))
            self.hive_combo1 = QComboBox()
            self.hive_combo1.setPlaceholderText("Bot 1…")
            self.hive_combo1.setMinimumWidth(110)
            layout.addWidget(self.hive_combo1)

            self.hive_combo2 = QComboBox()
            self.hive_combo2.setPlaceholderText("Bot 2…")
            self.hive_combo2.setMinimumWidth(110)
            layout.addWidget(self.hive_combo2)

            self.hive_combo3 = QComboBox()
            self.hive_combo3.setPlaceholderText("Bot 3…")
            self.hive_combo3.setMinimumWidth(110)
            layout.addWidget(self.hive_combo3)

            hive_btn = QPushButton("🤝  HIVE")
            hive_btn.setProperty("class", "hive")
            hive_btn.setMinimumWidth(80)
            hive_btn.clicked.connect(self._on_start_hive)
            layout.addWidget(hive_btn)

            layout.addSpacing(12)

            # Emergency Stop
            self.emergency_btn = QPushButton("🚨 EMERGENCY STOP")
            self.emergency_btn.setProperty("class", "danger")
            self.emergency_btn.setMinimumWidth(190)
            self.emergency_btn.setMinimumHeight(36)
            self.emergency_btn.clicked.connect(self._on_emergency_stop)
            self.emergency_btn.setToolTip("Ctrl+Shift+X")
            layout.addWidget(self.emergency_btn)

            return strip

        def _build_active_bots_panel(self) -> QWidget:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 6, 0, 0)
            layout.setSpacing(6)

            self.bots_table = QTableWidget()
            self.bots_table.setColumnCount(9)
            self.bots_table.setHorizontalHeaderLabels([
                "№", "Nickname", "Status", "Table",
                "Stack", "Edge", "Uptime", "Profile", "Action",
            ])

            hdr = self.bots_table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            for i in (4, 5, 6, 7, 8):
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            self.bots_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows
            )
            self.bots_table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers
            )
            self.bots_table.setAlternatingRowColors(True)
            self.bots_table.verticalHeader().setVisible(False)

            layout.addWidget(self.bots_table, stretch=1)

            # Counter
            self.counter_label = QLabel("No bots")
            self.counter_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 2px;"
            )
            layout.addWidget(self.counter_label)

            return panel

        # ── Refresh ────────────────────────────────────────────────────────────

        def _refresh_bots_table(self) -> None:
            if self._bot_manager is None:
                return

            bots = self._bot_manager.get_all_bots()
            self.bots_table.setRowCount(len(bots))

            for idx, bot in enumerate(bots):
                num = QTableWidgetItem(str(idx + 1))
                num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                num.setFlags(num.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.bots_table.setItem(idx, 0, num)

                nick = bot.account.nickname if bot.account else "?"
                self.bots_table.setItem(idx, 1, QTableWidgetItem(nick))

                sc = _STATUS_COLORS.get(bot.status, COLORS["text_secondary"])
                _status_labels = {
                    "searching": "🔍 SEARCHING",
                    "playing":   "🃏 PLAYING",
                    "seated":    "💺 SEATED",
                    "starting":  "⏳ STARTING",
                    "idle":      "⏸ IDLE",
                    "stopped":   "⏹ STOPPED",
                    "error":     "❌ ERROR",
                }
                status_text = _status_labels.get(
                    bot.status.value, bot.status.value.upper()
                )
                self.bots_table.setItem(idx, 2, _item(status_text, sc))

                self.bots_table.setItem(
                    idx, 3, QTableWidgetItem(bot.current_table or "—")
                )
                self.bots_table.setItem(
                    idx, 4,
                    _item(f"${bot.stack:.2f}" if bot.stack else "—",
                          COLORS["accent_green"]),
                )
                self.bots_table.setItem(
                    idx, 5,
                    _item(
                        f"{bot.collective_edge:.1f}%" if bot.collective_edge else "—",
                        COLORS["accent_purple"],
                    ),
                )

                uptime = int(bot.stats.uptime_seconds)
                m, s = divmod(uptime, 60)
                h, m = divmod(m, 60)
                ut = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                self.bots_table.setItem(idx, 6, QTableWidgetItem(ut))

                self.bots_table.setItem(
                    idx, 7, QTableWidgetItem(bot.profile_name or "default")
                )

                # Per-bot toggle switch
                row_toggle = BotToggleSwitch()
                row_toggle.set_state(bot.is_active(), animate=False)
                row_toggle.setEnabled(bot.can_start() or bot.is_active())
                row_toggle.setMinimumSize(80, 28)

                def _make_toggle_cb(bid: str, tog: "BotToggleSwitch"):
                    def _cb(on: bool) -> None:
                        if on:
                            self._start_bot(bid)
                        else:
                            self._stop_bot(bid)
                    return _cb

                row_toggle.toggled.connect(_make_toggle_cb(bot.bot_id, row_toggle))
                self.bots_table.setCellWidget(idx, 8, row_toggle)

            active = sum(1 for b in bots if b.is_active())
            self.counter_label.setText(
                f"Bots: {active} running / {len(bots)} total"
            )

        # ── Combo helpers ──────────────────────────────────────────────────────

        def _update_combos(self) -> None:
            # Show ALL accounts — not just captured ones (Start handles validation)
            for combo in (
                self.single_bot_combo,
                self.hive_combo1,
                self.hive_combo2,
                self.hive_combo3,
            ):
                prev = combo.currentData()
                combo.clear()
                for acc in self.accounts:
                    combo.addItem(acc.nickname, acc.account_id)
                # Restore previous selection, or auto-select first item
                restored = False
                if prev:
                    for i in range(combo.count()):
                        if combo.itemData(i) == prev:
                            combo.setCurrentIndex(i)
                            restored = True
                            break
                if not restored and combo.count() > 0:
                    combo.setCurrentIndex(0)

        # ── Slots ─────────────────────────────────────────────────────────────

        def _on_toggle_all(self, on: bool) -> None:
            """Toggle selected bot on or off via the combined switch."""
            if on:
                self._on_start_single()
            else:
                self._on_stop_selected()

        def _on_start_single(self) -> None:
            aid = self.single_bot_combo.currentData()
            if not aid:
                QMessageBox.warning(self, "No Account",
                    "Select an account from the dropdown first.")
                self.all_toggle.set_state(False)
                return
            if self._bot_manager:
                bot = self._bot_manager.get_bot_by_account(aid)
                if bot and bot.is_active():
                    return   # already running — toggle just reflects it
            self._start_bot_by_account(aid)

        def _on_stop_selected(self) -> None:
            """Stop the bot for the currently selected account."""
            if self._bot_manager is None:
                return
            aid = self.single_bot_combo.currentData()
            if aid:
                bot = self._bot_manager.get_bot_by_account(aid)
                if bot and bot.is_active():
                    self._bot_manager.stop_bot(bot.bot_id)
                    return
            # Fallback: stop all active bots
            active = self._bot_manager.get_active_bots()
            for bot in active:
                self._bot_manager.stop_bot(bot.bot_id)

        def _on_start_all(self) -> None:
            if self._bot_manager is None:
                return
            idle = self._bot_manager.get_idle_bots()
            if not idle:
                QMessageBox.information(self, "No Bots", "No idle bots to start.")
                return
            reply = QMessageBox.question(
                self, "Start All Bots",
                f"Start {len(idle)} idle bot(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._bot_manager.start_all()

        def _on_start_hive(self) -> None:
            ids = [
                self.hive_combo1.currentData(),
                self.hive_combo2.currentData(),
                self.hive_combo3.currentData(),
            ]
            if None in ids:
                QMessageBox.warning(
                    self, "Incomplete", "Select all 3 bots for the HIVE group."
                )
                return
            if len(set(ids)) != 3:
                QMessageBox.warning(
                    self, "Duplicate", "Select 3 *different* accounts."
                )
                return

            nicks = [
                next((a.nickname for a in self.accounts if a.account_id == i), i)
                for i in ids
            ]

            reply = QMessageBox.question(
                self,
                "Start HIVE Group",
                f"Start HIVE group?\n\n"
                f"  Bot 1: {nicks[0]}\n"
                f"  Bot 2: {nicks[1]}\n"
                f"  Bot 3: {nicks[2]}\n\n"
                "All 3 bots will coordinate on the same table (3vs1).\n"
                "Team coordination active.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            for aid in ids:
                self._start_bot_by_account(aid)

            # Switch to HIVE Sessions tab so user sees activity
            self.inner_tabs.setCurrentIndex(2)

        def _on_stop_all(self) -> None:
            if self._bot_manager is None:
                return
            active = self._bot_manager.get_active_bots()
            if not active:
                QMessageBox.information(
                    self, "No Active Bots", "No bots are running."
                )
                return
            reply = QMessageBox.question(
                self, "Stop All",
                f"Stop {len(active)} running bot(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._bot_manager.stop_all()

        def _on_emergency_stop(self) -> None:
            self.emergency_stop_requested.emit()

        def _start_bot(self, bot_id: str) -> None:
            if self._bot_manager:
                self._bot_manager.start_bot(bot_id)

        def _stop_bot(self, bot_id: str) -> None:
            if self._bot_manager:
                self._bot_manager.stop_bot(bot_id)

        def _start_bot_by_account(self, account_id: str) -> None:
            if self._bot_manager is None:
                return
            bot = self._bot_manager.get_bot_by_account(account_id)
            if bot:
                self._bot_manager.start_bot(bot.bot_id)
            else:
                account = next(
                    (a for a in self.accounts if a.account_id == account_id), None
                )
                if account:
                    from launcher.models.roi_config import ROIConfig
                    bot = self._bot_manager.create_bot(
                        account, ROIConfig(account_id=account_id)
                    )
                    self._bot_manager.start_bot(bot.bot_id)
