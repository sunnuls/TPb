from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from coach_app.schemas.blackjack import BlackjackState
from coach_app.schemas.common import Card
from coach_app.schemas.poker import PokerGameState


def validate_vision_confidence_map(
    confidence_map: dict[str, float] | None,
    *,
    default_threshold: float = 0.8,
) -> list[str]:
    warnings: list[str] = []
    if not confidence_map:
        return warnings

    for k, v in confidence_map.items():
        try:
            fv = float(v)
        except Exception:
            warnings.append(f"Vision confidence: поле '{k}' имеет некорректное значение")
            continue

        if not (0.0 <= fv <= 1.0):
            warnings.append(f"Vision confidence: поле '{k}' вне диапазона 0..1")
            continue

        if fv < float(default_threshold):
            warnings.append(f"Vision confidence низкая для '{k}': {fv:.2f} < {float(default_threshold):.2f}")

    return warnings


@dataclass(frozen=True)
class ValidationErrorDetail:
    code: str
    message: str
    path: str | None = None


class StateValidationError(ValueError):
    def __init__(self, errors: list[ValidationErrorDetail]):
        super().__init__("Invalid state")
        self.errors = errors


def _dedupe_cards(cards: Iterable[Card]) -> tuple[set[str], set[str]]:
    seen: set[str] = set()
    dup: set[str] = set()
    for c in cards:
        s = str(c)
        if s in seen:
            dup.add(s)
        seen.add(s)
    return seen, dup


def validate_poker_state(state: PokerGameState) -> None:
    errors: list[ValidationErrorDetail] = []

    if state.pot < 0:
        errors.append(ValidationErrorDetail(code="pot_negative", message="pot не может быть отрицательным", path="pot"))
    if state.small_blind < 0 or state.big_blind < 0 or state.ante < 0:
        errors.append(
            ValidationErrorDetail(code="blinds_negative", message="блайнды/анте не могут быть отрицательными")
        )
    if state.big_blind > 0 and state.small_blind > state.big_blind:
        errors.append(
            ValidationErrorDetail(
                code="sb_gt_bb", message="малый блайнд не может быть больше большого", path="small_blind"
            )
        )

    # Validate unique cards across hero + board.
    all_cards: list[Card] = []
    all_cards.extend(state.hero_hole)
    all_cards.extend(state.board)
    _, dup = _dedupe_cards(all_cards)
    if dup:
        errors.append(
            ValidationErrorDetail(
                code="duplicate_cards",
                message=f"обнаружены дубликаты карт: {', '.join(sorted(dup))}",
                path="hero_hole/board",
            )
        )

    # Validate players.
    seat_nos = [p.seat_no for p in state.players]
    if len(seat_nos) != len(set(seat_nos)):
        errors.append(
            ValidationErrorDetail(code="duplicate_seat", message="дублирующиеся seat_no у игроков", path="players")
        )
    for i, p in enumerate(state.players):
        if p.stack < 0:
            errors.append(
                ValidationErrorDetail(
                    code="stack_negative", message="stack не может быть отрицательным", path=f"players[{i}].stack"
                )
            )

    if state.to_act_seat_no is not None and state.to_act_seat_no not in set(seat_nos):
        errors.append(
            ValidationErrorDetail(code="to_act_unknown", message="to_act_seat_no отсутствует среди игроков")
        )

    if errors:
        raise StateValidationError(errors)


def validate_blackjack_state(state: BlackjackState) -> None:
    errors: list[ValidationErrorDetail] = []

    if not (0.0 <= state.confidence <= 1.0):
        errors.append(
            ValidationErrorDetail(code="confidence_range", message="confidence должен быть в диапазоне 0..1", path="confidence")
        )

    if state.true_count is not None and state.running_count is None:
        errors.append(
            ValidationErrorDetail(
                code="true_without_running",
                message="true_count задан без running_count",
                path="true_count",
            )
        )

    if not isinstance(state.player_hand, list) or len(state.player_hand) < 2:
        errors.append(
            ValidationErrorDetail(
                code="player_hand_invalid",
                message="player_hand должен быть списком из >=2 карт",
                path="player_hand",
            )
        )
    else:
        for i, c in enumerate(state.player_hand):
            if not isinstance(c, str) or len(c) != 2:
                errors.append(
                    ValidationErrorDetail(
                        code="card_token_invalid",
                        message="карта должна быть токеном вида 'Ah' (2 символа)",
                        path=f"player_hand[{i}]",
                    )
                )

    if not isinstance(state.dealer_upcard, str) or len(state.dealer_upcard) != 2:
        errors.append(
            ValidationErrorDetail(
                code="dealer_upcard_invalid",
                message="dealer_upcard должен быть токеном вида '9c' (2 символа)",
                path="dealer_upcard",
            )
        )

    if state.split_count < 0:
        errors.append(
            ValidationErrorDetail(
                code="split_count_negative",
                message="split_count не может быть отрицательным",
                path="split_count",
            )
        )
    elif state.rules and state.split_count > int(getattr(state.rules, "max_splits", 0)):
        errors.append(
            ValidationErrorDetail(
                code="split_count_exceeds_max",
                message="split_count превышает правила max_splits",
                path="split_count",
            )
        )

    if state.allowed_actions is not None:
        if not isinstance(state.allowed_actions, list):
            errors.append(
                ValidationErrorDetail(
                    code="allowed_actions_invalid",
                    message="allowed_actions должен быть списком",
                    path="allowed_actions",
                )
            )
        else:
            for i, a in enumerate(state.allowed_actions):
                if not hasattr(a, "value"):
                    errors.append(
                        ValidationErrorDetail(
                            code="allowed_actions_item_invalid",
                            message="allowed_actions содержит некорректное значение",
                            path=f"allowed_actions[{i}]",
                        )
                    )

    if errors:
        raise StateValidationError(errors)
