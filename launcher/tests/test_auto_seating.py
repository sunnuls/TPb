"""
Tests for AutoSeatingManager - Phase 3.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import asyncio

from launcher.auto_seating import AutoSeatingManager, HiveDeployment, DeploymentStatus
from launcher.lobby_scanner import LobbyScanner, LobbyTable
from launcher.bot_manager import BotManager
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def create_test_bot_manager(num_bots: int = 3) -> BotManager:
    """Create bot manager with test bots."""
    manager = BotManager()
    
    for i in range(num_bots):
        account = Account(nickname=f"TestBot{i+1:03d}", room="pokerstars")
        account.window_info = WindowInfo(
            window_id=f"{12345+i}",
            window_title=f"PokerStars - Bot{i+1}",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id)
        roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
        roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        
        manager.create_bot(account, roi)
    
    return manager


class TestHiveDeployment:
    """Tests for HiveDeployment."""
    
    def test_create_deployment(self):
        """Test creating deployment."""
        table = LobbyTable(
            table_id="t1",
            table_name="Table 1",
            human_count=2,
            players_seated=4,
            max_seats=9
        )
        
        deployment = HiveDeployment(
            deployment_id="deploy_001",
            table=table
        )
        
        assert deployment.deployment_id == "deploy_001"
        assert deployment.table == table
        assert len(deployment.bot_ids) == 0
        assert deployment.status == DeploymentStatus.PENDING
    
    def test_is_complete(self):
        """Test completion check."""
        table = LobbyTable("t1", "Table 1")
        
        # Not complete - pending
        deployment1 = HiveDeployment("d1", table)
        assert not deployment1.is_complete()
        
        # Not complete - completed but no bots
        deployment2 = HiveDeployment("d2", table, status=DeploymentStatus.COMPLETED)
        assert not deployment2.is_complete()
        
        # Complete - completed with 3 bots
        deployment3 = HiveDeployment(
            "d3",
            table,
            bot_ids=["bot1", "bot2", "bot3"],
            status=DeploymentStatus.COMPLETED
        )
        assert deployment3.is_complete()


class TestAutoSeatingManager:
    """Tests for AutoSeatingManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        bot_manager = create_test_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner,
            scan_interval=2.0
        )
        
        assert manager.bot_manager == bot_manager
        assert manager.lobby_scanner == lobby_scanner
        assert manager.scan_interval == 2.0
        assert not manager.is_running()
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping service."""
        bot_manager = create_test_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Start
        await manager.start()
        assert manager.is_running()
        
        # Wait a bit
        await asyncio.sleep(0.2)
        
        # Stop
        await manager.stop()
        assert not manager.is_running()
    
    @pytest.mark.asyncio
    async def test_deploy_hive_team(self):
        """Test deploying HIVE team."""
        bot_manager = create_test_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Create test table
        table = LobbyTable(
            table_id="test_table",
            table_name="Test Table",
            human_count=2,
            players_seated=4,
            max_seats=9
        )
        
        # Get bots
        bots = bot_manager.get_idle_bots()
        
        # Deploy
        deployment = await manager._deploy_hive_team(table, bots)
        
        # Verify
        assert deployment is not None
        assert deployment.status == DeploymentStatus.COMPLETED
        assert len(deployment.bot_ids) == 3
        assert deployment.is_complete()
        
        # Check bots have table assigned
        for bot in bots:
            assert bot.current_table == table.table_name
    
    @pytest.mark.asyncio
    async def test_deploy_wrong_bot_count(self):
        """Test deploying with wrong number of bots."""
        bot_manager = create_test_bot_manager(2)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        table = LobbyTable("t1", "Table 1")
        bots = bot_manager.get_idle_bots()
        
        # Should return None (only 2 bots)
        deployment = await manager._deploy_hive_team(table, bots)
        
        assert deployment is None
    
    def test_get_active_deployments(self):
        """Test getting active deployments."""
        bot_manager = create_test_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Add some deployments
        table1 = LobbyTable("t1", "Table 1")
        table2 = LobbyTable("t2", "Table 2")
        
        manager.deployments["d1"] = HiveDeployment(
            "d1",
            table1,
            status=DeploymentStatus.COMPLETED
        )
        manager.deployments["d2"] = HiveDeployment(
            "d2",
            table2,
            status=DeploymentStatus.FAILED
        )
        
        active = manager.get_active_deployments()
        
        # Only d1 should be active
        assert len(active) == 1
        assert active[0].deployment_id == "d1"
    
    def test_get_statistics(self):
        """Test getting statistics."""
        bot_manager = create_test_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Add deployments
        for i in range(5):
            table = LobbyTable(f"t{i}", f"Table {i}")
            status = DeploymentStatus.COMPLETED if i < 3 else DeploymentStatus.FAILED
            deployment = HiveDeployment(
                f"d{i}",
                table,
                bot_ids=["b1", "b2", "b3"] if status == DeploymentStatus.COMPLETED else [],
                status=status
            )
            manager.deployments[deployment.deployment_id] = deployment
        
        stats = manager.get_statistics()
        
        assert stats['total_deployments'] == 5
        assert stats['completed_deployments'] == 3
        assert stats['failed_deployments'] == 2
        assert stats['active_deployments'] == 3
    
    @pytest.mark.asyncio
    async def test_scan_and_deploy_no_bots(self):
        """Test scan when no idle bots available."""
        bot_manager = create_test_bot_manager(0)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Should handle gracefully
        await manager._scan_and_deploy()
        
        assert len(manager.deployments) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_deployments(self):
        """Test multiple deployments."""
        # Create 6 bots for 2 teams
        bot_manager = create_test_bot_manager(6)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner
        )
        
        # Create 2 tables
        table1 = LobbyTable("t1", "Table 1", human_count=1, players_seated=3, max_seats=9)
        table2 = LobbyTable("t2", "Table 2", human_count=2, players_seated=4, max_seats=9)
        
        # Deploy to both
        bots = bot_manager.get_idle_bots()
        
        deployment1 = await manager._deploy_hive_team(table1, bots[:3])
        deployment2 = await manager._deploy_hive_team(table2, bots[3:6])
        
        # Verify
        assert deployment1.is_complete()
        assert deployment2.is_complete()
        assert len(manager.deployments) == 2
        assert len(manager.targeted_tables) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
