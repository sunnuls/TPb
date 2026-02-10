"""
Capture Stability Test (Roadmap3 Phase 1 - Step 3).

Educational HCI Research: Tests screen capture stability by capturing
screenshots every 2 seconds and verifying consistency.

DRY-RUN MODE: Simulates captures without real window operations.

WARNING: This is a research prototype. Real-world use is PROHIBITED.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode, get_safety
from bridge.screen_capture import ScreenCapture
from bridge.roi_manager import ROIManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_capture_stability(
    interval_seconds: float = 2.0,
    num_captures: int = 10,
    save_screenshots: bool = True
) -> dict:
    """
    Test screen capture stability.
    
    Args:
        interval_seconds: Time between captures
        num_captures: Number of captures to perform
        save_screenshots: Save debug screenshots
        
    Returns:
        Dictionary with test results
        
    EDUCATIONAL NOTE:
        Phase 1 stability test: Verify consistent screen capture
        over time for HCI research applications.
    """
    logger.info("=" * 60)
    logger.info("PHASE 1 STABILITY TEST: Screen Capture")
    logger.info("=" * 60)
    logger.info(f"Mode: {'DRY-RUN' if get_safety().is_dry_run() else 'UNSAFE'}")
    logger.info(f"Interval: {interval_seconds}s")
    logger.info(f"Captures: {num_captures}")
    logger.info("=" * 60)
    
    # Initialize screen capture
    capture = ScreenCapture(
        window_title_pattern="PokerStars.*",
        save_screenshots=save_screenshots,
        screenshot_dir="bridge/debug_screenshots/stability_test"
    )
    
    # Find window
    logger.info("Step 1: Finding window...")
    window = capture.find_window()
    
    if window is None:
        logger.error("Window not found - test failed")
        return {'success': False, 'reason': 'window_not_found'}
    
    logger.info(f"  Window found: {window.title}")
    logger.info(f"  Resolution: {window.width}x{window.height}")
    logger.info(f"  Position: ({window.x}, {window.y})")
    
    # Run capture loop
    logger.info(f"\nStep 2: Running capture loop ({num_captures} captures)...")
    start_time = time.time()
    
    screenshots = capture.capture_loop(
        interval_seconds=interval_seconds,
        max_captures=num_captures
    )
    
    elapsed_time = time.time() - start_time
    
    # Analyze results
    logger.info(f"\nStep 3: Analyzing results...")
    logger.info(f"  Total time: {elapsed_time:.2f}s")
    logger.info(f"  Successful captures: {len(screenshots)}/{num_captures}")
    logger.info(f"  Success rate: {len(screenshots) / num_captures * 100:.1f}%")
    
    # Check stability (all captures should have same dimensions)
    if screenshots:
        shapes = [s.shape for s in screenshots]
        unique_shapes = set(shapes)
        
        logger.info(f"  Unique resolutions: {len(unique_shapes)}")
        logger.info(f"  Resolution stability: {'PASS' if len(unique_shapes) == 1 else 'FAIL'}")
        
        # Check for consistency
        if len(unique_shapes) == 1:
            logger.info(f"  Captured resolution: {shapes[0]}")
        
        # Calculate timing accuracy
        expected_time = (num_captures - 1) * interval_seconds
        timing_accuracy = (expected_time / elapsed_time) * 100 if elapsed_time > 0 else 0
        logger.info(f"  Timing accuracy: {timing_accuracy:.1f}%")
    
    # Get capture statistics
    stats = capture.get_statistics()
    logger.info(f"\nCapture Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Test results
    success = len(screenshots) == num_captures
    
    logger.info("\n" + "=" * 60)
    logger.info(f"STABILITY TEST: {'PASS' if success else 'FAIL'}")
    logger.info("=" * 60)
    
    return {
        'success': success,
        'captures': len(screenshots),
        'expected': num_captures,
        'elapsed_time': elapsed_time,
        'shapes': [s.shape for s in screenshots] if screenshots else [],
        'statistics': stats
    }


def test_roi_stability(
    room: str = "pokerstars_6max",
    resolution: str = "1920x1080"
) -> dict:
    """
    Test ROI loading stability.
    
    Args:
        room: Room configuration to test
        resolution: Resolution to test
        
    Returns:
        Dictionary with test results
    """
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1 STABILITY TEST: ROI Manager")
    logger.info("=" * 60)
    logger.info(f"Room: {room}")
    logger.info(f"Resolution: {resolution}")
    logger.info("=" * 60)
    
    # Initialize ROI manager
    manager = ROIManager()
    
    # List available
    logger.info("\nStep 1: Listing available configurations...")
    available_rooms = manager.list_available_rooms()
    logger.info(f"  Available rooms: {available_rooms}")
    
    # Load ROI set
    logger.info(f"\nStep 2: Loading ROI set...")
    success = manager.load_roi_set(room, resolution)
    
    if not success:
        logger.error("Failed to load ROI set")
        return {'success': False, 'reason': 'load_failed'}
    
    logger.info(f"  ROI set loaded successfully")
    
    # Get all ROIs
    logger.info(f"\nStep 3: Verifying ROIs...")
    all_rois = manager.get_all_rois()
    logger.info(f"  Total ROIs: {len(all_rois)}")
    
    # List each ROI
    for name, roi in all_rois.items():
        logger.info(f"    {name}: {roi.as_tuple()}")
    
    # Get statistics
    stats = manager.get_statistics()
    logger.info(f"\nROI Manager Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("\n" + "=" * 60)
    logger.info("ROI STABILITY TEST: PASS")
    logger.info("=" * 60)
    
    return {
        'success': True,
        'loaded_rois': len(all_rois),
        'room': room,
        'resolution': resolution,
        'statistics': stats
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("HCI RESEARCH - PHASE 1 STABILITY TEST")
    print("Educational Prototype - External Application Interface Study")
    print("=" * 70)
    print()
    
    # Initialize safety framework in dry-run mode
    SafetyFramework.get_instance(
        SafetyConfig(
            mode=SafetyMode.DRY_RUN,
            enable_kill_switch=True
        )
    )
    
    # Test 1: Screen capture stability
    print("\n[TEST 1] Screen Capture Stability Test")
    print("-" * 70)
    capture_result = test_capture_stability(
        interval_seconds=2.0,
        num_captures=5,  # Reduced for demo
        save_screenshots=True
    )
    
    # Test 2: ROI manager stability
    print("\n[TEST 2] ROI Manager Stability Test")
    print("-" * 70)
    roi_result = test_roi_stability(
        room="pokerstars_6max",
        resolution="1920x1080"
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("PHASE 1 STABILITY TEST SUMMARY")
    print("=" * 70)
    print(f"Screen Capture Test: {'PASS' if capture_result['success'] else 'FAIL'}")
    print(f"  Captures: {capture_result['captures']}/{capture_result['expected']}")
    print(f"  Time: {capture_result['elapsed_time']:.2f}s")
    print()
    print(f"ROI Manager Test: {'PASS' if roi_result['success'] else 'FAIL'}")
    print(f"  ROIs loaded: {roi_result['loaded_rois']}")
    print(f"  Room: {roi_result['room']}")
    print()
    print("=" * 70)
    print("Educational HCI Research - DRY-RUN mode active")
    print("All operations simulated - No real window access")
    print("=" * 70)
