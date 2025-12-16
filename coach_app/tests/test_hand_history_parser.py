from coach_app.ingest.hand_history.dispatch import parse_hand_history
from coach_app.state.validate import validate_poker_state

from coach_app.tests.fixtures import PS_CASH_6MAX_FLOP, PS_TOURNAMENT_ANTES_MULTI_STREETS


def test_parser_extracts_cash_hero_and_board():
    parsed = parse_hand_history(PS_CASH_6MAX_FLOP)
    state, report = parsed.state, parsed.report

    assert report.room in ("pokerstars", "generic")
    assert [str(c) for c in state.hero_hole] == ["Ah", "Ks"]
    assert [str(c) for c in state.board] in (["Ad", "7c", "2s"], ["Ad", "7c", "2s", "Td"])

    validate_poker_state(state)


def test_parser_extracts_tournament_antes_and_board():
    parsed = parse_hand_history(PS_TOURNAMENT_ANTES_MULTI_STREETS)
    state, report = parsed.state, parsed.report

    assert report.game_type_detected == "NLHE_MTT"
    assert [str(c) for c in state.hero_hole] == ["9h", "9d"]
    assert [str(c) for c in state.board] == ["2h", "7h", "9s", "Kh", "2d"]

    validate_poker_state(state)


