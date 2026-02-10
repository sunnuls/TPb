"""
Tests for Realtime Coordinator (Roadmap5 Phase 3).

⚠️ EDUCATIONAL RESEARCH ONLY - Tests real-time manipulation coordination.
"""

import pytest

from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
from hive.bot_pool import BotPool
from hive.card_sharing import CardSharingSystem
from hive.collusion_activation import CollusionActivator
from hive.manipulation_logic import ManipulationContext, ManipulationEngine
from hive.realtime_coordinator import CoordinationSession, CoordinationStatus, RealtimeCoordinator
from sim_engine.collective_decision import CollectiveState


class TestCoordinationSession:
    """Test coordination session."""
    
    def test_creation(self):
        """Test session creation."""
        session = CoordinationSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert session.team_id == "team_1"
        assert len(session.bot_ids) == 3
        assert session.status == CoordinationStatus.INACTIVE
    
    def test_record_action(self):
        """Test action recording."""
        session = CoordinationSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.record_action()
        session.record_action()
        
        assert session.actions_executed == 2
    
    def test_record_manipulation(self):
        """Test manipulation recording."""
        session = CoordinationSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.record_manipulation()
        
        assert session.manipulation_decisions == 1
    
    def test_record_error(self):
        """Test error recording."""
        session = CoordinationSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.record_error()
        
        assert session.errors == 1


class TestRealtimeCoordinator:
    """Test realtime coordinator."""
    
    def test_initialization_safe_mode(self):
        """Test initialization in safe mode."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.SAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion
        )
        
        assert coordinator.safety == safety
        assert coordinator.real_executor is None  # Not available in safe mode
    
    def test_initialization_unsafe_mode(self):
        """Test initialization in unsafe mode."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.UNSAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion
        )
        
        # May be None if pyautogui not available
        # Just check it doesn't crash
        assert coordinator is not None
    
    def test_start_session_requires_unsafe(self):
        """Test session start requires unsafe mode."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.SAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion
        )
        
        # Should fail (not unsafe mode)
        started = coordinator.start_session(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert started is False
    
    def test_start_session_requires_confirmation(self):
        """Test session start requires confirmation."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.UNSAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion,
            require_confirmation=True
        )
        
        # Should fail (requires confirmation)
        started = coordinator.start_session(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert started is False
    
    def test_start_session_no_confirmation(self):
        """Test session start without confirmation."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.UNSAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion,
            require_confirmation=False
        )
        
        # Should succeed
        started = coordinator.start_session(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert started is True
        assert "team_1" in coordinator.sessions
    
    def test_stop_session(self):
        """Test session stop."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.UNSAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion,
            require_confirmation=False
        )
        
        # Start session
        coordinator.start_session(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        # Stop
        stopped = coordinator.stop_session("team_1")
        
        assert stopped is True
        assert "team_1" not in coordinator.sessions
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        safety = SafetyFramework(SafetyConfig(mode=SafetyMode.SAFE))
        manipulation = ManipulationEngine()
        card_sharing = CardSharingSystem()
        bot_pool = BotPool(group_hash="test", pool_size=10)
        collusion = CollusionActivator(
            bot_pool=bot_pool,
            card_sharing=card_sharing
        )
        
        coordinator = RealtimeCoordinator(
            safety=safety,
            manipulation_engine=manipulation,
            card_sharing=card_sharing,
            collusion_activator=collusion
        )
        
        stats = coordinator.get_statistics()
        
        assert 'active_sessions' in stats
        assert 'total_actions_executed' in stats
        assert 'unsafe_mode' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
