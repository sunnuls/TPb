from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from coach_app.engine.poker.board import BoardTexture


SizingCategory = Literal["small", "medium", "large", "unknown"]


@dataclass(frozen=True)
class SizingRecommendation:
    pot_fraction: float | None
    recommended_bet_amount: float | None
    recommended_raise_to: float | None
    rounding_step: float | None


def recommend_sizing(
    *,
    sizing_category: SizingCategory,
    street: str,
    board_texture: BoardTexture | None,
    pot: float | None,
    to_call: float | None,
    action: Literal["bet", "raise"] = "bet",
) -> SizingRecommendation:
    if sizing_category == "unknown":
        return SizingRecommendation(pot_fraction=None, recommended_bet_amount=None, recommended_raise_to=None, rounding_step=None)

    pf = _pot_fraction_for_category(sizing_category=sizing_category, street=street, board_texture=board_texture)

    if pot is None or pf is None or pot < 0:
        return SizingRecommendation(pot_fraction=pf, recommended_bet_amount=None, recommended_raise_to=None, rounding_step=None)

    step = _infer_rounding_step(pot=pot, to_call=to_call)

    if action == "bet":
        amount = _round_step(pot * pf, step)
        return SizingRecommendation(pot_fraction=pf, recommended_bet_amount=amount, recommended_raise_to=None, rounding_step=step)

    # raise: interpret pf as fraction of (pot + to_call) added on top of a call
    tc = float(to_call) if isinstance(to_call, (int, float)) and to_call is not None and to_call > 0 else 0.0
    add = (pot + tc) * pf
    raise_to = _round_step(tc + add, step)
    return SizingRecommendation(pot_fraction=pf, recommended_bet_amount=None, recommended_raise_to=raise_to, rounding_step=step)


def _pot_fraction_for_category(
    *,
    sizing_category: SizingCategory,
    street: str,
    board_texture: BoardTexture | None,
) -> float | None:
    st = (street or "").lower().strip()
    dry = board_texture.dryness if board_texture is not None else "semi-wet"

    if sizing_category == "small":
        if st == "flop":
            return 0.33 if dry == "dry" else 0.40
        if st in ("turn", "river"):
            return 0.50
        return 0.33

    if sizing_category == "medium":
        if st == "flop":
            return 0.66 if dry != "dry" else 0.50
        if st in ("turn", "river"):
            return 0.75
        return 0.66

    if sizing_category == "large":
        if st == "flop":
            return 1.00
        if st in ("turn", "river"):
            return 1.00
        return 1.00

    return None


def _infer_rounding_step(*, pot: float, to_call: Any) -> float:
    def has_half(x: float) -> bool:
        # consider .5 as special case, avoid float precision issues
        frac = abs(x - round(x))
        return abs(frac - 0.5) < 1e-6

    if has_half(pot):
        return 0.5
    if isinstance(to_call, (int, float)) and to_call is not None and has_half(float(to_call)):
        return 0.5
    return 1.0


def _round_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return round(x / step) * step
