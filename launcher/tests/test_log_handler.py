"""
Tests for Log Handler - Phase 6.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import logging
from datetime import datetime

from launcher.log_handler import (
    LogEntry, LogLevel, SimpleLogHandler,
    setup_launcher_logging, get_log_handler
)


class TestLogEntry:
    """Tests for LogEntry."""
    
    def test_create_entry(self):
        """Test creating log entry."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            logger_name="test_logger",
            message="Test message"
        )
        
        assert entry.level == LogLevel.INFO
        assert entry.logger_name == "test_logger"
        assert entry.message == "Test message"
        assert entry.color  # Color should be set
    
    def test_color_for_level(self):
        """Test color assignment by level."""
        levels_colors = {
            LogLevel.DEBUG: "#888888",
            LogLevel.INFO: "#CCCCCC",
            LogLevel.ACTION: "#66FF66",
            LogLevel.WARNING: "#FFFF66",
            LogLevel.ERROR: "#FF6666",
            LogLevel.CRITICAL: "#FF3333"
        }
        
        for level, expected_color in levels_colors.items():
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                logger_name="test",
                message="test"
            )
            assert entry.color == expected_color
    
    def test_format_basic(self):
        """Test basic formatting."""
        entry = LogEntry(
            timestamp=datetime(2026, 2, 5, 12, 30, 45),
            level=LogLevel.INFO,
            logger_name="test_logger",
            message="Test message"
        )
        
        formatted = entry.format(include_timestamp=True, include_logger=False)
        
        assert "12:30:45" in formatted
        assert "[INFO]" in formatted
        assert "Test message" in formatted
        assert "test_logger" not in formatted
    
    def test_format_with_logger(self):
        """Test formatting with logger name."""
        entry = LogEntry(
            timestamp=datetime(2026, 2, 5, 12, 30, 45),
            level=LogLevel.ERROR,
            logger_name="test_logger",
            message="Error occurred"
        )
        
        formatted = entry.format(include_timestamp=True, include_logger=True)
        
        assert "test_logger" in formatted
        assert "[ERROR]" in formatted


class TestSimpleLogHandler:
    """Tests for SimpleLogHandler."""
    
    def test_initialization(self):
        """Test handler initialization."""
        handler = SimpleLogHandler()
        
        assert handler.entries == []
        assert handler.max_entries == 10000
    
    def test_emit_log(self):
        """Test emitting log records."""
        handler = SimpleLogHandler()
        logger = logging.getLogger("test_emit")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Emit logs
        logger.info("Test info message")
        logger.warning("Test warning")
        logger.error("Test error")
        
        # Check entries
        assert len(handler.entries) == 3
        assert handler.entries[0].level == LogLevel.INFO
        assert handler.entries[1].level == LogLevel.WARNING
        assert handler.entries[2].level == LogLevel.ERROR
    
    def test_get_recent_logs(self):
        """Test getting recent logs."""
        handler = SimpleLogHandler()
        logger = logging.getLogger("test_recent")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Emit 10 logs
        for i in range(10):
            logger.info(f"Message {i}")
        
        # Get recent 5
        recent = handler.get_recent_logs(count=5)
        assert len(recent) == 5
        assert recent[-1].message == "Message 9"
    
    def test_max_entries_limit(self):
        """Test max entries limit."""
        handler = SimpleLogHandler()
        handler.max_entries = 100
        
        logger = logging.getLogger("test_limit")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Emit 150 logs
        for i in range(150):
            logger.info(f"Message {i}")
        
        # Should be capped at 100
        assert len(handler.entries) == 100
    
    def test_clear_logs(self):
        """Test clearing logs."""
        handler = SimpleLogHandler()
        logger = logging.getLogger("test_clear_isolated")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        logger.info("Test message")
        assert len(handler.entries) >= 1
        
        handler.clear()
        assert len(handler.entries) == 0


class TestLoggingSetup:
    """Tests for logging setup."""
    
    def test_setup_launcher_logging(self):
        """Test launcher logging setup."""
        handler = setup_launcher_logging(use_qt=False)
        
        assert handler is not None
        assert isinstance(handler, SimpleLogHandler)
    
    def test_get_log_handler(self):
        """Test getting global log handler."""
        # Setup first
        handler = setup_launcher_logging(use_qt=False)
        
        # Get handler
        retrieved = get_log_handler()
        assert retrieved is handler
    
    def test_logging_integration(self):
        """Test full logging integration."""
        # Setup
        handler = setup_launcher_logging(use_qt=False)
        handler.clear()
        
        # Create logger
        logger = logging.getLogger("integration_test")
        
        # Log messages
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Check handler received all
        entries = handler.get_recent_logs()
        assert len(entries) >= 4
        
        # Check levels
        levels = [e.level for e in entries[-4:]]
        assert LogLevel.DEBUG in levels
        assert LogLevel.INFO in levels
        assert LogLevel.WARNING in levels
        assert LogLevel.ERROR in levels


def test_phase6_log_handler_summary():
    """Print Phase 6 log handler summary."""
    print("\n" + "=" * 60)
    print("PHASE 6 - LOG HANDLER TESTS")
    print("=" * 60)
    print()
    print("Components tested:")
    print("  ✓ LogEntry creation and formatting")
    print("  ✓ LogLevel color mapping")
    print("  ✓ SimpleLogHandler functionality")
    print("  ✓ Log emission and storage")
    print("  ✓ Max entries limiting")
    print("  ✓ Clear logs")
    print("  ✓ Logging setup and integration")
    print()
    print("Features:")
    print("  - Thread-safe log capture")
    print("  - Color-coded messages")
    print("  - Recent logs retrieval")
    print("  - Level filtering")
    print("  - Max 10,000 entries (auto-trim)")
    print()
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
