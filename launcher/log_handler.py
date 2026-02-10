"""
Log Handler - Launcher Application (Roadmap6 Phase 6).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Real-time log capture
- Color-coded messages
- Thread-safe queue
- Signal emission for GUI updates
"""

import logging
import queue
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYQT_AVAILABLE = False


class LogLevel(Enum):
    """Log level categories."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    ACTION = "ACTION"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """
    Single log entry.
    
    Attributes:
        timestamp: Log timestamp
        level: Log level
        logger_name: Logger name
        message: Log message
        color: Display color
    """
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    color: str = "#FFFFFF"
    
    def __post_init__(self):
        """Set color based on level."""
        if not self.color or self.color == "#FFFFFF":
            self.color = self._get_color_for_level()
    
    def _get_color_for_level(self) -> str:
        """
        Get display color for log level.
        
        Returns:
            Hex color code
        """
        color_map = {
            LogLevel.DEBUG: "#888888",      # Gray
            LogLevel.INFO: "#CCCCCC",       # Light gray
            LogLevel.ACTION: "#66FF66",     # Green
            LogLevel.WARNING: "#FFFF66",    # Yellow
            LogLevel.ERROR: "#FF6666",      # Red
            LogLevel.CRITICAL: "#FF3333"    # Bright red
        }
        return color_map.get(self.level, "#FFFFFF")
    
    def format(self, include_timestamp: bool = True, include_logger: bool = False) -> str:
        """
        Format log entry as string.
        
        Args:
            include_timestamp: Include timestamp
            include_logger: Include logger name
        
        Returns:
            Formatted string
        """
        parts = []
        
        if include_timestamp:
            parts.append(self.timestamp.strftime("%H:%M:%S"))
        
        parts.append(f"[{self.level.value}]")
        
        if include_logger:
            parts.append(f"({self.logger_name})")
        
        parts.append(self.message)
        
        return " ".join(parts)


if PYQT_AVAILABLE:
    class QtLogHandler(logging.Handler, QObject):
        """
        PyQt6-compatible log handler.
        
        Captures log records and emits signals for GUI updates.
        Thread-safe via internal queue.
        
        ⚠️ EDUCATIONAL NOTE:
            Captures logs from all bot instances for monitoring.
        
        Signals:
            log_received: Emitted when new log entry received
        """
        
        log_received = pyqtSignal(LogEntry)
        
        def __init__(self, level=logging.DEBUG):
            """
            Initialize handler.
            
            Args:
                level: Minimum log level
            """
            logging.Handler.__init__(self, level=level)
            QObject.__init__(self)
            
            self.log_queue = queue.Queue(maxsize=1000)
            self.max_entries = 10000
            self.entries = []
        
        def emit(self, record: logging.LogRecord):
            """
            Emit log record.
            
            Args:
                record: Log record
            """
            try:
                # Determine level
                level_map = {
                    logging.DEBUG: LogLevel.DEBUG,
                    logging.INFO: LogLevel.INFO,
                    logging.WARNING: LogLevel.WARNING,
                    logging.ERROR: LogLevel.ERROR,
                    logging.CRITICAL: LogLevel.CRITICAL
                }
                
                level = level_map.get(record.levelno, LogLevel.INFO)
                
                # Check for special "action" logs
                if hasattr(record, 'action') and record.action:
                    level = LogLevel.ACTION
                elif 'action' in record.getMessage().lower():
                    level = LogLevel.ACTION
                
                # Create entry
                entry = LogEntry(
                    timestamp=datetime.fromtimestamp(record.created),
                    level=level,
                    logger_name=record.name,
                    message=record.getMessage()
                )
                
                # Store
                self.entries.append(entry)
                if len(self.entries) > self.max_entries:
                    self.entries.pop(0)
                
                # Emit signal
                self.log_received.emit(entry)
            
            except Exception as e:
                # Don't let logging errors crash the app
                print(f"Log handler error: {e}")
        
        def get_recent_logs(self, count: int = 100) -> list:
            """
            Get recent log entries.
            
            Args:
                count: Number of entries
            
            Returns:
                List of recent log entries
            """
            return self.entries[-count:]
        
        def get_logs_by_level(self, level: LogLevel, count: int = 100) -> list:
            """
            Get logs filtered by level.
            
            Args:
                level: Log level to filter
                count: Maximum entries
            
            Returns:
                Filtered log entries
            """
            filtered = [e for e in self.entries if e.level == level]
            return filtered[-count:]
        
        def clear(self):
            """Clear all log entries."""
            self.entries.clear()
        
        def get_statistics(self) -> dict:
            """
            Get log statistics.
            
            Returns:
                Statistics dictionary
            """
            stats = {
                'total': len(self.entries),
                'by_level': {}
            }
            
            for level in LogLevel:
                count = len([e for e in self.entries if e.level == level])
                stats['by_level'][level.value] = count
            
            return stats


class SimpleLogHandler(logging.Handler):
    """
    Simple log handler for non-GUI environments.
    
    Stores logs in memory for testing.
    """
    
    def __init__(self, level=logging.DEBUG):
        """
        Initialize handler.
        
        Args:
            level: Minimum log level
        """
        super().__init__(level=level)
        self.entries = []
        self.max_entries = 10000
    
    def emit(self, record: logging.LogRecord):
        """
        Emit log record.
        
        Args:
            record: Log record
        """
        try:
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL
            }
            
            level = level_map.get(record.levelno, LogLevel.INFO)
            
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=level,
                logger_name=record.name,
                message=record.getMessage()
            )
            
            self.entries.append(entry)
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)
        
        except Exception:
            pass
    
    def get_recent_logs(self, count: int = 100) -> list:
        """Get recent log entries."""
        return self.entries[-count:]
    
    def clear(self):
        """Clear all log entries."""
        self.entries.clear()
    
    def get_statistics(self) -> dict:
        """
        Get log statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'total': len(self.entries),
            'by_level': {}
        }
        
        for level in LogLevel:
            count = len([e for e in self.entries if e.level == level])
            stats['by_level'][level.value] = count
        
        return stats


# Global handler instance
_global_handler: Optional[logging.Handler] = None


def setup_launcher_logging(use_qt: bool = True) -> logging.Handler:
    """
    Setup launcher logging.
    
    Args:
        use_qt: Use Qt handler (if available)
    
    Returns:
        Log handler instance
    """
    global _global_handler
    
    if _global_handler:
        return _global_handler
    
    # Create handler
    if use_qt and PYQT_AVAILABLE:
        handler = QtLogHandler()
    else:
        handler = SimpleLogHandler()
    
    handler.setLevel(logging.DEBUG)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    # Store globally
    _global_handler = handler
    
    return handler


def get_log_handler() -> Optional[logging.Handler]:
    """
    Get global log handler.
    
    Returns:
        Log handler if initialized
    """
    return _global_handler


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Log Handler - Educational Research")
    print("=" * 60)
    print()
    
    # Setup
    handler = setup_launcher_logging(use_qt=False)
    
    # Create test logger
    logger = logging.getLogger("test_bot")
    
    # Log messages
    logger.debug("Bot initialized")
    logger.info("Connected to table")
    logger.warning("High vision error rate")
    logger.error("Failed to execute action")
    
    # Get recent logs
    print("Recent logs:")
    for entry in handler.get_recent_logs():
        print(f"  {entry.format()}")
    
    print()
    
    # Statistics
    stats = handler.get_statistics() if hasattr(handler, 'get_statistics') else None
    if stats:
        print("Log statistics:")
        print(f"  Total: {stats['total']}")
        for level, count in stats['by_level'].items():
            if count > 0:
                print(f"  {level}: {count}")
    
    print()
    print("=" * 60)
    print("Log handler demonstration complete")
    print("=" * 60)
