"""
Debug Viewer - Visual feedback for bot vision.

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Show captured screen
- Display detected UI elements
- Show bounding boxes
- Real-time updates
"""

import logging
from typing import Optional, List
import numpy as np

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QScrollArea, QTextEdit, QGroupBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

try:
    import cv2
    CV_AVAILABLE = True
except:
    CV_AVAILABLE = False

from launcher.vision import AutoUIDetector, UIElement

logger = logging.getLogger(__name__)


class DebugViewer(QWidget):
    """
    Debug viewer for bot vision.
    
    Shows:
    - Captured screen
    - Detected elements (with bounding boxes)
    - Detection logs
    """
    
    def __init__(self, parent=None):
        """Initialize debug viewer."""
        super().__init__(parent)
        
        self.detector = AutoUIDetector()
        self.current_image = None
        self.detected_elements: List[UIElement] = []
        
        # Store capture parameters for auto-update
        self.capture_hwnd: Optional[int] = None
        self.capture_bbox: Optional[tuple] = None
        
        self.setWindowTitle("🔍 Bot Vision Debug Viewer")
        self.setGeometry(100, 100, 1200, 750)  # Reduced from 1400x900 to fit better on screen
        
        self._setup_ui()
        
        # Auto-update timer
        self.auto_update = False
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._auto_capture)
        
        logger.info("Debug Viewer initialized")
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔍 Bot Vision Debug Viewer")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #00AAFF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Window info label
        self.window_info_label = QLabel()
        self.window_info_label.setStyleSheet("font-size: 10pt; color: #FFAA00; padding: 5px;")
        self.window_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.window_info_label)
        
        # Main content (horizontal split)
        content_layout = QHBoxLayout()
        
        # Left: Image viewer
        image_group = QGroupBox("Captured Screen (with detected elements)")
        image_layout = QVBoxLayout(image_group)
        
        # Scroll area for image
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)  # Changed from True - don't auto-resize widget
        scroll.setMinimumSize(620, 420)  # Fixed scroll area size
        scroll.setMaximumSize(620, 420)  # Limit maximum size to prevent overlap
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #222; border: 2px solid #444;")
        self.image_label.setMinimumSize(600, 400)  # Image size
        
        scroll.setWidget(self.image_label)
        image_layout.addWidget(scroll)
        
        content_layout.addWidget(image_group, stretch=7)
        
        # Right: Detection info
        info_group = QGroupBox("Detection Info")
        info_layout = QVBoxLayout(info_group)
        
        # Stats
        self.stats_label = QLabel("No capture yet")
        self.stats_label.setStyleSheet("font-size: 11pt; color: #00FF00;")
        info_layout.addWidget(self.stats_label)
        
        # Detected elements list
        elements_label = QLabel("Detected Elements:")
        elements_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(elements_label)
        
        self.elements_text = QTextEdit()
        self.elements_text.setReadOnly(True)
        self.elements_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #00FF00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        info_layout.addWidget(self.elements_text)
        
        content_layout.addWidget(info_group, stretch=3)
        
        layout.addLayout(content_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        capture_btn = QPushButton("📸 Capture Now")
        capture_btn.setStyleSheet("background-color: #0066CC; color: white; font-weight: bold; padding: 10px;")
        capture_btn.clicked.connect(self._manual_capture)
        controls_layout.addWidget(capture_btn)
        
        self.auto_btn = QPushButton("🔄 Auto-Update: OFF")
        self.auto_btn.setStyleSheet("background-color: #666; color: white; font-weight: bold; padding: 10px;")
        self.auto_btn.clicked.connect(self._toggle_auto_update)
        controls_layout.addWidget(self.auto_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self._clear)
        controls_layout.addWidget(clear_btn)
        
        controls_layout.addStretch()
        
        close_btn = QPushButton("❌ Close")
        close_btn.clicked.connect(self.close)
        controls_layout.addWidget(close_btn)
        
        layout.addLayout(controls_layout)
    
    def capture_and_detect(self, hwnd: int = None, window_bbox: tuple = None):
        """
        Capture screen and detect elements.
        
        Args:
            hwnd: Window handle (HWND) - preferred for direct capture
            window_bbox: Window bounds (x, y, width, height) - fallback
        """
        # Store parameters for auto-update
        self.capture_hwnd = hwnd
        self.capture_bbox = window_bbox
        
        # Update window info label
        self._update_window_info_label()
        
        if hwnd:
            logger.info(f"Capturing window by HWND: {hwnd}")
        elif window_bbox:
            logger.info(f"Capturing screen region: {window_bbox}")
        else:
            logger.info("Capturing full screen")
        
        try:
            # Capture (prefer HWND for direct window capture)
            if hwnd:
                image = self.detector.capture_window(hwnd=hwnd, use_direct_capture=True)
            else:
                image = self.detector.capture_window(bbox=window_bbox, use_direct_capture=False)
            
            if image is None:
                logger.error("Failed to capture")
                self.stats_label.setText("❌ Capture failed")
                return
            
            self.current_image = image
            h, w = image.shape[:2]
            
            logger.info(f"Captured: {w}x{h}")
            
            # Detect elements
            elements = self.detector.detect_ui_elements(image)
            self.detected_elements = elements
            
            logger.info(f"Detected {len(elements)} elements")
            
            # Find game mode buttons specifically
            game_buttons = self.detector.find_game_mode_buttons(elements)
            
            # Update stats
            stats_text = f"✅ Image: {w}x{h}\n"
            stats_text += f"✅ Elements: {len(elements)}\n"
            stats_text += f"✅ Game Buttons: {len(game_buttons)}\n\n"
            
            if game_buttons:
                stats_text += "Game Modes Found:\n"
                for mode in game_buttons.keys():
                    stats_text += f"  • {mode}\n"
            
            self.stats_label.setText(stats_text)
            
            # Update elements list
            self._update_elements_list(elements, game_buttons)
            
            # Draw image with bounding boxes
            self._draw_image_with_boxes(image, elements, game_buttons)
        
        except Exception as e:
            logger.error(f"Capture error: {e}", exc_info=True)
            self.stats_label.setText(f"❌ Error: {str(e)}")
    
    def _draw_image_with_boxes(self, image: np.ndarray, elements: List[UIElement], game_buttons: dict):
        """Draw image with bounding boxes."""
        if not CV_AVAILABLE:
            return
        
        # Copy image
        img_draw = image.copy()
        
        # Draw all elements (yellow)
        for elem in elements:
            x, y, w, h = elem.bbox
            color = (0, 255, 255)  # Yellow
            cv2.rectangle(img_draw, (x, y), (x + w, y + h), color, 2)
            
            # Draw text if available
            if elem.text:
                cv2.putText(
                    img_draw,
                    elem.text[:20],
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1
                )
        
        # Draw game buttons (green, thicker)
        for mode, elem in game_buttons.items():
            x, y, w, h = elem.bbox
            color = (0, 255, 0)  # Green
            cv2.rectangle(img_draw, (x, y), (x + w, y + h), color, 4)
            
            # Draw label
            cv2.putText(
                img_draw,
                f"GAME: {mode}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
        
        # Convert to QPixmap
        height, width, channel = img_draw.shape
        bytes_per_line = 3 * width
        
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_draw, cv2.COLOR_BGR2RGB)
        
        q_image = QImage(
            img_rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale to fit if needed (much smaller to not overlap controls)
        max_width = 600   # Reduced from 750 to fit better
        max_height = 400  # Reduced from 550 to fit better
        
        # Scale to fit within bounds while maintaining aspect ratio
        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(
                max_width,
                max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        self.image_label.setPixmap(pixmap)
    
    def _update_elements_list(self, elements: List[UIElement], game_buttons: dict):
        """Update elements list."""
        text = ""
        
        # Game buttons first (most important)
        if game_buttons:
            text += "=" * 50 + "\n"
            text += "🎮 GAME MODE BUTTONS\n"
            text += "=" * 50 + "\n\n"
            
            for mode, elem in game_buttons.items():
                x, y, w, h = elem.bbox
                text += f"✅ {mode}\n"
                text += f"   Position: ({x}, {y})\n"
                text += f"   Size: {w}x{h}\n"
                text += f"   Confidence: {elem.confidence:.2f}\n\n"
        
        # All other elements
        text += "=" * 50 + "\n"
        text += f"📋 ALL ELEMENTS ({len(elements)})\n"
        text += "=" * 50 + "\n\n"
        
        for i, elem in enumerate(elements[:50], 1):  # First 50
            text += f"[{i}] {elem.element_type.value.upper()}\n"
            text += f"    Text: '{elem.text[:30]}'\n"
            text += f"    BBox: {elem.bbox}\n"
            text += f"    Conf: {elem.confidence:.2f}\n\n"
        
        if len(elements) > 50:
            text += f"\n... and {len(elements) - 50} more elements\n"
        
        self.elements_text.setPlainText(text)
    
    def _manual_capture(self):
        """Manual capture."""
        # Use stored capture parameters (hwnd or bbox)
        self.capture_and_detect(hwnd=self.capture_hwnd, window_bbox=self.capture_bbox)
    
    def _toggle_auto_update(self):
        """Toggle auto-update."""
        self.auto_update = not self.auto_update
        
        if self.auto_update:
            self.auto_btn.setText("🔄 Auto-Update: ON")
            self.auto_btn.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold; padding: 10px;")
            self.update_timer.start(2000)  # Update every 2 seconds
        else:
            self.auto_btn.setText("🔄 Auto-Update: OFF")
            self.auto_btn.setStyleSheet("background-color: #666; color: white; font-weight: bold; padding: 10px;")
            self.update_timer.stop()
    
    def _auto_capture(self):
        """Auto-capture timer."""
        if self.auto_update:
            # Use stored capture parameters (hwnd or bbox)
            self.capture_and_detect(hwnd=self.capture_hwnd, window_bbox=self.capture_bbox)
    
    def _update_window_info_label(self):
        """Update window info label to show what is being captured."""
        try:
            if self.capture_hwnd:
                # Try to get window title
                try:
                    import win32gui
                    title = win32gui.GetWindowText(self.capture_hwnd)
                    self.window_info_label.setText(f"📌 Capturing window: {title} (HWND: {self.capture_hwnd})")
                except:
                    self.window_info_label.setText(f"📌 Capturing window (HWND: {self.capture_hwnd})")
            elif self.capture_bbox:
                x, y, w, h = self.capture_bbox
                self.window_info_label.setText(f"📌 Capturing screen region: ({x}, {y}) {w}x{h}")
            else:
                self.window_info_label.setText("📌 Capturing full screen")
        except Exception as e:
            logger.warning(f"Failed to update window info label: {e}")
            self.window_info_label.setText("📌 Capturing...")
    
    def _clear(self):
        """Clear display."""
        self.image_label.clear()
        self.elements_text.clear()
        self.stats_label.setText("Cleared")
        self.current_image = None
        self.detected_elements = []


# Educational example
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    viewer = DebugViewer()
    viewer.show()
    
    sys.exit(app.exec())
