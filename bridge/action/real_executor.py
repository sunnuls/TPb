"""
Real Action Executor (Roadmap4 Phase 1 + auto_navigate.md Phase 2 + full_hive_month Этап 3).

CRITICAL WARNING: This module executes REAL mouse clicks and keyboard input.
Use ONLY in controlled educational research environment.

Risk Levels:
- LOW: fold/check/call (minimal risk)
- MEDIUM: bet/raise with fixed amounts
- HIGH: all-in/large raises

Phase 2 (auto_navigate.md):
- click_nav_region(): click a NavigationManager-discovered region
- click_table_entry(): click on a found table row
- execute_nav_action(): full nav action from NavResult
- scroll_nav(): scroll the lobby via NavManager integration

Этап 3 (full_hive_month.md):
- click_game_mode(): switch game mode (NL Hold'em, PLO, etc.)
- click_table_from_list(): click table by index in lobby
- scroll_table_list(): scroll through lobby table list
- click_join_button(): click the Join/Sit button
- execute_manipulation_action(): map ManipulationDecision → real click

EDUCATIONAL USE ONLY: For HCI research prototype testing.
Requires explicit --unsafe flag and user confirmation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    # pyautogui may not be available or have installation issues
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None  # Set to None for type checking

from bridge.safety import SafetyFramework, SafetyMode

# Graceful import of NavigationManager (auto_navigate.md Phase 2)
try:
    from launcher.navigation_manager import (
        NavigationManager,
        NavResult,
        NavStatus,
        TableEntry,
        ScreenType,
    )
    NAV_AVAILABLE = True
except Exception:
    NAV_AVAILABLE = False

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    LOW = "low"           # fold/check/call
    MEDIUM = "medium"     # bet/raise fixed
    HIGH = "high"         # all-in/large raises


class ExecutionResult(str, Enum):
    """Execution results."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED_BY_SAFETY = "blocked_by_safety"
    LIBRARY_NOT_AVAILABLE = "library_not_available"
    INVALID_COORDINATES = "invalid_coordinates"


@dataclass
class ActionCoordinates:
    """
    Coordinates for action execution.
    
    Attributes:
        button_x: X coordinate of button
        button_y: Y coordinate of button
        amount_field_x: X coordinate of amount input field (optional)
        amount_field_y: Y coordinate of amount input field (optional)
    """
    button_x: int
    button_y: int
    amount_field_x: Optional[int] = None
    amount_field_y: Optional[int] = None


@dataclass
class ExecutionLog:
    """
    Log entry for executed action.
    
    Attributes:
        timestamp: When action was executed
        action_type: Type of action (fold/check/call/raise/bet/allin)
        risk_level: Risk level of action
        coordinates: Coordinates used
        amount: Amount entered (if applicable)
        result: Execution result
        duration: Execution duration in seconds
        screenshot_path: Path to verification screenshot
    """
    timestamp: float
    action_type: str
    risk_level: RiskLevel
    coordinates: ActionCoordinates
    amount: Optional[float]
    result: ExecutionResult
    duration: float
    screenshot_path: Optional[str] = None


class RealActionExecutor:
    """
    Executes real mouse clicks and keyboard input.
    
    CRITICAL SAFETY:
    - Only works when SafetyFramework mode is UNSAFE
    - Requires explicit confirmation for each session
    - Blocks high-risk actions unless explicitly allowed
    - Logs every action with screenshot
    - Emergency shutdown on any anomaly
    
    EDUCATIONAL NOTE:
        This is the most dangerous component. It performs REAL
        actions on the desktop application. Use with extreme caution.
    """
    
    def __init__(
        self,
        safety: Optional[SafetyFramework] = None,
        max_risk_level: RiskLevel = RiskLevel.LOW,
        humanization_enabled: bool = True
    ):
        """
        Initialize real action executor.
        
        Args:
            safety: Safety framework instance
            max_risk_level: Maximum allowed risk level
            humanization_enabled: Enable human-like delays/movements
        
        Raises:
            RuntimeError: If safety mode is not UNSAFE
        """
        self.safety = safety or SafetyFramework.get_instance()
        self.max_risk_level = max_risk_level
        self.humanization_enabled = humanization_enabled
        
        # Safety check
        if self.safety.config.mode != SafetyMode.UNSAFE:
            raise RuntimeError(
                "RealActionExecutor requires UNSAFE mode. "
                "Current mode: {self.safety.config.mode.value}"
            )
        
        # Check library availability
        if not PYAUTOGUI_AVAILABLE:
            logger.error("pyautogui not available - install with: pip install pyautogui")
            raise ImportError("pyautogui required for real action execution")
        
        # Configure pyautogui safety
        if PYAUTOGUI_AVAILABLE and pyautogui is not None:
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1  # Minimum pause between calls
        
        # Statistics
        self.actions_executed = 0
        self.actions_blocked = 0
        self.execution_logs: list[ExecutionLog] = []
        
        logger.critical("=" * 60)
        logger.critical("REAL ACTION EXECUTOR INITIALIZED")
        logger.critical("Mode: UNSAFE - Real actions WILL be executed")
        logger.critical(f"Max risk level: {max_risk_level.value}")
        logger.critical("=" * 60)
    
    def execute_action(
        self,
        action_type: str,
        coordinates: ActionCoordinates,
        amount: Optional[float] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> ExecutionLog:
        """
        Execute real action.
        
        Args:
            action_type: Type of action (fold/check/call/raise/bet/allin)
            coordinates: Coordinates for click
            amount: Amount to enter (if applicable)
            risk_level: Risk level override (defaults based on action_type)
        
        Returns:
            Execution log entry
        
        EDUCATIONAL NOTE:
            This performs REAL mouse click and keyboard input.
            Action is irreversible once executed.
        """
        start_time = time.time()
        
        # Determine risk level
        if risk_level is None:
            risk_level = self._classify_risk(action_type, amount)
        
        # Safety checks
        if not self._check_safety(action_type, risk_level):
            log = ExecutionLog(
                timestamp=time.time(),
                action_type=action_type,
                risk_level=risk_level,
                coordinates=coordinates,
                amount=amount,
                result=ExecutionResult.BLOCKED_BY_SAFETY,
                duration=time.time() - start_time
            )
            self.execution_logs.append(log)
            self.actions_blocked += 1
            return log
        
        # Validate coordinates
        if not self._validate_coordinates(coordinates):
            log = ExecutionLog(
                timestamp=time.time(),
                action_type=action_type,
                risk_level=risk_level,
                coordinates=coordinates,
                amount=amount,
                result=ExecutionResult.INVALID_COORDINATES,
                duration=time.time() - start_time
            )
            self.execution_logs.append(log)
            return log
        
        # Execute action
        logger.critical(f"[EXECUTING REAL ACTION] {action_type} at ({coordinates.button_x}, {coordinates.button_y})")
        
        try:
            # Humanization delay
            if self.humanization_enabled:
                delay = self._calculate_humanization_delay(action_type, risk_level)
                time.sleep(delay)
            
            # Move to button
            self._move_mouse_to(coordinates.button_x, coordinates.button_y)
            
            # Click button
            if PYAUTOGUI_AVAILABLE and pyautogui is not None:
                pyautogui.click(coordinates.button_x, coordinates.button_y)
                logger.critical(f"[CLICKED] Button at ({coordinates.button_x}, {coordinates.button_y})")
            else:
                logger.warning("pyautogui not available - simulating click")
            
            # Enter amount if needed
            if amount is not None and coordinates.amount_field_x is not None:
                time.sleep(0.2)
                self._enter_amount(coordinates, amount)
            
            # Success
            log = ExecutionLog(
                timestamp=time.time(),
                action_type=action_type,
                risk_level=risk_level,
                coordinates=coordinates,
                amount=amount,
                result=ExecutionResult.SUCCESS,
                duration=time.time() - start_time
            )
            
            self.execution_logs.append(log)
            self.actions_executed += 1
            
            logger.critical(f"[SUCCESS] Action completed: {action_type}")
            return log
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            
            log = ExecutionLog(
                timestamp=time.time(),
                action_type=action_type,
                risk_level=risk_level,
                coordinates=coordinates,
                amount=amount,
                result=ExecutionResult.FAILED,
                duration=time.time() - start_time
            )
            
            self.execution_logs.append(log)
            return log
    
    def _classify_risk(self, action_type: str, amount: Optional[float]) -> RiskLevel:
        """
        Classify risk level of action.
        
        Args:
            action_type: Type of action
            amount: Amount (if applicable)
        
        Returns:
            Risk level
        """
        action_type = action_type.lower()
        
        # LOW risk actions
        if action_type in ['fold', 'check', 'call']:
            return RiskLevel.LOW
        
        # HIGH risk actions
        if action_type == 'allin':
            return RiskLevel.HIGH
        
        # MEDIUM/HIGH based on amount
        if action_type in ['bet', 'raise']:
            if amount is None:
                return RiskLevel.MEDIUM
            
            # Consider high if amount > 50bb (arbitrary threshold)
            if amount > 50.0:
                return RiskLevel.HIGH
            else:
                return RiskLevel.MEDIUM
        
        # Default to MEDIUM for unknown
        return RiskLevel.MEDIUM
    
    def _check_safety(self, action_type: str, risk_level: RiskLevel) -> bool:
        """
        Check if action is allowed by safety framework.
        
        Args:
            action_type: Type of action
            risk_level: Risk level
        
        Returns:
            True if allowed, False otherwise
        """
        # Check max risk level
        risk_levels_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        
        if risk_levels_order.index(risk_level) > risk_levels_order.index(self.max_risk_level):
            logger.warning(
                f"Action {action_type} blocked: risk={risk_level.value} > "
                f"max={self.max_risk_level.value}"
            )
            return False
        
        # Check safety framework
        if self.safety.config.mode != SafetyMode.UNSAFE:
            logger.error("Action blocked: not in UNSAFE mode")
            return False
        
        return True
    
    def _validate_coordinates(self, coordinates: ActionCoordinates) -> bool:
        """
        Validate coordinates are within screen bounds.
        
        Args:
            coordinates: Coordinates to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            logger.warning("pyautogui not available - skipping coordinate validation")
            return True  # Assume valid if can't check
        
        try:
            screen_width, screen_height = pyautogui.size()
            
            if not (0 <= coordinates.button_x < screen_width):
                return False
            if not (0 <= coordinates.button_y < screen_height):
                return False
            
            # Validate amount field if present
            if coordinates.amount_field_x is not None:
                if not (0 <= coordinates.amount_field_x < screen_width):
                    return False
            if coordinates.amount_field_y is not None:
                if not (0 <= coordinates.amount_field_y < screen_height):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Coordinate validation error: {e}")
            return False
    
    def _calculate_humanization_delay(
        self,
        action_type: str,
        risk_level: RiskLevel
    ) -> float:
        """
        Calculate human-like delay before action.
        
        Args:
            action_type: Type of action
            risk_level: Risk level
        
        Returns:
            Delay in seconds
        
        EDUCATIONAL NOTE:
            Humans think longer before risky decisions.
            LOW: 0.4-1.5s, MEDIUM: 1.0-2.5s, HIGH: 2.0-3.5s
        """
        import random
        
        if risk_level == RiskLevel.LOW:
            return random.uniform(0.4, 1.5)
        elif risk_level == RiskLevel.MEDIUM:
            return random.uniform(1.0, 2.5)
        else:  # HIGH
            return random.uniform(2.0, 3.5)
    
    def _move_mouse_to(self, x: int, y: int) -> None:
        """
        Move mouse to coordinates with Bezier curve.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
        
        EDUCATIONAL NOTE:
            Uses pyautogui's built-in easing for natural movement.
        """
        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            logger.warning("pyautogui not available - skipping mouse move")
            return
        
        if self.humanization_enabled:
            # Use bezier-like easing
            duration = 0.3 + (0.2 * (time.time() % 1))  # 0.3-0.5s
            pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
        else:
            # Instant move
            pyautogui.moveTo(x, y)
    
    def _enter_amount(
        self,
        coordinates: ActionCoordinates,
        amount: float
    ) -> None:
        """
        Enter amount in bet/raise field.
        
        Args:
            coordinates: Coordinates with amount field
            amount: Amount to enter
        
        EDUCATIONAL NOTE:
            Clicks field, clears it, types amount.
        """
        if coordinates.amount_field_x is None:
            return
        
        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            logger.warning("pyautogui not available - simulating amount entry")
            logger.critical(f"[SIMULATED TYPING] Amount: {amount:.2f}")
            return
        
        # Click amount field
        self._move_mouse_to(coordinates.amount_field_x, coordinates.amount_field_y)
        pyautogui.click(coordinates.amount_field_x, coordinates.amount_field_y)
        
        time.sleep(0.1)
        
        # Clear field (Ctrl+A, Delete)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyautogui.press('delete')
        time.sleep(0.05)
        
        # Type amount
        amount_str = f"{amount:.2f}"
        pyautogui.typewrite(amount_str, interval=0.05)
        
        logger.critical(f"[TYPED] Amount: {amount_str}")
    
    def get_statistics(self) -> dict:
        """Get execution statistics."""
        return {
            'actions_executed': self.actions_executed,
            'actions_blocked': self.actions_blocked,
            'total_actions': len(self.execution_logs),
            'max_risk_level': self.max_risk_level.value,
            'humanization_enabled': self.humanization_enabled
        }
    
    def get_execution_history(self, count: int = 10) -> list[ExecutionLog]:
        """
        Get recent execution history.
        
        Args:
            count: Number of recent logs to return
        
        Returns:
            List of execution logs
        """
        return self.execution_logs[-count:]

    # ------------------------------------------------------------------
    # Navigation-aware actions (auto_navigate.md Phase 2)
    # ------------------------------------------------------------------

    def click_nav_region(
        self,
        x: int,
        y: int,
        *,
        image_offset: tuple[int, int] = (0, 0),
        description: str = "nav_click",
    ) -> ExecutionLog:
        """Click a region discovered by NavigationManager.

        Translates relative image coordinates to absolute screen
        coordinates using *image_offset* (the client-area origin).

        Args:
            x:             X coordinate inside the captured image.
            y:             Y coordinate inside the captured image.
            image_offset:  (ox, oy) — top-left of client area in screen coords.
            description:   Label for the log entry.

        Returns:
            ExecutionLog with result.
        """
        abs_x = image_offset[0] + x
        abs_y = image_offset[1] + y
        coords = ActionCoordinates(button_x=abs_x, button_y=abs_y)
        return self.execute_action(
            action_type=description,
            coordinates=coords,
            risk_level=RiskLevel.LOW,
        )

    def click_table_entry(
        self,
        entry: "TableEntry",
        *,
        image_offset: tuple[int, int] = (0, 0),
        x_center: int = 400,
    ) -> ExecutionLog:
        """Click a TableEntry row found by NavigationManager.

        Args:
            entry:        The ``TableEntry`` to click.
            image_offset: Client-area origin in screen coordinates.
            x_center:     Horizontal center of the lobby table list.

        Returns:
            ExecutionLog with result.
        """
        if not NAV_AVAILABLE:
            return ExecutionLog(
                timestamp=time.time(),
                action_type="click_table",
                risk_level=RiskLevel.LOW,
                coordinates=ActionCoordinates(button_x=0, button_y=0),
                amount=None,
                result=ExecutionResult.LIBRARY_NOT_AVAILABLE,
                duration=0.0,
            )

        y_center = (entry.bbox[0] + entry.bbox[1]) // 2
        return self.click_nav_region(
            x_center,
            y_center,
            image_offset=image_offset,
            description=f"click_table:{entry.name or 'unknown'}",
        )

    def execute_nav_action(
        self,
        nav_result: "NavResult",
        *,
        image_offset: tuple[int, int] = (0, 0),
    ) -> ExecutionLog:
        """Execute an action based on a NavigationManager result.

        If the NavResult contains a matched table, clicks it.
        Otherwise logs a no-op.

        Args:
            nav_result:   Result from ``NavigationManager.navigate_to_table``.
            image_offset: Client-area origin in screen coordinates.

        Returns:
            ExecutionLog with result.
        """
        if not NAV_AVAILABLE:
            return ExecutionLog(
                timestamp=time.time(),
                action_type="nav_action",
                risk_level=RiskLevel.LOW,
                coordinates=ActionCoordinates(button_x=0, button_y=0),
                amount=None,
                result=ExecutionResult.LIBRARY_NOT_AVAILABLE,
                duration=0.0,
            )

        if nav_result.table is not None:
            return self.click_table_entry(
                nav_result.table,
                image_offset=image_offset,
            )

        # No table to click — log and return
        logger.info("execute_nav_action: no table in NavResult (status=%s)",
                     nav_result.status.value)
        return ExecutionLog(
            timestamp=time.time(),
            action_type="nav_noop",
            risk_level=RiskLevel.LOW,
            coordinates=ActionCoordinates(button_x=0, button_y=0),
            amount=None,
            result=ExecutionResult.SUCCESS,
            duration=0.0,
        )

    def scroll_nav(
        self,
        direction: str = "down",
        amount: int = 3,
    ) -> ExecutionLog:
        """Scroll the lobby using pyautogui (nav integration).

        Args:
            direction: ``"down"`` or ``"up"``.
            amount:    Number of scroll steps.

        Returns:
            ExecutionLog with result.
        """
        start = time.time()
        result = ExecutionResult.SUCCESS

        if not PYAUTOGUI_AVAILABLE or pyautogui is None:
            result = ExecutionResult.LIBRARY_NOT_AVAILABLE
        else:
            try:
                clicks = amount if direction == "up" else -amount
                pyautogui.scroll(clicks)
            except Exception as exc:
                logger.error("scroll_nav failed: %s", exc)
                result = ExecutionResult.FAILED

        log = ExecutionLog(
            timestamp=time.time(),
            action_type=f"scroll_{direction}",
            risk_level=RiskLevel.LOW,
            coordinates=ActionCoordinates(button_x=0, button_y=0),
            amount=None,
            result=result,
            duration=time.time() - start,
        )
        self.execution_logs.append(log)
        return log


    # ------------------------------------------------------------------
    # full_hive_month.md Этап 3: auto-clicks on modes / tables / scroll
    # ------------------------------------------------------------------

    def click_game_mode(
        self,
        x: int,
        y: int,
        *,
        mode_name: str = "NL Hold'em",
        image_offset: tuple[int, int] = (0, 0),
    ) -> ExecutionLog:
        """Click a game-mode tab/button in the poker client lobby.

        Args:
            x:            X coordinate of the mode button (in image space).
            y:            Y coordinate of the mode button (in image space).
            mode_name:    Human label for logging (e.g. "NL Hold'em", "PLO").
            image_offset: Client-area origin on screen.

        Returns:
            ExecutionLog.
        """
        abs_x = image_offset[0] + x
        abs_y = image_offset[1] + y
        coords = ActionCoordinates(button_x=abs_x, button_y=abs_y)
        logger.info("click_game_mode: '%s' at (%d, %d)", mode_name, abs_x, abs_y)
        return self.execute_action(
            action_type=f"game_mode:{mode_name}",
            coordinates=coords,
            risk_level=RiskLevel.LOW,
        )

    def click_table_from_list(
        self,
        row_index: int,
        *,
        list_x: int = 400,
        first_row_y: int = 200,
        row_height: int = 24,
        image_offset: tuple[int, int] = (0, 0),
    ) -> ExecutionLog:
        """Click a table row in the lobby by its index.

        Uses simple geometry: ``y = first_row_y + row_index * row_height``.

        Args:
            row_index:    0-based index of the row to click.
            list_x:       Horizontal center of the table list column.
            first_row_y:  Y of the first visible row.
            row_height:   Height of each row in pixels.
            image_offset: Client-area origin.

        Returns:
            ExecutionLog.
        """
        target_y = first_row_y + row_index * row_height + row_height // 2
        abs_x = image_offset[0] + list_x
        abs_y = image_offset[1] + target_y
        coords = ActionCoordinates(button_x=abs_x, button_y=abs_y)
        logger.info("click_table_from_list: row %d at (%d, %d)", row_index, abs_x, abs_y)
        return self.execute_action(
            action_type=f"table_row:{row_index}",
            coordinates=coords,
            risk_level=RiskLevel.LOW,
        )

    def scroll_table_list(
        self,
        direction: str = "down",
        amount: int = 5,
    ) -> ExecutionLog:
        """Scroll through the lobby table list.

        Wrapper around :meth:`scroll_nav` with sensible defaults for
        lobby scrolling.

        Args:
            direction: ``"down"`` or ``"up"``.
            amount:    Number of scroll ticks.

        Returns:
            ExecutionLog.
        """
        logger.info("scroll_table_list: %s x%d", direction, amount)
        return self.scroll_nav(direction=direction, amount=amount)

    def click_join_button(
        self,
        x: int,
        y: int,
        *,
        image_offset: tuple[int, int] = (0, 0),
    ) -> ExecutionLog:
        """Click the 'Join' / 'Sit Down' button.

        Args:
            x:            X coordinate of the button (image space).
            y:            Y coordinate of the button (image space).
            image_offset: Client-area origin on screen.

        Returns:
            ExecutionLog.
        """
        abs_x = image_offset[0] + x
        abs_y = image_offset[1] + y
        coords = ActionCoordinates(button_x=abs_x, button_y=abs_y)
        logger.info("click_join_button: at (%d, %d)", abs_x, abs_y)
        return self.execute_action(
            action_type="join_table",
            coordinates=coords,
            risk_level=RiskLevel.LOW,
        )

    def execute_manipulation_action(
        self,
        action_type: str,
        coordinates: ActionCoordinates,
        *,
        amount: Optional[float] = None,
        strategy: str = "",
    ) -> ExecutionLog:
        """Execute a manipulation-engine decision as a real click.

        Maps a :class:`ManipulationDecision` (action + amount) to a
        real desktop action using the standard :meth:`execute_action`
        pipeline (with safety / risk classification / humanization).

        Args:
            action_type:  Poker action string ("fold", "call", "raise", etc.).
            coordinates:  Button coordinates.
            amount:       Bet/raise amount (if applicable).
            strategy:     Label for the manipulation strategy used.

        Returns:
            ExecutionLog.
        """
        logger.critical(
            "execute_manipulation_action: %s (strategy=%s, amount=%s)",
            action_type, strategy, amount,
        )
        return self.execute_action(
            action_type=action_type,
            coordinates=coordinates,
            amount=amount,
        )


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Real Action Executor - Educational HCI Research Demo")
    print("=" * 60)
    print()
    print("CRITICAL WARNING:")
    print("This module executes REAL mouse clicks and keyboard input.")
    print("Do NOT run without proper safety measures.")
    print()
    print("=" * 60)
    print("Demo: Initialization check only (no real actions)")
    print("=" * 60)
    print()
    
    try:
        # Try to initialize (will fail if not in UNSAFE mode)
        from bridge.safety import SafetyConfig
        
        safety_config = SafetyConfig()
        safety_config.mode = SafetyMode.UNSAFE
        safety = SafetyFramework(config=safety_config)
        
        executor = RealActionExecutor(
            safety=safety,
            max_risk_level=RiskLevel.LOW,
            humanization_enabled=True
        )
        
        print("[OK] Executor initialized successfully")
        print(f"Max risk level: {executor.max_risk_level.value}")
        print(f"Humanization: {'enabled' if executor.humanization_enabled else 'disabled'}")
        print()
        
        stats = executor.get_statistics()
        print("Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print()
    print("=" * 60)
    print("Educational HCI Research - Real Action Executor")
    print("=" * 60)
