"""
Vision Module - Automatic UI Detection & Auto-Calibration.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from launcher.vision.auto_ui_detector import AutoUIDetector, UIElement, UIElementType
from launcher.vision.auto_navigator import AutoNavigator, NavigationResult
from launcher.vision.window_capturer import WindowCapturer
from launcher.vision.auto_roi_finder import AutoROIFinder, CalibrationResult, Anchor, AnchorType
from launcher.vision.multi_template_matching import (
    TemplateBank,
    MultiTemplateMatcher,
    RobustOCR,
    CardRecognizer,
    NumericRecognizer,
)
from launcher.vision.mouse_curve_generator import (
    MouseCurveGenerator,
    MousePath,
    CurvePoint,
)
from launcher.vision.behavioral_variance import (
    BehaviorProfile,
    BehaviorSampler,
    BehaviorStyle,
    ActionType,
    ProfileMixer,
)
from launcher.vision.anti_pattern_executor import (
    AntiPatternExecutor,
    ClickResult,
    PatternReport,
    PatternDetector,
)
from launcher.vision.lobby_anti_limit import (
    LobbyAntiLimit,
    ScanSource,
    ScanMetric,
    ScanStats,
    CircuitBreaker,
    CircuitState,
    ProxyPool,
    AdaptiveDelay,
)
from launcher.vision.lobby_http_parser import (
    LobbyHTTPParser,
    LobbyHTTPResult,
    HTTPResponse,
    EndpointConfig,
    RoomBackend,
    TokenBucketLimiter,
)
from launcher.vision.lobby_ocr import (
    LobbyOCR,
    LobbyLayout,
    LobbyOCRResult,
    LobbyRowResult,
    RowBBox,
    CellResult,
    ColumnSpec,
)
try:
    from launcher.vision.yolo_region_detector import (
        YOLORegionDetector,
        RegionDetectionResult,
        RegionDetection,
        RegionDatasetGenerator,
        REGION_CLASSES,
    )
except Exception:
    pass  # YOLO/torch DLL issues — graceful degradation

__all__ = [
    'AutoUIDetector',
    'UIElement',
    'UIElementType',
    'AutoNavigator',
    'NavigationResult',
    'WindowCapturer',
    'AutoROIFinder',
    'CalibrationResult',
    'Anchor',
    'AnchorType',
    'TemplateBank',
    'MultiTemplateMatcher',
    'RobustOCR',
    'CardRecognizer',
    'NumericRecognizer',
    'MouseCurveGenerator',
    'MousePath',
    'CurvePoint',
    'LobbyAntiLimit',
    'ScanSource',
    'ScanMetric',
    'ScanStats',
    'CircuitBreaker',
    'CircuitState',
    'ProxyPool',
    'AdaptiveDelay',
    'LobbyHTTPParser',
    'LobbyHTTPResult',
    'HTTPResponse',
    'EndpointConfig',
    'RoomBackend',
    'TokenBucketLimiter',
    'LobbyOCR',
    'LobbyLayout',
    'LobbyOCRResult',
    'LobbyRowResult',
    'RowBBox',
    'CellResult',
    'ColumnSpec',
    'YOLORegionDetector',
    'RegionDetectionResult',
    'RegionDetection',
    'RegionDatasetGenerator',
    'REGION_CLASSES',
    'BehaviorProfile',
    'BehaviorSampler',
    'BehaviorStyle',
    'ActionType',
    'ProfileMixer',
    'AntiPatternExecutor',
    'ClickResult',
    'PatternReport',
    'PatternDetector',
]
