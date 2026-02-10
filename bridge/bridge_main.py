"""
Bridge Main Module (Roadmap3 Phase 7).

Integrates all bridge components and provides operational modes.

Operational Modes:
1. --dry-run (default): Full simulation, no real actions
2. --safe: Conservative mode (only fold/check/call allowed)
3. --unsafe: Full mode (all actions including raise/bet)

EDUCATIONAL USE ONLY: For HCI research prototype.
Real poker operations strictly prohibited without explicit --unsafe flag.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from bridge.action_simulator import ActionSimulator
from bridge.action_translator import ActionTranslator
from bridge.bot_identification import BotIdentityManager
from bridge.external_hub_client import ExternalHubClient
from bridge.humanization_sim import HumanizationSimulator
from bridge.lobby_scanner import LobbyScanner
from bridge.monitoring import MonitoringSystem
from bridge.opportunity_detector import OpportunityDetector
from bridge.safety import SafetyConfig, SafetyFramework
from bridge.state_bridge import StateBridge

logger = logging.getLogger(__name__)


class OperationalMode(str, Enum):
    """Bridge operational modes."""
    DRY_RUN = "dry-run"
    SAFE = "safe"
    UNSAFE = "unsafe"


@dataclass
class BridgeConfig:
    """
    Bridge configuration.
    
    Attributes:
        mode: Operational mode
        enable_monitoring: Enable monitoring system
        enable_hub_connection: Enable external hub connection
        table_id: Target table ID
        room: Poker room name
        resolution: Screen resolution
        bot_id: Bot identifier
        shared_secret: Shared secret for HIVE coordination
    """
    mode: OperationalMode = OperationalMode.DRY_RUN
    enable_monitoring: bool = True
    enable_hub_connection: bool = False
    table_id: str = "table_001"
    room: str = "pokerstars"
    resolution: str = "1920x1080"
    bot_id: str = "bot_001"
    shared_secret: str = ""


@dataclass
class BridgeStatistics:
    """
    Bridge session statistics.
    
    Attributes:
        hands_played: Total hands played
        decisions_made: Total decisions made
        actions_executed: Total actions executed
        errors_encountered: Total errors
        anomalies_detected: Total anomalies
        session_duration: Session duration in seconds
        average_decision_time: Average decision time in seconds
    """
    hands_played: int = 0
    decisions_made: int = 0
    actions_executed: int = 0
    errors_encountered: int = 0
    anomalies_detected: int = 0
    session_duration: float = 0.0
    average_decision_time: float = 0.0


class BridgeMain:
    """
    Main bridge orchestrator.
    
    Integrates all bridge components:
    - State extraction (StateBridge)
    - Lobby scanning (LobbyScanner)
    - Opportunity detection (OpportunityDetector)
    - Bot identification (BotIdentityManager)
    - Hub connection (ExternalHubClient)
    - Action translation (ActionTranslator)
    - Action execution (ActionSimulator)
    - Humanization (HumanizationSimulator)
    - Monitoring (MonitoringSystem)
    - Safety (SafetyFramework)
    
    EDUCATIONAL NOTE:
        This orchestrates the complete bridge pipeline from
        screen capture to action execution (simulated).
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        """
        Initialize bridge main.
        
        Args:
            config: Bridge configuration
        """
        self.config = config or BridgeConfig()
        
        # Setup safety framework based on mode
        from bridge.safety import SafetyMode
        
        safety_config = SafetyConfig()
        if self.config.mode == OperationalMode.UNSAFE:
            safety_config.mode = SafetyMode.UNSAFE
        elif self.config.mode == OperationalMode.SAFE:
            safety_config.mode = SafetyMode.SAFE
        else:
            safety_config.mode = SafetyMode.DRY_RUN
        
        self.safety = SafetyFramework(config=safety_config)
        
        # Initialize components
        dry_run = (self.config.mode != OperationalMode.UNSAFE)
        
        self.state_bridge = StateBridge(dry_run=dry_run)
        self.lobby_scanner = LobbyScanner(dry_run=dry_run)
        self.opportunity_detector = OpportunityDetector(
            lobby_scanner=self.lobby_scanner
        )
        self.bot_identity = BotIdentityManager(
            bot_id=self.config.bot_id,
            shared_secret=self.config.shared_secret
        )
        
        self.action_translator = ActionTranslator()
        self.action_simulator = ActionSimulator()
        self.humanization = HumanizationSimulator()
        
        # Monitoring system (if enabled)
        self.monitoring: Optional[MonitoringSystem] = None
        if self.config.enable_monitoring:
            self.monitoring = MonitoringSystem(safety=self.safety)
        
        # Hub client (if enabled)
        self.hub_client: Optional[ExternalHubClient] = None
        if self.config.enable_hub_connection:
            self.hub_client = ExternalHubClient(
                bot_identity=self.bot_identity,
                safety=self.safety
            )
        
        # Session state
        self.session_active = False
        self.session_start_time = 0.0
        self.statistics = BridgeStatistics()
        
        logger.info(
            f"BridgeMain initialized: mode={self.config.mode.value}, "
            f"monitoring={self.config.enable_monitoring}, "
            f"hub_connection={self.config.enable_hub_connection}"
        )
    
    async def start_session(self) -> bool:
        """
        Start bridge session.
        
        Returns:
            True if session started successfully
        
        EDUCATIONAL NOTE:
            Initializes all components and begins monitoring.
        """
        if self.session_active:
            logger.warning("Session already active")
            return False
        
        logger.info(f"Starting bridge session in {self.config.mode.value} mode")
        
        # Safety check
        if self.config.mode == OperationalMode.UNSAFE:
            logger.critical("=" * 60)
            logger.critical("UNSAFE MODE ENABLED")
            logger.critical("Real actions WILL be executed")
            logger.critical("=" * 60)
            
            # Require explicit confirmation (in real implementation)
            # For now, just log the warning
        
        # Connect to hub if enabled
        if self.hub_client:
            connected = await self.hub_client.connect(
                environment_id="bridge_session"
            )
            if not connected:
                logger.error("Failed to connect to hub")
                return False
        
        # Mark session as active
        self.session_active = True
        self.session_start_time = time.time()
        
        logger.info("Bridge session started")
        return True
    
    async def stop_session(self) -> None:
        """
        Stop bridge session.
        
        EDUCATIONAL NOTE:
            Cleanly shuts down all components and saves logs.
        """
        if not self.session_active:
            logger.warning("No active session to stop")
            return
        
        logger.info("Stopping bridge session")
        
        # Disconnect from hub if connected
        if self.hub_client:
            await self.hub_client.disconnect()
        
        # Update statistics
        self.statistics.session_duration = time.time() - self.session_start_time
        
        # Mark session as inactive
        self.session_active = False
        
        logger.info("Bridge session stopped")
    
    async def process_hand(self) -> bool:
        """
        Process a single poker hand.
        
        Returns:
            True if hand processed successfully
        
        EDUCATIONAL NOTE:
            Complete pipeline:
            1. Extract state
            2. Check monitoring
            3. Make decision
            4. Translate to action
            5. Execute (simulate)
        """
        if not self.session_active:
            logger.error("No active session")
            return False
        
        try:
            # Step 1: Extract table state
            table_state = self.state_bridge.get_live_table_state(
                table_id=self.config.table_id,
                room=self.config.room,
                resolution=self.config.resolution
            )
            
            if not table_state:
                logger.error("Failed to extract table state")
                self.statistics.errors_encountered += 1
                if self.monitoring:
                    self.monitoring.record_error("State extraction failed")
                return False
            
            # Step 2: Monitoring checks
            if self.monitoring:
                # Check UI changes
                ui_alert = self.monitoring.check_ui_changes(screenshot=None)
                if ui_alert:
                    logger.warning(f"UI change detected: {ui_alert.message}")
                
                # Check state validity
                state_dict = {
                    'pot': table_state.pot,
                    'hero_stack': table_state.get_player_stack('hero'),
                    'hero_cards': table_state.get_hero_cards(),
                    'board': table_state.board
                }
                state_alert = self.monitoring.detect_invalid_state(state_dict)
                if state_alert:
                    logger.error(f"Invalid state: {state_alert.message}")
                    return False
                
                # Record success (resets error counter)
                self.monitoring.record_success()
            
            # Step 3: Make decision (placeholder - would use decision engine)
            # For now, simulate a simple decision
            decision = self._make_decision(table_state)
            self.statistics.decisions_made += 1
            
            # Step 4: Translate decision to action
            from bridge.action_translator import ActionContext
            
            context = ActionContext(
                pot_size=table_state.pot,
                bb_size=1.0,  # Placeholder
                legal_actions=['fold', 'check', 'call', 'raise'],
                stack_size=table_state.get_player_stack('hero')
            )
            
            # Apply mode restrictions
            decision = self._apply_mode_restrictions(decision)
            
            command = self.action_translator.translate(
                decision=decision,
                context=context
            )
            
            # Step 5: Execute action (simulated)
            log = self.action_simulator.simulate(
                command=command,
                capture_screenshot=True
            )
            
            if log.result.name.startswith('WOULD'):
                self.statistics.actions_executed += 1
            else:
                self.statistics.errors_encountered += 1
            
            # Log decision if monitoring enabled
            if self.monitoring:
                self.monitoring.log_decision(
                    decision=decision,
                    screenshot=None
                )
            
            # Update hand count
            self.statistics.hands_played += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Hand processing error: {e}", exc_info=True)
            self.statistics.errors_encountered += 1
            
            if self.monitoring:
                self.monitoring.record_error(str(e))
            
            return False
    
    def _make_decision(self, table_state) -> dict:
        """
        Make poker decision (placeholder).
        
        Args:
            table_state: Current table state
        
        Returns:
            Decision dict
        
        EDUCATIONAL NOTE:
            Real implementation would use collective decision engine.
            This is a simplified placeholder.
        """
        # Simple placeholder decision
        return {
            'action': 'check',
            'amount': 0.0,
            'reasoning': 'Placeholder decision'
        }
    
    def _apply_mode_restrictions(self, decision: dict) -> dict:
        """
        Apply operational mode restrictions to decision.
        
        Args:
            decision: Original decision
        
        Returns:
            Restricted decision if needed
        
        EDUCATIONAL NOTE:
            In SAFE mode, only fold/check/call allowed.
            Raise/bet are blocked.
        """
        if self.config.mode == OperationalMode.SAFE:
            # Restrict to safe actions only
            if decision['action'] in ['raise', 'bet']:
                logger.warning(
                    f"SAFE MODE: Blocking {decision['action']}, "
                    f"falling back to call"
                )
                decision = {
                    'action': 'call',
                    'amount': 0.0,
                    'reasoning': 'SAFE mode restriction'
                }
        
        return decision
    
    def get_statistics(self) -> dict:
        """Get session statistics."""
        stats = {
            'mode': self.config.mode.value,
            'hands_played': self.statistics.hands_played,
            'decisions_made': self.statistics.decisions_made,
            'actions_executed': self.statistics.actions_executed,
            'errors_encountered': self.statistics.errors_encountered,
            'session_duration': self.statistics.session_duration,
            'session_active': self.session_active
        }
        
        # Add monitoring statistics if available
        if self.monitoring:
            monitoring_stats = self.monitoring.get_statistics()
            stats['anomalies_detected'] = monitoring_stats['anomalies_detected']
            stats['monitoring_active'] = monitoring_stats['monitoring_active']
        
        # Add state bridge statistics (if available)
        try:
            state_stats = self.state_bridge.get_statistics()
            stats['extractions_count'] = state_stats.get('extractions_count', 0)
            stats['last_extraction_time'] = state_stats.get('last_extraction_time', 0.0)
        except Exception:
            stats['extractions_count'] = 0
            stats['last_extraction_time'] = 0.0
        
        # Add action statistics (if available)
        try:
            action_stats = self.action_simulator.get_statistics()
            stats['actions_simulated'] = action_stats.get('actions_simulated', 0)
        except Exception:
            stats['actions_simulated'] = 0
        
        return stats


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bridge Mode - Educational HCI Research Prototype"
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['dry-run', 'safe', 'unsafe'],
        default='dry-run',
        help='Operational mode (default: dry-run)'
    )
    
    parser.add_argument(
        '--table-id',
        type=str,
        default='table_001',
        help='Target table ID'
    )
    
    parser.add_argument(
        '--room',
        type=str,
        default='pokerstars',
        help='Poker room name'
    )
    
    parser.add_argument(
        '--hands',
        type=int,
        default=1,
        help='Number of hands to process'
    )
    
    parser.add_argument(
        '--enable-hub',
        action='store_true',
        help='Enable external hub connection'
    )
    
    parser.add_argument(
        '--bot-id',
        type=str,
        default='bot_001',
        help='Bot identifier'
    )
    
    parser.add_argument(
        '--no-monitoring',
        action='store_true',
        help='Disable monitoring system'
    )
    
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    """
    Main async entry point.
    
    Args:
        args: Command line arguments
    """
    # Create configuration
    config = BridgeConfig(
        mode=OperationalMode(args.mode),
        enable_monitoring=not args.no_monitoring,
        enable_hub_connection=args.enable_hub,
        table_id=args.table_id,
        room=args.room,
        bot_id=args.bot_id
    )
    
    # Initialize bridge
    bridge = BridgeMain(config=config)
    
    # Start session
    if not await bridge.start_session():
        logger.error("Failed to start session")
        sys.exit(1)
    
    try:
        # Process hands
        for hand_num in range(1, args.hands + 1):
            logger.info(f"Processing hand {hand_num}/{args.hands}")
            
            success = await bridge.process_hand()
            
            if not success:
                logger.warning(f"Hand {hand_num} processing failed")
            
            # Small delay between hands (in dry-run)
            await asyncio.sleep(0.1)
        
        # Print statistics
        stats = bridge.get_statistics()
        
        print("\n" + "=" * 60)
        print("Bridge Session Statistics")
        print("=" * 60)
        print(f"Mode: {stats['mode']}")
        print(f"Hands played: {stats['hands_played']}")
        print(f"Decisions made: {stats['decisions_made']}")
        print(f"Actions executed: {stats['actions_executed']}")
        print(f"Errors encountered: {stats['errors_encountered']}")
        
        if 'anomalies_detected' in stats:
            print(f"Anomalies detected: {stats['anomalies_detected']}")
        
        print(f"Session duration: {stats['session_duration']:.2f}s")
        print("=" * 60)
        
    finally:
        # Stop session
        await bridge.stop_session()


def main() -> None:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run async main
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
