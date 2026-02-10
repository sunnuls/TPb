"""
Tests for Collusion Activation (Roadmap5 Phase 2).

⚠️ EDUCATIONAL RESEARCH ONLY - Tests COLLUSION activation.
"""

import pytest

from hive.bot_pool import BotPool
from hive.card_sharing import CardSharingSystem
from hive.collusion_activation import (
    CollusionActivator,
    CollusionMode,
    CollusionSession,
)


class TestCollusionSession:
    """Test collusion session."""
    
    def test_creation(self):
        """Test session creation."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert session.team_id == "team_1"
        assert len(session.bot_ids) == 3
        assert session.mode == CollusionMode.PENDING
    
    def test_activate(self):
        """Test activation."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.activate()
        
        assert session.mode == CollusionMode.ACTIVE
        assert session.activation_time is not None
    
    def test_suspend(self):
        """Test suspension."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.activate()
        session.suspend()
        
        assert session.mode == CollusionMode.SUSPENDED
    
    def test_deactivate(self):
        """Test deactivation."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.activate()
        session.deactivate()
        
        assert session.mode == CollusionMode.INACTIVE
    
    def test_is_active(self):
        """Test active check."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        assert session.is_active() is False
        
        session.activate()
        assert session.is_active() is True
        
        session.deactivate()
        assert session.is_active() is False
    
    def test_record_hand(self):
        """Test hand recording."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.record_hand()
        session.record_hand()
        
        assert session.hands_played == 2
    
    def test_record_share(self):
        """Test share recording."""
        session = CollusionSession(
            team_id="team_1",
            table_id="table_1",
            bot_ids=["bot1", "bot2", "bot3"]
        )
        
        session.record_share()
        
        assert session.shares_exchanged == 1


class TestCollusionActivator:
    """Test collusion activator."""
    
    def test_initialization(self):
        """Test activator initialization."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=True
        )
        
        assert activator.bot_pool == pool
        assert activator.card_sharing == sharing
        assert activator.require_confirmation is True
        assert activator.activations_attempted == 0
    
    def test_check_team_ready(self):
        """Test team readiness check."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing
        )
        
        # Form team
        team = pool.form_team(table_id="table_1")
        
        # Should be ready (all bots seated)
        ready = activator.check_team_ready(team)
        assert ready is True
    
    def test_activate_collusion_with_confirmation(self):
        """Test activation with confirmation required."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=True
        )
        
        team = pool.form_team(table_id="table_1")
        
        # Should fail (requires confirmation)
        activated = activator.activate_collusion(team)
        
        assert activated is False
        assert activator.activations_failed >= 1
    
    def test_activate_collusion_forced(self):
        """Test forced activation."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=True
        )
        
        team = pool.form_team(table_id="table_1")
        
        # Force activation
        activated = activator.activate_collusion(team, force=True)
        
        assert activated is True
        assert activator.activations_succeeded == 1
        assert team.team_id in activator.sessions
    
    def test_activate_collusion_no_confirmation(self):
        """Test activation without confirmation requirement."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        
        # Should succeed
        activated = activator.activate_collusion(team)
        
        assert activated is True
    
    def test_deactivate_collusion(self):
        """Test deactivation."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        activator.activate_collusion(team)
        
        # Deactivate
        deactivated = activator.deactivate_collusion(team.team_id)
        
        assert deactivated is True
        assert team.team_id not in activator.sessions
    
    def test_suspend_collusion(self):
        """Test suspension."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        activator.activate_collusion(team)
        
        # Suspend
        suspended = activator.suspend_collusion(team.team_id)
        
        assert suspended is True
        assert activator.sessions[team.team_id].mode == CollusionMode.SUSPENDED
    
    def test_resume_collusion(self):
        """Test resumption."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        activator.activate_collusion(team)
        activator.suspend_collusion(team.team_id)
        
        # Resume
        resumed = activator.resume_collusion(team.team_id)
        
        assert resumed is True
        assert activator.sessions[team.team_id].is_active()
    
    def test_is_collusion_active(self):
        """Test active status check."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        
        # Not active initially
        assert activator.is_collusion_active(team.team_id) is False
        
        # Activate
        activator.activate_collusion(team)
        assert activator.is_collusion_active(team.team_id) is True
    
    def test_record_hand_played(self):
        """Test hand recording."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        team = pool.form_team(table_id="table_1")
        activator.activate_collusion(team)
        
        # Record hands
        activator.record_hand_played(team.team_id)
        activator.record_hand_played(team.team_id)
        
        assert activator.sessions[team.team_id].hands_played == 2
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        pool = BotPool(group_hash="test", pool_size=10)
        sharing = CardSharingSystem()
        activator = CollusionActivator(
            bot_pool=pool,
            card_sharing=sharing,
            require_confirmation=False
        )
        
        # Activate some teams
        team1 = pool.form_team(table_id="table_1")
        activator.activate_collusion(team1)
        
        stats = activator.get_statistics()
        
        assert stats['activations_attempted'] >= 1
        assert stats['activations_succeeded'] >= 1
        assert stats['active_sessions'] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
