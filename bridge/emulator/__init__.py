"""
Emulator backend package — mobile emulator support for HIVE bots.

Provides a hardware-agnostic capture/input abstraction (`CaptureBackend`)
so that `BotInstance` can drive either a Windows desktop poker client
(via Win32/HWND, existing behaviour) or an Android emulator instance
(via ADB, new behaviour) without changing the decision/coordination layer.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from bridge.emulator.capture_backend import CaptureBackend, CaptureBackendError
from bridge.emulator.adb_backend import ADBBackend, ADBDeviceInfo

__all__ = [
    "CaptureBackend",
    "CaptureBackendError",
    "ADBBackend",
    "ADBDeviceInfo",
]
