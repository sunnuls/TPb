"""
Tests for BotManager - Phase 2.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

import time

import pytest

from launcher.bot_manager import BotManager
from launcher.bot_instance import BotStatus
from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone


def _wait_until(pred, timeout=5.0, interval=0.1, msg="condition not met"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return
        time.sleep(interval)
    assert pred(), msg


def create_test_account(nickname: str) -> Account:
    """Create test account."""
    account = Account(nickname=nickname, room="pokerstars")
    account.window_info = WindowInfo(
        window_id=f"{hash(nickname)}",
        window_title=f"PokerStars - {nickname}",
        window_type=WindowType.DESKTOP_CLIENT
    )
    account.roi_configured = True
    return account


def create_test_roi(account_id: str) -> ROIConfig:
    """Create test ROI config."""
    roi = ROIConfig(account_id=account_id)
    roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
    roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
    roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
    roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
    return roi


class TestBotManager:
    """Tests for BotManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = BotManager()
        
        assert len(manager.bots) == 0
        assert len(manager.account_to_bot) == 0
    
    def test_create_bot(self):
        """Test creating bot."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        
        assert bot is not None
        assert bot.account == account
        assert bot.roi_config == roi
        assert bot.bot_id in manager.bots
        assert account.account_id in manager.account_to_bot
    
    def test_create_bot_duplicate(self):
        """Test creating duplicate bot for same account."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot1 = manager.create_bot(account, roi)
        bot2 = manager.create_bot(account, roi)
        
        # Should return same bot
        assert bot1.bot_id == bot2.bot_id
        assert len(manager.bots) == 1
    
    def test_get_bot(self):
        """Test getting bot by ID."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        
        retrieved = manager.get_bot(bot.bot_id)
        assert retrieved == bot
        
        missing = manager.get_bot("nonexistent")
        assert missing is None
    
    def test_get_bot_by_account(self):
        """Test getting bot by account ID."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        
        retrieved = manager.get_bot_by_account(account.account_id)
        assert retrieved == bot
    
    def test_get_all_bots(self):
        """Test getting all bots."""
        manager = BotManager()
        
        # Create multiple bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        all_bots = manager.get_all_bots()
        assert len(all_bots) == 3
    
    def test_get_active_bots(self):
        """Test getting active bots."""
        manager = BotManager()
        
        # Create bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # All idle
        assert len(manager.get_active_bots()) == 0
        
        # Set one to active
        bots = manager.get_all_bots()
        bots[0].status = BotStatus.PLAYING
        
        assert len(manager.get_active_bots()) == 1
    
    def test_get_idle_bots(self):
        """Test getting idle bots."""
        manager = BotManager()
        
        # Create bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # All can start
        assert len(manager.get_idle_bots()) == 3
        
        # Set one to running
        bots = manager.get_all_bots()
        bots[0].status = BotStatus.PLAYING
        
        assert len(manager.get_idle_bots()) == 2
    
    def test_start_bot(self):
        """Test starting bot."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        
        # Start bot
        success = manager.start_bot(bot.bot_id)
        assert success
        
        _wait_until(
            lambda: bot.status in [BotStatus.STARTING, BotStatus.SEARCHING],
            msg="bot did not reach STARTING/SEARCHING",
        )
        
        # Cleanup
        manager.stop_bot(bot.bot_id)
        _wait_until(lambda: bot.status == BotStatus.STOPPED, msg="bot did not stop")
    
    def test_start_all(self):
        """Test starting all bots."""
        manager = BotManager()
        
        # Create bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # Start all
        started = manager.start_all()
        assert started == 3
        
        _wait_until(
            lambda: len(manager.get_active_bots()) == 3,
            msg="expected 3 active bots",
        )
        
        # Cleanup
        manager.stop_all()
        _wait_until(lambda: len(manager.get_active_bots()) == 0, msg="bots still active")
    
    def test_start_all_with_limit(self):
        """Test starting limited number of bots."""
        manager = BotManager()
        
        # Create bots
        for i in range(5):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        # Start 3
        started = manager.start_all(max_count=3)
        assert started == 3
        
        _wait_until(
            lambda: len(manager.get_active_bots()) == 3,
            msg="expected 3 active bots",
        )
        
        # Cleanup
        manager.stop_all()
        _wait_until(lambda: len(manager.get_active_bots()) == 0, msg="bots still active")
    
    def test_stop_bot(self):
        """Test stopping bot."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        
        # Start and stop
        manager.start_bot(bot.bot_id)
        _wait_until(
            lambda: bot.status in [BotStatus.STARTING, BotStatus.SEARCHING],
            msg="bot did not start",
        )
        
        success = manager.stop_bot(bot.bot_id)
        assert success
        _wait_until(lambda: bot.status == BotStatus.STOPPED, msg="bot did not stop")
    
    def test_stop_all(self):
        """Test stopping all bots."""
        manager = BotManager()
        
        # Create and start bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        manager.start_all()
        _wait_until(
            lambda: len(manager.get_active_bots()) == 3,
            msg="expected 3 active bots",
        )
        
        # Stop all
        stopped = manager.stop_all()
        assert stopped == 3
        
        _wait_until(lambda: len(manager.get_active_bots()) == 0, msg="bots still active")
    
    def test_emergency_stop(self):
        """Test emergency stop."""
        manager = BotManager()
        
        # Create and start bots
        for i in range(3):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            manager.create_bot(account, roi)
        
        manager.start_all()
        _wait_until(
            lambda: len(manager.get_active_bots()) == 3,
            msg="expected 3 active bots",
        )
        
        # Emergency stop
        manager.emergency_stop()
        
        # All should be stopped
        _wait_until(lambda: len(manager.get_active_bots()) == 0, msg="bots still active")
    
    def test_remove_bot(self):
        """Test removing bot."""
        manager = BotManager()
        
        account = create_test_account("TestBot001")
        roi = create_test_roi(account.account_id)
        
        bot = manager.create_bot(account, roi)
        bot_id = bot.bot_id
        
        # Remove
        success = manager.remove_bot(bot_id)
        assert success
        
        assert bot_id not in manager.bots
        assert account.account_id not in manager.account_to_bot
    
    def test_get_statistics(self):
        """Test getting statistics."""
        manager = BotManager()
        
        # Create bots
        for i in range(5):
            account = create_test_account(f"TestBot{i+1:03d}")
            roi = create_test_roi(account.account_id)
            bot = manager.create_bot(account, roi)
            
            # Simulate some stats
            bot.stats.hands_played = 10 * (i + 1)
            bot.stats.pot_won = 50.0 * (i + 1)
            bot.stats.pot_lost = 25.0 * (i + 1)
        
        stats = manager.get_statistics()
        
        assert stats['total_bots'] == 5
        assert stats['active_bots'] == 0
        assert stats['idle_bots'] == 5
        assert stats['total_hands'] == 150  # 10+20+30+40+50
        assert stats['total_profit'] == 375.0  # 25*1 + 50*2 + 75*3 + 100*4 + 125*5 = 25+50+75+100+125


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
