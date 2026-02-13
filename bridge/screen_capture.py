"""
Screen Capture Module for HCI Research (Roadmap3 Phase 1 + bot_fixes Phase 3).

EDUCATIONAL USE ONLY: This module captures screenshots of external desktop
applications for Human-Computer Interaction research purposes.

DRY-RUN MODE: All capture operations are simulated by default.
Real window capture requires --unsafe flag.

Phase 3 enhancements (bot_fixes.md):
  - Full Win32 capture via PrintWindow / BitBlt (not just mss)
  - Real ``find_window_win32`` via ``AutoWindowFinder``
  - ``capture_client_area``: crops title-bar / borders automatically
  - ``capture_full_window``: full window including decorations
  - ``auto_crop_borders``: removes black / empty edges
  - ``capture_by_binding``: integrates with ``BotAccountBinder``

WARNING: This is a research prototype. Real-world use is PROHIBITED.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

# Import safety framework
from bridge.safety import get_safety, require_unsafe

logger = logging.getLogger(__name__)

# Try to import screen capture libraries (optional for dry-run)
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    MSS_AVAILABLE = False
    # Don't log here - will log in _check_dependencies

try:
    import win32gui
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except (ImportError, SyntaxError, AttributeError) as e:
    WIN32_AVAILABLE = False
    # Don't log here - will log in _check_dependencies

try:
    import cv2
    CV2_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CV2_AVAILABLE = False

# Phase 3: integrate with AutoWindowFinder
try:
    from launcher.auto_window_finder import AutoWindowFinder, WindowMatch
    FINDER_AVAILABLE = True
except Exception:
    FINDER_AVAILABLE = False
    AutoWindowFinder = None  # type: ignore[misc,assignment]

# Phase 3: integrate with BotAccountBinder
try:
    from launcher.bot_account_binder import BotAccountBinder, Binding
    BINDER_AVAILABLE = True
except Exception:
    BINDER_AVAILABLE = False


@dataclass
class WindowInfo:
    """
    Information about a captured window.
    
    Attributes:
        hwnd: Window handle (Windows specific)
        title: Window title
        process_name: Process name
        x: Window X position
        y: Window Y position
        width: Window width
        height: Window height
        is_visible: Whether window is visible
    """
    hwnd: Optional[int] = None
    title: str = ""
    process_name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_visible: bool = False


class ScreenCapture:
    """
    Screen capture system for HCI research.
    
    Features:
    - Find window by title pattern or process name
    - Capture specific window region
    - Save screenshots for analysis
    - DRY-RUN mode: simulates capture without real operations
    
    EDUCATIONAL NOTE:
        This class is designed for studying external application interfaces.
        All operations are DRY-RUN by default. Real capture requires --unsafe.
    """
    
    def __init__(
        self,
        window_title_pattern: Optional[str] = None,
        process_name: Optional[str] = None,
        save_screenshots: bool = False,
        screenshot_dir: str = "bridge/debug_screenshots"
    ):
        """
        Initialize screen capture.
        
        Args:
            window_title_pattern: Regex pattern for window title
            process_name: Process name (e.g., "PokerStars.exe")
            save_screenshots: Save debug screenshots
            screenshot_dir: Directory for screenshots
        """
        self.window_title_pattern = window_title_pattern
        self.process_name = process_name
        self.save_screenshots = save_screenshots
        self.screenshot_dir = Path(screenshot_dir)
        
        # Current window info
        self.current_window: Optional[WindowInfo] = None
        
        # Capture statistics
        self.capture_count = 0
        self.last_capture_time = 0.0
        
        # Create screenshot directory
        if save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Screenshot directory: {self.screenshot_dir}")
        
        # Check library availability
        self._check_dependencies()
        
        logger.info(f"ScreenCapture initialized (DRY-RUN: {get_safety().is_dry_run()})")
    
    def _check_dependencies(self) -> None:
        """Check if required libraries are available."""
        if not MSS_AVAILABLE:
            logger.warning("mss not available - install with: pip install mss")
        
        if not WIN32_AVAILABLE:
            logger.warning("pywin32 not available - install with: pip install pywin32")
        
        if get_safety().is_dry_run():
            logger.info("DRY-RUN mode: Screen capture will be simulated")
    
    def find_window(self) -> Optional[WindowInfo]:
        """
        Find window by title pattern or process name.
        
        Returns:
            WindowInfo if found, None otherwise
            
        EDUCATIONAL NOTE:
            In DRY-RUN mode, returns simulated window info.
        """
        safety = get_safety()
        
        # DRY-RUN: Return simulated window
        if safety.is_dry_run():
            logger.info(f"[DRY-RUN] Simulating window search: {self.window_title_pattern}")
            
            # Simulate found window
            self.current_window = WindowInfo(
                hwnd=12345,  # Fake handle
                title="PokerStars - Example Table",
                process_name="PokerStars.exe",
                x=100,
                y=100,
                width=1920,
                height=1080,
                is_visible=True
            )
            
            logger.info(f"[DRY-RUN] Simulated window found: {self.current_window.title}")
            return self.current_window
        
        # Real window search (requires --unsafe)
        try:
            require_unsafe("find_window")
        except PermissionError:
            logger.error("Window search blocked in safe mode")
            return None
        
        # Real implementation (Windows)
        if WIN32_AVAILABLE:
            return self._find_window_win32()
        else:
            logger.error("Window search not available - missing dependencies")
            return None
    
    def _find_window_win32(self) -> Optional[WindowInfo]:
        """Find window using Win32 API via AutoWindowFinder (Phase 3)."""
        if not FINDER_AVAILABLE:
            logger.warning("AutoWindowFinder not available")
            return None

        finder = AutoWindowFinder()
        if not finder.available:
            logger.warning("Win32 window API not available")
            return None

        pattern = self.window_title_pattern or ""
        match = finder.find(
            pattern,
            by_process=self.process_name or "",
        )

        if match is None:
            logger.warning("No matching window found for pattern=%r process=%r",
                           pattern, self.process_name)
            return None

        self.current_window = WindowInfo(
            hwnd=match.hwnd,
            title=match.title,
            process_name=match.process_name,
            x=match.full_rect.x,
            y=match.full_rect.y,
            width=match.full_rect.w,
            height=match.full_rect.h,
            is_visible=match.visible,
        )
        self._last_match = match  # keep for client_rect
        logger.info("Found window: %r (hwnd=%d, %dx%d)",
                     match.title, match.hwnd, match.full_rect.w, match.full_rect.h)
        return self.current_window
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        Capture window screenshot.
        
        Args:
            region: Optional region (x, y, width, height) within window
            
        Returns:
            Screenshot as numpy array (RGB) or None if failed
            
        EDUCATIONAL NOTE:
            In DRY-RUN mode, returns simulated screenshot (random noise).
        """
        safety = get_safety()
        
        # Check if window is available
        if self.current_window is None:
            logger.warning("No window selected - call find_window() first")
            return None
        
        # DRY-RUN: Return simulated screenshot
        if safety.is_dry_run():
            logger.debug(f"[DRY-RUN] Simulating screenshot capture")
            
            # Simulate screenshot (random noise for testing)
            if region:
                width, height = region[2], region[3]
            else:
                width = self.current_window.width
                height = self.current_window.height
            
            # Generate fake screenshot (black image for dry-run)
            screenshot = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Add some pattern to distinguish from real screenshots
            screenshot[::10, :] = 50  # Horizontal lines
            screenshot[:, ::10] = 50  # Vertical lines
            
            self.capture_count += 1
            self.last_capture_time = time.time()
            
            # Save if requested
            if self.save_screenshots:
                self._save_screenshot(screenshot, prefix="dryrun")
            
            return screenshot
        
        # Real capture (requires --unsafe)
        try:
            require_unsafe("capture_screenshot")
        except PermissionError:
            logger.error("Screenshot capture blocked in safe mode")
            return None
        
        # Real implementation
        if MSS_AVAILABLE:
            return self._capture_mss(region)
        else:
            logger.error("Screenshot capture not available - missing mss library")
            return None
    
    def _capture_mss(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """Capture using mss library."""
        try:
            with mss.mss() as sct:
                # Define monitor region
                if region:
                    x, y, width, height = region
                    monitor = {
                        "top": self.current_window.y + y,
                        "left": self.current_window.x + x,
                        "width": width,
                        "height": height
                    }
                else:
                    monitor = {
                        "top": self.current_window.y,
                        "left": self.current_window.x,
                        "width": self.current_window.width,
                        "height": self.current_window.height
                    }
                
                # Capture
                screenshot = sct.grab(monitor)
                
                # Convert to numpy array (RGB)
                img = np.array(screenshot)
                img = img[:, :, :3]  # Remove alpha channel
                img = img[:, :, ::-1]  # BGR to RGB
                
                self.capture_count += 1
                self.last_capture_time = time.time()
                
                # Save if requested
                if self.save_screenshots:
                    self._save_screenshot(img)
                
                return img
        
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def _save_screenshot(self, screenshot: np.ndarray, prefix: str = "capture") -> None:
        """
        Save screenshot to file.
        
        Args:
            screenshot: Screenshot array
            prefix: Filename prefix
        """
        try:
            # Try to import PIL for saving
            try:
                from PIL import Image
            except ImportError:
                logger.warning("PIL not available - cannot save screenshot")
                return
            
            # Generate filename
            timestamp = int(time.time() * 1000)
            filename = self.screenshot_dir / f"{prefix}_{timestamp}.png"
            
            # Convert and save
            img = Image.fromarray(screenshot)
            img.save(filename)
            
            logger.debug(f"Screenshot saved: {filename}")
        
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
    
    def capture_loop(
        self,
        interval_seconds: float = 2.0,
        max_captures: int = 10
    ) -> list[np.ndarray]:
        """
        Capture screenshots in a loop for stability testing.
        
        Args:
            interval_seconds: Time between captures
            max_captures: Maximum number of captures
            
        Returns:
            List of captured screenshots
            
        EDUCATIONAL NOTE:
            Phase 1 test: Capture every 2 seconds to verify stability.
        """
        logger.info(f"Starting capture loop: {max_captures} captures @ {interval_seconds}s interval")
        
        captures = []
        
        for i in range(max_captures):
            logger.info(f"Capture {i + 1}/{max_captures}")
            
            # Capture
            screenshot = self.capture()
            
            if screenshot is not None:
                captures.append(screenshot)
            else:
                logger.warning(f"Capture {i + 1} failed")
            
            # Wait (except on last iteration)
            if i < max_captures - 1:
                time.sleep(interval_seconds)
        
        logger.info(f"Capture loop complete: {len(captures)}/{max_captures} successful")
        
        return captures
    
    def get_statistics(self) -> dict:
        """
        Get capture statistics.
        
        Returns:
            Dict with statistics
        """
        return {
            'total_captures': self.capture_count,
            'last_capture_time': self.last_capture_time,
            'window_found': self.current_window is not None,
            'window_title': self.current_window.title if self.current_window else None,
            'dry_run': get_safety().is_dry_run()
        }

    # ------------------------------------------------------------------
    # Phase 3 — Full capture + crop (bot_fixes.md)
    # ------------------------------------------------------------------

    def capture_full_window(self, hwnd: Optional[int] = None) -> Optional[np.ndarray]:
        """Capture the full window including title-bar and borders.

        Uses Win32 PrintWindow/BitBlt for pixel-perfect capture that works
        even when the window is partially occluded.

        Args:
            hwnd: Window handle.  If ``None``, uses ``current_window.hwnd``.

        Returns:
            BGR numpy array or ``None``.
        """
        hwnd = hwnd or (self.current_window.hwnd if self.current_window else None)
        if not hwnd:
            logger.warning("capture_full_window: no hwnd")
            return None

        if not WIN32_AVAILABLE:
            logger.warning("capture_full_window: Win32 not available")
            return None

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            img = self._win32_grab(hwnd, width, height)
            if img is not None:
                self.capture_count += 1
                self.last_capture_time = time.time()
            return img

        except Exception as exc:
            logger.error("capture_full_window failed: %s", exc)
            return None

    def capture_client_area(self, hwnd: Optional[int] = None) -> Optional[np.ndarray]:
        """Capture only the client area (content without borders).

        Automatically computes the title-bar / border offsets and crops
        the capture to the client rectangle — this is the "auto-crop by
        edges" feature requested in bot_fixes Phase 3.

        Args:
            hwnd: Window handle.  If ``None``, uses ``current_window.hwnd``.

        Returns:
            BGR numpy array of the client area, or ``None``.
        """
        hwnd = hwnd or (self.current_window.hwnd if self.current_window else None)
        if not hwnd:
            logger.warning("capture_client_area: no hwnd")
            return None

        if not WIN32_AVAILABLE:
            logger.warning("capture_client_area: Win32 not available")
            return None

        try:
            # Full window rect
            wl, wt, wr, wb = win32gui.GetWindowRect(hwnd)
            fw = wr - wl
            fh = wb - wt

            # Client rect in screen coords
            cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
            cw = cr - cl
            ch = cb - ct
            sx, sy = win32gui.ClientToScreen(hwnd, (0, 0))

            # Offsets relative to the full-window capture
            off_x = sx - wl
            off_y = sy - wt

            full = self._win32_grab(hwnd, fw, fh)
            if full is None:
                return None

            # Crop to client area
            cropped = full[off_y:off_y + ch, off_x:off_x + cw].copy()
            self.capture_count += 1
            self.last_capture_time = time.time()

            if self.save_screenshots:
                self._save_screenshot(cropped, prefix="client")

            return cropped

        except Exception as exc:
            logger.error("capture_client_area failed: %s", exc)
            return None

    def capture_by_binding(self, binding: "Binding") -> Optional[np.ndarray]:
        """Capture client area using a ``BotAccountBinder.Binding``.

        Convenience wrapper that extracts hwnd from the binding.

        Args:
            binding: A ``Binding`` instance (from ``bot_account_binder``).

        Returns:
            BGR numpy array of the client area, or ``None``.
        """
        if not binding or not binding.hwnd:
            logger.warning("capture_by_binding: invalid binding")
            return None
        return self.capture_client_area(hwnd=binding.hwnd)

    @staticmethod
    def auto_crop_borders(
        image: np.ndarray,
        threshold: int = 10,
        min_content_frac: float = 0.02,
    ) -> np.ndarray:
        """Remove black / near-black borders from an image.

        Scans rows and columns from the edges inward, trimming any that
        are below *threshold* brightness.  Stops when a row/column has
        at least *min_content_frac* bright pixels.

        Args:
            image:             BGR or grayscale numpy array.
            threshold:         Pixel brightness below this is "empty".
            min_content_frac:  Fraction of pixels that must be bright to
                               consider a row/column as "content".

        Returns:
            Cropped image (copy).  If the image is fully black, returns
            the original unchanged.
        """
        if image is None or image.size == 0:
            return image

        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = np.max(image, axis=2)  # max channel
        else:
            gray = image

        h, w = gray.shape
        min_pixels = max(1, int(w * min_content_frac))
        min_pixels_v = max(1, int(h * min_content_frac))

        # Find top edge
        top = 0
        for r in range(h):
            if np.count_nonzero(gray[r, :] > threshold) >= min_pixels:
                top = r
                break

        # Find bottom edge
        bottom = h
        for r in range(h - 1, top, -1):
            if np.count_nonzero(gray[r, :] > threshold) >= min_pixels:
                bottom = r + 1
                break

        # Find left edge
        left = 0
        for c in range(w):
            if np.count_nonzero(gray[top:bottom, c] > threshold) >= min_pixels_v:
                left = c
                break

        # Find right edge
        right = w
        for c in range(w - 1, left, -1):
            if np.count_nonzero(gray[top:bottom, c] > threshold) >= min_pixels_v:
                right = c + 1
                break

        # Sanity check
        if right - left < 10 or bottom - top < 10:
            return image

        return image[top:bottom, left:right].copy()

    # -- Edge-detection crop (auto_find_window.md Phase 2) -----------------

    @staticmethod
    def edge_detect_crop(
        image: np.ndarray,
        *,
        method: str = "canny",
        canny_low: int = 50,
        canny_high: int = 150,
        sobel_ksize: int = 3,
        margin: int = 2,
        min_edge_density: float = 0.01,
    ) -> np.ndarray:
        """Crop an image to its content boundary using edge detection.

        Unlike :meth:`auto_crop_borders` (which scans for brightness),
        this method uses **Canny** or **Sobel** edge detectors to find
        the actual content edges — works better when the window border
        is a non-black colour or when content has low contrast.

        Args:
            image:            BGR or grayscale numpy array.
            method:           ``"canny"`` (default) or ``"sobel"``.
            canny_low:        Canny lower threshold.
            canny_high:       Canny upper threshold.
            sobel_ksize:      Sobel kernel size (odd, 1–31).
            margin:           Extra pixels to keep around detected edges.
            min_edge_density: Minimum fraction of edge pixels in a
                              row/column for it to be considered content.

        Returns:
            Cropped image (copy).  If edge detection is not available
            or no edges are found, falls back to :meth:`auto_crop_borders`.
        """
        if image is None or image.size == 0:
            return image

        if not CV2_AVAILABLE:
            logger.debug("edge_detect_crop: cv2 not available, falling back")
            return ScreenCapture.auto_crop_borders(image)

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        if method.lower() == "sobel":
            sobel_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=sobel_ksize)
            sobel_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=sobel_ksize)
            edges = np.uint8(np.clip(
                np.sqrt(sobel_x ** 2 + sobel_y ** 2), 0, 255
            ))
            # Binarize
            _, edges = cv2.threshold(edges, 30, 255, cv2.THRESH_BINARY)
        else:
            # Default: Canny
            edges = cv2.Canny(blurred, canny_low, canny_high)

        h, w = edges.shape
        if h == 0 or w == 0:
            return image

        min_h_pixels = max(1, int(w * min_edge_density))
        min_v_pixels = max(1, int(h * min_edge_density))

        # Scan rows for first/last with edges
        row_edge_count = np.count_nonzero(edges, axis=1)
        col_edge_count = np.count_nonzero(edges, axis=0)

        # Find top
        top = 0
        for r in range(h):
            if row_edge_count[r] >= min_h_pixels:
                top = max(0, r - margin)
                break

        # Find bottom
        bottom = h
        for r in range(h - 1, top, -1):
            if row_edge_count[r] >= min_h_pixels:
                bottom = min(h, r + 1 + margin)
                break

        # Find left
        left = 0
        for c in range(w):
            if col_edge_count[c] >= min_v_pixels:
                left = max(0, c - margin)
                break

        # Find right
        right = w
        for c in range(w - 1, left, -1):
            if col_edge_count[c] >= min_v_pixels:
                right = min(w, c + 1 + margin)
                break

        # Sanity check
        if right - left < 10 or bottom - top < 10:
            logger.debug("edge_detect_crop: too small, falling back")
            return ScreenCapture.auto_crop_borders(image)

        return image[top:bottom, left:right].copy()

    @staticmethod
    def smart_crop(
        image: np.ndarray,
        *,
        prefer_edge: bool = True,
        **kwargs,
    ) -> np.ndarray:
        """Combined smart crop: edge detection first, then brightness fallback.

        Args:
            image:       BGR or grayscale numpy array.
            prefer_edge: Try edge detection first (default True).
            **kwargs:    Passed to :meth:`edge_detect_crop`.

        Returns:
            Cropped image (copy).
        """
        if image is None or image.size == 0:
            return image

        if prefer_edge and CV2_AVAILABLE:
            cropped = ScreenCapture.edge_detect_crop(image, **kwargs)
            # If edge crop produced a meaningful reduction, use it
            if cropped.shape[0] < image.shape[0] or cropped.shape[1] < image.shape[1]:
                return cropped

        return ScreenCapture.auto_crop_borders(image)

    # -- internal Win32 capture helper -------------------------------------

    def _win32_grab(self, hwnd: int, width: int, height: int) -> Optional[np.ndarray]:
        """Low-level Win32 PrintWindow / BitBlt capture.

        Tries PrintWindow first (works for layered windows), falls back
        to BitBlt.

        Returns:
            BGR numpy array or ``None``.
        """
        if not WIN32_AVAILABLE:
            return None

        try:
            # Get window DC
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            # Try PrintWindow first
            captured = False
            try:
                import ctypes
                PW_RENDERFULLCONTENT = 0x00000002
                result = ctypes.windll.user32.PrintWindow(
                    hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT
                )
                if result:
                    captured = True
            except Exception:
                pass

            if not captured:
                # Fallback: BitBlt
                save_dc.BitBlt(
                    (0, 0), (width, height),
                    mfc_dc, (0, 0),
                    win32con.SRCCOPY,
                )

            # Convert to numpy
            bmpstr = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img.shape = (height, width, 4)  # BGRA
            img_bgr = img[:, :, :3].copy()

            # Check for blank image
            if np.sum(img_bgr) < 1000:
                img_bgr = None

            # Cleanup
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            return img_bgr

        except Exception as exc:
            logger.error("_win32_grab failed: %s", exc)
            return None


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("HCI Research - Screen Capture Demo (DRY-RUN)")
    print("=" * 60)
    print()
    
    # Initialize in dry-run mode
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
    SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    
    # Create capture instance
    capture = ScreenCapture(
        window_title_pattern="PokerStars.*",
        save_screenshots=True
    )
    
    # Find window
    print("Finding window...")
    window = capture.find_window()
    if window:
        print(f"  Window found: {window.title}")
        print(f"  Resolution: {window.width}x{window.height}")
    print()
    
    # Single capture
    print("Capturing screenshot...")
    screenshot = capture.capture()
    if screenshot is not None:
        print(f"  Captured: {screenshot.shape}")
    print()
    
    # Statistics
    stats = capture.get_statistics()
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode active")
    print("=" * 60)
