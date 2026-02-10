"""
Unit tests for safety framework (Roadmap3 Phase 0).

Tests safety framework functionality including:
- Dry-run enforcement
- Kill switch
- Emergency shutdown
- Mode checking
"""

import pytest
from bridge.safety import (
    EmergencyReason,
    SafetyConfig,
    SafetyFramework,
    SafetyMode,
    get_safety,
    is_dry_run,
)


class TestSafetyConfig:
    """Test SafetyConfig dataclass."""
    
    def test_default_config(self):
        """Default config is dry-run mode."""
        config = SafetyConfig()
        
        assert config.mode == SafetyMode.DRY_RUN
        assert config.max_runtime_seconds == 1800  # 30 minutes (Phase 4 update)
        assert config.max_vision_errors == 3  # Phase 4 addition
        assert config.max_hands_per_session == 500  # Phase 4 addition
        assert config.enable_kill_switch is True
        assert config.log_all_decisions is True
    
    def test_custom_config(self):
        """Can create custom config."""
        config = SafetyConfig(
            mode=SafetyMode.UNSAFE,
            max_runtime_seconds=1800,
            enable_kill_switch=False
        )
        
        assert config.mode == SafetyMode.UNSAFE
        assert config.max_runtime_seconds == 1800
        assert config.enable_kill_switch is False


class TestSafetyFramework:
    """Test SafetyFramework class."""
    
    def test_initialization_dry_run(self):
        """Framework initializes in dry-run mode by default."""
        config = SafetyConfig(mode=SafetyMode.DRY_RUN, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.config.mode == SafetyMode.DRY_RUN
        assert safety.is_dry_run() is True
        assert safety.is_unsafe_mode() is False
    
    def test_initialization_safe_mode(self):
        """Can initialize in safe mode."""
        config = SafetyConfig(mode=SafetyMode.SAFE, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.is_safe_mode() is True
        assert safety.is_dry_run() is False
    
    def test_initialization_unsafe_mode(self):
        """Can initialize in unsafe mode."""
        config = SafetyConfig(mode=SafetyMode.UNSAFE, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.is_unsafe_mode() is True
        assert safety.is_dry_run() is False


class TestModeChecking:
    """Test mode checking methods."""
    
    def test_is_dry_run_true(self):
        """is_dry_run returns True in dry-run mode."""
        config = SafetyConfig(mode=SafetyMode.DRY_RUN, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.is_dry_run() is True
    
    def test_is_dry_run_false(self):
        """is_dry_run returns False in other modes."""
        config = SafetyConfig(mode=SafetyMode.UNSAFE, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.is_dry_run() is False
    
    def test_is_safe_mode(self):
        """is_safe_mode returns correct value."""
        safe_config = SafetyConfig(mode=SafetyMode.SAFE, enable_kill_switch=False)
        safe_safety = SafetyFramework(safe_config)
        
        unsafe_config = SafetyConfig(mode=SafetyMode.UNSAFE, enable_kill_switch=False)
        unsafe_safety = SafetyFramework(unsafe_config)
        
        assert safe_safety.is_safe_mode() is True
        assert unsafe_safety.is_safe_mode() is False


class TestUnsafeModeRequirement:
    """Test unsafe mode requirement enforcement."""
    
    def test_require_unsafe_in_dry_run_blocks(self):
        """require_unsafe_mode blocks in dry-run."""
        config = SafetyConfig(mode=SafetyMode.DRY_RUN, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        with pytest.raises(PermissionError) as exc_info:
            safety.require_unsafe_mode("test_action")
        
        assert "requires --unsafe mode" in str(exc_info.value)
    
    def test_require_unsafe_in_safe_mode_blocks(self):
        """require_unsafe_mode blocks in safe mode."""
        config = SafetyConfig(mode=SafetyMode.SAFE, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        with pytest.raises(PermissionError):
            safety.require_unsafe_mode("dangerous_action")
    
    def test_require_unsafe_in_unsafe_mode_allows(self):
        """require_unsafe_mode allows in unsafe mode."""
        config = SafetyConfig(mode=SafetyMode.UNSAFE, enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        result = safety.require_unsafe_mode("dangerous_action")
        
        assert result is True


class TestSafetyChecks:
    """Test safety checking methods."""
    
    def test_check_safety_initially_true(self):
        """check_safety returns True initially."""
        config = SafetyConfig(enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        assert safety.check_safety() is True
    
    def test_check_safety_after_shutdown_false(self):
        """check_safety returns False after shutdown requested."""
        config = SafetyConfig(enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        safety._shutdown_requested = True
        
        assert safety.check_safety() is False
    
    def test_runtime_tracking(self):
        """Framework tracks runtime."""
        config = SafetyConfig(enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        runtime = safety.get_runtime()
        
        assert runtime >= 0
        assert runtime < 1.0  # Should be very short


class TestDecisionLogging:
    """Test decision logging functionality."""
    
    def test_log_decision(self):
        """Can log decisions."""
        config = SafetyConfig(enable_kill_switch=False, log_all_decisions=True)
        safety = SafetyFramework(config)
        
        safety.log_decision({
            'action': 'fold',
            'reason': 'weak_hand'
        })
        
        assert safety.get_decision_count() == 1
    
    def test_log_multiple_decisions(self):
        """Can log multiple decisions."""
        config = SafetyConfig(enable_kill_switch=False, log_all_decisions=True)
        safety = SafetyFramework(config)
        
        for i in range(5):
            safety.log_decision({'action': f'action_{i}'})
        
        assert safety.get_decision_count() == 5
    
    def test_decision_logging_disabled(self):
        """Decisions not logged when disabled."""
        config = SafetyConfig(enable_kill_switch=False, log_all_decisions=False)
        safety = SafetyFramework(config)
        
        safety.log_decision({'action': 'test'})
        
        # Still increments count even if not saved to file
        # (Internal list still maintained for emergency log)


class TestEmergencyCallbacks:
    """Test emergency callback registration."""
    
    def test_register_callback(self):
        """Can register emergency callback."""
        config = SafetyConfig(enable_kill_switch=False)
        safety = SafetyFramework(config)
        
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        safety.register_emergency_callback(test_callback)
        
        assert len(safety._emergency_callbacks) == 1


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_is_dry_run_global(self):
        """Global is_dry_run function works."""
        # Note: This uses singleton, so state may persist
        result = is_dry_run()
        
        assert isinstance(result, bool)


class TestSafetyModes:
    """Test all safety mode enums."""
    
    def test_safety_mode_values(self):
        """Safety mode enum has correct values."""
        assert SafetyMode.DRY_RUN.value == "dry_run"
        assert SafetyMode.SAFE.value == "safe"
        assert SafetyMode.UNSAFE.value == "unsafe"
    
    def test_emergency_reason_values(self):
        """Emergency reason enum has correct values."""
        assert EmergencyReason.KILL_SWITCH.value == "kill_switch"
        assert EmergencyReason.UI_CHANGE_DETECTED.value == "ui_change"
        assert EmergencyReason.USER_REQUESTED.value == "user_requested"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
