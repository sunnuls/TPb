from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from coach_app.product.mode import ProductMode
from coach_app.schemas.common import Street
from coach_app.schemas.meta import Meta


class PolicyReason(str, Enum):
    OK = "ok"
    REALTIME_POKER_ROOM_BLOCK = "realtime_poker_room_block"
    PRE_ACTION_BLOCK = "pre_action_block"
    REVIEW_HAND_NOT_COMPLETE = "review_hand_not_complete"
    TRAIN_EXTERNAL_INPUT_BLOCK = "train_external_input_block"
    LIVE_RESTRICTED_POKER_POSTFLOP_BLOCK = "live_restricted_poker_postflop_block"
    INSTANT_REVIEW_REQUIRES_POST_ACTION = "instant_review_requires_post_action"
    UNKNOWN_MODE = "unknown_mode"


class PolicyResult(BaseModel):
    allowed: bool
    reason: PolicyReason
    message: str
    audit_flags: list[str] = Field(default_factory=list)


def infer_hand_complete_from_hh(hand_history_text: str) -> bool:
    t = (hand_history_text or "").lower()
    markers = (
        "*** summary ***",
        "total pot",
        "collected",
        "wins ",
        "uncalled bet",
        "*** showdown ***",
    )
    return any(m in t for m in markers)


def _unwrap_state(state: Any) -> tuple[str | None, str | None, Any]:
    input_source: str | None = None
    hh_text: str | None = None
    inner_state: Any = state
    if isinstance(state, dict):
        input_source = state.get("_input_source")
        hh_text = state.get("hand_history_text")
        if "state" in state:
            inner_state = state.get("state")
    return input_source, hh_text, inner_state


def enforce_policy(
    mode: ProductMode | None,
    game: str,
    state: Any,
    meta: Meta,
    confidence: float | None,
) -> PolicyResult:
    input_source, hh_text, inner_state = _unwrap_state(state)

    audit_flags: list[str] = [
        f"mode={mode.value if mode is not None else '<missing>'}",
        f"game={game}",
        f"source={meta.source}",
        f"is_realtime={bool(meta.is_realtime)}",
        f"hand_complete={meta.hand_complete}",
        f"post_action={bool(meta.post_action)}",
        f"trigger={meta.trigger}",
        f"frame_id={meta.frame_id}",
        f"session_id={meta.session_id}",
    ]

    if input_source:
        audit_flags.append(f"input_source={input_source}")

    if meta.client_tag:
        audit_flags.append(f"client_tag={meta.client_tag}")
    if confidence is not None:
        try:
            audit_flags.append(f"confidence={float(confidence):.2f}")
        except Exception:
            pass

    if meta.source == "poker_room" and meta.is_realtime and game == "poker":
        if mode == ProductMode.INSTANT_REVIEW and meta.post_action is True:
            pass
        elif mode == ProductMode.INSTANT_REVIEW:
            return PolicyResult(
                allowed=False,
                reason=PolicyReason.PRE_ACTION_BLOCK,
                message="Заблокировано: до совершения действия подсказки запрещены (Instant Review).",
                audit_flags=audit_flags,
            )
        else:
            return PolicyResult(
                allowed=False,
                reason=PolicyReason.REALTIME_POKER_ROOM_BLOCK,
                message="Заблокировано: запрещена помощь в реальном времени для покер-румов.",
                audit_flags=audit_flags,
            )

    if mode is None:
        return PolicyResult(allowed=True, reason=PolicyReason.OK, message="OK", audit_flags=audit_flags)

    if mode == ProductMode.INSTANT_REVIEW:
        if meta.post_action is not True:
            return PolicyResult(
                allowed=False,
                reason=PolicyReason.INSTANT_REVIEW_REQUIRES_POST_ACTION,
                message="Заблокировано (INSTANT_REVIEW): подсказки доступны только после совершения действия.",
                audit_flags=audit_flags,
            )
        return PolicyResult(allowed=True, reason=PolicyReason.OK, message="OK", audit_flags=audit_flags)

    if mode == ProductMode.REVIEW:
        if game == "poker":
            if meta.hand_complete is not True:
                inferred = False
                if meta.hand_complete is None and isinstance(hh_text, str) and hh_text.strip():
                    inferred = infer_hand_complete_from_hh(hh_text)
                if inferred:
                    audit_flags.append("hand_complete_inferred_from_hh=true")
                else:
                    return PolicyResult(
                        allowed=False,
                        reason=PolicyReason.REVIEW_HAND_NOT_COMPLETE,
                        message="Заблокировано (REVIEW): анализ разрешён только после завершения раздачи.",
                        audit_flags=audit_flags,
                    )
        return PolicyResult(allowed=True, reason=PolicyReason.OK, message="OK", audit_flags=audit_flags)

    if mode == ProductMode.TRAIN:
        if input_source != "internal_trainer":
            return PolicyResult(
                allowed=False,
                reason=PolicyReason.TRAIN_EXTERNAL_INPUT_BLOCK,
                message="Заблокировано (TRAIN): внешний ввод запрещён; используйте внутренние сценарии тренажёра.",
                audit_flags=audit_flags,
            )
        if game == "poker":
            return PolicyResult(
                allowed=False,
                reason=PolicyReason.TRAIN_EXTERNAL_INPUT_BLOCK,
                message="Заблокировано (TRAIN): покер-анализ из внешних источников запрещён.",
                audit_flags=audit_flags,
            )
        return PolicyResult(allowed=True, reason=PolicyReason.OK, message="OK", audit_flags=audit_flags)

    if mode == ProductMode.LIVE_RESTRICTED:
        if game == "poker":
            street = getattr(inner_state, "street", None)
            if street != Street.PREFLOP:
                return PolicyResult(
                    allowed=False,
                    reason=PolicyReason.LIVE_RESTRICTED_POKER_POSTFLOP_BLOCK,
                    message="Заблокировано (LIVE_RESTRICTED): в покере разрешён только префлоп.",
                    audit_flags=audit_flags,
                )
        return PolicyResult(allowed=True, reason=PolicyReason.OK, message="OK", audit_flags=audit_flags)

    return PolicyResult(
        allowed=False,
        reason=PolicyReason.UNKNOWN_MODE,
        message="Заблокировано: неизвестный режим продукта.",
        audit_flags=audit_flags,
    )
