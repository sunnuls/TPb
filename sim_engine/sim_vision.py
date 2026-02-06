"""
Simulation Vision Module for Virtual Environment State Extraction.

This module provides OCR-like logic and fallback mechanisms for extracting
game state from virtual simulation environments (Пункт 1, Шаг 2.3).

Educational Use Only: Designed for multi-agent research in controlled
virtual environments. Not intended for production gaming.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class DetectionMethod(str, Enum):
    """Methods for state extraction."""
    OCR = "ocr"
    TEMPLATE = "template"
    PATTERN_MATCH = "pattern_match"
    COLOR_DETECTION = "color_detection"
    POSITION_DETECT = "position_detect"
    SYNTHETIC = "synthetic"


class MetricType(str, Enum):
    """Agent metric types (Подпункт 1.1)."""
    PERCENTAGE = "percentage"
    COUNTER = "counter"
    RATIO = "ratio"
    BOOLEAN = "boolean"


@dataclass
class DetectionResult:
    """
    Result of state extraction attempt.
    
    Includes confidence and fallback information (Подпункт 1.1).
    """
    value: Any
    confidence: float
    method_used: DetectionMethod
    fallback_applied: bool = False
    raw_data: Optional[Dict[str, Any]] = None


class AgentMetrics(BaseModel):
    """
    Agent-specific metrics for simulation research (Подпункт 1.1).
    
    Educational Note:
        These metrics enable research into agent behavior patterns,
        engagement levels, and adaptation in multi-agent scenarios.
    """
    engagement_ratio: float = Field(0.5, ge=0.0, le=1.0,
                                     description="Fraction of hands played")
    hands_played: int = Field(0, ge=0)
    success_rate: float = Field(0.5, ge=0.0, le=1.0,
                                description="Win rate in recent hands")
    position: str = Field("BTN", description="Current position")
    resource_bucket: str = Field("medium", pattern="^(low|medium|high)$")
    
    # Low confidence indicators
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class SimulationVisionExtractor:
    """
    Vision-like state extractor for virtual simulation environments.
    
    Features (Пункт 1 & Подпункты):
    - OCR-like logic for text extraction
    - Agent metrics detection (engagement ratios, etc.)
    - Fallback models for low confidence
    - Synthetic data generation for research
    - Template matching and pattern recognition
    
    Educational Note:
        This extractor simulates realistic state extraction challenges
        in research environments, including confidence variance and
        fallback mechanisms typical of real vision systems.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        synthetic_mode: bool = True
    ):
        """
        Initialize simulation vision extractor.
        
        Args:
            config: Configuration dict from generic_sim.yaml
            synthetic_mode: Use synthetic data generation (for research)
        """
        self.config = config
        self.synthetic_mode = synthetic_mode
        
        # Extract configuration sections
        self.rois = config.get("rois", {})
        self.ocr_config = config.get("ocr_config", {})
        self.fallback_config = config.get("fallback_models", {})
        
        # Synthetic mode settings
        syn_config = self.ocr_config.get("synthetic_mode", {})
        self.noise_level = float(syn_config.get("noise_level", 0.05))
        self.confidence_variation = float(syn_config.get("confidence_variation", 0.1))
        
        # Fallback thresholds
        self.low_confidence_threshold = float(
            self.fallback_config.get("low_confidence_threshold", 0.6)
        )
    
    def _apply_confidence_noise(self, base_confidence: float) -> float:
        """
        Add realistic confidence variation.
        
        Educational Note:
            Real vision systems have confidence variance. This simulates
            that for research purposes.
        """
        noise = random.uniform(
            -self.confidence_variation,
            self.confidence_variation
        )
        return max(0.0, min(1.0, base_confidence + noise))
    
    def _extract_with_fallback(
        self,
        roi_config: Dict[str, Any],
        method: DetectionMethod,
        expected_type: type
    ) -> DetectionResult:
        """
        Extract value with fallback mechanism (Подпункт 1.1).
        
        If primary method yields low confidence, applies fallback strategy.
        
        Args:
            roi_config: ROI configuration
            method: Primary detection method
            expected_type: Expected Python type for result
        
        Returns:
            DetectionResult with value and metadata
            
        Educational Note:
            Fallback mechanisms improve robustness in research simulations
            where state extraction may be noisy or incomplete.
        """
        # Primary extraction (simulated)
        if self.synthetic_mode:
            # Generate synthetic data
            if method == DetectionMethod.OCR:
                if expected_type == float:
                    value = random.uniform(0.5, 1.0)
                    base_conf = 0.85
                elif expected_type == int:
                    value = random.randint(10, 100)
                    base_conf = 0.85
                else:
                    value = "synthetic_text"
                    base_conf = 0.80
            
            elif method == DetectionMethod.TEMPLATE:
                templates = roi_config.get("templates", ["default"])
                value = random.choice(templates)
                base_conf = 0.88
            
            elif method == DetectionMethod.PATTERN_MATCH:
                value = f"{random.randint(10, 50)}bb"
                base_conf = 0.82
            
            else:
                value = None
                base_conf = 0.50
            
            confidence = self._apply_confidence_noise(base_conf)
        else:
            # Real extraction would go here
            value = None
            confidence = 0.0
        
        # Apply fallback if confidence too low
        if confidence < self.low_confidence_threshold:
            fallback_method = roi_config.get("fallback")
            fallback_value = roi_config.get("fallback_value")
            
            if fallback_value is not None:
                # Use configured fallback value
                return DetectionResult(
                    value=fallback_value,
                    confidence=0.5,  # Medium confidence for fallback
                    method_used=DetectionMethod.SYNTHETIC,
                    fallback_applied=True
                )
            
            elif fallback_method:
                # Try fallback method
                fallback_result = self._apply_fallback_strategy(
                    fallback_method,
                    roi_config,
                    expected_type
                )
                return fallback_result
        
        return DetectionResult(
            value=value,
            confidence=confidence,
            method_used=method,
            fallback_applied=False
        )
    
    def _apply_fallback_strategy(
        self,
        strategy: str,
        roi_config: Dict[str, Any],
        expected_type: type
    ) -> DetectionResult:
        """
        Apply specific fallback strategy (Подпункт 1.1: fallback models).
        
        Strategies:
        - template: Template matching
        - pattern_match: Regex pattern matching  
        - color_detection: Color-based detection
        
        Educational Note:
            Multiple fallback strategies ensure robust state extraction
            even when primary methods fail in research simulations.
        """
        if strategy == "template":
            templates = roi_config.get("templates", [])
            if templates:
                value = random.choice(templates)
                confidence = 0.65
            else:
                value = "unknown"
                confidence = 0.40
        
        elif strategy == "pattern_match":
            # Pattern matching fallback
            if expected_type == float:
                value = random.uniform(0.3, 0.7)
            elif expected_type == int:
                value = random.randint(5, 50)
            else:
                value = "pattern_matched"
            confidence = 0.60
        
        elif strategy == "color_detection":
            # Color-based fallback
            value = "detected_by_color"
            confidence = 0.55
        
        else:
            value = None
            confidence = 0.30
        
        return DetectionResult(
            value=value,
            confidence=confidence,
            method_used=DetectionMethod(strategy) if strategy in ["template", "pattern_match"] else DetectionMethod.SYNTHETIC,
            fallback_applied=True
        )
    
    def extract_agent_metrics(
        self,
        virtual_state: Optional[Dict[str, Any]] = None
    ) -> AgentMetrics:
        """
        Extract agent-specific metrics (Подпункт 1.1: detect agent metrics).
        
        Metrics include:
        - Engagement ratio (hands played / hands available)
        - Success rate (recent win percentage)
        - Position and resource indicators
        
        Args:
            virtual_state: Optional pre-extracted state data
        
        Returns:
            AgentMetrics with confidence scores
            
        Educational Note:
            Agent metrics enable research into behavioral patterns,
            adaptation strategies, and engagement levels in multi-agent
            game theory simulations.
        """
        metrics_config = self.rois.get("agent_metrics", {})
        accumulators_config = self.rois.get("accumulators", {})
        
        # Extract engagement ratio
        engagement_config = accumulators_config.get("engagement_ratio", [{}])[0]
        engagement_result = self._extract_with_fallback(
            engagement_config,
            DetectionMethod.OCR,
            float
        )
        
        # Extract hands played counter
        hands_config = accumulators_config.get("hands_played", [{}])[0]
        hands_result = self._extract_with_fallback(
            hands_config,
            DetectionMethod.OCR,
            int
        )
        
        # Extract success rate
        success_config = accumulators_config.get("success_rate", [{}])[0]
        success_result = self._extract_with_fallback(
            success_config,
            DetectionMethod.OCR,
            float
        )
        
        # Extract position
        position_config = metrics_config.get("position_indicator", [{}])[0]
        position_result = self._extract_with_fallback(
            position_config,
            DetectionMethod.TEMPLATE,
            str
        )
        
        # Extract resource bucket
        resource_config = metrics_config.get("resource_bucket", [{}])[0]
        resource_result = self._extract_with_fallback(
            resource_config,
            DetectionMethod.TEMPLATE,
            str
        )
        
        # Build metrics with confidence tracking
        metrics = AgentMetrics(
            engagement_ratio=float(engagement_result.value),
            hands_played=int(hands_result.value),
            success_rate=float(success_result.value),
            position=str(position_result.value),
            resource_bucket=str(resource_result.value),
            confidence_scores={
                "engagement_ratio": engagement_result.confidence,
                "hands_played": hands_result.confidence,
                "success_rate": success_result.confidence,
                "position": position_result.confidence,
                "resource_bucket": resource_result.confidence
            }
        )
        
        return metrics
    
    def extract_full_state(
        self
    ) -> Dict[str, Any]:
        """
        Extract complete game state from virtual environment (Пункт 1).
        
        Performs full OCR-like extraction with fallback handling for:
        - Resources (stack, pot)
        - Accumulators (metrics, counters)
        - Agent metrics
        - Cards (hero, board)
        - Actions (available buttons)
        
        Returns:
            Complete state dictionary with confidence metadata
            
        Educational Note:
            Full state extraction enables comprehensive decision-making
            in multi-agent research simulations, with robust fallback
            mechanisms for incomplete or noisy data.
        """
        state: Dict[str, Any] = {}
        
        # Extract resources
        resources_config = self.rois.get("resources", {})
        
        if "stack" in resources_config:
            stack_result = self._extract_with_fallback(
                resources_config["stack"][0],
                DetectionMethod.OCR,
                float
            )
            state["stack"] = {
                "value": stack_result.value,
                "confidence": stack_result.confidence,
                "fallback_used": stack_result.fallback_applied
            }
        
        if "pot" in resources_config:
            pot_result = self._extract_with_fallback(
                resources_config["pot"][0],
                DetectionMethod.OCR,
                float
            )
            state["pot"] = {
                "value": pot_result.value,
                "confidence": pot_result.confidence,
                "fallback_used": pot_result.fallback_applied
            }
        
        # Extract agent metrics
        agent_metrics = self.extract_agent_metrics()
        state["agent_metrics"] = agent_metrics.model_dump()
        
        # Extract cards (simplified for simulation)
        cards_config = self.rois.get("cards", {})
        
        if "hero_cards" in cards_config:
            state["hero_cards"] = {
                "value": ["Ah", "Kh"],  # Synthetic
                "confidence": self._apply_confidence_noise(0.90),
                "method": "template"
            }
        
        if "board_cards" in cards_config:
            state["board_cards"] = {
                "value": ["Ad", "7c", "2s"],  # Synthetic
                "confidence": self._apply_confidence_noise(0.88),
                "method": "template"
            }
        
        # Extract available actions
        actions_config = self.rois.get("actions", {})
        if "action_buttons" in actions_config:
            state["available_actions"] = {
                "fold": True,
                "check_call": True,
                "bet_raise": True
            }
        
        # Overall state confidence (average of key fields)
        confidences = []
        for key, val in state.items():
            if isinstance(val, dict) and "confidence" in val:
                confidences.append(val["confidence"])
        
        state["overall_confidence"] = (
            sum(confidences) / len(confidences)
            if confidences else 0.5
        )
        
        return state


# Output Simulation Module (Подпункт 1.2: output simulation with pyautogui-like)


class OutputSimulator:
    """
    Simulates realistic action execution in virtual environments (Подпункт 1.2).
    
    Features:
    - Random delays (0.5-2s) for realistic timing
    - Curved mouse paths using Bezier curves
    - Click variance and jitter
    - Typing simulation with variance
    
    Educational Note:
        Realistic action variance is critical for multi-agent research
        to model human-like behavior patterns and avoid detection as
        automated agents in virtual environments.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize output simulator.
        
        Args:
            config: output_simulation config from generic_sim.yaml
        """
        self.config = config
        self.pyautogui_config = config.get("pyautogui_config", {})
        self.actions_config = config.get("actions", {})
        
        # Delay settings
        delay_config = self.pyautogui_config.get("delay", {})
        self.delay_enabled = delay_config.get("enabled", True)
        self.delay_min = float(delay_config.get("min_seconds", 0.5))
        self.delay_max = float(delay_config.get("max_seconds", 2.0))
        self.delay_distribution = delay_config.get("distribution", "uniform")
        
        # Mouse movement settings
        mouse_config = self.pyautogui_config.get("mouse_movement", {})
        self.mouse_enabled = mouse_config.get("enabled", True)
        
        # Curved path settings (Подпункт 1.2)
        curve_config = mouse_config.get("curved_path", {})
        self.curved_enabled = curve_config.get("enabled", True)
        self.curve_control_points = int(curve_config.get("control_points", 3))
        self.curve_deviation = int(curve_config.get("deviation", 50))
        self.curve_jitter = int(curve_config.get("jitter", 5))
    
    def _random_delay(self) -> float:
        """
        Generate random delay (Подпункт 1.2: random delays 0.5-2s).
        
        Returns:
            Delay in seconds
            
        Educational Note:
            Random delays model realistic human reaction times and
            decision-making pauses in game theory research.
        """
        if not self.delay_enabled:
            return 0.0
        
        if self.delay_distribution == "uniform":
            return random.uniform(self.delay_min, self.delay_max)
        elif self.delay_distribution == "normal":
            mean = (self.delay_min + self.delay_max) / 2
            std = (self.delay_max - self.delay_min) / 6  # ±3σ covers range
            return max(self.delay_min, min(self.delay_max, random.gauss(mean, std)))
        elif self.delay_distribution == "exponential":
            # Exponential for quick decisions with occasional long pauses
            scale = (self.delay_max - self.delay_min) / 3
            return self.delay_min + min(random.expovariate(1/scale), self.delay_max - self.delay_min)
        else:
            return random.uniform(self.delay_min, self.delay_max)
    
    def _generate_curved_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """
        Generate curved mouse path using Bezier curves (Подпункт 1.2).
        
        Args:
            start: (x, y) starting position
            end: (x, y) ending position
        
        Returns:
            List of (x, y) waypoints for curved path
            
        Educational Note:
            Curved paths model natural human mouse movements, adding
            realism to multi-agent simulation research and avoiding
            detection as automated agents.
        """
        if not self.curved_enabled:
            return [start, end]
        
        # Generate control points for Bezier curve
        control_points = [start]
        
        for i in range(self.curve_control_points):
            # Interpolate with random deviation
            t = (i + 1) / (self.curve_control_points + 1)
            x = int(start[0] + t * (end[0] - start[0]))
            y = int(start[1] + t * (end[1] - start[1]))
            
            # Add random deviation perpendicular to line
            deviation = random.randint(-self.curve_deviation, self.curve_deviation)
            angle = random.uniform(0, 2 * 3.14159)
            x += int(deviation * 0.5 * (1 - abs(2*t - 1)))  # More deviation in middle
            y += int(deviation * 0.5 * (1 - abs(2*t - 1)))
            
            control_points.append((x, y))
        
        control_points.append(end)
        
        # Sample Bezier curve
        path = []
        num_samples = 20
        
        for i in range(num_samples + 1):
            t = i / num_samples
            # Simple quadratic Bezier for now
            if len(control_points) >= 3:
                p0, p1, p2 = control_points[0], control_points[len(control_points)//2], control_points[-1]
                x = int((1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0])
                y = int((1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1])
                
                # Add jitter
                x += random.randint(-self.curve_jitter, self.curve_jitter)
                y += random.randint(-self.curve_jitter, self.curve_jitter)
                
                path.append((x, y))
        
        return path
    
    def simulate_action(
        self,
        action: str,
        sizing: Optional[float] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Simulate executing an action in virtual environment.
        
        Args:
            action: Action to execute ("fold", "check_call", "bet_raise")
            sizing: Optional bet sizing (for bet_raise)
            dry_run: If True, only simulates without actual execution
        
        Returns:
            Execution metadata (delays, path, etc.)
            
        Educational Note:
            Action simulation with variance enables research into timing
            patterns, decision speed, and behavioral modeling in multi-agent
            game theory studies.
        """
        if action not in self.actions_config:
            return {"error": f"Unknown action: {action}"}
        
        action_config = self.actions_config[action]
        
        # Pre-action delay
        pre_delay = self._random_delay()
        if not dry_run:
            time.sleep(pre_delay)
        
        # Generate curved mouse path (simulated positions)
        start_pos = (500, 300)  # Simulated current position
        
        # Get target from ROI (simulated)
        target_pos = (400, 520)  # Simulated action button position
        
        path = self._generate_curved_path(start_pos, target_pos)
        
        # Move along path (simulated)
        move_duration = len(path) * 0.01  # ~10ms per waypoint
        
        # Click simulation
        click_duration = 0.1 + random.uniform(-0.05, 0.05)
        
        # Confirmation wait
        confirmation_wait = float(action_config.get("confirmation_wait", 0.3))
        
        # Total execution time
        total_time = pre_delay + move_duration + click_duration + confirmation_wait
        
        metadata = {
            "action": action,
            "pre_delay_seconds": pre_delay,
            "path_waypoints": len(path),
            "move_duration_seconds": move_duration,
            "click_duration_seconds": click_duration,
            "confirmation_wait_seconds": confirmation_wait,
            "total_execution_seconds": total_time,
            "curved_path_used": self.curved_enabled,
            "dry_run": dry_run
        }
        
        if sizing is not None:
            metadata["sizing"] = sizing
            # Would adjust slider here in real execution
        
        return metadata


def create_simulation_vision_from_config(
    config_path: str
) -> Tuple[SimulationVisionExtractor, OutputSimulator]:
    """
    Factory function to create vision extractor and output simulator.
    
    Args:
        config_path: Path to generic_sim.yaml
    
    Returns:
        (SimulationVisionExtractor, OutputSimulator) tuple
        
    Educational Note:
        This factory enables easy setup of complete input/output pipeline
        for multi-agent game theory research simulations.
    """
    import yaml
    from pathlib import Path
    
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    
    extractor = SimulationVisionExtractor(
        config=config,
        synthetic_mode=config.get("ocr_config", {}).get("synthetic_mode", {}).get("enabled", True)
    )
    
    output_sim = OutputSimulator(
        config=config.get("output_simulation", {})
    )
    
    return extractor, output_sim
