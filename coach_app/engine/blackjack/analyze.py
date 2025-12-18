from __future__ import annotations

from typing import Any

from coach_app.engine.blackjack.basic_strategy import recommend_action
from coach_app.engine.blackjack.ev import didactic_ev_compare
from coach_app.engine.blackjack.hand import classify_hand
from coach_app.schemas.blackjack import BlackjackAction, BlackjackDecision, BlackjackRules


def analyze_blackjack(
    *,
    player_hand: list[str],
    dealer_upcard: str,
    rules: BlackjackRules,
    allowed_actions: list[BlackjackAction] | None,
    split_count: int = 0,
    hand_doubled: bool = False,
) -> BlackjackDecision:
    info = classify_hand(player_hand)

    strat = recommend_action(
        player_hand=player_hand,
        dealer_upcard=dealer_upcard,
        rules=rules,
        allowed_actions=allowed_actions,
        split_count=split_count,
        hand_doubled=hand_doubled,
    )

    allowed = allowed_actions if allowed_actions is not None else [
        BlackjackAction.hit,
        BlackjackAction.stand,
        BlackjackAction.double,
        BlackjackAction.split,
        BlackjackAction.surrender,
    ]

    ev = didactic_ev_compare(
        player_total=info.total,
        player_hand_type=info.hand_type,
        dealer_upcard_rank=dealer_upcard[0].upper(),
        recommended_action=strat.action,
        allowed_actions=allowed,
    )

    key_facts: dict[str, Any] = {
        "player_hand": list(player_hand),
        "dealer_upcard": dealer_upcard,
        "rules": rules.model_dump(),
        "allowed_actions": [a.value for a in allowed],
        "rule_overrides_applied": list(strat.rule_overrides_applied),
        "player_hand_type": info.hand_type,
        "player_total": info.total,
        "recommended_action": strat.action.value,
        "ev_reasoning_summary": ev.ev_reasoning_summary,
        "avoided_mistakes": list(ev.avoided_mistakes),
        "action_ev_loss": dict(ev.action_ev_loss),
        "split_count": split_count,
        "hand_doubled": hand_doubled,
    }

    return BlackjackDecision(action=strat.action, confidence=0.9, key_facts=key_facts)
