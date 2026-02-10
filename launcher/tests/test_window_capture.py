"""
Tests for WindowCapture - Phase 1.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
from launcher.window_capture import WindowCapture


class TestWindowCapture:
    """Tests for WindowCapture."""
    
    def test_initialization(self):
        """Test window capture initialization."""
        capture = WindowCapture()
        
        # Should initialize without error
        assert capture is not None
    
    def test_availability(self):
        """Test checking availability."""
        capture = WindowCapture()
        
        # Available may be True or False depending on environment
        assert isinstance(capture.available, bool)
    
    @pytest.mark.skipif(
        not WindowCapture().available,
        reason="Window capture not available (requires pywin32)"
    )
    def test_list_windows(self):
        """Test listing windows."""
        capture = WindowCapture()
        
        # List windows
        windows = capture.list_windows()
        
        # Should return a list (may be empty in headless environment)
        assert isinstance(windows, list)
        
        # If windows found, check structure
        if windows:
            window = windows[0]
            assert 'window_id' in window
            assert 'title' in window
            assert 'position' in window
    
    @pytest.mark.skipif(
        not WindowCapture().available,
        reason="Window capture not available"
    )
    def test_list_windows_with_filters(self):
        """Test listing windows with filters."""
        capture = WindowCapture()
        
        # List with filters
        windows = capture.list_windows(
            filter_visible=True,
            min_width=200,
            min_height=200
        )
        
        assert isinstance(windows, list)
        
        # Verify all windows meet size requirements
        for window in windows:
            pos = window.get('position')
            if pos:
                x, y, width, height = pos
                assert width >= 200
                assert height >= 200
    
    def test_list_windows_unavailable(self):
        """Test listing windows when unavailable."""
        capture = WindowCapture()
        
        if not capture.available:
            windows = capture.list_windows()
            assert windows == []
    
    def test_get_window_by_id_unavailable(self):
        """Test getting window by ID when unavailable."""
        capture = WindowCapture()
        
        if not capture.available:
            window = capture.get_window_by_id("12345")
            assert window is None
    
    def test_focus_window_unavailable(self):
        """Test focusing window when unavailable."""
        capture = WindowCapture()
        
        if not capture.available:
            result = capture.focus_window("12345")
            assert result is False


# Demo test (always runs)
def test_window_capture_demo():
    """Demonstrate window capture functionality."""
    capture = WindowCapture()
    
    print("\n" + "=" * 60)
    print("Window Capture Demo")
    print("=" * 60)
    print(f"Available: {capture.available}")
    
    if capture.available:
        print("\nTesting window enumeration...")
        windows = capture.list_windows()
        print(f"Found {len(windows)} windows")
        
        if windows:
            print("\nFirst few windows:")
            for i, window in enumerate(windows[:3], 1):
                print(f"  {i}. {window['title'][:40]}")
    else:
        print("\nWindow capture not available")
        print("Install pywin32: pip install pywin32")
    
    print("=" * 60)
    
    # Always pass
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
