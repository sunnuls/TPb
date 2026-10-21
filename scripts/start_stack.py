"""Start HIVE CONTROL (8000) and ws-scrcpy (8090) together."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ws-scrcpy.yaml"
WS_MAIN = ROOT / "third_party" / "ws-scrcpy" / "main.js"
DASHBOARD = "http://127.0.0.1:8000/"
WS_URL = "http://127.0.0.1:8090/"

_children: list[subprocess.Popen] = []


def _kill(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def _shutdown(*_args) -> None:
    for proc in list(_children):
        _kill(proc)
    _children.clear()


def main() -> int:
    if not WS_MAIN.is_file():
        print("ws-scrcpy не установлен. Сначала: python scripts/install_ws_scrcpy.py")
        return 1
    node = shutil.which("node")
    if not node:
        print("Node.js не найден.")
        return 1
    py = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if CONFIG.is_file():
        env["WS_SCRCPY_CONFIG"] = str(CONFIG)

    fastapi = subprocess.Popen(
        [py, str(ROOT / "control" / "start.py")],
        cwd=str(ROOT),
        env=env,
    )
    _children.append(fastapi)
    ws = subprocess.Popen(
        [node, str(WS_MAIN)],
        cwd=str(WS_MAIN.parent),
        env=env,
    )
    _children.append(ws)

    signal.signal(signal.SIGINT, lambda *_: (_shutdown(), sys.exit(0)))
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: (_shutdown(), sys.exit(0)))

    print(f"HIVE CONTROL: {DASHBOARD}  PID={fastapi.pid}", flush=True)
    print(f"ws-scrcpy:    {WS_URL}  PID={ws.pid}", flush=True)
    time.sleep(1.2)
    webbrowser.open(DASHBOARD)

    try:
        while True:
            if fastapi.poll() is not None:
                print("FastAPI завершился, code=", fastapi.returncode)
                break
            if ws.poll() is not None:
                print("ws-scrcpy завершился, code=", ws.returncode)
                break
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
