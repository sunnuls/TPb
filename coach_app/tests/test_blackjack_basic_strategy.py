from __future__ import annotations

from coach_app.engine.blackjack.basic_strategy import recommend_action
from coach_app.schemas.blackjack import BlackjackAction, BlackjackRules, SurrenderAllowed


def test_soft_hand_differs_from_hard():
    rules = BlackjackRules()

    # Soft 18 vs 9 => hit (S17 multi-deck)
    r1 = recommend_action(
        player_hand=["Ah", "7d"],
        dealer_upcard="9c",
        rules=rules,
        allowed_actions=None,
    )
    assert r1.action == BlackjackAction.hit

    # Hard 18 vs 9 => stand
    r2 = recommend_action(
        player_hand=["Th", "8d"],
        dealer_upcard="9c",
        rules=rules,
        allowed_actions=None,
    )
    assert r2.action == BlackjackAction.stand


def test_pair_splitting_logic():
    rules = BlackjackRules()

    # 8,8 vs 10 => split
    r = recommend_action(
        player_hand=["8h", "8d"],
        dealer_upcard="Tc",
        rules=rules,
        allowed_actions=None,
        split_count=0,
    )
    assert r.action == BlackjackAction.split


def test_double_denied_falls_back():
    rules = BlackjackRules()

    # 11 vs 6 => double, but if double not allowed => hit
    r = recommend_action(
        player_hand=["9h", "2d"],
        dealer_upcard="6c",
        rules=rules,
        allowed_actions=[BlackjackAction.hit, BlackjackAction.stand],
    )
    assert r.action in (BlackjackAction.hit, BlackjackAction.stand)
    assert "double_denied_allowed_actions" in r.rule_overrides_applied


def test_surrender_allowed_vs_not_allowed():
    rules_ls = BlackjackRules(surrender_allowed=SurrenderAllowed.late)
    rules_no = BlackjackRules(surrender_allowed=SurrenderAllowed.none)

    # 16 vs A => surrender if allowed
    r1 = recommend_action(
        player_hand=["Th", "6d"],
        dealer_upcard="Ac",
        rules=rules_ls,
        allowed_actions=None,
    )
    assert r1.action == BlackjackAction.surrender

    # same spot but surrender disabled => hit
    r2 = recommend_action(
        player_hand=["Th", "6d"],
        dealer_upcard="Ac",
        rules=rules_no,
        allowed_actions=None,
    )
    assert r2.action in (BlackjackAction.hit, BlackjackAction.stand)
