"""
Automatic Navigator - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Automatic clicking on UI elements
- Scrolling through lists
- Waiting for UI changes
- Multi-step navigation sequences
"""

import logging
import time
from typing import Optional, Tuple, List
from enum import Enum

try:
    import pyautogui
    import win32api
    import win32con
    AUTOGUI_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    AUTOGUI_AVAILABLE = False
except SyntaxError:
    # Workaround for pyautogui null bytes issue
    AUTOGUI_AVAILABLE = False
    pyautogui = None

from launcher.vision.auto_ui_detector import AutoUIDetector, UIElement

logger = logging.getLogger(__name__)


class NavigationResult(Enum):
    """Navigation operation result."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    ERROR = "error"


class AutoNavigator:
    """
    Automatic navigator for poker client UI.
    
    ⚠️ EDUCATIONAL NOTE:
        Automatically interacts with poker client interface.
    """
    
    def __init__(self, detector: Optional[AutoUIDetector] = None):
        """
        Initialize navigator.
        
        Args:
            detector: UI detector instance (creates new if None)
        """
        self.available = AUTOGUI_AVAILABLE
        self.detector = detector or AutoUIDetector()
        
        if not self.available:
            logger.warning("AutoNavigator not available (requires pyautogui, win32api)")
        else:
            # Safety settings
            try:
                pyautogui.FAILSAFE = True  # Move mouse to corner to abort
                pyautogui.PAUSE = 0.5  # Pause between actions
            except:
                pass
    
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """
        Click at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks
        
        Returns:
            True if successful
        """
        if not self.available:
            logger.error("AutoNavigator not available")
            return False
        
        try:
            logger.info(f"Clicking at ({x}, {y}) with {button} button")
            
            # Move mouse smoothly
            pyautogui.moveTo(x, y, duration=0.3)
            time.sleep(0.1)
            
            # Click
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            return True
        
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    def click_element(self, element: UIElement, offset: Tuple[int, int] = (0, 0), window_offset: Tuple[int, int] = (0, 0)) -> bool:
        """
        Click on UI element.
        
        Args:
            element: UI element to click
            offset: Offset from element center (x, y)
            window_offset: Window position offset (x, y) - IMPORTANT for multi-window setups
        
        Returns:
            True if successful
        """
        center_x, center_y = element.get_center()
        
        # Add window offset (element coordinates are relative to window)
        screen_x = center_x + window_offset[0] + offset[0]
        screen_y = center_y + window_offset[1] + offset[1]
        
        logger.info(f"Element center (relative): ({center_x}, {center_y})")
        logger.info(f"Window offset: {window_offset}")
        logger.info(f"Screen position: ({screen_x}, {screen_y})")
        
        return self.click(screen_x, screen_y)
    
    def scroll(self, amount: int, x: int = None, y: int = None) -> bool:
        """
        Scroll at position.
        
        Args:
            amount: Scroll amount (positive = up, negative = down)
            x: X coordinate (None = current position)
            y: Y coordinate (None = current position)
        
        Returns:
            True if successful
        """
        if not self.available:
            return False
        
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.2)
            
            logger.info(f"Scrolling {amount} clicks")
            pyautogui.scroll(amount)
            
            return True
        
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    def type_text(self, text: str, interval: float = 0.1) -> bool:
        """
        Type text.
        
        Args:
            text: Text to type
            interval: Interval between keystrokes
        
        Returns:
            True if successful
        """
        if not self.available:
            return False
        
        try:
            logger.info(f"Typing text: {text}")
            pyautogui.write(text, interval=interval)
            return True
        
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    def wait_for_element(
        self,
        text: str,
        bbox: Tuple[int, int, int, int],
        timeout: float = 10.0,
        check_interval: float = 0.5
    ) -> Optional[UIElement]:
        """
        Wait for UI element to appear.
        
        Args:
            text: Element text to wait for
            bbox: Bounding box to search in
            timeout: Maximum wait time in seconds
            check_interval: Time between checks
        
        Returns:
            Found element or None
        """
        logger.info(f"Waiting for element: '{text}' (timeout: {timeout}s)")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Capture and detect
            image = self.detector.capture_window(bbox=bbox)
            if image is not None:
                elements = self.detector.detect_ui_elements(image)
                element = self.detector.find_element_by_text(elements, text)
                
                if element:
                    logger.info(f"Element found: '{text}'")
                    return element
            
            time.sleep(check_interval)
        
        logger.warning(f"Element not found: '{text}' (timeout)")
        return None
    
    def navigate_to_game_mode(
        self,
        mode_name: str,
        hwnd: int = None,
        window_bbox: Tuple[int, int, int, int] = None,
        wait_after_click: float = 2.0
    ) -> NavigationResult:
        """
        Navigate to game mode.
        
        Args:
            mode_name: Name of game mode (e.g., "Hold'em")
            hwnd: Window handle (HWND) - preferred for direct capture
            window_bbox: Window bounds - fallback if hwnd not available
            wait_after_click: Time to wait after clicking
        
        Returns:
            Navigation result
        """
        logger.info("=" * 70)
        logger.info(f"🎯 NAVIGATING TO GAME MODE: {mode_name}")
        if hwnd:
            logger.info(f"Window HWND: {hwnd}")
        elif window_bbox:
            logger.info(f"Window bbox: {window_bbox}")
        logger.info("=" * 70)
        
        try:
            # Capture window (prefer direct capture)
            logger.info("Step 1: Capturing window...")
            if hwnd:
                image = self.detector.capture_window(hwnd=hwnd, use_direct_capture=True)
            else:
                image = self.detector.capture_window(bbox=window_bbox, use_direct_capture=False)
            
            if image is None:
                logger.error("❌ Window capture failed - image is None")
                return NavigationResult.ERROR
            
            h, w = image.shape[:2]
            logger.info(f"✅ Captured: {w}x{h} pixels")
            
            # Detect elements
            logger.info("Step 2: Detecting UI elements...")
            elements = self.detector.detect_ui_elements(image)
            logger.info(f"✅ Detected {len(elements)} UI elements")
            
            # Log some detected elements for debugging
            if elements:
                logger.info("Sample detected elements:")
                for i, elem in enumerate(elements[:10], 1):
                    logger.info(f"  [{i}] {elem.element_type.value}: '{elem.text[:30]}' @ {elem.bbox}")
            
            # Find game mode button
            logger.info(f"Step 3: Looking for '{mode_name}' button...")
            mode_element = self.detector.find_element_by_text(elements, mode_name)
            
            if not mode_element:
                logger.warning(f"❌ Game mode button not found: {mode_name}")
                logger.warning("Available text elements:")
                text_elems = [e for e in elements if e.text.strip()]
                for elem in text_elems[:20]:
                    logger.warning(f"  - '{elem.text}'")
                return NavigationResult.NOT_FOUND
            
            logger.info(f"✅ Found '{mode_name}' button at {mode_element.bbox}")
            logger.info(f"   Element type: {mode_element.element_type.value}")
            logger.info(f"   Confidence: {mode_element.confidence:.2f}")
            
            # Click button (with window offset)
            logger.info(f"Step 4: Clicking button...")
            window_offset = (window_bbox[0], window_bbox[1])
            if not self.click_element(mode_element, window_offset=window_offset):
                logger.error("❌ Click failed")
                return NavigationResult.ERROR
            
            logger.info(f"✅ Clicked successfully!")
            
            # Wait for page to load
            logger.info(f"Step 5: Waiting {wait_after_click}s for page to load...")
            time.sleep(wait_after_click)
            
            logger.info("=" * 70)
            logger.info(f"✅ NAVIGATION TO {mode_name} COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            
            return NavigationResult.SUCCESS
        
        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"❌ NAVIGATION FAILED WITH ERROR")
            logger.error(f"Error: {e}", exc_info=True)
            logger.error("=" * 70)
            return NavigationResult.ERROR
    
    def find_and_scroll_to_table(
        self,
        stake_filter: str,
        min_players: int,
        max_players: int,
        scroll_area_bbox: Tuple[int, int, int, int],
        max_scrolls: int = 10
    ) -> Optional[UIElement]:
        """
        Find table matching criteria (with scrolling).
        
        Args:
            stake_filter: Stake filter (e.g., "$0.25/$0.50")
            min_players: Minimum players
            max_players: Maximum players
            scroll_area_bbox: Area to scroll
            max_scrolls: Maximum scroll attempts
        
        Returns:
            Found table element or None
        """
        logger.info("=" * 70)
        logger.info("🔍 SEARCHING FOR POKER TABLE")
        logger.info(f"Stake filter: {stake_filter}")
        logger.info(f"Players: {min_players}-{max_players}")
        logger.info(f"Scroll area: {scroll_area_bbox}")
        logger.info("=" * 70)
        
        x, y, w, h = scroll_area_bbox
        scroll_x = x + w // 2
        scroll_y = y + h // 2
        
        for scroll_num in range(max_scrolls):
            logger.info(f"📜 Scroll attempt {scroll_num + 1}/{max_scrolls}")
            
            # Capture current view
            logger.info(f"Capturing scroll area...")
            image = self.detector.capture_window(bbox=scroll_area_bbox)
            if image is None:
                logger.warning("⚠️ Failed to capture, skipping...")
                continue
            
            logger.info(f"✅ Captured: {image.shape[:2]}")
            
            # Detect tables
            logger.info("Detecting UI elements...")
            elements = self.detector.detect_ui_elements(image)
            logger.info(f"✅ Found {len(elements)} elements")
            
            # Log detected text for debugging
            text_elements = [e for e in elements if e.text.strip()]
            if text_elements:
                logger.info(f"Text elements found: {len(text_elements)}")
                for i, elem in enumerate(text_elements[:5], 1):
                    logger.info(f"  [{i}] '{elem.text[:40]}'")
            
            # Search for matching table
            matching_elements = []
            for element in elements:
                if stake_filter.lower() in element.text.lower():
                    matching_elements.append(element)
            
            if matching_elements:
                logger.info(f"✅ Found {len(matching_elements)} matching table(s)!")
                for elem in matching_elements:
                    logger.info(f"  - {elem.text}")
                logger.info("=" * 70)
                return matching_elements[0]
            
            # Scroll down
            if scroll_num < max_scrolls - 1:
                logger.info(f"Scrolling down at ({scroll_x}, {scroll_y})...")
                self.scroll(-3, x=scroll_x, y=scroll_y)
                time.sleep(0.5)
        
        logger.warning("=" * 70)
        logger.warning("❌ NO MATCHING TABLE FOUND AFTER SCROLLING")
        logger.warning("=" * 70)
        return None
    
    def join_table(
        self,
        table_element: UIElement,
        seat_number: Optional[int] = None,
        window_offset: Tuple[int, int] = (0, 0)
    ) -> NavigationResult:
        """
        Join a table.
        
        Args:
            table_element: Table UI element
            seat_number: Preferred seat (None = any)
            window_offset: Window position offset
        
        Returns:
            Navigation result
        """
        logger.info("=" * 70)
        logger.info(f"🪑 JOINING TABLE: {table_element.text}")
        logger.info(f"Table bbox: {table_element.bbox}")
        if seat_number:
            logger.info(f"Preferred seat: {seat_number}")
        logger.info("=" * 70)
        
        try:
            # Click table
            logger.info("Clicking table to join...")
            if not self.click_element(table_element, window_offset=window_offset):
                logger.error("❌ Click failed")
                return NavigationResult.ERROR
            
            logger.info("✅ Clicked table")
            
            time.sleep(1.0)
            
            # TODO: Implement seat selection and join confirmation
            # This will depend on specific poker client UI
            logger.info("⚠️ Seat selection not yet implemented - using default")
            
            logger.info("=" * 70)
            logger.info("✅ TABLE JOIN INITIATED")
            logger.info("=" * 70)
            return NavigationResult.SUCCESS
        
        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"❌ JOIN TABLE FAILED")
            logger.error(f"Error: {e}", exc_info=True)
            logger.error("=" * 70)
            return NavigationResult.ERROR
    
    def execute_navigation_sequence(
        self,
        mode_name: str,
        stake_filter: str,
        min_players: int,
        max_players: int,
        window_bbox: Tuple[int, int, int, int]
    ) -> NavigationResult:
        """
        Execute complete navigation sequence.
        
        Steps:
        1. Navigate to game mode
        2. Find suitable table
        3. Join table
        
        Args:
            mode_name: Game mode to navigate to
            stake_filter: Stake filter
            min_players: Minimum players
            max_players: Maximum players
            window_bbox: Window bounds
        
        Returns:
            Navigation result
        """
        logger.info("=" * 60)
        logger.info("STARTING NAVIGATION SEQUENCE")
        logger.info(f"Mode: {mode_name}")
        logger.info(f"Stakes: {stake_filter}")
        logger.info(f"Players: {min_players}-{max_players}")
        logger.info("=" * 60)
        
        # Step 1: Navigate to game mode
        result = self.navigate_to_game_mode(mode_name, window_bbox, wait_after_click=3.0)
        if result != NavigationResult.SUCCESS:
            logger.error(f"Failed to navigate to {mode_name}")
            return result
        
        # Step 2: Find table
        # Define scroll area (adjust based on actual UI)
        x, y, w, h = window_bbox
        scroll_bbox = (x + 50, y + 150, w - 100, h - 200)
        
        table = self.find_and_scroll_to_table(
            stake_filter,
            min_players,
            max_players,
            scroll_bbox,
            max_scrolls=10
        )
        
        if not table:
            logger.warning("No suitable table found")
            return NavigationResult.NOT_FOUND
        
        # Step 3: Join table
        result = self.join_table(table)
        
        logger.info("=" * 60)
        logger.info(f"NAVIGATION SEQUENCE COMPLETED: {result.value}")
        logger.info("=" * 60)
        
        return result


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Auto Navigator - Educational Research")
    print("=" * 60)
    print()
    
    navigator = AutoNavigator()
    
    print(f"Navigator available: {navigator.available}")
    print()
    
    if navigator.available:
        print("Testing basic navigation...")
        
        # Test: Navigate to Hold'em
        result = navigator.navigate_to_game_mode(
            "Hold'em",
            window_bbox=(0, 0, 1920, 1080),
            wait_after_click=2.0
        )
        
        print(f"Navigation result: {result.value}")
    
    print()
    print("=" * 60)
