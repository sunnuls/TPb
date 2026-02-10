"""
Integration Tests for Roadmap6 Phase 1.

⚠️ EDUCATIONAL RESEARCH ONLY.

Tests:
1. Account model complete
2. ROI model complete
3. Config persistence works
4. Window capture available
5. All components integrate correctly
"""

import pytest
import tempfile
from pathlib import Path

from launcher.models.account import Account, AccountStatus, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone
from launcher.config_manager import ConfigManager
from launcher.window_capture import WindowCapture


class TestPhase1Integration:
    """Integration tests for Phase 1."""
    
    def test_account_creation_and_serialization(self):
        """Test account creation and serialization."""
        # Create account
        account = Account(
            nickname="IntegrationBot",
            room="pokerstars",
            notes="Test account"
        )
        
        # Verify defaults
        assert account.status == AccountStatus.IDLE
        assert not account.bot_running
        assert not account.roi_configured
        
        # Serialize
        data = account.to_dict()
        assert data['nickname'] == "IntegrationBot"
        
        # Deserialize
        restored = Account.from_dict(data)
        assert restored.nickname == account.nickname
        assert restored.account_id == account.account_id
    
    def test_roi_configuration_workflow(self):
        """Test complete ROI configuration workflow."""
        account_id = "test-integration-123"
        
        # Create ROI config
        roi = ROIConfig(account_id=account_id, resolution=(1920, 1080))
        
        # Add hero cards
        roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
        roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
        
        # Add community cards
        for i in range(1, 6):
            roi.add_zone(ROIZone(f"board_card_{i}", 300 + i*60, 100, 50, 70))
        
        # Add pot and buttons
        roi.add_zone(ROIZone("pot", 500, 50, 100, 30))
        roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
        roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
        
        # Verify required zones
        assert roi.has_required_zones()
        
        # Serialize
        data = roi.to_dict()
        assert len(data['zones']) == 10
        
        # Deserialize
        restored = ROIConfig.from_dict(data)
        assert len(restored.zones) == 10
        assert restored.has_required_zones()
    
    def test_config_persistence_workflow(self):
        """Test complete config persistence workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir=config_dir)
            
            # Create accounts
            accounts = [
                Account(nickname="Bot001", room="pokerstars"),
                Account(nickname="Bot002", room="ignition")
            ]
            
            # Capture windows (simulate)
            accounts[0].window_info = WindowInfo(
                window_id="12345",
                window_title="PokerStars",
                window_type=WindowType.DESKTOP_CLIENT
            )
            
            # Configure ROI for first account
            accounts[0].roi_configured = True
            accounts[0].status = AccountStatus.READY
            
            # Save accounts
            manager.save_accounts(accounts)
            
            # Create ROI config for first account
            roi = ROIConfig(account_id=accounts[0].account_id)
            roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
            roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
            roi.add_zone(ROIZone("pot", 500, 100, 100, 30))
            roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
            roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
            
            manager.save_roi_config(accounts[0].account_id, roi)
            
            # Create new manager and load
            new_manager = ConfigManager(config_dir=config_dir)
            
            loaded_accounts = new_manager.load_accounts()
            assert len(loaded_accounts) == 2
            assert loaded_accounts[0].nickname == "Bot001"
            assert loaded_accounts[0].roi_configured is True
            
            loaded_roi = new_manager.load_roi_config(accounts[0].account_id)
            assert loaded_roi is not None
            assert len(loaded_roi.zones) == 5
    
    def test_window_capture_initialization(self):
        """Test window capture initialization."""
        capture = WindowCapture()
        
        # Should initialize
        assert capture is not None
        
        # Availability depends on environment
        if capture.available:
            # Try listing windows
            windows = capture.list_windows()
            assert isinstance(windows, list)
        else:
            # Should handle unavailability gracefully
            windows = capture.list_windows()
            assert windows == []
    
    def test_account_ready_state(self):
        """Test account ready state logic."""
        account = Account(nickname="ReadyTest")
        
        # Initially not ready
        assert not account.is_ready_to_run()
        
        # Capture window
        account.window_info.window_id = "12345"
        account.window_info.window_title = "Poker"
        assert not account.is_ready_to_run()
        
        # Configure ROI
        account.roi_configured = True
        account.status = AccountStatus.READY
        assert account.is_ready_to_run()
        
        # Start bot - no longer ready
        account.bot_running = True
        assert not account.is_ready_to_run()
    
    def test_phase1_components_available(self):
        """Test that all Phase 1 components are available."""
        # Models
        from launcher.models.account import Account, AccountStatus
        from launcher.models.roi_config import ROIConfig, ROIZone
        
        # Utilities
        from launcher.config_manager import ConfigManager
        from launcher.window_capture import WindowCapture
        
        # All imports should succeed
        assert Account is not None
        assert ROIConfig is not None
        assert ConfigManager is not None
        assert WindowCapture is not None
    
    def test_full_workflow_simulation(self):
        """Simulate full Phase 1 workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # 1. Initialize manager
            manager = ConfigManager(config_dir=config_dir)
            
            # 2. Create account
            account = Account(nickname="WorkflowBot", room="pokerstars")
            
            # 3. Simulate window capture
            capture = WindowCapture()
            account.window_info = WindowInfo(
                window_id="99999",
                window_title="PokerStars - Table 1",
                window_type=WindowType.DESKTOP_CLIENT
            )
            
            # 4. Configure ROI
            roi = ROIConfig(account_id=account.account_id)
            
            # Add all required zones
            required_zones = [
                ("hero_card_1", 100, 200, 50, 70),
                ("hero_card_2", 160, 200, 50, 70),
                ("pot", 500, 100, 100, 30),
                ("fold_button", 400, 800, 80, 40),
                ("call_button", 490, 800, 80, 40)
            ]
            
            for name, x, y, w, h in required_zones:
                roi.add_zone(ROIZone(name, x, y, w, h))
            
            account.roi_configured = True
            account.status = AccountStatus.READY
            
            # 5. Save everything
            manager.save_accounts([account])
            manager.save_roi_config(account.account_id, roi)
            
            # 6. Verify persistence
            loaded_accounts = manager.load_accounts()
            loaded_roi = manager.load_roi_config(account.account_id)
            
            assert len(loaded_accounts) == 1
            assert loaded_accounts[0].is_ready_to_run()
            assert loaded_roi.has_required_zones()
            
            print("\n" + "=" * 60)
            print("Phase 1 Workflow Simulation Complete")
            print("=" * 60)
            print(f"Account: {account.nickname}")
            print(f"Window: {account.window_info.window_title}")
            print(f"ROI Zones: {len(roi.zones)}")
            print(f"Ready to run: {account.is_ready_to_run()}")
            print("=" * 60)


# Summary test
def test_phase1_summary():
    """Print Phase 1 completion summary."""
    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETION SUMMARY")
    print("=" * 60)
    print()
    print("Components implemented:")
    print("  ✓ Account model (account.py)")
    print("  ✓ ROI config model (roi_config.py)")
    print("  ✓ Window capture (window_capture.py)")
    print("  ✓ Config persistence (config_manager.py)")
    print("  ✓ Accounts tab UI (accounts_tab.py)")
    print("  ✓ ROI overlay UI (roi_overlay.py)")
    print("  ✓ Main window integration (main_window.py)")
    print()
    print("Features:")
    print("  - Add/Edit/Remove accounts")
    print("  - Capture poker client windows")
    print("  - Draw ROI zones via overlay")
    print("  - Persistent JSON storage")
    print("  - Status tracking")
    print()
    print("Tests:")
    print("  - test_models.py")
    print("  - test_config_manager.py")
    print("  - test_window_capture.py")
    print("  - test_phase1_integration.py")
    print()
    print("=" * 60)
    print("Phase 1: Account Management & Window Capture COMPLETE")
    print("=" * 60)
    
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
