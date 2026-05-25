"""
HIVE Launcher — Dark Theme.

Provides a cohesive dark palette + QSS stylesheet for the whole application.
Apply once at startup via apply_dark_theme(app).
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


# ── Colour tokens ────────────────────────────────────────────────────────────

BG_DARK       = "#1a1d23"   # main background
BG_PANEL      = "#22262e"   # panels / group boxes
BG_WIDGET     = "#2b2f3a"   # inputs, tables, combos
BG_HOVER      = "#333848"   # hover state
BORDER        = "#3d4255"   # borders / dividers

ACCENT_BLUE   = "#4a9eff"   # primary action
ACCENT_PURPLE = "#9d65ff"   # collusion / HIVE
ACCENT_GREEN  = "#3ddc84"   # running / ok
ACCENT_ORANGE = "#ffb347"   # warning
ACCENT_RED    = "#ff4c4c"   # error / emergency

TEXT_PRIMARY   = "#e8eaf0"
TEXT_SECONDARY = "#9098b0"
TEXT_DISABLED  = "#505570"


def _build_palette() -> QPalette:
    """Build a QPalette matching the dark token set."""
    p = QPalette()

    def set_color(role, color, group=None):
        qc = QColor(color)
        if group is None:
            p.setColor(role, qc)
        else:
            p.setColor(group, role, qc)

    # Window / background
    set_color(QPalette.ColorRole.Window,          BG_DARK)
    set_color(QPalette.ColorRole.WindowText,      TEXT_PRIMARY)
    set_color(QPalette.ColorRole.Base,            BG_WIDGET)
    set_color(QPalette.ColorRole.AlternateBase,   BG_PANEL)
    set_color(QPalette.ColorRole.ToolTipBase,     BG_PANEL)
    set_color(QPalette.ColorRole.ToolTipText,     TEXT_PRIMARY)

    # Text
    set_color(QPalette.ColorRole.Text,            TEXT_PRIMARY)
    set_color(QPalette.ColorRole.BrightText,      "#ffffff")
    set_color(QPalette.ColorRole.PlaceholderText, TEXT_DISABLED)

    # Buttons
    set_color(QPalette.ColorRole.Button,          BG_WIDGET)
    set_color(QPalette.ColorRole.ButtonText,      TEXT_PRIMARY)

    # Highlight / selection
    set_color(QPalette.ColorRole.Highlight,       ACCENT_BLUE)
    set_color(QPalette.ColorRole.HighlightedText, "#ffffff")

    # Links
    set_color(QPalette.ColorRole.Link,            ACCENT_BLUE)
    set_color(QPalette.ColorRole.LinkVisited,     ACCENT_PURPLE)

    # Disabled state
    set_color(QPalette.ColorRole.Text,     TEXT_DISABLED, QPalette.ColorGroup.Disabled)
    set_color(QPalette.ColorRole.Button,   BG_PANEL,      QPalette.ColorGroup.Disabled)
    set_color(QPalette.ColorRole.ButtonText, TEXT_DISABLED, QPalette.ColorGroup.Disabled)

    return p


_STYLESHEET = f"""
/* ── Base ─────────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}}

/* ── Main Window ───────────────────────────────────────────────────────────── */
QMainWindow {{
    background-color: {BG_DARK};
}}

/* ── Menu Bar ──────────────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    border-radius: 4px;
}}
QMenu {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT_BLUE};
    color: white;
}}

/* ── Status Bar ────────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
    font-size: 9pt;
}}

/* ── Tab Widget ────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 0 6px 6px 6px;
    background-color: {BG_PANEL};
}}
QTabBar::tab {{
    background-color: {BG_DARK};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    font-size: 10pt;
}}
QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT_BLUE};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

/* ── Group Box ─────────────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    font-size: 10pt;
    color: {TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {ACCENT_BLUE};
}}

/* ── Push Button ───────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 10pt;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT_BLUE};
    color: {ACCENT_BLUE};
}}
QPushButton:pressed {{
    background-color: {ACCENT_BLUE};
    color: white;
}}
QPushButton:disabled {{
    color: {TEXT_DISABLED};
    border-color: {BORDER};
    background-color: {BG_PANEL};
}}

QPushButton[class="primary"] {{
    background-color: {ACCENT_BLUE};
    color: white;
    border: none;
    font-weight: bold;
}}
QPushButton[class="primary"]:hover {{
    background-color: #5faaff;
}}
QPushButton[class="danger"] {{
    background-color: {ACCENT_RED};
    color: white;
    border: none;
    font-weight: bold;
    font-size: 12pt;
}}
QPushButton[class="danger"]:hover {{
    background-color: #ff6b6b;
}}
QPushButton[class="success"] {{
    background-color: {ACCENT_GREEN};
    color: #111;
    border: none;
    font-weight: bold;
}}
QPushButton[class="success"]:hover {{
    background-color: #57e899;
}}
QPushButton[class="hive"] {{
    background-color: {ACCENT_PURPLE};
    color: white;
    border: none;
    font-weight: bold;
}}
QPushButton[class="hive"]:hover {{
    background-color: #b07fff;
}}
QPushButton[class="warning"] {{
    background-color: {ACCENT_ORANGE};
    color: #111;
    border: none;
    font-weight: bold;
}}

/* ── Line Edit / Text Edit ──────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_BLUE};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT_BLUE};
}}

/* ── Combo Box ─────────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 26px;
}}
QComboBox:hover {{
    border-color: {ACCENT_BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {TEXT_SECONDARY};
    margin-right: 4px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_BLUE};
    selection-color: white;
    outline: none;
}}

/* ── Spin Box ──────────────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 26px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT_BLUE};
}}

/* ── Slider ────────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 6px;
    background: {BG_WIDGET};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT_BLUE};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_BLUE};
    border-radius: 3px;
}}

/* ── Table Widget ──────────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {BG_WIDGET};
    alternate-background-color: {BG_PANEL};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: #2e3d5f;
    selection-color: {TEXT_PRIMARY};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:hover {{
    background-color: {BG_HOVER};
}}
QHeaderView::section {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    padding: 6px 8px;
    font-weight: bold;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QHeaderView::section:first {{
    border-top-left-radius: 6px;
}}
QHeaderView::section:last {{
    border-top-right-radius: 6px;
    border-right: none;
}}

/* ── List Widget ───────────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {BG_WIDGET};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QListWidget::item {{
    padding: 5px 8px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT_BLUE};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background-color: {BG_HOVER};
}}

/* ── Scroll Bars ───────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {BG_DARK};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_SECONDARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {BG_DARK};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {TEXT_SECONDARY};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Check Box ─────────────────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_WIDGET};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT_BLUE};
}}

/* ── Radio Button ──────────────────────────────────────────────────────────── */
QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {BG_WIDGET};
}}
QRadioButton::indicator:checked {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
}}

/* ── Progress Bar ──────────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_WIDGET};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
    color: {TEXT_PRIMARY};
    height: 16px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_GREEN};
    border-radius: 4px;
}}

/* ── Label ─────────────────────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
}}
QLabel[class="header"] {{
    font-size: 14pt;
    font-weight: bold;
    color: {ACCENT_BLUE};
}}
QLabel[class="subheader"] {{
    font-size: 11pt;
    color: {TEXT_SECONDARY};
}}
QLabel[class="value"] {{
    font-size: 12pt;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel[class="warning"] {{
    color: {ACCENT_ORANGE};
    font-weight: bold;
}}

/* ── Splitter ──────────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:hover {{
    background-color: {ACCENT_BLUE};
}}

/* ── Tooltip ───────────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 9pt;
}}

/* ── Dialog ────────────────────────────────────────────────────────────────── */
QDialog {{
    background-color: {BG_DARK};
}}

/* ── Message Box ───────────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {BG_DARK};
}}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply the dark theme to a QApplication instance."""
    app.setStyle("Fusion")
    app.setPalette(_build_palette())
    app.setStyleSheet(_STYLESHEET)


def btn_primary(text: str, **kwargs):
    """Helper: create a styled primary button."""
    from PyQt6.QtWidgets import QPushButton
    btn = QPushButton(text, **kwargs)
    btn.setProperty("class", "primary")
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    return btn


def btn_danger(text: str, **kwargs):
    """Helper: create a styled danger button."""
    from PyQt6.QtWidgets import QPushButton
    btn = QPushButton(text, **kwargs)
    btn.setProperty("class", "danger")
    return btn


def btn_success(text: str, **kwargs):
    """Helper: create a styled success (green) button."""
    from PyQt6.QtWidgets import QPushButton
    btn = QPushButton(text, **kwargs)
    btn.setProperty("class", "success")
    return btn


def btn_hive(text: str, **kwargs):
    """Helper: create a styled HIVE (purple) button."""
    from PyQt6.QtWidgets import QPushButton
    btn = QPushButton(text, **kwargs)
    btn.setProperty("class", "hive")
    return btn


# Token exports for use in other UI files
COLORS = {
    "bg_dark": BG_DARK,
    "bg_panel": BG_PANEL,
    "bg_widget": BG_WIDGET,
    "bg_hover": BG_HOVER,
    "border": BORDER,
    "accent_blue": ACCENT_BLUE,
    "accent_purple": ACCENT_PURPLE,
    "accent_green": ACCENT_GREEN,
    "accent_orange": ACCENT_ORANGE,
    "accent_red": ACCENT_RED,
    "text_primary": TEXT_PRIMARY,
    "text_secondary": TEXT_SECONDARY,
    "text_disabled": TEXT_DISABLED,
}
