"""
Tests for ActionSimulator (Roadmap3 Phase 5.2).

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

import pytest
import tempfile
from pathlib import Path

from bridge.action_simulator import (
    ActionSimulator,
    ActionLog,
    ActionHistory,
    SimulationResult
)
from bridge.action_translator import ActionCommand, ActionType, UIElement


class TestActionLog:
    """Test ActionLog dataclass."""
    
    def test_action_log_creation(self):
        """Test basic log creation."""
        command = ActionCommand(
            action_type=ActionType.CALL,
            amount=10.0,
            normalized_amount=10.0,
            description="Call 10bb"
        )
        
        log = ActionLog(
            timestamp=1234567890.0,
            command=command,
            result=SimulationResult.WOULD_SUCCEED,
            duration=0.5
        )
        
        assert log.timestamp == 1234567890.0
        assert log.command == command
        assert log.result == SimulationResult.WOULD_SUCCEED
        assert log.duration == 0.5
        assert log.description == "Call 10bb"  # Auto-filled


class TestActionHistory:
    """Test ActionHistory dataclass."""
    
    def test_action_history_creation(self):
        """Test basic history creation."""
        history = ActionHistory()
        
        assert len(history.logs) == 0
        assert history.total_actions == 0
        assert history.successful_actions == 0
        assert history.blocked_actions == 0
        assert history.total_duration == 0.0
    
    def test_add_log(self):
        """Test adding logs to history."""
        history = ActionHistory()
        
        command = ActionCommand(action_type=ActionType.FOLD, amount=0.0)
        log = ActionLog(
            timestamp=1234567890.0,
            command=command,
            result=SimulationResult.WOULD_SUCCEED,
            duration=0.3
        )
        
        history.add_log(log)
        
        assert len(history.logs) == 1
        assert history.total_actions == 1
        assert history.successful_actions == 1
        assert history.total_duration == 0.3
    
    def test_add_blocked_log(self):
        """Test adding blocked action log."""
        history = ActionHistory()
        
        command = ActionCommand(action_type=ActionType.BET, amount=50.0)
        log = ActionLog(
            timestamp=1234567890.0,
            command=command,
            result=SimulationResult.BLOCKED,
            duration=0.1
        )
        
        history.add_log(log)
        
        assert history.total_actions == 1
        assert history.successful_actions == 0
        assert history.blocked_actions == 1


class TestActionSimulator:
    """Test ActionSimulator core functionality."""
    
    def test_init(self):
        """Test simulator initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            simulator = ActionSimulator(
                log_dir=f"{tmpdir}/logs",
                screenshot_dir=f"{tmpdir}/screenshots"
            )
            
            assert simulator.history.total_actions == 0
            assert Path(f"{tmpdir}/logs").exists()
            assert Path(f"{tmpdir}/screenshots").exists()
    
    def test_simulate_fold(self):
        """Test simulating fold action."""
        simulator = ActionSimulator()
        
        command = ActionCommand(
            action_type=ActionType.FOLD,
            amount=0.0,
            ui_element=UIElement.FOLD_BUTTON,
            description="Fold"
        )
        
        log = simulator.simulate(command, capture_screenshot=False)
        
        assert log.result == SimulationResult.WOULD_SUCCEED
        assert log.duration > 0
        assert simulator.history.total_actions == 1
    
    def test_simulate_call(self):
        """Test simulating call action."""
        simulator = ActionSimulator()
        
        command = ActionCommand(
            action_type=ActionType.CALL,
            amount=10.0,
            ui_element=UIElement.CALL_BUTTON,
            description="Call 10bb"
        )
        
        log = simulator.simulate(command, capture_screenshot=False)
        
        assert log.result == SimulationResult.WOULD_SUCCEED
        assert log.command.action_type == ActionType.CALL
    
    def test_simulate_raise(self):
        """Test simulating raise action."""
        simulator = ActionSimulator()
        
        command = ActionCommand(
            action_type=ActionType.RAISE,
            amount=30.0,
            ui_element=UIElement.RAISE_BUTTON,
            normalized_amount=30.0,
            description="Raise to 30bb"
        )
        
        log = simulator.simulate(command, capture_screenshot=False)
        
        assert log.result == SimulationResult.WOULD_SUCCEED
        assert log.duration > 0
    
    def test_multiple_simulations(self):
        """Test multiple action simulations."""
        simulator = ActionSimulator()
        
        commands = [
            ActionCommand(ActionType.CALL, 10.0, UIElement.CALL_BUTTON),
            ActionCommand(ActionType.FOLD, 0.0, UIElement.FOLD_BUTTON),
            ActionCommand(ActionType.RAISE, 30.0, UIElement.RAISE_BUTTON)
        ]
        
        for command in commands:
            simulator.simulate(command, capture_screenshot=False)
        
        assert simulator.history.total_actions == 3
        assert simulator.history.successful_actions == 3
    
    def test_get_recent_actions(self):
        """Test getting recent actions."""
        simulator = ActionSimulator()
        
        # Simulate 5 actions
        for i in range(5):
            command = ActionCommand(ActionType.FOLD, 0.0)
            simulator.simulate(command, capture_screenshot=False)
        
        recent = simulator.get_recent_actions(count=3)
        
        assert len(recent) == 3
        # Should be most recent
        assert all(isinstance(log, ActionLog) for log in recent)
    
    def test_export_history(self):
        """Test exporting action history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            simulator = ActionSimulator(log_dir=tmpdir)
            
            # Simulate some actions
            commands = [
                ActionCommand(ActionType.CALL, 10.0),
                ActionCommand(ActionType.RAISE, 30.0)
            ]
            
            for command in commands:
                simulator.simulate(command, capture_screenshot=False)
            
            # Export history
            export_path = simulator.export_history("test_history.log")
            
            assert Path(export_path).exists()
            assert Path(export_path).stat().st_size > 0
    
    def test_get_statistics(self):
        """Test statistics collection."""
        simulator = ActionSimulator()
        
        # Simulate actions
        commands = [
            ActionCommand(ActionType.FOLD, 0.0),
            ActionCommand(ActionType.CALL, 10.0),
            ActionCommand(ActionType.RAISE, 30.0)
        ]
        
        for command in commands:
            simulator.simulate(command, capture_screenshot=False)
        
        stats = simulator.get_statistics()
        
        assert stats['total_actions'] == 3
        assert stats['successful_actions'] == 3
        assert stats['blocked_actions'] == 0
        assert stats['total_duration'] > 0
        assert stats['average_duration'] > 0


class TestIntegration:
    """Integration tests for action simulator."""
    
    def test_full_simulation_workflow(self):
        """Test complete simulation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            simulator = ActionSimulator(
                log_dir=f"{tmpdir}/logs",
                screenshot_dir=f"{tmpdir}/screenshots"
            )
            
            # Create commands
            commands = [
                ActionCommand(
                    action_type=ActionType.CALL,
                    amount=10.0,
                    ui_element=UIElement.CALL_BUTTON,
                    normalized_amount=10.0,
                    description="Call 10bb",
                    priority=80
                ),
                ActionCommand(
                    action_type=ActionType.RAISE,
                    amount=30.0,
                    ui_element=UIElement.RAISE_BUTTON,
                    normalized_amount=30.0,
                    description="Raise to 30bb",
                    priority=95
                ),
                ActionCommand(
                    action_type=ActionType.FOLD,
                    amount=0.0,
                    ui_element=UIElement.FOLD_BUTTON,
                    description="Fold",
                    priority=50
                )
            ]
            
            # Simulate all commands
            logs = [
                simulator.simulate(cmd, capture_screenshot=False)
                for cmd in commands
            ]
            
            # Validate results
            assert len(logs) == 3
            assert all(log.result == SimulationResult.WOULD_SUCCEED for log in logs)
            assert all(log.duration > 0 for log in logs)
            
            # Export history
            export_path = simulator.export_history()
            assert Path(export_path).exists()
            
            # Check statistics
            stats = simulator.get_statistics()
            assert stats['total_actions'] == 3
            assert stats['successful_actions'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
