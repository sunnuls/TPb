"""
Table Selection Dialog - Launcher Application (Roadmap6 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Configure game type preferences
- Set stake limits
- Tournament settings
- Collusion mode options
"""

import logging
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QDoubleSpinBox, QSpinBox, QCheckBox,
        QPushButton, QComboBox, QListWidget, QTabWidget,
        QWidget, QFormLayout
    )
    from PyQt6.QtCore import Qt
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False

from launcher.models.table_selection_config import (
    TableSelectionConfig, GameType, GameSpeed
)

logger = logging.getLogger(__name__)


if PYQT_AVAILABLE:
    class TableSelectionDialog(QDialog):
        """
        Table selection configuration dialog.
        
        Allows user to configure:
        - Game types to play
        - Stake ranges
        - Table preferences
        - Tournament settings
        - Collusion mode
        
        ⚠️ EDUCATIONAL NOTE:
            Configures automatic table selection for bots.
        """
        
        def __init__(self, parent=None, config: Optional[TableSelectionConfig] = None):
            """
            Initialize dialog.
            
            Args:
                parent: Parent widget
                config: Existing configuration to edit
            """
            super().__init__(parent)
            
            self.config = config or TableSelectionConfig()
            
            self.setWindowTitle("Table Selection Configuration")
            self.setModal(True)
            self.setMinimumSize(600, 500)
            
            self._setup_ui()
            self._load_config()
        
        def _setup_ui(self):
            """Setup UI."""
            layout = QVBoxLayout(self)
            
            # Tabs
            tabs = QTabWidget()
            tabs.addTab(self._create_game_types_tab(), "Game Types")
            tabs.addTab(self._create_stakes_tab(), "Stakes & Limits")
            tabs.addTab(self._create_tournament_tab(), "Tournaments")
            tabs.addTab(self._create_advanced_tab(), "Advanced")
            
            layout.addWidget(tabs)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(self.accept)
            btn_layout.addWidget(save_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
            
            layout.addLayout(btn_layout)
        
        def _create_game_types_tab(self) -> QWidget:
            """Create game types tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Game types
            group = QGroupBox("Select Game Types")
            group_layout = QVBoxLayout(group)
            
            self.game_type_checks = {}
            for game_type in GameType:
                check = QCheckBox(game_type.value)
                self.game_type_checks[game_type] = check
                group_layout.addWidget(check)
            
            layout.addWidget(group)
            
            # Table sizes
            sizes_group = QGroupBox("Preferred Table Sizes")
            sizes_layout = QVBoxLayout(sizes_group)
            
            self.size_6max = QCheckBox("6-max (6 players)")
            self.size_9max = QCheckBox("9-max (9 players)")
            self.size_heads_up = QCheckBox("Heads-Up (2 players)")
            
            sizes_layout.addWidget(self.size_6max)
            sizes_layout.addWidget(self.size_9max)
            sizes_layout.addWidget(self.size_heads_up)
            
            layout.addWidget(sizes_group)
            
            # Game speed
            speed_group = QGroupBox("Game Speed")
            speed_layout = QVBoxLayout(speed_group)
            
            self.speed_checks = {}
            for speed in GameSpeed:
                check = QCheckBox(speed.value)
                self.speed_checks[speed] = check
                speed_layout.addWidget(check)
            
            layout.addWidget(speed_group)
            
            layout.addStretch()
            
            return widget
        
        def _create_stakes_tab(self) -> QWidget:
            """Create stakes tab."""
            widget = QWidget()
            layout = QFormLayout(widget)
            
            # Stake range
            layout.addRow(QLabel("<b>Cash Game Stakes (BB)</b>"))
            
            self.min_stake = QDoubleSpinBox()
            self.min_stake.setRange(0.01, 1000.00)
            self.min_stake.setDecimals(2)
            self.min_stake.setSingleStep(0.10)
            self.min_stake.setPrefix("$")
            layout.addRow("Minimum Stake:", self.min_stake)
            
            self.max_stake = QDoubleSpinBox()
            self.max_stake.setRange(0.01, 1000.00)
            self.max_stake.setDecimals(2)
            self.max_stake.setSingleStep(0.10)
            self.max_stake.setPrefix("$")
            layout.addRow("Maximum Stake:", self.max_stake)
            
            layout.addRow(QLabel(""))  # Spacer
            
            # Player count
            layout.addRow(QLabel("<b>Table Filters</b>"))
            
            self.min_players = QSpinBox()
            self.min_players.setRange(1, 9)
            layout.addRow("Minimum Players:", self.min_players)
            
            self.max_players = QSpinBox()
            self.max_players.setRange(1, 9)
            layout.addRow("Maximum Players:", self.max_players)
            
            self.target_fish = QSpinBox()
            self.target_fish.setRange(0, 5)
            layout.addRow("Target Weak Players:", self.target_fish)
            
            layout.addRow(QLabel(""))
            
            # Wait time
            self.max_wait = QSpinBox()
            self.max_wait.setRange(10, 3600)
            self.max_wait.setSingleStep(10)
            self.max_wait.setSuffix(" seconds")
            layout.addRow("Max Wait Time:", self.max_wait)
            
            return widget
        
        def _create_tournament_tab(self) -> QWidget:
            """Create tournament tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Enable tournaments
            self.tournament_enabled = QCheckBox("Enable Tournament Selection")
            self.tournament_enabled.stateChanged.connect(self._on_tournament_toggled)
            layout.addWidget(self.tournament_enabled)
            
            # Tournament settings group
            self.tournament_group = QGroupBox("Tournament Settings")
            group_layout = QFormLayout(self.tournament_group)
            
            self.tournament_min = QDoubleSpinBox()
            self.tournament_min.setRange(0.10, 10000.00)
            self.tournament_min.setDecimals(2)
            self.tournament_min.setPrefix("$")
            group_layout.addRow("Min Buy-in:", self.tournament_min)
            
            self.tournament_max = QDoubleSpinBox()
            self.tournament_max.setRange(0.10, 10000.00)
            self.tournament_max.setDecimals(2)
            self.tournament_max.setPrefix("$")
            group_layout.addRow("Max Buy-in:", self.tournament_max)
            
            group_layout.addRow(QLabel(""))
            group_layout.addRow(QLabel("<b>Tournament Types:</b>"))
            
            self.tournament_types = QListWidget()
            self.tournament_types.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            self.tournament_types.addItems([
                "Freezeout",
                "Rebuy",
                "Re-entry",
                "Knockout",
                "Progressive Knockout",
                "Sit & Go",
                "Spin & Go",
                "All-In Race"
            ])
            group_layout.addRow(self.tournament_types)
            
            layout.addWidget(self.tournament_group)
            layout.addStretch()
            
            return widget
        
        def _create_advanced_tab(self) -> QWidget:
            """Create advanced tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Table preferences
            pref_group = QGroupBox("Table Preferences")
            pref_layout = QVBoxLayout(pref_group)
            
            self.avoid_pros = QCheckBox("Avoid tables with known professionals")
            self.avoid_pros.setChecked(True)
            pref_layout.addWidget(self.avoid_pros)
            
            self.prefer_loose = QCheckBox("Prefer loose/passive tables (high VPIP)")
            self.prefer_loose.setChecked(True)
            pref_layout.addWidget(self.prefer_loose)
            
            self.auto_rejoin = QCheckBox("Auto-rejoin after leaving table")
            self.auto_rejoin.setChecked(True)
            pref_layout.addWidget(self.auto_rejoin)
            
            rejoin_layout = QHBoxLayout()
            rejoin_layout.addWidget(QLabel("Rejoin delay:"))
            self.rejoin_delay = QSpinBox()
            self.rejoin_delay.setRange(0, 300)
            self.rejoin_delay.setSuffix(" seconds")
            rejoin_layout.addWidget(self.rejoin_delay)
            rejoin_layout.addStretch()
            pref_layout.addLayout(rejoin_layout)
            
            layout.addWidget(pref_group)
            
            # Collusion mode
            collusion_group = QGroupBox("⚠️ COLLUSION MODE (Educational Research)")
            collusion_group.setStyleSheet("QGroupBox { color: #FF6666; font-weight: bold; }")
            collusion_layout = QVBoxLayout(collusion_group)
            
            self.collusion_mode = QCheckBox("Enable collusion mode (3-bot coordination)")
            collusion_layout.addWidget(self.collusion_mode)
            
            collusion_info = QLabel(
                "⚠️ When enabled, bots will coordinate to fill tables together.\n"
                "Requires minimum empty seats for all 3 bots to join.\n\n"
                "EDUCATIONAL RESEARCH ONLY - ILLEGAL IN REAL POKER."
            )
            collusion_info.setWordWrap(True)
            collusion_info.setStyleSheet("color: #FFAA00; font-size: 9pt;")
            collusion_layout.addWidget(collusion_info)
            
            seats_layout = QHBoxLayout()
            seats_layout.addWidget(QLabel("Minimum empty seats:"))
            self.min_empty_seats = QSpinBox()
            self.min_empty_seats.setRange(3, 9)
            self.min_empty_seats.setValue(3)
            seats_layout.addWidget(self.min_empty_seats)
            seats_layout.addStretch()
            collusion_layout.addLayout(seats_layout)
            
            layout.addWidget(collusion_group)
            
            layout.addStretch()
            
            return widget
        
        def _on_tournament_toggled(self, state):
            """Handle tournament checkbox toggle."""
            self.tournament_group.setEnabled(state == 2)  # Qt.CheckState.Checked
        
        def _load_config(self):
            """Load configuration into UI."""
            # Game types
            for game_type, check in self.game_type_checks.items():
                check.setChecked(game_type in self.config.enabled_game_types)
            
            # Table sizes
            self.size_6max.setChecked(6 in self.config.preferred_table_sizes)
            self.size_9max.setChecked(9 in self.config.preferred_table_sizes)
            self.size_heads_up.setChecked(2 in self.config.preferred_table_sizes)
            
            # Game speeds
            for speed, check in self.speed_checks.items():
                check.setChecked(speed in self.config.preferred_speeds)
            
            # Stakes
            self.min_stake.setValue(self.config.min_stake)
            self.max_stake.setValue(self.config.max_stake)
            
            # Filters
            self.min_players.setValue(self.config.min_players)
            self.max_players.setValue(self.config.max_players)
            self.target_fish.setValue(self.config.target_fish_count)
            self.max_wait.setValue(self.config.max_wait_time)
            
            # Tournaments
            self.tournament_enabled.setChecked(self.config.tournament_enabled)
            self.tournament_min.setValue(self.config.tournament_min_buyin)
            self.tournament_max.setValue(self.config.tournament_max_buyin)
            
            # Select tournament types
            for i in range(self.tournament_types.count()):
                item = self.tournament_types.item(i)
                if item.text() in self.config.tournament_types:
                    item.setSelected(True)
            
            self._on_tournament_toggled(2 if self.config.tournament_enabled else 0)
            
            # Advanced
            self.avoid_pros.setChecked(self.config.avoid_pros)
            self.prefer_loose.setChecked(self.config.prefer_loose_tables)
            self.auto_rejoin.setChecked(self.config.auto_rejoin)
            self.rejoin_delay.setValue(self.config.rejoin_delay)
            
            # Collusion
            self.collusion_mode.setChecked(self.config.collusion_mode)
            self.min_empty_seats.setValue(self.config.min_empty_seats)
        
        def get_config(self) -> TableSelectionConfig:
            """Get configuration from UI."""
            # Game types
            self.config.enabled_game_types = [
                gt for gt, check in self.game_type_checks.items()
                if check.isChecked()
            ]
            
            # Table sizes
            self.config.preferred_table_sizes = []
            if self.size_6max.isChecked():
                self.config.preferred_table_sizes.append(6)
            if self.size_9max.isChecked():
                self.config.preferred_table_sizes.append(9)
            if self.size_heads_up.isChecked():
                self.config.preferred_table_sizes.append(2)
            
            # Game speeds
            self.config.preferred_speeds = [
                speed for speed, check in self.speed_checks.items()
                if check.isChecked()
            ]
            
            # Stakes
            self.config.min_stake = self.min_stake.value()
            self.config.max_stake = self.max_stake.value()
            
            # Filters
            self.config.min_players = self.min_players.value()
            self.config.max_players = self.max_players.value()
            self.config.target_fish_count = self.target_fish.value()
            self.config.max_wait_time = self.max_wait.value()
            
            # Tournaments
            self.config.tournament_enabled = self.tournament_enabled.isChecked()
            self.config.tournament_min_buyin = self.tournament_min.value()
            self.config.tournament_max_buyin = self.tournament_max.value()
            
            # Tournament types
            self.config.tournament_types = [
                item.text() for item in self.tournament_types.selectedItems()
            ]
            
            # Advanced
            self.config.avoid_pros = self.avoid_pros.isChecked()
            self.config.prefer_loose_tables = self.prefer_loose.isChecked()
            self.config.auto_rejoin = self.auto_rejoin.isChecked()
            self.config.rejoin_delay = self.rejoin_delay.value()
            
            # Collusion
            self.config.collusion_mode = self.collusion_mode.isChecked()
            self.config.min_empty_seats = self.min_empty_seats.value()
            
            return self.config


# Educational example
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test dialog
    dialog = TableSelectionDialog()
    
    if dialog.exec():
        config = dialog.get_config()
        print("Configuration saved:")
        print(f"  Game types: {[gt.value for gt in config.enabled_game_types]}")
        print(f"  Stakes: ${config.min_stake} - ${config.max_stake}")
        print(f"  Tournaments: {config.tournament_enabled}")
        print(f"  Collusion mode: {config.collusion_mode}")
    else:
        print("Configuration cancelled")
