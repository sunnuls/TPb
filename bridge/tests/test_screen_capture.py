"""
Unit tests for screen capture module (Roadmap3 Phase 1).

Tests screen capture functionality in DRY-RUN mode.
"""

import pytest
import numpy as np

from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
from bridge.screen_capture import ScreenCapture, WindowInfo


@pytest.fixture(autouse=True)
def setup_safety():
    """Setup safety framework in dry-run mode for tests."""
    SafetyFramework._instance = None  # Reset singleton
    SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN, enable_kill_switch=False))
    yield
    SafetyFramework._instance = None  # Cleanup


class TestWindowInfo:
    """Test WindowInfo dataclass."""
    
    def test_window_info_creation(self):
        """Can create WindowInfo."""
        window = WindowInfo(
            hwnd=12345,
            title="Test Window",
            process_name="test.exe",
            x=100,
            y=100,
            width=1920,
            height=1080,
            is_visible=True
        )
        
        assert window.hwnd == 12345
        assert window.title == "Test Window"
        assert window.width == 1920
        assert window.height == 1080


class TestScreenCaptureInit:
    """Test ScreenCapture initialization."""
    
    def test_initialization_default(self):
        """Can initialize with defaults."""
        capture = ScreenCapture()
        
        assert capture.window_title_pattern is None
        assert capture.process_name is None
        assert capture.save_screenshots is False
        assert capture.capture_count == 0
    
    def test_initialization_with_params(self):
        """Can initialize with parameters."""
        capture = ScreenCapture(
            window_title_pattern="PokerStars.*",
            process_name="PokerStars.exe",
            save_screenshots=True
        )
        
        assert capture.window_title_pattern == "PokerStars.*"
        assert capture.process_name == "PokerStars.exe"
        assert capture.save_screenshots is True


class TestFindWindow:
    """Test window finding."""
    
    def test_find_window_dry_run(self):
        """find_window returns simulated window in dry-run."""
        capture = ScreenCapture(window_title_pattern="PokerStars.*")
        
        window = capture.find_window()
        
        assert window is not None
        assert isinstance(window, WindowInfo)
        assert window.title != ""
        assert window.width > 0
        assert window.height > 0
    
    def test_find_window_stores_current(self):
        """find_window stores result in current_window."""
        capture = ScreenCapture()
        
        window = capture.find_window()
        
        assert capture.current_window is window


class TestCapture:
    """Test screenshot capture."""
    
    def test_capture_without_window_fails(self):
        """capture fails if no window selected."""
        capture = ScreenCapture()
        
        screenshot = capture.capture()
        
        assert screenshot is None
    
    def test_capture_dry_run_returns_array(self):
        """capture returns numpy array in dry-run."""
        capture = ScreenCapture()
        capture.find_window()  # Find window first
        
        screenshot = capture.capture()
        
        assert screenshot is not None
        assert isinstance(screenshot, np.ndarray)
        assert len(screenshot.shape) == 3  # Height, Width, Channels
        assert screenshot.shape[2] == 3  # RGB
    
    def test_capture_increments_count(self):
        """capture increments capture count."""
        capture = ScreenCapture()
        capture.find_window()
        
        initial_count = capture.capture_count
        capture.capture()
        
        assert capture.capture_count == initial_count + 1
    
    def test_capture_with_region(self):
        """capture can use custom region."""
        capture = ScreenCapture()
        capture.find_window()
        
        region = (100, 100, 200, 150)
        screenshot = capture.capture(region=region)
        
        assert screenshot is not None
        assert screenshot.shape[0] == 150  # Height
        assert screenshot.shape[1] == 200  # Width
    
    def test_capture_updates_timestamp(self):
        """capture updates last capture time."""
        capture = ScreenCapture()
        capture.find_window()
        
        initial_time = capture.last_capture_time
        capture.capture()
        
        assert capture.last_capture_time > initial_time


class TestCaptureLoop:
    """Test capture loop for stability testing."""
    
    def test_capture_loop_default(self):
        """capture_loop captures multiple screenshots."""
        capture = ScreenCapture()
        capture.find_window()
        
        screenshots = capture.capture_loop(interval_seconds=0.1, max_captures=3)
        
        assert len(screenshots) == 3
        assert all(isinstance(s, np.ndarray) for s in screenshots)
    
    def test_capture_loop_respects_max_captures(self):
        """capture_loop respects max_captures limit."""
        capture = ScreenCapture()
        capture.find_window()
        
        max_count = 5
        screenshots = capture.capture_loop(interval_seconds=0.05, max_captures=max_count)
        
        assert len(screenshots) == max_count
    
    def test_capture_loop_updates_count(self):
        """capture_loop updates total capture count."""
        capture = ScreenCapture()
        capture.find_window()
        
        initial_count = capture.capture_count
        num_captures = 4
        capture.capture_loop(interval_seconds=0.05, max_captures=num_captures)
        
        assert capture.capture_count == initial_count + num_captures


class TestStatistics:
    """Test statistics retrieval."""
    
    def test_get_statistics_initial(self):
        """get_statistics returns initial state."""
        capture = ScreenCapture()
        
        stats = capture.get_statistics()
        
        assert 'total_captures' in stats
        assert 'window_found' in stats
        assert 'dry_run' in stats
        assert stats['total_captures'] == 0
        assert stats['window_found'] is False
        assert stats['dry_run'] is True
    
    def test_get_statistics_after_capture(self):
        """get_statistics reflects capture activity."""
        capture = ScreenCapture()
        capture.find_window()
        capture.capture()
        
        stats = capture.get_statistics()
        
        assert stats['total_captures'] == 1
        assert stats['window_found'] is True
        assert stats['window_title'] is not None


class TestDryRunMode:
    """Test dry-run mode behavior."""
    
    def test_dry_run_no_real_capture(self):
        """Dry-run mode doesn't perform real captures."""
        capture = ScreenCapture()
        capture.find_window()
        screenshot = capture.capture()
        
        # Dry-run screenshot has pattern (lines)
        assert screenshot is not None
        # Check for pattern (should have some non-zero pixels)
        assert np.any(screenshot > 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
