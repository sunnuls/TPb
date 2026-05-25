"""
System Tray Integration - Launcher Application (Roadmap6 Phase 0).

⚠️ EDUCATIONAL RESEARCH ONLY - System tray and hotkeys.

Features:
- System tray icon with menu
- Global hotkeys (Ctrl+Alt+S = start/stop all)
- Quick access to main window
"""

import logging
import sys

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QAction, QIcon
    from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except (ImportError, ModuleNotFoundError, SyntaxError) as e:
    # keyboard library can fail on Windows with SyntaxError (null bytes)
    KEYBOARD_AVAILABLE = False
    if isinstance(e, SyntaxError):
        logging.getLogger(__name__).warning(
            "keyboard module has syntax errors - hotkeys disabled. "
            "This is a known issue on some Windows systems."
        )

logger = logging.getLogger(__name__)


class SystemTrayManager(QObject):
    """
    System tray manager.

    Features:
    - Tray icon with context menu (Show, Start All, Stop All, Emergency Stop, Exit)
    - Double-click to show/raise main window
    - update_status() for dynamic tooltip
    - Global hotkeys (optional, requires 'keyboard' package)

    ⚠️ EDUCATIONAL NOTE:
        System tray for bot management interface.
    """

    start_all_requested   = pyqtSignal()
    stop_all_requested    = pyqtSignal()
    emergency_stop_requested = pyqtSignal()
    show_window_requested = pyqtSignal()

    def __init__(self, app: QApplication, main_window):
        super().__init__()

        self.app = app
        self.main_window = main_window

        self.tray_icon = QSystemTrayIcon(self.app)

        self._setup_tray_icon()
        self._setup_tray_menu()
        self._setup_hotkeys()

        logger.info("System tray manager initialized")
    
    def _setup_tray_icon(self):
        """Setup tray icon."""
        # Use default icon (in production, would use custom icon)
        self.tray_icon.setIcon(self.app.style().standardIcon(
            self.app.style().StandardPixmap.SP_ComputerIcon
        ))
        
        self.tray_icon.setToolTip("HIVE Launcher (Educational Research)")
        
        # Connect activation
        self.tray_icon.activated.connect(self._on_tray_activated)
    
    def _setup_tray_menu(self):
        """Setup tray context menu."""
        menu = QMenu()

        show_action = QAction("Show Window", self.app)
        show_action.triggered.connect(self._on_show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        start_action = QAction("▶  Start All Bots", self.app)
        start_action.triggered.connect(self._on_start_all)
        menu.addAction(start_action)

        stop_action = QAction("■  Stop All Bots", self.app)
        stop_action.triggered.connect(self._on_stop_all)
        menu.addAction(stop_action)

        menu.addSeparator()

        emergency_action = QAction("🚨  EMERGENCY STOP", self.app)
        emergency_action.triggered.connect(self._on_emergency_stop)
        # Make it visually stand out via font colour
        try:
            from PyQt6.QtGui import QFont
            f = emergency_action.font()
            f.setBold(True)
            emergency_action.setFont(f)
        except Exception:
            pass
        menu.addAction(emergency_action)

        menu.addSeparator()

        exit_action = QAction("Exit", self.app)
        exit_action.triggered.connect(self._on_exit)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
    
    def _setup_hotkeys(self):
        """Setup global hotkeys."""
        if not KEYBOARD_AVAILABLE:
            logger.warning(
                "keyboard module not available - global hotkeys disabled. "
                "Use menu or buttons instead."
            )
            return
        
        try:
            # Register Ctrl+Alt+S for start/stop
            keyboard.add_hotkey(
                'ctrl+alt+s',
                self._on_hotkey_start_stop,
                suppress=True
            )
            
            logger.info("Global hotkey registered: Ctrl+Alt+S (start/stop all)")
            
        except Exception as e:
            logger.warning(f"Failed to register hotkeys: {e}. Hotkeys disabled.")
    
    def show(self):
        """Show tray icon."""
        self.tray_icon.show()
    
    def hide(self):
        """Hide tray icon."""
        self.tray_icon.hide()
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_show_window()
    
    def _on_show_window(self):
        """Show main window."""
        self.main_window.show()
        self.main_window.activateWindow()
        self.show_window_requested.emit()
    
    def _on_start_all(self):
        """Start all bots."""
        logger.info("Start all bots requested (via tray)")
        self.start_all_requested.emit()
    
    def _on_stop_all(self):
        """Stop all bots."""
        logger.info("Stop all bots requested (via tray)")
        self.stop_all_requested.emit()

    def _on_emergency_stop(self):
        """Emergency stop — confirm then emit."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.critical(
            self.main_window,
            "EMERGENCY STOP",
            "Immediately stop ALL bots?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            logger.critical("EMERGENCY STOP from system tray")
            self.emergency_stop_requested.emit()

    def update_status(
        self,
        active_bots: int = 0,
        total_bots: int = 0,
        hands: int = 0,
        hive_sessions: int = 0,
    ) -> None:
        """Update the tray icon tooltip with live stats."""
        lines = [
            "HIVE Launcher",
            f"  Bots: {active_bots} active / {total_bots} total",
            f"  Hands played: {hands:,}",
        ]
        if hive_sessions > 0:
            lines.append(f"  HIVE sessions: {hive_sessions}  ⚠ COLLUSION ACTIVE")
        self.tray_icon.setToolTip("\n".join(lines))

    def _on_hotkey_start_stop(self):
        """Handle hotkey for start/stop toggle."""
        logger.info("Hotkey triggered: Ctrl+Alt+S")
        # Will be implemented in Phase 2 (toggle based on current state)
        self.start_all_requested.emit()
    
    def _on_exit(self):
        """Exit application."""
        logger.info("Exit requested (via tray)")
        QApplication.quit()
    
    def show_notification(self, title: str, message: str, duration: int = 3000):
        """
        Show system notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Duration in milliseconds
        """
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            duration
        )


# Educational example
if __name__ == "__main__":
    if not PYQT6_AVAILABLE:
        print("ERROR: PyQt6 not available")
        print("Install with: pip install PyQt6")
        sys.exit(1)
    
    print("=" * 60)
    print("System Tray Manager - Educational Research")
    print("=" * 60)
    print()
    print("WARNING: Bot management interface for research only.")
    print()
    
    # Create minimal app for testing
    from PyQt6.QtWidgets import QMainWindow
    
    app = QApplication(sys.argv)
    
    class DummyWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Dummy Window")
    
    window = DummyWindow()
    
    tray = SystemTrayManager(app, window)
    tray.show()
    
    print("System tray shown")
    print("Global hotkey: Ctrl+Alt+S (start/stop)")
    print()
    print("Right-click tray icon for menu")
    print("Double-click to show window")
    print()
    
    # Note: In test mode, won't actually run event loop
    # In production: app.exec()
    
    print("=" * 60)
    print("System tray manager initialized")
    print("=" * 60)
