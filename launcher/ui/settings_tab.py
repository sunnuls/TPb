"""
Settings Tab — persistent settings panel embedded in the main window.

Replicates and extends SettingsDialog functionality as a full QWidget tab,
so the user never has to open a separate dialog for global settings.

Signals
-------
settings_changed(BotSettings):  emitted on any change (auto-save ready)
"""

import logging
from typing import Optional

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QButtonGroup, QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox,
        QHBoxLayout, QLabel, QMessageBox, QPushButton, QRadioButton,
        QScrollArea, QSlider, QSpinBox, QVBoxLayout,
        QWidget, QComboBox, QFrame,
    )
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.bot_settings import BotSettings, StrategyPreset
from launcher.ui.theme import COLORS

logger = logging.getLogger(__name__)

_PRESET_LABELS = {
    StrategyPreset.CONSERVATIVE: "Conservative",
    StrategyPreset.BALANCED:     "Balanced",
    StrategyPreset.AGGRESSIVE:   "Aggressive",
    StrategyPreset.GODMODE:      "GodMode",
    StrategyPreset.CUSTOM:       "Custom",
}
_LABEL_TO_PRESET = {v: k for k, v in _PRESET_LABELS.items()}


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {COLORS['accent_blue']}; "
        f"font-size: 10pt; font-weight: bold; "
        f"border-bottom: 1px solid {COLORS['border']}; "
        f"padding-bottom: 4px; margin-top: 8px;"
    )
    return lbl


def _make_slider(min_val: int, max_val: int, val: int) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(min_val, max_val)
    s.setValue(val)
    s.setFixedHeight(24)
    return s


if PYQT_AVAILABLE:
    class SettingsTab(QWidget):
        """
        Embedded settings panel.

        Groups
        ------
        1. Execution Mode  (DRY-RUN / LIVE toggle — controls SafetyFramework)
        2. Strategy Preset
        3. Aggression & Timing
        4. Collusion / HIVE
        5. Auto-Seating
        6. Safety limits
        """

        settings_changed  = pyqtSignal(BotSettings)
        # Emitted when execution mode changes: True = LIVE, False = DRY-RUN
        live_mode_changed = pyqtSignal(bool)

        def __init__(
            self,
            parent: Optional[QWidget] = None,
            settings: Optional[BotSettings] = None,
        ) -> None:
            super().__init__(parent)
            self._settings = settings or BotSettings()
            self._block_signals = False
            self._setup_ui()
            self._load(self._settings)

        # ── Public API ────────────────────────────────────────────────────────

        def get_settings(self) -> BotSettings:
            return self._settings

        def load_settings(self, settings: BotSettings) -> None:
            self._settings = settings
            self._block_signals = True
            self._load(settings)
            self._block_signals = False

        # ── UI setup ──────────────────────────────────────────────────────────

        def _setup_ui(self) -> None:
            # Use a scroll area so the tab doesn't overflow on small windows
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)

            container = QWidget()
            scroll.setWidget(container)

            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(scroll)

            root = QVBoxLayout(container)
            root.setContentsMargins(16, 12, 16, 16)
            root.setSpacing(10)

            # Header
            title = QLabel("Global Bot Settings")
            title.setProperty("class", "header")
            root.addWidget(title)

            sub = QLabel(
                "Changes apply to all newly-started bots. "
                "Running bots are not affected until restarted."
            )
            sub.setProperty("class", "subheader")
            sub.setWordWrap(True)
            root.addWidget(sub)

            # ── 0. Execution Mode ─────────────────────────────────────────────
            root.addWidget(self._build_execution_mode_group())

            # ── 1. Preset ─────────────────────────────────────────────────────
            root.addWidget(self._build_preset_group())

            # ── 2. Strategy params ────────────────────────────────────────────
            root.addWidget(self._build_strategy_group())

            # ── 3. Timing ─────────────────────────────────────────────────────
            root.addWidget(self._build_timing_group())

            # ── 4. HIVE / Collusion ───────────────────────────────────────────
            root.addWidget(self._build_hive_group())

            # ── 5. Auto-seating ───────────────────────────────────────────────
            root.addWidget(self._build_autoseat_group())

            # ── 6. Safety ─────────────────────────────────────────────────────
            root.addWidget(self._build_safety_group())

            # ── Bottom buttons ────────────────────────────────────────────────
            root.addLayout(self._build_bottom_buttons())

            root.addStretch()

        # ── Group builders ────────────────────────────────────────────────────

        def _build_execution_mode_group(self) -> QGroupBox:
            """Top-level DRY-RUN / LIVE execution mode switcher."""
            group = QGroupBox("Execution Mode")
            group.setStyleSheet(
                "QGroupBox { border: 2px solid #c0392b; border-radius: 6px;"
                " font-weight: bold; padding-top: 8px; }"
                "QGroupBox::title { color: #e74c3c; }"
            )
            layout = QVBoxLayout(group)

            # Warning banner
            warn = QLabel(
                "LIVE mode sends real mouse clicks / ADB taps to the poker client.\n"
                "Only enable if you accept full responsibility for the session."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "background:#1a2030; color:#c8d0e0; border-radius:4px;"
                " padding:8px; font-size:9pt;"
            )
            layout.addWidget(warn)

            # Radio buttons
            self._mode_btn_group = QButtonGroup(self)

            self.dry_run_radio = QRadioButton(
                "🔵  DRY-RUN  —  simulate only, no real clicks (safe)"
            )
            self.dry_run_radio.setChecked(True)
            self.dry_run_radio.setStyleSheet("color: #6ab4ff; font-weight: bold;")
            self._mode_btn_group.addButton(self.dry_run_radio, 0)
            layout.addWidget(self.dry_run_radio)

            self.live_radio = QRadioButton(
                "🔴  LIVE  —  real mouse/keyboard input to CoinPoker"
            )
            self.live_radio.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            self._mode_btn_group.addButton(self.live_radio, 1)
            layout.addWidget(self.live_radio)

            # Current mode indicator
            self._mode_status_label = QLabel("Current: DRY-RUN  (bots safe to run)")
            self._mode_status_label.setStyleSheet(
                "color: #6ab4ff; font-size: 9pt; padding: 4px;"
            )
            layout.addWidget(self._mode_status_label)

            # Apply button
            apply_mode_btn = QPushButton("Apply Mode Change")
            apply_mode_btn.setMinimumWidth(160)
            apply_mode_btn.clicked.connect(self._on_apply_mode)
            layout.addWidget(apply_mode_btn)

            return group

        def _build_preset_group(self) -> QGroupBox:
            group = QGroupBox("Strategy Preset")
            layout = QVBoxLayout(group)

            row = QHBoxLayout()
            row.addWidget(QLabel("Quick Preset:"))

            self.preset_combo = QComboBox()
            self.preset_combo.setMinimumWidth(180)
            for label in _LABEL_TO_PRESET:
                self.preset_combo.addItem(label)
            self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
            row.addWidget(self.preset_combo)

            row.addStretch()

            self.preset_desc_label = QLabel()
            self.preset_desc_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-style: italic;"
            )
            self.preset_desc_label.setWordWrap(True)
            row.addWidget(self.preset_desc_label)

            layout.addLayout(row)
            return group

        def _build_strategy_group(self) -> QGroupBox:
            group = QGroupBox("Strategy Parameters")
            form = QFormLayout(group)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(10)

            # Aggression (1–10) with live label
            agg_row = QHBoxLayout()
            self.aggression_slider = _make_slider(1, 10, 5)
            self.aggression_slider.valueChanged.connect(self._on_param_changed)
            self.agg_value_label = QLabel("5")
            self.agg_value_label.setFixedWidth(24)
            self.agg_value_label.setStyleSheet(
                f"color: {COLORS['accent_orange']}; font-weight: bold;"
            )
            self.aggression_slider.valueChanged.connect(
                lambda v: self.agg_value_label.setText(str(v))
            )
            agg_row.addWidget(self.aggression_slider)
            agg_row.addWidget(self.agg_value_label)
            form.addRow("Aggression (1–10):", agg_row)

            # Equity threshold (40–95 %)
            eq_row = QHBoxLayout()
            self.equity_slider = _make_slider(40, 95, 65)
            self.equity_slider.valueChanged.connect(self._on_param_changed)
            self.equity_value_label = QLabel("65 %")
            self.equity_value_label.setFixedWidth(44)
            self.equity_value_label.setStyleSheet(
                f"color: {COLORS['accent_blue']}; font-weight: bold;"
            )
            self.equity_slider.valueChanged.connect(
                lambda v: self.equity_value_label.setText(f"{v} %")
            )
            eq_row.addWidget(self.equity_slider)
            eq_row.addWidget(self.equity_value_label)
            form.addRow("Equity Threshold:", eq_row)

            # Max bet multiplier
            self.bet_mult_spin = QDoubleSpinBox()
            self.bet_mult_spin.setRange(1.0, 10.0)
            self.bet_mult_spin.setSingleStep(0.5)
            self.bet_mult_spin.setDecimals(1)
            self.bet_mult_spin.setValue(3.0)
            self.bet_mult_spin.valueChanged.connect(self._on_param_changed)
            form.addRow("Max Bet Multiplier:", self.bet_mult_spin)

            # Mouse curve
            mouse_row = QHBoxLayout()
            self.mouse_curve_slider = _make_slider(0, 10, 5)
            self.mouse_curve_slider.valueChanged.connect(self._on_param_changed)
            self.mouse_value_label = QLabel("5")
            self.mouse_value_label.setFixedWidth(24)
            self.mouse_value_label.setStyleSheet(
                f"color: {COLORS['text_secondary']};"
            )
            self.mouse_curve_slider.valueChanged.connect(
                lambda v: self.mouse_value_label.setText(str(v))
            )
            mouse_row.addWidget(self.mouse_curve_slider)
            mouse_row.addWidget(self.mouse_value_label)
            form.addRow("Mouse Curve (0 = linear):", mouse_row)

            return group

        def _build_timing_group(self) -> QGroupBox:
            group = QGroupBox("Timing / Human-like Delays")
            form = QFormLayout(group)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(10)

            # Delay min
            self.delay_min_spin = QDoubleSpinBox()
            self.delay_min_spin.setRange(0.1, 5.0)
            self.delay_min_spin.setSingleStep(0.1)
            self.delay_min_spin.setDecimals(1)
            self.delay_min_spin.setValue(0.4)
            self.delay_min_spin.setSuffix(" s")
            self.delay_min_spin.valueChanged.connect(self._on_param_changed)
            form.addRow("Action Delay Min:", self.delay_min_spin)

            # Delay max
            self.delay_max_spin = QDoubleSpinBox()
            self.delay_max_spin.setRange(0.1, 10.0)
            self.delay_max_spin.setSingleStep(0.1)
            self.delay_max_spin.setDecimals(1)
            self.delay_max_spin.setValue(3.5)
            self.delay_max_spin.setSuffix(" s")
            self.delay_max_spin.valueChanged.connect(self._on_param_changed)
            form.addRow("Action Delay Max:", self.delay_max_spin)

            # Session time
            self.session_time_spin = QSpinBox()
            self.session_time_spin.setRange(10, 600)
            self.session_time_spin.setSingleStep(10)
            self.session_time_spin.setValue(120)
            self.session_time_spin.setSuffix(" min")
            self.session_time_spin.valueChanged.connect(self._on_param_changed)
            form.addRow("Max Session Time:", self.session_time_spin)

            return group

        def _build_hive_group(self) -> QGroupBox:
            group = QGroupBox("HIVE / Collusion Settings")
            group.setStyleSheet(
                f"QGroupBox::title {{ color: {COLORS['accent_purple']}; }}"
            )
            layout = QVBoxLayout(group)
            layout.setSpacing(10)

            warning = QLabel(
                "Team coordination settings:\n"
                "card sharing and multi-bot strategies."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet(
                f"color: {COLORS['text_secondary']}; "
                f"background-color: {COLORS['bg_secondary']}; "
                f"border: 1px solid {COLORS['border']}; "
                f"border-radius: 4px; padding: 8px;"
            )
            layout.addWidget(warning)

            self.collusion_check = QCheckBox("Enable card sharing (team mode)")
            self.collusion_check.setStyleSheet(
                f"color: {COLORS['text_primary']}; font-weight: bold;"
            )
            self.collusion_check.stateChanged.connect(self._on_collusion_toggled)
            layout.addWidget(self.collusion_check)

            self.manipulation_check = QCheckBox("Enable 3vs1 team strategies")
            self.manipulation_check.setStyleSheet(
                f"color: {COLORS['accent_red']};"
            )
            self.manipulation_check.stateChanged.connect(self._on_param_changed)
            layout.addWidget(self.manipulation_check)

            # HIVE team size
            team_row = QHBoxLayout()
            team_row.addWidget(QLabel("HIVE team size:"))
            self.team_size_spin = QSpinBox()
            self.team_size_spin.setRange(2, 6)
            self.team_size_spin.setValue(3)
            self.team_size_spin.setMaximumWidth(70)
            self.team_size_spin.valueChanged.connect(self._on_param_changed)
            team_row.addWidget(self.team_size_spin)
            team_row.addWidget(
                QLabel("bots (default 3 for 3vs1 strategy)"),
            )
            team_row.addStretch()
            layout.addLayout(team_row)

            return group

        def _build_autoseat_group(self) -> QGroupBox:
            group = QGroupBox("Auto-Seating / Lobby Scanner")
            form = QFormLayout(group)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(10)

            # Min / max players at target table
            player_row = QHBoxLayout()
            self.min_players_spin = QSpinBox()
            self.min_players_spin.setRange(1, 9)
            self.min_players_spin.setValue(1)
            self.min_players_spin.setMaximumWidth(60)
            player_row.addWidget(self.min_players_spin)
            player_row.addWidget(QLabel("–"))
            self.max_players_spin = QSpinBox()
            self.max_players_spin.setRange(1, 9)
            self.max_players_spin.setValue(3)
            self.max_players_spin.setMaximumWidth(60)
            player_row.addWidget(self.max_players_spin)
            player_row.addWidget(QLabel("players at table"))
            player_row.addStretch()
            form.addRow("Target Player Range:", player_row)

            self.auto_join_check = QCheckBox("Auto-join tables automatically")
            self.auto_join_check.setChecked(True)
            form.addRow("", self.auto_join_check)

            self.auto_rejoin_check = QCheckBox("Auto-rejoin after disconnect")
            self.auto_rejoin_check.setChecked(True)
            form.addRow("", self.auto_rejoin_check)

            return group

        def _build_safety_group(self) -> QGroupBox:
            group = QGroupBox("Safety Limits")
            layout = QVBoxLayout(group)

            self.auto_stop_on_error_check = QCheckBox(
                "Auto-stop bot on repeated vision errors"
            )
            self.auto_stop_on_error_check.setChecked(True)
            layout.addWidget(self.auto_stop_on_error_check)

            # Max vision errors before auto-stop
            err_row = QHBoxLayout()
            err_row.addWidget(QLabel("Max vision errors before stop:"))
            self.max_vision_errors_spin = QSpinBox()
            self.max_vision_errors_spin.setRange(1, 50)
            self.max_vision_errors_spin.setValue(5)
            self.max_vision_errors_spin.setMaximumWidth(70)
            err_row.addWidget(self.max_vision_errors_spin)
            err_row.addStretch()
            layout.addLayout(err_row)

            # Max hands per session
            hands_row = QHBoxLayout()
            hands_row.addWidget(QLabel("Max hands per session:"))
            self.max_hands_spin = QSpinBox()
            self.max_hands_spin.setRange(1, 5000)
            self.max_hands_spin.setValue(500)
            self.max_hands_spin.setMaximumWidth(80)
            hands_row.addWidget(self.max_hands_spin)
            hands_row.addStretch()
            layout.addLayout(hands_row)

            # Max session time
            time_row = QHBoxLayout()
            time_row.addWidget(QLabel("Max session time (min):"))
            self.max_session_min_spin = QSpinBox()
            self.max_session_min_spin.setRange(5, 480)
            self.max_session_min_spin.setValue(30)
            self.max_session_min_spin.setMaximumWidth(80)
            time_row.addWidget(self.max_session_min_spin)
            time_row.addStretch()
            layout.addLayout(time_row)

            return group

        def _build_bottom_buttons(self) -> QHBoxLayout:
            row = QHBoxLayout()

            apply_btn = QPushButton("Apply Settings")
            apply_btn.setProperty("class", "primary")
            apply_btn.setMinimumWidth(140)
            apply_btn.clicked.connect(self._on_apply)
            row.addWidget(apply_btn)

            reset_btn = QPushButton("Reset to Defaults")
            reset_btn.clicked.connect(self._on_reset)
            row.addWidget(reset_btn)

            row.addStretch()

            self.save_status_label = QLabel("")
            self.save_status_label.setStyleSheet(
                f"color: {COLORS['accent_green']}; font-style: italic;"
            )
            row.addWidget(self.save_status_label)

            return row

        # ── Load / save ───────────────────────────────────────────────────────

        def _load(self, settings: BotSettings) -> None:
            """Populate controls from a BotSettings instance."""
            # Preset
            preset_label = _PRESET_LABELS.get(settings.preset, "Custom")
            idx = self.preset_combo.findText(preset_label)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)

            # Strategy
            self.aggression_slider.setValue(settings.aggression_level)
            self.equity_slider.setValue(int(settings.equity_threshold * 100))
            self.bet_mult_spin.setValue(settings.max_bet_multiplier)
            self.mouse_curve_slider.setValue(settings.mouse_curve_intensity)

            # Timing
            self.delay_min_spin.setValue(settings.delay_min)
            self.delay_max_spin.setValue(settings.delay_max)
            self.session_time_spin.setValue(settings.max_session_time)

            # HIVE
            self.collusion_check.setChecked(settings.enable_collusion)
            self.manipulation_check.setChecked(settings.enable_manipulation)

            # Auto-seating
            self.auto_rejoin_check.setChecked(settings.auto_rejoin)

            self._update_preset_desc()

        def _collect(self) -> BotSettings:
            """Collect settings from controls into a BotSettings instance."""
            preset_label = self.preset_combo.currentText()
            preset = _LABEL_TO_PRESET.get(preset_label, StrategyPreset.CUSTOM)

            return BotSettings(
                preset=preset,
                aggression_level=self.aggression_slider.value(),
                equity_threshold=self.equity_slider.value() / 100.0,
                max_bet_multiplier=self.bet_mult_spin.value(),
                delay_min=self.delay_min_spin.value(),
                delay_max=self.delay_max_spin.value(),
                mouse_curve_intensity=self.mouse_curve_slider.value(),
                max_session_time=self.session_time_spin.value(),
                auto_rejoin=self.auto_rejoin_check.isChecked(),
                enable_manipulation=self.manipulation_check.isChecked(),
                enable_collusion=self.collusion_check.isChecked(),
            )

        # ── Slots ─────────────────────────────────────────────────────────────

        def _on_preset_changed(self, label: str) -> None:
            if self._block_signals:
                return
            preset = _LABEL_TO_PRESET.get(label)
            if preset and preset != StrategyPreset.CUSTOM:
                new_settings = BotSettings.from_preset(preset)
                self._block_signals = True
                self._load(new_settings)
                self._block_signals = False
            self._update_preset_desc()

        def _on_param_changed(self) -> None:
            if self._block_signals:
                return
            # Switching to "Custom" if user changed parameters manually
            self._block_signals = True
            self.preset_combo.setCurrentText("Custom")
            self._block_signals = False

        def _on_collusion_toggled(self, state: int) -> None:
            if self._block_signals:
                return
            if state == 2:   # Qt.CheckState.Checked
                reply = QMessageBox.question(
                    self,
                    "Enable team card sharing",
                    "Enable shared hole cards between bots in a team?\n\n"
                    "Bots will exchange cards and make coordinated decisions.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self._block_signals = True
                    self.collusion_check.setChecked(False)
                    self._block_signals = False
                    return
            self._on_param_changed()

        def is_live_mode(self) -> bool:
            """Return True if LIVE execution mode is currently active."""
            return self.live_radio.isChecked()

        def _on_apply_mode(self) -> None:
            """Apply the selected execution mode to SafetyFramework."""
            want_live = self.live_radio.isChecked()
            if want_live:
                reply = QMessageBox.critical(
                    self,
                    "⚠️  ENABLE LIVE MODE?",
                    "You are about to switch to LIVE MODE.\n\n"
                    "This will send REAL mouse clicks and keyboard input\n"
                    "to CoinPoker. Real money may be wagered.\n\n"
                    "This is an educational research prototype.\n"
                    "Use ONLY in a controlled sandbox environment.\n\n"
                    "Are you absolutely sure you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.dry_run_radio.setChecked(True)
                    return
            self._apply_mode_to_safety(want_live)

        def _apply_mode_to_safety(self, live: bool) -> None:
            """Propagate mode change to SafetyFramework singleton."""
            try:
                from bridge.safety import SafetyFramework, SafetyMode
                fw = SafetyFramework.get_instance()
                fw.config.mode = SafetyMode.UNSAFE if live else SafetyMode.DRY_RUN
                logger.info("Safety mode changed to %s", fw.config.mode.value.upper())
            except Exception as exc:
                logger.warning("Could not update SafetyFramework mode: %s", exc)

            if live:
                self._mode_status_label.setText(
                    "Current: 🔴  LIVE  —  real actions ENABLED"
                )
                self._mode_status_label.setStyleSheet(
                    "color: #ff6b6b; font-size: 9pt; padding: 4px; font-weight: bold;"
                )
            else:
                self._mode_status_label.setText(
                    "Current: 🔵  DRY-RUN  —  bots safe to run"
                )
                self._mode_status_label.setStyleSheet(
                    "color: #6ab4ff; font-size: 9pt; padding: 4px;"
                )
            self.live_mode_changed.emit(live)

        def _on_apply(self) -> None:
            settings = self._collect()
            self._settings = settings
            self.settings_changed.emit(settings)
            self.save_status_label.setText("✓ Settings applied")

            # Clear the status message after 3 s
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(
                3000,
                lambda: self.save_status_label.setText(""),
            )
            logger.info(
                "Settings applied: preset=%s aggression=%d equity=%.0f%%",
                settings.preset.value,
                settings.aggression_level,
                settings.equity_threshold * 100,
            )

        def _on_reset(self) -> None:
            reply = QMessageBox.question(
                self,
                "Reset Settings",
                "Reset all settings to defaults (Balanced preset)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.load_settings(BotSettings())
                self._on_apply()

        def _update_preset_desc(self) -> None:
            label = self.preset_combo.currentText()
            descriptions = {
                "Conservative": "Safe play — high equity threshold, low aggression.",
                "Balanced":     "Default balanced strategy.",
                "Aggressive":   "Low threshold, fast & aggressive betting.",
                "GodMode":      "Maximum aggression + collusion enabled.",
                "Custom":       "Manually configured parameters.",
            }
            self.preset_desc_label.setText(descriptions.get(label, ""))
