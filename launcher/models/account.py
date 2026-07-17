"""
Account Data Model - Launcher Application (Roadmap6 Phase 1).

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from launcher.models.game_settings import GamePreferences


class AccountStatus(str, Enum):
    """Account operational status."""
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class PokerClient(str, Enum):
    """Known poker room clients."""
    COINPOKER   = "coinpoker"
    POKERSTARS  = "pokerstars"
    GGPOKER     = "ggpoker"
    PARTYPOKER  = "partypoker"
    UNKNOWN     = "unknown"


class WindowType(str, Enum):
    """Window/browser type."""
    DESKTOP_CLIENT = "desktop_client"
    BROWSER        = "browser"
    EMBEDDED       = "embedded"
    UNKNOWN        = "unknown"


@dataclass
class WindowInfo:
    """
    Window information.
    
    Attributes:
        window_id: Window handle/identifier (string)
        hwnd: Windows window handle (HWND) - for direct capture
        window_title: Window title
        window_type: Type of window
        process_name: Process name
        position: Window position (x, y, width, height)
        emulator_serial: ADB serial of a mobile emulator instance (e.g.
            "127.0.0.1:5555"). When set, the bot captures/clicks via
            `bridge.emulator.adb_backend.ADBBackend` instead of the
            Win32/HWND path — see `launcher/emulator_manager.py`.
    """
    window_id: Optional[str] = None
    hwnd: Optional[int] = None  # Windows HWND for direct capture
    window_title: Optional[str] = None
    window_type: WindowType = WindowType.UNKNOWN
    process_name: Optional[str] = None
    position: Optional[tuple] = None
    emulator_serial: Optional[str] = None  # ADB serial for mobile emulator targets
    
    def is_captured(self) -> bool:
        """Check if window is captured."""
        return self.window_id is not None or self.hwnd is not None or self.emulator_serial is not None


@dataclass
class Account:
    """
    Bot account.
    
    Attributes:
        account_id: Unique identifier
        nickname: Account nickname/login
        status: Current status
        window_info: Captured window information
        roi_configured: Whether ROI is configured
        bot_running: Whether bot is currently running
        room: Poker room (pokerstars, ignition, etc.)
        notes: Optional notes
        game_preferences: Game type and stake preferences
    
    ⚠️ EDUCATIONAL NOTE:
        Represents account for coordinated bot operation.
    """
    account_id: str = field(default_factory=lambda: str(uuid4()))
    nickname: str = "Unnamed"
    status: AccountStatus = AccountStatus.IDLE
    window_info: WindowInfo = field(default_factory=WindowInfo)
    roi_configured: bool = False
    poker_client: PokerClient = PokerClient.UNKNOWN
    bot_running: bool = False
    room: str = "pokerstars"
    notes: str = ""
    balance: float = 0.0  # Available chip balance (for buy-in filtering)
    game_preferences: Optional['GamePreferences'] = None
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            'account_id': self.account_id,
            'nickname': self.nickname,
            'status': self.status.value,
            'window_info': {
                'window_id': self.window_info.window_id,
                'window_title': self.window_info.window_title,
                'window_type': self.window_info.window_type.value,
                'process_name': self.window_info.process_name,
                'position': self.window_info.position,
                'emulator_serial': self.window_info.emulator_serial,
            },
            'roi_configured': self.roi_configured,
            'bot_running': self.bot_running,
            'room': self.room,
            'notes': self.notes,
            'balance': self.balance
        }
        
        if self.game_preferences:
            result['game_preferences'] = self.game_preferences.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Account':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
        
        Returns:
            Account instance
        """
        window_data = data.get('window_info', {})
        window_info = WindowInfo(
            window_id=window_data.get('window_id'),
            window_title=window_data.get('window_title'),
            window_type=WindowType(window_data.get('window_type', 'unknown')),
            process_name=window_data.get('process_name'),
            position=window_data.get('position'),
            emulator_serial=window_data.get('emulator_serial'),
        )
        
        # Load game preferences if available
        game_prefs = None
        if 'game_preferences' in data:
            from launcher.models.game_settings import GamePreferences
            game_prefs = GamePreferences.from_dict(data['game_preferences'])
        
        return cls(
            account_id=data['account_id'],
            nickname=data['nickname'],
            status=AccountStatus(data.get('status', 'idle')),
            window_info=window_info,
            roi_configured=data.get('roi_configured', False),
            bot_running=data.get('bot_running', False),
            room=data.get('room', 'pokerstars'),
            notes=data.get('notes', ''),
            balance=float(data.get('balance', 0.0)),
            game_preferences=game_prefs,
        )
    
    def is_ready_to_run(self) -> bool:
        """
        Check if account is ready to run bot.
        
        Returns:
            True if ready
        """
        return (
            self.window_info.is_captured() and
            self.roi_configured and
            not self.bot_running and
            self.status != AccountStatus.ERROR
        )


# Educational example
if __name__ == "__main__":
    print("=" * 60)
    print("Account Model - Educational Research")
    print("=" * 60)
    print()
    
    # Create account
    account = Account(
        nickname="TestBot001",
        room="pokerstars"
    )
    
    print(f"Account created:")
    print(f"  ID: {account.account_id[:8]}...")
    print(f"  Nickname: {account.nickname}")
    print(f"  Status: {account.status.value}")
    print(f"  Room: {account.room}")
    print(f"  Window captured: {account.window_info.is_captured()}")
    print(f"  ROI configured: {account.roi_configured}")
    print(f"  Ready to run: {account.is_ready_to_run()}")
    print()
    
    # Simulate window capture
    account.window_info.window_id = "12345"
    account.window_info.window_title = "PokerStars"
    account.window_info.window_type = WindowType.DESKTOP_CLIENT
    
    print(f"After window capture:")
    print(f"  Window captured: {account.window_info.is_captured()}")
    print(f"  Window title: {account.window_info.window_title}")
    print()
    
    # Simulate ROI configuration
    account.roi_configured = True
    account.status = AccountStatus.READY
    
    print(f"After ROI configuration:")
    print(f"  ROI configured: {account.roi_configured}")
    print(f"  Status: {account.status.value}")
    print(f"  Ready to run: {account.is_ready_to_run()}")
    print()
    
    # Convert to dict
    data = account.to_dict()
    print(f"Account as dict: {len(data)} fields")
    print()
    
    print("=" * 60)
    print("Account model demonstration complete")
    print("=" * 60)
