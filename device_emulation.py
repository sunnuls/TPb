#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
device_emulation.py — Fingerprint spoofing для масштабирования 100+ ботов.

Phase 2 of scaling.md.

Генерирует уникальные, реалистичные fingerprints для каждого бота,
чтобы каждый выглядел как отдельное устройство/браузер.

Компоненты:
- DeviceFingerprint: полный набор параметров устройства
- BrowserProfile: User-Agent + HTTP заголовки
- ScreenProfile: разрешение, DPI, color depth
- SystemProfile: OS, timezone, language, platform
- HardwareProfile: CPU cores, RAM, GPU vendor
- FingerprintGenerator: детерминированная генерация по seed/bot_id
- FingerprintStore: хранилище fingerprints с персистентностью
- HeaderInjector: применяет fingerprint к HTTP запросам

Каждый бот получает:
- Уникальный User-Agent (реалистичный, из базы)
- Уникальное разрешение экрана
- Уникальный timezone / language
- Уникальный canvas/WebGL hash (stub)
- Консистентный fingerprint (один bot_id → один fingerprint)

Usage::

    gen = FingerprintGenerator()
    fp = gen.generate("bot_42")
    headers = fp.to_headers()

    store = FingerprintStore(gen)
    fp = store.get("bot_42")  # cached, consistent

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OSType(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


class BrowserType(str, Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


# ---------------------------------------------------------------------------
# Realistic data pools
# ---------------------------------------------------------------------------

_CHROME_VERSIONS = [
    "120.0.6099.130", "120.0.6099.199", "121.0.6167.85",
    "121.0.6167.160", "122.0.6261.69", "122.0.6261.112",
    "123.0.6312.58", "123.0.6312.105", "124.0.6367.60",
    "124.0.6367.118", "125.0.6422.60", "125.0.6422.113",
]

_FIREFOX_VERSIONS = [
    "121.0", "122.0", "122.0.1", "123.0", "123.0.1",
    "124.0", "124.0.1", "125.0", "125.0.1",
]

_EDGE_VERSIONS = [
    "120.0.2210.91", "121.0.2277.83", "122.0.2365.52",
    "123.0.2420.65", "124.0.2478.51", "125.0.2535.51",
]

_SAFARI_VERSIONS = [
    "17.2", "17.2.1", "17.3", "17.3.1", "17.4", "17.4.1",
]

_WINDOWS_VERSIONS = [
    ("10", "10.0"), ("11", "10.0"),
]

_MACOS_VERSIONS = [
    ("Sonoma", "14_2_1"), ("Sonoma", "14_3"), ("Sonoma", "14_4"),
    ("Ventura", "13_6_3"), ("Ventura", "13_6_4"),
    ("Monterey", "12_7_2"), ("Monterey", "12_7_3"),
]

_SCREEN_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1600, 900), (2560, 1440), (1280, 720), (1280, 800),
    (1680, 1050), (1920, 1200), (2560, 1600), (3840, 2160),
    (1360, 768), (1024, 768), (1280, 1024),
]

_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "America/Denver", "America/Toronto", "America/Sao_Paulo",
    "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Europe/Moscow", "Europe/Madrid", "Europe/Rome",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
    "Asia/Bangkok", "Australia/Sydney", "Pacific/Auckland",
]

_LANGUAGES = [
    "en-US", "en-GB", "de-DE", "fr-FR", "es-ES",
    "pt-BR", "ru-RU", "ja-JP", "zh-CN", "ko-KR",
    "it-IT", "nl-NL", "pl-PL", "tr-TR", "sv-SE",
]

_GPU_VENDORS = [
    "NVIDIA Corporation", "ATI Technologies Inc.",
    "Intel Inc.", "Google Inc. (NVIDIA)",
    "Google Inc. (Intel)", "Google Inc. (AMD)",
]

_GPU_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
    "Apple GPU",
    "Apple M1",
    "Apple M2",
]


# ---------------------------------------------------------------------------
# Profile dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BrowserProfile:
    """Browser identification."""
    browser_type: BrowserType = BrowserType.CHROME
    version: str = ""
    user_agent: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "browser": self.browser_type.value,
            "version": self.version,
            "user_agent": self.user_agent,
        }


@dataclass
class ScreenProfile:
    """Display parameters."""
    width: int = 1920
    height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "color_depth": self.color_depth,
            "pixel_ratio": self.pixel_ratio,
        }


@dataclass
class SystemProfile:
    """Operating system and locale."""
    os_type: OSType = OSType.WINDOWS
    os_version: str = "10.0"
    platform: str = "Win32"
    timezone: str = "America/New_York"
    timezone_offset: int = -300           # minutes from UTC
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    do_not_track: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os": self.os_type.value,
            "os_version": self.os_version,
            "platform": self.platform,
            "timezone": self.timezone,
            "language": self.language,
        }


@dataclass
class HardwareProfile:
    """Hardware characteristics."""
    cpu_cores: int = 8
    memory_gb: int = 16
    gpu_vendor: str = "Google Inc. (NVIDIA)"
    gpu_renderer: str = ""
    max_touch_points: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "gpu_vendor": self.gpu_vendor,
            "max_touch_points": self.max_touch_points,
        }


@dataclass
class DeviceFingerprint:
    """Complete device fingerprint for one bot."""
    bot_id: str = ""
    browser: BrowserProfile = field(default_factory=BrowserProfile)
    screen: ScreenProfile = field(default_factory=ScreenProfile)
    system: SystemProfile = field(default_factory=SystemProfile)
    hardware: HardwareProfile = field(default_factory=HardwareProfile)

    # Canvas / WebGL hashes (stubs — unique per fingerprint)
    canvas_hash: str = ""
    webgl_hash: str = ""
    audio_hash: str = ""

    # Font list fingerprint (subset of common fonts)
    installed_fonts: List[str] = field(default_factory=list)

    created_at: float = field(default_factory=time.time)

    def to_headers(self) -> Dict[str, str]:
        """Generate HTTP headers matching this fingerprint."""
        headers: Dict[str, str] = {
            "User-Agent": self.browser.user_agent,
            "Accept-Language": self._accept_language(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }
        if self.system.do_not_track:
            headers["DNT"] = "1"

        # Browser-specific headers
        if self.browser.browser_type == BrowserType.CHROME:
            headers["Sec-Ch-Ua"] = self._sec_ch_ua()
            headers["Sec-Ch-Ua-Platform"] = f'"{self._platform_name()}"'
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-User"] = "?1"

        return headers

    def to_dict(self) -> Dict[str, Any]:
        """Full fingerprint as dict (for serialization)."""
        return {
            "bot_id": self.bot_id,
            "browser": self.browser.to_dict(),
            "screen": self.screen.to_dict(),
            "system": self.system.to_dict(),
            "hardware": self.hardware.to_dict(),
            "canvas_hash": self.canvas_hash,
            "webgl_hash": self.webgl_hash,
            "audio_hash": self.audio_hash,
            "installed_fonts": self.installed_fonts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceFingerprint":
        """Restore fingerprint from dict."""
        fp = cls(bot_id=data.get("bot_id", ""))

        b = data.get("browser", {})
        fp.browser = BrowserProfile(
            browser_type=BrowserType(b.get("browser", "chrome")),
            version=b.get("version", ""),
            user_agent=b.get("user_agent", ""),
        )

        s = data.get("screen", {})
        fp.screen = ScreenProfile(
            width=s.get("width", 1920),
            height=s.get("height", 1080),
            color_depth=s.get("color_depth", 24),
            pixel_ratio=s.get("pixel_ratio", 1.0),
        )

        sys_ = data.get("system", {})
        fp.system = SystemProfile(
            os_type=OSType(sys_.get("os", "windows")),
            os_version=sys_.get("os_version", "10.0"),
            platform=sys_.get("platform", "Win32"),
            timezone=sys_.get("timezone", "America/New_York"),
            language=sys_.get("language", "en-US"),
        )

        hw = data.get("hardware", {})
        fp.hardware = HardwareProfile(
            cpu_cores=hw.get("cpu_cores", 8),
            memory_gb=hw.get("memory_gb", 16),
            gpu_vendor=hw.get("gpu_vendor", ""),
        )

        fp.canvas_hash = data.get("canvas_hash", "")
        fp.webgl_hash = data.get("webgl_hash", "")
        fp.audio_hash = data.get("audio_hash", "")
        fp.installed_fonts = data.get("installed_fonts", [])

        return fp

    def _accept_language(self) -> str:
        langs = self.system.languages or [self.system.language]
        parts = []
        for i, lang in enumerate(langs):
            if i == 0:
                parts.append(lang)
            else:
                q = max(0.1, round(1.0 - i * 0.2, 1))
                parts.append(f"{lang};q={q}")
        return ",".join(parts)

    def _sec_ch_ua(self) -> str:
        ver = self.browser.version.split(".")[0] if self.browser.version else "120"
        if self.browser.browser_type == BrowserType.CHROME:
            return (
                f'"Not_A Brand";v="8", "Chromium";v="{ver}", '
                f'"Google Chrome";v="{ver}"'
            )
        elif self.browser.browser_type == BrowserType.EDGE:
            return (
                f'"Not_A Brand";v="8", "Chromium";v="{ver}", '
                f'"Microsoft Edge";v="{ver}"'
            )
        return ""

    def _platform_name(self) -> str:
        m = {
            OSType.WINDOWS: "Windows",
            OSType.MACOS: "macOS",
            OSType.LINUX: "Linux",
            OSType.ANDROID: "Android",
            OSType.IOS: "iOS",
        }
        return m.get(self.system.os_type, "Windows")


# ---------------------------------------------------------------------------
# Common font subsets
# ---------------------------------------------------------------------------

_COMMON_FONTS = [
    "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
    "Consolas", "Courier New", "Georgia", "Helvetica", "Impact",
    "Lucida Console", "Lucida Sans", "Microsoft Sans Serif",
    "Palatino Linotype", "Segoe UI", "Tahoma", "Times New Roman",
    "Trebuchet MS", "Verdana",
]

_MACOS_FONTS = [
    "Helvetica Neue", "San Francisco", "Menlo", "Monaco",
    "Avenir", "Futura", "Gill Sans",
]

_LINUX_FONTS = [
    "Liberation Sans", "Liberation Mono", "DejaVu Sans",
    "Noto Sans", "Ubuntu",
]


# ---------------------------------------------------------------------------
# FingerprintGenerator
# ---------------------------------------------------------------------------

class FingerprintGenerator:
    """Generates unique, realistic, deterministic fingerprints per bot_id.

    Uses bot_id as seed to produce consistent results:
    same bot_id → same fingerprint every time.
    """

    def __init__(self, base_seed: int = 0):
        self._base_seed = base_seed

    def generate(self, bot_id: str) -> DeviceFingerprint:
        """Generate a complete fingerprint for bot_id."""
        rng = self._make_rng(bot_id)

        # 1. OS
        os_type, os_version, platform_str = self._pick_os(rng)

        # 2. Browser
        browser_type = self._pick_browser(rng, os_type)
        browser_version = self._pick_browser_version(rng, browser_type)
        user_agent = self._build_user_agent(
            rng, browser_type, browser_version, os_type, os_version,
        )

        # 3. Screen
        width, height = rng.choice(_SCREEN_RESOLUTIONS)
        pixel_ratio = rng.choice([1.0, 1.0, 1.0, 1.25, 1.5, 2.0])
        color_depth = rng.choice([24, 24, 24, 32])

        # 4. Locale
        language = rng.choice(_LANGUAGES)
        secondary = rng.choice([l for l in _LANGUAGES if l != language][:5])
        timezone = rng.choice(_TIMEZONES)

        # 5. Hardware
        cpu_cores = rng.choice([2, 4, 4, 6, 8, 8, 12, 16])
        memory_gb = rng.choice([4, 8, 8, 16, 16, 32])
        gpu_vendor = rng.choice(_GPU_VENDORS)
        gpu_renderer = rng.choice(_GPU_RENDERERS)
        touch = 0 if os_type in (OSType.WINDOWS, OSType.LINUX, OSType.MACOS) else rng.choice([1, 5, 10])

        # 6. Hashes (deterministic pseudo-random)
        canvas_hash = self._gen_hash(rng, "canvas")
        webgl_hash = self._gen_hash(rng, "webgl")
        audio_hash = self._gen_hash(rng, "audio")

        # 7. Fonts
        fonts = self._pick_fonts(rng, os_type)

        return DeviceFingerprint(
            bot_id=bot_id,
            browser=BrowserProfile(
                browser_type=browser_type,
                version=browser_version,
                user_agent=user_agent,
            ),
            screen=ScreenProfile(
                width=width,
                height=height,
                color_depth=color_depth,
                pixel_ratio=pixel_ratio,
            ),
            system=SystemProfile(
                os_type=os_type,
                os_version=os_version,
                platform=platform_str,
                timezone=timezone,
                language=language,
                languages=[language, secondary],
                do_not_track=rng.random() < 0.1,
            ),
            hardware=HardwareProfile(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                gpu_vendor=gpu_vendor,
                gpu_renderer=gpu_renderer,
                max_touch_points=touch,
            ),
            canvas_hash=canvas_hash,
            webgl_hash=webgl_hash,
            audio_hash=audio_hash,
            installed_fonts=fonts,
        )

    # -- Internal helpers --

    def _make_rng(self, bot_id: str) -> random.Random:
        seed_bytes = hashlib.sha256(
            f"{self._base_seed}:{bot_id}".encode()
        ).digest()
        seed_int = int.from_bytes(seed_bytes[:8], "big")
        return random.Random(seed_int)

    @staticmethod
    def _pick_os(rng: random.Random) -> Tuple[OSType, str, str]:
        roll = rng.random()
        if roll < 0.65:
            name, ver = rng.choice(_WINDOWS_VERSIONS)
            return OSType.WINDOWS, ver, "Win32"
        elif roll < 0.85:
            name, ver = rng.choice(_MACOS_VERSIONS)
            return OSType.MACOS, ver, "MacIntel"
        else:
            return OSType.LINUX, "x86_64", "Linux x86_64"

    @staticmethod
    def _pick_browser(rng: random.Random, os_type: OSType) -> BrowserType:
        if os_type == OSType.MACOS:
            weights = [0.45, 0.15, 0.30, 0.10]  # Chrome, FF, Safari, Edge
        elif os_type == OSType.LINUX:
            weights = [0.55, 0.35, 0.0, 0.10]
        else:
            weights = [0.60, 0.15, 0.0, 0.25]

        browsers = [BrowserType.CHROME, BrowserType.FIREFOX,
                    BrowserType.SAFARI, BrowserType.EDGE]
        # Filter zero-weight
        pool = [(b, w) for b, w in zip(browsers, weights) if w > 0]
        total = sum(w for _, w in pool)
        r = rng.uniform(0, total)
        cumulative = 0.0
        for b, w in pool:
            cumulative += w
            if r <= cumulative:
                return b
        return pool[-1][0]

    @staticmethod
    def _pick_browser_version(rng: random.Random, bt: BrowserType) -> str:
        if bt == BrowserType.CHROME:
            return rng.choice(_CHROME_VERSIONS)
        elif bt == BrowserType.FIREFOX:
            return rng.choice(_FIREFOX_VERSIONS)
        elif bt == BrowserType.EDGE:
            return rng.choice(_EDGE_VERSIONS)
        elif bt == BrowserType.SAFARI:
            return rng.choice(_SAFARI_VERSIONS)
        return ""

    @staticmethod
    def _build_user_agent(
        rng: random.Random,
        bt: BrowserType,
        version: str,
        os_type: OSType,
        os_version: str,
    ) -> str:
        if bt == BrowserType.CHROME:
            if os_type == OSType.WINDOWS:
                return (
                    f"Mozilla/5.0 (Windows NT {os_version}; Win64; x64) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{version} Safari/537.36"
                )
            elif os_type == OSType.MACOS:
                mac_ver = os_version.replace("_", ".")
                return (
                    f"Mozilla/5.0 (Macintosh; Intel Mac OS X {os_version}) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{version} Safari/537.36"
                )
            else:
                return (
                    f"Mozilla/5.0 (X11; Linux x86_64) "
                    f"AppleWebKit/537.36 (KHTML, like Gecko) "
                    f"Chrome/{version} Safari/537.36"
                )

        elif bt == BrowserType.FIREFOX:
            if os_type == OSType.WINDOWS:
                return (
                    f"Mozilla/5.0 (Windows NT {os_version}; Win64; x64; rv:{version}) "
                    f"Gecko/20100101 Firefox/{version}"
                )
            elif os_type == OSType.MACOS:
                return (
                    f"Mozilla/5.0 (Macintosh; Intel Mac OS X {os_version}; rv:{version}) "
                    f"Gecko/20100101 Firefox/{version}"
                )
            else:
                return (
                    f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}) "
                    f"Gecko/20100101 Firefox/{version}"
                )

        elif bt == BrowserType.SAFARI:
            wk = rng.choice(["605.1.15", "605.1.15"])
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X {os_version}) "
                f"AppleWebKit/{wk} (KHTML, like Gecko) "
                f"Version/{version} Safari/{wk}"
            )

        elif bt == BrowserType.EDGE:
            return (
                f"Mozilla/5.0 (Windows NT {os_version}; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{version} Safari/537.36 Edg/{version}"
            )

        return "Mozilla/5.0"

    @staticmethod
    def _gen_hash(rng: random.Random, domain: str) -> str:
        raw = f"{domain}:{rng.getrandbits(256)}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _pick_fonts(rng: random.Random, os_type: OSType) -> List[str]:
        base = list(_COMMON_FONTS)
        if os_type == OSType.MACOS:
            base.extend(_MACOS_FONTS)
        elif os_type == OSType.LINUX:
            base.extend(_LINUX_FONTS)

        # Pick a random subset (realistic: not all fonts installed)
        count = rng.randint(max(10, len(base) // 2), len(base))
        return sorted(rng.sample(base, min(count, len(base))))


# ---------------------------------------------------------------------------
# FingerprintStore — cache + optional persistence
# ---------------------------------------------------------------------------

class FingerprintStore:
    """Stores fingerprints per bot, optionally saves to disk.

    Ensures each bot always gets the same fingerprint.
    """

    def __init__(
        self,
        generator: Optional[FingerprintGenerator] = None,
        persist_path: Optional[str | Path] = None,
    ):
        self._generator = generator or FingerprintGenerator()
        self._cache: Dict[str, DeviceFingerprint] = {}
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load()

    def get(self, bot_id: str) -> DeviceFingerprint:
        """Get or generate fingerprint for bot."""
        if bot_id in self._cache:
            return self._cache[bot_id]

        fp = self._generator.generate(bot_id)
        self._cache[bot_id] = fp
        return fp

    def invalidate(self, bot_id: str):
        """Remove cached fingerprint for bot (regenerated on next get)."""
        self._cache.pop(bot_id, None)

    def clear(self):
        """Clear all cached fingerprints."""
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)

    def save(self):
        """Persist all fingerprints to disk."""
        if not self._persist_path:
            return
        data = {bid: fp.to_dict() for bid, fp in self._cache.items()}
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved %d fingerprints to %s", len(data), self._persist_path)

    def _load(self):
        try:
            raw = self._persist_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            for bid, fp_dict in data.items():
                self._cache[bid] = DeviceFingerprint.from_dict(fp_dict)
            logger.info("Loaded %d fingerprints from %s",
                        len(self._cache), self._persist_path)
        except Exception as e:
            logger.warning("Failed to load fingerprints: %s", e)

    def all_fingerprints(self) -> Dict[str, DeviceFingerprint]:
        """Return copy of all cached fingerprints."""
        return dict(self._cache)


# ---------------------------------------------------------------------------
# HeaderInjector — applies fingerprint to request headers
# ---------------------------------------------------------------------------

class HeaderInjector:
    """Applies a DeviceFingerprint's headers to HTTP requests."""

    def __init__(self, store: FingerprintStore):
        self._store = store

    def inject(self, bot_id: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers for bot, merged with optional extra headers."""
        fp = self._store.get(bot_id)
        fp_headers = fp.to_headers()
        if headers:
            fp_headers.update(headers)
        return fp_headers

    def inject_to_session(self, bot_id: str, session: Any):
        """Inject fingerprint headers into an httpx/requests session."""
        fp_headers = self._store.get(bot_id).to_headers()
        if hasattr(session, "headers") and hasattr(session.headers, "update"):
            session.headers.update(fp_headers)
