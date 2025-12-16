from coach_app.engine.poker.preflop import recommend_preflop
from coach_app.schemas.poker import Position, PokerActionType


def test_same_hand_diff_positions_changes_action():
    # A5s is in BTN RFI but typically not UTG RFI in v0 presets
    hand = "A5s"
    plan_utg = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.UTG,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )
    plan_btn = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.BTN,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )

    assert plan_utg.action in (PokerActionType.fold, PokerActionType.check)
    assert plan_btn.action == PokerActionType.raise_


def test_same_hand_diff_stack_depth_changes_action_for_mtt_short():
    # AQo should be shove-able in short-stack MTT, but regular open/raise in deep
    hand = "AQo"
    plan_short = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.CO,
        has_aggression=False,
        game_type="NLHE_MTT",
        stack_bucket="mtt_lt20",
        effective_stack_bb=15.0,
    )
    plan_deep = recommend_preflop(
        hero_hand=hand,
        hero_pos=Position.CO,
        has_aggression=False,
        game_type="NLHE_MTT",
        stack_bucket="mtt_40plus",
        effective_stack_bb=50.0,
    )
    assert plan_short.action == PokerActionType.all_in
    assert plan_deep.action in (PokerActionType.raise_, PokerActionType.fold)

from coach_app.engine.poker.preflop import recommend_preflop
from coach_app.schemas.poker import Position


def test_same_hand_different_positions_changes_action():
    # A5s: UTG tight -> fold; BTN looser -> raise
    utg = recommend_preflop(
        hero_hand="A5s",
        hero_pos=Position.UTG,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )
    btn = recommend_preflop(
        hero_hand="A5s",
        hero_pos=Position.BTN,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )
    assert utg.action.value == "fold"
    assert btn.action.value in ("raise", "all_in")


def test_same_hand_different_stack_bucket_changes_action():
    # AQo open: cash deep -> raise; MTT <20bb -> shove
    cash = recommend_preflop(
        hero_hand="AQo",
        hero_pos=Position.CO,
        has_aggression=False,
        game_type="NLHE_6max_cash",
        stack_bucket="cash_deep",
        effective_stack_bb=100.0,
    )
    short = recommend_preflop(
        hero_hand="AQo",
        hero_pos=Position.CO,
        has_aggression=False,
        game_type="NLHE_MTT",
        stack_bucket="mtt_lt20",
        effective_stack_bb=15.0,
    )
    assert cash.action.value == "raise"
    assert short.action.value == "all_in"


