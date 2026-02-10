"""
Screen Capture Module for HCI Research (Roadmap3 Phase 1).

EDUCATIONAL USE ONLY: This module captures screenshots of external desktop
applications for Human-Computer Interaction research purposes.

DRY-RUN MODE: All capture operations are simulated by default.
Real window capture requires --unsafe flag.

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
        """Find window using Win32 API (Windows)."""
        # Real implementation would use win32gui.FindWindow, EnumWindows, etc.
        logger.warning("Real Win32 window search not implemented")
        return None
    
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
