"""Launch native scrcpy with smoothness flags for Realme RMX5566 / USB farm."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "config" / "scrcpy_optimize.json"

FLAGS = ["--max-size=1080", "--max-fps=60", "--video-bit-rate=8M", "--no-audio"]
INSTALL_HINT = (
    "scrcpy не найден. Установка:\n"
    "  winget install Genymobile.scrcpy\n"
    "  или https://github.com/Genymobile/scrcpy/releases\n"
    "Затем перезапустите терминал, чтобы PATH подхватил scrcpy."
)


def _adb() -> str:
    return shutil.which("adb") or ""


def _first_serial() -> str:
    adb = _adb()
    if not adb:
        return ""
    try:
        proc = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            timeout=5,
            check=False,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return ""


def _bitrate_flag(exe: str, bit_rate: str = "8M") -> str:
    helptext = ""
    try:
        proc = subprocess.run(
            [exe, "--help"],
            capture_output=True,
            timeout=8,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        helptext = (proc.stdout or "") + (proc.stderr or "")
    except (subprocess.TimeoutExpired, OSError):
        helptext = ""
    if "--video-bit-rate" in helptext:
        return f"--video-bit-rate={bit_rate}"
    return f"--bit-rate={bit_rate}"


def apply(serial: str = "") -> dict:
    exe = shutil.which("scrcpy")
    if not exe:
        return {"ok": False, "reason": "scrcpy not installed", "hint": INSTALL_HINT, "cmd": []}
    serial = (serial or "").strip() or _first_serial()
    if not serial:
        return {"ok": False, "reason": "no online device", "cmd": []}
    flags = ["--max-size=1080", "--max-fps=60", _bitrate_flag(exe, "8M"), "--no-audio"]
    cmd = [exe, "-s", serial, *flags, "--window-title", f"HIVE OPT {serial}"]
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError as exc:
        return {"ok": False, "reason": str(exc), "cmd": cmd}
    state = {
        "serial": serial,
        "flags": flags,
        "pid": proc.pid,
        "cmd": cmd,
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "pid": proc.pid, "serial": serial, "cmd": cmd, "flags": flags}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start scrcpy with 1080p/60fps/8Mbps/no-audio")
    p.add_argument("--serial", default="", help="device serial (default: first online)")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not shutil.which("scrcpy"):
        print(INSTALL_HINT)
        return 1
    result = apply(args.serial)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result.get("ok"):
        print("scrcpy started:", " ".join(result.get("cmd") or []))
        print("pid:", result.get("pid"))
    else:
        print(result.get("hint") or result.get("reason") or "failed")
        return 1
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
