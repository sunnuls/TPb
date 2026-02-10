"""
Window Capturer - Direct window capture using Win32 API.

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Direct window capture (works even if window is partially hidden)
- Proper handling of window positioning
- No interference with other windows
"""

import logging
from typing import Optional, Tuple
import numpy as np

try:
    from PIL import Image
    import cv2
    import win32gui
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    WIN32_AVAILABLE = False

logger = logging.getLogger(__name__)


class WindowCapturer:
    """
    Direct window capture using Win32 API.
    
    Advantages over ImageGrab:
    - Captures window content directly (not screen region)
    - Works even if window is partially hidden
    - No issues with window focus/visibility
    - More reliable for automation
    """
    
    def __init__(self):
        """Initialize capturer."""
        self.available = WIN32_AVAILABLE
        
        if not self.available:
            logger.warning("WindowCapturer not available (requires PIL, cv2, win32gui, win32ui)")
    
    def capture_window_by_hwnd(self, hwnd: int, include_border: bool = True) -> Optional[np.ndarray]:
        """
        Capture window by handle (HWND).
        
        Args:
            hwnd: Window handle
            include_border: Include window border/titlebar (True) or only client area (False)
        
        Returns:
            Captured image as numpy array (BGR) or None
        """
        if not self.available:
            return None
        
        try:
            # Get window title for logging
            try:
                title = win32gui.GetWindowText(hwnd)
                logger.info(f"Capturing window: {title} (HWND: {hwnd})")
            except:
                title = "Unknown"
            
            # Get window dimensions (full window with borders)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            logger.info(f"Window size (with borders): {width}x{height}")
            
            # Check if window is valid
            if width <= 0 or height <= 0:
                logger.error(f"Invalid window size: {width}x{height}")
                return None
            
            # Check if this is a child window
            parent = win32gui.GetParent(hwnd)
            if parent != 0:
                logger.warning(f"This is a child window! Parent HWND: {parent}")
                logger.warning("Consider capturing the parent window instead for full content")
            
            # Method 1: Try PrintWindow first (more reliable for some apps)
            try:
                logger.info("Attempting capture using PrintWindow API...")
                img_bgr = self._capture_using_printwindow(hwnd, width, height)
                if img_bgr is not None:
                    logger.info("✅ PrintWindow capture successful")
                    return img_bgr
                else:
                    logger.warning("PrintWindow returned None, falling back to BitBlt...")
            except Exception as e:
                logger.warning(f"PrintWindow failed: {e}, falling back to BitBlt...")
            
            # Method 2: Fallback to BitBlt
            logger.info("Using BitBlt capture method...")
            
            # Get window DC
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # Create bitmap
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            
            # Copy window content to bitmap
            result = save_dc.BitBlt(
                (0, 0),
                (width, height),
                mfc_dc,
                (0, 0),
                win32con.SRCCOPY
            )
            
            # Convert bitmap to numpy array
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (height, width, 4)  # BGRA
            
            # Remove alpha channel and convert to BGR
            img_bgr = img[:, :, :3]
            
            # Clean up
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            
            logger.info("✅ BitBlt capture successful")
            return img_bgr
        
        except Exception as e:
            logger.error(f"Failed to capture window by HWND: {e}", exc_info=True)
            return None
    
    def _capture_using_printwindow(self, hwnd: int, width: int, height: int) -> Optional[np.ndarray]:
        """
        Capture window using PrintWindow API (more reliable for layered windows).
        
        Args:
            hwnd: Window handle
            width: Window width
            height: Window height
        
        Returns:
            Captured image as numpy array or None
        """
        try:
            import win32api
            
            # Create device context
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # Create bitmap
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            
            # Use PrintWindow instead of BitBlt
            # PW_RENDERFULLCONTENT = 0x00000002 - render full content even if partially hidden
            result = win32gui.SendMessage(
                hwnd,
                win32con.WM_PRINT,
                save_dc.GetSafeHdc(),
                win32con.PRF_CLIENT | win32con.PRF_CHILDREN | win32con.PRF_OWNED
            )
            
            # Alternative: use PrintWindow function
            try:
                import ctypes
                from ctypes import windll
                
                # PW_CLIENTONLY = 0x00000001
                # PW_RENDERFULLCONTENT = 0x00000002
                PW_RENDERFULLCONTENT = 0x00000002
                
                result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
                
                if not result:
                    logger.warning("PrintWindow returned 0 (may have failed)")
            except Exception as e:
                logger.debug(f"PrintWindow ctypes call failed: {e}")
            
            # Convert bitmap to numpy array
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (height, width, 4)  # BGRA
            
            # Remove alpha channel and convert to BGR
            img_bgr = img[:, :, :3]
            
            # Check if image is not blank
            if np.sum(img_bgr) < 1000:  # Almost completely black
                logger.warning("PrintWindow produced blank image")
                # Clean up
                win32gui.DeleteObject(bitmap.GetHandle())
                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwnd_dc)
                return None
            
            # Clean up
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            
            return img_bgr
        
        except Exception as e:
            logger.error(f"PrintWindow capture failed: {e}")
            return None
    
    def capture_window_by_title(self, title: str, partial_match: bool = True) -> Optional[np.ndarray]:
        """
        Capture window by title.
        
        Args:
            title: Window title
            partial_match: Allow partial title match
        
        Returns:
            Captured image as numpy array or None
        """
        # Find window by title
        hwnd = None
        
        def callback(h, extra):
            nonlocal hwnd
            window_title = win32gui.GetWindowText(h)
            
            if partial_match:
                if title.lower() in window_title.lower():
                    hwnd = h
                    return False  # Stop enumeration
            else:
                if window_title == title:
                    hwnd = h
                    return False
            
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except:
            pass
        
        if not hwnd:
            logger.error(f"Window not found: {title}")
            return None
        
        return self.capture_window_by_hwnd(hwnd)
    
    def capture_region_from_window(
        self,
        hwnd: int,
        region: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        """
        Capture specific region from window.
        
        Args:
            hwnd: Window handle
            region: Region (x, y, width, height) relative to window
        
        Returns:
            Captured region as numpy array or None
        """
        # First capture full window
        full_img = self.capture_window_by_hwnd(hwnd)
        
        if full_img is None:
            return None
        
        # Crop region
        x, y, w, h = region
        
        # Validate region
        img_h, img_w = full_img.shape[:2]
        if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
            logger.warning(f"Region {region} is outside window bounds {img_w}x{img_h}")
            # Clip region to window bounds
            x = max(0, x)
            y = max(0, y)
            w = min(w, img_w - x)
            h = min(h, img_h - y)
        
        cropped = full_img[y:y+h, x:x+w]
        
        return cropped
    
    def get_root_window(self, hwnd: int) -> int:
        """
        Get root (top-level) window for a given window handle.
        
        If the window is a child window, returns its top-level parent.
        Otherwise returns the window itself.
        
        Args:
            hwnd: Window handle
        
        Returns:
            Root window handle
        """
        try:
            # Get ancestor window (top-level parent)
            root = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
            
            if root != 0:
                root_title = win32gui.GetWindowText(root)
                orig_title = win32gui.GetWindowText(hwnd)
                
                if root != hwnd:
                    logger.info(f"Found root window: {root_title} (HWND: {root})")
                    logger.info(f"  Original was: {orig_title} (HWND: {hwnd})")
                
                return root
            
            return hwnd
        
        except Exception as e:
            logger.error(f"Failed to get root window: {e}")
            return hwnd
    
    def get_window_info(self, hwnd: int) -> dict:
        """
        Get window information.
        
        Args:
            hwnd: Window handle
        
        Returns:
            Window info dict
        """
        try:
            title = win32gui.GetWindowText(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            
            # Check if it's a child window
            parent = win32gui.GetParent(hwnd)
            root = self.get_root_window(hwnd)
            
            return {
                'hwnd': hwnd,
                'title': title,
                'position': (left, top, right - left, bottom - top),
                'visible': win32gui.IsWindowVisible(hwnd),
                'minimized': win32gui.IsIconic(hwnd),
                'is_child': parent != 0,
                'parent_hwnd': parent if parent != 0 else None,
                'root_hwnd': root if root != hwnd else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get window info: {e}")
            return {}


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Window Capturer - Educational Research")
    print("=" * 60)
    print()
    print("Features:")
    print("  - Direct window capture using Win32 API")
    print("  - Captures window content directly (not screen region)")
    print("  - Works even if window is partially hidden")
    print("  - No interference with other windows")
    print()
    
    capturer = WindowCapturer()
    
    if capturer.available:
        print("✅ WindowCapturer available")
        print()
        print("Example usage:")
        print("  capturer.capture_window_by_hwnd(hwnd)")
        print("  capturer.capture_window_by_title('Notepad')")
        print("  capturer.capture_region_from_window(hwnd, (0, 0, 100, 100))")
    else:
        print("❌ WindowCapturer not available")
        print("Install required packages:")
        print("  pip install pillow opencv-python pywin32")
    
    print()
    print("⚠️ EDUCATIONAL RESEARCH ONLY")
