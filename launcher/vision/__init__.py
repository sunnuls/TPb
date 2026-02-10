"""
Vision Module - Automatic UI Detection.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from launcher.vision.auto_ui_detector import AutoUIDetector, UIElement, UIElementType
from launcher.vision.auto_navigator import AutoNavigator, NavigationResult
from launcher.vision.window_capturer import WindowCapturer

__all__ = [
    'AutoUIDetector',
    'UIElement',
    'UIElementType',
    'AutoNavigator',
    'NavigationResult',
    'WindowCapturer'
]
