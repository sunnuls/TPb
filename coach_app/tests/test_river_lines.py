from __future__ import annotations

from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.lines import LineType, select_line
from coach_app.schemas.common import Card


def _cards(*xs: str) -> list[Card]:
    return [Card.from_str(x) for x in xs]


def test_river_value_when_top_range_and_not_facing_bet():
    board_texture = classify_board(_cards("Ad", "7c", "2s", "Td", "3h"))
    prev_summary = {
        "previous_street": "turn",
        "actions": 2,
        "had_aggression": True,
        "checked_through": False,
        "last_aggressor": "Hero",
        "hero_aggressor": True,
    }

    line = select_line(
        street="river",
        board_texture=board_texture,
        hero_range_position="top",
        hero_hand_category="two_pair",
        preflop_aggressor=True,
        in_position=True,
        street_initiative="hero",
        flop_checked_through=False,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
        previous_street_summary=prev_summary,
        runout_change={"paired": False, "flush_intensified": False, "overcard": False, "connects": False},
    )

    assert line.line_type == LineType.river_value


def test_river_facing_bet_bottom_range_folds():
    board_texture = classify_board(_cards("Ad", "7c", "2s", "Td", "3h"))

    line = select_line(
        street="river",
        board_texture=board_texture,
        hero_range_position="bottom",
        hero_hand_category="high_card",
        preflop_aggressor=False,
        in_position=False,
        street_initiative="opponent",
        flop_checked_through=False,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=True,
        previous_street_summary=None,
        runout_change={"paired": False, "flush_intensified": False, "overcard": False, "connects": False},
    )

    assert line.line_type == LineType.river_check_fold
