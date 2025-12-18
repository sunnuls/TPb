from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.lines import LineType, select_line
from coach_app.schemas.common import Card


def _cards(*xs: str) -> list[Card]:
    return [Card.from_str(x) for x in xs]


def test_same_board_diff_line_ip_vs_oop_for_middle_range_pfa():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))

    ip_line = select_line(
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
    oop_line = select_line(
        street="flop",
        board_texture=board_texture,
        hero_range_position="middle",
        hero_hand_category="pair",
        preflop_aggressor=True,
        in_position=False,
        street_initiative="none",
        flop_checked_through=None,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
    )

    assert ip_line.line_type == LineType.cbet
    assert oop_line.line_type == LineType.check


def test_same_board_diff_line_when_not_preflop_aggressor():
    board_texture = classify_board(_cards("Ad", "7c", "2s"))

    pfa_line = select_line(
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
    not_pfa_line = select_line(
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

    assert pfa_line.line_type == LineType.cbet
    assert not_pfa_line.line_type == LineType.probe
