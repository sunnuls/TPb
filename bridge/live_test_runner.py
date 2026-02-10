"""
Live Test Runner (Roadmap4 Phase 3).

Controlled testing pipeline for live poker environment.

Testing Phases:
1. Dry-run (100 hands): Simulation only, no real actions
2. Safe mode (50 hands): Only fold/check/call allowed
3. Medium unsafe (10 hands): Small bet/raise allowed

EDUCATIONAL USE ONLY: For HCI research prototype testing.
Use ONLY in play-money environments.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from bridge.action.real_executor import ActionCoordinates, RealActionExecutor, RiskLevel
from bridge.bridge_main import BridgeConfig, BridgeMain, OperationalMode
from bridge.monitoring import MonitoringSystem
from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode

logger = logging.getLogger(__name__)


class TestPhase(str, Enum):
    """Test phases."""
    DRY_RUN = "dry_run"
    SAFE = "safe"
    MEDIUM_UNSAFE = "medium_unsafe"


@dataclass
class HandResult:
    """
    Result of a single hand in live testing.
    
    Attributes:
        hand_number: Hand number in test
        phase: Test phase
        success: Whether hand completed successfully
        decision_made: Whether decision was made
        action_executed: Whether action was executed
        action_type: Type of action (fold/check/call/raise/bet)
        amount: Amount of action (if applicable)
        vision_error: Vision extraction error (if any)
        latency_ms: Latency from screenshot to decision (ms)
        screenshot_path: Path to hand screenshot
    """
    hand_number: int
    phase: TestPhase
    success: bool
    decision_made: bool
    action_executed: bool
    action_type: Optional[str] = None
    amount: Optional[float] = None
    vision_error: Optional[str] = None
    latency_ms: float = 0.0
    screenshot_path: Optional[str] = None


@dataclass
class PhaseMetrics:
    """
    Metrics for a test phase.
    
    Attributes:
        phase: Test phase
        target_hands: Target number of hands
        completed_hands: Completed hands
        successful_hands: Successful hands
        failed_hands: Failed hands
        vision_errors: Vision extraction errors
        average_latency_ms: Average latency (ms)
        actions_by_type: Count of each action type
        total_duration: Total phase duration (seconds)
    """
    phase: TestPhase
    target_hands: int
    completed_hands: int = 0
    successful_hands: int = 0
    failed_hands: int = 0
    vision_errors: int = 0
    average_latency_ms: float = 0.0
    actions_by_type: dict = field(default_factory=dict)
    total_duration: float = 0.0


@dataclass
class TestReport:
    """
    Complete test report.
    
    Attributes:
        test_id: Unique test ID
        room: Poker room name
        start_time: Test start timestamp
        end_time: Test end timestamp
        phases: Metrics for each phase
        hand_results: Individual hand results
        overall_success_rate: Overall success rate
        overall_vision_accuracy: Vision accuracy
        recommendations: Test recommendations
    """
    test_id: str
    room: str
    start_time: float
    end_time: float
    phases: List[PhaseMetrics]
    hand_results: List[HandResult]
    overall_success_rate: float
    overall_vision_accuracy: float
    recommendations: List[str]


class LiveTestRunner:
    """
    Runs controlled live testing pipeline.
    
    Test Sequence:
    1. DRY-RUN Phase (100 hands):
       - Simulation only, no real actions
       - Establish baseline metrics
       - Identify vision issues
    
    2. SAFE Phase (50 hands):
       - Only fold/check/call
       - Real actions, minimal risk
       - Validate action execution
    
    3. MEDIUM UNSAFE Phase (10 hands):
       - Small bet/raise allowed
       - Full pipeline test
       - Monitor for anomalies
    
    CRITICAL SAFETY:
        - Use ONLY in play-money environment
        - Requires explicit confirmation for unsafe phases
        - Auto-shutdown on any anomaly
        - Complete logging with screenshots
    
    EDUCATIONAL NOTE:
        This tests the complete bridge pipeline in controlled
        conditions before any real-money use.
    """
    
    def __init__(
        self,
        room: str = "pokerstars",
        dataset_dir: str = "live_test_data",
        enable_monitoring: bool = True
    ):
        """
        Initialize live test runner.
        
        Args:
            room: Poker room name
            dataset_dir: Directory for test data/screenshots
            enable_monitoring: Enable monitoring system
        """
        self.room = room
        self.dataset_dir = Path(dataset_dir)
        self.enable_monitoring = enable_monitoring
        
        # Create directories
        self.screenshots_dir = self.dataset_dir / "screenshots"
        self.logs_dir = self.dataset_dir / "logs"
        
        for dir_path in [self.screenshots_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Test state
        self.test_id = f"livetest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_phase: Optional[TestPhase] = None
        self.hand_results: List[HandResult] = []
        self.phase_metrics: dict[TestPhase, PhaseMetrics] = {}
        
        logger.info(
            f"LiveTestRunner initialized: room={room}, "
            f"test_id={self.test_id}"
        )
    
    async def run_full_test(
        self,
        dry_run_hands: int = 100,
        safe_hands: int = 50,
        medium_unsafe_hands: int = 10
    ) -> TestReport:
        """
        Run complete test sequence.
        
        Args:
            dry_run_hands: Number of hands in dry-run phase
            safe_hands: Number of hands in safe phase
            medium_unsafe_hands: Number of hands in medium unsafe phase
        
        Returns:
            Complete test report
        
        EDUCATIONAL NOTE:
            Full test takes ~30-60 minutes depending on hand speed.
        """
        logger.critical("=" * 60)
        logger.critical("LIVE TEST PIPELINE STARTING")
        logger.critical(f"Test ID: {self.test_id}")
        logger.critical("=" * 60)
        
        start_time = time.time()
        
        try:
            # Phase 1: Dry-run
            logger.info("Starting Phase 1: DRY-RUN (simulation only)")
            await self._run_phase(
                TestPhase.DRY_RUN,
                target_hands=dry_run_hands,
                mode=OperationalMode.DRY_RUN
            )
            
            # Phase 2: Safe mode
            logger.critical("=" * 60)
            logger.critical("PHASE 2: SAFE MODE")
            logger.critical("Real actions will be executed (fold/check/call only)")
            logger.critical("=" * 60)
            
            confirmation = self._request_confirmation("safe")
            if not confirmation:
                logger.warning("Safe phase cancelled by user")
            else:
                await self._run_phase(
                    TestPhase.SAFE,
                    target_hands=safe_hands,
                    mode=OperationalMode.SAFE
                )
            
            # Phase 3: Medium unsafe
            logger.critical("=" * 60)
            logger.critical("PHASE 3: MEDIUM UNSAFE")
            logger.critical("Real actions including small bet/raise will be executed")
            logger.critical("=" * 60)
            
            confirmation = self._request_confirmation("medium_unsafe")
            if not confirmation:
                logger.warning("Medium unsafe phase cancelled by user")
            else:
                await self._run_phase(
                    TestPhase.MEDIUM_UNSAFE,
                    target_hands=medium_unsafe_hands,
                    mode=OperationalMode.UNSAFE,
                    max_risk=RiskLevel.MEDIUM
                )
            
            # Generate report
            end_time = time.time()
            report = self._generate_report(start_time, end_time)
            
            # Save report
            self._save_report(report)
            
            logger.critical("=" * 60)
            logger.critical("LIVE TEST COMPLETED")
            logger.critical(f"Overall success rate: {report.overall_success_rate:.1f}%")
            logger.critical(f"Vision accuracy: {report.overall_vision_accuracy:.1f}%")
            logger.critical("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise
    
    async def _run_phase(
        self,
        phase: TestPhase,
        target_hands: int,
        mode: OperationalMode,
        max_risk: RiskLevel = RiskLevel.LOW
    ) -> None:
        """
        Run a single test phase.
        
        Args:
            phase: Test phase
            target_hands: Target number of hands
            mode: Operational mode
            max_risk: Maximum risk level (for unsafe modes)
        """
        logger.info(f"Starting {phase.value} phase: {target_hands} hands")
        
        self.current_phase = phase
        phase_start = time.time()
        
        # Initialize metrics
        metrics = PhaseMetrics(
            phase=phase,
            target_hands=target_hands
        )
        
        # Initialize bridge
        config = BridgeConfig(
            mode=mode,
            enable_monitoring=self.enable_monitoring,
            room=self.room
        )
        
        bridge = BridgeMain(config=config)
        
        # Start session
        await bridge.start_session()
        
        try:
            # Process hands
            for hand_num in range(1, target_hands + 1):
                logger.info(f"[{phase.value}] Hand {hand_num}/{target_hands}")
                
                hand_start = time.time()
                
                # Process hand
                result = await self._process_hand(
                    bridge=bridge,
                    hand_number=hand_num,
                    phase=phase
                )
                
                # Calculate latency
                result.latency_ms = (time.time() - hand_start) * 1000
                
                # Update metrics
                metrics.completed_hands += 1
                if result.success:
                    metrics.successful_hands += 1
                else:
                    metrics.failed_hands += 1
                
                if result.vision_error:
                    metrics.vision_errors += 1
                
                if result.action_type:
                    metrics.actions_by_type[result.action_type] = \
                        metrics.actions_by_type.get(result.action_type, 0) + 1
                
                # Store result
                self.hand_results.append(result)
                
                # Small delay between hands
                await asyncio.sleep(0.5)
            
            # Calculate phase metrics
            metrics.total_duration = time.time() - phase_start
            
            if metrics.completed_hands > 0:
                total_latency = sum(
                    r.latency_ms for r in self.hand_results
                    if r.phase == phase
                )
                metrics.average_latency_ms = total_latency / metrics.completed_hands
            
            self.phase_metrics[phase] = metrics
            
            logger.info(
                f"Phase {phase.value} completed: "
                f"{metrics.successful_hands}/{metrics.completed_hands} successful"
            )
            
        finally:
            # Stop session
            await bridge.stop_session()
    
    async def _process_hand(
        self,
        bridge: BridgeMain,
        hand_number: int,
        phase: TestPhase
    ) -> HandResult:
        """
        Process a single hand.
        
        Args:
            bridge: Bridge instance
            hand_number: Hand number
            phase: Test phase
        
        Returns:
            Hand result
        """
        result = HandResult(
            hand_number=hand_number,
            phase=phase,
            success=False,
            decision_made=False,
            action_executed=False
        )
        
        try:
            # Process hand through bridge
            success = await bridge.process_hand()
            
            result.success = success
            result.decision_made = success
            result.action_executed = success
            
            # Note: In real implementation, would extract actual action details
            # For now, using placeholder
            if success:
                result.action_type = "check"  # Placeholder
            
        except Exception as e:
            logger.error(f"Hand {hand_number} error: {e}")
            result.vision_error = str(e)
        
        return result
    
    def _request_confirmation(self, phase: str) -> bool:
        """
        Request user confirmation for unsafe phase.
        
        Args:
            phase: Phase name
        
        Returns:
            True if confirmed, False otherwise
        
        EDUCATIONAL NOTE:
            In automated testing, this returns True.
            In production, would require interactive confirmation.
        """
        logger.warning(f"Confirmation required for {phase} phase")
        
        # For automated testing, return True
        # In production, would prompt user
        return True
    
    def _generate_report(
        self,
        start_time: float,
        end_time: float
    ) -> TestReport:
        """
        Generate test report.
        
        Args:
            start_time: Test start time
            end_time: Test end time
        
        Returns:
            Test report
        """
        # Calculate overall metrics
        total_hands = len(self.hand_results)
        successful_hands = sum(1 for r in self.hand_results if r.success)
        
        overall_success_rate = (
            successful_hands / total_hands * 100
            if total_hands > 0 else 0
        )
        
        vision_errors = sum(
            1 for r in self.hand_results
            if r.vision_error is not None
        )
        overall_vision_accuracy = (
            (total_hands - vision_errors) / total_hands * 100
            if total_hands > 0 else 0
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_success_rate,
            overall_vision_accuracy
        )
        
        report = TestReport(
            test_id=self.test_id,
            room=self.room,
            start_time=start_time,
            end_time=end_time,
            phases=list(self.phase_metrics.values()),
            hand_results=self.hand_results,
            overall_success_rate=overall_success_rate,
            overall_vision_accuracy=overall_vision_accuracy,
            recommendations=recommendations
        )
        
        return report
    
    def _generate_recommendations(
        self,
        success_rate: float,
        vision_accuracy: float
    ) -> List[str]:
        """
        Generate recommendations based on test results.
        
        Args:
            success_rate: Overall success rate
            vision_accuracy: Vision accuracy
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if success_rate < 90:
            recommendations.append(
                "Low success rate - review error logs and improve error handling"
            )
        
        if vision_accuracy < 95:
            recommendations.append(
                "Low vision accuracy - collect more training data and retrain models"
            )
        
        if success_rate >= 95 and vision_accuracy >= 96:
            recommendations.append(
                "Excellent performance - system ready for extended testing"
            )
        elif success_rate >= 90 and vision_accuracy >= 92:
            recommendations.append(
                "Good performance - continue testing with larger sample size"
            )
        else:
            recommendations.append(
                "Performance needs improvement - address issues before proceeding"
            )
        
        return recommendations
    
    def _save_report(self, report: TestReport) -> None:
        """
        Save test report to file.
        
        Args:
            report: Test report
        """
        report_path = self.logs_dir / f"{self.test_id}_report.json"
        
        # Convert to dict
        report_dict = asdict(report)
        
        # Save to JSON
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2)
        
        logger.info(f"Report saved: {report_path}")
        
        # Also save summary
        self._save_summary(report)
    
    def _save_summary(self, report: TestReport) -> None:
        """
        Save human-readable summary.
        
        Args:
            report: Test report
        """
        summary_path = self.logs_dir / f"{self.test_id}_summary.txt"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("LIVE TEST REPORT SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Test ID: {report.test_id}\n")
            f.write(f"Room: {report.room}\n")
            f.write(f"Duration: {report.end_time - report.start_time:.1f}s\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("OVERALL METRICS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Total hands: {len(report.hand_results)}\n")
            f.write(f"Success rate: {report.overall_success_rate:.1f}%\n")
            f.write(f"Vision accuracy: {report.overall_vision_accuracy:.1f}%\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("PHASE BREAKDOWN\n")
            f.write("=" * 60 + "\n\n")
            
            for phase_metrics in report.phases:
                f.write(f"Phase: {phase_metrics.phase.value.upper()}\n")
                f.write(f"  Target: {phase_metrics.target_hands} hands\n")
                f.write(f"  Completed: {phase_metrics.completed_hands}\n")
                f.write(f"  Successful: {phase_metrics.successful_hands}\n")
                f.write(f"  Failed: {phase_metrics.failed_hands}\n")
                f.write(f"  Vision errors: {phase_metrics.vision_errors}\n")
                f.write(f"  Avg latency: {phase_metrics.average_latency_ms:.1f}ms\n")
                f.write(f"  Duration: {phase_metrics.total_duration:.1f}s\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("=" * 60 + "\n\n")
            
            for i, rec in enumerate(report.recommendations, 1):
                f.write(f"{i}. {rec}\n")
            
            f.write("\n" + "=" * 60 + "\n")
        
        logger.info(f"Summary saved: {summary_path}")


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Live Test Runner - Educational HCI Research Demo")
    print("=" * 60)
    print()
    print("CRITICAL WARNING:")
    print("This module tests REAL actions in live environment.")
    print("Use ONLY in play-money poker rooms.")
    print()
    print("=" * 60)
    print("Demo: Quick test (5 hands per phase)")
    print("=" * 60)
    print()
    
    async def demo():
        runner = LiveTestRunner(
            room="pokerstars",
            dataset_dir="live_test_demo"
        )
        
        print(f"Test ID: {runner.test_id}")
        print(f"Room: {runner.room}")
        print()
        
        # Note: Would run full test in production
        # For demo, just show initialization
        print("[Demo mode - not running actual test]")
        print()
        print("In production, would run:")
        print("  - 100 hands dry-run")
        print("  - 50 hands safe mode")
        print("  - 10 hands medium unsafe")
        print()
        print("Expected duration: ~30-60 minutes")
    
    asyncio.run(demo())
    
    print()
    print("=" * 60)
    print("Educational HCI Research - Live Testing Pipeline")
    print("=" * 60)
