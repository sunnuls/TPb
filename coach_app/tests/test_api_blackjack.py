from __future__ import annotations

from fastapi.testclient import TestClient

from coach_app.api.main import create_app


def test_analyze_blackjack_endpoint_returns_decision_and_explanation():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/blackjack",
        json={
            "player_hand": ["Ah", "7d"],
            "dealer_upcard": "9c",
            "rules": {},
            "allowed_actions": ["hit", "stand", "double"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "decision" in data
    assert "explanation" in data
    assert "confidence" in data

    key_facts = data["decision"]["key_facts"]
    for k in (
        "player_hand",
        "dealer_upcard",
        "rules",
        "allowed_actions",
        "player_hand_type",
        "player_total",
        "recommended_action",
        "rule_overrides_applied",
        "ev_reasoning_summary",
        "avoided_mistakes",
        "action_ev_loss",
    ):
        assert k in key_facts


def test_trainer_mode_flow_correct_vs_incorrect():
    app = create_app()
    client = TestClient(app)

    # Get scenario
    resp1 = client.post("/train/blackjack", json={"mode": "trainer", "scenario_index": 0})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["correct"] is None

    recommended = data1["decision"]["action"]

    # Submit correct
    resp2 = client.post(
        "/train/blackjack",
        json={"mode": "trainer", "scenario_index": 0, "chosen_action": recommended},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["correct"] is True

    # Submit incorrect
    wrong = "stand" if recommended != "stand" else "hit"
    resp3 = client.post(
        "/train/blackjack",
        json={"mode": "trainer", "scenario_index": 0, "chosen_action": wrong},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["correct"] is False
    # must expose EV loss category when action provided
    assert data3["ev_loss"] in ("small", "medium", "large", "none")


def test_policy_blocks_train_mode_on_public_analyze_endpoint():
    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/analyze/blackjack",
        json={
            "player_hand": ["Ah", "7d"],
            "dealer_upcard": "9c",
            "rules": {},
            "allowed_actions": ["hit", "stand", "double"],
            "mode": "train",
            "meta": {"source": "unknown"},
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json()["detail"]
    assert detail["reason"] == "train_external_input_block"
