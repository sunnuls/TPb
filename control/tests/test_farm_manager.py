"""Unit tests for FarmManager — no real adb required."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from control.farm_manager import FarmManager, _is_black


FAKE_DEVICES = """List of devices attached
emulator-5554          device product:sdk_gphone model:sdk_gphone64_x86_64 device:generic
127.0.0.1:5556         device product:mumu model:MuMu device:mumu
emulator-5558          offline
"""


def _png_solid(size, color) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _png_home_like(size=(96, 160)) -> bytes:
    img = Image.new("RGB", size, (32, 96, 180))
    for x in range(0, size[0], 6):
        for y in range(0, size[1], 8):
            img.putpixel((x, y), (240, 220, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


BLACK_PNG = _png_solid((720, 1570), (0, 0, 0))
GOOD_PNG = _png_home_like((720, 1570))


@pytest.fixture
def farm(monkeypatch):
    fm = FarmManager(adb_path="adb")
    monkeypatch.setattr("control.farm_manager.time.sleep", lambda *_a, **_k: None)
    return fm


def _list_fake_run(calls=None):
    def fake_run(args, *, timeout=5.0, binary=False):
        if calls is not None:
            calls.append(list(args))
        if args[:2] == ["devices", "-l"] or args == ["devices", "-l"]:
            return 0, FAKE_DEVICES
        if "getprop" in args:
            return 0, "Pixel_Fake\n"
        if "wm" in args and "size" in args:
            return 0, "Physical size: 1080x1920\n"
        if "dumpsys" in args and "power" in args:
            return 0, "mWakefulness=Awake\n"
        return 0, ""

    return fake_run


def test_list_devices_parses_two_online_one_offline(farm, monkeypatch):
    calls = []
    monkeypatch.setattr(farm, "_run", _list_fake_run(calls))
    devices = farm.list_devices()
    assert len(devices) == 3
    online = [d for d in devices if d["status"] == "online"]
    offline = [d for d in devices if d["status"] == "offline"]
    assert len(online) == 2
    assert len(offline) == 1
    assert online[0]["serial"] == "emulator-5554"
    assert online[0]["resolution"] == "1080x1920"
    assert "awake" in online[0]
    assert online[0]["awake"] is True
    assert offline[0]["serial"] == "emulator-5558"
    assert offline[0]["awake"] is False


def test_list_devices_cache(farm, monkeypatch):
    n = {"c": 0}

    def fake_run(args, *, timeout=5.0, binary=False):
        if args[:2] == ["devices", "-l"] or args == ["devices", "-l"]:
            n["c"] += 1
            return 0, FAKE_DEVICES
        if "getprop" in args:
            return 0, "M\n"
        if "wm" in args:
            return 0, "Physical size: 720x1280\n"
        if "dumpsys" in args:
            return 0, "mWakefulness=Awake\n"
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    farm.list_devices()
    farm.list_devices()
    assert n["c"] == 1  # second call served from cache


def test_screenshot_returns_bytes(farm, monkeypatch):
    png = _png_solid((16, 16), (40, 90, 140))

    def fake_run(args, *, timeout=5.0, binary=False):
        assert args == ["-s", "ser1", "exec-out", "screencap", "-p"]
        assert binary is True
        return 0, png

    monkeypatch.setattr(farm, "_run", fake_run)
    data, stale = farm.screenshot("ser1")
    assert data == png
    assert stale is False


def test_screenshot_retries_black_then_good(farm, monkeypatch):
    shots = {"n": 0}

    def fake_run(args, *, timeout=5.0, binary=False):
        if "screencap" in args:
            shots["n"] += 1
            return 0, BLACK_PNG if shots["n"] == 1 else GOOD_PNG
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    data, stale = farm.screenshot("ser-retry")
    assert data == GOOD_PNG
    assert stale is False
    assert shots["n"] >= 2


def test_screenshot_always_black_stale_without_cache(farm, monkeypatch):
    def fake_run(args, *, timeout=5.0, binary=False):
        if "screencap" in args:
            return 0, BLACK_PNG
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    data, stale = farm.screenshot("ser-black")
    assert stale is True
    assert _is_black(data)


def test_screenshot_always_black_returns_last_good(farm, monkeypatch):
    farm._last_good["ser-hold"] = GOOD_PNG

    def fake_run(args, *, timeout=5.0, binary=False):
        if "screencap" in args:
            return 0, BLACK_PNG
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    data, stale = farm.screenshot("ser-hold")
    assert data == GOOD_PNG
    assert stale is True


def test_is_black_detects_solid_and_home():
    assert _is_black(BLACK_PNG) is True
    assert _is_black(GOOD_PNG) is False
    assert _is_black(b"not-a-png") is True


def test_tap_command_args(farm, monkeypatch):
    seen = {}

    def fake_run(args, *, timeout=5.0, binary=False):
        seen["args"] = list(args)
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    farm.tap("emu-1", 100, 200)
    assert seen["args"] == ["-s", "emu-1", "shell", "input", "tap", "100", "200"]


def test_swipe_command_args(farm, monkeypatch):
    seen = {}

    def fake_run(args, *, timeout=5.0, binary=False):
        seen["args"] = list(args)
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    farm.swipe("emu-1", 10, 20, 30, 40, 300)
    assert seen["args"] == [
        "-s", "emu-1", "shell", "input", "swipe",
        "10", "20", "30", "40", "300",
    ]


def test_keyevent_command_args(farm, monkeypatch):
    seen = {}

    def fake_run(args, *, timeout=5.0, binary=False):
        seen["args"] = list(args)
        return 0, ""

    monkeypatch.setattr(farm, "_run", fake_run)
    farm.keyevent("emu-1", 4)
    assert seen["args"] == ["-s", "emu-1", "shell", "input", "keyevent", "4"]


def test_adb_missing_no_exceptions(monkeypatch):
    monkeypatch.setattr("control.farm_manager.shutil.which", lambda _: None)
    monkeypatch.setattr("control.farm_manager.time.sleep", lambda *_a, **_k: None)
    fm = FarmManager(adb_path="")
    assert fm.list_devices() == []
    assert fm.is_online("anything") is False
    data, stale = fm.screenshot("x")
    assert data == b""
    assert stale is True
    fm.tap("x", 1, 2)  # no raise
    fm.swipe("x", 1, 2, 3, 4, 100)
    fm.keyevent("x", 3)
    fm.input_text("x", "hi")


@pytest.mark.integration
def test_live_adb_list_devices():
    """Optional live check — skipped in default suite."""
    fm = FarmManager()
    if not fm.adb_available:
        pytest.skip("adb not on PATH")
    devices = fm.list_devices()
    assert isinstance(devices, list)
