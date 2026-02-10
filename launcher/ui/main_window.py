"""
Main Window - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY - Bot management interface.
"""

import logging
import sys
from pathlib import Path

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QAction, QIcon
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QStatusBar,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False
    print("WARNING: PyQt6 not available")
    print("Install with: pip install PyQt6")

from launcher.config_manager import ConfigManager
from launcher.models.roi_config import ROIConfig, ROIZone
from launcher.bot_manager import BotManager
from launcher.bot_settings import BotSettings, BotSettingsManager
from launcher.log_handler import setup_launcher_logging

if PYQT6_AVAILABLE:
    from launcher.ui.accounts_tab import AccountsTab
    from launcher.ui.bots_control_tab import BotsControlTab
    from launcher.ui.settings_dialog import SettingsDialog
    from launcher.ui.logs_tab import LogsTab
    from launcher.ui.dashboard_tab import DashboardTab

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main launcher window.
    
    Features:
    - Tabbed interface (Accounts, ROI Config, Bots Control, Logs)
    - System tray integration
    - Global hotkey support
    - Status bar with real-time updates
    
    ⚠️ EDUCATIONAL NOTE:
        Interface for coordinated bot management.
        Educational research only.
    """
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        self.setWindowTitle("HIVE Launcher - Educational Research")
        self.setGeometry(100, 100, 1200, 800)
        
        # Setup logging
        self.log_handler = setup_launcher_logging(use_qt=True)
        
        # Config manager
        self.config_manager = ConfigManager()
        
        # Settings manager
        self.settings_manager = BotSettingsManager()
        
        # Bot manager
        self.bot_manager = BotManager()
        
        # Load saved data
        self.accounts = self.config_manager.load_accounts()
        self.global_settings = self.settings_manager.load_global_settings()
        
        logger.info(f"Loaded global settings: {self.global_settings.preset.value}")
        
        # Setup UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        
        # Show warning
        self._show_startup_warning()
    
    def _setup_ui(self):
        """Setup main UI layout."""
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Warning banner
        warning_label = QLabel(
            "⚠️ EDUCATIONAL RESEARCH ONLY - COLLUSION SYSTEM - ILLEGAL IN REAL POKER ⚠️"
        )
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet(
            "background-color: #ff4444; color: white; "
            "font-size: 14px; font-weight: bold; padding: 10px;"
        )
        layout.addWidget(warning_label)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create tabs
        self._create_tabs()
    
    def _create_tabs(self):
        """Create application tabs."""
        # Accounts tab (Phase 1)
        self.accounts_tab = AccountsTab()
        self.accounts_tab.account_added.connect(self._on_account_added)
        self.accounts_tab.account_removed.connect(self._on_account_removed)
        self.accounts_tab.roi_configured.connect(self._on_roi_configured)
        
        # Load accounts into tab
        self.accounts_tab.accounts = self.accounts
        self.accounts_tab._update_table()
        
        self.tabs.addTab(self.accounts_tab, "Accounts")
        
        # ROI Config tab
        roi_tab = QWidget()
        roi_layout = QVBoxLayout()
        roi_layout.addWidget(
            QLabel("ROI Configuration\n\nComing in Phase 1:\n"
                   "- Window overlay for drawing zones\n"
                   "- Card positions\n"
                   "- Button positions")
        )
        roi_tab.setLayout(roi_layout)
        self.tabs.addTab(roi_tab, "ROI Config")
        
        # Bots Control tab (Phase 2)
        self.bots_control_tab = BotsControlTab()
        self.bots_control_tab.set_accounts(self.accounts)
        
        self.tabs.addTab(self.bots_control_tab, "Bots Control")
        
        # Dashboard tab (Phase 6)
        self.dashboard_tab = DashboardTab(bot_manager=self.bot_manager)
        self.dashboard_tab.emergency_stop_requested.connect(self._on_emergency_stop)
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # Logs tab (Phase 6)
        self.logs_tab = LogsTab()
        self.logs_tab.load_initial_logs()
        self.tabs.addTab(self.logs_tab, "Logs")
    
    def _setup_menubar(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+S")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.status_label = QLabel("Ready (Dry-run mode)")
        self.statusbar.addWidget(self.status_label)
        
        # Timer for status updates (Phase 2+)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second
    
    def _update_status(self):
        """Update status bar."""
        # Count accounts by status
        total = len(self.accounts)
        ready = len([a for a in self.accounts if a.is_ready_to_run()])
        
        # Bot statistics
        bot_stats = self.bot_manager.get_statistics()
        active_bots = bot_stats.get('active_bots', 0)
        total_bots = bot_stats.get('total_bots', 0)
        
        status_text = (
            f"Accounts: {total} | Ready: {ready} | "
            f"Bots: {active_bots}/{total_bots} active | Mode: Dry-run"
        )
        self.status_label.setText(status_text)
    
    def _on_account_added(self, account):
        """Handle account added."""
        self.accounts.append(account)
        self.config_manager.save_accounts(self.accounts)
        self._update_status()
        logger.info(f"Account added: {account.nickname}")
    
    def _on_account_removed(self, account_id: str):
        """Handle account removed."""
        # Find and remove account
        self.accounts = [a for a in self.accounts if a.account_id != account_id]
        
        # Save and clean up ROI
        self.config_manager.save_accounts(self.accounts)
        self.config_manager.delete_roi_config(account_id)
        self._update_status()
        logger.info(f"Account removed: {account_id}")
    
    def _on_roi_configured(self, account_id: str, zones: list):
        """Handle ROI configured."""
        # Find account
        account = next((a for a in self.accounts if a.account_id == account_id), None)
        if not account:
            return
        
        # Create ROI config
        roi_config = ROIConfig(account_id=account_id)
        for zone in zones:
            roi_config.add_zone(zone)
        
        # Save
        self.config_manager.save_roi_config(account_id, roi_config)
        self.config_manager.save_accounts(self.accounts)
        self._update_status()
        logger.info(f"ROI configured for {account.nickname}: {len(zones)} zones")
        
        # Create bot if account is ready
        if account.is_ready_to_run():
            existing = self.bot_manager.get_bot_by_account(account_id)
            if not existing:
                self.bot_manager.create_bot(account, roi_config)
                logger.info(f"Bot created for {account.nickname}")
    
    def _on_bot_started(self, bot_id: str):
        """Handle bot started."""
        logger.info(f"Bot started: {bot_id[:8]}")
        self._update_status()
    
    def _on_bot_stopped(self, bot_id: str):
        """Handle bot stopped."""
        logger.info(f"Bot stopped: {bot_id[:8]}")
        self._update_status()
    
    def _on_emergency_stop(self):
        """Handle emergency stop."""
        logger.critical("EMERGENCY STOP activated")
        
        # Stop all bots immediately
        import asyncio
        
        async def stop_all():
            await self.bot_manager.stop_all()
        
        # Run in event loop
        try:
            asyncio.run(stop_all())
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
        
        # Show confirmation
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Emergency Stop Complete",
            "All bots have been stopped."
        )
        
        self._update_status()
    
    def _show_startup_warning(self):
        """Show startup warning dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("CRITICAL WARNING")
        msg.setText("Educational Research Only")
        msg.setInformativeText(
            "This software implements COORDINATED COLLUSION.\n\n"
            "ILLEGAL in real poker.\n"
            "EXTREMELY UNETHICAL.\n\n"
            "For educational game theory research ONLY.\n"
            "NEVER use without explicit consent of ALL participants.\n\n"
            "Continue only if you understand the ethical implications."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok |
            QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        
        result = msg.exec()
        
        if result == QMessageBox.StandardButton.Cancel:
            sys.exit(0)
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(
            parent=self,
            settings=self.global_settings,
            title="Global Bot Settings"
        )
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
    
    def _on_settings_saved(self, settings: BotSettings):
        """Handle settings saved."""
        self.global_settings = settings
        self.settings_manager.save_global_settings(settings)
        
        logger.info(
            f"Global settings saved: {settings.preset.value}, "
            f"aggression={settings.aggression_level}, "
            f"collusion={settings.enable_collusion}"
        )
        
        # Show confirmation
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Settings Saved",
            f"Global settings saved:\n"
            f"Preset: {settings.preset.value}\n"
            f"Aggression: {settings.aggression_level}/10\n"
            f"Equity: {settings.equity_threshold:.0%}"
        )
    
    def _show_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            "About HIVE Launcher",
            "HIVE Launcher v1.0.0\n\n"
            "Educational Game Theory Research\n\n"
            "WARNING: This software implements coordinated collusion.\n"
            "ILLEGAL in real poker. Educational research only.\n\n"
            "© 2026 - Educational Use Only"
        )
    
    def closeEvent(self, event):
        """Handle window close - save config."""
        # Save accounts on exit
        self.config_manager.save_accounts(self.accounts)
        logger.info("Launcher closed, configuration saved")
        event.accept()


def main():
    """Launch application."""
    if not PYQT6_AVAILABLE:
        print("ERROR: PyQt6 not available")
        print("Install with: pip install PyQt6")
        return 1
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern style
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
