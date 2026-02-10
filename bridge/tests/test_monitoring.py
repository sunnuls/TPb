"""
Tests for Monitoring System (Roadmap3 Phase 6).

Tests:
- UI change detection
- Anomaly detection (popups, disconnections, invalid states)
- Alert system
- Auto-shutdown mechanism
- Decision logging
- Statistics
"""

import time
from pathlib import Path

import numpy as np
import pytest

from bridge.monitoring import (
    Alert,
    AlertSeverity,
    AnomalyType,
    MonitoringState,
    MonitoringSystem,
)
from bridge.safety import SafetyFramework


@pytest.fixture
def temp_monitoring_dirs(tmp_path):
    """Create temporary directories for monitoring."""
    log_dir = tmp_path / "monitoring_logs"
    screenshot_dir = tmp_path / "monitoring_screenshots"
    log_dir.mkdir()
    screenshot_dir.mkdir()
    
    return {
        'log_dir': str(log_dir),
        'screenshot_dir': str(screenshot_dir)
    }


@pytest.fixture
def monitoring_system(temp_monitoring_dirs):
    """Create monitoring system instance with isolated SafetyFramework."""
    # Create isolated SafetyFramework (not singleton) for testing
    # SafetyFramework defaults to dry_run=True
    safety = SafetyFramework()
    
    return MonitoringSystem(
        safety=safety,
        log_dir=temp_monitoring_dirs['log_dir'],
        screenshot_dir=temp_monitoring_dirs['screenshot_dir'],
        ui_change_threshold=0.15,
        max_consecutive_errors=3
    )


class TestMonitoringState:
    """Test monitoring state tracking."""
    
    def test_initial_state(self):
        """Test initial monitoring state."""
        state = MonitoringState()
        
        assert state.monitoring_active is True
        assert state.last_screenshot_hash is None
        assert state.last_ui_check_time == 0.0
        assert state.consecutive_errors == 0
        assert len(state.alerts) == 0
        assert state.total_checks == 0
        assert state.anomalies_detected == 0
        assert state.shutdowns_triggered == 0


class TestAlert:
    """Test alert creation and structure."""
    
    def test_alert_creation(self):
        """Test alert creation with all fields."""
        alert = Alert(
            timestamp=time.time(),
            severity=AlertSeverity.WARNING,
            anomaly_type=AnomalyType.UI_CHANGE,
            message="Test alert",
            screenshot_path="/path/to/screenshot.png",
            should_shutdown=False,
            metadata={'key': 'value'}
        )
        
        assert alert.severity == AlertSeverity.WARNING
        assert alert.anomaly_type == AnomalyType.UI_CHANGE
        assert alert.message == "Test alert"
        assert alert.screenshot_path == "/path/to/screenshot.png"
        assert alert.should_shutdown is False
        assert alert.metadata['key'] == 'value'
    
    def test_critical_alert(self):
        """Test critical alert with shutdown."""
        alert = Alert(
            timestamp=time.time(),
            severity=AlertSeverity.CRITICAL,
            anomaly_type=AnomalyType.DISCONNECTION,
            message="Connection lost",
            should_shutdown=True
        )
        
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.should_shutdown is True


class TestMonitoringSystem:
    """Test monitoring system functionality."""
    
    def test_initialization(self, monitoring_system):
        """Test monitoring system initialization."""
        assert monitoring_system.state.monitoring_active is True
        assert monitoring_system.ui_change_threshold == 0.15
        assert monitoring_system.max_consecutive_errors == 3
        assert Path(monitoring_system.log_dir).exists()
        assert Path(monitoring_system.screenshot_dir).exists()
    
    def test_ui_check_no_screenshot(self, monitoring_system):
        """Test UI check with no screenshot (dry-run mode)."""
        alert = monitoring_system.check_ui_changes(screenshot=None)
        
        # No alert in dry-run
        assert alert is None
        assert monitoring_system.state.total_checks == 1
    
    def test_ui_check_first_baseline(self, monitoring_system):
        """Test UI check establishes baseline on first run."""
        # Create dummy screenshot
        screenshot = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        alert = monitoring_system.check_ui_changes(screenshot=screenshot)
        
        # No alert on first check (establishing baseline)
        assert alert is None
        assert monitoring_system.state.last_screenshot_hash is not None
        assert monitoring_system.state.total_checks == 1
    
    def test_ui_check_identical_screenshot(self, monitoring_system):
        """Test UI check with identical screenshot."""
        screenshot = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # First check - baseline
        monitoring_system.check_ui_changes(screenshot=screenshot)
        
        # Second check - identical
        alert = monitoring_system.check_ui_changes(screenshot=screenshot)
        
        # No alert for identical screenshot
        assert alert is None
        assert monitoring_system.state.total_checks == 2
    
    def test_ui_check_major_change(self, monitoring_system):
        """Test UI check with major change."""
        screenshot1 = np.zeros((100, 100, 3), dtype=np.uint8)
        screenshot2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        # Establish baseline
        monitoring_system.check_ui_changes(screenshot=screenshot1)
        
        # Major change
        alert = monitoring_system.check_ui_changes(screenshot=screenshot2)
        
        # Alert should be triggered for major change
        assert alert is not None
        assert alert.anomaly_type == AnomalyType.UI_CHANGE
        assert alert.severity == AlertSeverity.WARNING
        assert monitoring_system.state.anomalies_detected == 1
    
    def test_popup_detection(self, monitoring_system):
        """Test popup detection (placeholder)."""
        alert = monitoring_system.detect_popup(screenshot=None)
        
        # No popup in dry-run
        assert alert is None
    
    def test_disconnection_detection_connected(self, monitoring_system):
        """Test disconnection detection when connected."""
        alert = monitoring_system.detect_disconnection(connection_status=True)
        
        # No alert when connected
        assert alert is None
    
    def test_disconnection_detection_disconnected(self, monitoring_system):
        """Test disconnection detection when disconnected."""
        # Emergency shutdown calls sys.exit(1), so expect SystemExit
        with pytest.raises(SystemExit):
            alert = monitoring_system.detect_disconnection(connection_status=False)
        
        # Verify alert was created and stored
        assert monitoring_system.state.anomalies_detected == 1
        assert len(monitoring_system.state.alerts) == 1
        
        alert = monitoring_system.state.alerts[0]
        assert alert.anomaly_type == AnomalyType.DISCONNECTION
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.should_shutdown is True
    
    def test_invalid_state_negative_pot(self, monitoring_system):
        """Test invalid state detection - negative pot."""
        invalid_state = {
            'pot': -10.0,
            'hero_stack': 100.0
        }
        
        # Shutdown triggers sys.exit
        with pytest.raises(SystemExit):
            alert = monitoring_system.detect_invalid_state(invalid_state)
        
        # Verify alert was created
        assert monitoring_system.state.anomalies_detected == 1
        alert = monitoring_system.state.alerts[0]
        assert alert.anomaly_type == AnomalyType.INVALID_STATE
        assert alert.severity == AlertSeverity.ERROR
        assert alert.should_shutdown is True
        assert 'negative pot' in alert.metadata['issues']
    
    def test_invalid_state_negative_stack(self, monitoring_system):
        """Test invalid state detection - negative stack."""
        invalid_state = {
            'pot': 10.0,
            'hero_stack': -50.0
        }
        
        # Shutdown triggers sys.exit
        with pytest.raises(SystemExit):
            alert = monitoring_system.detect_invalid_state(invalid_state)
        
        # Verify alert was created
        assert monitoring_system.state.anomalies_detected == 1
        alert = monitoring_system.state.alerts[0]
        assert 'negative hero stack' in alert.metadata['issues']
    
    def test_invalid_state_missing_data(self, monitoring_system):
        """Test invalid state detection - missing critical data."""
        invalid_state = {
            'pot': 10.0,
            'hero_stack': 100.0
            # Missing hero_cards and board
        }
        
        # Shutdown triggers sys.exit
        with pytest.raises(SystemExit):
            alert = monitoring_system.detect_invalid_state(invalid_state)
        
        # Verify alert was created
        assert monitoring_system.state.anomalies_detected == 1
        alert = monitoring_system.state.alerts[0]
        assert 'missing card data' in alert.metadata['issues']
    
    def test_valid_state(self, monitoring_system):
        """Test valid state detection."""
        valid_state = {
            'pot': 30.0,
            'hero_stack': 100.0,
            'hero_cards': ['As', 'Kh'],
            'board': ['Qd', 'Jc', '9s']
        }
        
        alert = monitoring_system.detect_invalid_state(valid_state)
        
        # No alert for valid state
        assert alert is None
    
    def test_error_rate_below_threshold(self, monitoring_system):
        """Test error rate below threshold."""
        monitoring_system.record_error("Error 1")
        monitoring_system.record_error("Error 2")
        
        alert = monitoring_system.check_error_rate()
        
        # No alert below threshold (3 errors needed)
        assert alert is None
        assert monitoring_system.state.consecutive_errors == 2
    
    def test_error_rate_at_threshold(self, monitoring_system):
        """Test error rate at threshold."""
        monitoring_system.record_error("Error 1")
        monitoring_system.record_error("Error 2")
        
        # Third error triggers shutdown (record_error calls check_error_rate internally)
        with pytest.raises(SystemExit):
            monitoring_system.record_error("Error 3")
        
        # Verify alert was created
        assert monitoring_system.state.anomalies_detected == 1
        alert = monitoring_system.state.alerts[0]
        assert alert.anomaly_type == AnomalyType.EXCESSIVE_ERRORS
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.should_shutdown is True
    
    def test_record_success_clears_errors(self, monitoring_system):
        """Test that success clears error count."""
        monitoring_system.record_error("Error 1")
        monitoring_system.record_error("Error 2")
        
        assert monitoring_system.state.consecutive_errors == 2
        
        monitoring_system.record_success()
        
        # Errors cleared
        assert monitoring_system.state.consecutive_errors == 0
    
    def test_decision_logging(self, monitoring_system):
        """Test decision logging."""
        decision = {
            'action': 'raise',
            'amount': 20.0,
            'reasoning': 'Strong hand'
        }
        
        log_path = monitoring_system.log_decision(decision, screenshot=None)
        
        # Log file should be created
        assert log_path != ""
        assert Path(log_path).exists()
        
        # Verify log content
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'DECISION LOG' in content
            assert 'action: raise' in content
            assert 'amount: 20.0' in content
    
    def test_get_alerts_by_severity(self, monitoring_system):
        """Test filtering alerts by severity."""
        # Trigger various alerts (both trigger shutdown, so catch SystemExit)
        try:
            monitoring_system.detect_disconnection(connection_status=False)  # CRITICAL
        except SystemExit:
            pass
        
        # Create new monitoring system to test ERROR alert
        # (previous one is shutdown)
        safety2 = SafetyFramework()  # Defaults to dry_run=True
        monitoring_system2 = MonitoringSystem(
            safety=safety2,
            log_dir=monitoring_system.log_dir,
            screenshot_dir=monitoring_system.screenshot_dir
        )
        
        try:
            monitoring_system2.detect_invalid_state({'pot': -10.0})  # ERROR
        except SystemExit:
            pass
        
        # Test filtering on first system (CRITICAL)
        critical_alerts = monitoring_system.get_alerts_by_severity(AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].anomaly_type == AnomalyType.DISCONNECTION
        
        # Test filtering on second system (ERROR)
        error_alerts = monitoring_system2.get_alerts_by_severity(AlertSeverity.ERROR)
        assert len(error_alerts) == 1
        assert error_alerts[0].anomaly_type == AnomalyType.INVALID_STATE
    
    def test_get_recent_alerts(self, monitoring_system):
        """Test getting recent alerts."""
        # Trigger multiple alerts (but not enough to cause shutdown)
        # Record only 2 errors (threshold is 3)
        monitoring_system.record_error("Error 0")
        monitoring_system.record_error("Error 1")
        
        # Note: No alerts created yet (just error count increased)
        # Create some UI change alerts instead
        screenshot1 = np.zeros((100, 100, 3), dtype=np.uint8)
        screenshot2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        # Establish baseline
        monitoring_system.check_ui_changes(screenshot=screenshot1)
        
        # Trigger UI change alert
        monitoring_system.check_ui_changes(screenshot=screenshot2)
        
        recent = monitoring_system.get_recent_alerts(count=3)
        
        # Should get alerts (at least 1 UI change alert)
        assert len(recent) >= 1
        assert len(recent) <= 3
    
    def test_statistics(self, monitoring_system):
        """Test monitoring statistics."""
        # Perform some operations
        monitoring_system.check_ui_changes(screenshot=None)
        monitoring_system.detect_disconnection(connection_status=True)
        monitoring_system.record_error("Test error")
        
        stats = monitoring_system.get_statistics()
        
        # Verify statistics
        assert stats['monitoring_active'] is True
        assert stats['total_checks'] >= 1
        assert stats['consecutive_errors'] == 1
        assert stats['ui_change_threshold'] == 0.15
        assert stats['max_consecutive_errors'] == 3
        assert stats['shutdowns_triggered'] == 0


class TestAlertHandling:
    """Test alert handling and shutdown logic."""
    
    def test_alert_storage(self, monitoring_system):
        """Test alerts are stored in state."""
        initial_count = len(monitoring_system.state.alerts)
        
        # Disconnection triggers shutdown (sys.exit)
        with pytest.raises(SystemExit):
            monitoring_system.detect_disconnection(connection_status=False)
        
        # Alert should be stored (even though shutdown triggered)
        assert len(monitoring_system.state.alerts) == initial_count + 1
    
    def test_shutdown_trigger(self, monitoring_system):
        """Test shutdown trigger on critical alert."""
        # Trigger critical alert (triggers sys.exit)
        with pytest.raises(SystemExit):
            monitoring_system.detect_disconnection(connection_status=False)
        
        # Monitoring should be deactivated after shutdown
        assert monitoring_system.state.monitoring_active is False
        assert monitoring_system.state.shutdowns_triggered == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
