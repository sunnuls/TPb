from __future__ import annotations

from coach_app.product.mode import ProductMode
from coach_app.product.policy import PolicyReason, enforce_policy
from coach_app.schemas.meta import Meta


def test_instant_review_post_action_false_blocks():
    meta = Meta(source="unknown", is_realtime=False, post_action=False)
    res = enforce_policy(ProductMode.INSTANT_REVIEW, "poker", state={}, meta=meta, confidence=None)
    assert res.allowed is False
    assert res.reason == PolicyReason.INSTANT_REVIEW_REQUIRES_POST_ACTION


def test_instant_review_post_action_true_allows():
    meta = Meta(source="unknown", is_realtime=False, post_action=True)
    res = enforce_policy(ProductMode.INSTANT_REVIEW, "poker", state={}, meta=meta, confidence=None)
    assert res.allowed is True
    assert res.reason == PolicyReason.OK


def test_poker_room_realtime_post_action_false_blocks():
    meta = Meta(source="poker_room", is_realtime=True, post_action=False)
    res = enforce_policy(ProductMode.INSTANT_REVIEW, "poker", state={}, meta=meta, confidence=None)
    assert res.allowed is False
    assert res.reason == PolicyReason.PRE_ACTION_BLOCK


def test_poker_room_realtime_post_action_true_allows():
    meta = Meta(source="poker_room", is_realtime=True, post_action=True)
    res = enforce_policy(ProductMode.INSTANT_REVIEW, "poker", state={}, meta=meta, confidence=None)
    assert res.allowed is True
    assert res.reason == PolicyReason.OK
