from __future__ import annotations

from coach_app.engine.poker.streets import infer_current_street, previous_street_action_summary, runout_change
from coach_app.schemas.common import Card, Street


def test_infer_current_street_by_board_length():
    assert infer_current_street({"board": [], "street": None}) == Street.PREFLOP
    assert infer_current_street({"board": [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h")]}) == Street.FLOP
    assert (
        infer_current_street({"board": [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h"), Card.from_str("2c")]})
        == Street.TURN
    )
    assert (
        infer_current_street(
            {
                "board": [
                    Card.from_str("As"),
                    Card.from_str("Kd"),
                    Card.from_str("7h"),
                    Card.from_str("2c"),
                    Card.from_str("2d"),
                ]
            }
        )
        == Street.RIVER
    )


def test_previous_street_action_summary_detects_checked_through():
    action_history = [
        {"street": "preflop", "actor": "Villain", "kind": "raise", "amount": 2.0, "to_amount": 6.0},
        {"street": "flop", "actor": "Villain", "kind": "check", "amount": None, "to_amount": None},
        {"street": "flop", "actor": "Hero", "kind": "check", "amount": None, "to_amount": None},
        {"street": "turn", "actor": "Villain", "kind": "check", "amount": None, "to_amount": None},
        {"street": "turn", "actor": "Hero", "kind": "check", "amount": None, "to_amount": None},
    ]

    summary = previous_street_action_summary(
        {"street": "turn", "board": [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h"), Card.from_str("2c")]},
        action_history=action_history,
        hero_name="Hero",
    )

    assert summary["previous_street"] == "flop"
    assert summary["had_aggression"] is False
    assert summary["checked_through"] is True


def test_previous_street_action_summary_detects_last_aggressor():
    action_history = [
        {"street": "flop", "actor": "Villain", "kind": "bet", "amount": 3.0, "to_amount": None},
        {"street": "flop", "actor": "Hero", "kind": "call", "amount": 3.0, "to_amount": None},
        {"street": "turn", "actor": "Villain", "kind": "check", "amount": None, "to_amount": None},
    ]

    summary = previous_street_action_summary(
        {"street": "turn", "board": [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h"), Card.from_str("2c")]},
        action_history=action_history,
        hero_name="Hero",
    )

    assert summary["previous_street"] == "flop"
    assert summary["had_aggression"] is True
    assert summary["checked_through"] is False
    assert summary["last_aggressor"] == "Villain"
    assert summary["hero_aggressor"] is False


def test_runout_change_flags_pair_and_flush_intensified():
    before = [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h")]
    after = before + [Card.from_str("7d")]
    ru = runout_change(board_before=before, board_after=after)

    assert ru is not None
    assert ru["paired"] is True
    assert ru["flush_intensified"] is True

    before2 = [Card.from_str("As"), Card.from_str("Kd"), Card.from_str("7h")]
    after2 = before2 + [Card.from_str("2h")]
    ru2 = runout_change(board_before=before2, board_after=after2)

    assert ru2 is not None
    assert ru2["paired"] is False
    assert ru2["flush_intensified"] is True
