from __future__ import annotations

from coach_app.ingest.hand_history.dispatch import parse_hand_history
from coach_app.ingest.vision.base import VisionParseResult
from coach_app.ingest.vision.fusion import merge_partial_state
from coach_app.schemas.common import Street


PREFLOP_ONLY_HH = """\
PokerStars Hand #222:  Hold'em No Limit ($0.50/$1.00 USD) - 2025/12/16 14:00:00 ET
Table 'Delta' 6-max Seat #3 is the button
Seat 1: Hero (100 in chips)
Seat 2: Villain1 (100 in chips)
Seat 3: Villain2 (100 in chips)
Seat 4: Villain3 (100 in chips)
Seat 5: Villain4 (100 in chips)
Seat 6: Villain5 (100 in chips)
Villain4: posts small blind $0.50
Villain5: posts big blind $1.00
*** HOLE CARDS ***
Dealt to Hero [Ah Ks]
"""


def test_merge_partial_state_hh_plus_vision_board_updates_street_and_board():
    parsed = parse_hand_history(PREFLOP_ONLY_HH)
    base_state = parsed.state

    assert base_state.street == Street.PREFLOP
    assert base_state.board == []

    vision = VisionParseResult(
        partial_state={"board": ["Ad", "7c", "2s"], "street": "flop"},
        confidence_map={"board": 0.95, "street": 0.8},
        warnings=["vision: board detected"],
        adapter_name="generic",
        adapter_version="1.0",
    )

    merged = merge_partial_state(base_state, vision)
    state = merged.merged_state

    assert state.street == Street.FLOP
    assert [str(c) for c in state.board] == ["Ad", "7c", "2s"]
    assert [str(c) for c in state.hero_hole] == ["Ah", "Ks"]
    assert merged.global_confidence == 0.8


def test_conflict_resolution_hh_beats_vision_for_hero_hole():
    parsed = parse_hand_history(PREFLOP_ONLY_HH)
    base_state = parsed.state

    vision = VisionParseResult(
        partial_state={"hero_hole": ["Qh", "Jh"]},
        confidence_map={"hero_hole": 1.0},
        warnings=["vision: hero cards"],
        adapter_name="generic",
        adapter_version="1.0",
    )

    merged = merge_partial_state(base_state, vision)
    state = merged.merged_state

    assert [str(c) for c in state.hero_hole] == ["Ah", "Ks"]
    assert any("Конфликт hero_hole" in w for w in merged.warnings)
