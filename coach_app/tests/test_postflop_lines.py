from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.lines import LineType, select_line
from coach_app.schemas.common import Card


def _cards(*xs: str) -> list[Card]:
    return [Card.from_str(x) for x in xs]


def test_dry_top_range_selects_cbet():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))
    line = select_line(
        street="flop",
        board_texture=board_texture,
        hero_range_position="top",
        hero_hand_category="two_pair",
        preflop_aggressor=True,
        in_position=True,
        street_initiative="none",
        flop_checked_through=None,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
    )
    assert line.line_type == LineType.cbet


def test_wet_middle_range_checks_more_often():
    board_texture = classify_board(_cards("9h", "8h", "7h"))
    line = select_line(
        street="flop",
        board_texture=board_texture,
        hero_range_position="middle",
        hero_hand_category="pair",
        preflop_aggressor=True,
        in_position=True,
        street_initiative="none",
        flop_checked_through=None,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
    )
    assert line.line_type == LineType.check


def test_turn_delayed_cbet_after_checked_through_flop():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))
    line = select_line(
        street="turn",
        board_texture=board_texture,
        hero_range_position="middle",
        hero_hand_category="pair",
        preflop_aggressor=True,
        in_position=True,
        street_initiative="none",
        flop_checked_through=True,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
    )
    assert line.line_type == LineType.delayed_cbet


def test_flop_probe_when_not_preflop_aggressor_and_checked_to_ip():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))
    line = select_line(
        street="flop",
        board_texture=board_texture,
        hero_range_position="middle",
        hero_hand_category="pair",
        preflop_aggressor=False,
        in_position=True,
        street_initiative="none",
        flop_checked_through=None,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
    )
    assert line.line_type == LineType.probe


def test_facing_bet_top_range_ip_does_not_fold():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))
    line = select_line(
        street="flop",
        board_texture=board_texture,
        hero_range_position="top",
        hero_hand_category="two_pair",
        preflop_aggressor=False,
        in_position=True,
        street_initiative="opponent",
        flop_checked_through=None,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=True,
    )
    assert line.line_type == LineType.check_call
