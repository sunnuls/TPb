from coach_app.engine.poker.preflop import recommend_preflop
from coach_app.schemas.poker import Position, PokerActionType


def test_mtt_short_stack_prefers_shove_over_cash_open():
    hand = "AJs"

    mtt_short = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.BTN,
        has_aggression=False,
        game_type="NLHE_MTT",
        stack_bucket="mtt_lt20",
        effective_stack_bb=12.0,
    )
    cash_deep = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.BTN,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )

    assert mtt_short.action == PokerActionType.all_in
    assert cash_deep.action == PokerActionType.raise_

from coach_app.engine.poker.preflop import recommend_preflop
from coach_app.schemas.poker import Position


def test_mtt_short_stack_differs_from_cash_vs_open():
    # BB facing BTN open with KQs:
    # - cash deep: allowed as 3bet (v0 preset includes KQs at some frequency)
    # - mtt <20bb: avoid marginal plays -> fold unless in shove range
    cash = recommend_preflop(
        hero_hand="KQs",
        hero_pos=Position.BB,
        has_aggression=True,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )
    mtt = recommend_preflop(
        hero_hand="KQs",
        hero_pos=Position.BB,
        has_aggression=True,
        game_type="NLHE_MTT",
        stack_bucket="mtt_lt20",
        effective_stack_bb=15.0,
    )
    assert cash.action.value in ("raise", "call", "fold")
    assert mtt.action.value in ("all_in", "fold")
    assert cash.action.value != mtt.action.value


