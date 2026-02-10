"""
Settings Dialog - Launcher Application (Roadmap6 Phase 5).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Global and per-bot settings
- Strategy presets
- Real-time parameter adjustment
"""

import logging
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
        QPushButton, QComboBox, QGroupBox, QTabWidget, QWidget,
        QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.bot_settings import BotSettings, StrategyPreset

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class SettingsDialog(QDialog):
        """
        Bot settings configuration dialog.
        
        Features:
        - Strategy preset selection
        - Individual parameter controls
        - Global and per-bot modes
        - Real-time validation
        
        ⚠️ EDUCATIONAL NOTE:
            Configures bot behavior for coordinated operation.
        
        Signals:
            settings_saved: Emitted when settings are saved
        """
        
        settings_saved = pyqtSignal(BotSettings)
        
        def __init__(
            self,
            parent=None,
            settings: Optional[BotSettings] = None,
            title: str = "Bot Settings"
        ):
            """
            Initialize settings dialog.
            
            Args:
                parent: Parent widget
                settings: Existing settings (if editing)
                title: Dialog title
            """
            super().__init__(parent)
            
            self.settings = settings or BotSettings()
            
            self.setWindowTitle(title)
            self.setModal(True)
            self.setMinimumWidth(600)
            
            self._setup_ui()
            self._load_settings()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Warning banner
            warning = QLabel(
                "⚠️ COLLUSION SETTINGS - Educational Research Only"
            )
            warning.setStyleSheet(
                "background-color: #cc3333; color: white; "
                "font-weight: bold; padding: 8px; border-radius: 3px;"
            )
            warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(warning)
            
            # Preset selector
            preset_group = QGroupBox("Strategy Preset")
            preset_layout = QHBoxLayout()
            
            preset_layout.addWidget(QLabel("Preset:"))
            
            self.preset_combo = QComboBox()
            self.preset_combo.addItems([
                "Conservative",
                "Balanced",
                "Aggressive",
                "GodMode",
                "Custom"
            ])
            self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
            preset_layout.addWidget(self.preset_combo)
            
            preset_layout.addStretch()
            
            preset_group.setLayout(preset_layout)
            layout.addWidget(preset_group)
            
            # Parameters
            params_group = QGroupBox("Parameters")
            params_layout = QFormLayout()
            
            # Aggression level (1-10)
            self.aggression_spin = QSpinBox()
            self.aggression_spin.setRange(1, 10)
            self.aggression_spin.setValue(5)
            self.aggression_spin.valueChanged.connect(self._on_custom_change)
            params_layout.addRow("Aggression Level:", self.aggression_spin)
            
            # Equity threshold (0-100%)
            equity_layout = QHBoxLayout()
            self.equity_spin = QDoubleSpinBox()
            self.equity_spin.setRange(0.0, 1.0)
            self.equity_spin.setSingleStep(0.05)
            self.equity_spin.setDecimals(2)
            self.equity_spin.setValue(0.65)
            self.equity_spin.valueChanged.connect(self._on_custom_change)
            equity_layout.addWidget(self.equity_spin)
            equity_layout.addWidget(QLabel("(65% = aggressive)"))
            equity_layout.addStretch()
            params_layout.addRow("Equity Threshold:", equity_layout)
            
            # Max bet multiplier
            self.bet_mult_spin = QDoubleSpinBox()
            self.bet_mult_spin.setRange(1.0, 10.0)
            self.bet_mult_spin.setSingleStep(0.5)
            self.bet_mult_spin.setDecimals(1)
            self.bet_mult_spin.setValue(3.0)
            self.bet_mult_spin.valueChanged.connect(self._on_custom_change)
            params_layout.addRow("Max Bet Multiplier:", self.bet_mult_spin)
            
            # Delay range
            delay_layout = QHBoxLayout()
            self.delay_min_spin = QDoubleSpinBox()
            self.delay_min_spin.setRange(0.1, 5.0)
            self.delay_min_spin.setSingleStep(0.1)
            self.delay_min_spin.setDecimals(1)
            self.delay_min_spin.setValue(0.4)
            self.delay_min_spin.valueChanged.connect(self._on_custom_change)
            delay_layout.addWidget(self.delay_min_spin)
            
            delay_layout.addWidget(QLabel(" - "))
            
            self.delay_max_spin = QDoubleSpinBox()
            self.delay_max_spin.setRange(0.1, 10.0)
            self.delay_max_spin.setSingleStep(0.1)
            self.delay_max_spin.setDecimals(1)
            self.delay_max_spin.setValue(3.5)
            self.delay_max_spin.valueChanged.connect(self._on_custom_change)
            delay_layout.addWidget(self.delay_max_spin)
            
            delay_layout.addWidget(QLabel("seconds"))
            delay_layout.addStretch()
            params_layout.addRow("Action Delay:", delay_layout)
            
            # Mouse curve intensity (0-10)
            self.mouse_curve_spin = QSpinBox()
            self.mouse_curve_spin.setRange(0, 10)
            self.mouse_curve_spin.setValue(5)
            self.mouse_curve_spin.valueChanged.connect(self._on_custom_change)
            params_layout.addRow("Mouse Curve:", self.mouse_curve_spin)
            
            # Max session time
            self.session_time_spin = QSpinBox()
            self.session_time_spin.setRange(10, 600)
            self.session_time_spin.setSingleStep(10)
            self.session_time_spin.setValue(120)
            self.session_time_spin.setSuffix(" min")
            self.session_time_spin.valueChanged.connect(self._on_custom_change)
            params_layout.addRow("Max Session Time:", self.session_time_spin)
            
            params_group.setLayout(params_layout)
            layout.addWidget(params_group)
            
            # Advanced options
            advanced_group = QGroupBox("Advanced Options")
            advanced_layout = QVBoxLayout()
            
            self.auto_rejoin_check = QCheckBox("Auto-rejoin after disconnect")
            self.auto_rejoin_check.stateChanged.connect(self._on_custom_change)
            advanced_layout.addWidget(self.auto_rejoin_check)
            
            self.manipulation_check = QCheckBox("Enable 3vs1 manipulation (UNETHICAL)")
            self.manipulation_check.setStyleSheet("color: #ff6666;")
            self.manipulation_check.stateChanged.connect(self._on_custom_change)
            advanced_layout.addWidget(self.manipulation_check)
            
            self.collusion_check = QCheckBox("Enable card sharing (ILLEGAL)")
            self.collusion_check.setStyleSheet("color: #ff3333; font-weight: bold;")
            self.collusion_check.stateChanged.connect(self._on_custom_change)
            advanced_layout.addWidget(self.collusion_check)
            
            advanced_group.setLayout(advanced_layout)
            layout.addWidget(advanced_group)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(self._on_save)
            btn_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
        
        def _load_settings(self):
            """Load settings into UI."""
            # Preset
            preset_map = {
                StrategyPreset.CONSERVATIVE: "Conservative",
                StrategyPreset.BALANCED: "Balanced",
                StrategyPreset.AGGRESSIVE: "Aggressive",
                StrategyPreset.GODMODE: "GodMode",
                StrategyPreset.CUSTOM: "Custom"
            }
            self.preset_combo.setCurrentText(preset_map.get(self.settings.preset, "Balanced"))
            
            # Parameters
            self.aggression_spin.setValue(self.settings.aggression_level)
            self.equity_spin.setValue(self.settings.equity_threshold)
            self.bet_mult_spin.setValue(self.settings.max_bet_multiplier)
            self.delay_min_spin.setValue(self.settings.delay_min)
            self.delay_max_spin.setValue(self.settings.delay_max)
            self.mouse_curve_spin.setValue(self.settings.mouse_curve_intensity)
            self.session_time_spin.setValue(self.settings.max_session_time)
            
            # Advanced
            self.auto_rejoin_check.setChecked(self.settings.auto_rejoin)
            self.manipulation_check.setChecked(self.settings.enable_manipulation)
            self.collusion_check.setChecked(self.settings.enable_collusion)
        
        def _on_preset_changed(self, preset_name: str):
            """Handle preset change."""
            preset_map = {
                "Conservative": StrategyPreset.CONSERVATIVE,
                "Balanced": StrategyPreset.BALANCED,
                "Aggressive": StrategyPreset.AGGRESSIVE,
                "GodMode": StrategyPreset.GODMODE,
                "Custom": StrategyPreset.CUSTOM
            }
            
            preset = preset_map.get(preset_name, StrategyPreset.BALANCED)
            
            if preset != StrategyPreset.CUSTOM:
                # Load preset
                self.settings = BotSettings.from_preset(preset)
                self._load_settings()
        
        def _on_custom_change(self):
            """Handle custom parameter change."""
            # Switch to custom preset
            self.preset_combo.setCurrentText("Custom")
        
        def _on_save(self):
            """Save settings."""
            # Show warning if dangerous settings enabled
            if self.manipulation_check.isChecked() or self.collusion_check.isChecked():
                reply = QMessageBox.critical(
                    self,
                    "CRITICAL WARNING",
                    "You are enabling COLLUSION and/or MANIPULATION.\n\n"
                    "This is ILLEGAL in real poker.\n"
                    "EXTREMELY UNETHICAL.\n\n"
                    "Continue only for educational research.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Create settings from UI
            preset_map = {
                "Conservative": StrategyPreset.CONSERVATIVE,
                "Balanced": StrategyPreset.BALANCED,
                "Aggressive": StrategyPreset.AGGRESSIVE,
                "GodMode": StrategyPreset.GODMODE,
                "Custom": StrategyPreset.CUSTOM
            }
            
            self.settings = BotSettings(
                preset=preset_map.get(self.preset_combo.currentText(), StrategyPreset.CUSTOM),
                aggression_level=self.aggression_spin.value(),
                equity_threshold=self.equity_spin.value(),
                max_bet_multiplier=self.bet_mult_spin.value(),
                delay_min=self.delay_min_spin.value(),
                delay_max=self.delay_max_spin.value(),
                mouse_curve_intensity=self.mouse_curve_spin.value(),
                max_session_time=self.session_time_spin.value(),
                auto_rejoin=self.auto_rejoin_check.isChecked(),
                enable_manipulation=self.manipulation_check.isChecked(),
                enable_collusion=self.collusion_check.isChecked()
            )
            
            # Emit signal
            self.settings_saved.emit(self.settings)
            
            logger.info(f"Settings saved: {self.settings.preset.value}")
            self.accept()


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Settings Dialog - Educational Research")
    print("=" * 60)
    print()
    
    print("Settings Dialog (PyQt6):")
    print()
    print("  Preset Selector:")
    print("    - Conservative (safe, high threshold)")
    print("    - Balanced (default)")
    print("    - Aggressive (low threshold, fast)")
    print("    - GodMode (maximum aggression, collusion enabled)")
    print("    - Custom (manual configuration)")
    print()
    print("  Parameters:")
    print("    - Aggression Level: SpinBox (1-10)")
    print("    - Equity Threshold: DoubleSpinBox (0.0-1.0)")
    print("    - Max Bet Multiplier: DoubleSpinBox (1.0-10.0)")
    print("    - Action Delay: Min/Max DoubleSpinBox (0.1-10.0s)")
    print("    - Mouse Curve: SpinBox (0-10)")
    print("    - Max Session Time: SpinBox (10-600 min)")
    print()
    print("  Advanced Options:")
    print("    - Auto-rejoin after disconnect (CheckBox)")
    print("    - Enable 3vs1 manipulation (CheckBox, red)")
    print("    - Enable card sharing (CheckBox, bold red)")
    print()
    print("  Validation:")
    print("    - Critical warning if collusion enabled")
    print("    - Confirmation dialog required")
    print("    - Auto-switch to Custom on parameter change")
    print()
    print("=" * 60)
    print("Settings dialog demonstration complete")
    print("=" * 60)
