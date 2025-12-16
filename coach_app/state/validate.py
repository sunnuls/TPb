from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from coach_app.schemas.blackjack import BlackjackState
from coach_app.schemas.common import Card
from coach_app.schemas.poker import PokerGameState


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

    if errors:
        raise StateValidationError(errors)


