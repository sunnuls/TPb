"""
Launcher Application Main Entry Point (Roadmap6).

⚠️ CRITICAL ETHICAL WARNING:
    This launches coordinated bot management system (COLLUSION).
    
    EXTREMELY UNETHICAL and ILLEGAL in real poker.
    Educational research only. NEVER use without explicit consent.

Standalone GUI application for HIVE bot coordination.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False

from launcher.ui.main_window import MainWindow
from launcher.system_tray import SystemTrayManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class LauncherApp:
    """
    Main launcher application.
    
    Coordinates GUI, system tray, and bot management.
    
    ⚠️ EDUCATIONAL NOTE:
        Manages coordinated bot operations for research.
    """
    
    def __init__(self):
        """Initialize launcher application."""
        if not PYQT6_AVAILABLE:
            raise ImportError(
                "PyQt6 not available. Install with: pip install PyQt6"
            )
        
        logger.critical(
            "=" * 60 + "\n"
            "HIVE LAUNCHER STARTING\n"
            "Educational Research Only\n"
            "COLLUSION SYSTEM - ILLEGAL IN REAL POKER\n"
            "=" * 60
        )
        
        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("HIVE Launcher")
        self.app.setOrganizationName("Educational Research")
        
        # Apply dark theme
        self._apply_dark_theme()
        
        # Create main window
        self.main_window = MainWindow()
        
        # Create system tray
        self.system_tray = SystemTrayManager(
            app=self.app,
            main_window=self.main_window
        )
        
        # Connect signals
        self._connect_signals()
        
        # Show components
        self.main_window.show()
        self.system_tray.show()
        
        logger.info("Launcher application initialized")
    
    def _apply_dark_theme(self):
        """Apply dark theme to application."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #444444;
            background-color: #2b2b2b;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px 16px;
            margin: 2px;
            border: 1px solid #444444;
        }
        QTabBar::tab:selected {
            background-color: #0d7377;
            border-bottom: 2px solid #14ffec;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
        }
        QPushButton:pressed {
            background-color: #2c2c2c;
        }
        QLabel {
            color: #ffffff;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #3c3c3c;
        }
        QMenu {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #444444;
        }
        QMenu::item:selected {
            background-color: #0d7377;
        }
        QStatusBar {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        """
        
        self.app.setStyleSheet(dark_stylesheet)
    
    def _connect_signals(self):
        """Connect system tray signals."""
        # Start all bots
        self.system_tray.start_all_requested.connect(
            self._on_start_all_bots
        )
        
        # Stop all bots
        self.system_tray.stop_all_requested.connect(
            self._on_stop_all_bots
        )
        
        logger.debug("Signals connected")
    
    def _on_start_all_bots(self):
        """Handle start all bots request."""
        logger.info("START ALL BOTS requested")
        
        # Will be implemented in Phase 2
        self.system_tray.show_notification(
            "HIVE Launcher",
            "Start all bots - Coming in Phase 2",
            duration=2000
        )
    
    def _on_stop_all_bots(self):
        """Handle stop all bots request."""
        logger.info("STOP ALL BOTS requested")
        
        # Will be implemented in Phase 2
        self.system_tray.show_notification(
            "HIVE Launcher",
            "Stop all bots - Coming in Phase 2",
            duration=2000
        )
    
    def run(self) -> int:
        """
        Run application.
        
        Returns:
            Exit code
        """
        logger.info("Starting application event loop")
        
        return self.app.exec()


def main():
    """Main entry point."""
    try:
        app = LauncherApp()
        return app.run()
    
    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nInstall requirements:")
        print("  pip install -r launcher/requirements.txt")
        return 1
    
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
