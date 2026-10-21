"""Diagnose ws-scrcpy / ADB / codec settings for smoother streaming."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ws-scrcpy.yaml"
SCRCPY_OPT = ROOT / "config" / "scrcpy_optimize.json"
_ADB_TIMEOUT = 8.0


def _adb() -> str:
    return shutil.which("adb") or ""


def _run(args: list[str], timeout: float = _ADB_TIMEOUT) -> tuple[int, str]:
    adb = _adb()
    if not adb:
        return 1, ""
    try:
        proc = subprocess.run(
            [adb, *args],
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, str(exc)
    out = (proc.stdout or b"") + (proc.stderr or b"")
    return proc.returncode, out.decode("utf-8", errors="replace")


def _online_serials() -> list[str]:
    rc, out = _run(["devices", "-l"])
    serials: list[str] = []
    if rc != 0:
        return serials
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def _transport(serial: str, devices_l: str) -> str:
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}:\d+$", serial):
        return "Wi-Fi"
    if serial.startswith("emulator-"):
        return "emulator"
    for line in devices_l.splitlines():
        if not line.startswith(serial):
            continue
        low = line.lower()
        if "usb:" in low or "transport_id:" in low:
            return "USB"
    return "USB" if ":" not in serial else "Wi-Fi"


def _read_ws_config() -> dict:
    info: dict = {"path": str(CONFIG_PATH), "exists": CONFIG_PATH.is_file(), "text": ""}
    if CONFIG_PATH.is_file():
        info["text"] = CONFIG_PATH.read_text(encoding="utf-8")
    opt = {}
    if SCRCPY_OPT.is_file():
        try:
            opt = json.loads(SCRCPY_OPT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            opt = {}
    info["applied_optimize"] = opt
    return info


def _avc_codecs(serial: str) -> list[str]:
    found: list[str] = []
    name_re = re.compile(r"c2\.[A-Za-z0-9._]+\.avc\.[A-Za-z0-9._]+")

    def _collect(out: str) -> None:
        for m in name_re.findall(out):
            if m not in found:
                found.append(m)
        for line in out.splitlines():
            if 'type="video/avc"' in line or "type='video/avc'" in line.lower():
                s = line.strip()
                if s and s not in found:
                    found.append(s[:200])

    for args in (
        ["-s", serial, "shell", "media", "codec", "list"],
        ["-s", serial, "shell", "cmd", "media.codec", "list"],
        ["-s", serial, "shell", "dumpsys", "media.player"],
        ["-s", serial, "shell", "dumpsys", "media.codec"],
        [
            "-s",
            serial,
            "shell",
            "sh",
            "-c",
            "grep -h video/avc /vendor/etc/media_codecs.xml "
            "/vendor/etc/media_codecs_khaje_v0.xml "
            "/vendor/etc/media_codecs_google_c2_video.xml 2>/dev/null",
        ],
    ):
        rc, out = _run(args, timeout=12.0)
        if not out.strip():
            continue
        if "inaccessible" in out.lower() or "can't find service" in out.lower():
            continue
        _collect(out)
        if found:
            break
    return found[:40]


def _codec_stats(serial: str) -> str:
    chunks: list[str] = []
    for svc in ("media.codec", "media.player"):
        rc, out = _run(["-s", serial, "shell", "dumpsys", svc], timeout=12.0)
        label = f"[{svc}]"
        if rc != 0 or not out.strip():
            chunks.append(f"{label} недоступен")
            continue
        if "can't find service" in out.lower():
            chunks.append(f"{label} нет на этой прошивке")
            continue
        keys = ("bitrate", "bit-rate", "fps", "frame-rate", "video/avc", "c2.qti.avc")
        hits = []
        for line in out.splitlines():
            low = line.lower()
            if any(k in low for k in keys):
                hits.append(line.strip()[:240])
            if len(hits) >= 25:
                break
        chunks.append(label + "\n" + ("\n".join(hits) if hits else out[-800:]))
    return "\n".join(chunks) if chunks else "(нет данных)"


def _recommendations(transport: str, avc: list[str], scrcpy: bool) -> list[str]:
    rec = [
        "Для плавности: scrcpy --max-size=1080 --max-fps=60 --bit-rate=8M --no-audio",
        "ws-scrcpy (порт 8090) использует свой scrcpy-server; нативные флаги применяются окном scrcpy (кнопка Применить).",
        "Кабель USB 2.0/3.0 короче, без хаба; отключите энергосбережение USB.",
    ]
    if transport == "Wi-Fi":
        rec.insert(0, "Сейчас Wi-Fi ADB — латентность выше USB. Для 60 fps предпочтителен кабель.")
    if not avc:
        rec.append("Не удалось прочитать video/avc. Проверьте `adb shell media codec list`.")
    else:
        rec.append("H.264 (AVC) на устройстве найден — это нормальный кодек для scrcpy/ws-scrcpy.")
    if not scrcpy:
        rec.append("scrcpy не в PATH: winget install Genymobile.scrcpy")
    rec.append("В ws-scrcpy выбирайте H264 Converter / WebCodecs, не TinyH264 (софт-декод).")
    rec.append("Не гоняйте параллельно MJPEG-плитку HIVE и ws-scrcpy на одном USB — делят adb.")
    return rec


def diagnose(serial: str | None = None) -> dict:
    adb = _adb()
    report: dict = {
        "adb_available": bool(adb),
        "scrcpy_available": bool(shutil.which("scrcpy")),
        "ws_config": _read_ws_config(),
        "serial": serial or "",
        "transport": "",
        "model": "",
        "avc_codecs": [],
        "codec_dump": "",
        "recommendations": [],
    }
    if not adb:
        report["recommendations"] = ["Установите platform-tools (adb) в PATH."]
        return report
    rc, listing = _run(["devices", "-l"])
    serials = _online_serials()
    if not serial:
        serial = serials[0] if serials else ""
    report["serial"] = serial
    report["all_online"] = serials
    if not serial:
        report["recommendations"] = ["Нет online-устройств."]
        return report
    report["transport"] = _transport(serial, listing)
    rc, model = _run(["-s", serial, "shell", "getprop", "ro.product.model"])
    report["model"] = (model or "").strip() if rc == 0 else ""
    report["avc_codecs"] = _avc_codecs(serial)
    report["codec_dump"] = _codec_stats(serial)
    report["recommendations"] = _recommendations(
        report["transport"],
        report["avc_codecs"],
        report["scrcpy_available"],
    )
    return report


def format_report(data: dict) -> str:
    lines = [
        "=== Диагностика ws-scrcpy ===",
        f"adb: {'ok' if data.get('adb_available') else 'нет'}",
        f"scrcpy: {'ok' if data.get('scrcpy_available') else 'нет'}",
        f"serial: {data.get('serial') or '—'}",
        f"модель: {data.get('model') or '—'}",
        f"канал: {data.get('transport') or '—'}",
        "",
        "Конфиг ws-scrcpy:",
        (data.get("ws_config") or {}).get("text") or "(нет файла)",
        "",
        "Применённые флаги optimize:",
        json.dumps((data.get("ws_config") or {}).get("applied_optimize") or {}, ensure_ascii=False),
        "",
        "Кодеки video/avc:",
    ]
    avc = data.get("avc_codecs") or []
    if avc:
        lines.extend(f"  {x}" for x in avc)
    else:
        lines.append("  (не найдено)")
    lines += ["", "dumpsys media.codec (фильтр):", data.get("codec_dump") or "", "", "Рекомендации:"]
    for r in data.get("recommendations") or []:
        lines.append(f"  - {r}")
    return "\n".join(lines).strip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose ADB/ws-scrcpy stream smoothness")
    p.add_argument("--serial", default="", help="device serial (default: first online)")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = parse_args(argv)
    data = diagnose(args.serial.strip() or None)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_report(data))
    return 0 if data.get("adb_available") and data.get("serial") else 1


if __name__ == "__main__":
    raise SystemExit(main())
