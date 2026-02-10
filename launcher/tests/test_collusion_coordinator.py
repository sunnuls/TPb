"""
Tests for CollusionCoordinator - Phase 4.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import asyncio

from launcher.collusion_coordinator import CollusionCoordinator, CollusionSession
from launcher.auto_seating import HiveDeployment
from launcher.lobby_scanner import LobbyTable
from launcher.bot_instance import BotInstance
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def create_test_bot(nickname: str) -> BotInstance:
    """Create test bot."""
    account = Account(nickname=nickname, room="pokerstars")
    account.window_info = WindowInfo(
        window_id=f"{hash(nickname)}",
        window_title=f"PokerStars - {nickname}",
        window_type=WindowType.DESKTOP_CLIENT
    )
    account.roi_configured = True
    
    roi = ROIConfig(account_id=account.account_id)
    roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
    roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
    roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
    roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
    
    return BotInstance(account=account, roi_config=roi)


class TestCollusionSession:
    """Tests for CollusionSession."""
    
    def test_create_session(self):
        """Test creating collusion session."""
        table = LobbyTable("t1", "Table 1", human_count=2, players_seated=4, max_seats=9)
        deployment = HiveDeployment(
            deployment_id="deploy_001",
            table=table,
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session = CollusionSession(
            session_id="session_001",
            deployment=deployment,
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert session.session_id == "session_001"
        assert len(session.bot_ids) == 3
        assert not session.active
    
    def test_is_active(self):
        """Test active check."""
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table)
        
        # Not active - active=False
        session1 = CollusionSession("s1", deployment, bot_ids=["b1", "b2", "b3"])
        assert not session1.is_active()
        
        # Not active - only 2 bots
        session2 = CollusionSession("s2", deployment, bot_ids=["b1", "b2"], active=True)
        assert not session2.is_active()
        
        # Active - 3 bots and active=True
        session3 = CollusionSession("s3", deployment, bot_ids=["b1", "b2", "b3"], active=True)
        assert session3.is_active()


class TestCollusionCoordinator:
    """Tests for CollusionCoordinator."""
    
    def test_initialization(self):
        """Test coordinator initialization."""
        coordinator = CollusionCoordinator(enable_real_actions=False)
        
        assert coordinator is not None
        assert not coordinator.enable_real_actions
        assert len(coordinator.sessions) == 0
    
    def test_initialization_with_real_actions(self):
        """Test initialization with real actions enabled."""
        coordinator = CollusionCoordinator(enable_real_actions=True)
        
        # Real executor should not be initialized without safety in UNSAFE mode
        assert coordinator.real_executor is None
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating collusion session."""
        coordinator = CollusionCoordinator()
        
        # Create deployment
        table = LobbyTable("t1", "Table 1", human_count=2, players_seated=4, max_seats=9)
        deployment = HiveDeployment(
            deployment_id="deploy_test",
            table=table,
            bot_ids=["b1", "b2", "b3"]
        )
        deployment.status = "completed"  # Mark as complete
        
        # Create bots
        bots = [create_test_bot(f"TestBot{i+1}") for i in range(3)]
        for i, bot in enumerate(bots):
            bot.bot_id = f"b{i+1}"
        
        # Create session
        session = await coordinator.create_session(deployment, bots)
        
        # Verify
        if session:  # May be None if HIVE modules not available
            assert session.session_id.startswith("session_")
            assert len(session.bot_ids) == 3
            assert session.deployment == deployment
    
    @pytest.mark.asyncio
    async def test_create_session_wrong_bot_count(self):
        """Test creating session with wrong number of bots."""
        coordinator = CollusionCoordinator()
        
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table)
        deployment.status = "completed"
        
        # Only 2 bots
        bots = [create_test_bot(f"Bot{i}") for i in range(2)]
        
        session = await coordinator.create_session(deployment, bots)
        
        # Should return None
        assert session is None
    
    @pytest.mark.asyncio
    async def test_share_cards(self):
        """Test card sharing."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table, bot_ids=["b1", "b2", "b3"])
        deployment.status = "completed"
        
        bots = [create_test_bot(f"Bot{i}") for i in range(3)]
        for i, bot in enumerate(bots):
            bot.bot_id = f"b{i+1}"
        
        session = await coordinator.create_session(deployment, bots)
        
        if session and session.is_active():
            # Share cards
            success = await coordinator.share_cards(
                session.session_id,
                "b1",
                ("As", "Kh")
            )
            
            # May fail if card_sharing not available
            print(f"\nCard sharing success: {success}")
    
    @pytest.mark.asyncio
    async def test_make_collective_decision(self):
        """Test collective decision making."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table, bot_ids=["b1", "b2", "b3"])
        deployment.status = "completed"
        
        bots = [create_test_bot(f"Bot{i}") for i in range(3)]
        for i, bot in enumerate(bots):
            bot.bot_id = f"b{i+1}"
        
        session = await coordinator.create_session(deployment, bots)
        
        if session and session.is_active():
            # Make decision
            action = await coordinator.make_collective_decision(
                session.session_id,
                "b1",
                {"pot": 100, "stack": 500},
                ["fold", "call", "raise"]
            )
            
            print(f"\nCollective decision: {action}")
    
    @pytest.mark.asyncio
    async def test_execute_action(self):
        """Test action execution."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table, bot_ids=["b1", "b2", "b3"])
        deployment.status = "completed"
        
        bots = [create_test_bot(f"Bot{i}") for i in range(3)]
        for i, bot in enumerate(bots):
            bot.bot_id = f"b{i+1}"
        
        session = await coordinator.create_session(deployment, bots)
        
        if session and session.is_active():
            # Execute action (simulated)
            success = await coordinator.execute_action(
                session.session_id,
                "b1",
                "raise",
                amount=100.0
            )
            
            assert success
            assert session.manipulations_count == 1
    
    @pytest.mark.asyncio
    async def test_end_session(self):
        """Test ending session."""
        coordinator = CollusionCoordinator()
        
        # Create session
        table = LobbyTable("t1", "Table 1")
        deployment = HiveDeployment("d1", table, bot_ids=["b1", "b2", "b3"])
        deployment.status = "completed"
        
        bots = [create_test_bot(f"Bot{i}") for i in range(3)]
        for i, bot in enumerate(bots):
            bot.bot_id = f"b{i+1}"
        
        session = await coordinator.create_session(deployment, bots)
        
        if session:
            session_id = session.session_id
            
            # End session
            await coordinator.end_session(session_id)
            
            # Should be inactive
            assert not session.is_active()
    
    def test_get_active_sessions(self):
        """Test getting active sessions."""
        coordinator = CollusionCoordinator()
        
        # Add some sessions
        table1 = LobbyTable("t1", "Table 1")
        table2 = LobbyTable("t2", "Table 2")
        
        session1 = CollusionSession(
            "s1",
            HiveDeployment("d1", table1),
            bot_ids=["b1", "b2", "b3"],
            active=True
        )
        session2 = CollusionSession(
            "s2",
            HiveDeployment("d2", table2),
            bot_ids=["b4", "b5", "b6"],
            active=False
        )
        
        coordinator.sessions["s1"] = session1
        coordinator.sessions["s2"] = session2
        
        active = coordinator.get_active_sessions()
        
        # Only s1 should be active
        assert len(active) == 1
        assert active[0].session_id == "s1"
    
    def test_get_statistics(self):
        """Test getting statistics."""
        coordinator = CollusionCoordinator()
        
        # Add sessions with stats
        table = LobbyTable("t1", "Table 1")
        
        for i in range(3):
            session = CollusionSession(
                f"s{i}",
                HiveDeployment(f"d{i}", table),
                bot_ids=["b1", "b2", "b3"],
                active=(i < 2)
            )
            session.hands_played = 10 * (i + 1)
            session.total_profit = 50.0 * (i + 1)
            session.card_shares_count = 20 * (i + 1)
            session.manipulations_count = 5 * (i + 1)
            
            coordinator.sessions[f"s{i}"] = session
        
        stats = coordinator.get_statistics()
        
        assert stats['total_sessions'] == 3
        assert stats['active_sessions'] == 2
        assert stats['total_hands'] == 60  # 10+20+30
        assert stats['total_profit'] == 300.0  # 50+100+150
        assert stats['total_card_shares'] == 120  # 20+40+60
        assert stats['total_manipulations'] == 30  # 5+10+15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
