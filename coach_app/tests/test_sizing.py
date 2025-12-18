from __future__ import annotations

from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.sizing import recommend_sizing
from coach_app.schemas.common import Card


def test_recommend_sizing_returns_amount_when_pot_known():
    board = [Card.from_str("Ad"), Card.from_str("7c"), Card.from_str("2s")]
    bt = classify_board(board)

    rec = recommend_sizing(
        sizing_category="small",
        street="flop",
        board_texture=bt,
        pot=10.0,
        to_call=0.0,
        action="bet",
    )

    assert rec.pot_fraction is not None
    assert rec.recommended_bet_amount is not None
    assert rec.recommended_raise_to is None
    assert rec.recommended_bet_amount in (3.0, 3.5, 4.0)


def test_recommend_sizing_handles_unknown_pot():
    board = [Card.from_str("Ad"), Card.from_str("7c"), Card.from_str("2s")]
    bt = classify_board(board)

    rec = recommend_sizing(
        sizing_category="medium",
        street="flop",
        board_texture=bt,
        pot=None,
        to_call=None,
        action="bet",
    )

    assert rec.pot_fraction is not None
    assert rec.recommended_bet_amount is None
    assert rec.recommended_raise_to is None


def test_recommend_sizing_raise_to_uses_to_call_and_pf():
    board = [Card.from_str("Ad"), Card.from_str("7c"), Card.from_str("2s")]
    bt = classify_board(board)

    rec = recommend_sizing(
        sizing_category="large",
        street="turn",
        board_texture=bt,
        pot=20.0,
        to_call=5.0,
        action="raise",
    )

    assert rec.pot_fraction is not None
    assert rec.recommended_bet_amount is None
    assert rec.recommended_raise_to is not None
    assert rec.recommended_raise_to >= 5.0


def test_rounding_step_detects_half_units():
    board = [Card.from_str("Ad"), Card.from_str("7c"), Card.from_str("2s")]
    bt = classify_board(board)

    rec = recommend_sizing(
        sizing_category="small",
        street="flop",
        board_texture=bt,
        pot=10.5,
        to_call=0.0,
        action="bet",
    )

    assert rec.rounding_step == 0.5
