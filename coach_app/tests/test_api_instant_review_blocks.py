from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from coach_app.api import routes_poker
from coach_app.api.main import create_app
from coach_app.ingest.vision.base import VisionAdapter, VisionParseResult


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


def test_instant_review_blocks_and_returns_no_decision_or_explanation():
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

    payload = {
        "mode": "instant_review",
        "meta": {
            "source": "unknown",
            "is_realtime": True,
            "post_action": False,
            "trigger": "unknown",
            "session_id": "t1",
            "frame_id": "f1",
        },
    }

    resp = client.post(
        "/analyze/poker/screenshot",
        files={"image": ("x.png", _png_bytes(), "image/png")},
        data={"payload": json.dumps(payload)},
    )

    assert resp.status_code == 403, resp.text
    data = resp.json()
    assert "decision" not in data
    assert "explanation" not in data

    detail = data["detail"]
    assert detail["code"] == "POLICY_BLOCK"
    assert detail["reason"] in ("instant_review_requires_post_action", "pre_action_block")

    assert "decision" not in detail
    assert "explanation" not in detail
