from __future__ import annotations

from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.lines import LineType, select_line
from coach_app.schemas.common import Card


def _cards(*xs: str) -> list[Card]:
    return [Card.from_str(x) for x in xs]


def test_turn_second_barrel_after_flop_cbet_top_range():
    board_texture = classify_board(_cards("Ad", "7c", "2s", "Td"))
    prev_summary = {
        "previous_street": "flop",
        "actions": 2,
        "had_aggression": True,
        "checked_through": False,
        "last_aggressor": "Hero",
        "hero_aggressor": True,
    }
    runout = {"paired": False, "flush_intensified": False, "overcard": False, "connects": False}

    line = select_line(
        street="turn",
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
        runout_change=runout,
    )

    assert line.line_type == LineType.second_barrel


def test_turn_probe_when_flop_checked_through_and_not_pfa_ip():
    board_texture = classify_board(_cards("Ad", "7c", "2s", "Td"))
    prev_summary = {
        "previous_street": "flop",
        "actions": 2,
        "had_aggression": False,
        "checked_through": True,
        "last_aggressor": None,
        "hero_aggressor": None,
    }

    line = select_line(
        street="turn",
        board_texture=board_texture,
        hero_range_position="middle",
        hero_hand_category="pair",
        preflop_aggressor=False,
        in_position=True,
        street_initiative="none",
        flop_checked_through=True,
        stack_depth_class="mid",
        game_type="cash",
        facing_bet=False,
        previous_street_summary=prev_summary,
        runout_change={"paired": False},
    )

    assert line.line_type == LineType.turn_probe
