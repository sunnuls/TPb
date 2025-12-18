from __future__ import annotations

from dataclasses import dataclass

from coach_app.engine.blackjack.analyze import analyze_blackjack
from coach_app.schemas.blackjack import BlackjackAction, BlackjackDecision, BlackjackRules


@dataclass(frozen=True)
class TrainerScenario:
    player_hand: list[str]
    dealer_upcard: str
    allowed_actions: list[BlackjackAction] | None
    rules: BlackjackRules


_SCENARIOS: list[TrainerScenario] = [
    TrainerScenario(player_hand=["Ah", "7d"], dealer_upcard="9c", allowed_actions=None, rules=BlackjackRules()),
    TrainerScenario(player_hand=["8h", "8d"], dealer_upcard="Tc", allowed_actions=None, rules=BlackjackRules()),
    TrainerScenario(player_hand=["Th", "6d"], dealer_upcard="Tc", allowed_actions=None, rules=BlackjackRules()),
    TrainerScenario(player_hand=["9h", "2d"], dealer_upcard="6c", allowed_actions=[BlackjackAction.hit, BlackjackAction.stand, BlackjackAction.double], rules=BlackjackRules()),
]


def get_scenario(index: int | None) -> tuple[int, TrainerScenario]:
    idx = 0 if index is None else int(index)
    if not _SCENARIOS:
        raise ValueError("No trainer scenarios configured")
    idx = idx % len(_SCENARIOS)
    return idx, _SCENARIOS[idx]


def evaluate_answer(
    *,
    scenario_index: int | None,
    chosen_action: BlackjackAction | None,
) -> dict:
    idx, sc = get_scenario(scenario_index)
    decision: BlackjackDecision = analyze_blackjack(
        player_hand=sc.player_hand,
        dealer_upcard=sc.dealer_upcard,
        rules=sc.rules,
        allowed_actions=sc.allowed_actions,
        split_count=0,
        hand_doubled=False,
    )

    correct = chosen_action is not None and chosen_action == decision.action

    loss = None
    if chosen_action is not None:
        loss = decision.key_facts.get("action_ev_loss", {}).get(chosen_action.value)

    return {
        "scenario_index": idx,
        "scenario": {
            "player_hand": list(sc.player_hand),
            "dealer_upcard": sc.dealer_upcard,
            "allowed_actions": [a.value for a in sc.allowed_actions] if sc.allowed_actions else None,
            "rules": sc.rules.model_dump(),
        },
        "recommended_action": decision.action.value,
        "chosen_action": chosen_action.value if chosen_action else None,
        "correct": correct,
        "ev_loss": loss,
        "decision": decision,
    }
