"""
Action execution package.

Provides both simulated and real action execution.
"""

from bridge.action.real_executor import (
    ActionCoordinates,
    ExecutionLog,
    ExecutionResult,
    RealActionExecutor,
    RiskLevel,
)

__all__ = [
    'ActionCoordinates',
    'ExecutionLog',
    'ExecutionResult',
    'RealActionExecutor',
    'RiskLevel',
]
