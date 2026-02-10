"""
Tests for Auto-Seating (Roadmap5 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest

from hive.auto_seating import AutoSeating, DeploymentResult, DeploymentStatus
from hive.bot_pool import BotPool
from hive.table_scanner import HiveOpportunity, TablePriority, TableScanner


class TestDeploymentResult:
    """Test deployment result."""
    
    def test_creation(self):
        """Test result creation."""
        result = DeploymentResult(
            table_id="table_1",
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            status=DeploymentStatus.PENDING
        )
        
        assert result.table_id == "table_1"
        assert result.team_id == "team_1"
        assert len(result.bot_ids) == 3
        assert result.status == DeploymentStatus.PENDING
    
    def test_complete_success(self):
        """Test successful completion."""
        result = DeploymentResult(
            table_id="table_1",
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            status=DeploymentStatus.IN_PROGRESS
        )
        
        result.complete(success=True)
        
        assert result.status == DeploymentStatus.COMPLETED
        assert result.end_time is not None
        assert result.error_message is None
    
    def test_complete_failure(self):
        """Test failed completion."""
        result = DeploymentResult(
            table_id="table_1",
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            status=DeploymentStatus.IN_PROGRESS
        )
        
        result.complete(success=False, error="Test error")
        
        assert result.status == DeploymentStatus.FAILED
        assert result.end_time is not None
        assert result.error_message == "Test error"
    
    def test_get_duration(self):
        """Test duration calculation."""
        result = DeploymentResult(
            table_id="table_1",
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            status=DeploymentStatus.PENDING
        )
        
        # Before completion
        assert result.get_duration() is None
        
        # After completion
        result.complete(success=True)
        duration = result.get_duration()
        
        assert duration is not None
        assert duration >= 0


class TestAutoSeating:
    """Test auto-seating."""
    
    def test_initialization(self):
        """Test seating initialization."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            deployment_delay=1.0,
            dry_run=True
        )
        
        assert seating.bot_pool == pool
        assert seating.table_scanner == scanner
        assert seating.deployment_delay == 1.0
        assert seating.dry_run is True
        assert seating.deployments_attempted == 0
    
    def test_deploy_team(self):
        """Test team deployment."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            deployment_delay=0.1,  # Fast for testing
            dry_run=True
        )
        
        # Create opportunity
        opportunity = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0
        )
        
        # Deploy
        result = seating.deploy_team(opportunity)
        
        # Check result
        assert result.table_id == "table_1"
        assert len(result.bot_ids) == 3
        assert seating.deployments_attempted == 1
        
        # Status depends on simulated success rate
        assert result.status in [
            DeploymentStatus.COMPLETED,
            DeploymentStatus.FAILED
        ]
    
    def test_deploy_team_no_bots_available(self):
        """Test deployment fails when no bots."""
        pool = BotPool(group_hash="test", pool_size=2)  # Not enough
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            dry_run=True
        )
        
        opportunity = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0
        )
        
        result = seating.deploy_team(opportunity)
        
        assert result.status == DeploymentStatus.FAILED
        assert seating.deployments_failed == 1
    
    def test_deploy_team_table_already_occupied(self):
        """Test deployment fails if table occupied."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            deployment_delay=0.1,
            dry_run=True
        )
        
        opportunity = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0
        )
        
        # First deployment
        result1 = seating.deploy_team(opportunity)
        
        # Try second deployment to same table
        result2 = seating.deploy_team(opportunity)
        
        # Second should fail (table already has deployment)
        # Note: might succeed if first failed in simulation
        if result1.status == DeploymentStatus.COMPLETED:
            assert result2.status == DeploymentStatus.FAILED
    
    def test_select_seat(self):
        """Test seat selection."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            dry_run=True
        )
        
        opportunity = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0,
            metadata={'max_players': 9}
        )
        
        # Select seats for 3 bots
        seat1 = seating._select_seat(opportunity, bot_index=0, total_bots=3)
        seat2 = seating._select_seat(opportunity, bot_index=1, total_bots=3)
        seat3 = seating._select_seat(opportunity, bot_index=2, total_bots=3)
        
        # Seats should be within bounds
        assert 1 <= seat1 <= 9
        assert 1 <= seat2 <= 9
        assert 1 <= seat3 <= 9
        
        # Seats should be spread out
        assert seat1 != seat2
        assert seat2 != seat3
    
    def test_cancel_deployment(self):
        """Test deployment cancellation."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            deployment_delay=0.1,
            dry_run=True
        )
        
        opportunity = HiveOpportunity(
            table_id="table_1",
            human_count=1,
            seats_available=8,
            priority=TablePriority.CRITICAL,
            score=95.0
        )
        
        # Deploy
        result = seating.deploy_team(opportunity)
        
        if result.status == DeploymentStatus.COMPLETED:
            # Cancel
            cancelled = seating.cancel_deployment("table_1")
            
            assert cancelled is True
            assert "table_1" not in seating.active_deployments
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        pool = BotPool(group_hash="test", pool_size=10)
        scanner = TableScanner(dry_run=True)
        seating = AutoSeating(
            bot_pool=pool,
            table_scanner=scanner,
            dry_run=True
        )
        
        stats = seating.get_statistics()
        
        assert stats['deployments_attempted'] == 0
        assert stats['deployments_succeeded'] == 0
        assert stats['deployments_failed'] == 0
        assert stats['dry_run'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
