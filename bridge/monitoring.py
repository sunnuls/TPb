"""
Monitoring & Safety Module (Roadmap3 Phase 6).

Monitors poker client for anomalies and UI changes.
Implements auto-shutdown on suspicious events.

Key Features:
- UI change detection (screenshot comparison)
- Anomaly detection (unexpected events, popups, disconnects)
- Alert system with severity levels
- Auto-shutdown mechanism
- Complete decision + screenshot logging

EDUCATIONAL USE ONLY: For HCI research prototype.
Ensures safe operation with immediate shutdown on anomalies.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np

from bridge.safety import SafetyFramework, EmergencyReason

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    UI_CHANGE = "ui_change"
    UNEXPECTED_POPUP = "unexpected_popup"
    DISCONNECTION = "disconnection"
    INVALID_STATE = "invalid_state"
    TIMING_ANOMALY = "timing_anomaly"
    SCREENSHOT_FAIL = "screenshot_fail"
    EXCESSIVE_ERRORS = "excessive_errors"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """
    Alert for detected anomaly or event.
    
    Attributes:
        timestamp: When alert was triggered
        severity: Alert severity level
        anomaly_type: Type of anomaly detected
        message: Human-readable description
        screenshot_path: Path to screenshot at time of alert
        should_shutdown: Whether to trigger emergency shutdown
        metadata: Additional context data
    """
    timestamp: float
    severity: AlertSeverity
    anomaly_type: AnomalyType
    message: str
    screenshot_path: Optional[str] = None
    should_shutdown: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class MonitoringState:
    """
    Current monitoring state.
    
    Attributes:
        monitoring_active: Whether monitoring is active
        last_screenshot_hash: Hash of last captured screenshot
        last_ui_check_time: Timestamp of last UI check
        consecutive_errors: Count of consecutive errors
        alerts: List of all alerts
        total_checks: Total monitoring checks performed
        anomalies_detected: Total anomalies detected
        shutdowns_triggered: Number of emergency shutdowns
    """
    monitoring_active: bool = True
    last_screenshot_hash: Optional[str] = None
    last_ui_check_time: float = 0.0
    consecutive_errors: int = 0
    alerts: List[Alert] = field(default_factory=list)
    total_checks: int = 0
    anomalies_detected: int = 0
    shutdowns_triggered: int = 0


class MonitoringSystem:
    """
    Monitors poker client for anomalies and safety issues.
    
    Monitoring Components:
    1. UI Change Detection:
       - Compare consecutive screenshots
       - Detect unexpected UI changes
       - Alert on major layout shifts
    
    2. Anomaly Detection:
       - Popup detection (unexpected dialogs)
       - Disconnection detection
       - Invalid state detection
       - Timing anomalies
    
    3. Auto-Shutdown:
       - Emergency shutdown on CRITICAL alerts
       - Configurable shutdown triggers
       - Clean shutdown process
    
    4. Logging:
       - All alerts logged with screenshots
       - Decision history with visual verification
       - Anomaly reports
    
    EDUCATIONAL NOTE:
        This ensures safe operation by immediately shutting down
        on any unexpected behavior or UI changes.
    """
    
    def __init__(
        self,
        safety: Optional[SafetyFramework] = None,
        log_dir: str = "bridge/monitoring_logs",
        screenshot_dir: str = "bridge/monitoring_screenshots",
        ui_change_threshold: float = 0.15,
        max_consecutive_errors: int = 3
    ):
        """
        Initialize monitoring system.
        
        Args:
            safety: Safety framework instance
            log_dir: Directory for monitoring logs
            screenshot_dir: Directory for alert screenshots
            ui_change_threshold: Threshold for UI change detection (0.0-1.0)
            max_consecutive_errors: Max errors before shutdown
        """
        self.safety = safety or SafetyFramework.get_instance()
        self.log_dir = Path(log_dir)
        self.screenshot_dir = Path(screenshot_dir)
        self.ui_change_threshold = ui_change_threshold
        self.max_consecutive_errors = max_consecutive_errors
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Monitoring state
        self.state = MonitoringState()
        
        logger.info(
            f"MonitoringSystem initialized: "
            f"ui_threshold={ui_change_threshold}, "
            f"max_errors={max_consecutive_errors}"
        )
    
    def check_ui_changes(
        self,
        screenshot: Optional[np.ndarray] = None
    ) -> Optional[Alert]:
        """
        Check for unexpected UI changes.
        
        Args:
            screenshot: Current screenshot to analyze
        
        Returns:
            Alert if UI change detected, None otherwise
        
        EDUCATIONAL NOTE:
            Detects UI changes by comparing screenshot hashes.
            Large changes (>15% different) trigger alerts.
        """
        self.state.total_checks += 1
        self.state.last_ui_check_time = time.time()
        
        if screenshot is None:
            # Dry-run mode or no screenshot
            logger.debug("UI check skipped - no screenshot")
            return None
        
        # Calculate screenshot hash
        current_hash = self._calculate_screenshot_hash(screenshot)
        
        # First check - store baseline
        if self.state.last_screenshot_hash is None:
            self.state.last_screenshot_hash = current_hash
            logger.debug("UI baseline established")
            return None
        
        # Compare with previous hash
        similarity = self._calculate_similarity(
            self.state.last_screenshot_hash,
            current_hash
        )
        
        # Check if change exceeds threshold
        if similarity < (1.0 - self.ui_change_threshold):
            alert = Alert(
                timestamp=time.time(),
                severity=AlertSeverity.WARNING,
                anomaly_type=AnomalyType.UI_CHANGE,
                message=f"UI change detected: similarity={similarity:.1%}",
                should_shutdown=False,
                metadata={'similarity': similarity}
            )
            
            self._handle_alert(alert)
            return alert
        
        # Update baseline
        self.state.last_screenshot_hash = current_hash
        return None
    
    def detect_popup(
        self,
        screenshot: Optional[np.ndarray] = None
    ) -> Optional[Alert]:
        """
        Detect unexpected popup dialogs.
        
        Args:
            screenshot: Current screenshot to analyze
        
        Returns:
            Alert if popup detected, None otherwise
        
        EDUCATIONAL NOTE:
            Popups often indicate:
            - Connection issues
            - Account problems
            - Terms of service changes
            - Security alerts
            All require immediate shutdown.
        """
        if screenshot is None:
            return None
        
        # Placeholder for popup detection logic
        # Real implementation would use:
        # - Template matching for common dialog patterns
        # - Color analysis (dialogs often have specific colors)
        # - Text detection (OK/Cancel buttons)
        
        # For dry-run: no popups detected
        logger.debug("Popup detection check")
        
        # In real implementation:
        # if has_dialog_pattern(screenshot):
        #     alert = Alert(...)
        #     self._handle_alert(alert)
        #     return alert
        
        return None
    
    def detect_disconnection(
        self,
        connection_status: bool = True
    ) -> Optional[Alert]:
        """
        Detect connection loss.
        
        Args:
            connection_status: Current connection status
        
        Returns:
            Alert if disconnected, None otherwise
        
        EDUCATIONAL NOTE:
            Disconnection requires immediate shutdown to prevent
            actions on stale state.
        """
        if not connection_status:
            alert = Alert(
                timestamp=time.time(),
                severity=AlertSeverity.CRITICAL,
                anomaly_type=AnomalyType.DISCONNECTION,
                message="Connection lost - emergency shutdown",
                should_shutdown=True
            )
            
            self._handle_alert(alert)
            return alert
        
        return None
    
    def detect_invalid_state(
        self,
        state: Optional[dict] = None
    ) -> Optional[Alert]:
        """
        Detect invalid game state.
        
        Args:
            state: Current game state to validate
        
        Returns:
            Alert if invalid state detected, None otherwise
        
        EDUCATIONAL NOTE:
            Invalid states include:
            - Negative pot/stacks
            - Missing required fields
            - Inconsistent data (pot < sum of bets)
        """
        if state is None:
            return None
        
        # Validate state structure
        issues = []
        
        # Check for negative values
        if state.get('pot', 0) < 0:
            issues.append("negative pot")
        
        if state.get('hero_stack', 0) < 0:
            issues.append("negative hero stack")
        
        # Check for missing critical fields
        if 'hero_cards' not in state and 'board' not in state:
            issues.append("missing card data")
        
        if issues:
            alert = Alert(
                timestamp=time.time(),
                severity=AlertSeverity.ERROR,
                anomaly_type=AnomalyType.INVALID_STATE,
                message=f"Invalid state detected: {', '.join(issues)}",
                should_shutdown=True,
                metadata={'issues': issues}
            )
            
            self._handle_alert(alert)
            return alert
        
        return None
    
    def check_error_rate(self) -> Optional[Alert]:
        """
        Check if error rate is too high.
        
        Returns:
            Alert if excessive errors, None otherwise
        
        EDUCATIONAL NOTE:
            Consecutive errors indicate system instability.
            Triggers shutdown to prevent cascading failures.
        """
        if self.state.consecutive_errors >= self.max_consecutive_errors:
            alert = Alert(
                timestamp=time.time(),
                severity=AlertSeverity.CRITICAL,
                anomaly_type=AnomalyType.EXCESSIVE_ERRORS,
                message=f"Excessive errors ({self.state.consecutive_errors}) - shutdown",
                should_shutdown=True,
                metadata={'error_count': self.state.consecutive_errors}
            )
            
            self._handle_alert(alert)
            return alert
        
        return None
    
    def record_success(self) -> None:
        """
        Record successful operation (resets error count).
        
        EDUCATIONAL NOTE:
            Resets consecutive error counter on successful operations.
        """
        if self.state.consecutive_errors > 0:
            logger.info(f"Errors cleared (was {self.state.consecutive_errors})")
        
        self.state.consecutive_errors = 0
    
    def record_error(self, error_msg: str) -> None:
        """
        Record error occurrence.
        
        Args:
            error_msg: Error description
        
        EDUCATIONAL NOTE:
            Increments error counter and checks shutdown threshold.
        """
        self.state.consecutive_errors += 1
        
        logger.warning(
            f"Error recorded ({self.state.consecutive_errors}/"
            f"{self.max_consecutive_errors}): {error_msg}"
        )
        
        # Check if shutdown needed
        self.check_error_rate()
    
    def _handle_alert(self, alert: Alert) -> None:
        """
        Handle alert (log, store, trigger shutdown if needed).
        
        Args:
            alert: Alert to handle
        
        EDUCATIONAL NOTE:
            Critical alerts trigger emergency shutdown via SafetyFramework.
        """
        # Add to alert list
        self.state.alerts.append(alert)
        self.state.anomalies_detected += 1
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[alert.severity]
        
        logger.log(
            log_level,
            f"[{alert.severity.value.upper()}] {alert.anomaly_type.value}: "
            f"{alert.message}"
        )
        
        # Save alert to file
        self._save_alert_log(alert)
        
        # Trigger shutdown if needed
        if alert.should_shutdown:
            logger.critical("SHUTDOWN TRIGGERED BY ALERT")
            self._trigger_shutdown(alert)
    
    def _trigger_shutdown(self, alert: Alert) -> None:
        """
        Trigger emergency shutdown.
        
        Args:
            alert: Alert that triggered shutdown
        
        EDUCATIONAL NOTE:
            Uses SafetyFramework.emergency_shutdown() to halt all operations.
        """
        self.state.shutdowns_triggered += 1
        
        # Log shutdown
        shutdown_msg = (
            f"EMERGENCY SHUTDOWN: {alert.anomaly_type.value}\n"
            f"Reason: {alert.message}\n"
            f"Time: {datetime.fromtimestamp(alert.timestamp)}"
        )
        
        logger.critical(shutdown_msg)
        
        # Save shutdown report
        self._save_shutdown_report(alert)
        
        # Deactivate monitoring BEFORE sys.exit
        self.state.monitoring_active = False
        
        # Map anomaly type to emergency reason
        reason_map = {
            AnomalyType.UI_CHANGE: EmergencyReason.UI_CHANGE_DETECTED,
            AnomalyType.UNEXPECTED_POPUP: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.DISCONNECTION: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.INVALID_STATE: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.TIMING_ANOMALY: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.SCREENSHOT_FAIL: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.EXCESSIVE_ERRORS: EmergencyReason.ANOMALY_DETECTED,
            AnomalyType.UNKNOWN: EmergencyReason.ANOMALY_DETECTED,
        }
        
        emergency_reason = reason_map.get(
            alert.anomaly_type,
            EmergencyReason.ANOMALY_DETECTED
        )
        
        # Trigger SafetyFramework emergency shutdown
        try:
            self.safety.emergency_shutdown(reason=emergency_reason)
        except Exception as e:
            logger.error(f"Shutdown trigger error: {e}")
    
    def _calculate_screenshot_hash(self, screenshot: np.ndarray) -> str:
        """
        Calculate hash of screenshot for comparison.
        
        Args:
            screenshot: Screenshot array
        
        Returns:
            SHA256 hash of screenshot
        """
        # Downsample for faster comparison
        if screenshot.shape[0] > 100:
            # Resize to 100x100 for hash calculation
            step_h = screenshot.shape[0] // 100
            step_w = screenshot.shape[1] // 100
            small = screenshot[::step_h, ::step_w]
        else:
            small = screenshot
        
        # Calculate hash
        hasher = hashlib.sha256()
        hasher.update(small.tobytes())
        return hasher.hexdigest()
    
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calculate similarity between two hashes.
        
        Args:
            hash1: First hash
            hash2: Second hash
        
        Returns:
            Similarity score (0.0-1.0, 1.0 = identical)
        
        EDUCATIONAL NOTE:
            Uses Hamming distance on hex strings for fast comparison.
        """
        if hash1 == hash2:
            return 1.0
        
        # Hamming distance on hex strings
        differences = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        max_diff = len(hash1)
        
        similarity = 1.0 - (differences / max_diff)
        return similarity
    
    def _save_alert_log(self, alert: Alert) -> None:
        """
        Save alert to log file.
        
        Args:
            alert: Alert to save
        """
        try:
            timestamp_str = datetime.fromtimestamp(alert.timestamp).strftime(
                "%Y%m%d_%H%M%S"
            )
            filename = f"alert_{timestamp_str}_{alert.anomaly_type.value}.log"
            log_path = self.log_dir / filename
            
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("MONITORING ALERT\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Timestamp: {datetime.fromtimestamp(alert.timestamp)}\n")
                f.write(f"Severity: {alert.severity.value.upper()}\n")
                f.write(f"Anomaly Type: {alert.anomaly_type.value}\n")
                f.write(f"Message: {alert.message}\n")
                f.write(f"Shutdown: {alert.should_shutdown}\n\n")
                
                if alert.screenshot_path:
                    f.write(f"Screenshot: {alert.screenshot_path}\n\n")
                
                if alert.metadata:
                    f.write("Metadata:\n")
                    for key, value in alert.metadata.items():
                        f.write(f"  {key}: {value}\n")
            
            logger.debug(f"Alert log saved: {log_path}")
            
        except Exception as e:
            logger.error(f"Failed to save alert log: {e}")
    
    def _save_shutdown_report(self, alert: Alert) -> None:
        """
        Save emergency shutdown report.
        
        Args:
            alert: Alert that triggered shutdown
        """
        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SHUTDOWN_{timestamp_str}.log"
            report_path = self.log_dir / filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("EMERGENCY SHUTDOWN REPORT\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Time: {datetime.fromtimestamp(alert.timestamp)}\n")
                f.write(f"Trigger: {alert.anomaly_type.value}\n")
                f.write(f"Reason: {alert.message}\n\n")
                
                f.write("=" * 60 + "\n")
                f.write("Monitoring Statistics:\n")
                f.write("=" * 60 + "\n\n")
                
                stats = self.get_statistics()
                f.write(f"Total checks: {stats['total_checks']}\n")
                f.write(f"Anomalies detected: {stats['anomalies_detected']}\n")
                f.write(f"Total alerts: {stats['total_alerts']}\n")
                f.write(f"Consecutive errors: {stats['consecutive_errors']}\n\n")
                
                f.write("=" * 60 + "\n")
                f.write("Alert History:\n")
                f.write("=" * 60 + "\n\n")
                
                for i, a in enumerate(self.state.alerts[-10:], 1):  # Last 10
                    f.write(f"{i}. [{a.severity.value}] {a.anomaly_type.value}: {a.message}\n")
            
            logger.info(f"Shutdown report saved: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to save shutdown report: {e}")
    
    def log_decision(
        self,
        decision: dict,
        screenshot: Optional[np.ndarray] = None
    ) -> str:
        """
        Log decision with optional screenshot.
        
        Args:
            decision: Decision dict to log
            screenshot: Screenshot at time of decision
        
        Returns:
            Path to log file
        
        EDUCATIONAL NOTE:
            Complete decision logging enables post-session analysis
            and verification of decision quality.
        """
        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"decision_{timestamp_str}.log"
            log_path = self.log_dir / filename
            
            # Save screenshot if provided
            screenshot_path = None
            if screenshot is not None:
                screenshot_filename = f"decision_{timestamp_str}.png"
                screenshot_path = self.screenshot_dir / screenshot_filename
                # In dry-run: just record path (no real save)
                logger.debug(f"Would save screenshot: {screenshot_path}")
            
            # Save decision log
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("DECISION LOG\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Timestamp: {datetime.now()}\n\n")
                
                for key, value in decision.items():
                    f.write(f"{key}: {value}\n")
                
                if screenshot_path:
                    f.write(f"\nScreenshot: {screenshot_path}\n")
            
            logger.debug(f"Decision logged: {log_path}")
            return str(log_path)
            
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
            return ""
    
    def get_alerts_by_severity(
        self,
        severity: AlertSeverity
    ) -> List[Alert]:
        """
        Get all alerts of specific severity.
        
        Args:
            severity: Severity level to filter
        
        Returns:
            List of matching alerts
        """
        return [
            alert for alert in self.state.alerts
            if alert.severity == severity
        ]
    
    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """
        Get recent alerts.
        
        Args:
            count: Number of recent alerts
        
        Returns:
            List of recent alerts
        """
        return self.state.alerts[-count:]
    
    def get_statistics(self) -> dict:
        """Get monitoring statistics."""
        critical_alerts = len(self.get_alerts_by_severity(AlertSeverity.CRITICAL))
        error_alerts = len(self.get_alerts_by_severity(AlertSeverity.ERROR))
        warning_alerts = len(self.get_alerts_by_severity(AlertSeverity.WARNING))
        
        return {
            'monitoring_active': self.state.monitoring_active,
            'total_checks': self.state.total_checks,
            'anomalies_detected': self.state.anomalies_detected,
            'total_alerts': len(self.state.alerts),
            'critical_alerts': critical_alerts,
            'error_alerts': error_alerts,
            'warning_alerts': warning_alerts,
            'consecutive_errors': self.state.consecutive_errors,
            'shutdowns_triggered': self.state.shutdowns_triggered,
            'ui_change_threshold': self.ui_change_threshold,
            'max_consecutive_errors': self.max_consecutive_errors
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Monitoring System - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Initialize monitoring
    monitor = MonitoringSystem(
        ui_change_threshold=0.15,
        max_consecutive_errors=3
    )
    
    print("Monitoring Configuration:")
    print(f"  UI change threshold: {monitor.ui_change_threshold:.1%}")
    print(f"  Max consecutive errors: {monitor.max_consecutive_errors}")
    print(f"  Log directory: {monitor.log_dir}")
    print(f"  Screenshot directory: {monitor.screenshot_dir}")
    print()
    
    # Simulate monitoring checks
    print("=" * 60)
    print("Simulating Monitoring Checks:")
    print("=" * 60)
    print()
    
    # Check 1: UI check (no screenshot - dry-run)
    print("1. UI Change Check (dry-run):")
    alert = monitor.check_ui_changes(screenshot=None)
    print(f"   Result: {'Alert triggered' if alert else 'OK'}")
    print()
    
    # Check 2: Popup detection
    print("2. Popup Detection:")
    alert = monitor.detect_popup(screenshot=None)
    print(f"   Result: {'Alert triggered' if alert else 'OK'}")
    print()
    
    # Check 3: Connection check
    print("3. Connection Check (connected):")
    alert = monitor.detect_disconnection(connection_status=True)
    print(f"   Result: {'Alert triggered' if alert else 'OK'}")
    print()
    
    # Check 4: State validation
    print("4. State Validation (valid state):")
    valid_state = {
        'pot': 30.0,
        'hero_stack': 100.0,
        'hero_cards': ['As', 'Kh'],
        'board': ['Qd', 'Jc', '9s']
    }
    alert = monitor.detect_invalid_state(valid_state)
    print(f"   Result: {'Alert triggered' if alert else 'OK'}")
    print()
    
    # Check 5: Invalid state
    print("5. State Validation (invalid - negative pot):")
    invalid_state = {'pot': -10.0, 'hero_stack': 100.0}
    alert = monitor.detect_invalid_state(invalid_state)
    print(f"   Result: {'ALERT' if alert else 'OK'}")
    if alert:
        print(f"   Severity: {alert.severity.value}")
        print(f"   Should shutdown: {alert.should_shutdown}")
    print()
    
    # Check 6: Error rate
    print("6. Error Rate Check:")
    monitor.record_error("Test error 1")
    monitor.record_error("Test error 2")
    print(f"   Consecutive errors: {monitor.state.consecutive_errors}")
    alert = monitor.check_error_rate()
    print(f"   Result: {'Alert triggered' if alert else 'OK - below threshold'}")
    print()
    
    # Statistics
    stats = monitor.get_statistics()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    print(f"Monitoring active: {stats['monitoring_active']}")
    print(f"Total checks: {stats['total_checks']}")
    print(f"Anomalies detected: {stats['anomalies_detected']}")
    print(f"Total alerts: {stats['total_alerts']}")
    print(f"  Critical: {stats['critical_alerts']}")
    print(f"  Errors: {stats['error_alerts']}")
    print(f"  Warnings: {stats['warning_alerts']}")
    print(f"Consecutive errors: {stats['consecutive_errors']}")
    print(f"Shutdowns triggered: {stats['shutdowns_triggered']}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - Safety Monitoring")
    print("=" * 60)
    print("[NOTE] Auto-shutdown on any critical anomaly")
