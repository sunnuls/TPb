"""
Tests for Live Test Runner (Roadmap4 Phase 3).

Tests test pipeline logic and metrics calculation.
"""

import pytest

from bridge.live_test_runner import (
    HandResult,
    LiveTestRunner,
    PhaseMetrics,
    TestPhase,
    TestReport,
)


class TestTestPhase:
    """Test phase enum."""
    
    def test_phase_values(self):
        """Test phase enum values."""
        assert TestPhase.DRY_RUN.value == "dry_run"
        assert TestPhase.SAFE.value == "safe"
        assert TestPhase.MEDIUM_UNSAFE.value == "medium_unsafe"


class TestHandResult:
    """Test hand result dataclass."""
    
    def test_hand_result_creation(self):
        """Test creating hand result."""
        result = HandResult(
            hand_number=1,
            phase=TestPhase.DRY_RUN,
            success=True,
            decision_made=True,
            action_executed=True,
            action_type="check",
            amount=0.0,
            latency_ms=150.5
        )
        
        assert result.hand_number == 1
        assert result.phase == TestPhase.DRY_RUN
        assert result.success is True
        assert result.action_type == "check"
        assert result.latency_ms == 150.5


class TestPhaseMetrics:
    """Test phase metrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = PhaseMetrics(
            phase=TestPhase.DRY_RUN,
            target_hands=100
        )
        
        assert metrics.phase == TestPhase.DRY_RUN
        assert metrics.target_hands == 100
        assert metrics.completed_hands == 0
        assert metrics.successful_hands == 0
        assert metrics.failed_hands == 0
        assert metrics.vision_errors == 0


class TestLiveTestRunner:
    """Test live test runner."""
    
    def test_initialization(self, tmp_path):
        """Test runner initialization."""
        runner = LiveTestRunner(
            room="pokerstars",
            dataset_dir=str(tmp_path)
        )
        
        assert runner.room == "pokerstars"
        assert runner.dataset_dir == tmp_path
        assert runner.test_id.startswith("livetest_")
        
        # Check directories created
        assert (tmp_path / "screenshots").exists()
        assert (tmp_path / "logs").exists()
    
    def test_generate_recommendations_excellent(self):
        """Test recommendations for excellent performance."""
        runner = LiveTestRunner()
        
        recommendations = runner._generate_recommendations(
            success_rate=96.0,
            vision_accuracy=97.0
        )
        
        # Should recommend proceeding
        assert len(recommendations) > 0
        assert any("ready" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_good(self):
        """Test recommendations for good performance."""
        runner = LiveTestRunner()
        
        recommendations = runner._generate_recommendations(
            success_rate=92.0,
            vision_accuracy=93.0
        )
        
        # Should recommend continued testing
        assert len(recommendations) > 0
        assert any("continue" in rec.lower() or "good" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_poor(self):
        """Test recommendations for poor performance."""
        runner = LiveTestRunner()
        
        recommendations = runner._generate_recommendations(
            success_rate=80.0,
            vision_accuracy=85.0
        )
        
        # Should recommend improvement
        assert len(recommendations) > 0
        assert any("improve" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_low_success(self):
        """Test recommendations for low success rate."""
        runner = LiveTestRunner()
        
        recommendations = runner._generate_recommendations(
            success_rate=85.0,
            vision_accuracy=96.0
        )
        
        # Should recommend reviewing errors
        assert len(recommendations) > 0
        assert any("success" in rec.lower() or "error" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_low_vision(self):
        """Test recommendations for low vision accuracy."""
        runner = LiveTestRunner()
        
        recommendations = runner._generate_recommendations(
            success_rate=96.0,
            vision_accuracy=90.0
        )
        
        # Should recommend vision improvement
        assert len(recommendations) > 0
        assert any("vision" in rec.lower() or "training" in rec.lower() for rec in recommendations)
    
    def test_generate_report(self, tmp_path):
        """Test report generation."""
        runner = LiveTestRunner(dataset_dir=str(tmp_path))
        
        # Add some hand results
        runner.hand_results = [
            HandResult(1, TestPhase.DRY_RUN, True, True, True, "check", 0.0, latency_ms=100.0),
            HandResult(2, TestPhase.DRY_RUN, True, True, True, "fold", 0.0, latency_ms=120.0),
            HandResult(3, TestPhase.DRY_RUN, False, False, False, vision_error="Test error", latency_ms=50.0),
        ]
        
        # Add phase metrics
        runner.phase_metrics[TestPhase.DRY_RUN] = PhaseMetrics(
            phase=TestPhase.DRY_RUN,
            target_hands=3,
            completed_hands=3,
            successful_hands=2,
            failed_hands=1,
            vision_errors=1,
            average_latency_ms=90.0,
            total_duration=5.0
        )
        
        # Generate report
        report = runner._generate_report(
            start_time=1000.0,
            end_time=1005.0
        )
        
        assert report.test_id == runner.test_id
        assert report.room == runner.room
        assert report.start_time == 1000.0
        assert report.end_time == 1005.0
        assert len(report.phases) == 1
        assert len(report.hand_results) == 3
        
        # Check calculated metrics
        assert report.overall_success_rate == pytest.approx(66.67, abs=0.1)  # 2/3
        assert report.overall_vision_accuracy == pytest.approx(66.67, abs=0.1)  # 2/3 (1 error)
        
        assert len(report.recommendations) > 0
    
    def test_save_report(self, tmp_path):
        """Test report saving."""
        runner = LiveTestRunner(dataset_dir=str(tmp_path))
        
        # Create simple report
        report = TestReport(
            test_id=runner.test_id,
            room="pokerstars",
            start_time=1000.0,
            end_time=1005.0,
            phases=[],
            hand_results=[],
            overall_success_rate=95.0,
            overall_vision_accuracy=96.0,
            recommendations=["Test recommendation"]
        )
        
        # Save report
        runner._save_report(report)
        
        # Check files created
        report_file = tmp_path / "logs" / f"{runner.test_id}_report.json"
        summary_file = tmp_path / "logs" / f"{runner.test_id}_summary.txt"
        
        assert report_file.exists()
        assert summary_file.exists()
        
        # Check summary content
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "LIVE TEST REPORT SUMMARY" in content
            assert "Test recommendation" in content
    
    def test_request_confirmation(self):
        """Test confirmation request."""
        runner = LiveTestRunner()
        
        # In automated mode, should always return True
        assert runner._request_confirmation("safe") is True
        assert runner._request_confirmation("medium_unsafe") is True


class TestMetricsCalculation:
    """Test metrics calculation."""
    
    def test_phase_metrics_completion(self):
        """Test phase metrics with all hands completed."""
        metrics = PhaseMetrics(
            phase=TestPhase.DRY_RUN,
            target_hands=10,
            completed_hands=10,
            successful_hands=9,
            failed_hands=1
        )
        
        assert metrics.completed_hands == metrics.target_hands
        assert metrics.successful_hands + metrics.failed_hands == metrics.completed_hands
    
    def test_actions_by_type_tracking(self):
        """Test action type tracking."""
        metrics = PhaseMetrics(
            phase=TestPhase.SAFE,
            target_hands=10
        )
        
        # Simulate action tracking
        metrics.actions_by_type['fold'] = 3
        metrics.actions_by_type['check'] = 4
        metrics.actions_by_type['call'] = 3
        
        assert sum(metrics.actions_by_type.values()) == 10
        assert metrics.actions_by_type['fold'] == 3
        assert metrics.actions_by_type['check'] == 4
        assert metrics.actions_by_type['call'] == 3


class TestReportGeneration:
    """Test report generation."""
    
    def test_report_with_multiple_phases(self, tmp_path):
        """Test report with multiple phases."""
        runner = LiveTestRunner(dataset_dir=str(tmp_path))
        
        # Add results from multiple phases
        runner.hand_results = [
            # Dry-run phase
            HandResult(1, TestPhase.DRY_RUN, True, True, True, "check", latency_ms=100.0),
            HandResult(2, TestPhase.DRY_RUN, True, True, True, "fold", latency_ms=120.0),
            # Safe phase
            HandResult(3, TestPhase.SAFE, True, True, True, "call", latency_ms=150.0),
            HandResult(4, TestPhase.SAFE, True, True, True, "check", latency_ms=140.0),
        ]
        
        # Add phase metrics
        runner.phase_metrics[TestPhase.DRY_RUN] = PhaseMetrics(
            phase=TestPhase.DRY_RUN,
            target_hands=2,
            completed_hands=2,
            successful_hands=2,
            failed_hands=0
        )
        
        runner.phase_metrics[TestPhase.SAFE] = PhaseMetrics(
            phase=TestPhase.SAFE,
            target_hands=2,
            completed_hands=2,
            successful_hands=2,
            failed_hands=0
        )
        
        # Generate report
        report = runner._generate_report(1000.0, 1010.0)
        
        assert len(report.phases) == 2
        assert report.overall_success_rate == 100.0
        assert report.overall_vision_accuracy == 100.0
    
    def test_report_with_vision_errors(self, tmp_path):
        """Test report with vision errors."""
        runner = LiveTestRunner(dataset_dir=str(tmp_path))
        
        # Add results with vision errors
        runner.hand_results = [
            HandResult(1, TestPhase.DRY_RUN, True, True, True, "check", latency_ms=100.0),
            HandResult(2, TestPhase.DRY_RUN, False, False, False, vision_error="Error 1", latency_ms=50.0),
            HandResult(3, TestPhase.DRY_RUN, False, False, False, vision_error="Error 2", latency_ms=50.0),
        ]
        
        # Generate report
        report = runner._generate_report(1000.0, 1003.0)
        
        # Should calculate vision accuracy correctly
        # 1 success, 2 vision errors = 33.33% accuracy
        assert report.overall_vision_accuracy == pytest.approx(33.33, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
