"""Collect PNG screenshots from ADB devices into dataset/raw."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

_ADB_TIMEOUT = 8.0
_FOCUS_CACHE_TTL = 30.0
_FOCUS_RE = re.compile(
    r"mCurrentFocus\s*=\s*\S+\s+\S+\s+([A-Za-z0-9._]+)/",
    re.IGNORECASE,
)


def _adb_bin() -> str:
    return shutil.which("adb") or "adb"


def _run(args: list[str], *, timeout: float = _ADB_TIMEOUT, binary: bool = False) -> tuple[int, bytes | str]:
    cmd = [_adb_bin(), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return 1, b"" if binary else ""
    if binary:
        return proc.returncode, proc.stdout or b""
    return proc.returncode, (proc.stdout or b"").decode("utf-8", errors="replace")


def list_online_serials() -> list[str]:
    rc, out = _run(["devices"])
    if rc != 0 or not isinstance(out, str):
        return []
    serials: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def png_size(png: bytes) -> tuple[int, int]:
    if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", png[16:24])
    return int(width), int(height)


class FocusCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pkg: dict[str, tuple[float, str]] = {}

    def get(self, serial: str) -> str:
        now = time.time()
        with self._lock:
            hit = self._pkg.get(serial)
            if hit and now - hit[0] < _FOCUS_CACHE_TTL:
                return hit[1]
        pkg = self._query(serial)
        with self._lock:
            self._pkg[serial] = (now, pkg)
        return pkg

    def _query(self, serial: str) -> str:
        rc, out = _run(["-s", serial, "shell", "dumpsys", "window"], timeout=6.0)
        if rc != 0 or not isinstance(out, str):
            return ""
        for line in out.splitlines():
            if "mCurrentFocus" not in line:
                continue
            m = _FOCUS_RE.search(line)
            if m:
                return m.group(1)
            m2 = re.search(r"([A-Za-z0-9._]+)/[A-Za-z0-9._]+", line)
            if m2:
                return m2.group(1)
        return ""


class Collector:
    def __init__(self, out_dir: Path, interval: float, limit: int) -> None:
        self.out_dir = out_dir
        self.interval = max(0.05, float(interval))
        self.limit = int(limit)
        self.stop = threading.Event()
        self.count = 0
        self._count_lock = threading.Lock()
        self.focus = FocusCache()

    def bump(self) -> int:
        with self._count_lock:
            self.count += 1
            n = self.count
        if n % 50 == 0:
            print(f"frames: {n}", flush=True)
        return n

    def over_limit(self) -> bool:
        if self.limit <= 0:
            return False
        with self._count_lock:
            return self.count >= self.limit

    def worker(self, serial: str) -> None:
        dest = self.out_dir / serial
        dest.mkdir(parents=True, exist_ok=True)
        while not self.stop.is_set() and not self.over_limit():
            t0 = time.monotonic()
            rc, png = _run(
                ["-s", serial, "exec-out", "screencap", "-p"],
                timeout=_ADB_TIMEOUT,
                binary=True,
            )
            if rc == 0 and isinstance(png, (bytes, bytearray)) and len(png) > 100:
                epoch_ms = int(time.time() * 1000)
                png_path = dest / f"{epoch_ms}.png"
                json_path = dest / f"{epoch_ms}.json"
                png_bytes = bytes(png)
                png_path.write_bytes(png_bytes)
                w, h = png_size(png_bytes)
                payload = {
                    "serial": serial,
                    "ts": epoch_ms,
                    "width": w,
                    "height": h,
                    "app_package": self.focus.get(serial),
                }
                json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                self.bump()
            wait = self.interval - (time.monotonic() - t0)
            if wait > 0:
                self.stop.wait(wait)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect ADB screenshots into dataset/raw")
    p.add_argument("--serial", default="", help="device serial; omit = all online")
    p.add_argument("--out", default="dataset/raw", help="output root")
    p.add_argument("--interval", type=float, default=2.0, help="seconds between captures")
    p.add_argument("--limit", type=int, default=0, help="stop after N frames (0 = infinite)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not shutil.which("adb"):
        print("adb не найден в PATH", file=sys.stderr)
        return 1
    serials = [args.serial] if args.serial.strip() else list_online_serials()
    serials = [s.strip() for s in serials if s.strip()]
    if not serials:
        print("Нет online-устройств (adb devices).")
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    coll = Collector(out, args.interval, args.limit)

    def _on_stop(_signum, _frame) -> None:
        coll.stop.set()

    signal.signal(signal.SIGINT, _on_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_stop)

    threads = [
        threading.Thread(target=coll.worker, args=(s,), name=f"collect-{s}", daemon=True)
        for s in serials
    ]
    print(f"collecting serials={serials} out={out} interval={args.interval}s limit={args.limit}")
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads) and not coll.stop.is_set():
            if coll.over_limit():
                coll.stop.set()
                break
            time.sleep(0.2)
    except KeyboardInterrupt:
        coll.stop.set()
    for t in threads:
        t.join(timeout=5.0)
    print(f"stopped, frames={coll.count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
