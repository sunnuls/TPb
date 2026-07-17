#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_emulator_connection.py — Manual smoke test for a real Android emulator.

Verifies the full chain: ADB discovery -> ADBBackend.capture() -> resolution
parsing, and (with --unsafe) a real tap. Run this after starting LDPlayer/MuMu
with ADB debugging enabled ("Open Local Connection" in Other Settings).

Usage::

    python tools/test_emulator_connection.py
    python tools/test_emulator_connection.py --serial emulator-5554
    python tools/test_emulator_connection.py --unsafe --tap 360 640

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default=None, help="ADB serial (default: first ready device found)")
    parser.add_argument("--unsafe", action="store_true", help="Enable real taps (default: dry-run, capture only)")
    parser.add_argument("--tap", nargs=2, type=int, metavar=("X", "Y"), help="Send a real tap at X Y (requires --unsafe)")
    parser.add_argument("--save", default="tools/_emulator_test_screenshot.png", help="Where to save the captured screenshot")
    args = parser.parse_args()

    from bridge.emulator.adb_backend import ADBBackend, list_adb_devices
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode

    print("=" * 60)
    print("1. Discovering ADB devices...")
    devices = list_adb_devices()
    if not devices:
        print("   No ADB devices found.")
        print("   Checklist:")
        print("   - Is the emulator running?")
        print("   - LDPlayer: Other Settings -> ADB debugging -> 'Open Local Connection' -> Save -> Restart")
        print("   - Try manually: adb connect 127.0.0.1:5555")
        return 1

    for d in devices:
        marker = "OK" if d.is_ready() else "!!"
        print(f"   [{marker}] serial={d.serial}  state={d.state}  model={d.model}")

    serial = args.serial or next((d.serial for d in devices if d.is_ready()), None)
    if serial is None:
        print("   No device is in 'device' (ready) state — see [!!] above.")
        return 1
    print(f"   Using serial: {serial}")

    mode = SafetyMode.UNSAFE if args.unsafe else SafetyMode.DRY_RUN
    safety = SafetyFramework(config=SafetyConfig(mode=mode))
    backend = ADBBackend(serial=serial, safety=safety)

    print()
    print("2. Checking connection...")
    print(f"   is_connected() = {backend.is_connected()}")

    print()
    print("3. Reading resolution ('wm size')...")
    res = backend.get_resolution()
    if res is None:
        print("   FAILED to read resolution — is the device fully booted?")
    else:
        print(f"   Resolution: {res.width}x{res.height}")

    print()
    print("4. Capturing a screenshot ('screencap')...")
    frame = backend.capture()
    if frame is None:
        print("   FAILED — check that cv2/opencv-python is installed (pip install opencv-python)")
        return 1
    print(f"   Captured frame shape: {frame.shape}")

    save_path = Path(args.save)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import cv2
        cv2.imwrite(str(save_path), frame)
        print(f"   Saved to: {save_path.resolve()}")
    except Exception as exc:
        print(f"   Could not save screenshot: {exc}")

    if args.tap:
        print()
        print(f"5. Sending tap at {args.tap} (mode={mode.value})...")
        ok = backend.click(args.tap[0], args.tap[1])
        print(f"   click() -> {ok}" + ("" if args.unsafe else "  (blocked — pass --unsafe to actually tap)"))

    print()
    print("=" * 60)
    print("Smoke test complete.")
    if not args.unsafe:
        print("Note: ran in DRY-RUN mode — no real taps were sent. Pass --unsafe --tap X Y to test input.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
