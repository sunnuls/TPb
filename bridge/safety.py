"""
Safety Framework for HCI Research Bridge (Roadmap3 Phase 0).

EDUCATIONAL USE ONLY: This module is designed for Human-Computer Interaction
research studying external desktop application interfaces. All operations are
in DRY-RUN mode by default. Real actions require explicit --unsafe flag.

WARNING: This is a research prototype. Real-world use is PROHIBITED without
proper authorization and ethical review.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SafetyMode(str, Enum):
    """Safety operation modes for HCI research."""
    DRY_RUN = "dry_run"        # Default: Log only, no real actions
    SAFE = "safe"              # Conservative: fold/check/call only
    UNSAFE = "unsafe"          # Full access: all actions (requires explicit flag)


class EmergencyReason(str, Enum):
    """Reasons for emergency shutdown."""
    KILL_SWITCH = "kill_switch"
    UI_CHANGE_DETECTED = "ui_change"
    ANOMALY_DETECTED = "anomaly"
    USER_REQUESTED = "user_requested"
    TIMEOUT = "timeout"
    PERMISSION_ERROR = "permission_error"


@dataclass
class SafetyConfig:
    """
    Configuration for safety framework.
    
    Attributes:
        mode: Operating mode (default: DRY_RUN)
        max_runtime_seconds: Maximum runtime before auto-shutdown
        max_vision_errors: Maximum consecutive vision errors before shutdown
        max_hands_per_session: Maximum hands per session before auto-logout
        enable_kill_switch: Enable global emergency kill switch
        log_all_decisions: Log every decision to file
        screenshot_on_action: Capture screenshot before each action
    """
    mode: SafetyMode = SafetyMode.DRY_RUN
    max_runtime_seconds: int = 1800  # 30 minutes default (changed from 1 hour)
    max_vision_errors: int = 3  # Auto-stop after 3 consecutive vision errors
    max_hands_per_session: int = 500  # Auto-logout after 500 hands
    enable_kill_switch: bool = True
    log_all_decisions: bool = True
    screenshot_on_action: bool = True


class SafetyFramework:
    """
    Global safety framework for HCI research bridge.
    
    Features:
    - Global kill switch (Ctrl+C handler)
    - Dry-run enforcement
    - Emergency shutdown
    - Runtime limits
    - Decision logging
    
    EDUCATIONAL NOTE:
        This framework ensures all research operations remain in controlled
        sandbox environment. Real actions are BLOCKED by default.
    """
    
    _instance: Optional['SafetyFramework'] = None
    _lock = threading.Lock()
    
    def __init__(self, config: Optional[SafetyConfig] = None):
        """
        Initialize safety framework (singleton).
        
        Args:
            config: Safety configuration (defaults to DRY_RUN)
        """
        self.config = config or SafetyConfig()
        self._shutdown_requested = False
        self._start_time = time.time()
        self._emergency_callbacks: list[Callable] = []
        self._decision_log: list[dict] = []
        
        # Enhanced safety tracking (Phase 4)
        self._consecutive_vision_errors = 0
        self._hands_played = 0
        
        # Setup kill switch
        if self.config.enable_kill_switch:
            self._setup_kill_switch()
        
        logger.info(f"Safety Framework initialized in {self.config.mode.value.upper()} mode")
        logger.info(f"Educational HCI Research Prototype - Real actions {'ENABLED' if self.config.mode == SafetyMode.UNSAFE else 'DISABLED'}")
    
    @classmethod
    def get_instance(cls, config: Optional[SafetyConfig] = None) -> 'SafetyFramework':
        """Get singleton instance of safety framework."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance
    
    def _setup_kill_switch(self) -> None:
        """Setup emergency kill switch (Ctrl+C handler)."""
        def signal_handler(sig, frame):
            logger.critical("KILL SWITCH ACTIVATED - Emergency shutdown initiated")
            self.emergency_shutdown(EmergencyReason.KILL_SWITCH)
        
        signal.signal(signal.SIGINT, signal_handler)
        logger.info("Kill switch (Ctrl+C) registered")
    
    def check_safety(self) -> bool:
        """
        Check if operation is safe to continue.
        
        Returns:
            True if safe, False if should shutdown
        """
        # Check shutdown flag
        if self._shutdown_requested:
            logger.warning("Shutdown requested - blocking operation")
            return False
        
        # Check runtime limit
        runtime = time.time() - self._start_time
        if runtime > self.config.max_runtime_seconds:
            logger.critical(f"Runtime limit exceeded ({runtime:.1f}s > {self.config.max_runtime_seconds}s)")
            self.emergency_shutdown(EmergencyReason.TIMEOUT)
            return False
        
        return True
    
    def is_dry_run(self) -> bool:
        """Check if in dry-run mode (no real actions)."""
        return self.config.mode == SafetyMode.DRY_RUN
    
    def is_safe_mode(self) -> bool:
        """Check if in safe mode (conservative actions only)."""
        return self.config.mode == SafetyMode.SAFE
    
    def is_unsafe_mode(self) -> bool:
        """Check if in unsafe mode (all actions allowed)."""
        return self.config.mode == SafetyMode.UNSAFE
    
    def require_unsafe_mode(self, action_name: str) -> bool:
        """
        Check if action requires unsafe mode.
        
        Args:
            action_name: Name of action to perform
            
        Returns:
            True if allowed, False if blocked
            
        Raises:
            PermissionError if action blocked
        """
        if not self.is_unsafe_mode():
            error_msg = (
                f"Action '{action_name}' requires --unsafe mode. "
                f"Current mode: {self.config.mode.value}. "
                f"Educational HCI research prototype - real actions BLOCKED."
            )
            logger.error(error_msg)
            self.log_decision({
                'action': action_name,
                'blocked': True,
                'reason': 'requires_unsafe_mode',
                'current_mode': self.config.mode.value
            })
            raise PermissionError(error_msg)
        
        return True
    
    def log_decision(self, decision_data: dict) -> None:
        """
        Log decision for research tracking.
        
        Args:
            decision_data: Decision details to log
        """
        if self.config.log_all_decisions:
            decision_data['timestamp'] = time.time()
            decision_data['mode'] = self.config.mode.value
            self._decision_log.append(decision_data)
            
            logger.info(f"Decision logged: {decision_data.get('action', 'unknown')}")
    
    def register_emergency_callback(self, callback: Callable) -> None:
        """
        Register callback to execute on emergency shutdown.
        
        Args:
            callback: Function to call on shutdown
        """
        self._emergency_callbacks.append(callback)
        logger.debug(f"Emergency callback registered: {callback.__name__}")
    
    def record_vision_error(self) -> None:
        """
        Record vision error occurrence.
        
        EDUCATIONAL NOTE (Phase 4):
            Tracks consecutive vision errors and triggers shutdown
            if threshold exceeded (default: 3 errors).
        """
        self._consecutive_vision_errors += 1
        
        logger.warning(
            f"Vision error recorded ({self._consecutive_vision_errors}/"
            f"{self.config.max_vision_errors})"
        )
        
        # Check if threshold exceeded
        if self._consecutive_vision_errors >= self.config.max_vision_errors:
            logger.critical(
                f"VISION ERROR THRESHOLD EXCEEDED: "
                f"{self._consecutive_vision_errors} consecutive errors"
            )
            self.emergency_shutdown(EmergencyReason.ANOMALY_DETECTED)
    
    def record_vision_success(self) -> None:
        """
        Record successful vision extraction.
        
        EDUCATIONAL NOTE:
            Resets consecutive error counter on success.
        """
        if self._consecutive_vision_errors > 0:
            logger.info(
                f"Vision errors cleared (was {self._consecutive_vision_errors})"
            )
        
        self._consecutive_vision_errors = 0
    
    def record_hand_played(self) -> None:
        """
        Record hand played (increments counter).
        
        EDUCATIONAL NOTE (Phase 4):
            Tracks total hands and triggers auto-logout if
            max_hands_per_session exceeded.
        """
        self._hands_played += 1
        
        # Check if session limit reached
        if self._hands_played >= self.config.max_hands_per_session:
            logger.critical(
                f"SESSION HAND LIMIT REACHED: {self._hands_played} hands"
            )
            self.emergency_shutdown(EmergencyReason.TIMEOUT)
    
    def check_session_timeout(self) -> bool:
        """
        Check if session has exceeded time limit.
        
        Returns:
            True if timeout exceeded, False otherwise
        
        EDUCATIONAL NOTE (Phase 4):
            Checks elapsed time against max_runtime_seconds.
            Default: 30 minutes.
        """
        elapsed = time.time() - self._start_time
        
        if elapsed >= self.config.max_runtime_seconds:
            logger.critical(
                f"SESSION TIMEOUT: {elapsed:.1f}s (limit: "
                f"{self.config.max_runtime_seconds}s)"
            )
            self.emergency_shutdown(EmergencyReason.TIMEOUT)
            return True
        
        return False
    
    def get_session_info(self) -> dict:
        """
        Get current session information.
        
        Returns:
            Dict with session stats
        
        EDUCATIONAL NOTE:
            Provides real-time session monitoring data.
        """
        elapsed = time.time() - self._start_time
        remaining = self.config.max_runtime_seconds - elapsed
        
        return {
            'elapsed_seconds': elapsed,
            'remaining_seconds': max(0, remaining),
            'hands_played': self._hands_played,
            'hands_remaining': max(0, self.config.max_hands_per_session - self._hands_played),
            'consecutive_vision_errors': self._consecutive_vision_errors,
            'vision_errors_until_shutdown': max(
                0,
                self.config.max_vision_errors - self._consecutive_vision_errors
            ),
            'shutdown_requested': self._shutdown_requested
        }
    
    def emergency_shutdown(self, reason: EmergencyReason) -> None:
        """
        Trigger emergency shutdown.
        
        Args:
            reason: Reason for shutdown
        """
        if self._shutdown_requested:
            return  # Already shutting down
        
        self._shutdown_requested = True
        
        logger.critical("=" * 60)
        logger.critical("EMERGENCY SHUTDOWN TRIGGERED")
        logger.critical(f"Reason: {reason.value}")
        logger.critical("=" * 60)
        
        # Execute emergency callbacks
        for callback in self._emergency_callbacks:
            try:
                logger.info(f"Executing emergency callback: {callback.__name__}")
                callback()
            except Exception as e:
                logger.error(f"Emergency callback failed: {e}")
        
        # Save decision log
        if self._decision_log:
            try:
                import json
                log_file = f"emergency_log_{int(time.time())}.json"
                with open(log_file, 'w') as f:
                    json.dump(self._decision_log, f, indent=2)
                logger.info(f"Decision log saved to {log_file}")
            except Exception as e:
                logger.error(f"Failed to save decision log: {e}")
        
        logger.critical("Emergency shutdown complete")
        sys.exit(1)
    
    def get_runtime(self) -> float:
        """Get current runtime in seconds."""
        return time.time() - self._start_time
    
    def get_decision_count(self) -> int:
        """Get number of logged decisions."""
        return len(self._decision_log)


# Global convenience functions
def get_safety() -> SafetyFramework:
    """Get global safety framework instance."""
    return SafetyFramework.get_instance()


def is_dry_run() -> bool:
    """Check if in dry-run mode."""
    return get_safety().is_dry_run()


def require_unsafe(action_name: str) -> bool:
    """Require unsafe mode for action."""
    return get_safety().require_unsafe_mode(action_name)


def emergency_shutdown(reason: EmergencyReason = EmergencyReason.USER_REQUESTED) -> None:
    """Trigger emergency shutdown."""
    get_safety().emergency_shutdown(reason)


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("HCI Research Safety Framework - Educational Demo")
    print("=" * 60)
    print()
    
    # Demo: Dry-run mode (default)
    safety = SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    
    print(f"Current mode: {safety.config.mode.value}")
    print(f"Is dry-run: {safety.is_dry_run()}")
    print(f"Is unsafe: {safety.is_unsafe_mode()}")
    print()
    
    # Try action in dry-run mode
    print("Attempting 'click_button' in DRY-RUN mode:")
    try:
        safety.require_unsafe_mode("click_button")
    except PermissionError as e:
        print(f"  ✗ BLOCKED: {e}")
    print()
    
    # Log decision
    safety.log_decision({
        'action': 'fold',
        'reason': 'weak_hand',
        'equity': 0.25
    })
    print(f"Decisions logged: {safety.get_decision_count()}")
    print()
    
    # Check safety
    print(f"Safety check: {'PASS' if safety.check_safety() else 'FAIL'}")
    print(f"Runtime: {safety.get_runtime():.2f}s")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - All operations in DRY-RUN mode")
    print("Real actions require explicit --unsafe flag")
    print("=" * 60)
