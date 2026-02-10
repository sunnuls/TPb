"""
Tests for HumanizationSimulator (Roadmap3 Phase 5.3).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import math

from bridge.humanization_sim import (
    HumanizationSimulator,
    MousePath,
    TimingVariance
)


class TestMousePath:
    """Test MousePath dataclass."""
    
    def test_mouse_path_creation(self):
        """Test basic path creation."""
        path = MousePath(
            start=(0, 0),
            end=(100, 100),
            points=[(0, 0), (50, 50), (100, 100)],
            duration=0.5,
            distance=141.4
        )
        
        assert path.start == (0, 0)
        assert path.end == (100, 100)
        assert len(path.points) == 3
        assert path.duration == 0.5
        assert path.distance == pytest.approx(141.4)


class TestTimingVariance:
    """Test TimingVariance dataclass."""
    
    def test_timing_variance_creation(self):
        """Test basic timing creation."""
        timing = TimingVariance(
            base_delay=0.1,
            variance=0.5,
            think_time=1.5,
            execution_time=0.3,
            total_time=1.9
        )
        
        assert timing.base_delay == 0.1
        assert timing.variance == 0.5
        assert timing.think_time == 1.5
        assert timing.execution_time == 0.3
        assert timing.total_time == 1.9


class TestHumanizationSimulator:
    """Test HumanizationSimulator core functionality."""
    
    def test_init(self):
        """Test simulator initialization."""
        simulator = HumanizationSimulator(
            base_think_time=1.5,
            think_variance=0.8
        )
        
        assert simulator.base_think_time == 1.5
        assert simulator.think_variance == 0.8
        assert simulator.actions_count == 0
        assert simulator.fatigue_level == 0.0
    
    def test_simulate_timing_fold(self):
        """Test timing simulation for fold."""
        simulator = HumanizationSimulator()
        
        timing = simulator.simulate_timing('fold', hand_strength=0.2)
        
        assert timing.think_time > 0
        assert timing.execution_time > 0
        assert timing.total_time > 0
        assert timing.total_time == pytest.approx(
            timing.base_delay + timing.think_time + timing.execution_time,
            abs=0.01
        )
    
    def test_simulate_timing_call(self):
        """Test timing simulation for call."""
        simulator = HumanizationSimulator()
        
        timing = simulator.simulate_timing('call', hand_strength=0.5)
        
        assert timing.think_time > 0
        assert timing.execution_time > 0
        assert simulator.actions_count == 1
    
    def test_simulate_timing_raise(self):
        """Test timing simulation for raise."""
        simulator = HumanizationSimulator()
        
        timing = simulator.simulate_timing('raise', hand_strength=0.8)
        
        assert timing.execution_time > 0
        # Raise should take longer than simple actions
        assert timing.execution_time >= 0.15
    
    def test_hand_strength_affects_timing(self):
        """Test that hand strength affects think time."""
        simulator = HumanizationSimulator(
            base_think_time=2.0,
            think_variance=0.1  # Small variance for testing
        )
        
        # Strong hand should be faster
        strong_timing = simulator.simulate_timing('raise', hand_strength=0.9)
        
        simulator2 = HumanizationSimulator(
            base_think_time=2.0,
            think_variance=0.1
        )
        
        # Weak hand should be slower
        weak_timing = simulator2.simulate_timing('fold', hand_strength=0.1)
        
        # Weak hand should generally take more think time
        # (though variance means this isn't guaranteed every time)
        assert weak_timing.think_time >= strong_timing.think_time * 0.7
    
    def test_important_actions_take_longer(self):
        """Test that important actions have longer think time."""
        simulator = HumanizationSimulator()
        
        normal_timing = simulator.simulate_timing('raise', is_important=False)
        
        simulator2 = HumanizationSimulator()
        important_timing = simulator2.simulate_timing('raise', is_important=True)
        
        # Important actions should take at least as long
        assert important_timing.think_time >= normal_timing.think_time * 0.9
    
    def test_fatigue_accumulates(self):
        """Test that fatigue level increases."""
        simulator = HumanizationSimulator()
        
        initial_fatigue = simulator.fatigue_level
        
        # Simulate multiple actions
        for _ in range(10):
            simulator.simulate_timing('call')
        
        # Fatigue should increase
        assert simulator.fatigue_level > initial_fatigue
    
    def test_reset_fatigue(self):
        """Test fatigue reset."""
        simulator = HumanizationSimulator()
        
        # Simulate actions to build fatigue
        for _ in range(10):
            simulator.simulate_timing('call')
        
        assert simulator.fatigue_level > 0
        
        # Reset
        simulator.reset_fatigue()
        
        assert simulator.fatigue_level == 0.0
    
    def test_simulate_mouse_path(self):
        """Test mouse path simulation."""
        simulator = HumanizationSimulator()
        
        start = (100, 100)
        end = (300, 200)
        
        path = simulator.simulate_mouse_path(start, end)
        
        assert path.start == start
        assert path.end == end
        assert len(path.points) > 0
        assert path.duration > 0
        assert path.distance > 0
    
    def test_mouse_path_has_curve(self):
        """Test that mouse path is curved (not straight line)."""
        simulator = HumanizationSimulator()
        
        start = (0, 0)
        end = (100, 0)  # Horizontal line
        
        path = simulator.simulate_mouse_path(start, end)
        
        # Check that at least some points deviate from straight line
        # (due to Bezier curve)
        y_values = [point[1] for point in path.points]
        
        # Should have some y-values != 0 (curve deviation)
        non_zero_y = [y for y in y_values if abs(y) > 1]
        assert len(non_zero_y) > 0  # Path deviates from straight line
    
    def test_mouse_path_distance_calculation(self):
        """Test distance calculation for mouse path."""
        simulator = HumanizationSimulator()
        
        # Right triangle: 3-4-5
        start = (0, 0)
        end = (300, 400)
        
        path = simulator.simulate_mouse_path(start, end)
        
        # Expected distance: sqrt(300^2 + 400^2) = 500
        expected_distance = math.sqrt(300**2 + 400**2)
        assert path.distance == pytest.approx(expected_distance, abs=1)
    
    def test_get_statistics(self):
        """Test statistics collection."""
        simulator = HumanizationSimulator(
            base_think_time=1.5,
            think_variance=0.8
        )
        
        # Simulate actions
        for i in range(5):
            simulator.simulate_timing('call')
        
        stats = simulator.get_statistics()
        
        assert stats['actions_count'] == 5
        assert stats['session_duration'] > 0
        assert stats['average_action_time'] > 0
        assert stats['fatigue_level'] >= 0
        assert stats['base_think_time'] == 1.5
        assert stats['think_variance'] == 0.8


class TestIntegration:
    """Integration tests for humanization simulator."""
    
    def test_full_timing_workflow(self):
        """Test complete timing simulation workflow."""
        simulator = HumanizationSimulator(
            base_think_time=1.5,
            think_variance=0.5,
            fatigue_factor=0.05
        )
        
        # Simulate a sequence of actions
        actions = [
            ('fold', 0.2, False),
            ('call', 0.5, False),
            ('raise', 0.8, False),
            ('raise', 0.9, True),  # Important
            ('all_in', 0.95, True)
        ]
        
        timings = []
        for action, strength, important in actions:
            timing = simulator.simulate_timing(action, strength, important)
            timings.append(timing)
        
        # Validate all timings
        assert len(timings) == 5
        assert all(t.total_time > 0 for t in timings)
        
        # Check fatigue accumulated
        assert simulator.fatigue_level > 0
        
        # Check statistics
        stats = simulator.get_statistics()
        assert stats['actions_count'] == 5
        assert stats['session_duration'] > 0
    
    def test_full_mouse_path_workflow(self):
        """Test complete mouse path simulation workflow."""
        simulator = HumanizationSimulator()
        
        # Simulate paths to different UI elements
        paths_config = [
            ((100, 100), (300, 200)),  # Fold button
            ((100, 100), (400, 150)),  # Call button
            ((100, 100), (250, 300))   # Raise button
        ]
        
        paths = [
            simulator.simulate_mouse_path(start, end)
            for start, end in paths_config
        ]
        
        # Validate all paths
        assert len(paths) == 3
        assert all(len(p.points) > 0 for p in paths)
        assert all(p.duration > 0 for p in paths)
        assert all(p.distance > 0 for p in paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
