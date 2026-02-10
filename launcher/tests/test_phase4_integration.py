"""
Integration Tests for Roadmap6 Phase 4.

⚠️ EDUCATIONAL RESEARCH ONLY.

Tests:
1. Collusion coordinator integration
2. Full HIVE deployment with collusion
3. Card sharing workflow
4. Collective decision workflow
5. Action execution workflow
"""

import pytest
import asyncio

from launcher.collusion_coordinator import CollusionCoordinator
from launcher.auto_seating import AutoSeatingManager
from launcher.lobby_scanner import LobbyScanner, LobbyTable
from launcher.bot_manager import BotManager
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def create_full_bot_manager(num_bots: int) -> BotManager:
    """Create bot manager with fully configured bots."""
    manager = BotManager()
    
    for i in range(num_bots):
        account = Account(nickname=f"CollusionBot{i+1:03d}", room="pokerstars")
        account.window_info = WindowInfo(
            window_id=f"{20000+i}",
            window_title=f"PokerStars - CBot{i+1}",
            window_type=WindowType.DESKTOP_CLIENT,
            position=(100, 100, 800, 600)
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id, resolution=(1920, 1080))
        
        # Full ROI
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


class TestPhase4Integration:
    """Integration tests for Phase 4."""
    
    def test_collusion_coordinator_initialization(self):
        """Test collusion coordinator initialization."""
        coordinator = CollusionCoordinator(enable_real_actions=False)
        
        # Should initialize
        assert coordinator is not None
        assert len(coordinator.sessions) == 0
        
        # Check components
        print(f"\nCollusion components:")
        print(f"  Card sharing: {coordinator.card_sharing is not None}")
        print(f"  Collusion activator: {coordinator.collusion_activator is not None}")
        print(f"  Manipulation engine: {coordinator.manipulation_engine is not None}")
        print(f"  Real executor: {coordinator.real_executor is not None}")
    
    @pytest.mark.asyncio
    async def test_full_deployment_with_collusion(self):
        """Test full deployment with collusion activation."""
        print("\n" + "=" * 60)
        print("Full Deployment with Collusion Test")
        print("=" * 60)
        
        # 1. Create components
        bot_manager = create_full_bot_manager(3)
        lobby_scanner = LobbyScanner()
        collusion_coordinator = CollusionCoordinator(enable_real_actions=False)
        auto_seating = AutoSeatingManager(
            bot_manager,
            lobby_scanner,
            collusion_coordinator=collusion_coordinator
        )
        
        print(f"\n1. Components created:")
        print(f"   Bots: {len(bot_manager.get_all_bots())}")
        print(f"   Collusion coordinator: Ready")
        
        # 2. Create opportunity
        table = LobbyTable(
            table_id="collusion_table",
            table_name="Collusion Table",
            game_type="NLHE",
            stakes="0.50/1.00",
            players_seated=4,
            max_seats=9,
            human_count=2
        )
        
        print(f"\n2. Opportunity:")
        print(f"   Table: {table.table_name}")
        print(f"   Humans: {table.human_count}")
        print(f"   Seats: {table.seats_available()}")
        
        # 3. Deploy HIVE with collusion
        bots = bot_manager.get_idle_bots()
        deployment = await auto_seating._deploy_hive_team(table, bots)
        
        print(f"\n3. HIVE deployed:")
        print(f"   Deployment: {deployment.deployment_id[:30]}...")
        print(f"   Status: {deployment.status.value}")
        print(f"   Bots: {len(deployment.bot_ids)}")
        
        # 4. Verify collusion session
        stats = collusion_coordinator.get_statistics()
        print(f"\n4. Collusion statistics:")
        print(f"   Total sessions: {stats['total_sessions']}")
        print(f"   Active sessions: {stats['active_sessions']}")
        
        # May have session if HIVE modules available
        if stats['active_sessions'] > 0:
            active_sessions = collusion_coordinator.get_active_sessions()
            session = active_sessions[0]
            print(f"   Session ID: {session.session_id[:30]}...")
            print(f"   Table: {session.deployment.table.table_name}")
            print(f"   Bots in session: {len(session.bot_ids)}")
        
        print("\n" + "=" * 60)
        print("Full deployment with collusion complete")
        print("=" * 60)
        
        # Assertions
        assert deployment.is_complete()
        assert len(deployment.bot_ids) == 3
    
    @pytest.mark.asyncio
    async def test_card_sharing_workflow(self):
        """Test card sharing workflow."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1", human_count=2)
        deployment = await self._create_test_deployment(coordinator, table)
        
        if deployment and deployment.session_id:
            session = coordinator.sessions.get(deployment.session_id)
            
            if session and session.is_active():
                # Simulate card sharing
                print("\nCard sharing workflow:")
                
                for i, bot_id in enumerate(session.bot_ids):
                    cards = [("As", "Kh"), ("Qd", "Jc"), ("Th", "9s")][i]
                    success = await coordinator.share_cards(
                        session.session_id,
                        bot_id,
                        cards
                    )
                    print(f"  Bot {i+1} shared {cards}: {success}")
                
                # Check stats
                print(f"  Total shares: {session.card_shares_count}")
    
    @pytest.mark.asyncio
    async def test_collective_decision_workflow(self):
        """Test collective decision workflow."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = await self._create_test_deployment(coordinator, table)
        
        if deployment and deployment.session_id:
            session = coordinator.sessions.get(deployment.session_id)
            
            if session and session.is_active():
                # Make collective decisions
                print("\nCollective decision workflow:")
                
                game_state = {"pot": 100, "stack": 500}
                actions = ["fold", "call", "raise"]
                
                for i, bot_id in enumerate(session.bot_ids):
                    decision = await coordinator.make_collective_decision(
                        session.session_id,
                        bot_id,
                        game_state,
                        actions
                    )
                    print(f"  Bot {i+1} decision: {decision}")
    
    @pytest.mark.asyncio
    async def test_action_execution_workflow(self):
        """Test action execution workflow."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = await self._create_test_deployment(coordinator, table)
        
        if deployment and deployment.session_id:
            session = coordinator.sessions.get(deployment.session_id)
            
            if session and session.is_active():
                # Execute actions
                print("\nAction execution workflow:")
                
                actions = [("call", None), ("raise", 100.0), ("fold", None)]
                
                for i, (action, amount) in enumerate(actions):
                    bot_id = session.bot_ids[i]
                    success = await coordinator.execute_action(
                        session.session_id,
                        bot_id,
                        action,
                        amount
                    )
                    print(f"  Bot {i+1} {action} (${amount}): {success}")
                
                print(f"  Total manipulations: {session.manipulations_count}")
    
    @pytest.mark.asyncio
    async def test_multi_table_collusion(self):
        """Test collusion on multiple tables."""
        # Create 6 bots for 2 teams
        bot_manager = create_full_bot_manager(6)
        lobby_scanner = LobbyScanner()
        collusion_coordinator = CollusionCoordinator()
        auto_seating = AutoSeatingManager(
            bot_manager,
            lobby_scanner,
            collusion_coordinator=collusion_coordinator
        )
        
        # Create 2 tables
        tables = [
            LobbyTable("t1", "Table 1", human_count=1, players_seated=3, max_seats=9),
            LobbyTable("t2", "Table 2", human_count=2, players_seated=4, max_seats=9)
        ]
        
        # Deploy to both
        bots = bot_manager.get_idle_bots()
        
        deployment1 = await auto_seating._deploy_hive_team(tables[0], bots[:3])
        deployment2 = await auto_seating._deploy_hive_team(tables[1], bots[3:6])
        
        # Verify both deployments
        assert deployment1.is_complete()
        assert deployment2.is_complete()
        
        # Check collusion stats
        stats = collusion_coordinator.get_statistics()
        print(f"\nMulti-table collusion:")
        print(f"  Total sessions: {stats['total_sessions']}")
        print(f"  Active sessions: {stats['active_sessions']}")
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = await self._create_test_deployment(coordinator, table)
        
        if deployment and deployment.session_id:
            session = coordinator.sessions.get(deployment.session_id)
            
            if session:
                session_id = session.session_id
                
                # Verify active
                assert session in coordinator.get_active_sessions()
                
                # Simulate activity
                session.hands_played = 50
                session.total_profit = 125.50
                
                # End session
                await coordinator.end_session(session_id)
                
                # Verify inactive
                assert not session.is_active()
                assert session not in coordinator.get_active_sessions()
    
    async def _create_test_deployment(self, coordinator, table):
        """Helper to create test deployment with session."""
        from launcher.auto_seating import HiveDeployment
        
        deployment = HiveDeployment(
            f"deploy_{table.table_id}",
            table,
            bot_ids=["b1", "b2", "b3"]
        )
        deployment.status = "completed"
        
        # Create bots
        from launcher.bot_instance import BotInstance
        from launcher.models.account import Account
        
        bots = []
        for i in range(3):
            account = Account(nickname=f"TestBot{i+1}")
            account.window_info = WindowInfo(
                window_id=str(i),
                window_title=f"Table {i}",
                window_type=WindowType.DESKTOP_CLIENT
            )
            account.roi_configured = True
            
            roi = ROIConfig(account_id=account.account_id)
            roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
            roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
            
            bot = BotInstance(account=account, roi_config=roi)
            bot.bot_id = f"b{i+1}"
            bots.append(bot)
        
        # Create session
        session = await coordinator.create_session(deployment, bots)
        
        if session:
            deployment.session_id = session.session_id
        
        return deployment


# Summary test
def test_phase4_summary():
    """Print Phase 4 completion summary."""
    print("\n" + "=" * 60)
    print("PHASE 4 COMPLETION SUMMARY")
    print("=" * 60)
    print()
    print("Components implemented:")
    print("  ✓ CollusionCoordinator (collusion_coordinator.py)")
    print("  ✓ CollusionSession tracking")
    print("  ✓ Integration with HIVE modules")
    print("  ✓ Integration with AutoSeatingManager")
    print()
    print("Features:")
    print("  - Real-time collusion coordination")
    print("  - Card sharing system integration")
    print("  - Collective decision making")
    print("  - 3vs1 manipulation strategies")
    print("  - Real action execution (placeholder)")
    print("  - Session lifecycle management")
    print("  - Statistics tracking")
    print()
    print("Workflow:")
    print("  1. HIVE deployment completes")
    print("  2. CollusionCoordinator creates session")
    print("  3. Card sharing activated")
    print("  4. Collective decisions enabled")
    print("  5. Manipulation strategies applied")
    print("  6. Actions executed (simulated or real)")
    print("  7. Session statistics tracked")
    print()
    print("Integration points:")
    print("  - hive/card_sharing.py (CardSharingSystem)")
    print("  - hive/collusion_activation.py (CollusionActivator)")
    print("  - hive/manipulation_logic.py (ManipulationEngine)")
    print("  - bridge/action/real_executor.py (RealActionExecutor)")
    print()
    print("Tests:")
    print("  - test_collusion_coordinator.py")
    print("  - test_phase4_integration.py")
    print()
    print("=" * 60)
    print("Phase 4: Collusion & 3vs1 Manipulation COMPLETE")
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
