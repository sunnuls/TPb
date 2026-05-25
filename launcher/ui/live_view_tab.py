"""
Live View Tab — real-time preview of the bot's vision.

Shows a live screenshot of the selected bot's poker window with overlaid:
  - ROI zones (coloured rectangles with labels)
  - Detected anchor markers (from anchor_detector)
  - Card detection boxes (if available)

Uses the existing bridge.screen_capture.ScreenCapture and
launcher.bot_instance auto-ROI data, so nothing extra is needed.
"""

import logging
import time
from typing import List, Optional

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, pyqtSlot
    from PyQt6.QtGui import (
        QColor, QFont, QImage, QPainter, QPen, QPixmap,
    )
    from PyQt6.QtWidgets import (
        QCheckBox, QComboBox, QGroupBox, QHBoxLayout,
        QLabel, QPushButton, QSizePolicy, QSlider,
        QSplitter, QTextEdit, QVBoxLayout, QWidget,
        QProgressBar, QScrollArea,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

try:
    import numpy as np
    import cv2
    CV_AVAILABLE = True
except Exception:
    CV_AVAILABLE = False

try:
    from bridge.screen_capture import ScreenCapture
    HAS_CAPTURE = True
except Exception:
    HAS_CAPTURE = False

from launcher.models.account import Account
from launcher.ui.theme import COLORS

logger = logging.getLogger(__name__)

# Refresh rate options  (ms)
REFRESH_RATES = {
    "Fast (250 ms)":   250,
    "Normal (500 ms)": 500,
    "Slow (1 s)":     1000,
    "Paused":            0,
}

# Zone colour map  (name-prefix → RGB)
ZONE_COLORS = {
    "hero":   (64,  196, 255),   # blue
    "board":  (255, 196,  64),   # yellow
    "pot":    (64,  255, 128),   # green
    "button": (255,  96,  96),   # red
    "stack":  (200, 128, 255),   # purple
    "bet":    (255, 165,   0),   # orange
    "card":   (128, 255, 255),   # cyan
    "dealer": (255, 255,  64),   # bright yellow
}

_DEFAULT_COLOR = (180, 180, 180)


def _zone_color(name: str) -> tuple:
    name_lc = name.lower()
    for prefix, color in ZONE_COLORS.items():
        if name_lc.startswith(prefix):
            return color
    return _DEFAULT_COLOR


class _ROIRefreshWorker(QObject if PYQT_AVAILABLE else object):
    """Background worker: runs auto-ROI detection for Live View refresh."""
    if PYQT_AVAILABLE:
        finished = pyqtSignal(list, list)   # zones, anchors
        error    = pyqtSignal(str)

    def __init__(self, hwnd: int) -> None:
        if PYQT_AVAILABLE:
            super().__init__()
        self._hwnd = hwnd

    @pyqtSlot() if PYQT_AVAILABLE else (lambda f: f)
    def run(self) -> None:
        # NOTE: capture_full_window uses signal.signal() internally which
        # only works in main thread — so we emit finished with empty data
        # and let the caller handle ROI refresh synchronously instead.
        try:
            from bridge.vision.anchor_detector import (
                detect_roi, load_config as load_anchor_config,
            )
            import numpy as np, cv2
            # Use already-captured image passed via self._img if available
            img = getattr(self, "_img", None)
            if img is None:
                self.error.emit("No pre-captured image provided")
                return
            if hasattr(img, "convert"):
                img = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

            cfg = load_anchor_config()
            anchors, zones = detect_roi(img, config=cfg)
            self.finished.emit(
                [z.to_dict() if hasattr(z, "to_dict") else z for z in zones],
                [{"name": a.name, "x": a.x, "y": a.y,
                  "confidence": round(a.confidence, 3)}
                 for a in anchors if hasattr(a, "name")],
            )
        except Exception as exc:
            self.error.emit(str(exc))


if PYQT_AVAILABLE:
    class LiveViewTab(QWidget):
        """
        Live View tab: real-time bot vision preview.

        Features
        --------
        - Captures the selected account's poker window.
        - Draws ROI zones from bot.get_auto_roi_zones() or account.roi_zones.
        - Optionally overlays anchor detection markers.
        - FPS counter + status line.
        - Adjustable refresh rate.
        - "Freeze" mode for inspection.
        - "Refresh ROI" button — re-runs detection in background.
        - Detection quality progress bar (avg anchor confidence).
        """

        open_account_requested = pyqtSignal(str)   # account_id

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)

            self.accounts: List[Account] = []
            self._bot_manager = None
            self._screen_capture: Optional[ScreenCapture] = None
            self._current_pixmap: Optional[QPixmap] = None

            # Timing / stats
            self._frame_count: int = 0
            self._fps_acc_start: float = time.time()
            self._last_fps: float = 0.0
            self._capture_ms: float = 0.0
            self._frozen: bool = False

            # Latest cached ROI data (used when no bot is running)
            self._cached_zones: list = []
            self._cached_anchors: list = []
            self._avg_confidence: float = 0.0

            # ROI refresh thread
            self._roi_thread: Optional[QThread] = None

            # Zoom: None = "Fit to window", float = fixed scale
            self._zoom_factor: Optional[float] = None

            self._setup_ui()
            self._setup_timer()

        # ── Setup ────────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(6)

            # Top toolbar
            toolbar = self._build_toolbar()
            root.addLayout(toolbar)

            # Main area: preview | info panel
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Left: preview
            preview_group = QGroupBox("Live Preview")
            preview_layout = QVBoxLayout(preview_group)
            preview_layout.setContentsMargins(4, 12, 4, 4)

            self.preview_label = QLabel()
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self.preview_label.setMinimumSize(640, 400)
            self.preview_label.setStyleSheet(
                "background-color: #0d0f14; border-radius: 4px;"
            )

            # Scroll area — needed for zoom > 100%
            self._scroll_area = QScrollArea()
            self._scroll_area.setWidget(self.preview_label)
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._scroll_area.setStyleSheet(
                "QScrollArea { background-color: #0d0f14; border: none; }"
            )
            preview_layout.addWidget(self._scroll_area)

            # Status line under preview — create BEFORE _set_no_signal()
            self.status_bar = QLabel("No bot selected")
            self.status_bar.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 2px;"
            )
            preview_layout.addWidget(self.status_bar)

            self._set_no_signal()

            splitter.addWidget(preview_group)

            # Right: info + controls panel
            right_panel = self._build_right_panel()
            splitter.addWidget(right_panel)

            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([800, 280])

            root.addWidget(splitter)

        def _build_toolbar(self) -> QHBoxLayout:
            layout = QHBoxLayout()
            layout.setSpacing(8)

            # Account selector
            layout.addWidget(QLabel("Bot:"))
            self.bot_combo = QComboBox()
            self.bot_combo.setMinimumWidth(180)
            self.bot_combo.setPlaceholderText("Select bot...")
            self.bot_combo.currentIndexChanged.connect(self._on_bot_changed)
            layout.addWidget(self.bot_combo)

            layout.addSpacing(12)

            # Refresh rate
            layout.addWidget(QLabel("Refresh:"))
            self.rate_combo = QComboBox()
            for label in REFRESH_RATES:
                self.rate_combo.addItem(label)
            self.rate_combo.setCurrentIndex(1)  # Normal 500ms
            self.rate_combo.currentTextChanged.connect(self._on_rate_changed)
            self.rate_combo.setMinimumWidth(140)
            layout.addWidget(self.rate_combo)

            layout.addSpacing(12)

            # Overlay options
            self.show_roi_cb = QCheckBox("ROI zones")
            self.show_roi_cb.setChecked(True)
            layout.addWidget(self.show_roi_cb)

            self.show_anchors_cb = QCheckBox("Anchors")
            self.show_anchors_cb.setChecked(True)
            layout.addWidget(self.show_anchors_cb)

            layout.addSpacing(12)

            # Zoom control
            layout.addWidget(QLabel("Zoom:"))
            self.zoom_combo = QComboBox()
            self.zoom_combo.setMaximumWidth(90)
            for label in ("Fit", "50%", "75%", "100%", "150%", "200%"):
                self.zoom_combo.addItem(label)
            self.zoom_combo.setCurrentText("Fit")
            self.zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
            layout.addWidget(self.zoom_combo)

            layout.addStretch()

            # Refresh ROI
            self.refresh_roi_btn = QPushButton("🔄 Refresh ROI")
            self.refresh_roi_btn.setToolTip(
                "Re-run anchor detection for the current window.\n"
                "Updates zone overlay in real-time."
            )
            self.refresh_roi_btn.clicked.connect(self._on_refresh_roi)
            layout.addWidget(self.refresh_roi_btn)

            layout.addSpacing(4)

            # Freeze / Capture buttons
            self.freeze_btn = QPushButton("⏸ Freeze")
            self.freeze_btn.setCheckable(True)
            self.freeze_btn.setMinimumWidth(90)
            self.freeze_btn.toggled.connect(self._on_freeze_toggled)
            layout.addWidget(self.freeze_btn)

            capture_btn = QPushButton("📷 Capture Now")
            capture_btn.clicked.connect(self._capture_once)
            layout.addWidget(capture_btn)

            # FPS
            self.fps_label = QLabel("FPS: --")
            self.fps_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-size: 9pt; margin-left: 8px;"
            )
            layout.addWidget(self.fps_label)

            return layout

        def _build_right_panel(self) -> QWidget:
            panel = QWidget()
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            # ── ROI Zones ────────────────────────────────────────────────────
            zones_group = QGroupBox("Detected Zones")
            zones_layout = QVBoxLayout(zones_group)

            self.zones_label = QLabel("—")
            self.zones_label.setWordWrap(True)
            self.zones_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 4px;"
            )
            self.zones_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            zones_layout.addWidget(self.zones_label)
            layout.addWidget(zones_group)

            # ── Anchor Info ──────────────────────────────────────────────────
            anchor_group = QGroupBox("Anchor Detection")
            anchor_layout = QVBoxLayout(anchor_group)

            self.anchor_label = QLabel("—")
            self.anchor_label.setWordWrap(True)
            self.anchor_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 4px;"
            )
            self.anchor_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            anchor_layout.addWidget(self.anchor_label)
            layout.addWidget(anchor_group)

            # ── Detection Quality ─────────────────────────────────────────────
            quality_group = QGroupBox("Detection Quality")
            quality_layout = QVBoxLayout(quality_group)
            quality_layout.setSpacing(4)

            self.quality_bar = QProgressBar()
            self.quality_bar.setRange(0, 100)
            self.quality_bar.setValue(0)
            self.quality_bar.setFormat("Confidence: %p%")
            self.quality_bar.setTextVisible(True)
            self.quality_bar.setStyleSheet(
                "QProgressBar {"
                "  background-color: #1a1a2e;"
                "  border: 1px solid #333;"
                "  border-radius: 4px;"
                "  text-align: center;"
                "  color: #eee;"
                "  font-size: 9pt;"
                "}"
                "QProgressBar::chunk { background-color: #3ddc84; border-radius: 3px; }"
            )
            self.quality_bar.setMaximumHeight(22)
            quality_layout.addWidget(self.quality_bar)

            self.quality_label = QLabel("No anchors detected")
            self.quality_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 8pt; padding: 2px;"
            )
            quality_layout.addWidget(self.quality_label)
            layout.addWidget(quality_group)

            # ── Capture Info ─────────────────────────────────────────────────
            info_group = QGroupBox("Capture Info")
            info_layout = QVBoxLayout(info_group)

            self.capture_info_label = QLabel("—")
            self.capture_info_label.setWordWrap(True)
            self.capture_info_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 9pt; padding: 4px;"
            )
            info_layout.addWidget(self.capture_info_label)
            layout.addWidget(info_group)

            # ── Action log (recent frames) ────────────────────────────────────
            log_group = QGroupBox("Recent Events")
            log_layout = QVBoxLayout(log_group)

            self.event_log = QTextEdit()
            self.event_log.setReadOnly(True)
            self.event_log.setMaximumHeight(160)
            self.event_log.setStyleSheet(
                f"background-color: {COLORS['bg_dark']}; "
                f"color: {COLORS['text_secondary']}; "
                f"font-family: 'Consolas', monospace; font-size: 8pt; "
                f"border: none;"
            )
            log_layout.addWidget(self.event_log)

            clear_btn = QPushButton("Clear")
            clear_btn.setMaximumWidth(80)
            clear_btn.clicked.connect(self.event_log.clear)
            log_layout.addWidget(clear_btn)
            layout.addWidget(log_group)

            layout.addStretch()
            return panel

        def _setup_timer(self) -> None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._tick)
            rate = REFRESH_RATES[self.rate_combo.currentText()]
            if rate > 0:
                self.timer.start(rate)

        # ── Public API ────────────────────────────────────────────────────────

        def set_accounts(self, accounts: List[Account]) -> None:
            """Update the account list in the combo box."""
            self.accounts = accounts
            current = self.bot_combo.currentData()
            self.bot_combo.blockSignals(True)
            self.bot_combo.clear()
            for acc in accounts:
                self.bot_combo.addItem(acc.nickname, acc.account_id)
            # Restore selection
            if current:
                idx = self.bot_combo.findData(current)
                if idx >= 0:
                    self.bot_combo.setCurrentIndex(idx)
            self.bot_combo.blockSignals(False)

        def set_bot_manager(self, manager) -> None:
            """Attach the BotManager (for accessing auto-ROI zones)."""
            self._bot_manager = manager

        def add_event(self, text: str) -> None:
            """Append a timestamped line to the event log."""
            ts = time.strftime("%H:%M:%S")
            self.event_log.append(f"[{ts}] {text}")
            # Scroll to bottom
            sb = self.event_log.verticalScrollBar()
            sb.setValue(sb.maximum())

        # ── Internal slots ────────────────────────────────────────────────────

        def _on_bot_changed(self, index: int) -> None:
            self._set_no_signal()
            self._current_pixmap = None
            account_id = self.bot_combo.currentData()
            if account_id:
                self.add_event(f"Watching: {self.bot_combo.currentText()}")

        def _on_rate_changed(self, text: str) -> None:
            rate = REFRESH_RATES.get(text, 500)
            self.timer.stop()
            if rate > 0 and not self._frozen:
                self.timer.start(rate)

        def _on_freeze_toggled(self, frozen: bool) -> None:
            self._frozen = frozen
            self.freeze_btn.setText("▶ Resume" if frozen else "⏸ Freeze")
            if frozen:
                self.timer.stop()
                self.add_event("Frozen — inspection mode")
            else:
                rate = REFRESH_RATES.get(self.rate_combo.currentText(), 500)
                if rate > 0:
                    self.timer.start(rate)
                self.add_event("Resumed live capture")

        def _tick(self) -> None:
            """Timer tick — capture + render."""
            self._capture_once()

        def _capture_once(self) -> None:
            """Perform one capture cycle."""
            if self._frozen:
                return

            account = self._get_selected_account()
            if account is None:
                self._set_no_signal("No account selected")
                return

            if not account.window_info.is_captured():
                self._set_no_signal(f"{account.nickname}: window not captured")
                return

            hwnd = account.window_info.hwnd
            if not hwnd:
                self._set_no_signal(f"{account.nickname}: no HWND")
                return

            t0 = time.perf_counter()
            image = self._do_capture(hwnd)
            self._capture_ms = (time.perf_counter() - t0) * 1000

            if image is None:
                self._set_no_signal(f"{account.nickname}: capture failed")
                return

            h, w = image.shape[:2]

            # Get ROI zones — bot first, then account fallback, then cached
            bot_zones = []
            anchor_info = {}
            if self._bot_manager:
                bot = self._bot_manager.get_bot_by_account(account.account_id)
                if bot:
                    bot_zones = bot.get_auto_roi_zones()
                    anchor_info = bot.get_auto_roi_info()

            # Filter false-positive anchors at (0,0) with perfect confidence
            if "anchors" in anchor_info:
                anchor_info["anchors"] = self._clean_anchors(anchor_info["anchors"])

            if not bot_zones:
                # Fallback 1: account.roi_zones (set after Auto-Detect ROI)
                acct_zones = getattr(account, "roi_zones", None)
                if acct_zones:
                    bot_zones = acct_zones
                elif self._cached_zones:
                    # Fallback 2: last successful detection cache
                    bot_zones = self._cached_zones
                    anchor_info = {"anchors": self._cached_anchors}
            else:
                # Update cache on successful bot read
                self._cached_zones   = bot_zones
                self._cached_anchors = self._clean_anchors(
                    anchor_info.get("anchors", [])
                )

            # Draw overlays onto the image copy
            if self.show_roi_cb.isChecked() and bot_zones:
                image = self._draw_zones(image, bot_zones)

            if self.show_anchors_cb.isChecked() and anchor_info.get("anchors"):
                image = self._draw_anchors(image, anchor_info["anchors"])

            # Convert to QPixmap
            pixmap = self._ndarray_to_pixmap(image)
            if pixmap is None:
                return

            self._current_pixmap = pixmap
            self._apply_zoom(pixmap)

            # Update stats
            self._frame_count += 1
            elapsed = time.time() - self._fps_acc_start
            if elapsed >= 1.0:
                self._last_fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_acc_start = time.time()
                self.fps_label.setText(f"FPS: {self._last_fps:.1f}")

            # Update info panels
            self._update_zones_panel(bot_zones)
            self._update_anchor_panel(anchor_info)
            self._update_capture_info(w, h)
            self._update_quality_bar(anchor_info)
            self._update_status_bar(account, w, h, len(bot_zones))

        # ── Capture helpers ───────────────────────────────────────────────────

        def _do_capture(self, hwnd: int):
            """Capture window by HWND and return numpy array (BGR) or None."""
            if not HAS_CAPTURE or not CV_AVAILABLE:
                return None
            try:
                if self._screen_capture is None:
                    self._screen_capture = ScreenCapture()
                img = self._screen_capture.capture_full_window(hwnd)
                if img is None:
                    img = self._screen_capture.capture()
                if img is None:
                    return None
                # Normalise to numpy BGR
                if hasattr(img, "shape"):
                    return img
                if hasattr(img, "convert"):
                    rgb = np.array(img.convert("RGB"))
                    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            except Exception as exc:
                logger.debug("Capture error: %s", exc)
            return None

        # ── Drawing helpers ───────────────────────────────────────────────────

        def _draw_zones(self, image, zones: list):
            """Draw ROI zone rectangles onto image (in-place copy)."""
            img = image.copy()
            for zone in zones:
                if isinstance(zone, dict):
                    name = zone.get("name", "zone")
                    x = int(zone.get("x", 0))
                    y = int(zone.get("y", 0))
                    w = int(zone.get("w", zone.get("width", 50)))
                    h = int(zone.get("h", zone.get("height", 30)))
                else:
                    name = getattr(zone, "name", "zone")
                    x = int(getattr(zone, "x", 0))
                    y = int(getattr(zone, "y", 0))
                    w = int(getattr(zone, "w", getattr(zone, "width", 50)))
                    h = int(getattr(zone, "h", getattr(zone, "height", 30)))

                r, g, b = _zone_color(name)
                color_bgr = (b, g, r)

                # Semi-transparent fill
                overlay = img.copy()
                cv2.rectangle(overlay, (x, y), (x + w, y + h), color_bgr, -1)
                cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

                # Border
                cv2.rectangle(img, (x, y), (x + w, y + h), color_bgr, 2)

                # Label
                cv2.putText(
                    img, name, (x + 3, y + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_bgr, 1,
                    cv2.LINE_AA,
                )
            return img

        def _draw_anchors(self, image, anchors: list):
            """Draw anchor detection markers onto image."""
            img = image.copy()
            for anchor in anchors:
                ax = int(anchor.get("x", 0))
                ay = int(anchor.get("y", 0))
                name = anchor.get("name", "?")
                conf = anchor.get("confidence", 0.0)

                # Cross-hair
                cv2.drawMarker(
                    img, (ax, ay), (0, 255, 0),
                    cv2.MARKER_CROSS, 20, 2,
                )
                # Circle
                cv2.circle(img, (ax, ay), 10, (0, 255, 0), 1)
                # Label with confidence
                label = f"{name} {conf:.2f}"
                cv2.putText(
                    img, label, (ax + 12, ay - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1,
                    cv2.LINE_AA,
                )
            return img

        def _ndarray_to_pixmap(self, image) -> Optional[QPixmap]:
            """Convert BGR numpy array → QPixmap."""
            try:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                q_img = QImage(
                    rgb.data, w, h,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                )
                return QPixmap.fromImage(q_img)
            except Exception as exc:
                logger.debug("Pixmap conversion error: %s", exc)
                return None

        # ── Info panel updates ────────────────────────────────────────────────

        @staticmethod
        def _clean_anchors(anchors: list) -> list:
            """Remove false-positive anchors at (0,0) with suspiciously high confidence.

            Template matching often hits the top-left corner of the image when
            the template doesn't match anywhere. These appear as x=0, y=0 with
            confidence ≥ 0.99. We keep them only if the name suggests they
            genuinely belong to the top-left (none typically do in CoinPoker).
            """
            result = []
            for a in anchors:
                x, y = a.get("x", 0), a.get("y", 0)
                conf = a.get("confidence", 0.0)
                # Suppress zero-position matches with perfect confidence
                if x == 0 and y == 0 and conf >= 0.99:
                    continue
                result.append(a)
            return result

        def _update_zones_panel(self, zones: list) -> None:
            if not zones:
                self.zones_label.setText(
                    '<span style="color: #505570;">No zones detected</span>'
                )
                return

            lines = []
            for z in zones:
                if isinstance(z, dict):
                    name = z.get("name", "?")
                    x, y = z.get("x", 0), z.get("y", 0)
                    w = z.get("w", z.get("width", 0))
                    h = z.get("h", z.get("height", 0))
                else:
                    name = getattr(z, "name", "?")
                    x = getattr(z, "x", 0)
                    y = getattr(z, "y", 0)
                    w = getattr(z, "w", getattr(z, "width", 0))
                    h = getattr(z, "h", getattr(z, "height", 0))
                r, g, b = _zone_color(name)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                lines.append(
                    f'<span style="color:{hex_color};">■</span> '
                    f'{name} ({x},{y}) {w}×{h}'
                )

            self.zones_label.setText(
                f"<b>{len(zones)} zones:</b><br>" + "<br>".join(lines)
            )

        def _update_anchor_panel(self, anchor_info: dict) -> None:
            anchors = anchor_info.get("anchors", [])
            if not anchors:
                last = anchor_info.get("last_refresh", 0)
                if last:
                    ago = time.time() - last
                    self.anchor_label.setText(
                        f'<span style="color: #505570;">No anchors detected<br>'
                        f'Last refresh: {ago:.0f}s ago</span>'
                    )
                else:
                    self.anchor_label.setText(
                        '<span style="color: #505570;">Not detected yet</span>'
                    )
                return

            lines = [f"<b>{len(anchors)} anchors found:</b>"]
            for a in anchors:
                conf = a.get("confidence", 0)
                color = COLORS["accent_green"] if conf > 0.8 else COLORS["accent_orange"]
                lines.append(
                    f'<span style="color:{color};">'
                    f'{a.get("name","?")} @ ({a.get("x",0)}, {a.get("y",0)}) '
                    f'conf={conf:.2f}</span>'
                )
            self.anchor_label.setText("<br>".join(lines))

        def _update_capture_info(self, w: int, h: int) -> None:
            self.capture_info_label.setText(
                f"Resolution: {w} × {h}<br>"
                f"Capture time: {self._capture_ms:.1f} ms<br>"
                f"FPS: {self._last_fps:.1f}"
            )

        def _update_quality_bar(self, anchor_info: dict) -> None:
            """Update the detection quality progress bar from anchor confidence."""
            anchors = anchor_info.get("anchors", [])
            if not anchors:
                self.quality_bar.setValue(0)
                self.quality_bar.setStyleSheet(
                    "QProgressBar { background:#1a1a2e; border:1px solid #333;"
                    " border-radius:4px; text-align:center; color:#888; font-size:9pt; }"
                    "QProgressBar::chunk { background:#444; border-radius:3px; }"
                )
                self.quality_label.setText("No anchors — zones may be inaccurate")
                self._avg_confidence = 0.0
                return

            avg = sum(a.get("confidence", 0.0) for a in anchors) / len(anchors)
            self._avg_confidence = avg
            pct = int(avg * 100)
            self.quality_bar.setValue(pct)

            if avg >= 0.80:
                chunk_color = "#3ddc84"   # green
                status = f"Good  ({len(anchors)} anchors, avg {avg:.0%})"
            elif avg >= 0.55:
                chunk_color = "#f0a500"   # amber
                status = f"Fair  ({len(anchors)} anchors, avg {avg:.0%})"
            else:
                chunk_color = "#e05555"   # red
                status = f"Poor  ({len(anchors)} anchors, avg {avg:.0%})"

            self.quality_bar.setStyleSheet(
                "QProgressBar { background:#1a1a2e; border:1px solid #333;"
                " border-radius:4px; text-align:center; color:#eee; font-size:9pt; }"
                f"QProgressBar::chunk {{ background:{chunk_color}; border-radius:3px; }}"
            )
            self.quality_label.setText(status)

        def _on_refresh_roi(self) -> None:
            """Force re-run of anchor detection synchronously (no thread — signal.signal compat)."""
            if getattr(self, "_roi_refreshing", False):
                self.add_event("ROI refresh already in progress…")
                return

            account = self._get_selected_account()
            if account is None:
                self.add_event("No account selected for ROI refresh")
                return
            if not account.window_info.is_captured() or not account.window_info.hwnd:
                self.add_event(f"{account.nickname}: no HWND — capture window first")
                return

            hwnd = account.window_info.hwnd
            img = self._do_capture(hwnd)
            if img is None:
                self.add_event(f"{account.nickname}: capture failed for ROI refresh")
                return

            self._roi_refreshing = True
            self.refresh_roi_btn.setEnabled(False)
            self.refresh_roi_btn.setText("⏳ Refreshing…")
            self.add_event(f"Refreshing ROI for {account.nickname}…")

            try:
                import numpy as np, cv2 as _cv2
                from bridge.vision.anchor_detector import (
                    detect_roi, load_config as _load_cfg,
                )
                if hasattr(img, "convert"):
                    img = _cv2.cvtColor(np.array(img.convert("RGB")), _cv2.COLOR_RGB2BGR)
                cfg = _load_cfg()
                anchors_raw, zones_raw = detect_roi(img, config=cfg)
                zones = [z.to_dict() if hasattr(z, "to_dict") else z for z in zones_raw]
                anchors = [{"name": a.name, "x": a.x, "y": a.y,
                            "confidence": round(a.confidence, 3)}
                           for a in anchors_raw if hasattr(a, "name")]
                self._on_roi_refresh_done(zones, anchors)
            except Exception as exc:
                self._on_roi_refresh_error(str(exc))
            finally:
                self._roi_refreshing = False
                self._reset_refresh_btn()

        @pyqtSlot(list, list)
        def _on_roi_refresh_done(self, zones: list, anchors: list) -> None:
            anchors = self._clean_anchors(anchors)
            self._cached_zones   = zones
            self._cached_anchors = anchors
            self._update_zones_panel(zones)
            self._update_anchor_panel({"anchors": anchors})
            self._update_quality_bar({"anchors": anchors})
            n = len(zones)
            avg = (sum(a.get("confidence", 0) for a in anchors) / len(anchors)
                   if anchors else 0.0)
            self.add_event(
                f"ROI refresh done: {n} zones, {len(anchors)} anchors "
                f"(avg conf {avg:.0%})"
            )

        @pyqtSlot(str)
        def _on_roi_refresh_error(self, msg: str) -> None:
            self.add_event(f"ROI refresh failed: {msg}")
            logger.warning("Live View ROI refresh error: %s", msg)

        def _reset_refresh_btn(self) -> None:
            self.refresh_roi_btn.setEnabled(True)
            self.refresh_roi_btn.setText("🔄 Refresh ROI")

        # ── Zoom helpers ──────────────────────────────────────────────────────

        def _on_zoom_changed(self, text: str) -> None:
            """Handle zoom combo selection."""
            if text == "Fit":
                self._zoom_factor = None
                self._scroll_area.setWidgetResizable(True)
            else:
                pct = int(text.replace("%", ""))
                self._zoom_factor = pct / 100.0
                self._scroll_area.setWidgetResizable(False)

            # Immediately re-apply to current frame
            if self._current_pixmap:
                self._apply_zoom(self._current_pixmap)

        def _apply_zoom(self, pixmap: QPixmap) -> None:
            """Scale and display pixmap according to current zoom setting."""
            if self._zoom_factor is None:
                # Fit mode — scale to available viewport
                vp = self._scroll_area.viewport().size()
                scaled = pixmap.scaled(
                    vp,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
                self.preview_label.resize(scaled.size())
            else:
                # Fixed zoom
                new_w = int(pixmap.width()  * self._zoom_factor)
                new_h = int(pixmap.height() * self._zoom_factor)
                scaled = pixmap.scaled(
                    new_w, new_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
                self.preview_label.resize(scaled.size())

        def _update_status_bar(
            self, account: Account, w: int, h: int, zone_count: int
        ) -> None:
            nick = account.nickname
            window = account.window_info.window_title or "Unknown"
            self.status_bar.setText(
                f"{nick} | {window} | {w}×{h} | "
                f"{zone_count} zones | {self._last_fps:.1f} fps | "
                f"capture {self._capture_ms:.0f}ms"
            )

        # ── Utilities ──────────────────────────────────────────────────────────

        def _get_selected_account(self) -> Optional[Account]:
            account_id = self.bot_combo.currentData()
            if not account_id:
                return None
            return next(
                (a for a in self.accounts if a.account_id == account_id), None
            )

        def _set_no_signal(self, msg: str = "No signal") -> None:
            """Show a placeholder when no live image is available."""
            self.preview_label.clear()
            self.preview_label.setText(
                f'<span style="color: #505570; font-size: 14pt;">'
                f'📷 {msg}</span>'
            )
            self.status_bar.setText(msg)
            self.fps_label.setText("FPS: --")

        def resizeEvent(self, event) -> None:
            super().resizeEvent(event)
            # Re-apply zoom when window is resized (important for Fit mode)
            if self._current_pixmap:
                self._apply_zoom(self._current_pixmap)
