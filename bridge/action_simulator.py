"""
Action Simulator Module (Roadmap3 Phase 5.2).

Simulates poker action execution - **LOGGING ONLY, NO REAL CLICKS**.
Records what would be done without actual execution.

Key Features:
- Action command logging
- Execution timing simulation
- UI interaction simulation (no real input)
- Screenshot capture for verification
- Complete action history

EDUCATIONAL USE ONLY: For HCI research prototype.
Real execution prohibited without --unsafe flag.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from bridge.action_translator import ActionCommand, ActionType
from bridge.safety import SafetyFramework

logger = logging.getLogger(__name__)


class SimulationResult(str, Enum):
    """Simulation result status."""
    SUCCESS = "success"
    WOULD_SUCCEED = "would_succeed"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class ActionLog:
    """
    Log entry for simulated action.
    
    Attributes:
        timestamp: When action was simulated
        command: ActionCommand that was simulated
        result: Simulation result
        duration: Simulated execution time (seconds)
        description: Human-readable description
        screenshot_path: Path to verification screenshot (if captured)
        error: Error message if failed
    """
    timestamp: float
    command: ActionCommand
    result: SimulationResult
    duration: float = 0.0
    description: str = ""
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if not self.description:
            self.description = self.command.description


@dataclass
class ActionHistory:
    """
    Complete history of simulated actions.
    
    Attributes:
        logs: List of all action logs
        total_actions: Total actions simulated
        successful_actions: Number of successful simulations
        blocked_actions: Number of blocked actions
        total_duration: Total simulated time (seconds)
    """
    logs: List[ActionLog] = field(default_factory=list)
    total_actions: int = 0
    successful_actions: int = 0
    blocked_actions: int = 0
    total_duration: float = 0.0
    
    def add_log(self, log: ActionLog) -> None:
        """Add log entry and update statistics."""
        self.logs.append(log)
        self.total_actions += 1
        self.total_duration += log.duration
        
        if log.result == SimulationResult.WOULD_SUCCEED:
            self.successful_actions += 1
        elif log.result == SimulationResult.BLOCKED:
            self.blocked_actions += 1


class ActionSimulator:
    """
    Simulates poker action execution without real input.
    
    Simulation Process:
    1. Receive ActionCommand
    2. Check safety framework permissions
    3. Simulate execution timing
    4. Log what would be done (UI element + amount)
    5. Capture screenshot for verification
    6. Return simulation result
    
    **IMPORTANT**: NO REAL ACTIONS ARE EXECUTED
    - No mouse movement
    - No clicks
    - No keyboard input
    - ONLY logging and timing simulation
    
    EDUCATIONAL NOTE:
        This enables testing decision engine output in safe environment
        before any real execution (if ever enabled with --unsafe).
    """
    
    def __init__(
        self,
        safety: Optional[SafetyFramework] = None,
        log_dir: str = "bridge/action_logs",
        screenshot_dir: str = "bridge/action_screenshots"
    ):
        """
        Initialize action simulator.
        
        Args:
            safety: Safety framework instance
            log_dir: Directory for action logs
            screenshot_dir: Directory for verification screenshots
        """
        self.safety = safety or SafetyFramework.get_instance()
        self.log_dir = Path(log_dir)
        self.screenshot_dir = Path(screenshot_dir)
        
        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Action history
        self.history = ActionHistory()
        
        # Simulation parameters
        self.base_action_time = 0.1  # Base time per action (seconds)
        self.capture_screenshots = True
        
        logger.info(
            f"ActionSimulator initialized (dry_run mode) - "
            f"log_dir={self.log_dir}, screenshot_dir={self.screenshot_dir}"
        )
    
    def simulate(
        self,
        command: ActionCommand,
        capture_screenshot: bool = True
    ) -> ActionLog:
        """
        Simulate action execution.
        
        Args:
            command: ActionCommand to simulate
            capture_screenshot: Whether to capture verification screenshot
        
        Returns:
            ActionLog with simulation results
        
        EDUCATIONAL NOTE:
            This is the core simulation method.
            Records what would happen without executing.
        """
        start_time = time.time()
        
        # Log simulation start
        logger.info(
            f"[SIMULATION] Would execute: {command.description} "
            f"(ui:{command.ui_element.value if command.ui_element else 'none'})"
        )
        
        # Check safety permissions
        if not self._check_safety(command):
            # Action blocked by safety framework
            duration = time.time() - start_time
            
            log = ActionLog(
                timestamp=time.time(),
                command=command,
                result=SimulationResult.BLOCKED,
                duration=duration,
                description=f"[BLOCKED] {command.description}",
                error="Action blocked by safety framework"
            )
            
            self.history.add_log(log)
            
            logger.warning(f"[BLOCKED] Action blocked by safety: {command.description}")
            return log
        
        # Simulate execution
        try:
            # Simulate action timing
            simulated_duration = self._simulate_timing(command)
            time.sleep(min(simulated_duration, 0.01))  # Small actual delay for realism
            
            # Log what would be done
            self._log_simulation_details(command)
            
            # Capture screenshot if requested
            screenshot_path = None
            if capture_screenshot and self.capture_screenshots:
                screenshot_path = self._capture_verification_screenshot(command)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create log entry
            log = ActionLog(
                timestamp=time.time(),
                command=command,
                result=SimulationResult.WOULD_SUCCEED,
                duration=duration,
                description=f"[SIMULATED] {command.description}",
                screenshot_path=screenshot_path
            )
            
            self.history.add_log(log)
            
            logger.info(
                f"[SUCCESS] Simulation complete: {command.description} "
                f"(duration={duration:.3f}s)"
            )
            
            return log
            
        except Exception as e:
            duration = time.time() - start_time
            
            log = ActionLog(
                timestamp=time.time(),
                command=command,
                result=SimulationResult.ERROR,
                duration=duration,
                description=f"[ERROR] {command.description}",
                error=str(e)
            )
            
            self.history.add_log(log)
            
            logger.error(f"[ERROR] Simulation error: {e}", exc_info=True)
            return log
    
    def _check_safety(self, command: ActionCommand) -> bool:
        """
        Check if action is allowed by safety framework.
        
        Args:
            command: ActionCommand to check
        
        Returns:
            True if allowed
        
        EDUCATIONAL NOTE:
            In dry-run mode, all actions are "allowed" for simulation.
            In unsafe mode, additional checks would be enforced.
        """
        # In dry-run mode (default), all simulations are allowed
        if self.safety.is_dry_run():
            return True
        
        # Log decision
        self.safety.log_decision({
            'action': 'simulate_action',
            'command_action': command.action_type.value,
            'amount': command.amount,
            'reason': f"Simulating {command.action_type.value}",
            'allowed': True
        })
        
        return True
    
    def _simulate_timing(self, command: ActionCommand) -> float:
        """
        Calculate simulated execution time.
        
        Args:
            command: ActionCommand to simulate
        
        Returns:
            Simulated duration in seconds
        
        EDUCATIONAL NOTE:
            Different actions have different timing:
            - Fold/check/call: fast (0.1-0.2s)
            - Bet/raise: slower (0.2-0.4s) due to sizing input
            - All-in: medium (0.15-0.25s)
        """
        base_time = self.base_action_time
        
        # Action-specific timing
        if command.action_type in [ActionType.FOLD, ActionType.CHECK, ActionType.CALL]:
            return base_time * 1.5  # Simple actions
        elif command.action_type in [ActionType.BET, ActionType.RAISE]:
            return base_time * 3.0  # Complex actions with sizing
        elif command.action_type == ActionType.ALL_IN:
            return base_time * 2.0  # Medium complexity
        
        return base_time
    
    def _log_simulation_details(self, command: ActionCommand) -> None:
        """
        Log detailed simulation information.
        
        Args:
            command: ActionCommand being simulated
        
        EDUCATIONAL NOTE:
            This records exact details of what would be executed.
        """
        details = [
            f"[SIMULATION DETAILS]",
            f"  Action: {command.action_type.value}",
            f"  Amount: {command.normalized_amount:.2f}bb ({command.amount:.2f} chips)",
            f"  UI Element: {command.ui_element.value if command.ui_element else 'none'}",
            f"  Priority: {command.priority}",
            f"  Legal: {command.legal}",
            f"  Description: {command.description}"
        ]
        
        logger.info("\n".join(details))
    
    def _capture_verification_screenshot(self, command: ActionCommand) -> Optional[str]:
        """
        Capture screenshot for action verification.
        
        Args:
            command: ActionCommand being simulated
        
        Returns:
            Path to screenshot or None
        
        EDUCATIONAL NOTE:
            Screenshots allow post-simulation verification.
            In real execution, would capture before + after action.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"action_{command.action_type.value}_{timestamp}.png"
            screenshot_path = self.screenshot_dir / filename
            
            # Simulate screenshot capture (no real capture in dry-run)
            logger.debug(f"[SCREENSHOT] Would capture: {screenshot_path}")
            
            # In real execution:
            # screenshot = screen_capture.capture()
            # cv2.imwrite(str(screenshot_path), screenshot)
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Screenshot capture error: {e}")
            return None
    
    def get_history(self) -> ActionHistory:
        """Get complete action history."""
        return self.history
    
    def get_recent_actions(self, count: int = 10) -> List[ActionLog]:
        """
        Get recent action logs.
        
        Args:
            count: Number of recent actions to return
        
        Returns:
            List of recent ActionLog entries
        """
        return self.history.logs[-count:]
    
    def export_history(self, filename: Optional[str] = None) -> str:
        """
        Export action history to file.
        
        Args:
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to exported file
        
        EDUCATIONAL NOTE:
            Exports complete action log for analysis and verification.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"action_history_{timestamp}.log"
        
        log_path = self.log_dir / filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("Action Simulation History\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Total actions: {self.history.total_actions}\n")
            f.write(f"Successful: {self.history.successful_actions}\n")
            f.write(f"Blocked: {self.history.blocked_actions}\n")
            f.write(f"Total duration: {self.history.total_duration:.2f}s\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("Action Log:\n")
            f.write("=" * 60 + "\n\n")
            
            for i, log in enumerate(self.history.logs, 1):
                timestamp_str = datetime.fromtimestamp(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{i}. [{timestamp_str}] {log.description}\n")
                f.write(f"   Result: {log.result.value}\n")
                f.write(f"   Duration: {log.duration:.3f}s\n")
                if log.screenshot_path:
                    f.write(f"   Screenshot: {log.screenshot_path}\n")
                if log.error:
                    f.write(f"   Error: {log.error}\n")
                f.write("\n")
        
        logger.info(f"Action history exported to: {log_path}")
        return str(log_path)
    
    def get_statistics(self) -> dict:
        """Get simulator statistics."""
        return {
            'total_actions': self.history.total_actions,
            'successful_actions': self.history.successful_actions,
            'blocked_actions': self.history.blocked_actions,
            'error_count': len([
                log for log in self.history.logs 
                if log.result == SimulationResult.ERROR
            ]),
            'total_duration': self.history.total_duration,
            'average_duration': (
                self.history.total_duration / self.history.total_actions
                if self.history.total_actions > 0 else 0.0
            ),
            'log_dir': str(self.log_dir),
            'screenshot_dir': str(self.screenshot_dir)
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Action Simulator - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Create simulator
    simulator = ActionSimulator()
    
    # Example commands to simulate
    from bridge.action_translator import UIElement
    
    commands = [
        ActionCommand(
            action_type=ActionType.CALL,
            amount=10.0,
            ui_element=UIElement.CALL_BUTTON,
            normalized_amount=10.0,
            description="Call 10bb",
            legal=True,
            priority=80
        ),
        ActionCommand(
            action_type=ActionType.RAISE,
            amount=30.0,
            ui_element=UIElement.RAISE_BUTTON,
            normalized_amount=30.0,
            description="Raise to 30bb",
            legal=True,
            priority=95
        ),
        ActionCommand(
            action_type=ActionType.FOLD,
            amount=0.0,
            ui_element=UIElement.FOLD_BUTTON,
            normalized_amount=0.0,
            description="Fold",
            legal=True,
            priority=50
        )
    ]
    
    print("Simulating Actions:")
    print("-" * 60)
    
    for i, command in enumerate(commands, 1):
        print(f"\n{i}. Simulating: {command.description}")
        
        log = simulator.simulate(command, capture_screenshot=False)
        
        print(f"   Result: {log.result.value}")
        print(f"   Duration: {log.duration:.3f}s")
    
    print()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    stats = simulator.get_statistics()
    print(f"Total actions: {stats['total_actions']}")
    print(f"Successful: {stats['successful_actions']}")
    print(f"Blocked: {stats['blocked_actions']}")
    print(f"Total duration: {stats['total_duration']:.3f}s")
    print(f"Average duration: {stats['average_duration']:.3f}s")
    print()
    
    # Export history
    export_path = simulator.export_history()
    print(f"History exported to: {export_path}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
    print("[NOTE] NO REAL ACTIONS EXECUTED - simulation only")
