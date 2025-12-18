from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from coach_app.engine.blackjack.hand import HandInfo, classify_hand
from coach_app.schemas.blackjack import BlackjackAction, BlackjackRules, SurrenderAllowed


@dataclass(frozen=True)
class StrategyResult:
    action: BlackjackAction
    rule_overrides_applied: list[str]


def recommend_action(
    *,
    player_hand: list[str],
    dealer_upcard: str,
    rules: BlackjackRules,
    allowed_actions: list[BlackjackAction] | None,
    split_count: int = 0,
    hand_doubled: bool = False,
) -> StrategyResult:
    info = classify_hand(player_hand)
    up = dealer_upcard[0].upper()

    allowed = _normalize_allowed(allowed_actions)
    overrides: list[str] = []

    # If already doubled, only hit/stand are meaningful (engine respects allowed_actions but also enforces).
    if hand_doubled and BlackjackAction.double in allowed:
        allowed = [a for a in allowed if a != BlackjackAction.double]
        overrides.append("double_removed_hand_already_doubled")

    if info.is_blackjack:
        # No action required in real game; choose stand as safest.
        return StrategyResult(action=_fallback(BlackjackAction.stand, allowed, overrides, "force_stand_blackjack"), rule_overrides_applied=overrides)

    if info.is_bust:
        return StrategyResult(action=_fallback(BlackjackAction.stand, allowed, overrides, "force_stand_bust"), rule_overrides_applied=overrides)

    # Surrender spots first (late surrender only, didactic)
    if _surrender_allowed(rules) and BlackjackAction.surrender in allowed:
        if info.hand_type == "hard" and info.total == 16 and up in ("9", "T", "J", "Q", "K", "A"):
            return StrategyResult(action=BlackjackAction.surrender, rule_overrides_applied=overrides)
        if info.hand_type == "hard" and info.total == 15 and up in ("T", "J", "Q", "K"):
            return StrategyResult(action=BlackjackAction.surrender, rule_overrides_applied=overrides)

    # Pair splits
    if info.is_pair and BlackjackAction.split in allowed and split_count < rules.max_splits:
        a = _pair_strategy(rank=player_hand[0][0].upper(), up=up, rules=rules)
        if a == BlackjackAction.split:
            return StrategyResult(action=BlackjackAction.split, rule_overrides_applied=overrides)

    if info.is_pair and split_count >= rules.max_splits:
        overrides.append("split_denied_max_splits")

    # Soft / hard
    if info.hand_type == "soft":
        desired = _soft_strategy(total=info.total, up=up)
    else:
        desired = _hard_strategy(total=info.total, up=up)

    # Apply double availability constraints
    if desired == BlackjackAction.double:
        if BlackjackAction.double not in allowed:
            overrides.append("double_denied_allowed_actions")
            desired = _double_fallback(info=info, up=up)
        elif len(player_hand) != 2:
            overrides.append("double_denied_more_than_two_cards")
            desired = _double_fallback(info=info, up=up)

    # Apply split denied constraints (if suggested as split by pair table)
    if desired == BlackjackAction.split and BlackjackAction.split not in allowed:
        overrides.append("split_denied_allowed_actions")
        desired = _pair_fallback_as_total(info=info, up=up)

    # Apply surrender fallback if not allowed
    if desired == BlackjackAction.surrender and BlackjackAction.surrender not in allowed:
        overrides.append("surrender_denied_allowed_actions")
        desired = BlackjackAction.hit

    final_action = _fallback(desired, allowed, overrides, None)
    return StrategyResult(action=final_action, rule_overrides_applied=overrides)


def _normalize_allowed(allowed_actions: list[BlackjackAction] | None) -> list[BlackjackAction]:
    if not allowed_actions:
        return [
            BlackjackAction.hit,
            BlackjackAction.stand,
            BlackjackAction.double,
            BlackjackAction.split,
            BlackjackAction.surrender,
        ]
    # Ensure stable order
    order = {a: i for i, a in enumerate([BlackjackAction.hit, BlackjackAction.stand, BlackjackAction.double, BlackjackAction.split, BlackjackAction.surrender])}
    return sorted(list(allowed_actions), key=lambda a: order.get(a, 999))


def _fallback(desired: BlackjackAction, allowed: list[BlackjackAction], overrides: list[str], reason: str | None) -> BlackjackAction:
    if desired in allowed:
        return desired
    if reason:
        overrides.append(reason)

    # deterministic fallback preference
    for a in (BlackjackAction.stand, BlackjackAction.hit):
        if a in allowed:
            return a
    return allowed[0] if allowed else BlackjackAction.stand


def _surrender_allowed(rules: BlackjackRules) -> bool:
    return rules.surrender_allowed != SurrenderAllowed.none


def _pair_strategy(*, rank: str, up: str, rules: BlackjackRules) -> BlackjackAction:
    # Multi-deck S17 DAS baseline.
    if rank == "A":
        return BlackjackAction.split
    if rank == "8":
        return BlackjackAction.split
    if rank in ("T", "J", "Q", "K"):
        return BlackjackAction.stand
    if rank == "9":
        return BlackjackAction.split if up in ("2", "3", "4", "5", "6", "8", "9") else BlackjackAction.stand
    if rank == "7":
        return BlackjackAction.split if up in ("2", "3", "4", "5", "6", "7") else BlackjackAction.hit
    if rank == "6":
        return BlackjackAction.split if up in ("2", "3", "4", "5", "6") else BlackjackAction.hit
    if rank == "5":
        return BlackjackAction.double if up in ("2", "3", "4", "5", "6", "7", "8", "9") else BlackjackAction.hit
    if rank == "4":
        return BlackjackAction.split if rules.double_after_split and up in ("5", "6") else BlackjackAction.hit
    if rank == "3":
        return BlackjackAction.split if up in ("2", "3", "4", "5", "6", "7") else BlackjackAction.hit
    if rank == "2":
        return BlackjackAction.split if up in ("2", "3", "4", "5", "6", "7") else BlackjackAction.hit
    return BlackjackAction.hit


def _hard_strategy(*, total: int, up: str) -> BlackjackAction:
    if total >= 17:
        return BlackjackAction.stand
    if total <= 8:
        return BlackjackAction.hit
    if total == 9:
        return BlackjackAction.double if up in ("3", "4", "5", "6") else BlackjackAction.hit
    if total == 10:
        return BlackjackAction.double if up in ("2", "3", "4", "5", "6", "7", "8", "9") else BlackjackAction.hit
    if total == 11:
        return BlackjackAction.double if up in ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K") else BlackjackAction.hit
    if total == 12:
        return BlackjackAction.stand if up in ("4", "5", "6") else BlackjackAction.hit
    if total in (13, 14, 15, 16):
        return BlackjackAction.stand if up in ("2", "3", "4", "5", "6") else BlackjackAction.hit
    return BlackjackAction.hit


def _soft_strategy(*, total: int, up: str) -> BlackjackAction:
    # totals are 13..21
    if total <= 17:
        if total in (13, 14):
            return BlackjackAction.double if up in ("5", "6") else BlackjackAction.hit
        if total in (15, 16):
            return BlackjackAction.double if up in ("4", "5", "6") else BlackjackAction.hit
        # soft 17
        return BlackjackAction.double if up in ("3", "4", "5", "6") else BlackjackAction.hit

    if total == 18:
        if up in ("3", "4", "5", "6"):
            return BlackjackAction.double
        if up in ("2", "7", "8"):
            return BlackjackAction.stand
        return BlackjackAction.hit

    if total == 19:
        return BlackjackAction.double if up == "6" else BlackjackAction.stand

    return BlackjackAction.stand


def _double_fallback(*, info: HandInfo, up: str) -> BlackjackAction:
    # If double denied, revert to hit/stand baseline for that total.
    if info.hand_type == "soft":
        if info.total in (18, 19):
            return BlackjackAction.stand if up in ("2", "3", "4", "5", "6", "7", "8") else BlackjackAction.hit
        return BlackjackAction.hit

    # hard
    if info.total >= 17:
        return BlackjackAction.stand
    if info.total <= 11:
        return BlackjackAction.hit
    if info.total == 12:
        return BlackjackAction.stand if up in ("4", "5", "6") else BlackjackAction.hit
    if info.total in (13, 14, 15, 16):
        return BlackjackAction.stand if up in ("2", "3", "4", "5", "6") else BlackjackAction.hit
    return BlackjackAction.hit


def _pair_fallback_as_total(*, info: HandInfo, up: str) -> BlackjackAction:
    # When split is not allowed, treat pair as hard total (e.g. 8,8 => 16).
    return _hard_strategy(total=info.total, up=up)
