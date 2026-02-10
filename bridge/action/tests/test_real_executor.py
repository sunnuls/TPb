"""
Tests for Real Action Executor (Roadmap4 Phase 1).

SAFETY NOTE: These tests do NOT execute real actions.
They test logic, safety checks, and risk classification only.
"""

import pytest

from bridge.action.real_executor import (
    ActionCoordinates,
    ExecutionLog,
    ExecutionResult,
    RealActionExecutor,
    RiskLevel,
)
from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode


class TestRiskLevel:
    """Test risk level enum."""
    
    def test_risk_levels(self):
        """Test risk level values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


class TestActionCoordinates:
    """Test action coordinates."""
    
    def test_button_only(self):
        """Test coordinates with button only."""
        coords = ActionCoordinates(button_x=100, button_y=200)
        
        assert coords.button_x == 100
        assert coords.button_y == 200
        assert coords.amount_field_x is None
        assert coords.amount_field_y is None
    
    def test_with_amount_field(self):
        """Test coordinates with amount field."""
        coords = ActionCoordinates(
            button_x=100,
            button_y=200,
            amount_field_x=150,
            amount_field_y=180
        )
        
        assert coords.button_x == 100
        assert coords.button_y == 200
        assert coords.amount_field_x == 150
        assert coords.amount_field_y == 180


class TestExecutionLog:
    """Test execution log."""
    
    def test_log_creation(self):
        """Test log entry creation."""
        coords = ActionCoordinates(button_x=100, button_y=200)
        
        log = ExecutionLog(
            timestamp=1234567890.0,
            action_type="fold",
            risk_level=RiskLevel.LOW,
            coordinates=coords,
            amount=None,
            result=ExecutionResult.SUCCESS,
            duration=0.5
        )
        
        assert log.action_type == "fold"
        assert log.risk_level == RiskLevel.LOW
        assert log.result == ExecutionResult.SUCCESS
        assert log.duration == 0.5


class TestRealActionExecutor:
    """Test real action executor (logic only, no real actions)."""
    
    def test_initialization_requires_unsafe_mode(self):
        """Test that initialization requires UNSAFE mode."""
        # Try with DRY_RUN mode (should fail)
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.DRY_RUN
        safety = SafetyFramework(config=safety_config)
        
        with pytest.raises(RuntimeError, match="requires UNSAFE mode"):
            RealActionExecutor(safety=safety)
    
    def test_initialization_unsafe_mode(self):
        """Test initialization in UNSAFE mode."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(
                safety=safety,
                max_risk_level=RiskLevel.LOW,
                humanization_enabled=True
            )
            
            assert executor.max_risk_level == RiskLevel.LOW
            assert executor.humanization_enabled is True
            assert executor.actions_executed == 0
            assert executor.actions_blocked == 0
            
        except ImportError:
            # pyautogui not available - skip test
            pytest.skip("pyautogui not available")
    
    def test_classify_risk_low(self):
        """Test risk classification for low-risk actions."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Low risk actions
            assert executor._classify_risk('fold', None) == RiskLevel.LOW
            assert executor._classify_risk('check', None) == RiskLevel.LOW
            assert executor._classify_risk('call', None) == RiskLevel.LOW
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_classify_risk_medium(self):
        """Test risk classification for medium-risk actions."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Medium risk actions
            assert executor._classify_risk('bet', 10.0) == RiskLevel.MEDIUM
            assert executor._classify_risk('raise', 20.0) == RiskLevel.MEDIUM
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_classify_risk_high(self):
        """Test risk classification for high-risk actions."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # High risk actions
            assert executor._classify_risk('allin', None) == RiskLevel.HIGH
            assert executor._classify_risk('bet', 100.0) == RiskLevel.HIGH
            assert executor._classify_risk('raise', 200.0) == RiskLevel.HIGH
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_check_safety_max_risk_level(self):
        """Test safety check respects max risk level."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            # Max LOW risk
            executor = RealActionExecutor(
                safety=safety,
                max_risk_level=RiskLevel.LOW
            )
            
            # LOW should be allowed
            assert executor._check_safety('fold', RiskLevel.LOW) is True
            
            # MEDIUM should be blocked
            assert executor._check_safety('bet', RiskLevel.MEDIUM) is False
            
            # HIGH should be blocked
            assert executor._check_safety('allin', RiskLevel.HIGH) is False
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_check_safety_mode(self):
        """Test safety check requires UNSAFE mode."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Change mode to DRY_RUN
            executor.safety.config.mode = SafetyMode.DRY_RUN
            
            # Should block action
            assert executor._check_safety('fold', RiskLevel.LOW) is False
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_validate_coordinates_valid(self):
        """Test coordinate validation for valid coordinates."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Valid coordinates (assuming standard screen size)
            coords = ActionCoordinates(button_x=800, button_y=600)
            assert executor._validate_coordinates(coords) is True
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_validate_coordinates_invalid(self):
        """Test coordinate validation for invalid coordinates."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Invalid coordinates (negative)
            coords = ActionCoordinates(button_x=-10, button_y=600)
            assert executor._validate_coordinates(coords) is False
            
            # Invalid coordinates (way too large)
            coords = ActionCoordinates(button_x=99999, button_y=600)
            assert executor._validate_coordinates(coords) is False
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_calculate_humanization_delay(self):
        """Test humanization delay calculation."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety, humanization_enabled=True)
            
            # LOW risk: 0.4-1.5s
            delay = executor._calculate_humanization_delay('fold', RiskLevel.LOW)
            assert 0.4 <= delay <= 1.5
            
            # MEDIUM risk: 1.0-2.5s
            delay = executor._calculate_humanization_delay('bet', RiskLevel.MEDIUM)
            assert 1.0 <= delay <= 2.5
            
            # HIGH risk: 2.0-3.5s
            delay = executor._calculate_humanization_delay('allin', RiskLevel.HIGH)
            assert 2.0 <= delay <= 3.5
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_execute_action_blocked_by_risk(self):
        """Test action execution blocked by risk level."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            # Max LOW risk
            executor = RealActionExecutor(
                safety=safety,
                max_risk_level=RiskLevel.LOW
            )
            
            coords = ActionCoordinates(button_x=800, button_y=600)
            
            # Try MEDIUM risk action
            log = executor.execute_action(
                action_type='bet',
                coordinates=coords,
                amount=10.0,
                risk_level=RiskLevel.MEDIUM
            )
            
            # Should be blocked
            assert log.result == ExecutionResult.BLOCKED_BY_SAFETY
            assert executor.actions_blocked == 1
            assert executor.actions_executed == 0
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_execute_action_invalid_coordinates(self):
        """Test action execution with invalid coordinates."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Invalid coordinates
            coords = ActionCoordinates(button_x=-10, button_y=600)
            
            log = executor.execute_action(
                action_type='fold',
                coordinates=coords
            )
            
            # Should fail validation
            assert log.result == ExecutionResult.INVALID_COORDINATES
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(
                safety=safety,
                max_risk_level=RiskLevel.MEDIUM,
                humanization_enabled=True
            )
            
            stats = executor.get_statistics()
            
            assert 'actions_executed' in stats
            assert 'actions_blocked' in stats
            assert 'max_risk_level' in stats
            assert 'humanization_enabled' in stats
            
            assert stats['max_risk_level'] == 'medium'
            assert stats['humanization_enabled'] is True
            
        except ImportError:
            pytest.skip("pyautogui not available")
    
    def test_get_execution_history(self):
        """Test execution history retrieval."""
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Initially empty
            history = executor.get_execution_history()
            assert len(history) == 0
            
            # Add a log entry
            coords = ActionCoordinates(button_x=-10, button_y=600)
            executor.execute_action('fold', coords)
            
            # Should have 1 entry
            history = executor.get_execution_history()
            assert len(history) == 1
            
        except ImportError:
            pytest.skip("pyautogui not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
