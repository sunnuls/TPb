"""
Auto-Seating Manager - Launcher Application (Roadmap6 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY.

Features:
- Automatic table discovery
- Coordinate 3-bot HIVE deployment
- Seat selection strategy
- Session creation after full deployment
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
import time

from launcher.lobby_scanner import LobbyScanner, LobbyTable
from launcher.bot_manager import BotManager
from launcher.bot_instance import BotInstance

logger = logging.getLogger(__name__)

# Import collusion coordinator (optional for Phase 4)
try:
    from launcher.collusion_coordinator import CollusionCoordinator
    COLLUSION_AVAILABLE = True
except ImportError:
    COLLUSION_AVAILABLE = False


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HiveDeployment:
    """
    HIVE team deployment to a table.
    
    Attributes:
        deployment_id: Unique deployment ID
        table: Target table
        bot_ids: List of 3 bot IDs for HIVE team
        status: Deployment status
        started_at: Deployment start time
        completed_at: Deployment completion time
        error_message: Error message if failed
    """
    deployment_id: str
    table: LobbyTable
    bot_ids: List[str] = field(default_factory=list)
    status: DeploymentStatus = DeploymentStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: str = ""
    
    def is_complete(self) -> bool:
        """Check if deployment is complete."""
        return (
            self.status == DeploymentStatus.COMPLETED and
            len(self.bot_ids) == 3
        )


class AutoSeatingManager:
    """
    Automatic seating manager for HIVE deployment.
    
    Features:
    - Continuous lobby scanning
    - Priority-based opportunity selection
    - 3-bot team coordination
    - Strategic seat selection
    - Session creation after deployment
    
    ⚠️ EDUCATIONAL NOTE:
        Coordinates automated deployment of colluding bots.
    """
    
    def __init__(
        self,
        bot_manager: BotManager,
        lobby_scanner: LobbyScanner,
        scan_interval: float = 5.0,
        collusion_coordinator: Optional['CollusionCoordinator'] = None
    ):
        """
        Initialize auto-seating manager.
        
        Args:
            bot_manager: Bot manager instance
            lobby_scanner: Lobby scanner instance
            scan_interval: Lobby scan interval in seconds
            collusion_coordinator: Optional collusion coordinator (Phase 4)
        """
        self.bot_manager = bot_manager
        self.lobby_scanner = lobby_scanner
        self.scan_interval = scan_interval
        self.collusion_coordinator = collusion_coordinator
        
        # Active deployments
        self.deployments: Dict[str, HiveDeployment] = {}
        
        # Tables currently being targeted
        self.targeted_tables: set = set()
        
        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info("Auto-seating manager initialized")
        logger.critical(
            "CRITICAL: Auto-seating for COORDINATED COLLUSION. "
            "Educational research only. ILLEGAL in real poker."
        )
    
    def is_running(self) -> bool:
        """Check if auto-seating is running."""
        return self._running
    
    async def start(self):
        """Start auto-seating service."""
        if self._running:
            logger.warning("Auto-seating already running")
            return
        
        logger.info("Starting auto-seating service...")
        
        self._running = True
        self._task = asyncio.create_task(self._auto_seating_loop())
    
    async def stop(self):
        """Stop auto-seating service."""
        if not self._running:
            return
        
        logger.info("Stopping auto-seating service...")
        
        self._running = False
        
        # Cancel task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Auto-seating service stopped")
    
    async def _auto_seating_loop(self):
        """Main auto-seating loop."""
        try:
            logger.info("Auto-seating loop started")
            
            while self._running:
                # Scan for opportunities
                try:
                    await self._scan_and_deploy()
                except Exception as e:
                    logger.error(f"Error in auto-seating cycle: {e}")
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
        
        except asyncio.CancelledError:
            logger.info("Auto-seating loop cancelled")
        
        except Exception as e:
            logger.error(f"Fatal error in auto-seating loop: {e}")
    
    async def _scan_and_deploy(self):
        """Scan lobby and deploy to opportunities."""
        # Get idle bots
        idle_bots = self.bot_manager.get_idle_bots()
        
        if len(idle_bots) < 3:
            logger.debug(f"Not enough idle bots: {len(idle_bots)}/3")
            return
        
        # Scan lobby
        snapshot = self.lobby_scanner.scan_lobby()
        opportunities = snapshot.get_hive_opportunities()
        
        if not opportunities:
            logger.debug("No HIVE opportunities found")
            return
        
        # Filter out already targeted tables
        available = [
            opp for opp in opportunities
            if opp.table_id not in self.targeted_tables
        ]
        
        if not available:
            logger.debug("All opportunities already targeted")
            return
        
        # Deploy to best opportunity
        best = available[0]
        
        logger.info(
            f"Deploying HIVE to {best.table_name} "
            f"({best.human_count} humans, {best.seats_available()} seats)"
        )
        
        await self._deploy_hive_team(best, idle_bots[:3])
    
    async def _deploy_hive_team(
        self,
        table: LobbyTable,
        bots: List[BotInstance]
    ) -> Optional[HiveDeployment]:
        """
        Deploy HIVE team to table.
        
        Args:
            table: Target table
            bots: 3 bots for HIVE team
        
        Returns:
            Deployment object if successful
        """
        if len(bots) != 3:
            logger.error(f"HIVE team requires exactly 3 bots, got {len(bots)}")
            return None
        
        # Create deployment
        deployment = HiveDeployment(
            deployment_id=f"deploy_{int(time.time())}_{table.table_id}",
            table=table,
            bot_ids=[bot.bot_id for bot in bots],
            status=DeploymentStatus.DEPLOYING,
            started_at=time.time()
        )
        
        # Register deployment
        self.deployments[deployment.deployment_id] = deployment
        self.targeted_tables.add(table.table_id)
        
        try:
            # Deploy each bot
            for i, bot in enumerate(bots):
                logger.info(
                    f"Deploying bot {i+1}/3: {bot.account.nickname} "
                    f"to {table.table_name}"
                )
                
                # PLACEHOLDER: In real implementation, this would:
                # 1. Navigate to table
                # 2. Select strategic seat
                # 3. Join table
                # 4. Wait for confirmation
                
                # For Phase 3, just mark table for bot
                bot.current_table = table.table_name
                
                # Small delay between seats
                await asyncio.sleep(0.5)
            
            # Mark deployment complete
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = time.time()
            
            logger.info(
                f"HIVE deployment complete: {table.table_name} "
                f"({len(bots)} bots deployed)"
            )
            
            # Create HIVE session
            await self._create_hive_session(deployment)
            
            return deployment
        
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = time.time()
            
            logger.error(f"HIVE deployment failed: {e}")
            
            # Remove from targeted tables on failure
            self.targeted_tables.discard(table.table_id)
            
            return None
    
    async def _create_hive_session(self, deployment: HiveDeployment):
        """
        Create HIVE session after successful deployment.
        
        This activates:
        - Hole card sharing
        - Collective decision making
        - 3vs1 manipulation strategies
        
        Args:
            deployment: Completed deployment
        """
        logger.critical(
            f"HIVE SESSION CREATED: {deployment.table.table_name} - "
            f"COLLUSION ACTIVE. Educational research only."
        )
        
        # Phase 4: Use collusion coordinator if available
        if self.collusion_coordinator and COLLUSION_AVAILABLE:
            try:
                # Get bots for this deployment
                bots = [
                    self.bot_manager.get_bot(bot_id)
                    for bot_id in deployment.bot_ids
                ]
                bots = [b for b in bots if b is not None]
                
                if len(bots) == 3:
                    # Create collusion session
                    session = await self.collusion_coordinator.create_session(
                        deployment,
                        bots
                    )
                    
                    if session:
                        logger.critical(
                            f"COLLUSION SESSION ACTIVE: {deployment.table.table_name} - "
                            f"Card sharing and manipulation ENABLED"
                        )
                else:
                    logger.error(f"Failed to get all 3 bots for session")
            
            except Exception as e:
                logger.error(f"Failed to create collusion session: {e}")
        
        else:
            # Phase 3 behavior: Just log
            logger.info(
                f"HIVE session for {deployment.table.table_name}: "
                f"{len(deployment.bot_ids)} bots coordinating "
                f"(collusion coordinator not available)"
            )
    
    def get_active_deployments(self) -> List[HiveDeployment]:
        """
        Get active deployments.
        
        Returns:
            List of active deployments
        """
        return [
            d for d in self.deployments.values()
            if d.status in [DeploymentStatus.DEPLOYING, DeploymentStatus.COMPLETED]
        ]
    
    def get_statistics(self) -> dict:
        """
        Get auto-seating statistics.
        
        Returns:
            Statistics dictionary
        """
        total = len(self.deployments)
        completed = len([d for d in self.deployments.values() if d.is_complete()])
        failed = len([d for d in self.deployments.values() if d.status == DeploymentStatus.FAILED])
        active = len(self.get_active_deployments())
        
        return {
            'total_deployments': total,
            'completed_deployments': completed,
            'failed_deployments': failed,
            'active_deployments': active,
            'targeted_tables': len(self.targeted_tables)
        }


# Educational example
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Auto-Seating Manager - Educational Research")
    print("=" * 60)
    print()
    
    # Create components
    from launcher.bot_manager import BotManager
    from launcher.models.account import Account, WindowInfo, WindowType
    from launcher.models.roi_config import ROIConfig, ROIZone
    
    bot_manager = BotManager()
    lobby_scanner = LobbyScanner()
    
    # Create test bots
    print("Creating 3 test bots...")
    for i in range(3):
        account = Account(nickname=f"AutoBot{i+1:03d}", room="pokerstars")
        account.window_info = WindowInfo(
            window_id=f"{12345+i}",
            window_title=f"PokerStars - AutoBot{i+1:03d}",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id)
        roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
        roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        
        bot_manager.create_bot(account, roi)
    
    print(f"Created {len(bot_manager.get_all_bots())} bots")
    print()
    
    # Create auto-seating manager
    manager = AutoSeatingManager(
        bot_manager=bot_manager,
        lobby_scanner=lobby_scanner,
        scan_interval=2.0
    )
    
    print("Auto-seating manager created")
    print(f"  Scan interval: {manager.scan_interval}s")
    print(f"  Idle bots: {len(bot_manager.get_idle_bots())}")
    print()
    
    # Demonstrate deployment (async)
    async def demo():
        print("Simulating lobby with opportunities...")
        snapshot = lobby_scanner.simulate_lobby_data(10)
        opportunities = snapshot.get_hive_opportunities()
        
        print(f"Found {len(opportunities)} HIVE opportunities")
        
        if opportunities:
            best = opportunities[0]
            print(f"\nDeploying HIVE to: {best.table_name}")
            print(f"  Humans: {best.human_count}")
            print(f"  Seats: {best.seats_available()}")
            
            idle_bots = bot_manager.get_idle_bots()
            deployment = await manager._deploy_hive_team(best, idle_bots[:3])
            
            if deployment:
                print(f"\nDeployment complete:")
                print(f"  ID: {deployment.deployment_id[:20]}...")
                print(f"  Status: {deployment.status.value}")
                print(f"  Bots: {len(deployment.bot_ids)}")
        
        # Statistics
        stats = manager.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total deployments: {stats['total_deployments']}")
        print(f"  Completed: {stats['completed_deployments']}")
        print(f"  Active: {stats['active_deployments']}")
    
    # Run demo
    asyncio.run(demo())
    
    print()
    print("=" * 60)
    print("Auto-seating demonstration complete")
    print("=" * 60)
