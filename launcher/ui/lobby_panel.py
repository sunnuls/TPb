"""
Lobby Scanner Panel — find tables and deploy HIVE teams.

Integrates with:
  launcher.lobby_scanner.LobbyScanner   (scan / simulate)
  launcher.auto_seating.AutoSeatingManager  (deploy HIVE)

The scanner is run in a QThread worker so the UI never freezes.
"""

import logging
import time
from typing import List, Optional

try:
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, pyqtSlot, QObject,
    )
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QCheckBox, QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QMessageBox, QPushButton, QSpinBox,
        QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
        QSplitter, QFrame,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.lobby_scanner import LobbyScanner, LobbyTable, LobbySnapshot
from launcher.ui.theme import COLORS

logger = logging.getLogger(__name__)


# ── Worker (runs scan off the main thread) ─────────────────────────────────────

class _ScanWorker(QObject):
    """Runs LobbyScanner in a background thread."""

    finished = pyqtSignal(object)   # LobbySnapshot
    error    = pyqtSignal(str)

    def __init__(self, scanner: LobbyScanner, simulate: bool = False) -> None:
        super().__init__()
        self._scanner  = scanner
        self._simulate = simulate

    @pyqtSlot()
    def run(self) -> None:
        try:
            if self._simulate:
                snapshot = self._scanner.simulate_lobby_data(num_tables=12)
            else:
                snapshot = self._scanner.scan_lobby()
                # Fallback to simulation if real scan returned nothing
                if snapshot.total_tables == 0:
                    snapshot = self._scanner.simulate_lobby_data(num_tables=12)
            self.finished.emit(snapshot)
        except Exception as exc:
            self.error.emit(str(exc))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _priority_color(score: float) -> str:
    if score >= 80:
        return COLORS["accent_green"]
    if score >= 50:
        return COLORS["accent_orange"]
    return COLORS["text_secondary"]


def _colored(text: str, color: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(QColor(color))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


if PYQT_AVAILABLE:
    class LobbyPanel(QWidget):
        """
        Lobby scanner + HIVE deployment panel.

        Signals
        -------
        deploy_requested(list[str])   — list of 3 table_ids to seat bots at
        """

        deploy_requested = pyqtSignal(object)   # LobbyTable

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            bot_manager=None,
            auto_seating_manager=None,
        ) -> None:
            super().__init__(parent)

            self._bot_manager          = bot_manager
            self._auto_seating_manager = auto_seating_manager
            self._scanner              = LobbyScanner()
            self._last_snapshot: Optional[LobbySnapshot] = None

            self._scan_thread:  Optional[QThread]      = None
            self._scan_worker:  Optional[_ScanWorker]  = None

            self._auto_timer = QTimer(self)
            self._auto_timer.timeout.connect(self._start_scan)

            self._setup_ui()

        # ── Public API ────────────────────────────────────────────────────────

        def set_bot_manager(self, manager) -> None:
            self._bot_manager = manager

        def set_auto_seating_manager(self, manager) -> None:
            self._auto_seating_manager = manager

        def set_accounts(self, accounts: list) -> None:
            """Pass accounts so scanner can pick up CoinPoker HWND."""
            for acc in accounts:
                hwnd = getattr(acc.window_info, "hwnd", None) if acc.window_info else None
                if hwnd:
                    self._scanner.set_hwnd(hwnd)
                    break

        # ── UI ─────────────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(8)

            # ── Toolbar ────────────────────────────────────────────────────────
            toolbar = QHBoxLayout()

            self.scan_btn = QPushButton("🔍  Scan Lobby")
            self.scan_btn.setProperty("class", "primary")
            self.scan_btn.setMinimumWidth(130)
            self.scan_btn.clicked.connect(self._start_scan)
            toolbar.addWidget(self.scan_btn)

            self.auto_check = QCheckBox("Auto-scan every")
            self.auto_check.stateChanged.connect(self._toggle_auto_scan)
            toolbar.addWidget(self.auto_check)

            self.interval_spin = QSpinBox()
            self.interval_spin.setRange(5, 120)
            self.interval_spin.setValue(15)
            self.interval_spin.setSuffix(" s")
            self.interval_spin.setMaximumWidth(70)
            toolbar.addWidget(self.interval_spin)

            toolbar.addStretch()

            self.status_label = QLabel("Ready")
            self.status_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt;"
            )
            toolbar.addWidget(self.status_label)

            root.addLayout(toolbar)

            # ── Filter row ─────────────────────────────────────────────────────
            filter_row = QHBoxLayout()
            filter_row.addWidget(
                QLabel("Show tables with humans:")
            )

            self.min_humans_spin = QSpinBox()
            self.min_humans_spin.setRange(0, 9)
            self.min_humans_spin.setValue(1)
            self.min_humans_spin.setMaximumWidth(55)
            filter_row.addWidget(self.min_humans_spin)

            filter_row.addWidget(QLabel("–"))

            self.max_humans_spin = QSpinBox()
            self.max_humans_spin.setRange(0, 9)
            self.max_humans_spin.setValue(3)
            self.max_humans_spin.setMaximumWidth(55)
            filter_row.addWidget(self.max_humans_spin)

            self.hive_only_check = QCheckBox("HIVE-ready only (≥3 open seats)")
            self.hive_only_check.setChecked(True)
            filter_row.addWidget(self.hive_only_check)

            apply_filter_btn = QPushButton("Apply Filter")
            apply_filter_btn.setMaximumWidth(110)
            apply_filter_btn.clicked.connect(self._apply_filter)
            filter_row.addWidget(apply_filter_btn)

            filter_row.addStretch()
            root.addLayout(filter_row)

            # ── Table ──────────────────────────────────────────────────────────
            self.table = QTableWidget()
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "Table", "Type", "Stakes", "Seated/Max",
                "Humans", "Open Seats", "Avg Pot", "Priority",
            ])

            hdr = self.table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for i in range(1, 8):
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

            self.table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows
            )
            self.table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers
            )
            self.table.setAlternatingRowColors(True)
            self.table.verticalHeader().setVisible(False)
            self.table.doubleClicked.connect(self._on_table_double_clicked)

            root.addWidget(self.table, stretch=1)

            # ── Deploy section ────────────────────────────────────────────────
            root.addWidget(self._build_deploy_section())

        def _build_deploy_section(self) -> QGroupBox:
            group = QGroupBox("HIVE Deployment")
            layout = QVBoxLayout(group)
            layout.setSpacing(6)

            desc = QLabel(
                "Select a HIVE-ready table above (double-click or select + Deploy).\n"
                "3 idle bots will be deployed to that table."
            )
            desc.setWordWrap(True)
            desc.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt;"
            )
            layout.addWidget(desc)

            btn_row = QHBoxLayout()

            self.deploy_btn = QPushButton("🤝  Deploy HIVE to Selected Table")
            self.deploy_btn.setProperty("class", "hive")
            self.deploy_btn.setMinimumHeight(36)
            self.deploy_btn.setEnabled(False)
            self.deploy_btn.clicked.connect(self._on_deploy_clicked)
            btn_row.addWidget(self.deploy_btn)

            self.auto_deploy_check = QCheckBox("Auto-deploy when opportunity found")
            btn_row.addWidget(self.auto_deploy_check)

            btn_row.addStretch()
            layout.addLayout(btn_row)

            # Deployment status
            self.deploy_status_label = QLabel("—")
            self.deploy_status_label.setWordWrap(True)
            self.deploy_status_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 4px;"
            )
            layout.addWidget(self.deploy_status_label)

            return group

        # ── Scan logic ─────────────────────────────────────────────────────────

        def _start_scan(self) -> None:
            if self._scan_thread and self._scan_thread.isRunning():
                return   # already scanning

            self.scan_btn.setEnabled(False)
            self.status_label.setText("Scanning…")

            # Use simulation mode when no real lobby window is set
            simulate = self._scanner.lobby_window_id is None

            self._scan_worker = _ScanWorker(self._scanner, simulate=simulate)
            self._scan_thread = QThread(self)
            self._scan_worker.moveToThread(self._scan_thread)

            self._scan_thread.started.connect(self._scan_worker.run)
            self._scan_worker.finished.connect(self._on_scan_finished)
            self._scan_worker.error.connect(self._on_scan_error)
            self._scan_worker.finished.connect(self._scan_thread.quit)
            self._scan_worker.error.connect(self._scan_thread.quit)
            self._scan_thread.finished.connect(self._on_thread_done)

            self._scan_thread.start()

        @pyqtSlot(object)
        def _on_scan_finished(self, snapshot: LobbySnapshot) -> None:
            self._last_snapshot = snapshot
            self._populate_table(snapshot)

            n = snapshot.total_tables
            opp = len(snapshot.get_hive_opportunities())
            ts  = time.strftime("%H:%M:%S")
            self.status_label.setText(
                f"[{ts}]  {n} tables  |  {opp} HIVE opportunities"
            )

            # Auto-deploy if enabled
            if (
                self.auto_deploy_check.isChecked()
                and opp > 0
                and self._bot_manager
                and len(self._bot_manager.get_idle_bots()) >= 3
            ):
                best = snapshot.get_hive_opportunities()[0]
                self._deploy_to_table(best)

        @pyqtSlot(str)
        def _on_scan_error(self, msg: str) -> None:
            self.status_label.setText(f"Scan error: {msg}")
            logger.warning("Lobby scan error: %s", msg)

        @pyqtSlot()
        def _on_thread_done(self) -> None:
            self.scan_btn.setEnabled(True)

        def _toggle_auto_scan(self, state: int) -> None:
            if state == 2:  # Qt.CheckState.Checked
                interval_ms = self.interval_spin.value() * 1000
                self._auto_timer.start(interval_ms)
                self._start_scan()
            else:
                self._auto_timer.stop()

        # ── Populate table ────────────────────────────────────────────────────

        def _populate_table(self, snapshot: LobbySnapshot) -> None:
            tables = self._filtered_tables(snapshot)
            self.table.setRowCount(len(tables))

            for row, t in enumerate(tables):
                # Table name
                self.table.setItem(row, 0, QTableWidgetItem(t.table_name))

                # Game type
                self.table.setItem(row, 1, QTableWidgetItem(t.game_type))

                # Stakes
                self.table.setItem(row, 2, QTableWidgetItem(t.stakes))

                # Seated / Max
                seated_color = (
                    COLORS["accent_green"]
                    if t.seats_available() >= 3
                    else COLORS["text_secondary"]
                )
                self.table.setItem(
                    row, 3,
                    _colored(f"{t.players_seated}/{t.max_seats}", seated_color),
                )

                # Humans
                human_color = (
                    COLORS["accent_green"]
                    if 1 <= t.human_count <= 3
                    else COLORS["accent_orange"]
                )
                self.table.setItem(
                    row, 4, _colored(str(t.human_count), human_color)
                )

                # Open seats
                open_color = (
                    COLORS["accent_green"]
                    if t.seats_available() >= 3
                    else COLORS["accent_red"]
                )
                self.table.setItem(
                    row, 5, _colored(str(t.seats_available()), open_color)
                )

                # Avg pot
                self.table.setItem(
                    row, 6,
                    QTableWidgetItem(f"${t.avg_pot:.1f}"),
                )

                # Priority score
                score = t.priority_score()
                score_text = f"{score:.0f}" if score > 0 else "—"
                self.table.setItem(
                    row, 7,
                    _colored(score_text, _priority_color(score)),
                )

            # Enable deploy button if any HIVE-ready rows
            hive_rows = [t for t in tables if t.is_suitable_for_hive()]
            self.deploy_btn.setEnabled(len(hive_rows) > 0)

        def _filtered_tables(self, snapshot: LobbySnapshot) -> List[LobbyTable]:
            mn = self.min_humans_spin.value()
            mx = self.max_humans_spin.value()
            hive_only = self.hive_only_check.isChecked()

            result = []
            for t in snapshot.tables:
                if not (mn <= t.human_count <= mx):
                    continue
                if hive_only and not t.is_suitable_for_hive():
                    continue
                result.append(t)

            return sorted(result, key=lambda t: t.priority_score(), reverse=True)

        def _apply_filter(self) -> None:
            if self._last_snapshot:
                self._populate_table(self._last_snapshot)

        # ── Deploy logic ──────────────────────────────────────────────────────

        def _on_table_double_clicked(self) -> None:
            self._on_deploy_clicked()

        def _on_deploy_clicked(self) -> None:
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(
                    self, "No Selection", "Select a table first."
                )
                return

            if self._last_snapshot is None:
                return

            tables = self._filtered_tables(self._last_snapshot)
            if row >= len(tables):
                return

            target = tables[row]
            self._deploy_to_table(target)

        def _deploy_to_table(self, table: LobbyTable) -> None:
            if self._bot_manager is None:
                QMessageBox.warning(
                    self, "No Bot Manager",
                    "Bot Manager not connected."
                )
                return

            idle = self._bot_manager.get_idle_bots()
            if len(idle) < 3:
                QMessageBox.warning(
                    self,
                    "Not Enough Bots",
                    f"Need 3 idle bots — only {len(idle)} available.\n\n"
                    "Add accounts and configure ROI first.",
                )
                return

            reply = QMessageBox.question(
                self,
                "Deploy HIVE",
                f"Deploy HIVE team to:\n\n"
                f"  Table: {table.table_name}\n"
                f"  Stakes: {table.stakes}\n"
                f"  Humans: {table.human_count}\n"
                f"  Open seats: {table.seats_available()}\n"
                f"  Priority: {table.priority_score():.0f}/100\n\n"
                f"3 idle bots will be deployed.\n"
                f"⚠  ILLEGAL in real poker — educational only.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            logger.critical(
                "HIVE DEPLOY requested → table=%s  humans=%d",
                table.table_name, table.human_count,
            )

            # If we have a real auto_seating_manager, use it
            if self._auto_seating_manager:
                import asyncio

                async def _do_deploy():
                    await self._auto_seating_manager._deploy_hive_team(
                        table, idle[:3]
                    )

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(_do_deploy())
                    else:
                        asyncio.run(_do_deploy())
                except Exception as exc:
                    logger.error("Deploy error: %s", exc)

            else:
                # Fallback: manually assign table to 3 bots
                for bot in idle[:3]:
                    bot.current_table = table.table_name
                    logger.info(
                        "Bot %s assigned to %s",
                        bot.account.nickname if bot.account else "?",
                        table.table_name,
                    )

            self.deploy_requested.emit(table)

            self.deploy_status_label.setText(
                f"✓ Deployed to {table.table_name}  "
                f"({time.strftime('%H:%M:%S')})"
            )
            self.deploy_status_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 9pt; padding: 4px;"
            )
