"""Unit tests for streaming capture — no real adb."""

from __future__ import annotations

import io
import struct
import subprocess
import time
from unittest.mock import MagicMock

import numpy as np
from PIL import Image

from control.streamer import (
    CaptureThread,
    FrameSlot,
    StreamManager,
    iter_mjpeg,
    raw_capture,
)


def _png_solid(size, color) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _png_noisy(size=(32, 48)) -> bytes:
    img = Image.new("RGB", size, (40, 90, 160))
    for x in range(0, size[0], 3):
        for y in range(0, size[1], 4):
            img.putpixel((x, y), (220, 180, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


BLACK_PNG = _png_solid((32, 48), (0, 0, 0))
GOOD_PNG = _png_noisy()


def test_frame_slot_seq_grows_and_keeps_last():
    slot = FrameSlot()
    slot.put(b"one")
    data, _ts, seq = slot.get()
    assert seq == 1
    assert data == b"one"
    slot.put(b"two")
    data2, _ts2, seq2 = slot.get()
    assert seq2 == 2
    assert seq2 > seq
    assert data2 == b"two"


def test_capture_thread_skips_black_keeps_good():
    n = {"i": 0}

    def fake_capture():
        n["i"] += 1
        return BLACK_PNG if n["i"] <= 2 else GOOD_PNG

    slot = FrameSlot()
    thread = CaptureThread("emu-test", slot, capture_fn=fake_capture, pace=0.05)
    thread.start()
    try:
        deadline = time.time() + 1.2
        while time.time() < deadline:
            _data, _ts, seq = slot.get()
            if seq >= 1:
                break
            time.sleep(0.05)
        data, _ts, seq = slot.get()
        assert seq >= 1
        assert data == GOOD_PNG
        time.sleep(1.0)
        st = thread.stats()
        assert st["fps"] > 0
        assert st["frames"] >= 1
    finally:
        thread.stop()
        thread.join(timeout=2.0)
        assert not thread.is_alive()


def test_mjpeg_generator_emits_jpeg_part():
    slot = FrameSlot()
    slot.put(GOOD_PNG)
    part = next(iter_mjpeg(slot, max_parts=1))
    assert b"--hiveframe" in part
    assert b"Content-Type: image/jpeg" in part
    assert b"Content-Length:" in part


def test_stop_all_joins_under_two_seconds():
    def fake_capture():
        time.sleep(0.02)
        return GOOD_PNG

    mgr = StreamManager(capture_fn=fake_capture)
    mgr.ensure("s1")
    mgr.ensure("s2")
    time.sleep(0.15)
    t0 = time.time()
    mgr.stop_all()
    elapsed = time.time() - t0
    assert elapsed < 2.0
    with mgr._lock:
        assert mgr._threads == {}


def test_raw_capture_fake_rgba_returns_jpeg(monkeypatch):
    w, h = 16, 12
    pixels = np.zeros((h, w, 4), dtype=np.uint8)
    pixels[:, :, 0] = 200
    pixels[:, :, 1] = 90
    pixels[:, :, 2] = 30
    pixels[:, :, 3] = 255
    stdout = struct.pack("<III", w, h, 1) + pixels.tobytes()

    def fake_run(*_a, **_k):
        return subprocess.CompletedProcess(["adb"], 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr("control.streamer.subprocess.run", fake_run)
    jpeg = raw_capture("serial-1", adb_path="adb")
    assert len(jpeg) > 100
    assert jpeg[:2] == b"\xff\xd8"


def test_raw_capture_wrong_format_empty(monkeypatch):
    stdout = struct.pack("<III", 8, 8, 4) + b"\x00" * 128

    def fake_run(*_a, **_k):
        return subprocess.CompletedProcess(["adb"], 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr("control.streamer.subprocess.run", fake_run)
    assert raw_capture("serial-1", adb_path="adb") == b""


def test_capture_falls_back_to_png_when_raw_format_invalid(monkeypatch):
    monkeypatch.setattr("control.streamer.raw_capture", lambda *_a, **_k: b"")
    farm = MagicMock()
    farm._adb = "adb"
    farm._capture.return_value = GOOD_PNG
    slot = FrameSlot()
    thread = CaptureThread("ser-fb", slot, farm=farm, pace=0.05)
    thread.start()
    try:
        deadline = time.time() + 1.2
        while time.time() < deadline:
            if slot.get()[2] >= 1:
                break
            time.sleep(0.05)
        assert slot.get()[0] == GOOD_PNG
        assert thread.mode == "png"
        assert farm._capture.called
    finally:
        thread.stop()
        thread.join(timeout=2.0)


def test_stream_manager_ensure_is_idempotent():
    mgr = StreamManager(capture_fn=lambda: GOOD_PNG)
    slot1 = mgr.ensure("same")
    thread1 = mgr._threads["same"]
    slot2 = mgr.ensure("same")
    thread2 = mgr._threads["same"]
    try:
        assert slot1 is slot2
        assert thread1 is thread2
        assert thread1.is_alive()
    finally:
        mgr.stop_all()


def test_mjpeg_ping_after_one_second_idle():
    slot = FrameSlot()
    slot.put(GOOD_PNG)
    gen = iter_mjpeg(slot)
    first = next(gen)
    assert b"image/jpeg" in first
    t0 = time.time()
    second = next(gen)
    elapsed = time.time() - t0
    assert elapsed >= 0.9
    assert second == b": ping\r\n\r\n"
