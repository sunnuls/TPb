"""
Tests for Enhanced Safety Features (Roadmap4 Phase 4).

Tests new safety limits:
- Vision error tracking and auto-shutdown
- Session hand limit
- Session timeout (30 min default)
- Session info tracking
"""

import time

import pytest

from bridge.safety import EmergencyReason, SafetyConfig, SafetyFramework, SafetyMode


class TestEnhancedSafetyConfig:
    """Test enhanced safety configuration."""
    
    def test_default_config(self):
        """Test default safety config with phase 4 enhancements."""
        config = SafetyConfig()
        
        assert config.mode == SafetyMode.DRY_RUN
        assert config.max_runtime_seconds == 1800  # 30 minutes
        assert config.max_vision_errors == 3
        assert config.max_hands_per_session == 500
    
    def test_custom_config(self):
        """Test custom safety config."""
        config = SafetyConfig(
            max_runtime_seconds=600,    # 10 minutes
            max_vision_errors=5,
            max_hands_per_session=100
        )
        
        assert config.max_runtime_seconds == 600
        assert config.max_vision_errors == 5
        assert config.max_hands_per_session == 100


class TestVisionErrorTracking:
    """Test vision error tracking and shutdown."""
    
    def test_record_vision_error(self):
        """Test recording vision errors."""
        config = SafetyConfig(max_vision_errors=3)
        safety = SafetyFramework(config=config)
        
        # Record error
        safety.record_vision_error()
        
        assert safety._consecutive_vision_errors == 1
    
    def test_record_vision_success_clears_errors(self):
        """Test that success clears error count."""
        config = SafetyConfig(max_vision_errors=3)
        safety = SafetyFramework(config=config)
        
        # Record errors
        safety.record_vision_error()
        safety.record_vision_error()
        
        assert safety._consecutive_vision_errors == 2
        
        # Record success
        safety.record_vision_success()
        
        # Should be cleared
        assert safety._consecutive_vision_errors == 0
    
    def test_vision_error_threshold_shutdown(self):
        """Test shutdown on vision error threshold."""
        config = SafetyConfig(max_vision_errors=3)
        safety = SafetyFramework(config=config)
        
        # Record errors below threshold
        safety.record_vision_error()
        safety.record_vision_error()
        
        assert safety._consecutive_vision_errors == 2
        
        # Third error should trigger shutdown
        with pytest.raises(SystemExit):
            safety.record_vision_error()


class TestHandLimitTracking:
    """Test hand limit tracking and auto-logout."""
    
    def test_record_hand_played(self):
        """Test recording hands played."""
        config = SafetyConfig(max_hands_per_session=10)
        safety = SafetyFramework(config=config)
        
        # Record hands
        for i in range(5):
            safety.record_hand_played()
        
        assert safety._hands_played == 5
    
    def test_hand_limit_shutdown(self):
        """Test shutdown on hand limit."""
        config = SafetyConfig(max_hands_per_session=3)
        safety = SafetyFramework(config=config)
        
        # Record hands up to limit
        safety.record_hand_played()
        safety.record_hand_played()
        
        assert safety._hands_played == 2
        
        # Reaching limit should trigger shutdown
        with pytest.raises(SystemExit):
            safety.record_hand_played()


class TestSessionTimeout:
    """Test session timeout checking."""
    
    def test_check_session_timeout_not_exceeded(self):
        """Test timeout check when not exceeded."""
        config = SafetyConfig(max_runtime_seconds=10)
        safety = SafetyFramework(config=config)
        
        # Should not timeout immediately
        timeout = safety.check_session_timeout()
        
        assert timeout is False
    
    def test_check_session_timeout_exceeded(self):
        """Test timeout check when exceeded."""
        config = SafetyConfig(max_runtime_seconds=1)
        safety = SafetyFramework(config=config)
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Should trigger shutdown
        with pytest.raises(SystemExit):
            safety.check_session_timeout()


class TestSessionInfo:
    """Test session info retrieval."""
    
    def test_get_session_info_initial(self):
        """Test session info at start."""
        config = SafetyConfig(
            max_runtime_seconds=1800,
            max_vision_errors=3,
            max_hands_per_session=500
        )
        safety = SafetyFramework(config=config)
        
        info = safety.get_session_info()
        
        # Check fields
        assert 'elapsed_seconds' in info
        assert 'remaining_seconds' in info
        assert 'hands_played' in info
        assert 'hands_remaining' in info
        assert 'consecutive_vision_errors' in info
        assert 'vision_errors_until_shutdown' in info
        assert 'shutdown_requested' in info
        
        # Check initial values
        assert info['elapsed_seconds'] >= 0
        assert info['remaining_seconds'] <= 1800
        assert info['hands_played'] == 0
        assert info['hands_remaining'] == 500
        assert info['consecutive_vision_errors'] == 0
        assert info['vision_errors_until_shutdown'] == 3
        assert info['shutdown_requested'] is False
    
    def test_get_session_info_after_activity(self):
        """Test session info after some activity."""
        config = SafetyConfig(
            max_runtime_seconds=3600,
            max_vision_errors=3,
            max_hands_per_session=100
        )
        safety = SafetyFramework(config=config)
        
        # Record some activity
        safety.record_hand_played()
        safety.record_hand_played()
        safety.record_vision_error()
        
        info = safety.get_session_info()
        
        # Check updated values
        assert info['hands_played'] == 2
        assert info['hands_remaining'] == 98
        assert info['consecutive_vision_errors'] == 1
        assert info['vision_errors_until_shutdown'] == 2
    
    def test_get_session_info_near_limits(self):
        """Test session info near limits."""
        config = SafetyConfig(
            max_runtime_seconds=10,
            max_vision_errors=3,
            max_hands_per_session=5
        )
        safety = SafetyFramework(config=config)
        
        # Near hand limit
        for i in range(4):
            safety.record_hand_played()
        
        # Near vision error limit
        safety.record_vision_error()
        safety.record_vision_error()
        
        info = safety.get_session_info()
        
        # Check warnings
        assert info['hands_remaining'] == 1
        assert info['vision_errors_until_shutdown'] == 1


class TestIntegratedSafety:
    """Test integrated safety features."""
    
    def test_multiple_safety_mechanisms(self):
        """Test multiple safety mechanisms work together."""
        config = SafetyConfig(
            max_runtime_seconds=3600,
            max_vision_errors=3,
            max_hands_per_session=10
        )
        safety = SafetyFramework(config=config)
        
        # Simulate session activity
        for i in range(5):
            safety.record_hand_played()
        
        safety.record_vision_error()
        
        info = safety.get_session_info()
        
        # All tracking should work
        assert info['hands_played'] == 5
        assert info['consecutive_vision_errors'] == 1
        assert info['shutdown_requested'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
