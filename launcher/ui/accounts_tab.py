"""
Accounts Management Tab - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Account table (nickname, status, window, ROI, bot)
- Add/Edit/Remove accounts
- Capture windows
- Configure ROI
"""

import logging
import time
from typing import List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
        QTableWidget, QTableWidgetItem, QHeaderView,
        QDialog, QLineEdit, QLabel, QFormLayout,
        QComboBox, QMessageBox, QListWidget, QCheckBox,
        QProgressDialog, QDoubleSpinBox,
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, pyqtSlot
    from PyQt6.QtGui import QColor
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.account import Account, AccountStatus, WindowInfo, WindowType
from launcher.models.roi_config import ROIZone
from launcher.models.game_settings import GamePreferences
from launcher.window_capture import WindowCapture

def _detect_poker_client(title: str, process: str) -> str:
    """Guess poker client from window title / process name."""
    t = (title or "").lower()
    p = (process or "").lower()
    if "coinpoker" in t or "coin poker" in t or "coinpoker" in p:
        return "coinpoker"
    if "pokerstars" in t or "stars" in t or "pokerstars" in p:
        return "pokerstars"
    if "ggpoker" in t or "ggpoker" in p:
        return "ggpoker"
    if "partypoker" in t or "partypoker" in p:
        return "partypoker"
    return "unknown"

if PYQT_AVAILABLE:
    from launcher.ui.roi_overlay import ROIOverlay
    from launcher.ui.game_settings_dialog import GameSettingsDialog
    from launcher.ui.debug_viewer import DebugViewer
    from launcher.ui.theme import COLORS

# --- Auto-ROI worker ---------------------------------------------------

class _AutoROIWorker(QObject if PYQT_AVAILABLE else object):
    """Runs auto-ROI detection off the UI thread."""
    if PYQT_AVAILABLE:
        finished = pyqtSignal(list, list)   # (zones, anchors)
        error    = pyqtSignal(str)

    def __init__(self, hwnd: int) -> None:
        if PYQT_AVAILABLE:
            super().__init__()
        self._hwnd = hwnd

    @pyqtSlot() if PYQT_AVAILABLE else (lambda f: f)
    def run(self) -> None:
        try:
            from bridge.screen_capture import ScreenCapture
            from bridge.vision.anchor_detector import (
                detect_roi, load_config as load_anchor_config,
            )
            import numpy as np

            sc  = ScreenCapture()
            img = sc.capture(hwnd=self._hwnd)

            if img is None:
                self.error.emit("Capture returned None — is the window visible?")
                return

            # Normalise to numpy
            if hasattr(img, "convert"):
                import cv2
                img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

            cfg     = load_anchor_config()
            anchors, zones = detect_roi(img, config=cfg)

            zone_dicts = [
                (z.to_dict() if hasattr(z, "to_dict") else z)
                for z in zones
            ]
            anchor_dicts = [
                {"name": a.name, "x": a.x, "y": a.y,
                 "confidence": round(a.confidence, 3)}
                for a in anchors if hasattr(a, "name")
            ]
            self.finished.emit(zone_dicts, anchor_dicts)

        except Exception as exc:
            self.error.emit(str(exc))

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class AddAccountDialog(QDialog):
        """Dialog for adding/editing account."""
        
        def __init__(self, parent=None, account: Optional[Account] = None):
            """
            Initialize dialog.
            
            Args:
                parent: Parent widget
                account: Existing account to edit (if any)
            """
            super().__init__(parent)
            
            self.account = account
            self.edit_mode = account is not None
            
            self.setWindowTitle("Edit Account" if self.edit_mode else "Add Account")
            self.setModal(True)
            self.setMinimumWidth(400)
            
            self._setup_ui()
            
            if self.edit_mode:
                self._load_account()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QFormLayout(self)
            
            # Nickname
            self.nickname_input = QLineEdit()
            self.nickname_input.setPlaceholderText("e.g., TestBot001")
            layout.addRow("Nickname:", self.nickname_input)
            
            # Room
            self.room_combo = QComboBox()
            self.room_combo.addItems([
                "coinpoker",
                "pokerstars",
                "ignition",
                "ggpoker",
                "888poker",
                "partypoker"
            ])
            layout.addRow("Poker Room:", self.room_combo)
            
            # Chip balance (used for table buy-in filtering)
            bal_row = QHBoxLayout()
            self.balance_spin = QDoubleSpinBox()
            self.balance_spin.setRange(0, 100_000_000)
            self.balance_spin.setDecimals(0)
            self.balance_spin.setSingleStep(1000)
            self.balance_spin.setValue(0)
            self.balance_spin.setToolTip(
                "Your current chip balance in the poker room.\n"
                "The bot uses this to filter tables it can afford.\n"
                "Set to 0 to let the bot detect it automatically."
            )
            bal_row.addWidget(self.balance_spin)
            bal_lbl = QLabel("(0 = auto-detect from lobby)")
            bal_lbl.setStyleSheet("color: #888; font-size: 11px;")
            bal_row.addWidget(bal_lbl)
            layout.addRow("Chip Balance:", bal_row)

            # Notes
            self.notes_input = QLineEdit()
            self.notes_input.setPlaceholderText("Optional notes")
            layout.addRow("Notes:", self.notes_input)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(self.accept)
            btn_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
            
            layout.addRow(btn_layout)
        
        def _load_account(self):
            """Load account data."""
            if self.account:
                self.nickname_input.setText(self.account.nickname)
                self.room_combo.setCurrentText(self.account.room)
                self.balance_spin.setValue(float(getattr(self.account, 'balance', 0.0)))
                self.notes_input.setText(self.account.notes)
        
        def get_account_data(self) -> dict:
            """
            Get account data from form.
            
            Returns:
                Account data dict
            """
            return {
                'nickname': self.nickname_input.text().strip(),
                'room': self.room_combo.currentText(),
                'balance': float(self.balance_spin.value()),
                'notes': self.notes_input.text().strip()
            }
    
    
    class WindowSelectDialog(QDialog):
        """Dialog for selecting window."""
        
        def __init__(self, parent=None):
            """Initialize dialog."""
            super().__init__(parent)
            
            self.selected_window: Optional[dict] = None
            self.capture = WindowCapture()
            self.show_all = False
            
            self.setWindowTitle("Select Window")
            self.setModal(True)
            self.setMinimumSize(700, 500)
            
            self._setup_ui()
            self._refresh_windows()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Instructions
            label = QLabel("Select poker client window (or any window to capture):")
            layout.addWidget(label)
            
            # Filter options
            filter_layout = QHBoxLayout()
            
            self.show_all_checkbox = QCheckBox("Show all windows (including hidden)")
            self.show_all_checkbox.stateChanged.connect(self._on_filter_changed)
            filter_layout.addWidget(self.show_all_checkbox)
            
            filter_layout.addStretch()
            
            self.count_label = QLabel()
            filter_layout.addWidget(self.count_label)
            
            layout.addLayout(filter_layout)
            
            # Window list
            self.window_list = QListWidget()
            self.window_list.itemDoubleClicked.connect(self._on_window_selected)
            layout.addWidget(self.window_list)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            refresh_btn = QPushButton("Refresh")
            refresh_btn.clicked.connect(self._refresh_windows)
            btn_layout.addWidget(refresh_btn)
            
            select_btn = QPushButton("Select")
            select_btn.clicked.connect(self._on_select_clicked)
            btn_layout.addWidget(select_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
        
        def _on_filter_changed(self, state):
            """Handle filter checkbox change."""
            self.show_all = (state == 2)  # Qt.CheckState.Checked = 2
            self._refresh_windows()
        
        def _refresh_windows(self):
            """Refresh window list."""
            self.window_list.clear()
            
            if not self.capture.available:
                self.window_list.addItem("Window capture not available (requires pywin32)")
                return
            
            # Get windows with appropriate filters
            windows = self.capture.list_windows(
                filter_visible=not self.show_all,
                min_width=10 if self.show_all else 100,
                min_height=10 if self.show_all else 50
            )
            
            if not windows:
                self.window_list.addItem("No windows found")
                self.count_label.setText("Found: 0 windows")
                return
            
            # Sort windows by title for easier browsing
            windows.sort(key=lambda w: w['title'].lower())
            
            self.count_label.setText(f"Found: {len(windows)} windows")
            
            for window in windows:
                # Format with size info
                w, h = window['position'][2], window['position'][3]
                item_text = f"{window['title']} | {window['process_name']} | {w}x{h}"
                item = self.window_list.addItem(item_text)
                # Store window data
                self.window_list.item(self.window_list.count() - 1).setData(
                    Qt.ItemDataRole.UserRole,
                    window
                )
        
        def _on_window_selected(self, item):
            """Handle window double-click selection."""
            # Use the same logic as _on_select_clicked
            self._on_select_clicked()
        
        def _on_select_clicked(self):
            """Handle select button."""
            current = self.window_list.currentItem()
            if not current:
                return
            
            window = current.data(Qt.ItemDataRole.UserRole)
            
            # Check if this is a child window and offer to capture parent instead
            try:
                from launcher.vision import WindowCapturer
                capturer = WindowCapturer()
                
                if capturer.available:
                    window_info = capturer.get_window_info(window['hwnd'])
                    
                    if window_info.get('is_child') and window_info.get('root_hwnd'):
                        root_hwnd = window_info['root_hwnd']
                        root_info = capturer.get_window_info(root_hwnd)
                        
                        reply = QMessageBox.question(
                            self,
                            "Child Window Detected",
                            f"⚠️ Warning: You selected a child window!\n\n"
                            f"Selected: {window['title']}\n"
                            f"Size: {window['position'][2]}x{window['position'][3]}\n\n"
                            f"Root window found: {root_info['title']}\n"
                            f"Size: {root_info['position'][2]}x{root_info['position'][3]}\n\n"
                            f"Child windows may not capture the full application content.\n\n"
                            f"Do you want to capture the ROOT WINDOW instead?\n"
                            f"(Recommended for full window capture)",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.Yes
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            # Use root window instead
                            self.selected_window = {
                                'window_id': str(root_hwnd),
                                'hwnd': root_hwnd,
                                'title': root_info['title'],
                                'position': root_info['position'],
                                'process_name': window.get('process_name', 'unknown')
                            }
                            logger.info(f"User chose ROOT window: {root_info['title']} (HWND: {root_hwnd})")
                            self.accept()
                            return
            except Exception as e:
                logger.warning(f"Failed to check for child window: {e}")
            
            # Use selected window as-is
            self.selected_window = window
            self.accept()
    
    
    class AccountsTab(QWidget):
        """
        Accounts management tab.
        
        Features:
        - Account table
        - Add/Edit/Remove accounts
        - Capture windows
        - Configure ROI
        
        ⚠️ EDUCATIONAL NOTE:
            Manages bot accounts for coordinated operation.
        
        Signals:
            account_added: Emitted when account is added
            account_removed: Emitted when account is removed
            roi_configured: Emitted when ROI is configured
        """
        
        account_added = pyqtSignal(Account)
        account_removed = pyqtSignal(str)  # account_id
        roi_configured = pyqtSignal(str, list)  # account_id, zones
        
        def __init__(self, parent=None):
            """Initialize accounts tab."""
            super().__init__(parent)
            
            self.accounts: List[Account] = []
            
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Table
            self.table = QTableWidget()
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels([
                "№",
                "Nickname",
                "Status",
                "Window",
                "ROI Zones",
                "Games",
                "Bot Running",
            ])
            
            # Table settings
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            
            layout.addWidget(self.table)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            add_btn = QPushButton("➕ Add Account")
            add_btn.clicked.connect(self._on_add_account)
            btn_layout.addWidget(add_btn)
            
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.clicked.connect(self._on_edit_account)
            btn_layout.addWidget(edit_btn)
            
            remove_btn = QPushButton("❌ Remove")
            remove_btn.clicked.connect(self._on_remove_account)
            btn_layout.addWidget(remove_btn)
            
            btn_layout.addStretch()
            
            # Quick-find CoinPoker button
            find_cp_btn = QPushButton("🪙 Find CoinPoker")
            find_cp_btn.setToolTip("Auto-find a running CoinPoker window and assign it")
            find_cp_btn.setStyleSheet("background-color: #1a4a6b; color: #7fd4ff; font-weight: bold;")
            find_cp_btn.clicked.connect(self._on_find_coinpoker)
            btn_layout.addWidget(find_cp_btn)

            capture_btn = QPushButton("🪟 Capture Window")
            capture_btn.clicked.connect(self._on_capture_window)
            btn_layout.addWidget(capture_btn)
            
            roi_btn = QPushButton("📐 Configure ROI")
            roi_btn.clicked.connect(self._on_configure_roi)
            btn_layout.addWidget(roi_btn)
            
            game_settings_btn = QPushButton("🎮 Game Settings")
            game_settings_btn.setStyleSheet("background-color: #0066CC; color: white;")
            game_settings_btn.clicked.connect(self._on_game_settings)
            btn_layout.addWidget(game_settings_btn)
            
            # Skip ROI button (for testing without real window capture)
            skip_roi_btn = QPushButton("⚠️ Skip ROI (Test Mode)")
            skip_roi_btn.setStyleSheet("background-color: #FFA500; color: white;")
            skip_roi_btn.clicked.connect(self._on_skip_roi)
            btn_layout.addWidget(skip_roi_btn)
            
            layout.addLayout(btn_layout)
            
            # Second row: Auto-ROI + Debug viewer
            row2 = QHBoxLayout()

            auto_roi_btn = QPushButton("🎯 Auto-Detect ROI")
            auto_roi_btn.setProperty("class", "primary")
            auto_roi_btn.setToolTip(
                "Automatically detect ROI zones using anchor template matching.\n"
                "Requires window captured and bridge/vision available."
            )
            auto_roi_btn.clicked.connect(self._on_auto_detect_roi)
            row2.addWidget(auto_roi_btn)

            debug_viewer_btn = QPushButton("🔍 Debug Viewer")
            debug_viewer_btn.setStyleSheet("background-color: #FF6600; color: white; font-weight: bold;")
            debug_viewer_btn.setToolTip("Visual feedback: see what bot sees")
            debug_viewer_btn.clicked.connect(self._on_open_debug_viewer)
            row2.addWidget(debug_viewer_btn)

            test_auto_nav_btn = QPushButton("🤖 Test Navigation")
            test_auto_nav_btn.setStyleSheet("background-color: #9900FF; color: white; font-weight: bold;")
            test_auto_nav_btn.setToolTip("Test automatic UI detection and navigation")
            test_auto_nav_btn.clicked.connect(self._on_test_auto_navigation)
            row2.addWidget(test_auto_nav_btn)

            row2.addStretch()
            layout.addLayout(row2)
        
        def _on_add_account(self):
            """Add new account."""
            dialog = AddAccountDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_account_data()
                
                if not data['nickname']:
                    QMessageBox.warning(self, "Invalid Input", "Nickname is required.")
                    return
                
                # Create account
                account = Account(
                    nickname=data['nickname'],
                    room=data['room'],
                    notes=data['notes'],
                    balance=data.get('balance', 0.0),
                )
                
                self.accounts.append(account)
                self._update_table()
                self.account_added.emit(account)
                
                logger.info(f"Account added: {account.nickname}")
        
        def _on_edit_account(self):
            """Edit selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account to edit.")
                return
            
            account = self.accounts[row]
            dialog = AddAccountDialog(self, account)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_account_data()
                
                account.nickname = data['nickname']
                account.room = data['room']
                account.notes = data['notes']
                account.balance = data.get('balance', account.balance)

                self._update_table()
                logger.info(f"Account updated: {account.nickname} balance={account.balance:.0f}")
        
        def _on_remove_account(self):
            """Remove selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account to remove.")
                return
            
            account = self.accounts[row]
            
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Remove account '{account.nickname}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.accounts.pop(row)
                self._update_table()
                self.account_removed.emit(account.account_id)
                
                logger.info(f"Account removed: {account.nickname}")
        
        def _on_capture_window(self):
            """Capture window for selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            # Show window selection dialog
            dialog = WindowSelectDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                window = dialog.selected_window
                
                if window:
                    account.window_info = WindowInfo(
                        window_id=window['window_id'],
                        hwnd=window.get('hwnd'),
                        window_title=window['title'],
                        window_type=WindowType.DESKTOP_CLIENT,
                        process_name=window.get('process_name'),
                        position=window.get('position'),
                    )
                    # Auto-detect poker client from title/process
                    try:
                        from launcher.models.account import PokerClient
                        detected = _detect_poker_client(
                            window['title'], window.get('process_name', ''))
                        account.poker_client = PokerClient(detected)
                        if detected == 'coinpoker':
                            logger.info("CoinPoker window detected for %s", account.nickname)
                    except Exception:
                        pass
                    
                    # Update status
                    if account.status == AccountStatus.IDLE:
                        account.status = AccountStatus.READY if account.roi_configured else AccountStatus.IDLE
                    
                    self._update_table()
                    logger.info(f"Window captured for {account.nickname}: {window['title']}")
        

        def _on_find_coinpoker(self):
            """Auto-find a running CoinPoker window and assign it to selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Select an account first.")
                return
            account = self.accounts[row]
            found_raw = []
            try:
                from launcher.window_capture import WindowCapture as _WC
                _wc = _WC()
                wins = _wc.list_windows(filter_visible=True, min_width=400, min_height=300)
                found_raw = [w for w in wins
                             if "coinpoker" in (w.get("title","")).lower()
                             or "coinpoker" in (w.get("process_name","")).lower()]
            except Exception as exc:
                logger.warning("CoinPoker search error: %s", exc)

            if not found_raw:
                # Try AutoWindowFinder
                try:
                    from launcher.auto_window_finder import AutoWindowFinder
                    finder = AutoWindowFinder()
                    matches = finder.find_all_poker()
                    for m in matches:
                        if "coinpoker" in (m.title or "").lower() or "coinpoker" in (m.process_name or "").lower():
                            found_raw = [{"hwnd": m.hwnd, "title": m.title,
                                          "process_name": m.process_name,
                                          "position": (m.client_rect.x, m.client_rect.y,
                                                       m.client_rect.w, m.client_rect.h)
                                          if hasattr(m,"client_rect") and m.client_rect else None,
                                          "window_id": str(m.hwnd)}]
                            break
                except Exception as exc2:
                    logger.warning("AutoWindowFinder error: %s", exc2)

            if not found_raw:
                QMessageBox.warning(self, "CoinPoker Not Found",
                    "No running CoinPoker window found.\n\nMake sure CoinPoker is open, "
                    "then try again — or use 'Capture Window' to select manually.")
                return

            w = found_raw[0]
            account.window_info = WindowInfo(
                window_id=str(w.get("hwnd", w.get("window_id",""))),
                hwnd=w.get("hwnd"),
                window_title=w.get("title","CoinPoker"),
                window_type=WindowType.DESKTOP_CLIENT,
                process_name=w.get("process_name"),
                position=w.get("position"),
            )
            try:
                from launcher.models.account import PokerClient
                account.poker_client = PokerClient.COINPOKER
            except Exception:
                pass
            if account.status == AccountStatus.IDLE:
                account.status = AccountStatus.READY if account.roi_configured else AccountStatus.IDLE
            self._update_table()
            title = w.get("title","CoinPoker")
            QMessageBox.information(self, "CoinPoker Found",
                f"CoinPoker assigned to {account.nickname}:\n{title}")
            logger.info("CoinPoker auto-assigned to %s: %s", account.nickname, title)

        def _on_configure_roi(self):
            """Configure ROI for selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            logger.info(f"Configure ROI requested for: {account.nickname}")
            logger.info(f"  Window ID: {account.window_info.window_id}")
            logger.info(f"  Window Title: {account.window_info.window_title}")
            logger.info(f"  Is captured: {account.window_info.is_captured()}")
            
            if not account.window_info.is_captured():
                QMessageBox.warning(
                    self,
                    "No Window",
                    f"Please capture a window first before configuring ROI.\n\n"
                    f"Current window status:\n"
                    f"  Window ID: {account.window_info.window_id}\n"
                    f"  Title: {account.window_info.window_title or 'Not captured'}"
                )
                return
            
            try:
                logger.info(f"Creating ROI overlay for window {account.window_info.window_id}")
                
                # Show ROI overlay
                overlay = ROIOverlay(self, account.window_info.window_id)
                overlay.roi_saved.connect(lambda zones: self._on_roi_saved(account, zones))
                
                # Make sure overlay is visible and on top
                overlay.showFullScreen()
                overlay.raise_()
                overlay.activateWindow()
                
                logger.info("ROI overlay shown")
                
            except Exception as e:
                logger.error(f"Failed to show ROI overlay: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "ROI Error",
                    f"Failed to open ROI overlay:\n{str(e)}\n\n"
                    f"This may happen if:\n"
                    f"- Window is minimized or closed\n"
                    f"- Window ID is invalid\n"
                    f"- Screen capture not available\n\n"
                    f"Try recapturing the window."
                )
                return
        
        def _on_skip_roi(self):
            """Skip ROI configuration for testing (creates dummy zones)."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            # Confirm test mode
            reply = QMessageBox.question(
                self,
                "Test Mode",
                f"Skip ROI for {account.nickname}?\n\n"
                f"This will create DUMMY ROI zones for testing.\n"
                f"Bot will NOT be able to interact with real poker client.\n\n"
                f"Use this ONLY for testing the launcher interface.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Create dummy window info if not captured
            if not account.window_info.is_captured():
                account.window_info = WindowInfo(
                    window_id="dummy_window_test",
                    window_title="Test Window (Dummy)",
                    window_type=WindowType.DESKTOP_CLIENT,
                    process_name="test.exe",
                    position=(0, 0, 1920, 1080)
                )
            
            # Create dummy ROI zones
            dummy_zones = [
                ROIZone(name="cards", x=100, y=100, width=200, height=150),
                ROIZone(name="button_fold", x=300, y=500, width=80, height=40),
                ROIZone(name="button_call", x=400, y=500, width=80, height=40),
                ROIZone(name="button_raise", x=500, y=500, width=80, height=40)
            ]
            
            self._on_roi_saved(account, dummy_zones)
            
            logger.warning(f"TEST MODE: ROI skipped for {account.nickname} - dummy zones created")
            
            QMessageBox.information(
                self,
                "Test Mode Enabled",
                f"Account {account.nickname} is now in TEST MODE.\n\n"
                f"Dummy ROI zones created.\n"
                f"Bot will appear as READY but cannot interact with real poker."
            )
        
        def _on_auto_detect_roi(self):
            """Auto-detect ROI synchronously in main thread (no threading to avoid signal issues)."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Select an account first.")
                return
            account = self.accounts[row]
            if not account.window_info or not account.window_info.hwnd:
                QMessageBox.warning(self, "No Window Handle",
                    "Capture a window first (Find CoinPoker or Capture Window).")
                return

            # Store current account reference (used by _on_roi_detected/_on_roi_detect_error)
            self._roi_account = account

            # Find the Auto-Detect button and disable only it (not the whole tab)
            sender_btn = self.sender()
            if sender_btn:
                sender_btn.setEnabled(False)
                sender_btn.setText("⏳ Detecting…")

            try:
                from bridge.screen_capture import ScreenCapture
                sc = ScreenCapture()
                img = sc.capture_full_window(hwnd=account.window_info.hwnd)
                if img is None:
                    raise RuntimeError("Could not capture window — is CoinPoker visible?")

                import numpy as np
                import cv2 as _cv2
                if hasattr(img, "convert"):
                    img = _cv2.cvtColor(np.array(img.convert("RGB")), _cv2.COLOR_RGB2BGR)

                zones, anchors = [], []
                try:
                    from bridge.vision.anchor_detector import (
                        detect_roi, load_config as _load_cfg)
                    anchors_raw, zones_raw = detect_roi(img, config=_load_cfg())
                    zones   = [z.to_dict() if hasattr(z, "to_dict") else z for z in zones_raw]
                    anchors = [{"name": a.name, "x": a.x, "y": a.y,
                                "confidence": round(a.confidence, 3)}
                               for a in anchors_raw if hasattr(a, "name")]
                except Exception as det_exc:
                    logger.warning("anchor_detector unavailable: %s", det_exc)

                if sender_btn:
                    sender_btn.setEnabled(True)
                    sender_btn.setText("🎯 Auto-Detect ROI")
                self._on_roi_detected(zones, anchors)

            except Exception as exc:
                if sender_btn:
                    sender_btn.setEnabled(True)
                    sender_btn.setText("🎯 Auto-Detect ROI")
                self._on_roi_detect_error(str(exc))
        @pyqtSlot(list, list)
        def _on_roi_detected(self, zones: list, anchors: list):
            """Handle successful auto-ROI detection result."""
            account = getattr(self, "_roi_account", None)
            if account is None:
                return

            if not zones:
                # Offer fallback
                reply = QMessageBox.question(
                    self,
                    "No Zones Detected",
                    f"No anchor zones detected for {account.nickname}.\n\n"
                    "Possible reasons:\n"
                    "• Poker window is not a supported layout\n"
                    "• Anchor templates not configured\n"
                    "• Window is obscured\n\n"
                    "Would you like to use manual ROI drawing instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._on_configure_roi()
                return

            # Build readable summary
            zone_lines = []
            for z in zones:
                if isinstance(z, dict):
                    name = z.get("name", "?")
                    x, y = z.get("x", 0), z.get("y", 0)
                    w = z.get("w", z.get("width", 0))
                    h = z.get("h", z.get("height", 0))
                else:
                    name = getattr(z, "name", "?")
                    x, y = getattr(z, "x", 0), getattr(z, "y", 0)
                    w = getattr(z, "w", getattr(z, "width", 0))
                    h = getattr(z, "h", getattr(z, "height", 0))
                zone_lines.append(f"  • {name}  ({x},{y})  {w}×{h}")

            anchor_summary = (
                f"\nAnchors found: {len(anchors)}\n"
                + "\n".join(
                    f"  ◉ {a['name']}  conf={a['confidence']:.2f}"
                    for a in anchors
                )
                if anchors else "\nNo anchors found (fallback zones used)"
            )

            msg = (
                f"Auto-ROI Detection Complete\n\n"
                f"Account: {account.nickname}\n"
                f"Zones found: {len(zones)}\n"
                f"{anchor_summary}\n\n"
                f"Zones:\n" + "\n".join(zone_lines) + "\n\n"
                "Apply these zones to the account?"
            )

            reply = QMessageBox.question(
                self, "Auto-ROI Result",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Convert to ROIZone list
                roi_zones = []
                for z in zones:
                    if isinstance(z, dict):
                        roi_zones.append(ROIZone(
                            name=z.get("name", "zone"),
                            x=int(z.get("x", 0)),
                            y=int(z.get("y", 0)),
                            width=int(z.get("w", z.get("width", 50))),
                            height=int(z.get("h", z.get("height", 30))),
                        ))
                    else:
                        roi_zones.append(z)
                self._on_roi_saved(account, roi_zones)
                logger.info(
                    "Auto-ROI applied for %s: %d zones, %d anchors",
                    account.nickname, len(roi_zones), len(anchors),
                )

        @pyqtSlot(str)
        def _on_roi_detect_error(self, msg: str):
            """Handle auto-ROI detection error."""
            QMessageBox.critical(
                self,
                "Auto-ROI Failed",
                f"Auto-ROI detection failed:\n\n{msg}\n\n"
                "Make sure:\n"
                "• bridge/vision/anchor_detector is installed\n"
                "• numpy and opencv are available\n"
                "• Window is visible and not minimized",
            )
            logger.error("Auto-ROI error: %s", msg)

        def _on_roi_saved(self, account: Account, zones: list):
            """Handle ROI configuration saved."""
            account.roi_configured = True

            if account.window_info.is_captured():
                account.status = AccountStatus.READY

            self._update_table()
            self.roi_configured.emit(account.account_id, zones)
            
            logger.info(f"ROI configured for {account.nickname}: {len(zones)} zones")
        
        def _on_game_settings(self):
            """Configure game preferences for selected account."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            # Open game settings dialog
            dialog = GameSettingsDialog(self, account.game_preferences)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                preferences = dialog.get_preferences()
                account.game_preferences = preferences
                
                # Log summary
                enabled_games = [g.value for g in preferences.enabled_games]
                logger.info(f"Game settings configured for {account.nickname}:")
                logger.info(f"  Games: {', '.join(enabled_games)}")
                logger.info(f"  Stakes: {preferences.min_stake} - {preferences.max_stake}")
                logger.info(f"  Player range: {preferences.min_players}-{preferences.max_players}")
                logger.info(f"  Auto-join: {preferences.auto_join_tables}")
                
                QMessageBox.information(
                    self,
                    "Settings Saved",
                    f"Game settings saved for {account.nickname}.\n\n"
                    f"Enabled games: {', '.join(enabled_games)}\n"
                    f"Stakes: {preferences.min_stake} - {preferences.max_stake}\n"
                    f"Player range: {preferences.min_players}-{preferences.max_players} players"
                )
        
        def _on_test_auto_navigation(self):
            """Test automatic UI detection and navigation."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            # Check if window is captured
            if not account.window_info.is_captured():
                QMessageBox.warning(
                    self,
                    "No Window",
                    "Please capture a window first.\n\n"
                    "Steps:\n"
                    "1. Capture poker client window\n"
                    "2. Configure game settings\n"
                    "3. Test auto-navigation"
                )
                return
            
            # Check if game preferences are set
            if not account.game_preferences:
                QMessageBox.warning(
                    self,
                    "No Game Settings",
                    "Please configure game settings first.\n\n"
                    "Click 'Game Settings' button to configure."
                )
                return
            
            # Import auto-navigator
            try:
                from launcher.vision import AutoNavigator, AutoUIDetector
            except ImportError:
                QMessageBox.critical(
                    self,
                    "Not Available",
                    "Auto-navigation not available.\n\n"
                    "Install required packages:\n"
                    "pip install pillow opencv-python pytesseract pyautogui pywin32"
                )
                return
            
            # Show info dialog
            enabled_games = [g.value for g in account.game_preferences.enabled_games]
            first_game = enabled_games[0] if enabled_games else "Hold'em"
            
            reply = QMessageBox.question(
                self,
                "Test Auto-Navigation",
                f"This will test automatic UI detection for:\n\n"
                f"Account: {account.nickname}\n"
                f"Window: {account.window_info.window_title}\n"
                f"Target game: {first_game}\n\n"
                f"The bot will:\n"
                f"1. Scan UI and detect elements (OCR)\n"
                f"2. Find '{first_game}' button\n"
                f"3. Log detected elements\n\n"
                f"⚠️ This is a TEST - no actual clicks will be made yet.\n\n"
                f"Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            logger.info("=" * 60)
            logger.info("AUTO-NAVIGATION TEST STARTED")
            logger.info(f"Account: {account.nickname}")
            logger.info(f"Window: {account.window_info.window_title}")
            logger.info("=" * 60)
            
            try:
                # Create detector
                detector = AutoUIDetector()
                
                if not detector.available:
                    QMessageBox.critical(
                        self,
                        "Not Available",
                        "Vision system not available.\n\n"
                        "Check logs for details."
                    )
                    return
                
                # Get window bounds
                x, y, w, h = account.window_info.position
                window_bbox = (x, y, w, h)
                
                logger.info(f"Capturing window: {window_bbox}")
                
                # Capture window
                image = detector.capture_window(bbox=window_bbox)
                if image is None:
                    QMessageBox.critical(
                        self,
                        "Capture Failed",
                        "Failed to capture window.\n\n"
                        "Make sure the window is visible and not minimized."
                    )
                    return
                
                logger.info(f"Captured image: {image.shape}")
                
                # Detect UI elements
                logger.info("Detecting UI elements...")
                elements = detector.detect_ui_elements(image)
                
                logger.info(f"Detected {len(elements)} UI elements")
                
                # Log all detected elements
                for i, elem in enumerate(elements, 1):
                    logger.info(f"  [{i}] {elem.element_type.value}: '{elem.text}' @ {elem.bbox} (conf: {elem.confidence:.2f})")
                
                # Find game mode buttons
                game_buttons = detector.find_game_mode_buttons(elements)
                
                logger.info(f"\nFound {len(game_buttons)} game mode buttons:")
                for mode, elem in game_buttons.items():
                    logger.info(f"  - {mode}: {elem.bbox}")
                
                # Check if target game was found
                target_found = any(first_game.lower() in mode.lower() for mode in game_buttons.keys())
                
                # Show results
                result_text = f"Auto-Navigation Test Results:\n\n"
                result_text += f"✅ Captured window: {w}x{h}\n"
                result_text += f"✅ Detected {len(elements)} UI elements\n"
                result_text += f"✅ Found {len(game_buttons)} game mode buttons\n\n"
                
                if target_found:
                    result_text += f"✅ Target game '{first_game}' FOUND!\n\n"
                else:
                    result_text += f"⚠️ Target game '{first_game}' NOT found.\n\n"
                
                result_text += f"Game modes detected:\n"
                for mode in game_buttons.keys():
                    result_text += f"  - {mode}\n"
                
                result_text += f"\n📋 Check logs for detailed information."
                
                QMessageBox.information(
                    self,
                    "Test Complete",
                    result_text
                )
                
                logger.info("=" * 60)
                logger.info("AUTO-NAVIGATION TEST COMPLETED")
                logger.info("=" * 60)
            
            except Exception as e:
                logger.error(f"Auto-navigation test failed: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Test Failed",
                    f"Auto-navigation test failed:\n\n{str(e)}\n\n"
                    f"Check logs for details."
                )
        
        def _on_open_debug_viewer(self):
            """Open debug viewer window."""
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.information(self, "No Selection", "Please select an account first.")
                return
            
            account = self.accounts[row]
            
            # Check if window is captured
            if not account.window_info.is_captured():
                QMessageBox.warning(
                    self,
                    "No Window",
                    "Please capture a window first.\n\n"
                    "The Debug Viewer shows what the bot sees in the captured window."
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
            
            logger.info(f"Opening Debug Viewer for {account.nickname}")
            
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
                f"Debug Viewer opened!\n\n"
                f"This window shows:\n"
                f"• Captured screen from bot's perspective\n"
                f"• Detected UI elements (yellow boxes)\n"
                f"• Game mode buttons (green boxes)\n"
                f"• Detection info and logs\n\n"
                f"Use '📸 Capture Now' to refresh.\n"
                f"Enable 'Auto-Update' for real-time view."
            )
        
        def _update_table(self):
            """Update accounts table."""
            self.table.setRowCount(len(self.accounts))
            
            for row, account in enumerate(self.accounts):
                # Number
                self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                
                # Nickname
                self.table.setItem(row, 1, QTableWidgetItem(account.nickname))
                
                # Status
                status_item = QTableWidgetItem(account.status.value.upper())
                if account.status == AccountStatus.READY:
                    status_item.setForeground(QColor(0, 255, 0))
                elif account.status == AccountStatus.RUNNING:
                    status_item.setForeground(QColor(0, 200, 255))
                elif account.status == AccountStatus.ERROR:
                    status_item.setForeground(QColor(255, 0, 0))
                self.table.setItem(row, 2, status_item)
                
                # Window
                window_text = account.window_info.window_title if account.window_info.is_captured() else "Not captured"
                self.table.setItem(row, 3, QTableWidgetItem(window_text))
                
                # ROI Zones — show count if available, else ✓/✗
                roi_zones = getattr(account, "roi_zones", None) or []
                n_zones = len(roi_zones)
                if n_zones > 0:
                    roi_text = f"{n_zones} zones"
                    roi_color = QColor(0, 220, 100)
                elif account.roi_configured:
                    roi_text = "✓ ready"
                    roi_color = QColor(0, 200, 255)
                else:
                    roi_text = "✗ not set"
                    roi_color = QColor(255, 100, 100)
                roi_item = QTableWidgetItem(roi_text)
                roi_item.setForeground(roi_color)
                self.table.setItem(row, 4, roi_item)
                
                # Games
                if account.game_preferences:
                    games_count = len(account.game_preferences.enabled_games)
                    games_text = f"{games_count} game(s)"
                    games_item = QTableWidgetItem(games_text)
                    games_item.setForeground(QColor(0, 200, 255))
                else:
                    games_item = QTableWidgetItem("Not set")
                    games_item.setForeground(QColor(200, 200, 200))
                self.table.setItem(row, 5, games_item)
                
                # Bot Running
                bot_item = QTableWidgetItem("✓" if account.bot_running else "✗")
                bot_item.setForeground(QColor(0, 255, 0) if account.bot_running else QColor(150, 150, 150))
                self.table.setItem(row, 6, bot_item)
        
        def get_accounts(self) -> List[Account]:
            """
            Get all accounts.
            
            Returns:
                List of accounts
            """
            return self.accounts
        
        def get_ready_accounts(self) -> List[Account]:
            """
            Get accounts ready to run.
            
            Returns:
                List of ready accounts
            """
            return [acc for acc in self.accounts if acc.is_ready_to_run()]


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Accounts Tab - Educational Research")
    print("=" * 60)
    print()
    
    print("Accounts Management Tab:")
    print("  - Account table with status indicators")
    print("  - Add/Edit/Remove accounts")
    print("  - Capture poker client windows")
    print("  - Configure ROI zones via overlay")
    print()
    
    print("Table columns:")
    print("  1. Number")
    print("  2. Nickname")
    print("  3. Status (IDLE/READY/RUNNING/ERROR)")
    print("  4. Window (captured window title)")
    print("  5. ROI Ready (✓/✗)")
    print("  6. Bot Running (✓/✗)")
    print()
    
    print("Actions:")
    print("  - Add Account: Open form dialog")
    print("  - Edit: Modify nickname/room/notes")
    print("  - Remove: Delete account")
    print("  - Capture Window: Select from open windows")
    print("  - Configure ROI: Draw zones on overlay")
    print()
    
    print("=" * 60)
    print("Accounts tab demonstration complete")
    print("=" * 60)
