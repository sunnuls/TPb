"""
HIVE Launcher — Main Entry Point.

Multi-bot poker automation GUI (PyQt6).
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Apply process stealth at startup (hides console, renames process)
try:
    from launcher.stealth_launcher import apply_stealth_at_startup
    apply_stealth_at_startup(index=0)
except Exception:
    pass

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False

# Setup logging before any other import so the log handler is available
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def main() -> int:
    """Application entry point."""
    if not PYQT6_AVAILABLE:
        print("ERROR: PyQt6 is not installed.")
        print("  pip install PyQt6")
        return 1

    logger.info("HIVE Launcher v2.0 starting")

    from launcher.ui.theme import apply_dark_theme
    from launcher.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("HIVE Launcher")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("HIVE")

    # Apply the unified dark theme (palette + QSS)
    apply_dark_theme(app)

    # Create main window first (tray needs real reference)
    window = MainWindow()

    # Try to set up system tray (optional — requires display/QSystemTrayIcon support)
    try:
        from launcher.system_tray import SystemTrayManager

        tray = SystemTrayManager(app=app, main_window=window)

        # Wire tray signals → window actions
        tray.start_all_requested.connect(window._start_all_bots)
        tray.stop_all_requested.connect(window._stop_all_bots)
        tray.emergency_stop_requested.connect(window._on_emergency_stop)
        tray.show_window_requested.connect(window.show)

        # Give window a reference so it can update the tooltip each second
        window._tray_manager = tray
        tray.show()
        logger.info("System tray initialized")
    except Exception as exc:
        logger.debug("System tray not available: %s", exc)
        window._tray_manager = None

    window.show()

    logger.info("Application event loop started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
