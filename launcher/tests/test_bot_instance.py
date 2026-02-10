"""
Tests for BotInstance - Phase 2.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import pytest
import asyncio

from launcher.bot_instance import BotInstance, BotStatus, BotStatistics
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


class TestBotStatistics:
    """Tests for BotStatistics."""
    
    def test_create_default(self):
        """Test creating default statistics."""
        stats = BotStatistics()
        
        assert stats.hands_played == 0
        assert stats.pot_won == 0.0
        assert stats.pot_lost == 0.0
        assert stats.vision_errors == 0
        assert stats.decisions_made == 0
        assert stats.actions_executed == 0
        assert stats.uptime_seconds == 0.0
    
    def test_net_profit(self):
        """Test net profit calculation."""
        stats = BotStatistics()
        
        stats.pot_won = 150.0
        stats.pot_lost = 75.0
        
        assert stats.net_profit() == 75.0
    
    def test_net_profit_negative(self):
        """Test negative net profit."""
        stats = BotStatistics()
        
        stats.pot_won = 50.0
        stats.pot_lost = 100.0
        
        assert stats.net_profit() == -50.0


class TestBotInstance:
    """Tests for BotInstance."""
    
    def test_create_default(self):
        """Test creating bot with defaults."""
        bot = BotInstance()
        
        assert bot.bot_id
        assert bot.account is None
        assert bot.roi_config is None
        assert bot.status == BotStatus.IDLE
        assert bot.current_table == ""
        assert bot.stack == 0.0
        assert bot.collective_edge == 0.0
        assert not bot._running
    
    def test_create_with_account(self):
        """Test creating bot with account."""
        account = Account(nickname="TestBot", room="pokerstars")
        roi = ROIConfig(account_id=account.account_id)
        
        bot = BotInstance(account=account, roi_config=roi)
        
        assert bot.account == account
        assert bot.roi_config == roi
    
    def test_is_active(self):
        """Test active status check."""
        bot = BotInstance()
        
        # IDLE is not active
        bot.status = BotStatus.IDLE
        assert not bot.is_active()
        
        # STARTING is active
        bot.status = BotStatus.STARTING
        assert bot.is_active()
        
        # PLAYING is active
        bot.status = BotStatus.PLAYING
        assert bot.is_active()
        
        # STOPPED is not active
        bot.status = BotStatus.STOPPED
        assert not bot.is_active()
        
        # ERROR is not active
        bot.status = BotStatus.ERROR
        assert not bot.is_active()
    
    def test_can_start(self):
        """Test can start check."""
        bot = BotInstance()
        
        # Cannot start without account
        assert not bot.can_start()
        
        # Create ready account
        account = Account(nickname="TestBot", room="pokerstars")
        account.window_info = WindowInfo(
            window_id="12345",
            window_title="PokerStars",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id)
        roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
        roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        
        bot.account = account
        bot.roi_config = roi
        
        # Can start
        assert bot.can_start()
        
        # Cannot start if already running
        bot.status = BotStatus.PLAYING
        assert not bot.can_start()
    
    @pytest.mark.asyncio
    async def test_start_bot(self):
        """Test starting bot."""
        # Create ready account
        account = Account(nickname="TestBot", room="pokerstars")
        account.window_info = WindowInfo(
            window_id="12345",
            window_title="PokerStars",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id)
        
        bot = BotInstance(account=account, roi_config=roi)
        
        # Start bot
        await bot.start()
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Check status
        assert bot.status in [BotStatus.STARTING, BotStatus.SEARCHING]
        assert bot._running
        assert bot.start_time is not None
        
        # Stop bot
        await bot.stop()
    
    @pytest.mark.asyncio
    async def test_stop_bot(self):
        """Test stopping bot."""
        account = Account(nickname="TestBot", room="pokerstars")
        account.window_info = WindowInfo(
            window_id="12345",
            window_title="PokerStars",
            window_type=WindowType.DESKTOP_CLIENT
        )
        account.roi_configured = True
        
        roi = ROIConfig(account_id=account.account_id)
        bot = BotInstance(account=account, roi_config=roi)
        
        # Start and stop
        await bot.start()
        await asyncio.sleep(0.1)
        await bot.stop()
        
        # Check status
        assert bot.status == BotStatus.STOPPED
        assert not bot._running
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        account = Account(nickname="TestBot", room="pokerstars")
        roi = ROIConfig(account_id=account.account_id)
        
        bot = BotInstance(account=account, roi_config=roi)
        bot.stats.hands_played = 10
        bot.stats.pot_won = 50.0
        bot.stats.pot_lost = 25.0
        
        data = bot.to_dict()
        
        assert 'bot_id' in data
        assert data['nickname'] == "TestBot"
        assert data['status'] == BotStatus.IDLE.value
        assert 'stats' in data
        assert data['stats']['hands_played'] == 10
        assert data['stats']['net_profit'] == 25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
