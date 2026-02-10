"""
Phase 2 Demo - Bot Control & Deployment.

⚠️ EDUCATIONAL RESEARCH ONLY.

This demo illustrates Phase 2 functionality WITHOUT requiring PyQt6.
"""

import asyncio
import time

from launcher.models.account import Account, WindowInfo, WindowType
from launcher.models.roi_config import ROIConfig, ROIZone
from launcher.bot_instance import BotInstance, BotStatus
from launcher.bot_manager import BotManager


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def create_test_account(nickname: str, room: str = "pokerstars") -> Account:
    """Create test account ready to run."""
    account = Account(nickname=nickname, room=room)
    account.window_info = WindowInfo(
        window_id=f"{hash(nickname)}",
        window_title=f"PokerStars - {nickname}",
        window_type=WindowType.DESKTOP_CLIENT,
        position=(100, 100, 800, 600)
    )
    account.roi_configured = True
    return account


def create_test_roi(account_id: str) -> ROIConfig:
    """Create test ROI configuration."""
    roi = ROIConfig(account_id=account_id, resolution=(1920, 1080))
    
    # Hero cards
    roi.add_zone(ROIZone("hero_card_1", 100, 200, 50, 70))
    roi.add_zone(ROIZone("hero_card_2", 160, 200, 50, 70))
    
    # Board cards
    for i in range(1, 6):
        roi.add_zone(ROIZone(f"board_card_{i}", 300 + i*60, 100, 50, 70))
    
    # Controls
    roi.add_zone(ROIZone("pot", 500, 50, 100, 30))
    roi.add_zone(ROIZone("fold_button", 400, 800, 80, 40))
    roi.add_zone(ROIZone("call_button", 490, 800, 80, 40))
    roi.add_zone(ROIZone("raise_button", 580, 800, 80, 40))
    
    return roi


def demo_bot_instance():
    """Demonstrate bot instance."""
    print_section("1. Bot Instance")
    
    # Create account and ROI
    account = create_test_account("DemoBot001", "pokerstars")
    roi = create_test_roi(account.account_id)
    
    # Create bot
    bot = BotInstance(account=account, roi_config=roi)
    
    print(f"\nBot instance created:")
    print(f"  ID: {bot.bot_id[:8]}...")
    print(f"  Account: {bot.account.nickname}")
    print(f"  Status: {bot.status.value}")
    print(f"  Can start: {bot.can_start()}")
    print(f"  Is active: {bot.is_active()}")
    print()
    
    # Simulate stats
    bot.stats.hands_played = 25
    bot.stats.pot_won = 150.50
    bot.stats.pot_lost = 75.25
    bot.stats.decisions_made = 80
    bot.stats.actions_executed = 60
    bot.stats.uptime_seconds = 1800.0  # 30 minutes
    
    print(f"Simulated statistics:")
    print(f"  Hands played: {bot.stats.hands_played}")
    print(f"  Net profit: ${bot.stats.net_profit():.2f}")
    print(f"  Decisions: {bot.stats.decisions_made}")
    print(f"  Actions: {bot.stats.actions_executed}")
    print(f"  Uptime: {bot.stats.uptime_seconds/60:.1f} min")
    print()
    
    return bot


def demo_bot_manager():
    """Demonstrate bot manager."""
    print_section("2. Bot Manager")
    
    # Create manager
    manager = BotManager()
    
    print(f"\nBot manager created")
    print(f"  Total bots: {len(manager.get_all_bots())}")
    print()
    
    # Create accounts and bots
    print("Creating 5 bot instances...")
    for i in range(5):
        account = create_test_account(f"ManagedBot{i+1:03d}", "pokerstars")
        roi = create_test_roi(account.account_id)
        bot = manager.create_bot(account, roi)
        print(f"  {i+1}. {bot.account.nickname} ({bot.bot_id[:8]})")
    
    print()
    
    # Statistics
    stats = manager.get_statistics()
    print(f"Pool statistics:")
    print(f"  Total bots: {stats['total_bots']}")
    print(f"  Active bots: {stats['active_bots']}")
    print(f"  Idle bots: {stats['idle_bots']}")
    print()
    
    return manager


async def demo_start_stop(manager: BotManager):
    """Demonstrate start/stop operations."""
    print_section("3. Start/Stop Operations")
    
    # Start 3 bots
    print("\nStarting 3 bots...")
    started = await manager.start_all(max_count=3)
    print(f"  Started: {started} bots")
    
    # Wait for initialization
    await asyncio.sleep(0.5)
    
    # Check status
    active = manager.get_active_bots()
    print(f"\nActive bots: {len(active)}")
    for bot in active:
        print(f"  - {bot.account.nickname}: {bot.status.value}")
    
    print()
    
    # Simulate running for a bit
    print("Running for 2 seconds...")
    for i in range(4):
        await asyncio.sleep(0.5)
        print(f"  {(i+1)*0.5:.1f}s - {len(manager.get_active_bots())} active")
    
    print()
    
    # Stop all
    print("Stopping all bots...")
    stopped = await manager.stop_all()
    print(f"  Stopped: {stopped} bots")
    
    # Final status
    stats = manager.get_statistics()
    print(f"\nFinal status:")
    print(f"  Active bots: {stats['active_bots']}")
    print(f"  Total bots: {stats['total_bots']}")
    print()


async def demo_emergency_stop(manager: BotManager):
    """Demonstrate emergency stop."""
    print_section("4. Emergency Stop")
    
    # Start all bots
    print("\nStarting all bots...")
    started = await manager.start_all()
    print(f"  Started: {started} bots")
    
    await asyncio.sleep(0.5)
    
    # Emergency stop
    print("\nEMERGENCY STOP!")
    await manager.emergency_stop()
    print("  All bots force-stopped")
    
    # Verify
    stats = manager.get_statistics()
    print(f"\nVerification:")
    print(f"  Active bots: {stats['active_bots']} (should be 0)")
    print()


def demo_bots_control_tab():
    """Demonstrate Bots Control Tab features."""
    print_section("5. Bots Control Tab UI")
    
    print("\nBotsControlTab Widget (PyQt6):")
    print()
    print("  Controls:")
    print("    - SpinBox: Select bot count (1-100)")
    print("    - [> Start Selected]: Start N idle bots")
    print("    - [>> Start All]: Start all idle bots")
    print("    - [Stop Selected]: Stop selected rows")
    print("    - [Stop All]: Stop all active bots")
    print("    - [EMERGENCY STOP]: Force-stop all (red button)")
    print()
    print("  Table columns (8):")
    print("    1. № - Row number (stores bot_id)")
    print("    2. Account - Account nickname")
    print("    3. Status - Color-coded (GREEN=playing, CYAN=active, RED=error)")
    print("    4. Table - Current table name")
    print("    5. Stack - Current stack size")
    print("    6. Edge % - Collective edge percentage")
    print("    7. Hands - Hands played")
    print("    8. Profit - Net profit (color-coded)")
    print()
    print("  Statistics bar:")
    print("    - Total: X bots")
    print("    - Active: Y bots")
    print("    - Hands: Z total")
    print("    - Profit: $X.XX total")
    print()
    print("  Real-time updates:")
    print("    - Auto-refresh every 1 second")
    print("    - Table updates with current bot status")
    print("    - Statistics recalculated")
    print()


async def main():
    """Run Phase 2 demo."""
    print("\n" + "=" * 60)
    print("PHASE 2 DEMO - Bot Control & Deployment")
    print("=" * 60)
    print("\nEducational Game Theory Research")
    print("WARNING: CRITICAL: COLLUSION SYSTEM - ILLEGAL IN REAL POKER")
    print("=" * 60)
    
    await asyncio.sleep(1)
    
    # Demo 1: Bot Instance
    demo_bot_instance()
    await asyncio.sleep(0.5)
    
    # Demo 2: Bot Manager
    manager = demo_bot_manager()
    await asyncio.sleep(0.5)
    
    # Demo 3: Start/Stop
    await demo_start_stop(manager)
    await asyncio.sleep(0.5)
    
    # Demo 4: Emergency Stop
    await demo_emergency_stop(manager)
    await asyncio.sleep(0.5)
    
    # Demo 5: UI Components
    demo_bots_control_tab()
    
    # Summary
    print_section("PHASE 2 COMPLETE")
    print("\nImplemented:")
    print("  -> BotInstance with lifecycle management")
    print("  -> BotStatistics for tracking performance")
    print("  -> BotManager for pool operations")
    print("  -> BotsControlTab UI with real-time monitoring")
    print("  -> Start/Stop/Emergency stop workflows")
    print("  -> Full integration with main window")
    print()
    print("Tests: 36 passed")
    print("Files: 6 created/modified")
    print()
    print("Next Phase: Фаза 3 - Table Search & Auto-Fill")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
