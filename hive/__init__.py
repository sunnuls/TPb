"""
HIVE Coordination System - Educational Game Theory Research.

⚠️ CRITICAL ETHICAL WARNING:
    This module implements multi-agent coordination (collusion) for
    EDUCATIONAL and RESEARCH purposes ONLY.
    
    NEVER use in real games without explicit consent.
    Demonstrates game theory concepts in controlled environment.

Modules:
- bot_pool: Pool of coordinating agents (Phase 1)
- table_scanner: Automated table selection (Phase 1)
- auto_seating: Coordinated table joining (Phase 1)
- card_sharing: Card information sharing (Phase 2 - COLLUSION)
- collusion_activation: Collusion mode activation (Phase 2)
- manipulation_logic: 3vs1 manipulation strategies (Phase 3)
- realtime_coordinator: Real-time coordination with real actions (Phase 3)
"""

__all__ = [
    # Phase 1: Bot Pool & Scanning
    'BotPool',
    'HiveTeam',
    'TableScanner',
    'AutoSeating',
    
    # Phase 2: Card Sharing & Collusion
    'CardSharingSystem',
    'CollusionActivator',
    'CollusionMode',
    
    # Phase 3: Manipulation & Real-time Coordination
    'ManipulationEngine',
    'ManipulationStrategy',
    'RealtimeCoordinator'
]
