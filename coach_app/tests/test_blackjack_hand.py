from __future__ import annotations

from coach_app.engine.blackjack.hand import classify_hand, hand_total, is_blackjack, is_bust


def test_hand_total_soft_vs_hard():
    assert hand_total(["Ah", "7d"]) == 18
    assert classify_hand(["Ah", "7d"]).hand_type == "soft"

    assert hand_total(["Ah", "7d", "9c"]) == 17
    assert classify_hand(["Ah", "7d", "9c"]).hand_type == "hard"


def test_is_blackjack_and_bust():
    assert is_blackjack(["Ah", "Td"]) is True
    assert is_blackjack(["Ah", "9d"]) is False

    assert is_bust(["Th", "9d", "5c"]) is True
    assert is_bust(["Ah", "9d", "5c"]) is False
