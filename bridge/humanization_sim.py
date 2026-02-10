"""
Humanization Simulator Module (Roadmap3 Phase 5.3).

Simulates human-like interaction patterns - **NO REAL INPUT**.
Models timing delays, mouse paths, and behavioral variance.

Key Features:
- Realistic timing delays (think time + execution time)
- Mouse path generation (Bezier curves)
- Action variance (never identical timing)
- Fatigue modeling (slower actions over time)
- Attention patterns (faster/slower based on hand strength)

EDUCATIONAL USE ONLY: For HCI research prototype.
Models human behavior without actual execution.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MousePath:
    """
    Simulated mouse movement path.
    
    Attributes:
        start: Starting position (x, y)
        end: Target position (x, y)
        points: Intermediate points along path
        duration: Total movement duration (seconds)
        distance: Euclidean distance (pixels)
    """
    start: Tuple[int, int]
    end: Tuple[int, int]
    points: List[Tuple[int, int]]
    duration: float
    distance: float


@dataclass
class TimingVariance:
    """
    Timing variance parameters for action.
    
    Attributes:
        base_delay: Base delay before action (seconds)
        variance: Random variance range (±seconds)
        think_time: Thinking time before action (seconds)
        execution_time: Action execution time (seconds)
        total_time: Combined total time (seconds)
    """
    base_delay: float
    variance: float
    think_time: float
    execution_time: float
    total_time: float


class HumanizationSimulator:
    """
    Simulates human-like interaction patterns.
    
    Simulation Components:
    1. Think Time: Decision making delay (0.5-3.0s typical)
    2. Mouse Movement: Curved path with variable speed
    3. Execution Time: Click/type timing (0.1-0.3s)
    4. Variance: Never identical timing between actions
    5. Fatigue: Gradual slowdown over session
    
    **IMPORTANT**: NO REAL INPUT IS EXECUTED
    - No actual mouse movement
    - No real clicks
    - ONLY timing and path simulation
    
    EDUCATIONAL NOTE:
        This models realistic human behavior for research purposes.
        Helps understand timing patterns in multi-agent coordination.
    """
    
    def __init__(
        self,
        base_think_time: float = 1.5,
        think_variance: float = 0.8,
        fatigue_factor: float = 0.05,
        attention_factor: float = 0.3
    ):
        """
        Initialize humanization simulator.
        
        Args:
            base_think_time: Average thinking time (seconds)
            think_variance: Variance in think time (±seconds)
            fatigue_factor: Fatigue accumulation rate
            attention_factor: Attention-based timing adjustment
        """
        self.base_think_time = base_think_time
        self.think_variance = think_variance
        self.fatigue_factor = fatigue_factor
        self.attention_factor = attention_factor
        
        # Session state
        self.actions_count = 0
        self.session_duration = 0.0
        self.fatigue_level = 0.0
        
        logger.info(
            f"HumanizationSimulator initialized: "
            f"think_time={base_think_time}±{think_variance}s"
        )
    
    def simulate_timing(
        self,
        action_type: str,
        hand_strength: float = 0.5,
        is_important: bool = False
    ) -> TimingVariance:
        """
        Simulate realistic action timing.
        
        Args:
            action_type: Type of action ('fold', 'call', 'raise', etc)
            hand_strength: Hand strength (0.0-1.0) affects timing
            is_important: Whether action is important (all-in, big bet)
        
        Returns:
            TimingVariance with all timing components
        
        EDUCATIONAL NOTE:
            Timing patterns:
            - Strong hands: faster decisions (less thinking)
            - Weak hands: slower (more thinking about fold)
            - Important actions: more thinking time
            - Fatigue: gradually slower over time
        """
        # Base think time with variance
        think_time = self.base_think_time + random.uniform(
            -self.think_variance, 
            self.think_variance
        )
        
        # Adjust for hand strength
        # Strong hands (0.8+): 70% of normal think time
        # Weak hands (0.2-): 130% of normal think time
        strength_factor = 1.0 - (hand_strength - 0.5) * self.attention_factor
        think_time *= strength_factor
        
        # Adjust for action importance
        if is_important:
            think_time *= 1.5  # 50% longer for important decisions
        
        # Apply fatigue
        think_time *= (1.0 + self.fatigue_level)
        
        # Execution time (mouse movement + click)
        execution_time = self._simulate_execution_time(action_type)
        
        # Base delay (time before starting to move mouse)
        base_delay = random.uniform(0.1, 0.3)
        
        # Calculate total
        total_time = base_delay + think_time + execution_time
        
        # Update session state
        self.actions_count += 1
        self.session_duration += total_time
        self.fatigue_level = min(
            0.5,  # Max 50% slowdown
            self.fatigue_level + self.fatigue_factor
        )
        
        logger.debug(
            f"Timing simulated: {action_type}, "
            f"think={think_time:.2f}s, exec={execution_time:.2f}s, "
            f"total={total_time:.2f}s"
        )
        
        return TimingVariance(
            base_delay=base_delay,
            variance=self.think_variance,
            think_time=think_time,
            execution_time=execution_time,
            total_time=total_time
        )
    
    def simulate_mouse_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: Optional[float] = None
    ) -> MousePath:
        """
        Simulate mouse movement path using Bezier curve.
        
        Args:
            start: Starting position (x, y)
            end: Target position (x, y)
            duration: Movement duration (auto-calculated if None)
        
        Returns:
            MousePath with smooth curved trajectory
        
        EDUCATIONAL NOTE:
            Human mouse movement is rarely straight line.
            Uses quadratic Bezier curve for realistic path.
        """
        # Calculate distance
        distance = math.sqrt(
            (end[0] - start[0])**2 + 
            (end[1] - start[1])**2
        )
        
        # Calculate duration if not provided
        # Typical: 200-400 pixels/second
        if duration is None:
            pixels_per_second = random.uniform(200, 400)
            duration = distance / pixels_per_second
        
        # Generate control point for Bezier curve
        # Offset perpendicular to direct line
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
        # Perpendicular offset (random direction)
        offset = random.uniform(20, 60)
        if random.random() < 0.5:
            offset = -offset
        
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        perp_angle = angle + math.pi / 2
        
        control = (
            int(mid_x + offset * math.cos(perp_angle)),
            int(mid_y + offset * math.sin(perp_angle))
        )
        
        # Generate points along Bezier curve
        num_points = max(10, int(distance / 10))
        points = []
        
        for i in range(num_points + 1):
            t = i / num_points
            
            # Quadratic Bezier: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
            x = (
                (1 - t)**2 * start[0] + 
                2 * (1 - t) * t * control[0] + 
                t**2 * end[0]
            )
            y = (
                (1 - t)**2 * start[1] + 
                2 * (1 - t) * t * control[1] + 
                t**2 * end[1]
            )
            
            points.append((int(x), int(y)))
        
        logger.debug(
            f"Mouse path simulated: {start} → {end}, "
            f"distance={distance:.0f}px, duration={duration:.2f}s, "
            f"points={len(points)}"
        )
        
        return MousePath(
            start=start,
            end=end,
            points=points,
            duration=duration,
            distance=distance
        )
    
    def _simulate_execution_time(self, action_type: str) -> float:
        """
        Simulate execution time for action.
        
        Args:
            action_type: Type of action
        
        Returns:
            Execution time in seconds
        
        EDUCATIONAL NOTE:
            Execution times vary by action complexity:
            - Fold/check/call: 0.15-0.25s (simple button click)
            - Bet/raise: 0.3-0.5s (input + confirm)
            - All-in: 0.2-0.35s (button + confirm)
        """
        action_lower = action_type.lower()
        
        if action_lower in ['fold', 'check', 'call']:
            # Simple actions - just click button
            return random.uniform(0.15, 0.25)
        
        elif action_lower in ['bet', 'raise']:
            # Complex actions - input amount + confirm
            return random.uniform(0.3, 0.5)
        
        elif action_lower == 'all_in':
            # Medium complexity - click + confirm
            return random.uniform(0.2, 0.35)
        
        else:
            # Default
            return random.uniform(0.2, 0.3)
    
    def reset_fatigue(self) -> None:
        """
        Reset fatigue level (e.g., after break).
        
        EDUCATIONAL NOTE:
            Simulates taking a break to reset attention/fatigue.
        """
        self.fatigue_level = 0.0
        logger.info("Fatigue reset (simulated break)")
    
    def get_statistics(self) -> dict:
        """Get humanization simulator statistics."""
        avg_time = (
            self.session_duration / self.actions_count
            if self.actions_count > 0 else 0.0
        )
        
        return {
            'actions_count': self.actions_count,
            'session_duration': self.session_duration,
            'average_action_time': avg_time,
            'fatigue_level': self.fatigue_level,
            'base_think_time': self.base_think_time,
            'think_variance': self.think_variance
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Humanization Simulator - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Create simulator
    simulator = HumanizationSimulator(
        base_think_time=1.5,
        think_variance=0.8
    )
    
    # Simulate timing for different scenarios
    scenarios = [
        ('fold', 0.2, False, "Weak hand fold"),
        ('call', 0.5, False, "Medium hand call"),
        ('raise', 0.8, False, "Strong hand raise"),
        ('raise', 0.9, True, "Very strong hand big raise"),
        ('all_in', 0.95, True, "Premium hand all-in")
    ]
    
    print("Timing Simulations:")
    print("-" * 60)
    
    for action, strength, important, description in scenarios:
        print(f"\n{description}:")
        
        timing = simulator.simulate_timing(
            action_type=action,
            hand_strength=strength,
            is_important=important
        )
        
        print(f"  Think time: {timing.think_time:.2f}s")
        print(f"  Execution time: {timing.execution_time:.2f}s")
        print(f"  Total time: {timing.total_time:.2f}s")
    
    print()
    print("=" * 60)
    print("Mouse Path Simulation:")
    print("=" * 60)
    
    # Simulate mouse paths
    paths = [
        ((100, 100), (300, 200), "Fold button"),
        ((100, 100), (400, 150), "Raise button"),
        ((100, 100), (250, 300), "Bet slider")
    ]
    
    for start, end, description in paths:
        print(f"\n{description}:")
        
        path = simulator.simulate_mouse_path(start, end)
        
        print(f"  Distance: {path.distance:.0f}px")
        print(f"  Duration: {path.duration:.2f}s")
        print(f"  Points: {len(path.points)}")
        print(f"  Start: {path.start} -> End: {path.end}")
    
    print()
    print("=" * 60)
    print("Statistics:")
    print("=" * 60)
    stats = simulator.get_statistics()
    print(f"Actions simulated: {stats['actions_count']}")
    print(f"Session duration: {stats['session_duration']:.2f}s")
    print(f"Average action time: {stats['average_action_time']:.2f}s")
    print(f"Fatigue level: {stats['fatigue_level']:.1%}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - Behavior Modeling")
    print("=" * 60)
    print("[NOTE] NO REAL INPUT - simulation only")
