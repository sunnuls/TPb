"""Start HIVE CONTROL dashboard + screenshot collector together."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = "http://127.0.0.1:8000/"
HEALTH = "http://127.0.0.1:8000/api/health"
_ADB_TIMEOUT = 8.0

_children: list[subprocess.Popen] = []


def _python() -> str:
    return shutil.which("python") or sys.executable


def _popen_kwargs() -> dict:
    kwargs: dict = {
        "cwd": str(ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    kwargs["env"] = env
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _shutdown(*_args) -> None:
    for proc in list(_children):
        _kill(proc)
    _children.clear()


def _online_serial() -> str:
    adb = shutil.which("adb")
    if not adb:
        return ""
    try:
        proc = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            timeout=_ADB_TIMEOUT,
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


def _health_ok() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=3) as resp:
            return 200 <= int(resp.status) < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main() -> int:
    serial = _online_serial()
    if not serial:
        print("Нет online-устройств (adb devices). Подключи телефон.")
        return 1

    dash = subprocess.Popen([_python(), "control/start.py"], **_popen_kwargs())
    _children.append(dash)
    time.sleep(3)
    if not _health_ok():
        print("HIVE CONTROL не ответил на", HEALTH)

    collect = subprocess.Popen(
        [
            _python(),
            "tools/collect_data.py",
            "--serial",
            serial,
            "--interval",
            "2",
            "--out",
            "dataset/raw",
        ],
        **_popen_kwargs(),
    )
    _children.append(collect)

    webbrowser.open(DASHBOARD)

    print(f"✅ HIVE CONTROL: {DASHBOARD}")
    print(f"✅ Сборщик: пишет в dataset/raw/{serial}/")
    print("✅ Кликни на плитку → кнопка '🎮 scrcpy 60fps' для плавного стрима")
    print(f"PID дашборда: {dash.pid}, PID сборщика: {collect.pid}")
    print("Ctrl+C — остановить оба процесса.", flush=True)

    def _on_stop(*_a) -> None:
        print("\nОстановка…", flush=True)
        _shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_stop)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _on_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
