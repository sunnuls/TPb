"""
Auto-Seating System - Educational Game Theory Research.

⚠️ ETHICAL WARNING:
    This implements coordinated multi-agent table joining for RESEARCH ONLY.
    Demonstrates synchronized agent deployment in game environments.
    NEVER use without explicit participant consent.

Coordinates 3-bot HIVE team deployment:
- Synchronized table joining
- Seat selection strategy
- Timing coordination
- Deployment verification
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from hive.bot_pool import BotPool, HiveTeam
from hive.table_scanner import HiveOpportunity, TableScanner

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """HIVE deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DeploymentResult:
    """
    HIVE deployment result.
    
    Attributes:
        table_id: Target table
        team_id: HIVE team identifier
        bot_ids: Bot identifiers
        status: Deployment status
        start_time: Deployment start
        end_time: Deployment completion
        error_message: Error if failed
    """
    table_id: str
    team_id: str
    bot_ids: List[str]
    status: DeploymentStatus
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark deployment as complete.
        
        Args:
            success: Whether deployment succeeded
            error: Error message if failed
        """
        self.end_time = time.time()
        
        if success:
            self.status = DeploymentStatus.COMPLETED
        else:
            self.status = DeploymentStatus.FAILED
            self.error_message = error
    
    def get_duration(self) -> Optional[float]:
        """
        Get deployment duration.
        
        Returns:
            Duration in seconds, or None if not complete
        """
        if self.end_time:
            return self.end_time - self.start_time
        
        return None


class AutoSeating:
    """
    Automated HIVE seating coordinator.
    
    Manages coordinated deployment of 3-bot teams to tables.
    
    Features:
    - Opportunity evaluation
    - Bot pool integration
    - Synchronized seating
    - Seat selection strategy
    - Deployment verification
    
    ⚠️ EDUCATIONAL USE ONLY:
        Demonstrates multi-agent coordination for research.
        NOT for use in real games.
    """
    
    def __init__(
        self,
        bot_pool: BotPool,
        table_scanner: TableScanner,
        deployment_delay: float = 2.0,
        dry_run: bool = True
    ):
        """
        Initialize auto-seating system.
        
        Args:
            bot_pool: Bot pool manager
            table_scanner: Table scanner
            deployment_delay: Delay between bot joins (seconds)
            dry_run: If True, simulation mode
        """
        self.bot_pool = bot_pool
        self.table_scanner = table_scanner
        self.deployment_delay = deployment_delay
        self.dry_run = dry_run
        
        # Deployment tracking
        self.deployments: Dict[str, DeploymentResult] = {}
        self.active_deployments: Dict[str, str] = {}  # table_id -> team_id
        
        # Statistics
        self.deployments_attempted = 0
        self.deployments_succeeded = 0
        self.deployments_failed = 0
        
        logger.info(
            f"AutoSeating initialized "
            f"(delay: {deployment_delay}s, dry_run: {dry_run})"
        )
    
    async def deploy_team_async(
        self,
        opportunity: HiveOpportunity
    ) -> DeploymentResult:
        """
        Deploy HIVE team to table (async).
        
        Args:
            opportunity: Target table opportunity
        
        Returns:
            DeploymentResult
        
        EDUCATIONAL NOTE:
            Simulates coordinated agent deployment for research.
        """
        self.deployments_attempted += 1
        
        table_id = opportunity.table_id
        
        # Check if table already has team
        if table_id in self.active_deployments:
            error = f"Table {table_id} already has active deployment"
            logger.warning(error)
            
            result = DeploymentResult(
                table_id=table_id,
                team_id="",
                bot_ids=[],
                status=DeploymentStatus.FAILED
            )
            result.complete(success=False, error=error)
            
            self.deployments_failed += 1
            return result
        
        # Form team
        team = self.bot_pool.form_team(table_id=table_id)
        
        if not team:
            error = "Failed to form team (no available bots)"
            logger.error(error)
            
            result = DeploymentResult(
                table_id=table_id,
                team_id="",
                bot_ids=[],
                status=DeploymentStatus.FAILED
            )
            result.complete(success=False, error=error)
            
            self.deployments_failed += 1
            return result
        
        # Create deployment
        result = DeploymentResult(
            table_id=table_id,
            team_id=team.team_id,
            bot_ids=team.bot_ids,
            status=DeploymentStatus.IN_PROGRESS
        )
        
        self.deployments[team.team_id] = result
        self.active_deployments[table_id] = team.team_id
        
        logger.info(
            f"Deploying team {team.team_id[:8]} to table {table_id}"
        )
        
        # Deploy bots sequentially (simulate)
        try:
            for i, bot_id in enumerate(team.bot_ids):
                # Select seat (simulate strategic positioning)
                seat = self._select_seat(
                    opportunity=opportunity,
                    bot_index=i,
                    total_bots=len(team.bot_ids)
                )
                
                # Join table (simulated)
                success = await self._join_table_async(
                    bot_id=bot_id,
                    table_id=table_id,
                    seat=seat
                )
                
                if not success:
                    raise RuntimeError(f"Bot {bot_id[:8]} failed to join")
                
                logger.info(
                    f"Bot {bot_id[:8]} joined table {table_id}, "
                    f"seat {seat}"
                )
                
                # Delay before next bot
                if i < len(team.bot_ids) - 1:
                    await asyncio.sleep(self.deployment_delay)
            
            # Mark table as occupied
            self.table_scanner.mark_table_occupied(table_id)
            
            # Complete deployment
            result.complete(success=True)
            
            self.deployments_succeeded += 1
            
            logger.info(
                f"Team {team.team_id[:8]} deployed successfully "
                f"to table {table_id}"
            )
            
        except Exception as e:
            error = f"Deployment failed: {str(e)}"
            logger.error(error, exc_info=True)
            
            # Cleanup: disband team
            self.bot_pool.disband_team(team.team_id)
            
            # Remove from active
            if table_id in self.active_deployments:
                del self.active_deployments[table_id]
            
            result.complete(success=False, error=error)
            
            self.deployments_failed += 1
        
        return result
    
    def deploy_team(self, opportunity: HiveOpportunity) -> DeploymentResult:
        """
        Deploy HIVE team to table (sync wrapper).
        
        Args:
            opportunity: Target table opportunity
        
        Returns:
            DeploymentResult
        """
        return asyncio.run(self.deploy_team_async(opportunity))
    
    async def _join_table_async(
        self,
        bot_id: str,
        table_id: str,
        seat: int
    ) -> bool:
        """
        Join table (simulated).
        
        Args:
            bot_id: Bot identifier
            table_id: Table identifier
            seat: Seat number
        
        Returns:
            True if successful
        
        EDUCATIONAL NOTE:
            In production, would execute real table join actions.
            In dry-run, simulates successful join.
        """
        if self.dry_run:
            # Simulate join delay
            await asyncio.sleep(0.5)
            
            # Simulate success (95% success rate)
            import random
            success = random.random() < 0.95
            
            if success:
                logger.debug(
                    f"[DRY-RUN] Bot {bot_id[:8]} joined table {table_id}, "
                    f"seat {seat}"
                )
            else:
                logger.warning(
                    f"[DRY-RUN] Bot {bot_id[:8]} failed to join table {table_id}"
                )
            
            return success
        
        # Real implementation would:
        # 1. Navigate to table in lobby
        # 2. Click "Sit" button
        # 3. Select seat
        # 4. Confirm join
        # 5. Wait for confirmation
        
        # For now, always fail in non-dry-run
        logger.error("Real table joining not implemented (requires UI automation)")
        return False
    
    def _select_seat(
        self,
        opportunity: HiveOpportunity,
        bot_index: int,
        total_bots: int
    ) -> int:
        """
        Select seat for bot.
        
        Args:
            opportunity: Table opportunity
            bot_index: Bot index in team (0, 1, 2)
            total_bots: Total bots in team
        
        Returns:
            Seat number
        
        EDUCATIONAL NOTE:
            Strategic seat selection for optimal 3vs1 positioning.
        """
        # Ideal: spread bots around table for pressure
        # Example 9-max: seats 2, 5, 8 (evenly distributed)
        # Example 6-max: seats 1, 3, 5
        
        # Get max_seats from metadata (LobbyTable)
        max_seats = 9  # Default
        if hasattr(opportunity.metadata, 'max_seats'):
            max_seats = opportunity.metadata.max_seats
        elif isinstance(opportunity.metadata, dict):
            max_seats = opportunity.metadata.get('max_players', 9)
        
        # Calculate ideal spacing
        spacing = max_seats // total_bots
        
        # Assign seat
        seat = (bot_index * spacing) + 1
        
        # Ensure within bounds
        seat = max(1, min(seat, max_seats))
        
        return seat
    
    def cancel_deployment(self, table_id: str) -> bool:
        """
        Cancel active deployment.
        
        Args:
            table_id: Table identifier
        
        Returns:
            True if cancelled
        """
        if table_id not in self.active_deployments:
            logger.warning(f"No active deployment for table {table_id}")
            return False
        
        team_id = self.active_deployments[table_id]
        
        # Disband team
        self.bot_pool.disband_team(team_id)
        
        # Update deployment result
        if team_id in self.deployments:
            self.deployments[team_id].status = DeploymentStatus.CANCELLED
            self.deployments[team_id].end_time = time.time()
        
        # Remove from active
        del self.active_deployments[table_id]
        
        logger.info(f"Deployment to table {table_id} cancelled")
        
        return True
    
    def get_deployment_result(self, team_id: str) -> Optional[DeploymentResult]:
        """
        Get deployment result.
        
        Args:
            team_id: Team identifier
        
        Returns:
            DeploymentResult if found
        """
        return self.deployments.get(team_id)
    
    def get_statistics(self) -> dict:
        """
        Get seating statistics.
        
        Returns:
            Statistics dictionary
        """
        active_count = len(self.active_deployments)
        
        success_rate = 0.0
        if self.deployments_attempted > 0:
            success_rate = (
                self.deployments_succeeded / self.deployments_attempted * 100
            )
        
        return {
            'deployments_attempted': self.deployments_attempted,
            'deployments_succeeded': self.deployments_succeeded,
            'deployments_failed': self.deployments_failed,
            'active_deployments': active_count,
            'success_rate': success_rate,
            'dry_run': self.dry_run
        }


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Auto-Seating System - Educational Game Theory Research")
    print("=" * 60)
    print()
    print("WARNING - CRITICAL:")
    print("This demonstrates coordinated agent deployment for RESEARCH ONLY.")
    print("NEVER use in real games without explicit consent.")
    print()
    
    # Create components
    from hive.bot_pool import BotPool
    from hive.table_scanner import HiveOpportunity, TablePriority, TableScanner
    
    bot_pool = BotPool(group_hash="research", pool_size=10)
    scanner = TableScanner(dry_run=True)
    
    seating = AutoSeating(
        bot_pool=bot_pool,
        table_scanner=scanner,
        deployment_delay=1.0,
        dry_run=True
    )
    
    print("Auto-seating initialized")
    print()
    
    # Create test opportunity
    opportunity = HiveOpportunity(
        table_id="research_table_1",
        human_count=1,
        seats_available=8,
        priority=TablePriority.CRITICAL,
        score=95.0
    )
    
    print(f"Test opportunity: {opportunity.table_id}")
    print(f"  Humans: {opportunity.human_count}")
    print(f"  Seats: {opportunity.seats_available}")
    print(f"  Priority: {opportunity.priority.value}")
    print()
    
    # Deploy team
    print("Deploying HIVE team...")
    result = seating.deploy_team(opportunity)
    
    print(f"\nDeployment result:")
    print(f"  Status: {result.status.value}")
    print(f"  Team ID: {result.team_id[:8]}")
    print(f"  Bots: {[b[:8] for b in result.bot_ids]}")
    print(f"  Duration: {result.get_duration():.2f}s")
    print()
    
    # Statistics
    stats = seating.get_statistics()
    print("Seating statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    print("=" * 60)
    print("Educational demonstration complete")
    print("=" * 60)
