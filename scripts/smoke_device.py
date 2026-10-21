"""Smoke-test first ADB device on the farm (no hardcoded serial)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_PATH = ROOT / "smoke_screen.png"
ADB_TIMEOUT = 10.0


def _adb() -> str:
    path = shutil.which("adb")
    if not path:
        print("ADB не найден в PATH. Установите Android platform-tools.")
        sys.exit(1)
    return path


def _run(adb: str, args: list[str], *, timeout: float = ADB_TIMEOUT, binary: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [adb, *args],
        capture_output=True,
        timeout=timeout,
        text=not binary,
    )


def _first_online_serial(adb: str) -> str:
    proc = _run(adb, ["devices"])
    if proc.returncode != 0:
        print("Не удалось выполнить `adb devices`.")
        if proc.stderr:
            print(proc.stderr.strip())
        sys.exit(1)

    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]

    print("Нет устройства со статусом device.")
    print("Подключите телефон USB-отладкой (или эмулятор) и проверьте: adb devices")
    sys.exit(1)


def _shell_out(adb: str, serial: str, shell_args: list[str]) -> str:
    proc = _run(adb, ["-s", serial, "shell", *shell_args])
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return f"(ошибка: {err or proc.returncode})"
    return (proc.stdout or "").strip()


def _parse_battery(dumpsys: str) -> str:
    match = re.search(r"level:\s*(\d+)", dumpsys)
    if match:
        return f"{match.group(1)}%"
    return dumpsys.splitlines()[0] if dumpsys else "(нет данных)"


def _parse_wm_size(raw: str) -> str:
    match = re.search(r"(\d+)\s*x\s*(\d+)", raw, re.I)
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    return raw or "(нет данных)"


def main() -> int:
    adb = _adb()
    serial = _first_online_serial(adb)

    model = _shell_out(adb, serial, ["getprop", "ro.product.model"])
    android = _shell_out(adb, serial, ["getprop", "ro.build.version.release"])
    wm_raw = _shell_out(adb, serial, ["wm", "size"])
    resolution = _parse_wm_size(wm_raw)
    battery_raw = _shell_out(adb, serial, ["dumpsys", "battery"])
    battery = _parse_battery(battery_raw)

    print(f"Serial: {serial}")
    print(f"Модель: {model}")
    print(f"Android: {android}")
    print(f"Разрешение: {resolution}")
    print(f"Батарея: {battery}")

    shot = _run(adb, ["-s", serial, "exec-out", "screencap", "-p"], binary=True, timeout=15.0)
    screenshot_ok = shot.returncode == 0 and shot.stdout and len(shot.stdout) > 100
    if screenshot_ok:
        SCREENSHOT_PATH.write_bytes(shot.stdout)
        print(f"Скриншот: {SCREENSHOT_PATH.name}, {len(shot.stdout)} байт — ok")
    else:
        size = len(shot.stdout or b"")
        print(f"Скриншот: ошибка (returncode={shot.returncode}, {size} байт)")

    stayon = _run(adb, ["-s", serial, "shell", "svc", "power", "stayon", "usb"])
    stayon_ok = stayon.returncode == 0
    print(f"stayon usb: {'ok' if stayon_ok else 'ошибка'} (returncode={stayon.returncode})")

    tap = _run(adb, ["-s", serial, "shell", "input", "tap", "5", "5"])
    tap_ok = tap.returncode == 0
    print(f"Тестовый тап 5,5: {'ok' if tap_ok else 'ошибка'} (returncode={tap.returncode})")

    all_ok = screenshot_ok and stayon_ok and tap_ok
    print("---")
    print("Резюме:")
    print(f"  устройство: {serial} ({model}, Android {android}, {resolution}, батарея {battery})")
    print(f"  скриншот: {'ok' if screenshot_ok else 'ошибка'}")
    print(f"  stayon usb: {'ok' if stayon_ok else 'ошибка'}")
    print(f"  тап: {'ok' if tap_ok else 'ошибка'}")
    print(f"  итог: {'ЗЕЛЁНЫЙ' if all_ok else 'КРАСНЫЙ'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired:
        print("ADB команда превысила timeout.")
        raise SystemExit(1)
