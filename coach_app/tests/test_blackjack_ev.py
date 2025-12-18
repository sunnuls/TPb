from __future__ import annotations

from coach_app.engine.blackjack.ev import didactic_ev_compare
from coach_app.schemas.blackjack import BlackjackAction


def test_ev_reasoning_marks_big_mistakes():
    ev = didactic_ev_compare(
        player_total=16,
        player_hand_type="hard",
        dealer_upcard_rank="T",
        recommended_action=BlackjackAction.hit,
        allowed_actions=[BlackjackAction.hit, BlackjackAction.stand],
    )

    assert ev.action_ev_loss["hit"] == "none"
    assert ev.action_ev_loss["stand"] in ("medium", "large")
    assert any("stand" in s for s in ev.avoided_mistakes)
