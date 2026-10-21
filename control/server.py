"""
HIVE CONTROL — local FastAPI server (127.0.0.1 only).

Serves the farm UI and thin ADB REST API. No external network calls.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlencode
import importlib.util

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse

from control.farm_manager import FarmManager
from control.streamer import StreamManager, iter_mjpeg

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(title="HIVE CONTROL", docs_url=None, redoc_url=None)
_farm = FarmManager()
_streams = StreamManager(_farm)
_scrcpy_last: dict[str, int] = {}


WS_SCRCPY_URL = "http://127.0.0.1:8090"
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(filename: str, modname: str):
    path = _REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scrcpy_available() -> bool:
    return bool(shutil.which("scrcpy"))


def _ws_scrcpy_available() -> bool:
    for path in ("/api/health", "/"):
        try:
            urllib.request.urlopen(WS_SCRCPY_URL + path, timeout=2)
            return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    return False


def _ws_scrcpy_iframe_url(serial: str) -> str:
    base = WS_SCRCPY_URL.rstrip("/")
    ws_scheme = "wss" if base.lower().startswith("https") else "ws"
    host = base.split("://", 1)[-1]
    ws = (
        f"{ws_scheme}://{host}/?action=proxy-adb"
        f"&remote=tcp:8886&udid={quote(serial, safe='')}"
    )
    fragment = urlencode(
        {
            "action": "stream",
            "udid": serial,
            "player": "webcodecs",
            "ws": ws,
            "fitToScreen": "true",
        }
    )
    return f"{base}/#!{fragment}"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                timeout=5,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        out = proc.stdout or ""
        return str(pid) in out and "INFO:" not in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@app.on_event("startup")
def _startup() -> None:
    adb = shutil.which("adb")
    if not adb:
        logger.warning("ADB not found on PATH — device API will report offline")
        _farm._adb = ""
    else:
        _farm._adb = adb
        logger.info("ADB available: %s", adb)
    try:
        if _ws_scrcpy_available():
            _streams.stop_all()
        elif _farm.adb_available:
            _streams.sync(_farm.list_devices())
    except Exception:
        logger.exception("stream sync on startup failed")


@app.on_event("shutdown")
def _shutdown() -> None:
    _streams.stop_all()


@app.get("/")
def index():
    html = STATIC_DIR / "index.html"
    if not html.is_file():
        raise HTTPException(404, "index.html missing")
    return FileResponse(html, media_type="text/html; charset=utf-8")


@app.get("/api/health")
def health():
    devices = _farm.list_devices() if _farm.adb_available else []
    ws_up = _ws_scrcpy_available()
    if _farm.adb_available:
        if ws_up:
            _streams.stop_all()
        else:
            _streams.sync(devices)
    online = sum(1 for d in devices if d.get("status") == "online")
    return {
        "ok": True,
        "adb_available": _farm.adb_available,
        "devices_online": online,
        "scrcpy_available": _scrcpy_available(),
    }


@app.get("/api/devices")
def devices():
    rows = _farm.list_devices()
    if _ws_scrcpy_available():
        _streams.stop_all()
    else:
        _streams.sync(rows)
    return rows


@app.get("/api/ws_scrcpy_health")
def ws_scrcpy_health():
    return {"available": _ws_scrcpy_available(), "url": WS_SCRCPY_URL}


@app.get("/api/devices/{serial}/ws_scrcpy_url")
def ws_scrcpy_url(serial: str):
    return {
        "ok": True,
        "serial": serial,
        "url": _ws_scrcpy_iframe_url(serial),
        "available": _ws_scrcpy_available(),
    }


@app.get("/api/devices/{serial}/screen.png")
def screen(serial: str):
    png, stale = _farm.screenshot(serial)
    if not png:
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "X-Frame-Stale": "1" if stale else "0",
        },
    )


@app.get("/api/devices/{serial}/stream")
def stream(serial: str):
    slot = _streams.ensure(serial)
    return StreamingResponse(
        iter_mjpeg(slot),
        media_type="multipart/x-mixed-replace; boundary=hiveframe",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/devices/{serial}/stream_stats")
def stream_stats(serial: str):
    _streams.ensure(serial)
    return _streams.stats(serial)


@app.post("/api/devices/{serial}/live")
def live(serial: str):
    exe = shutil.which("scrcpy")
    if not exe:
        return {"ok": False, "reason": "scrcpy not installed"}
    flags = 0
    kwargs = {}
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(
            [exe, "-s", serial, "--window-title", f"HIVE LIVE {serial}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError as exc:
        logger.warning("scrcpy spawn failed: %s", exc)
        return {"ok": False, "reason": str(exc)}
    return {"ok": True, "pid": proc.pid}


@app.post("/api/devices/{serial}/scrcpy")
def scrcpy_start(serial: str):
    script = _REPO_ROOT / "scripts" / "start_scrcpy.py"
    if not script.is_file():
        return {"ok": False, "reason": "start_scrcpy.py missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--serial", serial, "--json"],
            capture_output=True,
            timeout=20,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("start_scrcpy.py failed: %s", exc)
        return {"ok": False, "reason": str(exc)}
    raw = (proc.stdout or "").strip()
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        err = (proc.stderr or raw or "invalid json")[:400]
        return {"ok": False, "reason": err}
    if not isinstance(data, dict):
        return {"ok": False, "reason": "invalid json"}
    pid = data.get("pid")
    if data.get("ok") and pid:
        try:
            _scrcpy_last[serial] = int(pid)
        except (TypeError, ValueError):
            pass
    return data


@app.get("/api/devices/{serial}/scrcpy_status")
def scrcpy_status(serial: str):
    pid = _scrcpy_last.get(serial)
    if pid is None:
        try:
            mod = _load_script("start_scrcpy.py", "start_scrcpy")
            pid = mod.pid_for(serial)
        except Exception:
            pid = None
    running = bool(pid) and _pid_alive(int(pid))
    return {"ok": True, "pid": pid, "running": running}


@app.post("/api/devices/{serial}/tap")
def tap(
    serial: str,
    x: int = Query(...),
    y: int = Query(...),
):
    _farm.tap(serial, x, y)
    return {"ok": True}


@app.post("/api/devices/{serial}/key")
def key(
    serial: str,
    key: str = Query(...),
):
    _farm.keyevent(serial, key)
    return {"ok": True}


@app.get("/api/stream_optimize")
def stream_optimize(serial: str = Query("")):
    diag = _load_script("diagnose_ws_scrcpy.py", "diagnose_ws_scrcpy")
    data = diag.diagnose(serial.strip() or None)
    text = diag.format_report(data)
    fps = 0.0
    ser = data.get("serial") or ""
    if ser:
        try:
            fps = float(_streams.stats(ser).get("fps") or 0)
        except Exception:
            fps = 0.0
    return {
        "ok": True,
        "report": text,
        "data": data,
        "hive_mjpeg_fps": fps,
    }


@app.post("/api/stream_optimize/apply")
def stream_optimize_apply(serial: str = Query("")):
    opt = _load_script("optimize_scrcpy.py", "optimize_scrcpy")
    result = opt.apply(serial.strip())
    return result


@app.get("/api/bots")
def bots():
    """Stub — BotEngine wiring comes later."""
    return []
