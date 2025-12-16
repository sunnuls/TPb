from __future__ import annotations

import re

from fastapi.testclient import TestClient

from coach_app.api.main import create_app
from coach_app.tests.fixtures import MINIMAL_HH_NO_SIZES, PS_CASH_6MAX_FLOP


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
        "pot",
        "to_call",
        "pot_odds",
        "hero_hand",
        "board",
        "hand_category",
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


def test_when_pot_odds_unknown_explanation_does_not_mention_it():
    app = create_app()
    client = TestClient(app)

    resp = client.post("/analyze/poker", json={"hand_history_text": MINIMAL_HH_NO_SIZES})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["decision"]["key_facts"].get("pot_odds") is None
    assert "Pot odds" not in data["explanation"]


