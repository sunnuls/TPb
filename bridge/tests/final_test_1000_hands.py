"""
Final Test: 1000 Hands in Dry-Run Mode (Roadmap3 Phase 7).

Comprehensive test of bridge system with 1000 hands simulation.

Test Coverage:
- Full bridge pipeline
- Error handling and recovery
- Monitoring and anomaly detection
- Performance metrics
- Decision quality tracking

EDUCATIONAL USE ONLY: For HCI research prototype testing.
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from bridge.bridge_main import BridgeConfig, BridgeMain, OperationalMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class HandResult:
    """Result of a single hand."""
    hand_number: int
    success: bool
    decision_made: bool
    action_executed: bool
    error: str = ""
    processing_time: float = 0.0


@dataclass
class TestReport:
    """
    Final test report.
    
    Attributes:
        total_hands: Total hands attempted
        successful_hands: Successfully processed hands
        failed_hands: Failed hands
        decisions_made: Total decisions
        actions_executed: Total actions
        errors: Total errors
        anomalies: Total anomalies
        total_time: Total test duration
        average_hand_time: Average time per hand
        success_rate: Success rate percentage
        error_rate: Error rate percentage
    """
    total_hands: int
    successful_hands: int
    failed_hands: int
    decisions_made: int
    actions_executed: int
    errors: int
    anomalies: int
    total_time: float
    average_hand_time: float
    success_rate: float
    error_rate: float


async def run_1000_hands_test() -> TestReport:
    """
    Run 1000 hands test.
    
    Returns:
        Test report with results
    """
    logger.info("=" * 60)
    logger.info("Starting 1000 Hands Test - Dry-Run Mode")
    logger.info("=" * 60)
    
    # Configuration
    config = BridgeConfig(
        mode=OperationalMode.DRY_RUN,
        enable_monitoring=True,
        enable_hub_connection=False
    )
    
    # Initialize bridge
    bridge = BridgeMain(config=config)
    
    # Start session
    logger.info("Starting bridge session...")
    if not await bridge.start_session():
        logger.error("Failed to start session")
        sys.exit(1)
    
    # Test parameters
    total_hands = 1000
    results: List[HandResult] = []
    
    start_time = time.time()
    
    try:
        # Process hands
        for hand_num in range(1, total_hands + 1):
            hand_start = time.time()
            
            # Progress logging
            if hand_num % 100 == 0:
                logger.info(f"Processing hand {hand_num}/{total_hands}...")
            
            # Process hand
            try:
                success = await bridge.process_hand()
                
                result = HandResult(
                    hand_number=hand_num,
                    success=success,
                    decision_made=True,
                    action_executed=success,
                    processing_time=time.time() - hand_start
                )
                
            except Exception as e:
                logger.error(f"Hand {hand_num} error: {e}")
                result = HandResult(
                    hand_number=hand_num,
                    success=False,
                    decision_made=False,
                    action_executed=False,
                    error=str(e),
                    processing_time=time.time() - hand_start
                )
            
            results.append(result)
            
            # Small delay to simulate realistic timing
            await asyncio.sleep(0.01)
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Get final statistics
        stats = bridge.get_statistics()
        
        # Calculate metrics
        successful_hands = sum(1 for r in results if r.success)
        failed_hands = sum(1 for r in results if not r.success)
        average_hand_time = total_time / total_hands if total_hands > 0 else 0
        success_rate = (successful_hands / total_hands * 100) if total_hands > 0 else 0
        error_rate = (failed_hands / total_hands * 100) if total_hands > 0 else 0
        
        # Create report
        report = TestReport(
            total_hands=total_hands,
            successful_hands=successful_hands,
            failed_hands=failed_hands,
            decisions_made=stats['decisions_made'],
            actions_executed=stats['actions_executed'],
            errors=stats['errors_encountered'],
            anomalies=stats.get('anomalies_detected', 0),
            total_time=total_time,
            average_hand_time=average_hand_time,
            success_rate=success_rate,
            error_rate=error_rate
        )
        
        return report
        
    finally:
        # Stop session
        logger.info("Stopping bridge session...")
        await bridge.stop_session()


def print_report(report: TestReport) -> None:
    """
    Print test report.
    
    Args:
        report: Test report to print
    """
    print("\n" + "=" * 60)
    print("1000 HANDS TEST REPORT")
    print("=" * 60)
    print()
    
    print("Test Configuration:")
    print("  Mode: DRY-RUN")
    print("  Total hands: 1000")
    print()
    
    print("Results:")
    print(f"  Successful hands: {report.successful_hands}")
    print(f"  Failed hands: {report.failed_hands}")
    print(f"  Success rate: {report.success_rate:.1f}%")
    print(f"  Error rate: {report.error_rate:.1f}%")
    print()
    
    print("Operations:")
    print(f"  Decisions made: {report.decisions_made}")
    print(f"  Actions executed: {report.actions_executed}")
    print(f"  Errors encountered: {report.errors}")
    print(f"  Anomalies detected: {report.anomalies}")
    print()
    
    print("Performance:")
    print(f"  Total time: {report.total_time:.2f}s")
    print(f"  Average hand time: {report.average_hand_time:.4f}s")
    print(f"  Hands per second: {1/report.average_hand_time:.2f}")
    print()
    
    print("=" * 60)
    
    # Pass/Fail assessment
    if report.success_rate >= 95.0 and report.error_rate < 5.0:
        print("TEST STATUS: PASS")
        print("System performed within acceptable parameters.")
    elif report.success_rate >= 80.0:
        print("TEST STATUS: WARNING")
        print("System functional but with elevated error rate.")
    else:
        print("TEST STATUS: FAIL")
        print("System has high failure rate - requires investigation.")
    
    print("=" * 60)


def save_report(report: TestReport) -> str:
    """
    Save report to file.
    
    Args:
        report: Test report to save
    
    Returns:
        Path to saved report
    """
    # Create reports directory
    reports_dir = Path("bridge/test_reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_report_1000hands_{timestamp}.json"
    filepath = reports_dir / filename
    
    # Convert report to dict
    report_dict = asdict(report)
    report_dict['timestamp'] = timestamp
    report_dict['test_type'] = "1000_hands_dry_run"
    
    # Save to JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2)
    
    logger.info(f"Report saved to: {filepath}")
    return str(filepath)


async def main() -> None:
    """Main entry point."""
    try:
        # Run test
        report = await run_1000_hands_test()
        
        # Print report
        print_report(report)
        
        # Save report
        report_path = save_report(report)
        
        print(f"\nFull report saved to: {report_path}")
        
        # Exit code based on success rate
        if report.success_rate >= 95.0:
            sys.exit(0)
        elif report.success_rate >= 80.0:
            sys.exit(1)
        else:
            sys.exit(2)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Bridge Final Test - 1000 Hands (Dry-Run)")
    print("Educational HCI Research Prototype")
    print("=" * 60)
    print()
    print("This test will:")
    print("  - Process 1000 poker hands in dry-run mode")
    print("  - Test all bridge components")
    print("  - Track errors and anomalies")
    print("  - Generate performance metrics")
    print()
    print("Expected duration: ~30-60 seconds")
    print()
    
    input("Press Enter to start test...")
    print()
    
    asyncio.run(main())
