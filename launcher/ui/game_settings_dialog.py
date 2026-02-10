"""
Game Settings Dialog - Launcher Application (Roadmap6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Select game types (Hold'em, PLO, etc.)
- Configure stake limits
- Set table joining preferences
"""

import logging
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QCheckBox, QSpinBox,
        QComboBox, QGridLayout, QLineEdit, QScrollArea, QWidget
    )
    from PyQt6.QtCore import Qt
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.game_settings import GameType, StakeLevel, GamePreferences, STAKE_PRESETS

logger = logging.getLogger(__name__)


class GameSettingsDialog(QDialog):
    """
    Dialog for configuring game preferences.
    
    ⚠️ EDUCATIONAL NOTE:
        Configures which games and stakes the bot will play.
    """
    
    def __init__(self, parent=None, current_preferences: Optional[GamePreferences] = None):
        """
        Initialize dialog.
        
        Args:
            parent: Parent widget
            current_preferences: Current game preferences (if editing)
        """
        super().__init__(parent)
        
        self.preferences = current_preferences or GamePreferences()
        self.game_checkboxes = {}
        self.stake_checkboxes = {}
        
        self.setWindowTitle("Game Preferences")
        self.setModal(True)
        self.setMinimumSize(600, 700)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Scroll area for all settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Game Types Section
        games_group = self._create_game_types_section()
        scroll_layout.addWidget(games_group)
        
        # Stakes Section
        stakes_group = self._create_stakes_section()
        scroll_layout.addWidget(stakes_group)
        
        # Table Selection Section
        table_group = self._create_table_selection_section()
        scroll_layout.addWidget(table_group)
        
        # Auto-Join Settings
        autojoin_group = self._create_autojoin_section()
        scroll_layout.addWidget(autojoin_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_game_types_section(self) -> QGroupBox:
        """Create game types selection."""
        group = QGroupBox("Game Types")
        layout = QGridLayout(group)
        
        label = QLabel("Select which game types this bot can play:")
        layout.addWidget(label, 0, 0, 1, 3)
        
        row = 1
        col = 0
        for game_type in GameType:
            checkbox = QCheckBox(game_type.value)
            self.game_checkboxes[game_type] = checkbox
            
            layout.addWidget(checkbox, row, col)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        return group
    
    def _create_stakes_section(self) -> QGroupBox:
        """Create stakes selection."""
        group = QGroupBox("Stake Limits")
        layout = QVBoxLayout(group)
        
        # Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Preset:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Custom")
        for preset_name in STAKE_PRESETS.keys():
            self.preset_combo.addItem(preset_name)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        
        layout.addLayout(preset_layout)
        
        # Manual stake input
        stake_layout = QGridLayout()
        
        stake_layout.addWidget(QLabel("Min Stake:"), 0, 0)
        self.min_stake_input = QLineEdit()
        self.min_stake_input.setPlaceholderText("e.g., $0.10/$0.25")
        stake_layout.addWidget(self.min_stake_input, 0, 1)
        
        stake_layout.addWidget(QLabel("Max Stake:"), 1, 0)
        self.max_stake_input = QLineEdit()
        self.max_stake_input.setPlaceholderText("e.g., $1/$2")
        stake_layout.addWidget(self.max_stake_input, 1, 1)
        
        layout.addLayout(stake_layout)
        
        # Stake levels
        levels_label = QLabel("Or select stake levels:")
        layout.addWidget(levels_label)
        
        levels_layout = QHBoxLayout()
        for stake_level in StakeLevel:
            checkbox = QCheckBox(stake_level.value)
            self.stake_checkboxes[stake_level] = checkbox
            levels_layout.addWidget(checkbox)
        levels_layout.addStretch()
        
        layout.addLayout(levels_layout)
        
        return group
    
    def _create_table_selection_section(self) -> QGroupBox:
        """Create table selection preferences."""
        group = QGroupBox("Table Selection")
        layout = QGridLayout(group)
        
        # Player range
        layout.addWidget(QLabel("Min Players:"), 0, 0)
        self.min_players_spin = QSpinBox()
        self.min_players_spin.setRange(1, 9)
        self.min_players_spin.setValue(1)
        layout.addWidget(self.min_players_spin, 0, 1)
        
        layout.addWidget(QLabel("Max Players:"), 1, 0)
        self.max_players_spin = QSpinBox()
        self.max_players_spin.setRange(1, 9)
        self.max_players_spin.setValue(3)
        layout.addWidget(self.max_players_spin, 1, 1)
        
        info_label = QLabel("Tip: For 3vs1 collusion, set Min=1, Max=3")
        info_label.setStyleSheet("color: #00AA00; font-style: italic;")
        layout.addWidget(info_label, 2, 0, 1, 2)
        
        # Table size
        layout.addWidget(QLabel("Preferred Table Size:"), 3, 0)
        self.table_size_combo = QComboBox()
        self.table_size_combo.addItems(["2 (Heads-up)", "6 (6-max)", "9 (Full ring)"])
        self.table_size_combo.setCurrentIndex(1)  # Default to 6-max
        layout.addWidget(self.table_size_combo, 3, 1)
        
        return group
    
    def _create_autojoin_section(self) -> QGroupBox:
        """Create auto-join settings."""
        group = QGroupBox("Auto-Join Settings")
        layout = QVBoxLayout(group)
        
        # Auto-join enabled
        self.autojoin_checkbox = QCheckBox("Enable Auto-Join Tables")
        self.autojoin_checkbox.setChecked(True)
        layout.addWidget(self.autojoin_checkbox)
        
        # Max tables
        max_tables_layout = QHBoxLayout()
        max_tables_layout.addWidget(QLabel("Max Simultaneous Tables:"))
        self.max_tables_spin = QSpinBox()
        self.max_tables_spin.setRange(1, 10)
        self.max_tables_spin.setValue(1)
        max_tables_layout.addWidget(self.max_tables_spin)
        max_tables_layout.addStretch()
        layout.addLayout(max_tables_layout)
        
        # Additional filters
        self.avoid_bots_checkbox = QCheckBox("Avoid tables with only bots")
        self.avoid_bots_checkbox.setChecked(True)
        layout.addWidget(self.avoid_bots_checkbox)
        
        self.prefer_weak_checkbox = QCheckBox("Prefer tables with weak players")
        self.prefer_weak_checkbox.setChecked(True)
        layout.addWidget(self.prefer_weak_checkbox)
        
        return group
    
    def _load_current_settings(self):
        """Load current preferences into UI."""
        # Game types
        for game_type, checkbox in self.game_checkboxes.items():
            checkbox.setChecked(game_type in self.preferences.enabled_games)
        
        # Stakes
        self.min_stake_input.setText(self.preferences.min_stake)
        self.max_stake_input.setText(self.preferences.max_stake)
        
        for stake_level, checkbox in self.stake_checkboxes.items():
            checkbox.setChecked(stake_level in self.preferences.stake_levels)
        
        # Table selection
        self.min_players_spin.setValue(self.preferences.min_players)
        self.max_players_spin.setValue(self.preferences.max_players)
        
        # Table size
        size_map = {2: 0, 6: 1, 9: 2}
        self.table_size_combo.setCurrentIndex(size_map.get(self.preferences.preferred_table_size, 1))
        
        # Auto-join
        self.autojoin_checkbox.setChecked(self.preferences.auto_join_tables)
        self.max_tables_spin.setValue(self.preferences.max_tables)
        self.avoid_bots_checkbox.setChecked(self.preferences.avoid_full_bot_tables)
        self.prefer_weak_checkbox.setChecked(self.preferences.prefer_weak_players)
    
    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection."""
        if preset_name == "Custom":
            return
        
        if preset_name in STAKE_PRESETS:
            preset = STAKE_PRESETS[preset_name]
            self.min_stake_input.setText(preset['min_stake'])
            self.max_stake_input.setText(preset['max_stake'])
            
            # Update checkboxes
            for stake_level, checkbox in self.stake_checkboxes.items():
                checkbox.setChecked(stake_level in preset['levels'])
    
    def get_preferences(self) -> GamePreferences:
        """
        Get configured preferences.
        
        Returns:
            Game preferences
        """
        # Collect enabled games
        enabled_games = [
            game_type for game_type, checkbox in self.game_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        # Collect stake levels
        stake_levels = [
            stake_level for stake_level, checkbox in self.stake_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        # Table size
        size_map = {0: 2, 1: 6, 2: 9}
        table_size = size_map.get(self.table_size_combo.currentIndex(), 6)
        
        return GamePreferences(
            enabled_games=enabled_games or [GameType.HOLDEM],
            min_stake=self.min_stake_input.text() or "$0.10/$0.25",
            max_stake=self.max_stake_input.text() or "$1/$2",
            stake_levels=stake_levels or [StakeLevel.MICRO],
            min_players=self.min_players_spin.value(),
            max_players=self.max_players_spin.value(),
            preferred_table_size=table_size,
            auto_join_tables=self.autojoin_checkbox.isChecked(),
            max_tables=self.max_tables_spin.value(),
            avoid_full_bot_tables=self.avoid_bots_checkbox.isChecked(),
            prefer_weak_players=self.prefer_weak_checkbox.isChecked()
        )


# Educational example
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    dialog = GameSettingsDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        prefs = dialog.get_preferences()
        print("Selected preferences:")
        print(f"  Games: {[g.value for g in prefs.enabled_games]}")
        print(f"  Stakes: {prefs.min_stake} - {prefs.max_stake}")
        print(f"  Player range: {prefs.min_players}-{prefs.max_players}")
    
    sys.exit()
