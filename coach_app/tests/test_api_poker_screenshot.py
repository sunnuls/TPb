from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from coach_app.api.main import create_app
from coach_app.ingest.vision.base import VisionAdapter, VisionParseResult
from coach_app.api import routes_poker
from coach_app.tests.fixtures import PS_CASH_6MAX_FLOP


class _MockVisionAdapter(VisionAdapter):
    adapter_name = "mock"
    adapter_version = "test"

    def __init__(self, *, result: VisionParseResult):
        self._result = result

    def parse(self, image):  # type: ignore[override]
        return self._result


def _png_bytes() -> bytes:
    img = Image.new("RGB", (20, 20), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_screenshot_endpoint_rejects_when_hero_cards_missing():
    app = create_app()

    def dep():
        return _MockVisionAdapter(
            result=VisionParseResult(
                partial_state={"board": ["Ad", "7c", "2s"], "street": "flop"},
                confidence_map={"board": 0.95, "street": 0.8},
                warnings=["vision board only"],
                adapter_name="mock",
                adapter_version="test",
            )
        )

    app.dependency_overrides[routes_poker.get_poker_vision_adapter] = dep

    client = TestClient(app)
    resp = client.post(
        "/analyze/poker/screenshot",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"payload": "{}"},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert "hero_hole" in detail.get("missing_fields", [])


def test_screenshot_endpoint_merges_hh_and_vision_and_adds_disclaimer():
    app = create_app()

    def dep():
        return _MockVisionAdapter(
            result=VisionParseResult(
                partial_state={"board": ["Ad", "7c", "2s"], "street": "flop"},
                confidence_map={"board": 0.95, "street": 0.8},
                warnings=["vision: board detected"],
                adapter_name="mock",
                adapter_version="test",
            )
        )

    app.dependency_overrides[routes_poker.get_poker_vision_adapter] = dep

    client = TestClient(app)
    resp = client.post(
        "/analyze/poker/screenshot",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"payload": '{"hand_history_text": ' + '"' + PS_CASH_6MAX_FLOP.replace("\n", "\\n") + '"' + "}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "decision" in data
    assert "explanation" in data
    assert "confidence" in data
    assert "warnings" in data

    assert float(data["confidence"]) < 1.0
    assert data["explanation"].startswith("Анализ основан")


def test_live_rta_blocks_when_source_not_simulator():
    app = create_app()

    def dep():
        return _MockVisionAdapter(
            result=VisionParseResult(
                partial_state={"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                confidence_map={"hero_hole": 0.95, "street": 0.9},
                warnings=["vision: hero_hole detected"],
                adapter_name="mock",
                adapter_version="test",
            )
        )

    app.dependency_overrides[routes_poker.get_poker_vision_adapter] = dep
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker/screenshot",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"payload": '{"mode": "live_rta", "meta": {"source": "unknown", "is_realtime": true}}'},
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == "live_rta_requires_simulator_source"


def test_live_rta_allows_for_simulator_source():
    app = create_app()

    def dep():
        return _MockVisionAdapter(
            result=VisionParseResult(
                partial_state={"hero_hole": ["Ah", "Ks"], "street": "preflop"},
                confidence_map={"hero_hole": 0.95, "street": 0.9},
                warnings=["vision: hero_hole detected"],
                adapter_name="mock",
                adapter_version="test",
            )
        )

    app.dependency_overrides[routes_poker.get_poker_vision_adapter] = dep
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker/screenshot",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"payload": '{"mode": "live_rta", "meta": {"source": "simulator", "is_realtime": true}}'},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "decision" in data
    assert "explanation" in data
