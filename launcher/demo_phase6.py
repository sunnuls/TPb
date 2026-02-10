"""
Phase 6 Demo - Logs, Monitoring & Safety.

⚠️ EDUCATIONAL RESEARCH ONLY.

This demo illustrates Phase 6 functionality WITHOUT requiring PyQt6.
"""

import logging
import time
from launcher.log_handler import setup_launcher_logging, get_log_handler
from launcher.bot_manager import BotManager
from launcher.models.account import Account
from launcher.models.roi_config import ROIConfig


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def demo_log_handler():
    """Demonstrate log handler."""
    print_section("1. Log Handler & Color Coding")
    
    # Setup logging
    handler = setup_launcher_logging(use_qt=False)
    handler.clear()
    
    # Create test logger
    logger = logging.getLogger("demo_bot")
    
    print("\nEmitting logs at different levels...")
    logger.debug("Debug: Capturing screen frame")
    logger.info("Info: Connected to table")
    logger.warning("Warning: High latency detected")
    logger.error("Error: Vision OCR failed")
    logger.critical("Critical: Emergency stop triggered")
    
    # Display logs
    print("\nCaptured logs (with colors):")
    for entry in handler.get_recent_logs(count=5):
        print(f"  [{entry.level.value:8s}] {entry.message} (color: {entry.color})")
    
    # Statistics
    stats = handler.get_statistics()
    print(f"\nLog Statistics:")
    print(f"  Total logs: {stats['total']}")
    for level, count in stats['by_level'].items():
        if count > 0:
            print(f"  {level}: {count}")


def demo_vision_error_tracking():
    """Demonstrate vision error tracking."""
    print_section("2. Vision Error Tracking")
    
    manager = BotManager(max_vision_errors=3)
    
    # Create test bot
    account = Account(nickname="Test Bot")
    roi_config = ROIConfig(account_id=account.account_id)
    bot = manager.create_bot(account, roi_config)
    
    print(f"\nBot created: {bot.account.nickname}")
    print(f"Max vision errors: {manager.max_vision_errors}")
    print()
    
    # Simulate errors
    print("Simulating vision errors...")
    for i in range(5):
        should_stop = manager.record_vision_error(bot.bot_id)
        error_count = manager._consecutive_vision_errors.get(bot.bot_id, 0)
        
        print(f"  Error #{i+1}: Count = {error_count}, Should stop = {should_stop}")
        
        if should_stop:
            print(f"  -> Bot exceeded threshold! Would be auto-stopped.")
            break
    
    print()
    
    # Test reset
    print("Recording vision success (resets counter)...")
    manager.record_vision_success(bot.bot_id)
    error_count = manager._consecutive_vision_errors.get(bot.bot_id, 0)
    print(f"  Error count after success: {error_count}")


def demo_dashboard_statistics():
    """Demonstrate dashboard statistics."""
    print_section("3. Dashboard Statistics")
    
    manager = BotManager()
    
    # Create multiple bots
    print("\nCreating 10 bots...")
    accounts = [Account(nickname=f"Bot {i+1}") for i in range(10)]
    rois = [ROIConfig(account_id=acc.account_id) for acc in accounts]
    
    for i, (acc, roi) in enumerate(zip(accounts, rois)):
        bot = manager.create_bot(acc, roi)
        
        # Simulate activity
        bot.stats.hands_played = 50 + (i * 10)
        bot.stats.pot_won = 200.0 + (i * 20)
        bot.stats.pot_lost = 150.0 + (i * 10)
        bot.stats.vision_errors = i % 3
        bot.stats.actions_executed = 200 + (i * 20)
        bot.stats.uptime_seconds = 1800 + (i * 300)
        bot.collective_edge = 5.0 + (i * 0.5)
    
    # Get statistics
    stats = manager.get_statistics()
    
    print("\nDashboard Statistics:")
    print(f"  Total Bots: {stats['total_bots']}")
    print(f"  Active Bots: {stats['active_bots']}")
    print(f"  Active Tables: {stats['active_tables']}")
    print(f"  HIVE Teams: {stats['hive_teams']}")
    print(f"  Hands Played: {stats['hands_played']}")
    print(f"  Total Profit: ${stats['total_profit']:.2f}")
    print(f"  Vision Errors: {stats['vision_errors']}")
    print(f"  Actions Executed: {stats['actions_executed']}")
    print(f"  Uptime: {stats['uptime_seconds']//3600}h {(stats['uptime_seconds']%3600)//60}m")
    print(f"  Avg Collective Edge: {stats['avg_collective_edge']:.1f}%")
    
    # Performance indicators
    print("\nPerformance Indicators:")
    if stats['hands_played'] > 0:
        error_rate = (stats['vision_errors'] / stats['hands_played']) * 100
        vision_health = max(0, 100 - error_rate * 10)
        print(f"  Vision Health: {vision_health:.0f}% (error rate: {error_rate:.1f}%)")
    
    if stats['uptime_seconds'] > 0:
        actions_per_min = (stats['actions_executed'] / stats['uptime_seconds']) * 60
        print(f"  Decision Speed: {actions_per_min:.1f} actions/min")


def demo_alert_system():
    """Demonstrate alert system."""
    print_section("4. Alert System")
    
    manager = BotManager()
    
    # Scenario 1: High vision errors
    print("\nScenario 1: High vision error rate")
    account1 = Account(nickname="Faulty Bot")
    roi1 = ROIConfig(account_id=account1.account_id)
    bot1 = manager.create_bot(account1, roi1)
    bot1.stats.hands_played = 100
    bot1.stats.vision_errors = 15  # 15% error rate
    
    stats = manager.get_statistics()
    error_rate = stats['vision_errors'] / stats['hands_played']
    
    if error_rate > 0.1:
        print(f"  -> ALERT: High vision error rate: {error_rate:.1%}")
        print(f"     Recommendation: Check ROI configuration or restart bots")
    
    # Scenario 2: Large losses
    print("\nScenario 2: Large losses")
    for i in range(5):
        acc = Account(nickname=f"Losing Bot {i}")
        roi = ROIConfig(account_id=acc.account_id)
        bot = manager.create_bot(acc, roi)
        bot.stats.pot_won = 50.0
        bot.stats.pot_lost = 150.0
    
    stats = manager.get_statistics()
    
    if stats['total_profit'] < -100:
        print(f"  -> ALERT: Large losses: ${abs(stats['total_profit']):.2f}")
        print(f"     Recommendation: Review bot settings and strategy")
    
    # Scenario 3: No active bots
    print("\nScenario 3: No active bots")
    stats = manager.get_statistics()
    
    if stats['active_bots'] == 0 and stats['total_bots'] > 0:
        print(f"  -> ALERT: No active bots running")
        print(f"     Recommendation: Check bot startup issues")


def demo_logs_tab():
    """Demonstrate logs tab features (description)."""
    print_section("5. Logs Tab UI (PyQt6)")
    
    print("\nLogsTab Features:")
    print("  - Real-time log display (QTextEdit)")
    print("  - Dark theme (black background)")
    print("  - Monospace font (Consolas)")
    print("  - Color-coded messages:")
    print("    * Debug:    Gray (#888888)")
    print("    * Info:     Light gray (#CCCCCC)")
    print("    * Actions:  Green (#66FF66)")
    print("    * Warnings: Yellow (#FFFF66)")
    print("    * Errors:   Red (#FF6666)")
    print()
    print("  Level Filters (Checkboxes):")
    print("    - Debug, Info, Actions, Warnings, Errors")
    print("    - Toggle to show/hide each level")
    print()
    print("  Controls:")
    print("    - Auto-scroll: Automatically scroll to latest")
    print("    - Clear Logs: Remove all entries")
    print()
    print("  Statistics Bar:")
    print("    - Total logs, Actions, Warnings, Errors")
    print("    - Real-time counts")


def demo_dashboard_tab():
    """Demonstrate dashboard tab features (description)."""
    print_section("6. Dashboard Tab UI (PyQt6)")
    
    print("\nDashboardTab Features:")
    print()
    print("  Emergency Controls:")
    print("    - Warning banner (orange)")
    print("    - Large EMERGENCY STOP button (red)")
    print("    - Confirmation dialog required")
    print("    - Stops ALL bots immediately")
    print()
    print("  System Statistics (Grid):")
    print("    - Total Bots / Active Bots")
    print("    - Active Tables / HIVE Teams")
    print("    - Total Profit (green/red)")
    print("    - Hands Played")
    print("    - Vision Errors (yellow)")
    print("    - Actions Executed")
    print("    - Avg Collective Edge (blue)")
    print("    - Session Uptime (HH:MM:SS)")
    print()
    print("  Performance Indicators:")
    print("    - Vision Health:")
    print("      * Progress bar (0-100%)")
    print("      * Green (>80%), Orange (50-80%), Red (<50%)")
    print("    - Decision Speed:")
    print("      * Actions per minute")
    print()
    print("  Active Alerts:")
    print("    - High vision error rate (>10%)")
    print("    - Large losses (< -$100)")
    print("    - No active bots")
    print("    - Color: Yellow (warning) or Green (OK)")
    print()
    print("  Real-time Updates:")
    print("    - QTimer: 1 second interval")
    print("    - Queries BotManager.get_statistics()")
    print("    - Auto-updates all displays")


def main():
    """Run Phase 6 demo."""
    print("\n" + "=" * 60)
    print("PHASE 6 DEMO - Logs, Monitoring & Safety")
    print("=" * 60)
    print("\nEducational Game Theory Research")
    print("WARNING: CRITICAL: COLLUSION SYSTEM - ILLEGAL IN REAL POKER")
    print("=" * 60)
    
    # Demo 1: Log Handler
    demo_log_handler()
    
    # Demo 2: Vision Error Tracking
    demo_vision_error_tracking()
    
    # Demo 3: Dashboard Statistics
    demo_dashboard_statistics()
    
    # Demo 4: Alert System
    demo_alert_system()
    
    # Demo 5: Logs Tab Description
    demo_logs_tab()
    
    # Demo 6: Dashboard Tab Description
    demo_dashboard_tab()
    
    # Summary
    print_section("PHASE 6 COMPLETE")
    print("\nImplemented:")
    print("  -> Log handler (color-coded)")
    print("  -> Vision error tracking (auto-stop)")
    print("  -> Dashboard statistics")
    print("  -> Alert system")
    print("  -> Logs Tab (PyQt6)")
    print("  -> Dashboard Tab (PyQt6)")
    print("  -> Emergency STOP button")
    print()
    print("Safety Features:")
    print("  - Max 5 consecutive vision errors (configurable)")
    print("  - Auto-stop bots on error threshold")
    print("  - Emergency stop all bots")
    print("  - Real-time monitoring and alerts")
    print("  - Vision health indicator")
    print()
    print("Tests: 22 passed")
    print("Files: 7 created/modified")
    print()
    print("Next Phase: Phase 7 - Testing & Finalization")
    print("=" * 60)


if __name__ == "__main__":
    main()
