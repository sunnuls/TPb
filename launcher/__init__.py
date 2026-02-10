"""
Launcher Application - Educational Game Theory Research (Roadmap6).

⚠️ CRITICAL ETHICAL WARNING:
    This launcher manages coordinated bot operations (COLLUSION).
    
    EXTREMELY UNETHICAL and ILLEGAL in real poker.
    Educational research only. NEVER use without explicit consent.

Standalone GUI application for managing HIVE bot pool.
"""

__version__ = "1.0.0"

from launcher.models import (
    Account,
    AccountStatus,
    WindowInfo,
    WindowType,
    ROIConfig,
    ROIZone
)
from launcher.config_manager import ConfigManager
from launcher.window_capture import WindowCapture
from launcher.bot_instance import BotInstance, BotStatus, BotStatistics
from launcher.bot_manager import BotManager
from launcher.bot_settings import BotSettings, StrategyPreset, BotSettingsManager
from launcher.lobby_scanner import LobbyScanner, LobbyTable, LobbySnapshot
from launcher.auto_seating import AutoSeatingManager, HiveDeployment, DeploymentStatus
from launcher.collusion_coordinator import CollusionCoordinator, CollusionSession
from launcher.log_handler import (
    LogEntry, LogLevel, SimpleLogHandler,
    setup_launcher_logging, get_log_handler
)

# Conditional import for PyQt6-dependent components
try:
    from launcher.log_handler import QtLogHandler
    QTLOG_AVAILABLE = True
except ImportError:
    QTLOG_AVAILABLE = False

__all__ = [
    'Account',
    'AccountStatus',
    'WindowInfo',
    'WindowType',
    'ROIConfig',
    'ROIZone',
    'ConfigManager',
    'WindowCapture',
    'BotInstance',
    'BotStatus',
    'BotStatistics',
    'BotManager',
    'BotSettings',
    'StrategyPreset',
    'BotSettingsManager',
    'LobbyScanner',
    'LobbyTable',
    'LobbySnapshot',
    'AutoSeatingManager',
    'HiveDeployment',
    'DeploymentStatus',
    'CollusionCoordinator',
    'CollusionSession',
    'LogEntry',
    'LogLevel',
    'SimpleLogHandler',
    'setup_launcher_logging',
    'get_log_handler',
    'LauncherApp',
    'MainWindow'
]

# Add QtLogHandler to __all__ if available
if QTLOG_AVAILABLE:
    __all__.append('QtLogHandler')
