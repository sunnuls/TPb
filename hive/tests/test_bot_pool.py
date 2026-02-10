"""
Tests for Bot Pool (Roadmap5 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest

from hive.bot_pool import BotInstance, BotPool, BotStatus, HiveTeam


class TestBotInstance:
    """Test bot instance."""
    
    def test_creation(self):
        """Test bot instance creation."""
        bot = BotInstance(
            bot_id="test_bot_1",
            group_hash="test_group"
        )
        
        assert bot.bot_id == "test_bot_1"
        assert bot.group_hash == "test_group"
        assert bot.status == BotStatus.IDLE
        assert bot.current_table is None
        assert bot.hands_played == 0
    
    def test_update_status(self):
        """Test status update."""
        bot = BotInstance(bot_id="test", group_hash="group")
        
        bot.update_status(BotStatus.SEATED)
        
        assert bot.status == BotStatus.SEATED
    
    def test_assign_table(self):
        """Test table assignment."""
        bot = BotInstance(bot_id="test", group_hash="group")
        
        bot.assign_table("table_1")
        
        assert bot.current_table == "table_1"
        assert bot.status == BotStatus.SEATED
    
    def test_leave_table(self):
        """Test leaving table."""
        bot = BotInstance(bot_id="test", group_hash="group")
        
        bot.assign_table("table_1")
        bot.leave_table()
        
        assert bot.current_table is None
        assert bot.status == BotStatus.IDLE
    
    def test_record_hand(self):
        """Test hand recording."""
        bot = BotInstance(bot_id="test", group_hash="group")
        
        bot.record_hand()
        bot.record_hand()
        
        assert bot.hands_played == 2


class TestHiveTeam:
    """Test HIVE team."""
    
    def test_creation(self):
        """Test team creation."""
        team = HiveTeam(
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            table_id="table_1"
        )
        
        assert team.team_id == "team_1"
        assert len(team.bot_ids) == 3
        assert team.table_id == "table_1"
        assert team.active is True
    
    def test_invalid_team_size(self):
        """Test team requires exactly 3 bots."""
        with pytest.raises(ValueError, match="exactly 3 bots"):
            HiveTeam(
                team_id="team_1",
                bot_ids=["bot1", "bot2"],
                table_id="table_1"
            )
    
    def test_contains_bot(self):
        """Test bot membership check."""
        team = HiveTeam(
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            table_id="table_1"
        )
        
        assert team.contains_bot("bot1") is True
        assert team.contains_bot("bot4") is False
    
    def test_deactivate(self):
        """Test team deactivation."""
        team = HiveTeam(
            team_id="team_1",
            bot_ids=["bot1", "bot2", "bot3"],
            table_id="table_1"
        )
        
        team.deactivate()
        
        assert team.active is False


class TestBotPool:
    """Test bot pool."""
    
    def test_initialization(self):
        """Test pool initialization."""
        pool = BotPool(
            group_hash="test_group",
            pool_size=10,
            max_teams=3
        )
        
        assert pool.pool_size == 10
        assert pool.max_teams == 3
        assert len(pool.bots) == 10
        assert len(pool.teams) == 0
    
    def test_get_idle_bots(self):
        """Test getting idle bots."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        idle = pool.get_idle_bots(count=3)
        
        assert len(idle) == 3
    
    def test_form_team(self):
        """Test team formation."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        team = pool.form_team(table_id="table_1")
        
        assert team is not None
        assert len(team.bot_ids) == 3
        assert team.table_id == "table_1"
        assert team.team_id in pool.teams
        
        # Check bots are seated
        for bot_id in team.bot_ids:
            assert pool.bots[bot_id].status == BotStatus.SEATED
            assert pool.bots[bot_id].current_table == "table_1"
    
    def test_form_team_no_bots_available(self):
        """Test team formation fails when no bots."""
        pool = BotPool(group_hash="test", pool_size=2)
        
        team = pool.form_team(table_id="table_1")
        
        assert team is None
    
    def test_form_team_max_teams_reached(self):
        """Test team formation fails when max teams reached."""
        pool = BotPool(group_hash="test", pool_size=10, max_teams=1)
        
        # Form first team
        team1 = pool.form_team(table_id="table_1")
        assert team1 is not None
        
        # Try to form second team
        team2 = pool.form_team(table_id="table_2")
        assert team2 is None
    
    def test_disband_team(self):
        """Test team disbanding."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        team = pool.form_team(table_id="table_1")
        assert team is not None
        
        # Disband
        success = pool.disband_team(team.team_id)
        
        assert success is True
        assert team.active is False
        
        # Check bots returned to idle
        for bot_id in team.bot_ids:
            assert pool.bots[bot_id].status == BotStatus.IDLE
            assert pool.bots[bot_id].current_table is None
    
    def test_get_team_at_table(self):
        """Test getting team at table."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        team = pool.form_team(table_id="table_1")
        
        found = pool.get_team_at_table("table_1")
        
        assert found is not None
        assert found.team_id == team.team_id
    
    def test_record_hand_played(self):
        """Test recording hand played."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        bot_id = list(pool.bots.keys())[0]
        
        pool.record_hand_played(bot_id)
        
        assert pool.bots[bot_id].hands_played == 1
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        pool = BotPool(group_hash="test", pool_size=10)
        
        # Form team
        pool.form_team(table_id="table_1")
        
        stats = pool.get_statistics()
        
        assert stats['pool_size'] == 10
        assert stats['active_teams'] == 1
        assert stats['status_distribution'][BotStatus.IDLE.value] == 7
        assert stats['status_distribution'][BotStatus.SEATED.value] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
