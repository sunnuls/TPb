from __future__ import annotations

import re

from fastapi.testclient import TestClient

from coach_app.api.main import create_app
from coach_app.tests.fixtures import MINIMAL_HH_NO_SIZES, PS_CASH_6MAX_FLOP, PS_TOURNAMENT_ANTES_MULTI_STREETS


def _extract_card_tokens(text: str) -> set[str]:
    # matches As, Kd, 7h, Tc, etc.
    return set(re.findall(r"\b[2-9TJQKA][shdc]\b", text))


def test_analyze_poker_endpoint_returns_decision_explanation_and_parse_report():
    app = create_app()
    client = TestClient(app)

    resp = client.post("/analyze/poker", json={"hand_history_text": PS_CASH_6MAX_FLOP, "meta": {"source": "test"}})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "decision" in data
    assert "explanation" in data
    assert "parse_report" in data

    decision = data["decision"]
    key_facts = decision["key_facts"]

    # Required key_facts fields for this iteration
    for k in (
        "street",
        "game_type",
        "effective_stack_bb",
        "stack_bucket",
        "stack_class",
        "pot",
        "to_call",
        "pot_odds",
        "hero_hand",
        "board",
        "board_texture",
        "preflop_aggressor",
        "in_position",
        "street_initiative",
        "flop_checked_through",
        "previous_street_summary",
        "runout_change",
        "selected_line",
        "sizing_category",
        "pot_fraction",
        "recommended_bet_amount",
        "recommended_raise_to",
        "rounding_step",
        "line_reason",
        "street_plan",
        "hand_category",
        "hero_range_name",
        "opponent_range_name",
        "range_intersection_note",
        "range_position",
        "plan_hint",
        "range_summary",
        "combos_summary",
        "notes",
    ):
        assert k in key_facts

    # Explanation "no hallucinations" guard:
    # every card token mentioned in explanation must exist in key_facts hero_hand+board
    mentioned_cards = _extract_card_tokens(data["explanation"])
    allowed_cards = set(key_facts.get("hero_hand", [])) | set(key_facts.get("board", []))
    assert mentioned_cards.issubset(allowed_cards)

    # Explanation should mention range names when present
    if key_facts.get("hero_range_name"):
        assert str(key_facts["hero_range_name"]) in data["explanation"]
    if key_facts.get("opponent_range_name"):
        assert str(key_facts["opponent_range_name"]) in data["explanation"]

    # Line logic should be present and referenced
    assert key_facts.get("selected_line") is not None
    assert key_facts.get("street_plan") is not None
    assert str(key_facts["selected_line"]) in data["explanation"]

    # Streets / runout facts should be present as keys (values may be None depending on street)
    assert "previous_street_summary" in key_facts
    assert "runout_change" in key_facts


def test_when_pot_odds_unknown_explanation_does_not_mention_it():
    app = create_app()
    client = TestClient(app)

    resp = client.post("/analyze/poker", json={"hand_history_text": MINIMAL_HH_NO_SIZES})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["decision"]["key_facts"].get("pot_odds") is None
    assert "Pot odds" not in data["explanation"]


def test_policy_blocks_realtime_poker_room():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker",
        json={
            "hand_history_text": PS_CASH_6MAX_FLOP,
            "meta": {"source": "poker_room", "is_realtime": True},
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == "realtime_poker_room_block"


def test_policy_review_requires_completed_hand_when_mode_explicit():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker",
        json={
            "hand_history_text": PS_CASH_6MAX_FLOP,
            "mode": "review",
            "meta": {"hand_complete": False},
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == "review_hand_not_complete"


def test_policy_review_allows_when_hand_complete_inferred_from_hh():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker",
        json={
            "hand_history_text": PS_TOURNAMENT_ANTES_MULTI_STREETS,
            "mode": "review",
            "meta": {},
        },
    )
    assert resp.status_code == 200, resp.text


def test_policy_live_restricted_blocks_postflop():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/poker",
        json={
            "hand_history_text": PS_CASH_6MAX_FLOP,
            "mode": "live_restricted",
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == "live_restricted_poker_postflop_block"


def test_policy_live_restricted_allows_preflop():
    app = create_app()
    client = TestClient(app)

    preflop_hh = """\
PokerStars Hand #2222222222:  Hold'em No Limit ($0.50/$1.00 USD) - 2025/12/16 15:00:00 ET
Table 'Delta' 6-max Seat #2 is the button
Seat 1: Hero (100 in chips)
Seat 2: Villain (100 in chips)
Hero: posts small blind $0.50
Villain: posts big blind $1.00
*** HOLE CARDS ***
Dealt to Hero [Ah Ks]
Hero: raises $2.00 to $3.00
Villain: folds
"""

    resp = client.post(
        "/analyze/poker",
        json={
            "hand_history_text": preflop_hh,
            "mode": "live_restricted",
        },
    )
    assert resp.status_code == 200, resp.text

