from coach_app.engine.poker.board import classify_board
from coach_app.schemas.common import Card


def _cards(*xs: str) -> list[Card]:
    return [Card.from_str(x) for x in xs]


def test_board_texture_dry_unpaired_rainbow():
    tx = classify_board(_cards("Ad", "7c", "2s"))
    assert tx.is_paired is False
    assert tx.is_monotone is False
    assert tx.is_two_tone is False
    assert tx.straight_connectivity == "low"
    assert tx.dryness == "dry"


def test_board_texture_monotone_is_wet():
    tx = classify_board(_cards("Ah", "7h", "2h"))
    assert tx.is_monotone is True
    assert tx.dryness == "wet"


def test_board_texture_paired_is_semi_wet():
    tx = classify_board(_cards("Ad", "7c", "7s"))
    assert tx.is_paired is True
    assert tx.dryness == "semi-wet"


def test_board_texture_high_connectivity_is_wet():
    tx = classify_board(_cards("9d", "8c", "7s"))
    assert tx.straight_connectivity == "high"
    assert tx.dryness == "wet"
