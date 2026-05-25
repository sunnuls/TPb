"""
Session History Widget — shows past bot sessions stored in session_history.json.

Sub-tab ("History") inside BotsControlTab.

Columns:  Started | Nickname | Table | Profile | Hands | Profit | Duration | End
Buttons:  Refresh | Export CSV | Clear History
Summary bar: Total sessions · Total hands · Total profit · Best session
"""

from __future__ import annotations

import csv
import datetime
import logging
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QFileDialog, QGroupBox, QHBoxLayout, QHeaderView,
        QLabel, QMessageBox, QPushButton, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.ui.theme import COLORS

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_item(
    text: str,
    color: Optional[str] = None,
    align: int = int(Qt.AlignmentFlag.AlignLeft) if PYQT_AVAILABLE else 1,
) -> "QTableWidgetItem":
    it = QTableWidgetItem(str(text))
    it.setTextAlignment(align | int(Qt.AlignmentFlag.AlignVCenter))
    if color:
        it.setForeground(QColor(color))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


def _sep() -> "QLabel":
    lbl = QLabel("|")
    lbl.setStyleSheet("color: #3a3f55; padding: 0 2px;")
    return lbl


def _stat_label(text: str) -> "QLabel":
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {COLORS['text_secondary']}; font-size: 10pt; padding: 0 4px;"
    )
    return lbl


# ── Widget ────────────────────────────────────────────────────────────────────

if PYQT_AVAILABLE:
    class SessionHistoryWidget(QWidget):
        """
        Read-only view of finished bot sessions.

        Call ``set_session_logger(logger)`` to connect the data source.
        Auto-refreshes every 5 s.
        """

        _COLS = [
            "Started", "Nickname", "Table", "Profile",
            "Hands", "Profit", "Duration", "End",
        ]

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._session_logger = None
            self._setup_ui()

            self._refresh_timer = QTimer(self)
            self._refresh_timer.timeout.connect(self.refresh)
            self._refresh_timer.start(5000)

        # ── Public API ────────────────────────────────────────────────────────

        def set_session_logger(self, session_logger) -> None:
            self._session_logger = session_logger
            self.refresh()

        def refresh(self) -> None:
            self._update_summary()
            self._update_table()

        # ── UI ────────────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(6)

            # ── Summary bar ───────────────────────────────────────────────────
            summary_group = QGroupBox("Totals")
            sl = QHBoxLayout(summary_group)
            sl.setSpacing(8)

            self._lbl_sessions = _stat_label("Sessions: 0")
            self._lbl_hands    = _stat_label("Hands: 0")
            self._lbl_profit   = _stat_label("Profit: $0.00")
            self._lbl_best     = _stat_label("Best: —")

            for w in (
                self._lbl_sessions, _sep(),
                self._lbl_hands,    _sep(),
                self._lbl_profit,   _sep(),
                self._lbl_best,
            ):
                sl.addWidget(w)
            sl.addStretch()
            root.addWidget(summary_group)

            # ── Toolbar ───────────────────────────────────────────────────────
            toolbar = QHBoxLayout()
            toolbar.setSpacing(8)

            for btn_text, btn_slot, btn_style in (
                ("🔄 Refresh",       self.refresh,              ""),
                ("💾 Export CSV",    self._on_export_csv,       ""),
                ("🗑 Clear History", self._on_clear_history,
                 f"color: {COLORS['accent_red']};"),
            ):
                btn = QPushButton(btn_text)
                btn.setMaximumWidth(135)
                if btn_style:
                    btn.setStyleSheet(btn_style)
                btn.clicked.connect(btn_slot)
                toolbar.addWidget(btn)

            toolbar.addStretch()

            self._count_label = QLabel("0 sessions")
            self._count_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt;"
            )
            toolbar.addWidget(self._count_label)
            root.addLayout(toolbar)

            # ── Table ─────────────────────────────────────────────────────────
            self._table = QTableWidget(0, len(self._COLS))
            self._table.setHorizontalHeaderLabels(self._COLS)

            hdr = self._table.horizontalHeader()
            stretch_cols = {1, 2}      # Nickname, Table
            for i in range(len(self._COLS)):
                mode = (QHeaderView.ResizeMode.Stretch
                        if i in stretch_cols
                        else QHeaderView.ResizeMode.ResizeToContents)
                hdr.setSectionResizeMode(i, mode)

            self._table.verticalHeader().setVisible(False)
            self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self._table.setAlternatingRowColors(True)
            self._table.setStyleSheet(
                "QTableWidget { alternate-background-color: #1e2030; }"
                "QTableWidget::item { padding: 3px 6px; }"
            )
            root.addWidget(self._table, stretch=1)

        # ── Data ──────────────────────────────────────────────────────────────

        def _update_summary(self) -> None:
            if not self._session_logger:
                return
            try:
                s = self._session_logger.get_summary()
                self._lbl_sessions.setText(f"Sessions: {s['total_sessions']}")
                self._lbl_hands.setText(f"Hands: {s['total_hands']:,}")

                profit = s["total_profit"]
                sign   = "+" if profit >= 0 else ""
                p_color = (COLORS["accent_green"] if profit >= 0
                           else COLORS["accent_red"])
                self._lbl_profit.setText(f"Profit: {sign}{profit:.2f}")
                self._lbl_profit.setStyleSheet(
                    f"color: {p_color}; font-weight: bold; padding: 0 4px;"
                )

                best = s.get("best_session")
                if best:
                    self._lbl_best.setText(
                        f"Best: {best.nickname}  {best.profit_str}"
                    )
            except Exception as exc:
                logger.debug("SessionHistory summary error: %s", exc)

        def _update_table(self) -> None:
            if not self._session_logger:
                return
            try:
                history = self._session_logger.get_history(limit=200)
            except Exception:
                return

            self._table.setRowCount(len(history))
            self._count_label.setText(f"{len(history)} sessions")

            RIGHT = int(Qt.AlignmentFlag.AlignRight)

            for row, rec in enumerate(history):
                p_color = (COLORS["accent_green"] if rec.profit >= 0
                           else COLORS["accent_red"])
                e_color = (COLORS["accent_red"]   if rec.end_reason == "error"
                           else COLORS["accent_green"] if rec.end_reason in
                                ("stopped", "emergency")
                           else COLORS["text_secondary"])

                cells = [
                    _make_item(rec.started_str),
                    _make_item(rec.nickname,   COLORS["text_primary"]),
                    _make_item(rec.table or "—"),
                    _make_item(rec.profile or "—"),
                    _make_item(str(rec.hands),  align=RIGHT),
                    _make_item(rec.profit_str,  p_color, align=RIGHT),
                    _make_item(rec.duration_str, align=RIGHT),
                    _make_item(rec.end_reason or "—", e_color),
                ]
                for col, cell in enumerate(cells):
                    self._table.setItem(row, col, cell)

        # ── Button handlers ───────────────────────────────────────────────────

        def _on_export_csv(self) -> None:
            if not self._session_logger:
                QMessageBox.information(self, "No Data",
                                        "Session logger not connected.")
                return

            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Session History",
                f"session_history_{ts}.csv",
                "CSV Files (*.csv);;All Files (*)",
            )
            if not path:
                return

            try:
                history = self._session_logger.get_history(limit=1000)
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(self._COLS)
                    for r in history:
                        writer.writerow([
                            r.started_str, r.nickname, r.table or "",
                            r.profile or "", r.hands, r.profit_str,
                            r.duration_str, r.end_reason or "",
                        ])
                QMessageBox.information(
                    self, "Export Complete",
                    f"Saved {len(history)} records to:\n{path}",
                )
                logger.info("Session history exported → %s", path)
            except OSError as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

        def _on_clear_history(self) -> None:
            reply = QMessageBox.question(
                self, "Clear History",
                "Delete ALL session records?\nThis cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            if self._session_logger:
                self._session_logger._records.clear()
                self._session_logger._save()
            self.refresh()
            logger.info("Session history cleared by user")
