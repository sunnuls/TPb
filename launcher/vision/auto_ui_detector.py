"""
Automatic UI Detector - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Automatic detection of UI elements (buttons, menus, tables)
- OCR text recognition for navigation
- Template matching for icons
- Automatic navigation and interaction
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from PIL import Image, ImageGrab
    import cv2
    import pytesseract
    CV_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CV_AVAILABLE = False

try:
    from launcher.vision.window_capturer import WindowCapturer
    CAPTURER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CAPTURER_AVAILABLE = False
    WindowCapturer = None

logger = logging.getLogger(__name__)


class UIElementType(Enum):
    """Types of UI elements."""
    BUTTON = "button"
    MENU = "menu"
    TAB = "tab"
    TABLE_ITEM = "table_item"
    SCROLL_AREA = "scroll_area"
    TEXT_FIELD = "text_field"
    CHECKBOX = "checkbox"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """
    Detected UI element.
    
    Attributes:
        element_type: Type of element
        text: Detected text (if any)
        bbox: Bounding box (x, y, width, height)
        confidence: Detection confidence (0-1)
        clickable: Whether element is clickable
    """
    element_type: UIElementType
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    clickable: bool = True
    
    def get_center(self) -> Tuple[int, int]:
        """Get center point of element."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)


class AutoUIDetector:
    """
    Automatic UI detector.
    
    ⚠️ EDUCATIONAL NOTE:
        Automatically finds and interacts with poker client UI.
    """
    
    def __init__(self):
        """Initialize detector."""
        self.available = CV_AVAILABLE
        
        if not self.available:
            logger.warning("AutoUIDetector not available (requires PIL, cv2, pytesseract)")
        
        # Initialize window capturer (better than ImageGrab)
        self.capturer = WindowCapturer() if CAPTURER_AVAILABLE else None
        
        # Known game modes (from screenshots)
        self.known_game_modes = [
            "Hold'em", "Холдем",
            "PLO",
            "Omaha", "Омаха",
            "Rush & Cash", "Rush and Cash",
            "Spin Gold", "SPIN GOLD",
            "Mystery", "Battle",
            "Tournament", "Турнир",
            "Flip", "FlipNGo"
        ]
    
    def capture_window(
        self,
        hwnd: int = None,
        window_id: str = None,
        bbox: Tuple[int, int, int, int] = None,
        use_direct_capture: bool = True
    ) -> Optional[np.ndarray]:
        """
        Capture window or screen region.
        
        Args:
            hwnd: Window handle (HWND) - preferred method
            window_id: Window title for capture (if hwnd not provided)
            bbox: Bounding box to capture (x, y, width, height) - fallback to screen region capture
            use_direct_capture: Use direct window capture (True) or screen region (False)
        
        Returns:
            Captured image as numpy array (BGR)
        
        Note:
            Direct capture (hwnd) is preferred as it:
            - Works even if window is partially hidden
            - Doesn't interfere with other windows
            - More reliable for automation
        """
        if not self.available:
            return None
        
        try:
            # Method 1: Direct window capture (BEST - no interference with other windows)
            if use_direct_capture and self.capturer and self.capturer.available:
                if hwnd:
                    logger.info(f"Using direct window capture (HWND: {hwnd})")
                    return self.capturer.capture_window_by_hwnd(hwnd)
                
                elif window_id:
                    logger.info(f"Using direct window capture (Title: {window_id})")
                    return self.capturer.capture_window_by_title(window_id)
            
            # Method 2: Screen region capture (FALLBACK - can have issues with overlapping windows)
            logger.warning("Using screen region capture (fallback) - may have issues with overlapping windows")
            
            if bbox:
                x, y, w, h = bbox
                screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            else:
                screenshot = ImageGrab.grab()
            
            # Convert to numpy array (BGR for OpenCV)
            img_array = np.array(screenshot)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_bgr
        
        except Exception as e:
            logger.error(f"Failed to capture window: {e}", exc_info=True)
            return None
    
    def detect_ui_elements(self, image: np.ndarray) -> List[UIElement]:
        """
        Detect all UI elements in image.
        
        Args:
            image: Image to analyze
        
        Returns:
            List of detected UI elements
        """
        if not self.available:
            return []
        
        elements = []
        
        # Detect text elements (OCR)
        text_elements = self._detect_text_elements(image)
        elements.extend(text_elements)
        
        # Detect buttons (color/shape based)
        button_elements = self._detect_buttons(image)
        elements.extend(button_elements)
        
        # Detect tables/lists
        table_elements = self._detect_tables(image)
        elements.extend(table_elements)
        
        logger.info(f"Detected {len(elements)} UI elements")
        
        return elements
    
    def _detect_text_elements(self, image: np.ndarray) -> List[UIElement]:
        """Detect text elements using OCR."""
        if not self.available:
            return []
        
        elements = []
        
        try:
            # Run OCR
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Process each detected text
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                if text and conf > 30:  # Confidence threshold
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Determine element type based on text
                    element_type = UIElementType.TEXT_FIELD
                    if any(mode.lower() in text.lower() for mode in self.known_game_modes):
                        element_type = UIElementType.BUTTON
                    
                    elements.append(UIElement(
                        element_type=element_type,
                        text=text,
                        bbox=(x, y, w, h),
                        confidence=conf / 100.0,
                        clickable=True
                    ))
        
        except Exception as e:
            logger.error(f"OCR detection failed: {e}")
        
        return elements
    
    def _detect_buttons(self, image: np.ndarray) -> List[UIElement]:
        """Detect buttons based on color and shape."""
        if not self.available:
            return []
        
        elements = []
        
        try:
            # Convert to HSV for color detection
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Detect green buttons (common in poker UI)
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([85, 255, 255])
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            
            # Find contours
            contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size (buttons are usually a certain size)
                if 50 < w < 300 and 30 < h < 100:
                    elements.append(UIElement(
                        element_type=UIElementType.BUTTON,
                        text="",
                        bbox=(x, y, w, h),
                        confidence=0.7,
                        clickable=True
                    ))
        
        except Exception as e:
            logger.error(f"Button detection failed: {e}")
        
        return elements
    
    def _detect_tables(self, image: np.ndarray) -> List[UIElement]:
        """Detect table/list elements."""
        # TODO: Implement table detection
        return []
    
    def find_element_by_text(self, elements: List[UIElement], text: str, partial: bool = True) -> Optional[UIElement]:
        """
        Find UI element by text.
        
        Args:
            elements: List of detected elements
            text: Text to search for
            partial: Allow partial matches
        
        Returns:
            Found element or None
        """
        text_lower = text.lower()
        
        for element in elements:
            element_text_lower = element.text.lower()
            
            if partial:
                if text_lower in element_text_lower or element_text_lower in text_lower:
                    return element
            else:
                if text_lower == element_text_lower:
                    return element
        
        return None
    
    def find_game_mode_buttons(self, elements: List[UIElement]) -> Dict[str, UIElement]:
        """
        Find all game mode buttons.
        
        Args:
            elements: List of detected elements
        
        Returns:
            Dictionary mapping game mode to UI element
        """
        game_buttons = {}
        
        for mode in self.known_game_modes:
            element = self.find_element_by_text(elements, mode, partial=True)
            if element:
                game_buttons[mode] = element
        
        return game_buttons
    
    def auto_navigate_to_mode(self, mode_name: str, window_bbox: Tuple[int, int, int, int] = None) -> bool:
        """
        Automatically navigate to a game mode.
        
        Args:
            mode_name: Name of game mode (e.g., "Hold'em", "PLO")
            window_bbox: Window bounds for capture
        
        Returns:
            True if navigation successful
        """
        logger.info(f"Auto-navigating to mode: {mode_name}")
        
        # Capture window
        image = self.capture_window(bbox=window_bbox)
        if image is None:
            logger.error("Failed to capture window")
            return False
        
        # Detect UI elements
        elements = self.detect_ui_elements(image)
        logger.info(f"Detected {len(elements)} UI elements")
        
        # Find game mode button
        mode_button = self.find_element_by_text(elements, mode_name, partial=True)
        
        if mode_button:
            logger.info(f"Found '{mode_name}' button at {mode_button.bbox}")
            # TODO: Implement click action
            return True
        else:
            logger.warning(f"Could not find '{mode_name}' button")
            return False


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Auto UI Detector - Educational Research")
    print("=" * 60)
    print()
    
    detector = AutoUIDetector()
    
    print(f"Detector available: {detector.available}")
    print(f"Known game modes: {len(detector.known_game_modes)}")
    print()
    
    if detector.available:
        print("Capturing screen...")
        image = detector.capture_window()
        
        if image is not None:
            print(f"Captured image: {image.shape}")
            
            print("\nDetecting UI elements...")
            elements = detector.detect_ui_elements(image)
            
            print(f"Found {len(elements)} elements:")
            for i, elem in enumerate(elements[:10], 1):
                print(f"  {i}. {elem.element_type.value}: '{elem.text}' @ {elem.bbox}")
            
            if len(elements) > 10:
                print(f"  ... and {len(elements) - 10} more")
    
    print()
    print("=" * 60)
