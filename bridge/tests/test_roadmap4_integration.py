"""
Roadmap4 Integration Tests - Final Validation.

Tests complete integration of all roadmap4 features:
- Phase 1: Unsafe action executor
- Phase 2: Vision enhancement + multi-room support
- Phase 3: Live testing pipeline
- Phase 4: Final safety & demo mode

EDUCATIONAL USE ONLY: Integration testing for HCI research prototype.
"""

import pytest

from bridge.action.real_executor import RealActionExecutor, RiskLevel
from bridge.demo_mode import DemoMode
from bridge.live_test_runner import LiveTestRunner, TestPhase
from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
from bridge.vision.training_data_collector import TrainingDataCollector


class TestPhase1Integration:
    """Test Phase 1: Unsafe Action Executor integration."""
    
    def test_real_executor_requires_unsafe_mode(self):
        """Test real executor requires unsafe mode."""
        # Create dry-run safety
        config = SafetyConfig(mode=SafetyMode.DRY_RUN)
        safety = SafetyFramework(config=config)
        
        # Should fail to initialize
        with pytest.raises(RuntimeError, match="requires UNSAFE mode"):
            RealActionExecutor(safety=safety)
    
    def test_real_executor_risk_classification(self):
        """Test risk classification system."""
        # Create unsafe safety
        config = SafetyConfig(mode=SafetyMode.UNSAFE)
        safety = SafetyFramework(config=config)
        
        try:
            executor = RealActionExecutor(safety=safety)
            
            # Test risk classification
            assert executor._classify_risk('fold', None) == RiskLevel.LOW
            assert executor._classify_risk('check', None) == RiskLevel.LOW
            assert executor._classify_risk('call', None) == RiskLevel.LOW
            assert executor._classify_risk('bet', 10.0) == RiskLevel.MEDIUM
            assert executor._classify_risk('raise', 20.0) == RiskLevel.MEDIUM
            assert executor._classify_risk('bet', 100.0) == RiskLevel.HIGH
            assert executor._classify_risk('allin', None) == RiskLevel.HIGH
            
        except ImportError:
            pytest.skip("pyautogui not available")


class TestPhase2Integration:
    """Test Phase 2: Vision enhancement + multi-room support."""
    
    def test_training_data_collector(self, tmp_path):
        """Test training data collector initialization."""
        collector = TrainingDataCollector(
            dataset_dir=str(tmp_path),
            room="pokerstars"
        )
        
        assert collector.room == "pokerstars"
        assert (tmp_path / "screenshots").exists()
        assert (tmp_path / "annotations").exists()
    
    @pytest.mark.parametrize("room_name", [
        "pokerstars",
        "ignition",
        "ggpoker",
        "888poker",
        "partypoker"
    ])
    def test_room_configs_exist(self, room_name):
        """Test all room configs exist."""
        from pathlib import Path
        
        config_path = Path("config/rooms") / f"{room_name}.yaml"
        assert config_path.exists(), f"Missing config for {room_name}"


class TestPhase3Integration:
    """Test Phase 3: Live testing pipeline."""
    
    def test_live_test_runner_initialization(self, tmp_path):
        """Test live test runner initialization."""
        runner = LiveTestRunner(
            room="pokerstars",
            dataset_dir=str(tmp_path)
        )
        
        assert runner.room == "pokerstars"
        assert runner.test_id.startswith("livetest_")
        assert (tmp_path / "screenshots").exists()
        assert (tmp_path / "logs").exists()
    
    def test_test_phases_defined(self):
        """Test all test phases are defined."""
        assert TestPhase.DRY_RUN.value == "dry_run"
        assert TestPhase.SAFE.value == "safe"
        assert TestPhase.MEDIUM_UNSAFE.value == "medium_unsafe"


class TestPhase4Integration:
    """Test Phase 4: Final safety & demo mode."""
    
    def test_demo_mode_initialization(self):
        """Test demo mode initialization."""
        demo = DemoMode()
        
        assert demo.state_bridge is not None
        assert demo.state_bridge.dry_run is True
    
    def test_enhanced_safety_vision_errors(self):
        """Test enhanced safety vision error tracking."""
        config = SafetyConfig(max_vision_errors=3)
        safety = SafetyFramework(config=config)
        
        # Record errors
        safety.record_vision_error()
        assert safety._consecutive_vision_errors == 1
        
        # Clear with success
        safety.record_vision_success()
        assert safety._consecutive_vision_errors == 0
    
    def test_enhanced_safety_hand_limit(self):
        """Test enhanced safety hand limit."""
        config = SafetyConfig(max_hands_per_session=10)
        safety = SafetyFramework(config=config)
        
        # Record hands
        for i in range(5):
            safety.record_hand_played()
        
        assert safety._hands_played == 5
        
        # Check session info
        info = safety.get_session_info()
        assert info['hands_played'] == 5
        assert info['hands_remaining'] == 5
    
    def test_enhanced_safety_session_timeout(self):
        """Test enhanced safety session timeout."""
        config = SafetyConfig(max_runtime_seconds=10)
        safety = SafetyFramework(config=config)
        
        # Should not timeout immediately
        timeout = safety.check_session_timeout()
        assert timeout is False
    
    def test_session_info_complete(self):
        """Test session info provides all metrics."""
        config = SafetyConfig(
            max_runtime_seconds=1800,
            max_vision_errors=3,
            max_hands_per_session=500
        )
        safety = SafetyFramework(config=config)
        
        info = safety.get_session_info()
        
        # All fields present
        required_fields = [
            'elapsed_seconds',
            'remaining_seconds',
            'hands_played',
            'hands_remaining',
            'consecutive_vision_errors',
            'vision_errors_until_shutdown',
            'shutdown_requested'
        ]
        
        for field in required_fields:
            assert field in info, f"Missing field: {field}"


class TestFullSystemIntegration:
    """Test complete system integration."""
    
    def test_all_components_available(self):
        """Test all roadmap4 components are available."""
        # Phase 1
        from bridge.action import RealActionExecutor, RiskLevel, ActionCoordinates
        
        # Phase 2
        from bridge.vision.training_data_collector import (
            TrainingDataCollector,
            CardAnnotation,
            NumericAnnotation
        )
        
        # Phase 3
        from bridge.live_test_runner import (
            LiveTestRunner,
            TestPhase,
            HandResult,
            PhaseMetrics
        )
        
        # Phase 4
        from bridge.demo_mode import DemoMode
        from bridge.safety import SafetyConfig, SafetyFramework
        
        # All imports successful
        assert True
    
    def test_safety_modes_hierarchy(self):
        """Test safety mode hierarchy."""
        # DRY_RUN -> SAFE -> UNSAFE progression
        modes = [SafetyMode.DRY_RUN, SafetyMode.SAFE, SafetyMode.UNSAFE]
        
        # Each mode has distinct value
        mode_values = [m.value for m in modes]
        assert len(mode_values) == len(set(mode_values))
        
        # Expected values
        assert SafetyMode.DRY_RUN.value == "dry_run"
        assert SafetyMode.SAFE.value == "safe"
        assert SafetyMode.UNSAFE.value == "unsafe"
    
    def test_risk_level_hierarchy(self):
        """Test risk level hierarchy."""
        # LOW -> MEDIUM -> HIGH progression
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        
        # Each level has distinct value
        level_values = [l.value for l in levels]
        assert len(level_values) == len(set(level_values))
        
        # Expected values
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
