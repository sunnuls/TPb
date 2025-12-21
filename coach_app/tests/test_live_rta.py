from __future__ import annotations

import threading
import time

import pytest
from PIL import Image


class _StubVision:
    def __init__(self, states):
        self._states = list(states)
        self._i = 0

    def capture_screen(self, region=None):
        # return a stable RGB image
        return Image.new("RGB", (40, 40), color=(0, 0, 0))

    def parse(self, image):
        from coach_app.ingest.vision.base import VisionParseResult

        if self._i >= len(self._states):
            st = self._states[-1]
        else:
            st = self._states[self._i]
        self._i += 1

        return VisionParseResult(
            partial_state=st["partial_state"],
            confidence_map=st.get("confidence_map", {}),
            warnings=list(st.get("warnings", [])),
            adapter_name="stub",
            adapter_version="0",
        )


def _wait_for(predicate, *, timeout=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class _NoStartThread:
    def __init__(self, *, target=None, daemon=None):
        self._target = target
        self.daemon = daemon

    def start(self):
        return


def test_live_rta_emits_when_ethics_off(tmp_path, monkeypatch):
    # Arrange: config treated as adapter config (has 'rois'); LiveVisionAdapter must not be constructed in test.
    cfg = tmp_path / "adapter.yaml"
    cfg.write_text("rois: {}\n", encoding="utf-8")

    from coach_app.rta import live_rta

    # Don't start keyboard hotkey thread in tests.
    monkeypatch.setattr(live_rta.threading, "Thread", _NoStartThread)

    # Prevent real LiveVisionAdapter usage.
    monkeypatch.setattr(live_rta, "LiveVisionAdapter", lambda *a, **k: None)

    rta = live_rta.LiveRTA(str(cfg), output_mode="console", ethical_mode=False)

    emitted = {"text": None}

    def _capture(text: str):
        emitted["text"] = text
        rta.stop()

    rta._output = _capture  # type: ignore[method-assign]

    rta.vision = _StubVision(
        [
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            }
        ]
    )

    # Act
    rta.start()

    # Assert
    assert _wait_for(lambda: emitted["text"] is not None)
    assert isinstance(emitted["text"], str)
    assert "Рекомендация" in emitted["text"]


def test_live_rta_requires_trigger_in_ethical_mode(tmp_path, monkeypatch):
    cfg = tmp_path / "adapter.yaml"
    cfg.write_text("rois: {}\n", encoding="utf-8")

    from coach_app.rta import live_rta

    monkeypatch.setattr(live_rta.threading, "Thread", _NoStartThread)
    monkeypatch.setattr(live_rta, "LiveVisionAdapter", lambda *a, **k: None)

    rta = live_rta.LiveRTA(str(cfg), output_mode="console", ethical_mode=True)

    emitted = {"count": 0}

    def _capture(text: str):
        emitted["count"] += 1
        rta.stop()

    rta._output = _capture  # type: ignore[method-assign]

    rta.vision = _StubVision(
        [
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            },
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            },
        ]
    )

    # start loop, but don't trigger yet
    rta.start()

    # allow a short time for a couple loop iterations
    time.sleep(0.15)
    assert emitted["count"] == 0

    # now trigger and expect an output
    rta.trigger_post_action(trigger="hotkey")

    assert _wait_for(lambda: emitted["count"] == 1)


def test_live_rta_does_not_spam_waiting_in_console(tmp_path, monkeypatch):
    cfg = tmp_path / "adapter.yaml"
    cfg.write_text("rois: {}\n", encoding="utf-8")

    from coach_app.rta import live_rta

    monkeypatch.setattr(live_rta.threading, "Thread", _NoStartThread)
    monkeypatch.setattr(live_rta, "LiveVisionAdapter", lambda *a, **k: None)

    rta = live_rta.LiveRTA(str(cfg), output_mode="console", ethical_mode=True)

    emitted: list[str] = []

    def _capture(text: str):
        emitted.append(text)
        if len(emitted) > 3:
            rta.stop()

    rta._output = _capture  # type: ignore[method-assign]

    # Provide 2 iterations of the same parseable state (state change only once).
    rta.vision = _StubVision(
        [
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            },
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            },
        ]
    )

    rta.start()
    time.sleep(0.2)
    rta.stop()

    assert all("Waiting for your action" not in x for x in emitted)


def test_live_rta_multiple_tables_overlay_calls(tmp_path, monkeypatch):
    cfg = tmp_path / "adapter.yaml"
    cfg.write_text("rois: {}\n", encoding="utf-8")

    from coach_app.rta import live_rta

    monkeypatch.setattr(live_rta.threading, "Thread", _NoStartThread)
    monkeypatch.setattr(live_rta, "LiveVisionAdapter", lambda *a, **k: None)

    rta = live_rta.LiveRTA(str(cfg), output_mode="overlay", ethical_mode=False)

    # Mock table detection to return two tables.
    monkeypatch.setattr(
        rta,
        "_detect_table_regions",
        lambda: [
            ("t1", {"left": 0, "top": 0, "width": 300, "height": 300}, (0, 0, 300, 300)),
            ("t2", {"left": 400, "top": 0, "width": 300, "height": 300}, (400, 0, 300, 300)),
        ],
    )

    calls: list[tuple[str, str]] = []

    class _StubOverlay:
        def show(self, text: str, *, table_id: str = "default", anchor_rect=None):
            calls.append((table_id, text))
            if len(calls) >= 2:
                rta.stop()

    rta._overlay = _StubOverlay()  # type: ignore[assignment]

    rta.vision = _StubVision(
        [
            {
                "partial_state": {"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                "confidence_map": {"hero_hole": 0.95, "street": 0.9},
            }
        ]
    )

    rta.start()

    assert _wait_for(lambda: len(calls) >= 2)
    assert {c[0] for c in calls} == {"t1", "t2"}
