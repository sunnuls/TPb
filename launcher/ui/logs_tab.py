"""
Logs Tab - Launcher Application (Roadmap6 Phase 6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Real-time log display
- Color-coded messages
- Level filtering
- Auto-scroll
- Clear logs
"""

import logging
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QPushButton, QCheckBox, QLabel,
        QGroupBox
    )
    from PyQt6.QtCore import Qt, pyqtSlot
    from PyQt6.QtGui import QTextCursor, QColor
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.log_handler import LogEntry, LogLevel, get_log_handler

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class LogsTab(QWidget):
        """
        Logs display tab.
        
        Features:
        - Real-time log output
        - Color-coded by level
        - Level filtering (checkboxes)
        - Auto-scroll
        - Clear button
        
        ⚠️ EDUCATIONAL NOTE:
            Monitors all bot activity in real-time.
        """
        
        def __init__(self, parent=None):
            """
            Initialize logs tab.
            
            Args:
                parent: Parent widget
            """
            super().__init__(parent)
            
            self.log_handler = get_log_handler()
            self.auto_scroll = True
            self.max_lines = 10000
            
            # Level filters
            self.level_filters = {
                LogLevel.DEBUG: True,
                LogLevel.INFO: True,
                LogLevel.ACTION: True,
                LogLevel.WARNING: True,
                LogLevel.ERROR: True,
                LogLevel.CRITICAL: True
            }
            
            self._setup_ui()
            self._connect_signals()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Controls
            controls_group = QGroupBox("Log Controls")
            controls_layout = QHBoxLayout()
            
            # Level filters
            controls_layout.addWidget(QLabel("Show:"))
            
            self.debug_check = QCheckBox("Debug")
            self.debug_check.setChecked(True)
            self.debug_check.stateChanged.connect(self._on_filter_changed)
            controls_layout.addWidget(self.debug_check)
            
            self.info_check = QCheckBox("Info")
            self.info_check.setChecked(True)
            self.info_check.stateChanged.connect(self._on_filter_changed)
            controls_layout.addWidget(self.info_check)
            
            self.action_check = QCheckBox("Actions")
            self.action_check.setChecked(True)
            self.action_check.setStyleSheet("color: #66FF66; font-weight: bold;")
            self.action_check.stateChanged.connect(self._on_filter_changed)
            controls_layout.addWidget(self.action_check)
            
            self.warning_check = QCheckBox("Warnings")
            self.warning_check.setChecked(True)
            self.warning_check.setStyleSheet("color: #FFFF66;")
            self.warning_check.stateChanged.connect(self._on_filter_changed)
            controls_layout.addWidget(self.warning_check)
            
            self.error_check = QCheckBox("Errors")
            self.error_check.setChecked(True)
            self.error_check.setStyleSheet("color: #FF6666; font-weight: bold;")
            self.error_check.stateChanged.connect(self._on_filter_changed)
            controls_layout.addWidget(self.error_check)
            
            controls_layout.addStretch()
            
            # Auto-scroll
            self.auto_scroll_check = QCheckBox("Auto-scroll")
            self.auto_scroll_check.setChecked(True)
            self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)
            controls_layout.addWidget(self.auto_scroll_check)
            
            # Clear button
            clear_btn = QPushButton("Clear Logs")
            clear_btn.clicked.connect(self._on_clear_logs)
            controls_layout.addWidget(clear_btn)
            
            controls_group.setLayout(controls_layout)
            layout.addWidget(controls_group)
            
            # Log display
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            self.log_display.setStyleSheet(
                "QTextEdit {"
                "    background-color: #1E1E1E;"
                "    color: #CCCCCC;"
                "    font-family: 'Consolas', 'Courier New', monospace;"
                "    font-size: 10pt;"
                "}"
            )
            layout.addWidget(self.log_display)
            
            # Statistics
            self.stats_label = QLabel("Logs: 0 | Actions: 0 | Warnings: 0 | Errors: 0")
            self.stats_label.setStyleSheet("padding: 5px;")
            layout.addWidget(self.stats_label)
        
        def _connect_signals(self):
            """Connect signals."""
            if self.log_handler and hasattr(self.log_handler, 'log_received'):
                self.log_handler.log_received.connect(self._on_log_received)
        
        @pyqtSlot(LogEntry)
        def _on_log_received(self, entry: LogEntry):
            """
            Handle new log entry.
            
            Args:
                entry: Log entry
            """
            # Check filter
            if not self.level_filters.get(entry.level, True):
                return
            
            # Format
            formatted = entry.format(include_timestamp=True, include_logger=False)
            
            # Append with color
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            
            # Set color
            format = cursor.charFormat()
            format.setForeground(QColor(entry.color))
            cursor.setCharFormat(format)
            
            # Insert text
            cursor.insertText(formatted + "\n")
            
            # Limit lines
            if self.log_display.document().blockCount() > self.max_lines:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 100)
                cursor.removeSelectedText()
            
            # Auto-scroll
            if self.auto_scroll:
                self.log_display.setTextCursor(cursor)
                self.log_display.ensureCursorVisible()
            
            # Update statistics
            self._update_statistics()
        
        def _on_filter_changed(self):
            """Handle filter change."""
            self.level_filters[LogLevel.DEBUG] = self.debug_check.isChecked()
            self.level_filters[LogLevel.INFO] = self.info_check.isChecked()
            self.level_filters[LogLevel.ACTION] = self.action_check.isChecked()
            self.level_filters[LogLevel.WARNING] = self.warning_check.isChecked()
            self.level_filters[LogLevel.ERROR] = self.error_check.isChecked()
            self.level_filters[LogLevel.CRITICAL] = self.error_check.isChecked()
            
            # Reload logs with new filters
            self._reload_logs()
        
        def _on_auto_scroll_changed(self, state):
            """Handle auto-scroll change."""
            self.auto_scroll = (state == Qt.CheckState.Checked.value)
        
        def _on_clear_logs(self):
            """Clear logs."""
            self.log_display.clear()
            
            if self.log_handler and hasattr(self.log_handler, 'clear'):
                self.log_handler.clear()
            
            self._update_statistics()
            
            logger.info("Logs cleared by user")
        
        def _reload_logs(self):
            """Reload logs with current filters."""
            if not self.log_handler or not hasattr(self.log_handler, 'get_recent_logs'):
                return
            
            # Clear display
            self.log_display.clear()
            
            # Get recent logs
            entries = self.log_handler.get_recent_logs(count=1000)
            
            # Add filtered entries
            for entry in entries:
                if self.level_filters.get(entry.level, True):
                    self._on_log_received(entry)
        
        def _update_statistics(self):
            """Update statistics label."""
            if not self.log_handler or not hasattr(self.log_handler, 'get_statistics'):
                return
            
            stats = self.log_handler.get_statistics()
            
            total = stats.get('total', 0)
            by_level = stats.get('by_level', {})
            
            actions = by_level.get('ACTION', 0)
            warnings = by_level.get('WARNING', 0)
            errors = by_level.get('ERROR', 0) + by_level.get('CRITICAL', 0)
            
            self.stats_label.setText(
                f"Logs: {total} | Actions: {actions} | "
                f"Warnings: {warnings} | Errors: {errors}"
            )
        
        def load_initial_logs(self):
            """Load initial logs from handler."""
            if not self.log_handler or not hasattr(self.log_handler, 'get_recent_logs'):
                return
            
            entries = self.log_handler.get_recent_logs(count=1000)
            
            for entry in entries:
                self._on_log_received(entry)


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Logs Tab - Educational Research")
    print("=" * 60)
    print()
    
    print("LogsTab Window (PyQt6):")
    print()
    print("  Controls:")
    print("    - Level filters: Debug, Info, Actions, Warnings, Errors")
    print("    - Auto-scroll checkbox")
    print("    - Clear logs button")
    print()
    print("  Log Display:")
    print("    - QTextEdit with dark theme")
    print("    - Monospace font (Consolas)")
    print("    - Color-coded messages:")
    print("      * Debug:    Gray (#888888)")
    print("      * Info:     Light gray (#CCCCCC)")
    print("      * Actions:  Green (#66FF66)")
    print("      * Warnings: Yellow (#FFFF66)")
    print("      * Errors:   Red (#FF6666)")
    print("    - Auto-scroll to latest")
    print("    - Max 10,000 lines (auto-trim)")
    print()
    print("  Statistics Bar:")
    print("    - Total logs count")
    print("    - Actions count")
    print("    - Warnings count")
    print("    - Errors count")
    print()
    print("  Real-time Updates:")
    print("    - Receives logs via QtLogHandler")
    print("    - Thread-safe signal/slot")
    print("    - Filters applied before display")
    print()
    print("=" * 60)
    print("Logs tab demonstration complete")
    print("=" * 60)
