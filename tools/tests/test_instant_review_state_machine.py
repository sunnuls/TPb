from __future__ import annotations

from tools.instant_review_tracker import InstantReviewStateMachine


def test_state_machine_hotkey_triggers_request_and_resets():
    calls: list[bytes] = []

    def vision_parse(frame_bytes: bytes):
        calls.append(frame_bytes)
        return {"street": "flop"}

    sm = InstantReviewStateMachine(
        session_id="s1",
        meta_defaults={"source": "poker_room", "is_realtime": True, "client_tag": "t"},
        vision_parse=vision_parse,
    )

    sm.observe_frame(frame_bytes=b"frame1", frame_id="f1")
    assert sm.build_payload(mode="instant_review", frame_id="f1") is None

    sm.trigger_post_action(trigger="hotkey")
    payload = sm.build_payload(mode="instant_review", frame_id="f1")
    assert payload is not None
    assert payload["mode"] == "instant_review"

    meta = payload["meta"]
    assert meta["post_action"] is True
    assert meta["trigger"] == "hotkey"
    assert meta["session_id"] == "s1"
    assert meta["frame_id"] == "f1"

    sm.mark_sent()
    assert sm.build_payload(mode="instant_review", frame_id="f2") is None

    assert calls == [b"frame1"]
