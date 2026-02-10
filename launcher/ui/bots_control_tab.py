"""
Bots Control Tab - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Start/stop individual bots
- Start collusion groups (3 bots)
- Monitor bot status
- View active sessions
"""

import logging
from typing import List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
        QTableWidget, QTableWidgetItem, QHeaderView,
        QLabel, QSpinBox, QGroupBox, QMessageBox,
        QComboBox
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.account import Account, AccountStatus
from launcher.auto_bot_controller import AutoBotController, BotState

logger = logging.getLogger(__name__)


class BotsControlTab(QWidget):
    """
    Bots control tab.
    
    Features:
    - Start/stop bots
    - Collusion groups
    - Status monitoring
    
    ⚠️ EDUCATIONAL NOTE:
        Controls automated bot operation.
    """
    
    def __init__(self, parent=None):
        """Initialize bots control tab."""
        super().__init__(parent)
        
        self.accounts: List[Account] = []
        self.controller = AutoBotController()
        
        self._setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # Update every second
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("🤖 Automated Bot Control")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #00AAFF;")
        layout.addWidget(header)
        
        # Quick Start Section
        quick_start_group = self._create_quick_start_section()
        layout.addWidget(quick_start_group)
        
        # Active Bots Table
        bots_group = QGroupBox("Active Bots")
        bots_layout = QVBoxLayout(bots_group)
        
        self.bots_table = QTableWidget()
        self.bots_table.setColumnCount(6)
        self.bots_table.setHorizontalHeaderLabels([
            "Nickname",
            "State",
            "Table",
            "Stack",
            "Uptime",
            "Actions"
        ])
        
        header = self.bots_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.bots_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        bots_layout.addWidget(self.bots_table)
        
        layout.addWidget(bots_group)
        
        # Control Buttons
        control_layout = QHBoxLayout()
        
        stop_all_btn = QPushButton("⏹️ Stop All Bots")
        stop_all_btn.setStyleSheet("background-color: #AA0000; color: white; font-weight: bold; padding: 10px;")
        stop_all_btn.clicked.connect(self._on_stop_all)
        control_layout.addWidget(stop_all_btn)
        
        debug_viewer_btn = QPushButton("🔍 Debug Viewer")
        debug_viewer_btn.setStyleSheet("background-color: #FF6600; color: white; font-weight: bold; padding: 10px;")
        debug_viewer_btn.setToolTip("See what the selected bot sees")
        debug_viewer_btn.clicked.connect(self._on_open_debug_viewer)
        control_layout.addWidget(debug_viewer_btn)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
    
    def _create_quick_start_section(self) -> QGroupBox:
        """Create quick start section."""
        group = QGroupBox("Quick Start")
        layout = QVBoxLayout(group)
        
        # Single Bot
        single_layout = QHBoxLayout()
        
        single_label = QLabel("Start Single Bot:")
        single_layout.addWidget(single_label)
        
        self.single_bot_combo = QComboBox()
        self.single_bot_combo.setPlaceholderText("Select account...")
        single_layout.addWidget(self.single_bot_combo)
        
        start_single_btn = QPushButton("▶️ Start Bot")
        start_single_btn.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold;")
        start_single_btn.clicked.connect(self._on_start_single_bot)
        single_layout.addWidget(start_single_btn)
        
        single_layout.addStretch()
        
        layout.addLayout(single_layout)
        
        # Collusion Group
        collusion_layout = QHBoxLayout()
        
        collusion_label = QLabel("Start Collusion Group (3 bots):")
        collusion_layout.addWidget(collusion_label)
        
        self.collusion_combo1 = QComboBox()
        self.collusion_combo1.setPlaceholderText("Bot 1...")
        collusion_layout.addWidget(self.collusion_combo1)
        
        self.collusion_combo2 = QComboBox()
        self.collusion_combo2.setPlaceholderText("Bot 2...")
        collusion_layout.addWidget(self.collusion_combo2)
        
        self.collusion_combo3 = QComboBox()
        self.collusion_combo3.setPlaceholderText("Bot 3...")
        collusion_layout.addWidget(self.collusion_combo3)
        
        start_collusion_btn = QPushButton("🤝 Start Collusion")
        start_collusion_btn.setStyleSheet("background-color: #9900FF; color: white; font-weight: bold; padding: 10px;")
        start_collusion_btn.clicked.connect(self._on_start_collusion)
        collusion_layout.addWidget(start_collusion_btn)
        
        layout.addLayout(collusion_layout)
        
        # Info
        info_label = QLabel(
            "ℹ️ Collusion: 3 bots will coordinate on the same table (3vs1 strategy)\n"
            "⚠️ Make sure all 3 accounts have Game Settings configured!"
        )
        info_label.setStyleSheet("color: #FFAA00; font-style: italic;")
        layout.addWidget(info_label)
        
        return group
    
    def set_accounts(self, accounts: List[Account]):
        """
        Set available accounts.
        
        Args:
            accounts: List of accounts
        """
        self.accounts = accounts
        self._update_account_combos()
    
    def _update_account_combos(self):
        """Update account combo boxes."""
        # Get ready accounts
        ready_accounts = [
            acc for acc in self.accounts
            if acc.window_info.is_captured() and acc.roi_configured and acc.game_preferences
        ]
        
        # Update combos
        for combo in [self.single_bot_combo, self.collusion_combo1, self.collusion_combo2, self.collusion_combo3]:
            combo.clear()
            for acc in ready_accounts:
                combo.addItem(acc.nickname, acc.account_id)
    
    def _on_start_single_bot(self):
        """Start single bot."""
        account_id = self.single_bot_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "No Selection", "Please select an account.")
            return
        
        account = next((a for a in self.accounts if a.account_id == account_id), None)
        if not account:
            return
        
        # Verify account is ready
        if not account.game_preferences:
            QMessageBox.warning(
                self,
                "Not Configured",
                f"Account {account.nickname} needs Game Settings.\n\n"
                "Go to Accounts tab and click 'Game Settings'."
            )
            return
        
        # Confirm
        games = [g.value for g in account.game_preferences.enabled_games]
        reply = QMessageBox.question(
            self,
            "Start Bot",
            f"Start bot for {account.nickname}?\n\n"
            f"Game modes: {', '.join(games)}\n"
            f"Stakes: {account.game_preferences.min_stake} - {account.game_preferences.max_stake}\n\n"
            f"Bot will:\n"
            f"1. Navigate to game mode\n"
            f"2. Find suitable table\n"
            f"3. Join and play\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        logger.info(f"Starting bot for {account.nickname}")
        
        success = self.controller.start_bot(account)
        
        if success:
            account.status = AccountStatus.RUNNING
            account.bot_running = True
            QMessageBox.information(
                self,
                "Bot Started",
                f"Bot started for {account.nickname}!\n\n"
                f"Check Logs tab for details."
            )
        else:
            QMessageBox.critical(
                self,
                "Start Failed",
                f"Failed to start bot for {account.nickname}.\n\n"
                "Check logs for details."
            )
    
    def _on_start_collusion(self):
        """Start collusion group."""
        # Get selected accounts
        account_ids = [
            self.collusion_combo1.currentData(),
            self.collusion_combo2.currentData(),
            self.collusion_combo3.currentData()
        ]
        
        if None in account_ids:
            QMessageBox.warning(self, "Incomplete Selection", "Please select all 3 accounts.")
            return
        
        # Check for duplicates
        if len(set(account_ids)) != 3:
            QMessageBox.warning(self, "Duplicate Selection", "Please select 3 different accounts.")
            return
        
        # Get accounts
        accounts = [
            next((a for a in self.accounts if a.account_id == aid), None)
            for aid in account_ids
        ]
        
        if None in accounts:
            return
        
        # Verify all configured
        for acc in accounts:
            if not acc.game_preferences:
                QMessageBox.warning(
                    self,
                    "Not Configured",
                    f"Account {acc.nickname} needs Game Settings.\n\n"
                    "Configure all 3 accounts first."
                )
                return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Start Collusion Group",
            f"Start collusion group?\n\n"
            f"Bots:\n"
            f"  1. {accounts[0].nickname}\n"
            f"  2. {accounts[1].nickname}\n"
            f"  3. {accounts[2].nickname}\n\n"
            f"⚠️ All 3 bots will:\n"
            f"1. Navigate to game mode\n"
            f"2. Find table with 1-3 players\n"
            f"3. Coordinate 3vs1 strategy\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        logger.info("=" * 60)
        logger.info("STARTING COLLUSION GROUP")
        logger.info(f"Bots: {[a.nickname for a in accounts]}")
        logger.info("=" * 60)
        
        success = self.controller.start_collusion_group(accounts)
        
        if success:
            for acc in accounts:
                acc.status = AccountStatus.RUNNING
                acc.bot_running = True
            
            QMessageBox.information(
                self,
                "Collusion Started",
                f"Collusion group started!\n\n"
                f"All 3 bots are now searching for suitable table.\n\n"
                f"Check Logs tab for detailed progress."
            )
        else:
            QMessageBox.critical(
                self,
                "Start Failed",
                "Failed to start collusion group.\n\n"
                "Check logs for details."
            )
    
    def _on_stop_all(self):
        """Stop all bots."""
        if not self.controller.sessions:
            QMessageBox.information(self, "No Active Bots", "No bots are currently running.")
            return
        
        reply = QMessageBox.question(
            self,
            "Stop All Bots",
            f"Stop all {len(self.controller.sessions)} active bots?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.stop_all()
            
            # Update account statuses
            for acc in self.accounts:
                if acc.bot_running:
                    acc.status = AccountStatus.READY
                    acc.bot_running = False
            
            QMessageBox.information(self, "Stopped", "All bots have been stopped.")
    
    def _update_status(self):
        """Update bot status table."""
        sessions = self.controller.get_all_sessions()
        
        self.bots_table.setRowCount(len(sessions))
        
        for row, session in enumerate(sessions):
            # Nickname
            self.bots_table.setItem(row, 0, QTableWidgetItem(session['nickname']))
            
            # State
            state_item = QTableWidgetItem(session['state'].upper())
            if session['state'] == 'playing':
                state_item.setForeground(QColor(0, 255, 0))
            elif session['state'] == 'error':
                state_item.setForeground(QColor(255, 0, 0))
            else:
                state_item.setForeground(QColor(255, 255, 0))
            self.bots_table.setItem(row, 1, state_item)
            
            # Table
            table_text = session['table_id'] if session['table_id'] else "Searching..."
            self.bots_table.setItem(row, 2, QTableWidgetItem(table_text))
            
            # Stack
            stack_text = f"${session['stack']:.2f}" if session['stack'] > 0 else "-"
            self.bots_table.setItem(row, 3, QTableWidgetItem(stack_text))
            
            # Uptime
            uptime = int(session['uptime'])
            minutes = uptime // 60
            seconds = uptime % 60
            uptime_text = f"{minutes}:{seconds:02d}"
            self.bots_table.setItem(row, 4, QTableWidgetItem(uptime_text))
            
            # Actions
            stop_btn = QPushButton("⏹️ Stop")
            stop_btn.setStyleSheet("background-color: #AA0000; color: white;")
            stop_btn.clicked.connect(lambda checked, aid=session['account_id']: self._stop_bot(aid))
            self.bots_table.setCellWidget(row, 5, stop_btn)
    
    def _stop_bot(self, account_id: str):
        """Stop specific bot."""
        self.controller.stop_bot(account_id)
        
        # Update account status
        account = next((a for a in self.accounts if a.account_id == account_id), None)
        if account:
            account.status = AccountStatus.READY
            account.bot_running = False
    
    def _on_open_debug_viewer(self):
        """Open debug viewer for selected bot."""
        row = self.bots_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a running bot from the table.")
            return
        
        # Get account ID from table
        account_id_item = self.bots_table.item(row, 0)
        if not account_id_item:
            return
        
        nickname = account_id_item.text()
        
        # Find account
        account = next((a for a in self.accounts if a.nickname == nickname), None)
        if not account:
            QMessageBox.warning(self, "Error", "Account not found.")
            return
        
        # Check if window is captured
        if not account.window_info.is_captured():
            QMessageBox.warning(
                self,
                "No Window",
                "Bot window information not available."
            )
            return
        
        # Import debug viewer
        try:
            from launcher.ui.debug_viewer import DebugViewer
        except ImportError:
            QMessageBox.critical(
                self,
                "Not Available",
                "Debug Viewer not available.\n\n"
                "Install required packages:\n"
                "pip install pillow opencv-python pytesseract"
            )
            return
        
        logger.info(f"Opening Debug Viewer for bot: {nickname}")
        
        # Create debug viewer
        debug_viewer = DebugViewer(self)
        
        # Prefer HWND for direct capture, fallback to bbox
        hwnd = account.window_info.hwnd
        window_bbox = None
        
        if hwnd:
            logger.info(f"Using direct window capture (HWND: {hwnd})")
        else:
            logger.warning("HWND not available, using screen region capture (may have issues)")
            x, y, w, h = account.window_info.position
            window_bbox = (x, y, w, h)
        
        # Show viewer and capture
        debug_viewer.show()
        debug_viewer.capture_and_detect(hwnd=hwnd, window_bbox=window_bbox)
        
        # Show info
        QMessageBox.information(
            self,
            "Debug Viewer",
            f"Debug Viewer opened for bot: {nickname}\n\n"
            f"This window shows:\n"
            f"• What the bot sees (captured screen)\n"
            f"• Detected UI elements (yellow boxes)\n"
            f"• Game mode buttons (green boxes)\n"
            f"• Real-time detection info\n\n"
            f"Enable 'Auto-Update' to see bot's vision in real-time!"
        )


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Bots Control Tab - Educational Research")
    print("=" * 60)
    print()
    print("Features:")
    print("  - Start/stop individual bots")
    print("  - Start collusion groups (3 bots)")
    print("  - Monitor bot status")
    print("  - Real-time updates")
    print()
    print("=" * 60)
