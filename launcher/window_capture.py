"""
Window Capture Utilities - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- List all open windows
- Capture window by selection
- Window position tracking
"""

import logging
import sys
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Platform-specific window enumeration
if sys.platform == 'win32':
    try:
        import win32gui
        import win32process
        WIN32_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        WIN32_AVAILABLE = False
        logger.warning("pywin32 not available - install with: pip install pywin32")
else:
    WIN32_AVAILABLE = False


class WindowCapture:
    """
    Window capture utility.
    
    Features:
    - Enumerate windows
    - Get window information
    - Track window position
    
    ⚠️ EDUCATIONAL NOTE:
        Captures poker client windows for bot operation.
    """
    
    def __init__(self):
        """Initialize window capture."""
        self.available = WIN32_AVAILABLE
        
        if not self.available:
            logger.warning("Window capture not available (requires pywin32 on Windows)")
    
    def list_windows(
        self,
        filter_visible: bool = True,
        min_width: int = 50,
        min_height: int = 50
    ) -> List[dict]:
        """
        List all open windows.
        
        Args:
            filter_visible: Only show visible windows
            min_width: Minimum window width
            min_height: Minimum window height
        
        Returns:
            List of window info dicts
        """
        if not self.available:
            logger.error("Window enumeration not available")
            return []
        
        windows = []
        
        def enum_callback(hwnd, results):
            """Callback for EnumWindows."""
            # Check if window is visible (if filter enabled)
            if filter_visible and not win32gui.IsWindowVisible(hwnd):
                return
            
            # Get window title
            title = win32gui.GetWindowText(hwnd)
            
            # Skip windows without title (but log them for debugging)
            if not title or len(title.strip()) == 0:
                return
            
            # Get window rect
            try:
                rect = win32gui.GetWindowRect(hwnd)
                x, y, right, bottom = rect
                width = right - x
                height = bottom - y
                
                # Filter by size (allow smaller windows now)
                if width < min_width or height < min_height:
                    return
                
                # Get process name
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    
                    # Try to get actual process name
                    try:
                        import psutil
                        process = psutil.Process(pid)
                        process_name = process.name()
                    except:
                        process_name = f"pid_{pid}"
                except:
                    process_name = "unknown"
                
                results.append({
                    'window_id': str(hwnd),
                    'hwnd': hwnd,  # Store actual HWND for direct capture
                    'title': title,
                    'position': (x, y, width, height),
                    'process_name': process_name
                })
            
            except Exception as e:
                logger.debug(f"Error getting window info for {hwnd}: {e}")
        
        try:
            win32gui.EnumWindows(enum_callback, windows)
            logger.info(f"Found {len(windows)} windows")
        except Exception as e:
            logger.error(f"Failed to enumerate windows: {e}")
        
        return windows
    
    def get_window_by_id(self, window_id: str) -> Optional[dict]:
        """
        Get window information by ID.
        
        Args:
            window_id: Window handle
        
        Returns:
            Window info dict if found
        """
        if not self.available:
            return None
        
        try:
            hwnd = int(window_id)
            
            if not win32gui.IsWindow(hwnd):
                return None
            
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            
            return {
                'window_id': window_id,
                'title': title,
                'position': (x, y, right - x, bottom - y)
            }
        
        except Exception as e:
            logger.error(f"Failed to get window info: {e}")
            return None
    
    def focus_window(self, window_id: str) -> bool:
        """
        Focus window.
        
        Args:
            window_id: Window handle
        
        Returns:
            True if successful
        """
        if not self.available:
            return False
        
        try:
            hwnd = int(window_id)
            win32gui.SetForegroundWindow(hwnd)
            return True
        
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Window Capture - Educational Research")
    print("=" * 60)
    print()
    
    capture = WindowCapture()
    
    print(f"Window capture available: {capture.available}")
    print()
    
    if capture.available:
        print("Listing windows...")
        windows = capture.list_windows()
        
        print(f"Found {len(windows)} windows:")
        for i, window in enumerate(windows[:10], 1):
            print(f"  {i}. {window['title'][:50]}")
        
        if len(windows) > 10:
            print(f"  ... and {len(windows) - 10} more")
        print()
    else:
        print("Window enumeration not available")
        print("Install pywin32: pip install pywin32")
        print()
    
    print("=" * 60)
    print("Window capture demonstration complete")
    print("=" * 60)
