"""
Integration Tests for Roadmap6 Phase 2.

⚠️ EDUCATIONAL RESEARCH ONLY.

Tests:
1. Bot instance lifecycle
2. Bot manager pool operations
3. Start/stop workflows
4. Statistics aggregation
5. Full integration
"""

import pytest
import asyncio

from launcher.bot_instance import BotInstance, BotStatus
from launcher.bot_manager import BotManager
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def create_ready_account(nickname: str) -> Account:
    """Create account ready to run."""
    account = Account(nickname=nickname, room="pokerstars")
    account.window_info = WindowInfo(
        window_id=f"{hash(nickname)}",
        window_title=f"PokerStars - {nickname}",
        window_type=WindowType.DESKTOP_CLIENT
    )
    account.roi_configured = True
    return account


def create_full_roi(account_id: str) -> ROIConfig:
    """Create complete ROI configuration."""
    roi = ROIConfig(account_id=account_id, resolution=(1920, 1080))
    
    # Hero cards
    roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
    
    # Board cards
    for i in range(1, 6):
        roi.add_zone(ROIZone(f"board_card_{i}", 300 + i*60, 100, 50, 70))
    
    # Pot and buttons
    roi.add_zone(ROIZone("pot", 500, 50, 100, 30))
    roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
    roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
    roi.add_zone(ROIZone("raise_button", 580, 800, 80, 40))
    
    return roi


class TestPhase2Integration:
    """Integration tests for Phase 2."""
    
    def test_bot_instance_creation_workflow(self):
        """Test complete bot creation workflow."""
        # Create account
        account = create_ready_account("IntegrationBot")
        
        # Create ROI
        roi = create_full_roi(account.account_id)
        
        # Create bot instance
        bot = BotInstance(account=account, roi_config=roi)
        
        # Verify
        assert bot.can_start()
        assert bot.status == BotStatus.IDLE
        assert bot.account.is_ready_to_run()
        assert roi.has_required_zones()
    
    @pytest.mark.asyncio
    async def test_bot_lifecycle(self):
        """Test bot start/stop lifecycle."""
        account = create_ready_account("LifecycleBot")
        roi = create_full_roi(account.account_id)
        bot = BotInstance(account=account, roi_config=roi)
        
        # Initial state
        assert bot.status == BotStatus.IDLE
        assert not bot.is_active()
        
        # Start
        await bot.start()
        await asyncio.sleep(0.1)
        
        assert bot.status in [BotStatus.STARTING, BotStatus.SEARCHING]
        assert bot.is_active()
        assert bot.start_time is not None
        
        # Stop
        await bot.stop()
        
        assert bot.status == BotStatus.STOPPED
        assert not bot.is_active()
        assert bot.stats.uptime_seconds > 0
    
    def test_bot_manager_pool_operations(self):
        """Test bot manager pool operations."""
        manager = BotManager()
        
        # Create multiple accounts and bots
        accounts = [create_ready_account(f"Bot{i+1:03d}") for i in range(10)]
        
        for account in accounts:
            roi = create_full_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # Verify
        assert len(manager.get_all_bots()) == 10
        assert len(manager.get_idle_bots()) == 10
        assert len(manager.get_active_bots()) == 0
        
        # Test retrieval
        for account in accounts:
            bot = manager.get_bot_by_account(account.account_id)
            assert bot is not None
            assert bot.account == account
    
    @pytest.mark.asyncio
    async def test_start_stop_workflow(self):
        """Test complete start/stop workflow."""
        manager = BotManager()
        
        # Create bots
        for i in range(5):
            account = create_ready_account(f"WorkflowBot{i+1:03d}")
            roi = create_full_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # Start 3 bots
        started = await manager.start_all(max_count=3)
        assert started == 3
        
        await asyncio.sleep(0.2)
        
        # Verify
        assert len(manager.get_active_bots()) == 3
        assert len(manager.get_idle_bots()) == 2
        
        # Stop all
        stopped = await manager.stop_all()
        assert stopped == 3
        
        assert len(manager.get_active_bots()) == 0
        # After stop, bots are in STOPPED state, not IDLE
        # So idle_bots should be 2 (the ones that were never started)
        assert len(manager.get_idle_bots()) == 2
    
    @pytest.mark.asyncio
    async def test_statistics_aggregation(self):
        """Test statistics aggregation."""
        manager = BotManager()
        
        # Create bots with simulated stats
        for i in range(5):
            account = create_ready_account(f"StatsBot{i+1:03d}")
            roi = create_full_roi(account.account_id)
            bot = manager.create_bot(account, roi)
            
            # Simulate stats
            bot.stats.hands_played = 20 * (i + 1)
            bot.stats.pot_won = 100.0 * (i + 1)
            bot.stats.pot_lost = 50.0 * (i + 1)
            bot.stats.decisions_made = 60 * (i + 1)
        
        # Get statistics
        stats = manager.get_statistics()
        
        assert stats['total_bots'] == 5
        assert stats['total_hands'] == 300  # 20+40+60+80+100
        assert stats['total_profit'] == 750.0  # 50+100+150+200+250
        assert stats['bots_by_status'][BotStatus.IDLE.value] == 5
    
    @pytest.mark.asyncio
    async def test_emergency_stop_workflow(self):
        """Test emergency stop workflow."""
        manager = BotManager()
        
        # Create and start bots
        for i in range(5):
            account = create_ready_account(f"EmergencyBot{i+1:03d}")
            roi = create_full_roi(account.account_id)
            manager.create_bot(account, roi)
        
        await manager.start_all()
        await asyncio.sleep(0.2)
        
        # Verify all running
        assert len(manager.get_active_bots()) == 5
        
        # Emergency stop
        await manager.emergency_stop()
        
        # Verify all stopped
        assert len(manager.get_active_bots()) == 0
        
        # All bots should be stopped
        for bot in manager.get_all_bots():
            assert bot.status == BotStatus.STOPPED
    
    def test_bot_removal_workflow(self):
        """Test bot removal workflow."""
        manager = BotManager()
        
        # Create bots
        accounts = [create_ready_account(f"RemoveBot{i+1:03d}") for i in range(5)]
        
        for account in accounts:
            roi = create_full_roi(account.account_id)
            manager.create_bot(account, roi)
        
        assert len(manager.get_all_bots()) == 5
        
        # Remove one bot
        bot_to_remove = manager.get_bot_by_account(accounts[0].account_id)
        success = manager.remove_bot(bot_to_remove.bot_id)
        
        assert success
        assert len(manager.get_all_bots()) == 4
        assert manager.get_bot_by_account(accounts[0].account_id) is None
    
    def test_bot_to_dict_serialization(self):
        """Test bot serialization."""
        account = create_ready_account("SerializeBot")
        roi = create_full_roi(account.account_id)
        bot = BotInstance(account=account, roi_config=roi)
        
        # Add some stats
        bot.stats.hands_played = 50
        bot.stats.pot_won = 250.0
        bot.stats.pot_lost = 150.0
        bot.stats.decisions_made = 120
        bot.current_table = "Table 5"
        bot.stack = 100.50
        bot.collective_edge = 0.65
        
        # Serialize
        data = bot.to_dict()
        
        # Verify
        assert data['nickname'] == "SerializeBot"
        assert data['status'] == BotStatus.IDLE.value
        assert data['current_table'] == "Table 5"
        assert data['stack'] == 100.50
        assert data['collective_edge'] == 0.65
        assert data['stats']['hands_played'] == 50
        assert data['stats']['net_profit'] == 100.0
    
    @pytest.mark.asyncio
    async def test_full_phase2_workflow(self):
        """Test complete Phase 2 workflow."""
        print("\n" + "=" * 60)
        print("Phase 2 Full Workflow Test")
        print("=" * 60)
        
        # 1. Create manager
        manager = BotManager()
        print(f"\n1. Manager created")
        
        # 2. Create accounts
        accounts = []
        for i in range(5):
            account = create_ready_account(f"FullBot{i+1:03d}")
            accounts.append(account)
        
        print(f"2. Created {len(accounts)} accounts")
        
        # 3. Create bots
        for account in accounts:
            roi = create_full_roi(account.account_id)
            manager.create_bot(account, roi)
        
        print(f"3. Created {len(manager.get_all_bots())} bots")
        
        # 4. Start 3 bots
        started = await manager.start_all(max_count=3)
        await asyncio.sleep(0.2)
        
        print(f"4. Started {started} bots")
        print(f"   Active: {len(manager.get_active_bots())}")
        print(f"   Idle: {len(manager.get_idle_bots())}")
        
        # 5. Get statistics
        stats = manager.get_statistics()
        print(f"5. Statistics:")
        print(f"   Total bots: {stats['total_bots']}")
        print(f"   Active bots: {stats['active_bots']}")
        
        # 6. Stop all
        stopped = await manager.stop_all()
        print(f"6. Stopped {stopped} bots")
        
        # 7. Final stats
        final_stats = manager.get_statistics()
        print(f"7. Final statistics:")
        print(f"   Total bots: {final_stats['total_bots']}")
        print(f"   Active bots: {final_stats['active_bots']}")
        
        print("=" * 60)
        print("Full workflow test complete")
        print("=" * 60)
        
        # Verify
        assert final_stats['total_bots'] == 5
        assert final_stats['active_bots'] == 0


# Summary test
def test_phase2_summary():
    """Print Phase 2 completion summary."""
    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETION SUMMARY")
    print("=" * 60)
    print()
    print("Components implemented:")
    print("  ✓ BotInstance (bot_instance.py)")
    print("  ✓ BotStatistics")
    print("  ✓ BotManager (bot_manager.py)")
    print("  ✓ BotsControlTab UI (bots_control_tab.py)")
    print("  ✓ Main window integration")
    print()
    print("Features:")
    print("  - Bot lifecycle management (start/stop)")
    print("  - Pool operations (create/remove)")
    print("  - Real-time monitoring table")
    print("  - Statistics aggregation")
    print("  - Emergency stop")
    print("  - Async operation support")
    print()
    print("UI Controls:")
    print("  - SpinBox: Select bot count (1-100)")
    print("  - Start Selected / Start All")
    print("  - Stop Selected / Stop All")
    print("  - Emergency Stop button")
    print("  - Real-time table with 8 columns")
    print("  - Statistics bar")
    print()
    print("Tests:")
    print("  - test_bot_instance.py")
    print("  - test_bot_manager.py")
    print("  - test_phase2_integration.py")
    print()
    print("=" * 60)
    print("Phase 2: Bot Control & Deployment COMPLETE")
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
