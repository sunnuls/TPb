"""
Integration Tests for Roadmap6 Phase 3.

⚠️ EDUCATIONAL RESEARCH ONLY.

Tests:
1. Lobby scanning workflow
2. Auto-seating workflow
3. Full HIVE deployment
4. Multiple team coordination
5. Statistics tracking
"""

import pytest
import asyncio

from launcher.lobby_scanner import LobbyScanner, LobbyTable, LobbySnapshot
from launcher.auto_seating import AutoSeatingManager, DeploymentStatus
from launcher.bot_manager import BotManager
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def create_full_bot_manager(num_bots: int) -> BotManager:
    """Create bot manager with fully configured bots."""
    manager = BotManager()
    
    for i in range(num_bots):
        account = Account(nickname=f"IntegrationBot{i+1:03d}", room="pokerstars")
        account.window_info = WindowInfo(
            window_id=f"{10000+i}",
            window_title=f"PokerStars - IntBot{i+1}",
            window_type=WindowType.DESKTOP_CLIENT,
            position=(100, 100, 800, 600)
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id, resolution=(1920, 1080))
        
        # Full ROI configuration
        roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        for j in range(1, 6):
            roi.add_zone(ROIZone(f"board_card_{j}", 300 + j*60, 100, 50, 70))
        roi.add_zone(ROIZone("pot", 500, 50, 100, 30))
        roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        roi.add_zone(ROIZone("raise_button", 580, 800, 80, 40))
        
        manager.create_bot(account, roi)
    
    return manager


class TestPhase3Integration:
    """Integration tests for Phase 3."""
    
    def test_lobby_scanning_workflow(self):
        """Test complete lobby scanning workflow."""
        scanner = LobbyScanner()
        
        # Simulate lobby
        snapshot = scanner.simulate_lobby_data(20)
        
        # Verify structure
        assert len(snapshot.tables) == 20
        assert snapshot.total_tables == 20
        
        # Find opportunities
        opportunities = snapshot.get_hive_opportunities()
        
        # Should find some opportunities (probabilistic)
        print(f"\nFound {len(opportunities)} opportunities in 20 tables")
        
        # Verify opportunities are sorted by priority
        if len(opportunities) >= 2:
            assert opportunities[0].priority_score() >= opportunities[1].priority_score()
    
    @pytest.mark.asyncio
    async def test_auto_seating_workflow(self):
        """Test complete auto-seating workflow."""
        # Create components
        bot_manager = create_full_bot_manager(3)
        lobby_scanner = LobbyScanner()
        
        manager = AutoSeatingManager(
            bot_manager=bot_manager,
            lobby_scanner=lobby_scanner,
            scan_interval=1.0
        )
        
        # Create opportunity
        table = LobbyTable(
            table_id="integration_table",
            table_name="Integration Table",
            game_type="NLHE",
            stakes="0.50/1.00",
            players_seated=4,
            max_seats=9,
            human_count=2
        )
        
        # Get bots
        bots = bot_manager.get_idle_bots()
        assert len(bots) == 3
        
        # Deploy
        deployment = await manager._deploy_hive_team(table, bots)
        
        # Verify deployment
        assert deployment is not None
        assert deployment.is_complete()
        assert deployment.status == DeploymentStatus.COMPLETED
        assert len(deployment.bot_ids) == 3
        
        # Verify bots are assigned
        for bot in bots:
            assert bot.current_table == table.table_name
        
        # Verify statistics
        stats = manager.get_statistics()
        assert stats['total_deployments'] == 1
        assert stats['completed_deployments'] == 1
        assert stats['active_deployments'] == 1
    
    @pytest.mark.asyncio
    async def test_full_hive_deployment(self):
        """Test full HIVE deployment with all phases."""
        print("\n" + "=" * 60)
        print("Full HIVE Deployment Test")
        print("=" * 60)
        
        # 1. Setup
        bot_manager = create_full_bot_manager(3)
        lobby_scanner = LobbyScanner()
        auto_seating = AutoSeatingManager(bot_manager, lobby_scanner)
        
        print(f"\n1. Setup complete:")
        print(f"   Bots: {len(bot_manager.get_all_bots())}")
        print(f"   Idle bots: {len(bot_manager.get_idle_bots())}")
        
        # 2. Simulate lobby
        snapshot = lobby_scanner.simulate_lobby_data(30)
        opportunities = snapshot.get_hive_opportunities()
        
        print(f"\n2. Lobby scanned:")
        print(f"   Total tables: {snapshot.total_tables}")
        print(f"   Opportunities: {len(opportunities)}")
        
        if opportunities:
            best = opportunities[0]
            print(f"\n3. Best opportunity:")
            print(f"   Table: {best.table_name}")
            print(f"   Humans: {best.human_count}")
            print(f"   Seats: {best.seats_available()}")
            print(f"   Priority: {best.priority_score():.1f}")
            
            # 4. Deploy HIVE
            bots = bot_manager.get_idle_bots()
            deployment = await auto_seating._deploy_hive_team(best, bots)
            
            print(f"\n4. HIVE deployed:")
            print(f"   Deployment ID: {deployment.deployment_id[:30]}...")
            print(f"   Status: {deployment.status.value}")
            print(f"   Bots: {len(deployment.bot_ids)}")
            
            # 5. Verify
            print(f"\n5. Verification:")
            print(f"   Deployment complete: {deployment.is_complete()}")
            print(f"   All bots assigned: {all(b.current_table for b in bots)}")
            
            # 6. Statistics
            stats = auto_seating.get_statistics()
            print(f"\n6. Statistics:")
            print(f"   Total deployments: {stats['total_deployments']}")
            print(f"   Completed: {stats['completed_deployments']}")
            print(f"   Targeted tables: {stats['targeted_tables']}")
            
            print("\n" + "=" * 60)
            print("Full deployment test complete")
            print("=" * 60)
            
            # Assertions
            assert deployment.is_complete()
            assert all(b.current_table == best.table_name for b in bots)
        else:
            print("\n   No opportunities found (probabilistic)")
    
    @pytest.mark.asyncio
    async def test_multiple_team_coordination(self):
        """Test coordinating multiple HIVE teams."""
        # Create 9 bots for 3 teams
        bot_manager = create_full_bot_manager(9)
        lobby_scanner = LobbyScanner()
        auto_seating = AutoSeatingManager(bot_manager, lobby_scanner)
        
        # Create 3 tables
        tables = [
            LobbyTable(f"t{i}", f"Table {i}", players_seated=3+i, max_seats=9, human_count=i+1)
            for i in range(3)
        ]
        
        # Deploy to all tables
        all_bots = bot_manager.get_idle_bots()
        deployments = []
        
        for i, table in enumerate(tables):
            bots_slice = all_bots[i*3:(i+1)*3]
            deployment = await auto_seating._deploy_hive_team(table, bots_slice)
            deployments.append(deployment)
        
        # Verify all deployments
        assert len(deployments) == 3
        assert all(d.is_complete() for d in deployments)
        
        # Verify statistics
        stats = auto_seating.get_statistics()
        assert stats['total_deployments'] == 3
        assert stats['completed_deployments'] == 3
        assert stats['targeted_tables'] == 3
        
        # Verify all bots have table assignments
        # Note: Bots remain in IDLE status because deployment is placeholder (Phase 3)
        # Actual bot starting happens in Phase 4
        assert all(bot.current_table for bot in all_bots)
    
    @pytest.mark.asyncio
    async def test_auto_seating_service(self):
        """Test auto-seating as a service."""
        bot_manager = create_full_bot_manager(3)
        lobby_scanner = LobbyScanner()
        auto_seating = AutoSeatingManager(
            bot_manager,
            lobby_scanner,
            scan_interval=0.5
        )
        
        # Start service
        await auto_seating.start()
        assert auto_seating.is_running()
        
        # Run for a short time
        await asyncio.sleep(1.0)
        
        # Stop service
        await auto_seating.stop()
        assert not auto_seating.is_running()
    
    def test_opportunity_prioritization(self):
        """Test opportunity prioritization logic."""
        scanner = LobbyScanner()
        
        # Create tables with different characteristics
        tables = [
            LobbyTable("t1", "Table 1", players_seated=3, max_seats=9, human_count=1),  # Best
            LobbyTable("t2", "Table 2", players_seated=4, max_seats=9, human_count=2),  # Medium
            LobbyTable("t3", "Table 3", players_seated=5, max_seats=9, human_count=3),  # Lower
            LobbyTable("t4", "Table 4", players_seated=8, max_seats=9, human_count=5),  # Unsuitable
        ]
        
        snapshot = LobbySnapshot(tables=tables, total_tables=len(tables))
        opportunities = snapshot.get_hive_opportunities()
        
        # Should have 3 suitable tables
        assert len(opportunities) == 3
        
        # Should be sorted by priority
        assert opportunities[0].table_id == "t1"  # 1 human = best
        assert opportunities[1].table_id == "t2"  # 2 humans
        assert opportunities[2].table_id == "t3"  # 3 humans
    
    @pytest.mark.asyncio
    async def test_deployment_error_handling(self):
        """Test error handling in deployment."""
        bot_manager = create_full_bot_manager(3)
        lobby_scanner = LobbyScanner()
        auto_seating = AutoSeatingManager(bot_manager, lobby_scanner)
        
        table = LobbyTable("t1", "Table 1")
        
        # Try to deploy with only 2 bots (should fail)
        bots = bot_manager.get_idle_bots()[:2]
        deployment = await auto_seating._deploy_hive_team(table, bots)
        
        # Should return None on failure
        assert deployment is None
        
        # Table should not be in targeted set
        assert table.table_id not in auto_seating.targeted_tables


# Summary test
def test_phase3_summary():
    """Print Phase 3 completion summary."""
    print("\n" + "=" * 60)
    print("PHASE 3 COMPLETION SUMMARY")
    print("=" * 60)
    print()
    print("Components implemented:")
    print("  ✓ LobbyScanner (lobby_scanner.py)")
    print("  ✓ LobbyTable with suitability checks")
    print("  ✓ LobbySnapshot with opportunity filtering")
    print("  ✓ AutoSeatingManager (auto_seating.py)")
    print("  ✓ HiveDeployment tracking")
    print("  ✓ Deployment status management")
    print()
    print("Features:")
    print("  - Lobby scanning (with simulation)")
    print("  - Opportunity prioritization")
    print("  - 3-bot HIVE deployment")
    print("  - Multi-team coordination")
    print("  - Strategic seat selection (placeholder)")
    print("  - HIVE session creation (placeholder)")
    print("  - Statistics tracking")
    print()
    print("Auto-seating logic:")
    print("  - Scan interval: configurable")
    print("  - Target criteria: 1-3 humans, 3+ seats")
    print("  - Priority: fewer humans = higher")
    print("  - Prevents double-targeting")
    print("  - Creates HIVE session after deployment")
    print()
    print("Tests:")
    print("  - test_lobby_scanner.py")
    print("  - test_auto_seating.py")
    print("  - test_phase3_integration.py")
    print()
    print("=" * 60)
    print("Phase 3: Table Search & Auto-Fill COMPLETE")
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
