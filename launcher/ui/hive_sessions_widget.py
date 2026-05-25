"""
HIVE Sessions Widget — shows active collusion sessions in real-time.

Pulls data from CollusionCoordinator.get_active_sessions() and
AutoSeatingManager.get_active_deployments().

Updates every second via QTimer.
"""

import logging
import time
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QPushButton, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.ui.theme import COLORS

logger = logging.getLogger(__name__)


def _colored(text: str, color: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(QColor(color))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


if PYQT_AVAILABLE:
    class HiveSessionsWidget(QWidget):
        """
        Displays active HIVE deployments and collusion sessions.

        Refreshes every 1 s. Works with or without CollusionCoordinator
        (falls back to showing BotManager active-bot groups).
        """

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            bot_manager=None,
            collusion_coordinator=None,
            auto_seating_manager=None,
        ) -> None:
            super().__init__(parent)

            self._bot_manager             = bot_manager
            self._collusion_coordinator   = collusion_coordinator
            self._auto_seating_manager    = auto_seating_manager

            self._setup_ui()

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._refresh)
            self._timer.start(1000)

        # ── Public API ────────────────────────────────────────────────────────

        def set_bot_manager(self, m) -> None:
            self._bot_manager = m

        def set_collusion_coordinator(self, c) -> None:
            self._collusion_coordinator = c

        def set_auto_seating_manager(self, m) -> None:
            self._auto_seating_manager = m

        # ── UI ─────────────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(8)

            # ── Summary stats row ─────────────────────────────────────────────
            stats_group = QGroupBox("HIVE Overview")
            stats_row = QHBoxLayout(stats_group)

            def _stat_pair(label: str, init: str, color: str):
                lbl = QLabel(label)
                lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 9pt;")
                val = QLabel(init)
                val.setStyleSheet(
                    f"color: {color}; font-size: 13pt; font-weight: bold;"
                )
                stats_row.addWidget(lbl)
                stats_row.addWidget(val)
                stats_row.addSpacing(20)
                return val

            self._active_sessions_val = _stat_pair(
                "Active sessions:", "0", COLORS["accent_purple"]
            )
            self._active_tables_val = _stat_pair(
                "Tables occupied:", "0", COLORS["accent_blue"]
            )
            self._total_hands_val = _stat_pair(
                "Hands played:", "0", COLORS["text_primary"]
            )
            self._total_profit_val = _stat_pair(
                "Total profit:", "$0.00", COLORS["accent_green"]
            )
            self._card_shares_val = _stat_pair(
                "Card shares:", "0", COLORS["accent_orange"]
            )
            stats_row.addStretch()
            root.addWidget(stats_group)

            # ── Active sessions table ─────────────────────────────────────────
            sessions_group = QGroupBox("Active Collusion Sessions")
            sessions_layout = QVBoxLayout(sessions_group)

            self.sessions_table = QTableWidget()
            self.sessions_table.setColumnCount(8)
            self.sessions_table.setHorizontalHeaderLabels([
                "Table", "Bot 1", "Bot 2", "Bot 3",
                "Hands", "Profit", "Card Shares", "Uptime",
            ])
            hdr = self.sessions_table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for i in range(1, 8):
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            self.sessions_table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers
            )
            self.sessions_table.setAlternatingRowColors(True)
            self.sessions_table.verticalHeader().setVisible(False)
            sessions_layout.addWidget(self.sessions_table)

            root.addWidget(sessions_group, stretch=1)

            # ── Active deployments table ──────────────────────────────────────
            deploy_group = QGroupBox("Active Deployments")
            deploy_layout = QVBoxLayout(deploy_group)

            self.deploy_table = QTableWidget()
            self.deploy_table.setColumnCount(5)
            self.deploy_table.setHorizontalHeaderLabels([
                "Table", "Status", "Bots", "Started", "Elapsed",
            ])
            dhdr = self.deploy_table.horizontalHeader()
            dhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for i in range(1, 5):
                dhdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            self.deploy_table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers
            )
            self.deploy_table.setAlternatingRowColors(True)
            self.deploy_table.verticalHeader().setVisible(False)
            deploy_layout.addWidget(self.deploy_table)

            root.addWidget(deploy_group)

        # ── Refresh ────────────────────────────────────────────────────────────

        def _refresh(self) -> None:
            self._refresh_sessions()
            self._refresh_deployments()
            self._refresh_stats()

        def _refresh_sessions(self) -> None:
            if self._collusion_coordinator is None:
                self._refresh_sessions_from_bots()
                return

            try:
                sessions = self._collusion_coordinator.get_active_sessions()
            except Exception:
                sessions = []

            self.sessions_table.setRowCount(len(sessions))

            for row, s in enumerate(sessions):
                # Table name
                table_name = getattr(
                    getattr(s, "deployment", None), "table", None
                )
                table_name = (
                    getattr(table_name, "table_name", "?")
                    if table_name else "?"
                )
                self.sessions_table.setItem(row, 0, QTableWidgetItem(table_name))

                # Bot nicknames (from bot_manager if available)
                bot_ids = getattr(s, "bot_ids", [])
                for col_offset, bid in enumerate(bot_ids[:3]):
                    nick = "?"
                    if self._bot_manager:
                        bot = self._bot_manager.get_bot(bid)
                        if bot and bot.account:
                            nick = bot.account.nickname
                    self.sessions_table.setItem(
                        row, 1 + col_offset,
                        _colored(nick, COLORS["accent_purple"]),
                    )

                # Hands
                hands = getattr(s, "hands_played", 0)
                self.sessions_table.setItem(row, 4, QTableWidgetItem(str(hands)))

                # Profit
                profit = getattr(s, "total_profit", 0.0)
                profit_color = (
                    COLORS["accent_green"] if profit >= 0 else COLORS["accent_red"]
                )
                self.sessions_table.setItem(
                    row, 5, _colored(f"${profit:.2f}", profit_color)
                )

                # Card shares
                shares = getattr(s, "card_shares_count", 0)
                self.sessions_table.setItem(
                    row, 6,
                    _colored(str(shares), COLORS["accent_orange"]),
                )

                # Uptime
                started = getattr(s, "started_at", None)
                if started:
                    elapsed = int(time.time() - started)
                    m, sec = divmod(elapsed, 60)
                    h, m = divmod(m, 60)
                    uptime = f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
                else:
                    uptime = "—"
                self.sessions_table.setItem(row, 7, QTableWidgetItem(uptime))

        def _refresh_sessions_from_bots(self) -> None:
            """Fallback: group active bots by current_table."""
            if self._bot_manager is None:
                self.sessions_table.setRowCount(0)
                return

            active = self._bot_manager.get_active_bots()
            # Group by table
            groups: dict = {}
            for bot in active:
                t = bot.current_table or "(unknown)"
                groups.setdefault(t, []).append(bot)

            rows = [(t, bots) for t, bots in groups.items() if len(bots) >= 1]
            self.sessions_table.setRowCount(len(rows))

            for row, (table_name, bots) in enumerate(rows):
                self.sessions_table.setItem(
                    row, 0, QTableWidgetItem(table_name)
                )
                for col_offset, bot in enumerate(bots[:3]):
                    nick = bot.account.nickname if bot.account else "?"
                    self.sessions_table.setItem(
                        row, 1 + col_offset,
                        _colored(nick, COLORS["accent_purple"]),
                    )
                # Hands / profit from first bot
                if bots:
                    hands = bots[0].stats.hands_played
                    profit = bots[0].stats.net_profit()
                    self.sessions_table.setItem(
                        row, 4, QTableWidgetItem(str(hands))
                    )
                    profit_color = (
                        COLORS["accent_green"] if profit >= 0
                        else COLORS["accent_red"]
                    )
                    self.sessions_table.setItem(
                        row, 5, _colored(f"${profit:.2f}", profit_color)
                    )

        def _refresh_deployments(self) -> None:
            if self._auto_seating_manager is None:
                self.deploy_table.setRowCount(0)
                return

            try:
                deployments = self._auto_seating_manager.get_active_deployments()
            except Exception:
                deployments = []

            self.deploy_table.setRowCount(len(deployments))

            for row, d in enumerate(deployments):
                table_name = getattr(
                    getattr(d, "table", None), "table_name", "?"
                )
                self.deploy_table.setItem(row, 0, QTableWidgetItem(table_name))

                status = getattr(d, "status", None)
                status_str = status.value if status else "?"
                status_color = (
                    COLORS["accent_green"]
                    if status_str == "completed"
                    else COLORS["accent_orange"]
                )
                self.deploy_table.setItem(
                    row, 1, _colored(status_str.upper(), status_color)
                )

                n_bots = len(getattr(d, "bot_ids", []))
                self.deploy_table.setItem(
                    row, 2,
                    _colored(str(n_bots), COLORS["accent_blue"]),
                )

                started = getattr(d, "started_at", None)
                if started:
                    self.deploy_table.setItem(
                        row, 3,
                        QTableWidgetItem(time.strftime("%H:%M:%S", time.localtime(started))),
                    )
                    elapsed = int(time.time() - started)
                    m, s = divmod(elapsed, 60)
                    self.deploy_table.setItem(
                        row, 4, QTableWidgetItem(f"{m}:{s:02d}")
                    )

        def _refresh_stats(self) -> None:
            # Sessions count
            if self._collusion_coordinator:
                try:
                    stats = self._collusion_coordinator.get_statistics()
                    self._active_sessions_val.setText(
                        str(stats.get("active_sessions", 0))
                    )
                    self._total_hands_val.setText(
                        str(stats.get("total_hands", 0))
                    )
                    profit = stats.get("total_profit", 0.0)
                    profit_color = (
                        COLORS["accent_green"] if profit >= 0 else COLORS["accent_red"]
                    )
                    self._total_profit_val.setText(f"${profit:.2f}")
                    self._total_profit_val.setStyleSheet(
                        f"color: {profit_color}; font-size: 13pt; font-weight: bold;"
                    )
                    self._card_shares_val.setText(
                        str(stats.get("total_card_shares", 0))
                    )
                except Exception:
                    pass
            elif self._bot_manager:
                active = self._bot_manager.get_active_bots()
                tables = len(set(b.current_table for b in active if b.current_table))
                self._active_sessions_val.setText(str(len(active)))
                self._active_tables_val.setText(str(tables))

                bm_stats = self._bot_manager.get_statistics()
                self._total_hands_val.setText(
                    str(bm_stats.get("hands_played", 0))
                )
                profit = bm_stats.get("total_profit", 0.0)
                self._total_profit_val.setText(f"${profit:.2f}")

            # Deployments
            if self._auto_seating_manager:
                try:
                    ds = self._auto_seating_manager.get_statistics()
                    self._active_tables_val.setText(
                        str(ds.get("active_deployments", 0))
                    )
                except Exception:
                    pass
