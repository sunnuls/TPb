"""
Dashboard Tab - Launcher Application (Roadmap6 Phase 6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Real-time statistics
- Active tables monitoring
- Profit/loss tracking
- Vision error monitoring
- Collective edge display
- Emergency stop
"""

import logging
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QGroupBox, QProgressBar
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class DashboardTab(QWidget):
        """
        Dashboard monitoring tab.
        
        Features:
        - Real-time bot statistics
        - Active tables count
        - Profit/loss tracking
        - Vision error monitoring
        - Collective edge display
        - Emergency stop button
        
        ⚠️ EDUCATIONAL NOTE:
            Monitors coordinated bot activity for research analysis.
        
        Signals:
            emergency_stop_requested: Emitted when emergency stop pressed
        """
        
        emergency_stop_requested = pyqtSignal()
        
        def __init__(self, bot_manager=None, parent=None):
            """
            Initialize dashboard tab.
            
            Args:
                bot_manager: Bot manager instance
                parent: Parent widget
            """
            super().__init__(parent)
            
            self.bot_manager = bot_manager
            
            self._setup_ui()
            
            # Update timer
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self._update_statistics)
            self.update_timer.start(1000)  # Update every second
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Emergency Stop Banner
            emergency_group = QGroupBox("Emergency Controls")
            emergency_layout = QVBoxLayout()
            
            warning_label = QLabel(
                "⚠️ WARNING: Emergency Stop will immediately halt ALL bots\n"
                "Use only if critical issue detected"
            )
            warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            warning_label.setStyleSheet(
                "background-color: #FF9933; color: black; "
                "font-weight: bold; padding: 8px; border-radius: 3px;"
            )
            emergency_layout.addWidget(warning_label)
            
            self.emergency_btn = QPushButton("🚨 EMERGENCY STOP 🚨")
            self.emergency_btn.setStyleSheet(
                "QPushButton {"
                "    background-color: #CC0000;"
                "    color: white;"
                "    font-size: 18pt;"
                "    font-weight: bold;"
                "    padding: 15px;"
                "    border-radius: 5px;"
                "}"
                "QPushButton:hover {"
                "    background-color: #FF0000;"
                "}"
                "QPushButton:pressed {"
                "    background-color: #990000;"
                "}"
            )
            self.emergency_btn.clicked.connect(self._on_emergency_stop)
            emergency_layout.addWidget(self.emergency_btn)
            
            emergency_group.setLayout(emergency_layout)
            layout.addWidget(emergency_group)
            
            # Statistics Grid
            stats_group = QGroupBox("System Statistics")
            stats_layout = QGridLayout()
            
            # Row 0: Bot counts
            stats_layout.addWidget(self._create_label("Total Bots:", bold=True), 0, 0)
            self.total_bots_label = self._create_value_label("0")
            stats_layout.addWidget(self.total_bots_label, 0, 1)
            
            stats_layout.addWidget(self._create_label("Active Bots:", bold=True), 0, 2)
            self.active_bots_label = self._create_value_label("0", color="#66FF66")
            stats_layout.addWidget(self.active_bots_label, 0, 3)
            
            # Row 1: Table stats
            stats_layout.addWidget(self._create_label("Active Tables:", bold=True), 1, 0)
            self.active_tables_label = self._create_value_label("0")
            stats_layout.addWidget(self.active_tables_label, 1, 1)
            
            stats_layout.addWidget(self._create_label("HIVE Teams:", bold=True), 1, 2)
            self.hive_teams_label = self._create_value_label("0", color="#FFAA00")
            stats_layout.addWidget(self.hive_teams_label, 1, 3)
            
            # Row 2: Profit/Loss
            stats_layout.addWidget(self._create_label("Total Profit:", bold=True), 2, 0)
            self.total_profit_label = self._create_value_label("$0.00", color="#66FF66")
            stats_layout.addWidget(self.total_profit_label, 2, 1)
            
            stats_layout.addWidget(self._create_label("Hands Played:", bold=True), 2, 2)
            self.hands_played_label = self._create_value_label("0")
            stats_layout.addWidget(self.hands_played_label, 2, 3)
            
            # Row 3: Vision errors
            stats_layout.addWidget(self._create_label("Vision Errors:", bold=True), 3, 0)
            self.vision_errors_label = self._create_value_label("0", color="#FFFF66")
            stats_layout.addWidget(self.vision_errors_label, 3, 1)
            
            stats_layout.addWidget(self._create_label("Actions Executed:", bold=True), 3, 2)
            self.actions_executed_label = self._create_value_label("0")
            stats_layout.addWidget(self.actions_executed_label, 3, 3)
            
            # Row 4: Collective edge
            stats_layout.addWidget(self._create_label("Avg Collective Edge:", bold=True), 4, 0)
            self.collective_edge_label = self._create_value_label("0.0%", color="#66CCFF")
            stats_layout.addWidget(self.collective_edge_label, 4, 1)
            
            stats_layout.addWidget(self._create_label("Session Uptime:", bold=True), 4, 2)
            self.uptime_label = self._create_value_label("0:00:00")
            stats_layout.addWidget(self.uptime_label, 4, 3)
            
            stats_group.setLayout(stats_layout)
            layout.addWidget(stats_group)
            
            # Performance Indicators
            performance_group = QGroupBox("Performance Indicators")
            performance_layout = QVBoxLayout()
            
            # Vision health
            vision_layout = QHBoxLayout()
            vision_layout.addWidget(QLabel("Vision Health:"))
            self.vision_progress = QProgressBar()
            self.vision_progress.setRange(0, 100)
            self.vision_progress.setValue(100)
            self.vision_progress.setStyleSheet(
                "QProgressBar {"
                "    border: 1px solid #666;"
                "    border-radius: 3px;"
                "    text-align: center;"
                "}"
                "QProgressBar::chunk {"
                "    background-color: #66FF66;"
                "}"
            )
            vision_layout.addWidget(self.vision_progress)
            performance_layout.addLayout(vision_layout)
            
            # Decision speed
            decision_layout = QHBoxLayout()
            decision_layout.addWidget(QLabel("Decision Speed:"))
            self.decision_label = QLabel("N/A")
            decision_layout.addWidget(self.decision_label)
            decision_layout.addStretch()
            performance_layout.addLayout(decision_layout)
            
            performance_group.setLayout(performance_layout)
            layout.addWidget(performance_group)
            
            # Alerts
            alerts_group = QGroupBox("Active Alerts")
            alerts_layout = QVBoxLayout()
            
            self.alerts_label = QLabel("No active alerts")
            self.alerts_label.setStyleSheet("color: #66FF66; padding: 10px;")
            self.alerts_label.setWordWrap(True)
            alerts_layout.addWidget(self.alerts_label)
            
            alerts_group.setLayout(alerts_layout)
            layout.addWidget(alerts_group)
            
            layout.addStretch()
        
        def _create_label(self, text: str, bold: bool = False) -> QLabel:
            """
            Create formatted label.
            
            Args:
                text: Label text
                bold: Bold font
            
            Returns:
                QLabel
            """
            label = QLabel(text)
            if bold:
                font = label.font()
                font.setBold(True)
                label.setFont(font)
            return label
        
        def _create_value_label(self, text: str, color: str = "#FFFFFF") -> QLabel:
            """
            Create value display label.
            
            Args:
                text: Value text
                color: Text color
            
            Returns:
                QLabel
            """
            label = QLabel(text)
            label.setStyleSheet(f"color: {color}; font-size: 12pt;")
            return label
        
        def _update_statistics(self):
            """Update all statistics."""
            if not self.bot_manager:
                return
            
            try:
                # Get statistics
                stats = self.bot_manager.get_statistics()
                
                # Bot counts
                total_bots = stats.get('total_bots', 0)
                active_bots = stats.get('active_bots', 0)
                
                self.total_bots_label.setText(str(total_bots))
                self.active_bots_label.setText(str(active_bots))
                
                # Table stats
                active_tables = stats.get('active_tables', 0)
                hive_teams = stats.get('hive_teams', 0)
                
                self.active_tables_label.setText(str(active_tables))
                self.hive_teams_label.setText(str(hive_teams))
                
                # Profit/Loss
                total_profit = stats.get('total_profit', 0.0)
                profit_color = "#66FF66" if total_profit >= 0 else "#FF6666"
                self.total_profit_label.setText(f"${total_profit:.2f}")
                self.total_profit_label.setStyleSheet(f"color: {profit_color}; font-size: 12pt;")
                
                # Hands
                hands_played = stats.get('hands_played', 0)
                self.hands_played_label.setText(str(hands_played))
                
                # Vision errors
                vision_errors = stats.get('vision_errors', 0)
                self.vision_errors_label.setText(str(vision_errors))
                
                # Actions
                actions_executed = stats.get('actions_executed', 0)
                self.actions_executed_label.setText(str(actions_executed))
                
                # Collective edge
                collective_edge = stats.get('avg_collective_edge', 0.0)
                self.collective_edge_label.setText(f"{collective_edge:.1f}%")
                
                # Uptime
                uptime_seconds = int(stats.get('uptime_seconds', 0))
                hours = uptime_seconds // 3600
                minutes = (uptime_seconds % 3600) // 60
                seconds = uptime_seconds % 60
                self.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Vision health
                if active_bots > 0 and hands_played > 0:
                    error_rate = (vision_errors / max(hands_played, 1)) * 100
                    health = max(0, 100 - error_rate * 10)
                    self.vision_progress.setValue(int(health))
                    
                    # Update color
                    if health > 80:
                        color = "#66FF66"
                    elif health > 50:
                        color = "#FFAA00"
                    else:
                        color = "#FF6666"
                    
                    self.vision_progress.setStyleSheet(
                        f"QProgressBar::chunk {{ background-color: {color}; }}"
                    )
                else:
                    self.vision_progress.setValue(100)
                
                # Decision speed
                if actions_executed > 0 and uptime_seconds > 0:
                    actions_per_minute = (actions_executed / uptime_seconds) * 60
                    self.decision_label.setText(f"{actions_per_minute:.1f} actions/min")
                
                # Check for alerts
                self._check_alerts(stats)
            
            except Exception as e:
                logger.error(f"Failed to update dashboard statistics: {e}")
        
        def _check_alerts(self, stats: dict):
            """
            Check for active alerts.
            
            Args:
                stats: Statistics dictionary
            """
            alerts = []
            
            # Vision error rate
            vision_errors = stats.get('vision_errors', 0)
            hands_played = stats.get('hands_played', 0)
            
            if hands_played > 10:
                error_rate = vision_errors / hands_played
                if error_rate > 0.1:
                    alerts.append(f"⚠️ High vision error rate: {error_rate:.1%}")
            
            # Negative profit
            total_profit = stats.get('total_profit', 0.0)
            if total_profit < -100:
                alerts.append(f"⚠️ Large losses: ${abs(total_profit):.2f}")
            
            # No active bots
            active_bots = stats.get('active_bots', 0)
            if active_bots == 0 and stats.get('total_bots', 0) > 0:
                alerts.append("⚠️ No active bots running")
            
            # Display alerts
            if alerts:
                self.alerts_label.setText("\n".join(alerts))
                self.alerts_label.setStyleSheet("color: #FFFF66; padding: 10px;")
            else:
                self.alerts_label.setText("✓ No active alerts - System operating normally")
                self.alerts_label.setStyleSheet("color: #66FF66; padding: 10px;")
        
        def _on_emergency_stop(self):
            """Handle emergency stop."""
            from PyQt6.QtWidgets import QMessageBox
            
            reply = QMessageBox.critical(
                self,
                "EMERGENCY STOP",
                "Are you sure you want to IMMEDIATELY STOP all bots?\n\n"
                "This will:\n"
                "- Stop all bot instances\n"
                "- Disconnect from tables\n"
                "- End all HIVE sessions\n\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                logger.critical("EMERGENCY STOP requested by user")
                self.emergency_stop_requested.emit()
        
        def set_bot_manager(self, bot_manager):
            """
            Set bot manager.
            
            Args:
                bot_manager: Bot manager instance
            """
            self.bot_manager = bot_manager


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Dashboard Tab - Educational Research")
    print("=" * 60)
    print()
    
    print("DashboardTab Window (PyQt6):")
    print()
    print("  Emergency Controls:")
    print("    - Warning banner (orange)")
    print("    - Large EMERGENCY STOP button (red)")
    print("    - Confirmation dialog required")
    print()
    print("  System Statistics:")
    print("    - Total Bots / Active Bots")
    print("    - Active Tables / HIVE Teams")
    print("    - Total Profit (green/red)")
    print("    - Hands Played")
    print("    - Vision Errors (yellow)")
    print("    - Actions Executed")
    print("    - Avg Collective Edge (blue)")
    print("    - Session Uptime (HH:MM:SS)")
    print()
    print("  Performance Indicators:")
    print("    - Vision Health: Progress bar (0-100%)")
    print("      * Green (>80%), Orange (50-80%), Red (<50%)")
    print("    - Decision Speed: Actions/minute")
    print()
    print("  Active Alerts:")
    print("    - High vision error rate (>10%)")
    print("    - Large losses (< -$100)")
    print("    - No active bots")
    print("    - Display: Yellow warning or Green OK")
    print()
    print("  Real-time Updates:")
    print("    - QTimer: 1 second interval")
    print("    - Queries BotManager.get_statistics()")
    print("    - Auto-updates all displays")
    print()
    print("=" * 60)
    print("Dashboard tab demonstration complete")
    print("=" * 60)
