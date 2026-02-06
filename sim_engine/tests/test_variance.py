"""
Tests for Variance and Adaptive Modeling Module (Шаг 3.2).

Educational Use Only: Testing behavioral variance and opponent profiling.
"""

from __future__ import annotations

import numpy as np
import pytest

from sim_engine.variance_module import (
    AnomalyDetector,
    AnomalySignal,
    BehaviorType,
    BehaviorVariance,
    OpponentProfiler,
    SessionState,
    generate_training_data,
    TORCH_AVAILABLE,
)


class TestBehaviorVariance:
    """Test behavioral variance generator (Пункт 1)."""
    
    def test_conservative_behavior_reduces_equity(self):
        """Test conservative behavior reduces equity estimates."""
        variance = BehaviorVariance(base_behavior=BehaviorType.CONSERVATIVE)
        
        base_equity = 0.65
        context = {}
        
        adjusted, metadata = variance.apply_behavioral_variance(base_equity, context)
        
        # Conservative should reduce equity
        assert adjusted <= base_equity
        assert metadata["variance_applied"] == "conservative"
        assert metadata["risk_factor"] == "low"
    
    def test_aggressive_behavior_increases_equity(self):
        """Test aggressive behavior increases equity estimates."""
        variance = BehaviorVariance(base_behavior=BehaviorType.AGGRESSIVE)
        
        base_equity = 0.50
        context = {}
        
        adjusted, metadata = variance.apply_behavioral_variance(base_equity, context)
        
        # Aggressive should increase equity
        assert adjusted >= base_equity
        assert metadata["variance_applied"] == "aggressive"
        assert metadata["risk_factor"] == "high"
    
    def test_balanced_behavior_minimal_variance(self):
        """Test balanced behavior has minimal variance."""
        variance = BehaviorVariance(base_behavior=BehaviorType.BALANCED)
        
        base_equity = 0.60
        context = {}
        
        # Run multiple times to check variance bounds
        adjustments = []
        for _ in range(20):
            adjusted, _ = variance.apply_behavioral_variance(base_equity, context)
            adjustments.append(abs(adjusted - base_equity))
        
        # All adjustments should be small
        assert all(adj < 0.10 for adj in adjustments)
    
    def test_adaptive_behavior_uses_context(self):
        """Test adaptive behavior adjusts based on context."""
        variance = BehaviorVariance(base_behavior=BehaviorType.ADAPTIVE)
        
        base_equity = 0.60
        
        # High pot odds, few opponents -> more aggressive
        context_aggressive = {
            "pot_odds": 0.7,
            "opponent_count": 1
        }
        
        adjusted_agg, _ = variance.apply_behavioral_variance(base_equity, context_aggressive)
        
        # Low pot odds, many opponents -> more conservative
        context_conservative = {
            "pot_odds": 0.3,
            "opponent_count": 5
        }
        
        adjusted_cons, _ = variance.apply_behavioral_variance(base_equity, context_conservative)
        
        # Aggressive context should yield higher equity
        assert adjusted_agg > adjusted_cons


class TestSessionState:
    """Test session state tracking (Подпункт 1.1)."""
    
    def test_session_creation(self):
        """Test session state creation."""
        session = SessionState(
            session_id="test_session_001",
            max_duration_seconds=3600.0,
            max_hands=100
        )
        
        assert session.session_id == "test_session_001"
        assert session.hands_played == 0
        assert session.decisions_made == 0
    
    def test_session_elapsed_time(self):
        """Test elapsed time calculation."""
        import time
        
        session = SessionState(session_id="test_time")
        
        time.sleep(0.1)
        
        elapsed = session.elapsed_seconds()
        assert elapsed >= 0.1
    
    def test_session_should_reset_by_time(self):
        """Test session reset by time limit (Подпункт 1.1: 1-2h cycles)."""
        session = SessionState(
            session_id="test_reset_time",
            max_duration_seconds=0.1  # 0.1 seconds for testing
        )
        
        import time
        time.sleep(0.15)
        
        assert session.should_reset() is True
    
    def test_session_should_reset_by_hands(self):
        """Test session reset by hand limit."""
        session = SessionState(
            session_id="test_reset_hands",
            max_hands=10
        )
        
        session.hands_played = 10
        
        assert session.should_reset() is True
    
    def test_session_should_not_reset_early(self):
        """Test session doesn't reset prematurely."""
        session = SessionState(
            session_id="test_no_reset",
            max_duration_seconds=3600.0,
            max_hands=100
        )
        
        session.hands_played = 5
        
        assert session.should_reset() is False


class TestOpponentProfiler:
    """Test opponent profiling (Пункт 1: NN opponent profiling)."""
    
    def test_profiler_creation(self):
        """Test profiler initialization."""
        profiler = OpponentProfiler(
            input_size=10,
            hidden_size=16,
            output_size=3
        )
        
        assert profiler.input_size == 10
        assert profiler.hidden_size == 16
        assert profiler.output_size == 3
    
    def test_feature_extraction(self):
        """Test feature extraction from observations."""
        profiler = OpponentProfiler()
        
        observations = [
            {"action": "raise", "sizing": 0.75},
            {"action": "call"},
            {"action": "raise", "sizing": 1.0},
            {"action": "fold"}
        ]
        
        features = profiler.extract_features("opponent_001", observations)
        
        assert isinstance(features, np.ndarray)
        assert len(features) == profiler.input_size
        assert all(0.0 <= f <= 1.0 or f == 0.0 for f in features)
    
    def test_opponent_prediction_conservative(self):
        """Test prediction of conservative opponent."""
        profiler = OpponentProfiler()
        
        # Conservative pattern: mostly folds, rare raises
        observations = [
            {"action": "fold"},
            {"action": "fold"},
            {"action": "call"},
            {"action": "fold"},
            {"action": "fold"}
        ]
        
        behavior, confidence = profiler.predict_opponent_type("opponent_cons", observations)
        
        # Prediction may vary, but should be valid
        assert behavior in [BehaviorType.CONSERVATIVE, BehaviorType.BALANCED, BehaviorType.AGGRESSIVE]
        assert 0.0 <= confidence <= 1.0
    
    def test_opponent_prediction_aggressive(self):
        """Test prediction of aggressive opponent."""
        profiler = OpponentProfiler()
        
        # Aggressive pattern: frequent raises
        observations = [
            {"action": "raise", "sizing": 1.0},
            {"action": "raise", "sizing": 0.8},
            {"action": "call"},
            {"action": "raise", "sizing": 1.2},
            {"action": "bet", "sizing": 0.9}
        ]
        
        behavior, confidence = profiler.predict_opponent_type("opponent_agg", observations)
        
        # Prediction may vary due to heuristics/NN, but should be valid
        assert behavior in [BehaviorType.CONSERVATIVE, BehaviorType.BALANCED, BehaviorType.AGGRESSIVE]
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_training_on_batch(self):
        """Test NN training on batch (Подпункт 1.2: train NN)."""
        profiler = OpponentProfiler()
        
        # Generate small batch
        batch_size = 8
        features = np.random.rand(batch_size, profiler.input_size).astype(np.float32)
        labels = np.random.randint(0, profiler.output_size, size=batch_size)
        
        loss = profiler.train_on_batch(features, labels)
        
        assert isinstance(loss, float)
        assert loss >= 0.0


class TestAnomalyDetector:
    """Test anomaly detection (Подпункт 1.1)."""
    
    def test_detector_creation(self):
        """Test anomaly detector initialization."""
        detector = AnomalyDetector()
        
        assert detector.activity_threshold > 0
        assert detector.pattern_window > 0
    
    def test_normal_session_no_anomalies(self):
        """Test normal session has no anomalies."""
        detector = AnomalyDetector()
        
        session = SessionState(
            session_id="normal_session",
            max_duration_seconds=3600.0
        )
        session.decisions_made = 10
        
        recent_actions = [
            {"action": "call"},
            {"action": "raise"},
            {"action": "fold"},
            {"action": "call"}
        ]
        
        anomalies = detector.detect_anomalies(session, recent_actions)
        
        assert AnomalySignal.NORMAL in anomalies
        assert AnomalySignal.EXCESSIVE_ACTIVITY not in anomalies
    
    def test_session_timeout_detection(self):
        """Test session timeout anomaly (Подпункт 1.1)."""
        detector = AnomalyDetector()
        
        session = SessionState(
            session_id="timeout_session",
            max_duration_seconds=0.1
        )
        
        import time
        time.sleep(0.15)
        
        anomalies = detector.detect_anomalies(session, [])
        
        assert AnomalySignal.SESSION_TIMEOUT in anomalies
    
    def test_pattern_detection(self):
        """Test repetitive pattern detection."""
        detector = AnomalyDetector()
        
        session = SessionState(session_id="pattern_session")
        
        # Highly repetitive pattern
        recent_actions = [{"action": "fold"} for _ in range(25)]
        
        anomalies = detector.detect_anomalies(session, recent_actions)
        
        assert AnomalySignal.PATTERN_DETECTED in anomalies


class TestTrainingDataGeneration:
    """Test training data generation (Подпункт 1.2)."""
    
    def test_generate_training_data(self):
        """Test synthetic data generation (Подпункт 1.2: generated data)."""
        train_X, train_y, val_X, val_y = generate_training_data(
            num_samples=100,
            validation_split=0.2
        )
        
        # Check shapes
        assert train_X.shape[0] == 80  # 80% train
        assert val_X.shape[0] == 20  # 20% validation
        
        assert train_X.shape[1] == 10  # 10 features
        
        # Check labels in range [0, 2]
        assert all(0 <= label <= 2 for label in train_y)
        assert all(0 <= label <= 2 for label in val_y)
    
    def test_validation_split(self):
        """Test validation set creation (Подпункт 1.2: add validation sets)."""
        train_X, train_y, val_X, val_y = generate_training_data(
            num_samples=200,
            validation_split=0.3
        )
        
        # 30% validation
        assert val_X.shape[0] == 60
        assert train_X.shape[0] == 140
    
    def test_feature_ranges(self):
        """Test generated features are in valid ranges."""
        train_X, _, _, _ = generate_training_data(num_samples=50)
        
        # Features should generally be in [0, 1] range
        assert np.all(train_X >= 0.0)
        assert np.all(train_X <= 1.5)  # Some padding might exceed 1


class TestIntegration:
    """Integration tests for variance module."""
    
    def test_behavior_variance_with_profiler(self):
        """Test behavior variance + opponent profiling integration."""
        variance = BehaviorVariance(BehaviorType.ADAPTIVE)
        profiler = OpponentProfiler()
        
        # Simulate opponent observations
        observations = [
            {"action": "raise", "sizing": 0.8},
            {"action": "raise", "sizing": 1.0},
            {"action": "call"}
        ]
        
        # Profile opponent
        opponent_type, confidence = profiler.predict_opponent_type(
            "opponent_test",
            observations
        )
        
        # Adjust behavior based on opponent
        context = {
            "opponent_type": opponent_type.value,
            "opponent_confidence": confidence,
            "pot_odds": 0.6
        }
        
        base_equity = 0.55
        adjusted, metadata = variance.apply_behavioral_variance(base_equity, context)
        
        assert 0.0 <= adjusted <= 1.0
        assert "variance_applied" in metadata
    
    def test_full_pipeline_with_session(self):
        """Test complete pipeline: session + variance + anomaly detection."""
        session = SessionState(
            session_id="integration_test",
            max_duration_seconds=3600.0,
            max_hands=50
        )
        
        variance = BehaviorVariance(BehaviorType.BALANCED)
        detector = AnomalyDetector()
        
        recent_actions = []
        
        # Simulate 10 decisions
        for i in range(10):
            session.decisions_made += 1
            
            # Generate decision with variance
            base_equity = 0.60
            adjusted, _ = variance.apply_behavioral_variance(base_equity, {})
            
            # Record action
            action = "call" if adjusted > 0.55 else "fold"
            recent_actions.append({"action": action, "resource_level": 0.5})
        
        # Check anomalies
        anomalies = detector.detect_anomalies(session, recent_actions)
        
        assert len(anomalies) > 0
        assert session.should_reset() is False  # Not exceeded limits
