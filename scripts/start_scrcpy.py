"""Launch native scrcpy with HIVE 1080/60/8M flags."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "config" / "scrcpy_sessions.json"

DEFAULT_MAX_SIZE = 1080
DEFAULT_MAX_FPS = 60
DEFAULT_BIT_RATE = "8M"


def which_scrcpy() -> str:
    exe = shutil.which("scrcpy")
    if exe:
        return exe
    extra = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "scrcpy" / "scrcpy.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "scrcpy.exe",
    ]
    pkgs = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if pkgs.is_dir():
        extra.extend(pkgs.glob("**/scrcpy.exe"))
    for path in extra:
        if path and path.is_file():
            return str(path)
    return ""


def _first_serial() -> str:
    adb = shutil.which("adb") or ""
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


def _read_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def video_bitrate_flag(exe: str, bit_rate: str) -> str:
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


def launch(
    serial: str = "",
    max_size: int = DEFAULT_MAX_SIZE,
    max_fps: int = DEFAULT_MAX_FPS,
    bit_rate: str = DEFAULT_BIT_RATE,
    no_audio: bool = True,
) -> dict:
    exe = which_scrcpy()
    if not exe:
        return {
            "ok": False,
            "reason": "scrcpy not installed",
            "hint": "Установи: winget install Genymobile.scrcpy",
            "pid": None,
        }
    serial = (serial or "").strip() or _first_serial()
    if not serial:
        return {"ok": False, "reason": "no online device", "pid": None}
    cmd = [
        exe,
        "-s",
        serial,
        f"--max-size={max_size}",
        f"--max-fps={max_fps}",
        video_bitrate_flag(exe, bit_rate),
        "--window-title",
        f"HIVE LIVE {serial}",
    ]
    if no_audio:
        cmd.append("--no-audio")
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
        return {"ok": False, "reason": str(exc), "pid": None, "cmd": cmd}
    state = _read_state()
    state[serial] = {"pid": proc.pid, "cmd": cmd, "exe": exe}
    _write_state(state)
    return {"ok": True, "pid": proc.pid, "serial": serial, "cmd": cmd}


def pid_for(serial: str) -> int | None:
    rec = _read_state().get(serial) or {}
    pid = rec.get("pid")
    try:
        return int(pid) if pid is not None else None
    except (TypeError, ValueError):
        return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start native scrcpy for a device")
    p.add_argument("--serial", default="", help="device serial (default: first online)")
    p.add_argument("--max-size", type=int, default=DEFAULT_MAX_SIZE)
    p.add_argument("--max-fps", type=int, default=DEFAULT_MAX_FPS)
    p.add_argument("--bit-rate", default=DEFAULT_BIT_RATE)
    p.add_argument("--no-audio", action="store_true", default=True)
    p.add_argument("--audio", action="store_true", help="enable audio (overrides --no-audio)")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    no_audio = not args.audio
    result = launch(
        serial=args.serial,
        max_size=args.max_size,
        max_fps=args.max_fps,
        bit_rate=args.bit_rate,
        no_audio=no_audio,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result.get("ok"):
        print("pid:", result.get("pid"))
        print(" ".join(str(x) for x in (result.get("cmd") or [])))
    else:
        print(result.get("hint") or result.get("reason") or "failed")
        return 1
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
