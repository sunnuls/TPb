from __future__ import annotations

from dataclasses import dataclass

from coach_app.schemas.blackjack import BlackjackAction


EVLossCategory = str  # "small" | "medium" | "large" | "none"


@dataclass(frozen=True)
class EVComparison:
    recommended_action: BlackjackAction
    ev_reasoning_summary: str
    avoided_mistakes: list[str]
    action_ev_loss: dict[str, EVLossCategory]


def didactic_ev_compare(
    *,
    player_total: int,
    player_hand_type: str,
    dealer_upcard_rank: str,
    recommended_action: BlackjackAction,
    allowed_actions: list[BlackjackAction],
) -> EVComparison:
    up = dealer_upcard_rank
    losses: dict[str, EVLossCategory] = {}
    avoided: list[str] = []

    # baseline
    losses[recommended_action.value] = "none"

    def loss_for(a: BlackjackAction) -> EVLossCategory:
        # Coarse, deterministic buckets.
        if a == recommended_action:
            return "none"

        # Big mistakes
        if recommended_action == BlackjackAction.surrender and a in (BlackjackAction.stand, BlackjackAction.hit):
            return "large"
        if recommended_action == BlackjackAction.split and a in (BlackjackAction.stand, BlackjackAction.hit):
            return "large"
        if recommended_action == BlackjackAction.double and a in (BlackjackAction.hit, BlackjackAction.stand):
            return "medium"

        # Standing too early vs pressure
        if a == BlackjackAction.stand and recommended_action == BlackjackAction.hit and player_total <= 16 and up in ("T", "J", "Q", "K", "A", "9"):
            return "large"

        # Hitting a made stand hand
        if a == BlackjackAction.hit and recommended_action == BlackjackAction.stand and player_total >= 17:
            return "large"

        return "small"

    for a in allowed_actions:
        losses[a.value] = loss_for(a)

    for a, cat in losses.items():
        if cat in ("medium", "large") and a != recommended_action.value:
            avoided.append(f"{a} loses {cat} EV vs {recommended_action.value} here")

    summary = _mk_summary(recommended_action=recommended_action, losses=losses)
    return EVComparison(
        recommended_action=recommended_action,
        ev_reasoning_summary=summary,
        avoided_mistakes=avoided,
        action_ev_loss=losses,
    )


def _mk_summary(*, recommended_action: BlackjackAction, losses: dict[str, EVLossCategory]) -> str:
    worst = [a for a, c in losses.items() if c == "large" and a != recommended_action.value]
    mid = [a for a, c in losses.items() if c == "medium" and a != recommended_action.value]
    if worst:
        return f"Лучшее действие: {recommended_action.value}. Избегаем крупных ошибок: {', '.join(sorted(worst))}."
    if mid:
        return f"Лучшее действие: {recommended_action.value}. Альтернативы {', '.join(sorted(mid))} теряют заметное EV."
    return f"Лучшее действие: {recommended_action.value}. Остальные варианты теряют немного EV (упрощённая оценка)."
