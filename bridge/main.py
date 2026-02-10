"""
Bridge Main Entry Point (HCI Research Prototype - Roadmap3).

Educational use only - for studying external desktop application interfaces.
All operations in DRY-RUN mode by default.

Usage:
    python -m bridge.main --bridge-mode --dry-run
    python -m bridge.main --bridge-mode --safe
    python -m bridge.main --bridge-mode --unsafe  # Requires explicit flag

Educational HCI Research Only - Real actions PROHIBITED without authorization.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='HCI Research Bridge - External Application Interface Study',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Educational Use Only:
  This is a Human-Computer Interaction research prototype for studying
  external desktop application interfaces. All operations are in DRY-RUN
  mode by default. Real actions require explicit --unsafe flag.

Safety Modes:
  --dry-run    Log only, no real actions (DEFAULT)
  --safe       Conservative: fold/check/call only
  --unsafe     Full access: all actions (REQUIRES EXPLICIT FLAG)

Examples:
  python -m bridge.main --bridge-mode --dry-run
  python -m bridge.main --bridge-mode --safe
  python -m bridge.main --bridge-mode --unsafe  # Use with caution

Educational HCI Research - Real-world use PROHIBITED without authorization.
        """
    )
    
    # Bridge mode flag
    parser.add_argument(
        '--bridge-mode',
        action='store_true',
        help='Enable bridge mode (HCI research prototype)'
    )
    
    # Safety mode (mutually exclusive)
    safety_group = parser.add_mutually_exclusive_group()
    safety_group.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Dry-run mode: log only, no real actions (DEFAULT)'
    )
    safety_group.add_argument(
        '--safe',
        action='store_true',
        help='Safe mode: conservative actions only (fold/check/call)'
    )
    safety_group.add_argument(
        '--unsafe',
        action='store_true',
        help='Unsafe mode: all actions allowed (REQUIRES EXPLICIT FLAG)'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        default='bridge/config/live_config.yaml',
        help='Path to configuration file'
    )
    
    # Runtime limits
    parser.add_argument(
        '--max-runtime',
        type=int,
        default=3600,
        help='Maximum runtime in seconds (default: 3600 = 1 hour)'
    )
    
    # Logging
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    # Debug options
    parser.add_argument(
        '--save-screenshots',
        action='store_true',
        help='Save debug screenshots'
    )
    
    args = parser.parse_args()
    
    # Validate bridge mode is enabled
    if not args.bridge_mode:
        parser.error("Bridge mode not enabled. Use --bridge-mode flag.")
    
    return args


def determine_safety_mode(args: argparse.Namespace) -> SafetyMode:
    """
    Determine safety mode from arguments.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Safety mode
    """
    if args.unsafe:
        logger.warning("=" * 60)
        logger.warning("UNSAFE MODE ENABLED")
        logger.warning("Real actions are ALLOWED")
        logger.warning("Educational HCI Research - Use with extreme caution")
        logger.warning("=" * 60)
        return SafetyMode.UNSAFE
    elif args.safe:
        logger.info("SAFE MODE: Conservative actions only (fold/check/call)")
        return SafetyMode.SAFE
    else:
        logger.info("DRY-RUN MODE: Log only, no real actions")
        return SafetyMode.DRY_RUN


def main() -> int:
    """
    Main entry point for bridge mode.
    
    Returns:
        Exit code
    """
    # Parse arguments
    args = parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Determine safety mode
    safety_mode = determine_safety_mode(args)
    
    # Initialize safety framework
    safety_config = SafetyConfig(
        mode=safety_mode,
        max_runtime_seconds=args.max_runtime,
        enable_kill_switch=True,
        log_all_decisions=True,
        screenshot_on_action=args.save_screenshots
    )
    
    safety = SafetyFramework.get_instance(safety_config)
    
    # Display banner
    print()
    print("=" * 70)
    print("HCI RESEARCH BRIDGE - External Application Interface Study")
    print("=" * 70)
    print(f"Mode: {safety_mode.value.upper()}")
    print(f"Config: {args.config}")
    print(f"Max Runtime: {args.max_runtime}s")
    print(f"Educational Prototype - Phase 0: Safety Framework Active")
    print("=" * 70)
    print()
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return 1
    
    logger.info(f"Configuration loaded from {config_path}")
    
    # Phase 0 demo: Safety framework active
    logger.info("Phase 0: Safety Framework initialized")
    logger.info(f"Kill switch (Ctrl+C): {'ENABLED' if safety.config.enable_kill_switch else 'DISABLED'}")
    logger.info(f"Decision logging: {'ENABLED' if safety.config.log_all_decisions else 'DISABLED'}")
    
    # Demo: Log a test decision
    safety.log_decision({
        'phase': 0,
        'action': 'initialization',
        'status': 'complete'
    })
    
    logger.info(f"Runtime: {safety.get_runtime():.2f}s")
    logger.info(f"Decisions logged: {safety.get_decision_count()}")
    
    print()
    print("=" * 70)
    print("Phase 0 Complete: Safety Framework Active")
    print("Next: Implement Phase 1 (Screen Capture & ROI System)")
    print("=" * 70)
    print()
    print("Educational HCI Research - All operations in DRY-RUN mode by default")
    print("Real actions require explicit --unsafe flag")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
