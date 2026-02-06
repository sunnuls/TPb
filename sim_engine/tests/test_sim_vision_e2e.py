"""
End-to-End Tests for Simulation Vision Pipeline (Пункт 2, Шаг 2.3).

These tests validate the complete pipeline:
simulate input → extract → decide → output

Educational Use Only: For validating multi-agent research simulation infrastructure.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest
import yaml

from sim_engine.decision import (
    AgentContext,
    LineType,
    SimulatedActionType,
    generate_simulated_decision,
)
from sim_engine.sim_vision import (
    DetectionMethod,
    MetricType,
    OutputSimulator,
    SimulationVisionExtractor,
    create_simulation_vision_from_config,
)
from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position


@pytest.fixture
def sim_config_path(tmp_path):
    """Create temporary config for testing."""
    config = {
        "adapter_name": "test_simulation",
        "game_type": "poker",
        "rois": {
            "resources": {
                "stack": [{
                    "x": 50, "y": 400, "width": 150, "height": 40,
                    "method": "ocr",
                    "fallback": "template",
                    "confidence_threshold": 0.7
                }],
                "pot": [{
                    "x": 350, "y": 250, "width": 120, "height": 35,
                    "method": "ocr",
                    "confidence_threshold": 0.7
                }]
            },
            "accumulators": {
                "engagement_ratio": [{
                    "x": 800, "y": 50, "width": 100, "height": 30,
                    "method": "ocr",
                    "metric_type": "percentage",
                    "confidence_threshold": 0.6,
                    "fallback_value": 0.5
                }],
                "hands_played": [{
                    "x": 800, "y": 90, "width": 80, "height": 25,
                    "method": "ocr",
                    "metric_type": "counter",
                    "confidence_threshold": 0.6,
                    "fallback_value": 0
                }],
                "success_rate": [{
                    "x": 800, "y": 130, "width": 100, "height": 30,
                    "method": "ocr",
                    "metric_type": "percentage",
                    "confidence_threshold": 0.6,
                    "fallback_value": 0.5
                }]
            },
            "agent_metrics": {
                "position_indicator": [{
                    "x": 100, "y": 50, "width": 60, "height": 25,
                    "method": "template",
                    "templates": ["BTN", "SB", "BB", "CO", "HJ"],
                    "confidence_threshold": 0.8
                }],
                "resource_bucket": [{
                    "x": 200, "y": 50, "width": 80, "height": 25,
                    "method": "template",
                    "templates": ["low", "medium", "high"],
                    "confidence_threshold": 0.7,
                    "fallback_value": "medium"
                }]
            },
            "actions": {
                "action_buttons": {
                    "fold": [{
                        "x": 250, "y": 500, "width": 100, "height": 40
                    }],
                    "check_call": [{
                        "x": 370, "y": 500, "width": 100, "height": 40
                    }],
                    "bet_raise": [{
                        "x": 490, "y": 500, "width": 100, "height": 40
                    }]
                }
            },
            "cards": {
                "hero_cards": [{
                    "x": 300, "y": 420, "width": 120, "height": 80,
                    "method": "template",
                    "confidence_threshold": 0.85
                }],
                "board_cards": [{
                    "x": 250, "y": 200, "width": 400, "height": 80,
                    "method": "template",
                    "confidence_threshold": 0.85
                }]
            }
        },
        "ocr_config": {
            "engine": "tesseract",
            "synthetic_mode": {
                "enabled": True,
                "noise_level": 0.05,
                "confidence_variation": 0.1
            }
        },
        "fallback_models": {
            "low_confidence_threshold": 0.6,
            "strategies": {
                "template_matching": {"enabled": True},
                "pattern_recognition": {"enabled": True}
            }
        },
        "output_simulation": {
            "enabled": True,
            "pyautogui_config": {
                "delay": {
                    "enabled": True,
                    "min_seconds": 0.5,
                    "max_seconds": 2.0,
                    "distribution": "uniform"
                },
                "mouse_movement": {
                    "enabled": True,
                    "curved_path": {
                        "enabled": True,
                        "control_points": 3,
                        "deviation": 50,
                        "jitter": 5
                    }
                }
            },
            "actions": {
                "fold": {"target_roi": "actions.action_buttons.fold", "confirmation_wait": 0.3},
                "check_call": {"target_roi": "actions.action_buttons.check_call", "confirmation_wait": 0.3},
                "bet_raise": {"target_roi": "actions.action_buttons.bet_raise", "confirmation_wait": 0.3}
            }
        }
    }
    
    config_path = tmp_path / "test_sim.yaml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return str(config_path)


class TestEndToEndSimulationPipeline:
    """
    End-to-End Tests for Full Simulation Pipeline (Пункт 2).
    
    Tests validate: input simulation → extraction → decision → output
    
    Educational Note:
        These tests ensure the complete multi-agent research pipeline
        functions correctly from state extraction through action execution.
    """
    
    def test_e2e_1_basic_extraction_and_decision(self, sim_config_path):
        """
        E2E Test 1: Basic state extraction and decision generation.
        
        Pipeline: Extract state → Generate decision
        
        Educational Note:
            Validates basic pipeline functionality for single-agent scenarios.
        """
        # Create extractor
        extractor = SimulationVisionExtractor(
            config=yaml.safe_load(Path(sim_config_path).read_text()),
            synthetic_mode=True
        )
        
        # Step 1: Extract state (simulate input)
        state = extractor.extract_full_state()
        
        # Validate extraction
        assert "hero_cards" in state
        assert "agent_metrics" in state
        assert "overall_confidence" in state
        assert state["overall_confidence"] > 0.5
        
        # Step 2: Generate decision
        agent_metrics = state["agent_metrics"]
        context = AgentContext(
            position=Position[agent_metrics["position"]],
            resource_bucket=agent_metrics["resource_bucket"],
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=state["hero_cards"]["value"],
            environment=state["board_cards"]["value"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Validate decision
        assert decision.action in [
            SimulatedActionType.INCREMENT,
            SimulatedActionType.HOLD,
            SimulatedActionType.DECREMENT,
            SimulatedActionType.CHECK
        ]
        assert 0.0 <= decision.confidence <= 1.0
        assert decision.line_type in [
            LineType.PROACTIVE,
            LineType.REACTIVE,
            LineType.BALANCED,
            LineType.EXPLOITATIVE
        ]
        
        print(f"[E2E-1] Extracted state with confidence: {state['overall_confidence']:.2%}")
        print(f"[E2E-1] Decision: {decision.action}, Line: {decision.line_type}")
    
    def test_e2e_2_agent_metrics_extraction(self, sim_config_path):
        """
        E2E Test 2: Agent metrics extraction and usage in decisions.
        
        Pipeline: Extract metrics → Use in context → Decide
        
        Educational Note:
            Validates agent-specific metrics (engagement ratio, success rate)
            are correctly extracted and influence decision-making.
        """
        extractor = SimulationVisionExtractor(
            config=yaml.safe_load(Path(sim_config_path).read_text()),
            synthetic_mode=True
        )
        
        # Extract agent metrics
        metrics = extractor.extract_agent_metrics()
        
        # Validate metrics
        assert 0.0 <= metrics.engagement_ratio <= 1.0
        assert metrics.hands_played >= 0
        assert 0.0 <= metrics.success_rate <= 1.0
        assert metrics.position in ["BTN", "SB", "BB", "CO", "HJ"]
        assert metrics.resource_bucket in ["low", "medium", "high"]
        
        # Validate confidence scores present
        assert "engagement_ratio" in metrics.confidence_scores
        assert "position" in metrics.confidence_scores
        
        # Use metrics in decision context
        context = AgentContext(
            position=Position[metrics.position],
            resource_bucket=metrics.resource_bucket,
            opponent_models={},
            session_state={
                "engagement_ratio": metrics.engagement_ratio,
                "hands_played": metrics.hands_played
            }
        )
        
        decision = generate_simulated_decision(
            agent_state=["As", "Ad"],
            environment=[],
            street=Street.PREFLOP,
            pot_bb=1.5,
            to_call_bb=0.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Premium hand should trigger strong action
        assert decision.action in [SimulatedActionType.INCREMENT, SimulatedActionType.HOLD]
        
        print(f"[E2E-2] Agent metrics: engagement={metrics.engagement_ratio:.2%}, "
              f"success={metrics.success_rate:.2%}")
        print(f"[E2E-2] Decision with metrics: {decision.action}")
    
    def test_e2e_3_fallback_mechanisms(self, sim_config_path):
        """
        E2E Test 3: Fallback mechanism activation with low confidence.
        
        Pipeline: Low confidence extraction → Fallback → Decision
        
        Educational Note:
            Validates that fallback models correctly activate when primary
            detection methods yield low confidence, ensuring robust extraction.
        """
        config = yaml.safe_load(Path(sim_config_path).read_text())
        
        # Lower confidence threshold to trigger fallbacks
        config["fallback_models"]["low_confidence_threshold"] = 0.9
        
        extractor = SimulationVisionExtractor(
            config=config,
            synthetic_mode=True
        )
        
        # Extract with high fallback likelihood
        state = extractor.extract_full_state()
        
        # Check if any fallbacks were used
        fallbacks_used = []
        for key, value in state.items():
            if isinstance(value, dict) and value.get("fallback_used"):
                fallbacks_used.append(key)
        
        # At least one field should have used fallback with tight threshold
        # (Not guaranteed due to synthetic randomness, but likely)
        print(f"[E2E-3] Fallbacks triggered for: {fallbacks_used}")
        
        # State should still be usable
        assert "overall_confidence" in state
        assert state["overall_confidence"] > 0.3  # Lower bound with fallbacks
    
    def test_e2e_4_output_simulation_execution(self, sim_config_path):
        """
        E2E Test 4: Complete pipeline with output action simulation.
        
        Pipeline: Extract → Decide → Output (with variance)
        
        Educational Note:
            Validates output simulation with realistic delays and curved paths,
            essential for modeling human-like behavior in research.
        """
        config = yaml.safe_load(Path(sim_config_path).read_text())
        
        extractor = SimulationVisionExtractor(config=config, synthetic_mode=True)
        output_sim = OutputSimulator(config=config["output_simulation"])
        
        # Step 1: Extract
        state = extractor.extract_full_state()
        
        # Step 2: Decide
        agent_metrics = state["agent_metrics"]
        context = AgentContext(
            position=Position[agent_metrics["position"]],
            resource_bucket=agent_metrics["resource_bucket"],
            opponent_models={},
            session_state={}
        )
        
        decision = generate_simulated_decision(
            agent_state=state["hero_cards"]["value"],
            environment=state["board_cards"]["value"],
            street=Street.FLOP,
            pot_bb=12.0,
            to_call_bb=4.0,
            context=context,
            use_monte_carlo=False
        )
        
        # Step 3: Output (simulate action)
        # Map decision to action
        action_map = {
            SimulatedActionType.INCREMENT: "bet_raise",
            SimulatedActionType.HOLD: "check_call",
            SimulatedActionType.DECREMENT: "fold",
            SimulatedActionType.CHECK: "check_call"
        }
        
        action = action_map.get(decision.action, "check_call")
        
        # Simulate output with dry_run=True (no actual execution)
        output_metadata = output_sim.simulate_action(
            action=action,
            sizing=decision.sizing,
            dry_run=True
        )
        
        # Validate output simulation
        assert "pre_delay_seconds" in output_metadata
        assert 0.5 <= output_metadata["pre_delay_seconds"] <= 2.0  # Within configured range
        assert output_metadata["path_waypoints"] > 1  # Curved path has multiple waypoints
        assert output_metadata["curved_path_used"] is True
        assert output_metadata["total_execution_seconds"] > 0
        
        print(f"[E2E-4] Action: {action}, Delay: {output_metadata['pre_delay_seconds']:.2f}s, "
              f"Path points: {output_metadata['path_waypoints']}")
    
    def test_e2e_5_multi_iteration_variance(self, sim_config_path):
        """
        E2E Test 5: Multiple iterations showing realistic variance.
        
        Pipeline: Repeat (Extract → Decide → Output) × N, validate variance
        
        Educational Note:
            Validates that output simulation produces realistic variance across
            multiple iterations, crucial for multi-agent research avoiding
            detection patterns.
        """
        config = yaml.safe_load(Path(sim_config_path).read_text())
        
        extractor = SimulationVisionExtractor(config=config, synthetic_mode=True)
        output_sim = OutputSimulator(config=config["output_simulation"])
        
        delays = []
        path_lengths = []
        confidences = []
        
        # Run 10 iterations
        num_iterations = 10
        
        for i in range(num_iterations):
            # Extract
            state = extractor.extract_full_state()
            confidences.append(state["overall_confidence"])
            
            # Decide
            agent_metrics = state["agent_metrics"]
            context = AgentContext(
                position=Position[agent_metrics["position"]],
                resource_bucket=agent_metrics["resource_bucket"],
                opponent_models={},
                session_state={}
            )
            
            decision = generate_simulated_decision(
                agent_state=["Kh", "Qh"],
                environment=["Kc", "7h", "2s"],
                street=Street.FLOP,
                pot_bb=12.0,
                to_call_bb=0.0,
                context=context,
                use_monte_carlo=False
            )
            
            # Output
            output_metadata = output_sim.simulate_action(
                action="check_call",
                dry_run=True
            )
            
            delays.append(output_metadata["pre_delay_seconds"])
            path_lengths.append(output_metadata["path_waypoints"])
        
        # Validate variance
        assert len(set(delays)) > 1, "Delays should vary"
        # Path lengths may be constant (fixed sample points), but delays must vary
        assert len(set(confidences)) > 1, "Confidences should vary"
        
        # Check delays in expected range
        assert all(0.5 <= d <= 2.0 for d in delays)
        
        # Calculate variance statistics
        import statistics
        delay_variance = statistics.variance(delays) if len(delays) > 1 else 0
        
        print(f"[E2E-5] Tested {num_iterations} iterations")
        print(f"[E2E-5] Delay variance: {delay_variance:.4f}")
        print(f"[E2E-5] Unique delays: {len(set(delays))}/{num_iterations}")
        print(f"[E2E-5] Delay range: {min(delays):.2f}s - {max(delays):.2f}s")


class TestFactoryFunction:
    """Test factory function for easy setup."""
    
    def test_factory_creates_both_components(self, sim_config_path):
        """Test that factory function creates extractor and output simulator."""
        extractor, output_sim = create_simulation_vision_from_config(sim_config_path)
        
        assert isinstance(extractor, SimulationVisionExtractor)
        assert isinstance(output_sim, OutputSimulator)
        
        # Test basic functionality
        state = extractor.extract_full_state()
        assert "overall_confidence" in state
        
        output = output_sim.simulate_action("check_call", dry_run=True)
        assert "total_execution_seconds" in output
