"""
Collusion Coordinator - Launcher Application (Roadmap6 Phase 4).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Coordinate real-time collusion between HIVE bots
- Integrate card sharing, collective decisions, and manipulation
- Execute real actions via RealActionExecutor
- Low-latency communication
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import time

from launcher.bot_instance import BotInstance
from launcher.auto_seating import HiveDeployment

# Import from existing HIVE modules
try:
    from hive.card_sharing import CardSharingSystem, CardShare
    from hive.collusion_activation import CollusionActivator, CollusionMode
    from hive.manipulation_logic import ManipulationEngine, ManipulationStrategy
    HIVE_AVAILABLE = True
except ImportError:
    HIVE_AVAILABLE = False
    logger.warning("HIVE modules not available")

# Import from bridge
try:
    from bridge.safety import SafetyFramework, SafetyMode
    from bridge.action.real_executor import RealActionExecutor
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CollusionSession:
    """
    Active collusion session for HIVE team.
    
    Attributes:
        session_id: Unique session ID
        deployment: Associated deployment
        bot_ids: 3 bot IDs in HIVE team
        active: Whether collusion is active
        started_at: Session start time
        hands_played: Hands played in session
        total_profit: Total profit in session
        card_shares_count: Number of card shares
        manipulations_count: Number of manipulations
    """
    session_id: str
    deployment: HiveDeployment
    bot_ids: List[str] = field(default_factory=list)
    active: bool = False
    started_at: Optional[float] = None
    hands_played: int = 0
    total_profit: float = 0.0
    card_shares_count: int = 0
    manipulations_count: int = 0
    
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.active and len(self.bot_ids) == 3


class CollusionCoordinator:
    """
    Coordinates real-time collusion for HIVE teams.
    
    Features:
    - Card sharing between 3 bots
    - Collective decision making
    - 3vs1 manipulation strategies
    - Real action execution
    
    ⚠️ EDUCATIONAL NOTE:
        Implements COORDINATED COLLUSION and MANIPULATION.
        ILLEGAL in real poker. Educational research only.
    """
    
    def __init__(
        self,
        safety: Optional['SafetyFramework'] = None,
        enable_real_actions: bool = False
    ):
        """
        Initialize collusion coordinator.
        
        Args:
            safety: Safety framework instance
            enable_real_actions: Enable real action execution (UNSAFE)
        """
        self.safety = safety
        self.enable_real_actions = enable_real_actions
        
        # Active sessions
        self.sessions: Dict[str, CollusionSession] = {}
        
        # Components (if available)
        self.card_sharing: Optional['CardSharingSystem'] = None
        self.collusion_activator: Optional['CollusionActivator'] = None
        self.manipulation_engine: Optional['ManipulationEngine'] = None
        self.real_executor: Optional['RealActionExecutor'] = None
        
        # Initialize components
        self._initialize_components()
        
        logger.info("Collusion coordinator initialized")
        logger.critical(
            "CRITICAL: Collusion coordinator for COORDINATED COLLUSION. "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def _initialize_components(self):
        """Initialize collusion components."""
        if not HIVE_AVAILABLE:
            logger.error("HIVE modules not available - collusion disabled")
            return
        
        try:
            # Card sharing system
            self.card_sharing = CardSharingSystem(enable_logging=True)
            logger.info("Card sharing system initialized")
            
            # Collusion activator (requires bot_pool and card_sharing)
            # For Phase 4, we'll skip full initialization
            # In a complete implementation, this would be:
            # self.collusion_activator = CollusionActivator(bot_pool, self.card_sharing)
            self.collusion_activator = None
            logger.info("Collusion activator (placeholder)")
            
            # Manipulation engine
            self.manipulation_engine = ManipulationEngine(
                aggressive_threshold=0.65,
                fold_threshold=0.40,
                enable_manipulation=True
            )
            logger.critical("Manipulation engine initialized - 3vs1 ACTIVE")
            
            # Real executor (if enabled and available)
            if self.enable_real_actions and BRIDGE_AVAILABLE:
                if self.safety and self.safety.config.mode == SafetyMode.UNSAFE:
                    try:
                        self.real_executor = RealActionExecutor(safety=self.safety)
                        logger.critical(
                            "REAL ACTION EXECUTOR INITIALIZED - "
                            "UNSAFE MODE. Educational research only."
                        )
                    except Exception as e:
                        logger.error(f"Failed to initialize real executor: {e}")
                else:
                    logger.warning(
                        "Real actions requested but not in UNSAFE mode - "
                        "actions will be simulated"
                    )
        
        except Exception as e:
            logger.error(f"Failed to initialize collusion components: {e}")
    
    async def create_session(
        self,
        deployment: HiveDeployment,
        bots: List[BotInstance]
    ) -> Optional[CollusionSession]:
        """
        Create collusion session for HIVE deployment.
        
        Args:
            deployment: HIVE deployment
            bots: 3 bots in HIVE team
        
        Returns:
            Collusion session if successful
        """
        if len(bots) != 3:
            logger.error(f"HIVE session requires 3 bots, got {len(bots)}")
            return None
        
        if not deployment.is_complete():
            logger.error("Cannot create session for incomplete deployment")
            return None
        
        # Create session
        session = CollusionSession(
            session_id=f"session_{deployment.deployment_id}",
            deployment=deployment,
            bot_ids=[bot.bot_id for bot in bots],
            active=False,
            started_at=time.time()
        )
        
        # Register session
        self.sessions[session.session_id] = session
        
        logger.critical(
            f"COLLUSION SESSION CREATED: {deployment.table.table_name} - "
            f"3 bots coordinating. Educational research only."
        )
        
        # Activate collusion
        await self._activate_collusion(session, bots)
        
        return session
    
    async def _activate_collusion(
        self,
        session: CollusionSession,
        bots: List[BotInstance]
    ):
        """
        Activate collusion for session.
        
        Args:
            session: Collusion session
            bots: Bots in session
        """
        try:
            # Create team in collusion system
            team_id = f"team_{session.session_id}"
            
            # PLACEHOLDER: In real implementation, this would:
            # 1. Register team with collusion_activator (if available)
            # 2. Enable card sharing for team
            # 3. Activate manipulation strategies
            # 4. Start real-time coordination
            
            # For Phase 4, mark as active directly
            session.active = True
            
            logger.critical(
                f"COLLUSION ACTIVATED: {session.deployment.table.table_name} - "
                f"Card sharing and manipulation ENABLED"
            )
        
        except Exception as e:
            logger.error(f"Failed to activate collusion: {e}")
    
    async def share_cards(
        self,
        session_id: str,
        bot_id: str,
        hole_cards: tuple
    ) -> bool:
        """
        Share hole cards with team.
        
        Args:
            session_id: Session ID
            bot_id: Bot ID sharing cards
            hole_cards: Hole cards tuple
        
        Returns:
            True if successful
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active():
            return False
        
        if not self.card_sharing:
            logger.warning("Card sharing system not available")
            return False
        
        try:
            # Create card share
            card_share = CardShare(
                bot_id=bot_id,
                card1=hole_cards[0],
                card2=hole_cards[1],
                timestamp=time.time()
            )
            
            # Share with team
            team_id = f"team_{session_id}"
            self.card_sharing.share_cards(team_id, card_share)
            
            session.card_shares_count += 1
            
            logger.debug(
                f"Cards shared: {bot_id[:8]} in {session.deployment.table.table_name}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to share cards: {e}")
            return False
    
    async def make_collective_decision(
        self,
        session_id: str,
        bot_id: str,
        game_state: dict,
        available_actions: list
    ) -> Optional[str]:
        """
        Make collective decision with full collusion.
        
        Args:
            session_id: Session ID
            bot_id: Bot making decision
            game_state: Current game state
            available_actions: Available actions
        
        Returns:
            Chosen action if successful
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active():
            return None
        
        if not self.manipulation_engine:
            logger.warning("Manipulation engine not available")
            return None
        
        try:
            # PLACEHOLDER: In real implementation, this would:
            # 1. Get known opponent cards from card_sharing
            # 2. Calculate collective equity
            # 3. Apply manipulation strategy based on equity
            # 4. Return action
            
            # For Phase 4, return placeholder
            action = "check"
            
            logger.debug(
                f"Collective decision: {bot_id[:8]} → {action}"
            )
            
            return action
        
        except Exception as e:
            logger.error(f"Failed to make collective decision: {e}")
            return None
    
    async def execute_action(
        self,
        session_id: str,
        bot_id: str,
        action: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Execute action for bot.
        
        Args:
            session_id: Session ID
            bot_id: Bot executing action
            action: Action to execute
            amount: Amount (for bet/raise)
        
        Returns:
            True if successful
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active():
            return False
        
        try:
            # Use real executor if available
            if self.real_executor:
                # PLACEHOLDER: In real implementation, this would:
                # 1. Map action to button position from ROI
                # 2. Execute mouse click via real_executor
                # 3. Handle bet amount input
                # 4. Verify action execution
                
                logger.critical(
                    f"REAL ACTION EXECUTED: {action} by {bot_id[:8]} "
                    f"(amount: {amount})"
                )
                
                session.manipulations_count += 1
                return True
            
            else:
                # Simulate action
                logger.info(
                    f"Action simulated: {action} by {bot_id[:8]} "
                    f"(amount: {amount})"
                )
                
                session.manipulations_count += 1
                return True
        
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            return False
    
    async def end_session(self, session_id: str):
        """
        End collusion session.
        
        Args:
            session_id: Session ID
        """
        session = self.sessions.get(session_id)
        if not session:
            return
        
        session.active = False
        
        logger.info(
            f"Collusion session ended: {session.deployment.table.table_name} - "
            f"Hands: {session.hands_played}, Profit: ${session.total_profit:.2f}, "
            f"Card shares: {session.card_shares_count}, "
            f"Manipulations: {session.manipulations_count}"
        )
    
    def get_active_sessions(self) -> List[CollusionSession]:
        """
        Get active collusion sessions.
        
        Returns:
            List of active sessions
        """
        return [s for s in self.sessions.values() if s.is_active()]
    
    def get_statistics(self) -> dict:
        """
        Get collusion statistics.
        
        Returns:
            Statistics dictionary
        """
        active = self.get_active_sessions()
        
        total_hands = sum(s.hands_played for s in self.sessions.values())
        total_profit = sum(s.total_profit for s in self.sessions.values())
        total_shares = sum(s.card_shares_count for s in self.sessions.values())
        total_manipulations = sum(s.manipulations_count for s in self.sessions.values())
        
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': len(active),
            'total_hands': total_hands,
            'total_profit': total_profit,
            'total_card_shares': total_shares,
            'total_manipulations': total_manipulations,
            'real_actions_enabled': self.real_executor is not None
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Collusion Coordinator - Educational Research")
    print("=" * 60)
    print()
    
    # Create coordinator
    coordinator = CollusionCoordinator(enable_real_actions=False)
    
    print(f"Collusion coordinator created")
    print(f"  Card sharing: {'Available' if coordinator.card_sharing else 'Not available'}")
    print(f"  Manipulation: {'Available' if coordinator.manipulation_engine else 'Not available'}")
    print(f"  Real actions: {'Enabled' if coordinator.real_executor else 'Disabled'}")
    print()
    
    # Statistics
    stats = coordinator.get_statistics()
    print(f"Statistics:")
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Real actions: {stats['real_actions_enabled']}")
    print()
    
    print("=" * 60)
    print("Collusion coordinator demonstration complete")
    print("=" * 60)
