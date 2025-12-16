from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


StackClass = Literal["short", "mid", "deep"]


def classify_stack(bb: float | None) -> StackClass | None:
    """
    Generic stack classifier used by both cash and MTT logic.
    - short: < 20bb
    - mid: 20..60bb
    - deep: > 60bb
    """
    if bb is None:
        return None
    if bb < 20:
        return "short"
    if bb <= 60:
        return "mid"
    return "deep"


def stack_bucket(game_type: str, effective_bb: float | None) -> str:
    """
    Deterministic bucket naming used for range presets.
    - cash: assume deep unless effective <60bb
    - mtt: 40bb+, 20-40, <20
    """
    if effective_bb is None:
        return "unknown"
    gt = game_type.lower()
    if "mtt" in gt or "tournament" in gt:
        if effective_bb < 20:
            return "mtt_lt20"
        if effective_bb < 40:
            return "mtt_20_40"
        return "mtt_40plus"

    # cash
    if effective_bb < 25:
        return "cash_short"
    if effective_bb < 60:
        return "cash_mid"
    return "cash_deep"


@dataclass(frozen=True)
class StackInfo:
    effective_stack_bb: float | None
    stack_class: StackClass | None
    bucket: str
    notes: list[str]


def compute_effective_stack_bb(*, hero_stack: float | None, opp_stacks: list[float], bb: float | None) -> float | None:
    """
    Effective stack in BBs: min(hero_stack, max(opponent_stacks)) / bb.
    If bb or stacks missing, returns None.
    """
    if bb is None or bb <= 0:
        return None
    if hero_stack is None or hero_stack <= 0:
        return None
    stack_vals = [float(s) for s in opp_stacks if s is not None and s > 0]
    if not stack_vals:
        return None
    eff = min(float(hero_stack), float(max(stack_vals)))
    return eff / float(bb)


