"""
ADBBackend — CaptureBackend implementation for Android emulator instances.

Drives a single Android emulator instance (LDPlayer, MuMu, BlueStacks, Nox,
stock AVD, ...) over ADB. Any emulator that exposes an ADB endpoint works
the same way — capture is `adb exec-out screencap`, input is `adb shell input`.

This mirrors the existing `bridge/screen_capture.py` (Win32/HWND) and
`bridge/action/real_executor.py` (pyautogui) pair, but for the ADB
transport, and implements the shared `CaptureBackend` contract so the
rest of the pipeline (ROI detection, action execution, HIVE coordination)
does not need to know which transport is active.

DRY-RUN MODE: All real ADB commands are gated behind the same
`SafetyFramework` used everywhere else in `bridge/`. In DRY_RUN (default)
mode, `click`/`swipe`/`type_text`/`key_event` are logged only; `capture()`
still performs the (read-only) screenshot so vision/ROI code can be
developed and tested without flipping to UNSAFE mode.

Usage::

    backend = ADBBackend(serial="127.0.0.1:5555")
    if backend.is_connected():
        frame = backend.capture()
        backend.click(540, 1200)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import logging
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from bridge.emulator.capture_backend import BackendResolution, CaptureBackend
from bridge.safety import SafetyFramework, get_safety

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    CV2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default timeout for ADB subprocess calls (seconds).
DEFAULT_ADB_TIMEOUT = 8.0


@dataclass
class ADBDeviceInfo:
    """One line of `adb devices -l` output, parsed."""
    serial: str
    state: str = "unknown"        # device / offline / unauthorized
    model: str = ""
    transport_id: str = ""

    def is_ready(self) -> bool:
        return self.state == "device"


def list_adb_devices(adb_path: str = "adb", timeout: float = DEFAULT_ADB_TIMEOUT) -> List[ADBDeviceInfo]:
    """Return all devices/emulators currently visible to ADB.

    Runs ``adb devices -l`` and parses the output. Returns an empty list
    (never raises) if `adb` is not installed or the server can't be reached —
    callers should treat that the same as "no emulators available".
    """
    if shutil.which(adb_path) is None and adb_path == "adb":
        logger.warning("list_adb_devices: 'adb' not found on PATH")
        return []

    try:
        result = subprocess.run(
            [adb_path, "devices", "-l"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("list_adb_devices: adb invocation failed: %s", exc)
        return []

    devices: List[ADBDeviceInfo] = []
    for line in result.stdout.splitlines()[1:]:  # skip "List of devices attached"
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial, state = parts[0], parts[1] if len(parts) > 1 else "unknown"
        model = ""
        transport_id = ""
        for token in parts[2:]:
            if token.startswith("model:"):
                model = token.split(":", 1)[1]
            elif token.startswith("transport_id:"):
                transport_id = token.split(":", 1)[1]
        devices.append(ADBDeviceInfo(serial=serial, state=state, model=model, transport_id=transport_id))

    return devices


class ADBBackend(CaptureBackend):
    """
    CaptureBackend for a single Android emulator instance, addressed by
    its ADB serial (e.g. "127.0.0.1:5555" for LDPlayer/MuMu, or
    "emulator-5554" for a stock AVD).

    Real taps/swipes/text-input require SafetyFramework UNSAFE mode,
    exactly like `RealActionExecutor` for the desktop path. `capture()`
    is always real (read-only) so vision development can proceed safely.
    """

    def __init__(
        self,
        serial: str,
        adb_path: str = "adb",
        timeout: float = DEFAULT_ADB_TIMEOUT,
        safety: Optional[SafetyFramework] = None,
    ) -> None:
        self.serial = serial
        self.adb_path = adb_path
        self.timeout = timeout
        self.safety = safety or get_safety()
        self._last_resolution: Optional[BackendResolution] = None
        self._consecutive_failures = 0

        logger.info("ADBBackend created for serial=%s", serial)

    def __repr__(self) -> str:
        return f"ADBBackend(serial={self.serial!r})"

    # ── Connection state ─────────────────────────────────────────────────

    def is_connected(self) -> bool:
        devices = list_adb_devices(self.adb_path, timeout=self.timeout)
        return any(d.serial == self.serial and d.is_ready() for d in devices)

    def get_resolution(self) -> Optional[BackendResolution]:
        if self._last_resolution is not None:
            return self._last_resolution

        out = self._adb_shell(["wm", "size"])
        if not out:
            return None
        # Expected: "Physical size: 720x1280"
        try:
            size_str = out.strip().split(":")[-1].strip()
            w_str, h_str = size_str.lower().split("x")
            self._last_resolution = BackendResolution(width=int(w_str), height=int(h_str))
            return self._last_resolution
        except (ValueError, IndexError):
            logger.warning("ADBBackend(%s): could not parse 'wm size' output: %r", self.serial, out)
            return None

    # ── Capture (always real — read-only) ───────────────────────────────

    def capture(self) -> Optional[np.ndarray]:
        """Capture a screenshot as BGR numpy array.

        Tries PNG via ``exec-out screencap -p`` first (with CRLF fix for
        Windows). MuMu/LDPlayer often produce corrupt PNG over ADB on
        Windows — falls back to raw ``screencap`` (RGBA framebuffer).
        """
        if not CV2_AVAILABLE:
            logger.warning("ADBBackend(%s): cv2 not available — cannot decode screenshot", self.serial)
            return None

        img = self._capture_png()
        if img is None:
            img = self._capture_raw()

        if img is None:
            self._consecutive_failures += 1
            return None

        self._consecutive_failures = 0
        return img

    def _capture_png(self) -> Optional[np.ndarray]:
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.serial, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("ADBBackend(%s): png capture failed: %s", self.serial, exc)
            return None

        if result.returncode != 0 or not result.stdout:
            return None

        # Windows ADB sometimes injects CR into PNG stream.
        raw = result.stdout.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        try:
            img = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                logger.debug("ADBBackend(%s): png decode failed, will try raw screencap", self.serial)
            return img
        except Exception as exc:
            logger.debug("ADBBackend(%s): png decode error: %s", self.serial, exc)
            return None

    def _capture_raw(self) -> Optional[np.ndarray]:
        """Fallback: decode raw RGBA framebuffer from ``screencap`` (no -p)."""
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.serial, "exec-out", "screencap"],
                capture_output=True, timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("ADBBackend(%s): raw capture failed: %s", self.serial, exc)
            return None

        if result.returncode != 0 or len(result.stdout) < 16:
            return None

        try:
            width, height = struct.unpack("<II", result.stdout[:8])
            pixel_bytes = width * height * 4
            # MuMu/LDPlayer use a 16-byte header; stock AVD often uses 12.
            for header_size in (16, 12):
                payload = result.stdout[header_size: header_size + pixel_bytes]
                if len(payload) != pixel_bytes:
                    continue
                rgba = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 4)
                return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        except Exception as exc:
            logger.warning("ADBBackend(%s): raw decode failed: %s", self.serial, exc)
        return None

    # ── Input (gated by SafetyFramework, like RealActionExecutor) ──────────

    def click(self, x: int, y: int) -> bool:
        if not self._check_unsafe("click"):
            return False
        return self._adb_shell(["input", "tap", str(int(x)), str(int(y))]) is not None

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        if not self._check_unsafe("swipe"):
            return False
        return self._adb_shell([
            "input", "swipe",
            str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms)),
        ]) is not None

    def type_text(self, text: str) -> bool:
        if not self._check_unsafe("type_text"):
            return False
        # ADB's `input text` requires spaces to be escaped as %s.
        escaped = text.replace(" ", "%s")
        return self._adb_shell(["input", "text", escaped]) is not None

    def key_event(self, key: str) -> bool:
        if not self._check_unsafe("key_event"):
            return False
        return self._adb_shell(["input", "keyevent", key]) is not None

    # ── Internal helpers ─────────────────────────────────────────────────

    def _check_unsafe(self, action_name: str) -> bool:
        """Gate real input actions behind SafetyFramework.

        Mirrors `RealActionExecutor`'s convention: real taps/swipes/text
        input only execute in UNSAFE mode. DRY_RUN and SAFE both log-only
        for this generic transport layer — action-level risk classification
        (fold/check/call vs raise/all-in) happens one layer up, the same
        way it does for the desktop `RealActionExecutor` path.
        """
        if not self.safety.is_unsafe_mode():
            logger.info(
                "[%s] ADBBackend(%s): would execute %s (requires --unsafe)",
                self.safety.config.mode.value.upper(), self.serial, action_name,
            )
            return False
        return True

    def _adb_shell(self, args: List[str]) -> Optional[str]:
        """Run `adb -s <serial> shell <args...>` and return stdout, or None on failure."""
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.serial, "shell", *args],
                capture_output=True, text=True, timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("ADBBackend(%s): shell %s failed: %s", self.serial, args, exc)
            return None

        if result.returncode != 0:
            logger.debug(
                "ADBBackend(%s): shell %s returned rc=%d stderr=%s",
                self.serial, args, result.returncode, result.stderr.strip()[:200],
            )
        return result.stdout
