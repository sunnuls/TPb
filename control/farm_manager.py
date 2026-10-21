"""
FarmManager — ADB device pool control for HIVE CONTROL.

All adb calls go through subprocess with timeouts. Never hangs, never
raises on adb errors (returns offline / empty instead).

Local educational use only.
"""

from __future__ import annotations

import io
import logging
import re
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

_ADB_TIMEOUT = 5.0
_LIST_CACHE_TTL = 10.0
_AWAKE_CACHE_TTL = 5.0
_RETRY_SLEEP = 0.15


def _is_black(png_bytes: bytes, threshold: float = 8.0) -> bool:
    """True if PNG is missing, broken, or nearly all-black (subsampled)."""
    if not png_bytes:
        return True
    try:
        img = Image.open(io.BytesIO(png_bytes)).convert("L")
        raw = img.tobytes()
        sample = raw[::16]
        if not sample:
            return True
        mean = sum(sample) / len(sample)
        return mean < threshold
    except Exception:
        return True


class FarmManager:
    """Thin ADB facade for emulator / device farm control."""

    def __init__(self, adb_path: Optional[str] = None):
        self._adb = adb_path if adb_path is not None else (shutil.which("adb") or "")
        self._list_cache: List[dict] = []
        self._list_cache_ts: float = 0.0
        self._last_good: dict[str, bytes] = {}
        self._tuned_serials: Set[str] = set()
        self._awake_cache: Dict[str, Tuple[float, bool]] = {}

    @property
    def adb_available(self) -> bool:
        return bool(self._adb)

    def _run(
        self,
        args: List[str],
        *,
        timeout: float = _ADB_TIMEOUT,
        binary: bool = False,
    ) -> Tuple[int, bytes | str]:
        """Run adb; return (returncode, stdout). Never raises."""
        if not self._adb:
            return 1, b"" if binary else ""
        cmd = [self._adb, *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            out = proc.stdout if binary else proc.stdout.decode("utf-8", errors="replace")
            return proc.returncode, out
        except subprocess.TimeoutExpired:
            logger.warning("adb timeout: %s", " ".join(cmd))
            return 1, b"" if binary else ""
        except OSError as exc:
            logger.warning("adb OSError: %s", exc)
            return 1, b"" if binary else ""

    def _apply_farm_settings(self, serial: str) -> None:
        self._run(
            ["-s", serial, "shell", "svc", "power", "stayon", "usb"],
            timeout=_ADB_TIMEOUT,
        )
        self._run(
            ["-s", serial, "shell", "settings", "put", "system", "screen_off_timeout", "1800000"],
            timeout=_ADB_TIMEOUT,
        )
        self._run(
            ["-s", serial, "shell", "settings", "put", "global", "lockscreen_disabled", "1"],
            timeout=_ADB_TIMEOUT,
        )

    def is_awake(self, serial: str) -> bool:
        now = time.time()
        cached = self._awake_cache.get(serial)
        if cached and (now - cached[0]) < _AWAKE_CACHE_TTL:
            return cached[1]
        rc, out = self._run(["-s", serial, "shell", "dumpsys", "power"], timeout=_ADB_TIMEOUT)
        awake = False
        if rc == 0 and isinstance(out, str):
            awake = "mWakefulness=Awake" in out
        self._awake_cache[serial] = (now, awake)
        return awake

    def _with_awake(self, device: dict) -> dict:
        row = dict(device)
        if row.get("status") == "online":
            row["awake"] = self.is_awake(row["serial"])
        else:
            row["awake"] = False
        return row

    def list_devices(self) -> List[dict]:
        """Return cached device list: {serial, model, resolution, status, awake}."""
        now = time.time()
        if self._list_cache and (now - self._list_cache_ts) < _LIST_CACHE_TTL:
            return [self._with_awake(d) for d in self._list_cache]

        devices: List[dict] = []
        if not self._adb:
            self._list_cache = []
            self._list_cache_ts = now
            return []

        rc, out = self._run(["devices", "-l"], timeout=_ADB_TIMEOUT)
        if rc != 0 or not isinstance(out, str):
            self._list_cache = []
            self._list_cache_ts = now
            return []

        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            status = "online" if state == "device" else "offline"
            model = ""
            resolution = ""
            if status == "online":
                if serial not in self._tuned_serials:
                    self._apply_farm_settings(serial)
                    self._tuned_serials.add(serial)
                model = self._getprop(serial, "ro.product.model") or serial
                resolution = self._wm_size(serial)
            else:
                model = serial
            devices.append(
                {
                    "serial": serial,
                    "model": model,
                    "resolution": resolution,
                    "status": status,
                    "awake": False,
                }
            )

        self._list_cache = devices
        self._list_cache_ts = now
        return [self._with_awake(d) for d in devices]

    def _getprop(self, serial: str, prop: str) -> str:
        rc, out = self._run(["-s", serial, "shell", "getprop", prop], timeout=_ADB_TIMEOUT)
        if rc != 0 or not isinstance(out, str):
            return ""
        return out.strip()

    def _wm_size(self, serial: str) -> str:
        rc, out = self._run(["-s", serial, "shell", "wm", "size"], timeout=_ADB_TIMEOUT)
        if rc != 0 or not isinstance(out, str):
            return ""
        m = re.search(r"(\d+)\s*x\s*(\d+)", out, re.IGNORECASE)
        if not m:
            return ""
        return f"{m.group(1)}x{m.group(2)}"

    def _capture(self, serial: str) -> bytes:
        rc, out = self._run(
            ["-s", serial, "exec-out", "screencap", "-p"],
            timeout=_ADB_TIMEOUT,
            binary=True,
        )
        if rc != 0 or not isinstance(out, (bytes, bytearray)):
            return b""
        return bytes(out)

    def screenshot(self, serial: str, retries: int = 3) -> tuple[bytes, bool]:
        """Return (png_bytes, is_stale). Retries past black frames; may serve last good."""
        last_black = b""
        for attempt in range(max(1, retries)):
            png = self._capture(serial)
            last_black = png
            if png and not _is_black(png):
                self._last_good[serial] = png
                return png, False
            if attempt < retries - 1:
                time.sleep(_RETRY_SLEEP)

        self.keyevent(serial, 224)
        self._run(
            ["-s", serial, "shell", "svc", "power", "stayon", "usb"],
            timeout=_ADB_TIMEOUT,
        )
        png = self._capture(serial)
        if png and not _is_black(png):
            self._last_good[serial] = png
            return png, False
        if serial in self._last_good:
            return self._last_good[serial], True
        return (png or last_black), True

    def tap(self, serial: str, x: int, y: int) -> None:
        self._run(
            ["-s", serial, "shell", "input", "tap", str(int(x)), str(int(y))],
            timeout=_ADB_TIMEOUT,
        )

    def swipe(
        self,
        serial: str,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        ms: int,
    ) -> None:
        self._run(
            [
                "-s",
                serial,
                "shell",
                "input",
                "swipe",
                str(int(x1)),
                str(int(y1)),
                str(int(x2)),
                str(int(y2)),
                str(int(ms)),
            ],
            timeout=_ADB_TIMEOUT,
        )

    def keyevent(self, serial: str, key: int | str) -> None:
        self._run(
            ["-s", serial, "shell", "input", "keyevent", str(key)],
            timeout=_ADB_TIMEOUT,
        )

    def input_text(self, serial: str, text: str) -> None:
        safe = (text or "").replace(" ", "%s")
        self._run(
            ["-s", serial, "shell", "input", "text", safe],
            timeout=_ADB_TIMEOUT,
        )

    def is_online(self, serial: str) -> bool:
        if not self._adb or not serial:
            return False
        for d in self.list_devices():
            if d.get("serial") == serial and d.get("status") == "online":
                return True
        return False

    def invalidate_cache(self) -> None:
        self._list_cache = []
        self._list_cache_ts = 0.0
        self._awake_cache.clear()
