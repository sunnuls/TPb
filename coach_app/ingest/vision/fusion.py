from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from coach_app.ingest.vision.base import VisionParseResult
from coach_app.schemas.blackjack import BlackjackState
from coach_app.schemas.common import Card, Confidence, Street
from coach_app.schemas.poker import PokerGameState, PokerGameType
from coach_app.state.validate import (
    StateValidationError,
    validate_blackjack_state,
    validate_poker_state,
    validate_vision_confidence_map,
)


class MergedStateResult(BaseModel):
    merged_state: PokerGameState | BlackjackState
    global_confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


def _min_conf(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return float(min(vals))


def merge_partial_state(
    base_state: PokerGameState | BlackjackState | None,
    vision_result: VisionParseResult,
) -> MergedStateResult:
    partial = dict(vision_result.partial_state or {})
    warnings: list[str] = list(vision_result.warnings or [])

    warnings.extend(validate_vision_confidence_map(vision_result.confidence_map))

    used_conf: list[float] = []

    if isinstance(base_state, PokerGameState) or ("hero_hole" in partial or "board" in partial or "street" in partial):
        merged, w, confs = _merge_poker(base_state if isinstance(base_state, PokerGameState) else None, partial, vision_result)
        warnings.extend(w)
        used_conf.extend(confs)
        merged = PokerGameState.model_validate(merged.model_dump())
        try:
            validate_poker_state(merged)
        except StateValidationError as ve:
            raise ve
        gc = 1.0 if base_state is not None and not used_conf else _min_conf(used_conf)
        return MergedStateResult(merged_state=merged, global_confidence=gc, warnings=warnings)

    merged_bj, w, confs = _merge_blackjack(
        base_state if isinstance(base_state, BlackjackState) else None, partial, vision_result
    )
    warnings.extend(w)
    used_conf.extend(confs)
    merged_bj = BlackjackState.model_validate(merged_bj.model_dump())
    try:
        validate_blackjack_state(merged_bj)
    except StateValidationError as ve:
        raise ve
    gc = 1.0 if base_state is not None and not used_conf else _min_conf(used_conf)
    return MergedStateResult(merged_state=merged_bj, global_confidence=gc, warnings=warnings)


def _merge_poker(
    base: PokerGameState | None,
    partial: dict[str, Any],
    vision_result: VisionParseResult,
) -> tuple[PokerGameState, list[str], list[float]]:
    warnings: list[str] = []
    confs: list[float] = []

    hero_tokens = partial.get("hero_hole")
    board_tokens = partial.get("board")
    street_val = partial.get("street")

    hero_cards: list[Card] | None = None
    if isinstance(hero_tokens, list) and len(hero_tokens) == 2 and all(isinstance(x, str) for x in hero_tokens):
        try:
            hero_cards = [Card.from_str(x) for x in hero_tokens]
        except Exception:
            warnings.append("Vision: не удалось преобразовать hero_hole в карты.")

    board_cards: list[Card] | None = None
    if isinstance(board_tokens, list) and 0 < len(board_tokens) <= 5 and all(isinstance(x, str) for x in board_tokens):
        try:
            board_cards = [Card.from_str(x) for x in board_tokens]
        except Exception:
            warnings.append("Vision: не удалось преобразовать board в карты.")

    street: Street | None = None
    if isinstance(street_val, str):
        try:
            street = Street(street_val)
        except Exception:
            street = None

    if base is None:
        st = street
        if st is None:
            if board_cards is not None:
                if len(board_cards) == 3:
                    st = Street.FLOP
                elif len(board_cards) == 4:
                    st = Street.TURN
                elif len(board_cards) == 5:
                    st = Street.RIVER
            if st is None:
                st = Street.PREFLOP

        merged = PokerGameState(
            game_type=PokerGameType.NLHE_6MAX_CASH,
            street=st,
            players=[],
            small_blind=0.0,
            big_blind=0.0,
            ante=0.0,
            pot=0.0,
            hero_hole=hero_cards or [],
            board=board_cards or [],
            to_act_seat_no=None,
            last_aggressive_action="none",
            confidence=Confidence(value=_min_conf(list((vision_result.confidence_map or {}).values())), source="vision", notes=list(warnings)),
        )

        if "hero_hole" in (vision_result.confidence_map or {}) and hero_cards is not None:
            confs.append(float(vision_result.confidence_map["hero_hole"]))
        if "board" in (vision_result.confidence_map or {}) and board_cards is not None:
            confs.append(float(vision_result.confidence_map["board"]))
        if "street" in (vision_result.confidence_map or {}) and street is not None:
            confs.append(float(vision_result.confidence_map["street"]))

        return merged, warnings, confs

    merged = base.model_copy(deep=True)

    base_board_empty = not bool(base.board)
    base_street = base.street

    if hero_cards is not None:
        if len(merged.hero_hole) == 2:
            if [str(c) for c in merged.hero_hole] != [str(c) for c in hero_cards]:
                warnings.append("Конфликт hero_hole: базовое состояние сохранено, vision проигнорирован.")
        else:
            merged.hero_hole = hero_cards
            if "hero_hole" in (vision_result.confidence_map or {}):
                confs.append(float(vision_result.confidence_map["hero_hole"]))

    if board_cards is not None:
        if merged.board:
            if [str(c) for c in merged.board] != [str(c) for c in board_cards]:
                warnings.append("Конфликт board: базовое состояние сохранено, vision проигнорирован.")
        else:
            merged.board = board_cards
            if "board" in (vision_result.confidence_map or {}):
                confs.append(float(vision_result.confidence_map["board"]))

    if street is not None:
        if merged.street != street:
            can_update_street = base_street == Street.PREFLOP and base_board_empty and board_cards is not None
            if can_update_street:
                merged.street = street
                if "street" in (vision_result.confidence_map or {}):
                    confs.append(float(vision_result.confidence_map["street"]))
            else:
                warnings.append("Конфликт street: базовое состояние сохранено, vision проигнорирован.")

    if base_board_empty and board_cards is not None and base_street == Street.PREFLOP and street is None:
        if len(board_cards) == 3:
            merged.street = Street.FLOP
        elif len(board_cards) == 4:
            merged.street = Street.TURN
        elif len(board_cards) == 5:
            merged.street = Street.RIVER

    return merged, warnings, confs


def _merge_blackjack(
    base: BlackjackState | None,
    partial: dict[str, Any],
    vision_result: VisionParseResult,
) -> tuple[BlackjackState, list[str], list[float]]:
    warnings: list[str] = []
    confs: list[float] = []

    dealer = partial.get("dealer_upcard")
    player_hand = partial.get("player_hand")

    if base is None:
        if not (isinstance(dealer, str) and len(dealer) == 2):
            raise ValueError("dealer_upcard отсутствует или некорректен")
        if not (isinstance(player_hand, list) and len(player_hand) >= 2 and all(isinstance(x, str) and len(x) == 2 for x in player_hand)):
            raise ValueError("player_hand отсутствует или некорректен")

        if "dealer_upcard" in (vision_result.confidence_map or {}):
            confs.append(float(vision_result.confidence_map["dealer_upcard"]))
        if "player_hand" in (vision_result.confidence_map or {}):
            confs.append(float(vision_result.confidence_map["player_hand"]))

        conf = _min_conf(confs)
        merged = BlackjackState(
            player_hand=list(player_hand),
            dealer_upcard=str(dealer),
            allowed_actions=None,
            split_count=0,
            hand_doubled=False,
            running_count=None,
            true_count=None,
            rules={},
            confidence=conf,
        )
        return merged, warnings, confs

    merged = base.model_copy(deep=True)

    if isinstance(dealer, str) and len(dealer) == 2 and dealer != merged.dealer_upcard:
        warnings.append("Конфликт dealer_upcard: базовое состояние сохранено, vision проигнорирован.")

    if isinstance(player_hand, list) and player_hand and [str(x) for x in player_hand] != [str(x) for x in merged.player_hand]:
        warnings.append("Конфликт player_hand: базовое состояние сохранено, vision проигнорирован.")

    return merged, warnings, confs
