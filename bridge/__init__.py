"""
Bridge Package - HCI Research Prototype (Roadmap3).

Educational use only - for studying external desktop application interfaces.
All operations in DRY-RUN mode by default.

Modules:
- safety: Safety framework with kill-switch and dry-run enforcement
- main: Entry point for bridge mode

Educational HCI Research - Real actions PROHIBITED without authorization.
"""

__version__ = "0.1.0-phase0"
__author__ = "HCI Research Team"

from bridge.safety import (
    SafetyFramework,
    SafetyConfig,
    SafetyMode,
    EmergencyReason,
    get_safety,
    is_dry_run,
    require_unsafe,
    emergency_shutdown
)

__all__ = [
    "SafetyFramework",
    "SafetyConfig",
    "SafetyMode",
    "EmergencyReason",
    "get_safety",
    "is_dry_run",
    "require_unsafe",
    "emergency_shutdown",
]
