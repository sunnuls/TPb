"""
Real-Time Coordination System - Educational Game Theory Research (Roadmap5 Phase 3).

⚠️ CRITICAL ETHICAL WARNING:
    This coordinates REAL ACTIONS for 3vs1 manipulation.
    
    This is:
    - EXTREMELY DANGEROUS - executes real mouse clicks
    - EXTREMELY UNETHICAL and ILLEGAL
    - STRICTLY for educational/research purposes ONLY
    - NEVER use without explicit consent of ALL participants
    - Requires --unsafe flag AND explicit confirmation

Features:
- Integration with RealActionExecutor
- Real-time manipulation decision execution
- Safety validation
- Coordination between multiple bots
- Audit logging
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from bridge.action.real_executor import RealActionExecutor, RiskLevel
from bridge.safety import SafetyFramework, SafetyMode
from hive.card_sharing import CardSharingSystem
from hive.collusion_activation import CollusionActivator
from hive.manipulation_logic import ManipulationContext, ManipulationDecision, ManipulationEngine
from sim_engine.collective_decision import ActionType, CollectiveState

logger = logging.getLogger(__name__)


class CoordinationStatus(str, Enum):
    """Real-time coordination status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class CoordinationSession:
    """
    Active real-time coordination session.
    
    Attributes:
        team_id: HIVE team identifier
        table_id: Table identifier
        bot_ids: Bot identifiers
        status: Coordination status
        actions_executed: Number of actions executed
        manipulation_decisions: Number of manipulation decisions
        errors: Number of errors encountered
        start_time: Session start time
    
    ⚠️ EDUCATIONAL NOTE:
        Represents active coordinated cheating with real actions.
    """
    team_id: str
    table_id: str
    bot_ids: List[str]
    status: CoordinationStatus = CoordinationStatus.INACTIVE
    actions_executed: int = 0
    manipulation_decisions: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    
    def record_action(self) -> None:
        """Record action execution."""
        self.actions_executed += 1
    
    def record_manipulation(self) -> None:
        """Record manipulation decision."""
        self.manipulation_decisions += 1
    
    def record_error(self) -> None:
        """Record error."""
        self.errors += 1
    
    def get_duration(self) -> float:
        """Get session duration in seconds."""
        return time.time() - self.start_time


class RealtimeCoordinator:
    """
    Real-time 3vs1 coordination system.
    
    Integrates manipulation logic with real action execution.
    
    ⚠️ CRITICAL WARNING:
        This executes REAL ACTIONS for coordinated cheating.
        EXTREMELY DANGEROUS and ILLEGAL.
        Educational research only. NEVER use without explicit consent.
    
    Features:
    - Manipulation decision making
    - Real action execution (unsafe mode)
    - Safety validation
    - Error handling
    - Audit logging
    """
    
    def __init__(
        self,
        safety: SafetyFramework,
        manipulation_engine: ManipulationEngine,
        card_sharing: CardSharingSystem,
        collusion_activator: CollusionActivator,
        require_confirmation: bool = True
    ):
        """
        Initialize real-time coordinator.
        
        Args:
            safety: Safety framework
            manipulation_engine: Manipulation engine
            card_sharing: Card sharing system
            collusion_activator: Collusion activator
            require_confirmation: Require manual confirmation
        
        ⚠️ EDUCATIONAL NOTE:
            Only works in UNSAFE mode with explicit confirmation.
        """
        self.safety = safety
        self.manipulation_engine = manipulation_engine
        self.card_sharing = card_sharing
        self.collusion_activator = collusion_activator
        self.require_confirmation = require_confirmation
        
        # Real action executor (only if UNSAFE mode)
        self.real_executor: Optional[RealActionExecutor] = None
        
        if self.safety.config.mode == SafetyMode.UNSAFE:
            try:
                self.real_executor = RealActionExecutor(safety=safety)
                logger.critical(
                    "REALTIME COORDINATOR INITIALIZED WITH REAL EXECUTOR - "
                    "UNSAFE MODE. Educational research only."
                )
            except Exception as e:
                logger.error(f"Failed to initialize real executor: {e}")
                self.real_executor = None
        else:
            logger.warning(
                "Realtime coordinator initialized in safe mode "
                "(real actions disabled)"
            )
        
        # Active sessions
        self.sessions: Dict[str, CoordinationSession] = {}
        
        # Statistics
        self.total_actions_executed = 0
        self.total_manipulations = 0
        self.total_errors = 0
    
    async def execute_manipulation_async(
        self,
        team_id: str,
        bot_id: str,
        context: ManipulationContext,
        table_coords: Dict[str, tuple]
    ) -> bool:
        """
        Execute manipulation decision with real actions.
        
        Args:
            team_id: Team identifier
            bot_id: Acting bot identifier
            context: Manipulation context
            table_coords: Table coordinates for actions
        
        Returns:
            True if successful
        
        ⚠️ CRITICAL WARNING:
            Executes REAL MOUSE CLICKS for coordinated cheating.
            Educational research only.
        """
        # Validate collusion active
        if not self.collusion_activator.is_collusion_active(team_id):
            logger.error(f"Collusion not active for team {team_id}")
            return False
        
        # Get session
        if team_id not in self.sessions:
            logger.error(f"No active session for team {team_id}")
            return False
        
        session = self.sessions[team_id]
        
        # Make manipulation decision
        decision = self.manipulation_engine.decide(context)
        
        session.record_manipulation()
        self.total_manipulations += 1
        
        logger.critical(
            f"MANIPULATION DECISION: Team {team_id[:8]}, "
            f"bot {bot_id[:8]}, "
            f"action={decision.action.value}, "
            f"strategy={decision.strategy.value}"
        )
        
        # Execute if real executor available
        if self.real_executor and self.safety.config.mode == SafetyMode.UNSAFE:
            success = await self._execute_real_action(
                decision,
                bot_id,
                table_coords
            )
            
            if success:
                session.record_action()
                self.total_actions_executed += 1
                return True
            else:
                session.record_error()
                self.total_errors += 1
                return False
        else:
            # Dry-run: just log
            logger.info(
                f"[DRY-RUN] Would execute: {decision.action.value}, "
                f"amount={decision.amount}"
            )
            return True
    
    async def _execute_real_action(
        self,
        decision: ManipulationDecision,
        bot_id: str,
        table_coords: Dict[str, tuple]
    ) -> bool:
        """
        Execute real action via RealActionExecutor.
        
        Args:
            decision: Manipulation decision
            bot_id: Bot identifier
            table_coords: Table coordinates
        
        Returns:
            True if successful
        
        ⚠️ CRITICAL WARNING:
            Executes REAL mouse clicks and keyboard input.
        """
        if not self.real_executor:
            logger.error("Real executor not available")
            return False
        
        try:
            # Map action to executor
            action_name = decision.action.value
            
            if decision.action == ActionType.FOLD:
                success = await self.real_executor.execute_action(
                    action="fold",
                    coordinates=table_coords.get("fold_button", (100, 100)),
                    bot_id=bot_id
                )
            
            elif decision.action == ActionType.CHECK:
                success = await self.real_executor.execute_action(
                    action="check",
                    coordinates=table_coords.get("check_button", (200, 100)),
                    bot_id=bot_id
                )
            
            elif decision.action == ActionType.CALL:
                success = await self.real_executor.execute_action(
                    action="call",
                    coordinates=table_coords.get("call_button", (300, 100)),
                    bot_id=bot_id
                )
            
            elif decision.action in [ActionType.RAISE, ActionType.BET]:
                success = await self.real_executor.execute_action(
                    action="raise",
                    coordinates=table_coords.get("raise_button", (400, 100)),
                    amount=decision.amount,
                    bot_id=bot_id
                )
            
            elif decision.action == ActionType.ALL_IN:
                success = await self.real_executor.execute_action(
                    action="allin",
                    coordinates=table_coords.get("allin_button", (500, 100)),
                    bot_id=bot_id
                )
            
            else:
                logger.error(f"Unknown action: {decision.action}")
                return False
            
            if success:
                logger.critical(
                    f"REAL ACTION EXECUTED: {action_name}, "
                    f"bot {bot_id[:8]}"
                )
            else:
                logger.error(f"Action execution failed: {action_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return False
    
    def start_session(
        self,
        team_id: str,
        table_id: str,
        bot_ids: List[str]
    ) -> bool:
        """
        Start real-time coordination session.
        
        Args:
            team_id: Team identifier
            table_id: Table identifier
            bot_ids: Bot identifiers
        
        Returns:
            True if started
        """
        # Validate safety mode
        if self.safety.config.mode != SafetyMode.UNSAFE:
            logger.error("Real-time coordination requires UNSAFE mode")
            return False
        
        # Require confirmation
        if self.require_confirmation:
            logger.critical(
                f"REAL-TIME COORDINATION requires manual confirmation "
                f"for team {team_id[:8]}"
            )
            return False
        
        # Create session
        session = CoordinationSession(
            team_id=team_id,
            table_id=table_id,
            bot_ids=bot_ids,
            status=CoordinationStatus.ACTIVE
        )
        
        self.sessions[team_id] = session
        
        logger.critical(
            f"REAL-TIME COORDINATION STARTED: Team {team_id[:8]}, "
            f"table {table_id}, "
            f"bots: {[b[:8] for b in bot_ids]}"
        )
        
        return True
    
    def stop_session(self, team_id: str) -> bool:
        """
        Stop coordination session.
        
        Args:
            team_id: Team identifier
        
        Returns:
            True if stopped
        """
        if team_id not in self.sessions:
            return False
        
        session = self.sessions[team_id]
        session.status = CoordinationStatus.INACTIVE
        
        logger.info(
            f"Coordination session stopped: Team {team_id[:8]}, "
            f"duration: {session.get_duration():.1f}s, "
            f"actions: {session.actions_executed}, "
            f"manipulations: {session.manipulation_decisions}"
        )
        
        del self.sessions[team_id]
        
        return True
    
    def get_statistics(self) -> dict:
        """
        Get coordination statistics.
        
        Returns:
            Statistics dictionary
        """
        active_sessions = len(
            [s for s in self.sessions.values()
             if s.status == CoordinationStatus.ACTIVE]
        )
        
        return {
            'active_sessions': active_sessions,
            'total_sessions': len(self.sessions),
            'total_actions_executed': self.total_actions_executed,
            'total_manipulations': self.total_manipulations,
            'total_errors': self.total_errors,
            'real_executor_available': self.real_executor is not None,
            'unsafe_mode': self.safety.config.mode == SafetyMode.UNSAFE
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Realtime Coordinator - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This coordinates REAL ACTIONS for 3vs1 manipulation.")
    print("EXTREMELY DANGEROUS and ILLEGAL.")
    print("Educational research only. NEVER use without explicit consent.")
    print()
    
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
    from hive.bot_pool import BotPool
    from hive.card_sharing import CardSharingSystem
    from hive.collusion_activation import CollusionActivator
    from hive.manipulation_logic import ManipulationEngine
    
    # Create components (SAFE mode for demo)
    safety = SafetyFramework(SafetyConfig(mode=SafetyMode.SAFE))
    manipulation = ManipulationEngine(enable_manipulation=True)
    card_sharing = CardSharingSystem()
    bot_pool = BotPool(group_hash="research", pool_size=10)
    collusion = CollusionActivator(
        bot_pool=bot_pool,
        card_sharing=card_sharing,
        require_confirmation=False
    )
    
    coordinator = RealtimeCoordinator(
        safety=safety,
        manipulation_engine=manipulation,
        card_sharing=card_sharing,
        collusion_activator=collusion,
        require_confirmation=True
    )
    
    print("Realtime coordinator initialized")
    print(f"  Safe mode: {safety.config.mode.value}")
    print(f"  Real executor: {coordinator.real_executor is not None}")
    print()
    
    # Statistics
    stats = coordinator.get_statistics()
    print("Coordinator statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("NOTE: Real actions require UNSAFE mode and explicit confirmation")
    print("=" * 60)
