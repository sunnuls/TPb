"""Background ADB capture threads and MJPEG helpers for HIVE CONTROL."""

from __future__ import annotations

import io
import logging
import shutil
import struct
import subprocess
import threading
import time
from collections import deque
from typing import Callable, Dict, Iterator, List, Optional, Tuple

import numpy as np
from PIL import Image

from control.farm_manager import FarmManager, _is_black

logger = logging.getLogger(__name__)

_PACE_SEC = 0.05
_FPS_WINDOW = 5.0
_PIXEL_FORMAT_RGBA_8888 = 1


class FrameSlot:
    """Thread-safe cell holding the latest JPEG (or PNG) frame."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._bytes: bytes = b""
        self._ts: float = 0.0
        self._seq: int = 0

    def put(self, png_bytes: bytes) -> None:
        with self._cond:
            self._seq += 1
            self._bytes = png_bytes
            self._ts = time.time()
            self._cond.notify_all()

    def get(self) -> Tuple[bytes, float, int]:
        with self._cond:
            return self._bytes, self._ts, self._seq

    def wait_seq(self, last_seq: int, timeout: float = 1.0) -> Tuple[bytes, float, int]:
        with self._cond:
            if self._seq != last_seq:
                return self._bytes, self._ts, self._seq
            self._cond.wait(timeout=timeout)
            return self._bytes, self._ts, self._seq


def raw_capture(serial: str, adb_path: Optional[str] = None) -> bytes:
    """Raw `screencap` (RGBA_8888) encoded to JPEG on the PC. Empty bytes on failure."""
    adb = adb_path or shutil.which("adb") or ""
    if not adb or not serial:
        return b""
    try:
        proc = subprocess.run(
            [adb, "-s", serial, "exec-out", "screencap"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return b""
    if proc.returncode != 0 or not proc.stdout or len(proc.stdout) < 12:
        return b""
    width, height, fmt = struct.unpack_from("<III", proc.stdout, 0)
    if fmt != _PIXEL_FORMAT_RGBA_8888 or width <= 0 or height <= 0:
        return b""
    need = height * width * 4
    payload = proc.stdout[12 : 12 + need]
    if len(payload) < need:
        return b""
    try:
        rgba = np.frombuffer(payload, dtype=np.uint8).reshape((height, width, 4))
        bgr = np.ascontiguousarray(rgba[:, :, :3])
        img = Image.fromarray(bgr).convert("RGB")
        buf = io.BytesIO()
        img.save(
            buf,
            format="JPEG",
            quality=80,
            optimize=True,
            subsampling="4:2:0",
        )
        jpeg = buf.getvalue()
    except Exception:
        return b""
    return jpeg if len(jpeg) > 100 else b""


def png_to_jpeg(png_bytes: bytes, quality: int = 80) -> bytes:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _as_jpeg(frame: bytes) -> bytes:
    if frame[:2] == b"\xff\xd8":
        return frame
    return png_to_jpeg(frame, quality=80)


class CaptureThread(threading.Thread):
    """Daemon capture loop for one serial."""

    def __init__(
        self,
        serial: str,
        slot: FrameSlot,
        farm: Optional[FarmManager] = None,
        capture_fn: Optional[Callable[[], bytes]] = None,
        pace: float = _PACE_SEC,
    ) -> None:
        super().__init__(daemon=True, name=f"hive-cap-{serial}")
        self.serial = serial
        self.slot = slot
        self._farm = farm
        self._capture_fn = capture_fn
        self._pace = max(0.01, float(pace))
        self._halt = threading.Event()
        self.frames = 0
        self.mode = "inject" if capture_fn is not None else "raw"
        self._frame_times: deque[float] = deque()
        self._times_lock = threading.Lock()

    def stop(self) -> None:
        self._halt.set()

    def _grab(self) -> bytes:
        if self._capture_fn is not None:
            try:
                return self._capture_fn() or b""
            except Exception:
                return b""
        adb = (self._farm._adb if self._farm else "") or shutil.which("adb") or ""
        if self.mode != "png":
            jpeg = raw_capture(self.serial, adb)
            if jpeg and len(jpeg) > 100:
                self.mode = "raw"
                return jpeg
            self.mode = "png"
        if self._farm is None:
            return b""
        try:
            return self._farm._capture(self.serial)
        except Exception:
            return b""

    def stats(self) -> dict:
        now = time.time()
        with self._times_lock:
            while self._frame_times and now - self._frame_times[0] > _FPS_WINDOW:
                self._frame_times.popleft()
            times = list(self._frame_times)
        fps = 0.0
        if len(times) >= 2:
            span = now - times[0]
            if span > 0:
                fps = len(times) / span
        elif len(times) == 1:
            span = max(now - times[0], 1e-3)
            fps = 1.0 / span if span <= _FPS_WINDOW else 0.0
        _, ts, seq = self.slot.get()
        last_age_ms = int((now - ts) * 1000) if seq else 0
        return {
            "fps": round(fps, 2),
            "frames": self.frames,
            "last_age_ms": last_age_ms,
            "mode": self.mode,
        }

    def run(self) -> None:
        while not self._halt.is_set():
            frame = self._grab()
            if frame and not _is_black(frame):
                self.slot.put(frame)
                self.frames += 1
                with self._times_lock:
                    self._frame_times.append(time.time())
            self._halt.wait(self._pace)


class StreamManager:
    """Owns one CaptureThread + FrameSlot per online serial (process singleton)."""

    def __init__(
        self,
        farm: Optional[FarmManager] = None,
        capture_fn: Optional[Callable[[], bytes]] = None,
    ) -> None:
        self._farm = farm
        self._capture_fn = capture_fn
        self._lock = threading.Lock()
        self._slots: Dict[str, FrameSlot] = {}
        self._threads: Dict[str, CaptureThread] = {}

    def ensure(self, serial: str) -> FrameSlot:
        with self._lock:
            existing = self._threads.get(serial)
            if existing is not None:
                return self._slots[serial]
            slot = FrameSlot()
            thread = CaptureThread(
                serial,
                slot,
                farm=self._farm,
                capture_fn=self._capture_fn,
            )
            self._slots[serial] = slot
            self._threads[serial] = thread
            thread.start()
            return slot

    def drop(self, serial: str) -> None:
        with self._lock:
            thread = self._threads.pop(serial, None)
            self._slots.pop(serial, None)
        if thread is not None:
            thread.stop()
            thread.join(timeout=1.5)

    def stop_all(self) -> None:
        with self._lock:
            items = list(self._threads.items())
            self._threads.clear()
            self._slots.clear()
        for _serial, thread in items:
            thread.stop()
        deadline = time.time() + 1.8
        for _serial, thread in items:
            remain = max(0.05, deadline - time.time())
            thread.join(timeout=remain)

    def sync(self, devices: List[dict]) -> None:
        online = {
            str(d.get("serial") or "")
            for d in devices
            if d.get("status") == "online" and d.get("serial")
        }
        with self._lock:
            current = set(self._threads)
        for serial in online:
            self.ensure(serial)
        for serial in current - online:
            self.drop(serial)

    def slot(self, serial: str) -> Optional[FrameSlot]:
        with self._lock:
            return self._slots.get(serial)

    def stats(self, serial: str) -> dict:
        with self._lock:
            thread = self._threads.get(serial)
        if thread is None:
            return {"fps": 0.0, "frames": 0, "last_age_ms": 0, "mode": ""}
        return thread.stats()


def iter_mjpeg(
    slot: FrameSlot,
    *,
    max_parts: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
) -> Iterator[bytes]:
    """Yield multipart MJPEG parts. Ping comment after 1s without a new seq."""
    last_seq = -1
    parts = 0
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        data, _ts, seq = slot.wait_seq(last_seq, timeout=1.0)
        if seq == last_seq or not data:
            yield b": ping\r\n\r\n"
        else:
            last_seq = seq
            try:
                jpeg = _as_jpeg(data)
            except Exception:
                yield b": ping\r\n\r\n"
            else:
                header = (
                    b"--hiveframe\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: "
                    + str(len(jpeg)).encode("ascii")
                    + b"\r\n\r\n"
                )
                yield header + jpeg + b"\r\n"
        parts += 1
        if max_parts is not None and parts >= max_parts:
            return
