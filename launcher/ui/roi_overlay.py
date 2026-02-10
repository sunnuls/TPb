"""
ROI Overlay Window - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Transparent overlay window
- Draw ROI rectangles
- Label zones
- Save configuration
"""

import logging
from typing import Optional, List, Callable

try:
    from PyQt6.QtWidgets import (
        QWidget, QLabel, QVBoxLayout, QHBoxLayout,
        QPushButton, QLineEdit, QComboBox, QMessageBox
    )
    from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
    from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QKeyEvent
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.roi_config import ROIZone

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class ROIOverlay(QWidget):
        """
        Transparent overlay for ROI selection.
        
        Features:
        - Draw rectangles by dragging mouse
        - Label zones
        - Save ROI configuration
        
        ⚠️ EDUCATIONAL NOTE:
            Configures bot vision zones.
        
        Signals:
            roi_saved: Emitted when ROI is saved (List[ROIZone])
        """
        
        roi_saved = pyqtSignal(list)
        
        # Standard zone templates
        ZONE_TEMPLATES = [
            "hero_card_1",
            "hero_card_2",
            "board_card_1",
            "board_card_2",
            "board_card_3",
            "board_card_4",
            "board_card_5",
            "pot",
            "stack_1",
            "stack_2",
            "stack_3",
            "stack_4",
            "stack_5",
            "stack_6",
            "stack_7",
            "stack_8",
            "stack_9",
            "fold_button",
            "check_button",
            "call_button",
            "raise_button",
            "bet_input",
            "custom"
        ]
        
        def __init__(self, parent=None, target_window_id: Optional[str] = None):
            """
            Initialize ROI overlay.
            
            Args:
                parent: Parent widget
                target_window_id: Target window to overlay
            """
            super().__init__(parent)
            
            self.target_window_id = target_window_id
            self.zones: List[ROIZone] = []
            
            # Drawing state
            self.drawing = False
            self.start_point = QPoint()
            self.current_rect = QRect()
            
            # Current zone name
            self.current_zone_name = "hero_card_1"
            
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup UI."""
            # Window flags for overlay
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            
            # Semi-transparent background
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
            
            # Enable mouse tracking
            self.setMouseTracking(True)
            
            # Control panel
            self._create_control_panel()
            
            # Note: showFullScreen() will be called externally
        
        def _create_control_panel(self):
            """Create control panel (draggable)."""
            # Create draggable panel
            self.control_panel = QWidget(self)
            self.control_panel.setStyleSheet("""
                QWidget {
                    background-color: rgba(30, 30, 30, 230);
                    border: 2px solid #00FF00;
                    border-radius: 5px;
                    padding: 10px;
                }
                QLabel { color: white; }
                QPushButton {
                    background-color: #444;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #555; }
                QComboBox {
                    background-color: #444;
                    color: white;
                    border: none;
                    padding: 5px;
                }
            """)
            
            # Make panel draggable
            self.panel_dragging = False
            self.panel_drag_position = QPoint()
            
            panel = self.control_panel
            
            layout = QVBoxLayout(panel)
            
            # Title (draggable indicator)
            title = QLabel("⬍ ROI CONFIGURATION ⬍")
            title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #00FF00; cursor: move;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)
            
            # Drag hint
            drag_hint = QLabel("(Drag this panel to move)")
            drag_hint.setStyleSheet("font-size: 9pt; color: #888; font-style: italic;")
            drag_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(drag_hint)
            
            # Instructions
            instructions = QLabel(
                "Draw ROI zones by dragging mouse OUTSIDE this panel.\n"
                "ESC: Exit | ENTER: Save | DELETE: Remove last zone"
            )
            instructions.setStyleSheet("font-size: 10pt; color: #FFFF00;")
            instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(instructions)
            
            # Zone selector
            zone_layout = QHBoxLayout()
            zone_layout.addWidget(QLabel("Zone:"))
            
            self.zone_combo = QComboBox()
            self.zone_combo.addItems(self.ZONE_TEMPLATES)
            zone_layout.addWidget(self.zone_combo)
            
            layout.addLayout(zone_layout)
            
            # Status
            self.status_label = QLabel(f"Zones: 0")
            self.status_label.setStyleSheet("font-size: 12pt; color: #00FFFF;")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.status_label)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            save_btn = QPushButton("✓ SAVE ROI")
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00AA00;
                    color: white;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #00CC00; }
            """)
            save_btn.clicked.connect(self._on_save)
            btn_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("✕ CANCEL")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #AA0000;
                    color: white;
                    font-size: 12pt;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QPushButton:hover { background-color: #CC0000; }
            """)
            cancel_btn.clicked.connect(self.close)
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
            
            # Position panel (larger and more visible)
            panel.setGeometry(20, 20, 450, 250)
        
        def paintEvent(self, event):
            """Paint ROI zones."""
            painter = QPainter(self)
            
            # Draw existing zones
            for zone in self.zones:
                # Zone rectangle
                pen = QPen(QColor(0, 255, 0), 2)
                painter.setPen(pen)
                painter.drawRect(zone.x, zone.y, zone.width, zone.height)
                
                # Zone label
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                painter.drawText(
                    zone.x + 5,
                    zone.y + 15,
                    zone.name
                )
            
            # Draw current rectangle being drawn
            if self.drawing:
                pen = QPen(QColor(255, 255, 0), 2, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(self.current_rect)
        
        def mousePressEvent(self, event):
            """Mouse press - start drawing or dragging panel."""
            if event.button() == Qt.MouseButton.LeftButton:
                # Check if click is inside control panel
                if self.control_panel.geometry().contains(event.pos()):
                    # Start dragging panel
                    self.panel_dragging = True
                    self.panel_drag_position = event.pos() - self.control_panel.pos()
                else:
                    # Start drawing zone
                    self.drawing = True
                    self.start_point = event.pos()
                    self.current_rect = QRect(self.start_point, QPoint())
                    self.current_zone_name = self.zone_combo.currentText()
        
        def mouseMoveEvent(self, event):
            """Mouse move - update current rectangle or drag panel."""
            if self.panel_dragging:
                # Drag control panel
                new_pos = event.pos() - self.panel_drag_position
                # Keep panel within window bounds
                new_pos.setX(max(0, min(new_pos.x(), self.width() - self.control_panel.width())))
                new_pos.setY(max(0, min(new_pos.y(), self.height() - self.control_panel.height())))
                self.control_panel.move(new_pos)
            elif self.drawing:
                # Draw zone rectangle
                self.current_rect = QRect(self.start_point, event.pos()).normalized()
                self.update()
        
        def mouseReleaseEvent(self, event):
            """Mouse release - finalize zone or stop dragging."""
            if event.button() == Qt.MouseButton.LeftButton:
                if self.panel_dragging:
                    # Stop dragging panel
                    self.panel_dragging = False
                elif self.drawing:
                    # Finalize zone
                    self.drawing = False
                    
                    # Create zone
                    zone = ROIZone(
                        name=self.current_zone_name,
                        x=self.current_rect.x(),
                        y=self.current_rect.y(),
                        width=self.current_rect.width(),
                        height=self.current_rect.height()
                    )
                    
                    # Validate size
                    if zone.width > 10 and zone.height > 10:
                        self.zones.append(zone)
                        self._update_status()
                        self.update()
                        
                        logger.info(f"Zone added: {zone.name} ({zone.width}x{zone.height})")
                    
                    self.current_rect = QRect()
        
        def keyPressEvent(self, event: QKeyEvent):
            """Handle keyboard shortcuts."""
            if event.key() == Qt.Key.Key_Escape:
                self.close()
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self._on_save()
            elif event.key() == Qt.Key.Key_Delete and self.zones:
                removed = self.zones.pop()
                logger.info(f"Zone removed: {removed.name}")
                self._update_status()
                self.update()
        
        def _update_status(self):
            """Update status label."""
            self.status_label.setText(f"Zones: {len(self.zones)}")
        
        def _on_save(self):
            """Save ROI configuration."""
            if not self.zones:
                QMessageBox.warning(self, "No Zones", "Please draw at least one ROI zone.")
                return
            
            # Emit signal
            self.roi_saved.emit(self.zones)
            
            logger.info(f"ROI saved: {len(self.zones)} zones")
            self.close()


# Educational example (non-GUI)
if __name__ == "__main__":
    print("=" * 60)
    print("ROI Overlay - Educational Research")
    print("=" * 60)
    print()
    
    print("ROI Overlay Window:")
    print("  - Transparent fullscreen overlay")
    print("  - Draw rectangles by dragging mouse")
    print("  - Label zones (hero cards, pot, buttons, etc.)")
    print("  - Save configuration")
    print()
    
    print("Controls:")
    print("  - Left click + drag: Draw zone")
    print("  - ESC: Cancel")
    print("  - ENTER: Save")
    print("  - DELETE: Remove last zone")
    print()
    
    print("Standard zones:")
    if PYQT_AVAILABLE:
        for i, zone in enumerate(ROIOverlay.ZONE_TEMPLATES[:10], 1):
            print(f"  {i}. {zone}")
        print("  ... and more")
    print()
    
    print("=" * 60)
    print("ROI overlay demonstration complete")
    print("=" * 60)
