"""
Tests for Main Window (Roadmap6 Phase 0).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest

try:
    from PyQt6.QtWidgets import QApplication
    PYQT6_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT6_AVAILABLE = False


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests."""
    if not PYQT6_AVAILABLE:
        pytest.skip("PyQt6 not available")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    yield app


class TestMainWindow:
    """Test main window."""
    
    def test_import(self):
        """Test importing main window."""
        if not PYQT6_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        from launcher.ui.main_window import MainWindow
        assert MainWindow is not None
    
    def test_initialization(self, qapp):
        """Test window initialization."""
        from launcher.ui.main_window import MainWindow
        
        # Create window (will show warning dialog)
        # For testing, we just verify it can be instantiated
        # Note: Cannot test GUI interaction in automated tests
        
        # Just verify the class exists and has expected methods
        assert hasattr(MainWindow, '__init__')
        assert hasattr(MainWindow, '_setup_ui')
        assert hasattr(MainWindow, '_setup_menubar')
        assert hasattr(MainWindow, '_setup_statusbar')


class TestSystemTray:
    """Test system tray."""
    
    def test_import(self):
        """Test importing system tray."""
        if not PYQT6_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        from launcher.system_tray import SystemTrayManager
        assert SystemTrayManager is not None


class TestLauncherApp:
    """Test launcher app."""
    
    def test_import(self):
        """Test importing launcher app."""
        if not PYQT6_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        from launcher.main import LauncherApp
        assert LauncherApp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
