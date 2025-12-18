from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from coach_app.schemas.common import Street
from coach_app.schemas.ingest import ParseReport
 


Initiative = Literal["hero", "opponent", "none"]


@dataclass(frozen=True)
class PostflopContext:
    was_hero_preflop_aggressor: bool | None
    in_position: bool | None
    street_initiative: Initiative
    flop_checked_through: bool | None
def safe_get(report: ParseReport, key: str, default: Any = None) -> Any:
    return report.parsed.get(key, default)


def parse_action_history(report: ParseReport) -> list[Mapping[str, Any]]:
    raw = report.parsed.get("action_history")
    return raw if isinstance(raw, list) else []


def detect_postflop_context(
    *,
    action_history: list[Mapping[str, Any]] | None,
    hero_name: str | None,
    decision_street: Street,
) -> PostflopContext:
    """
    Compute postflop roles strictly from action_history (up to the hero decision point).

    action_history format (dicts):
      { street: "preflop|flop|turn|river", actor: str, kind: str, amount?: float, to_amount?: float }

    Notes:
    - in_position is computed by whether any non-hero action already occurred on decision_street
      before hero's decision point.
    - preflop aggressor is the last bet/raise on preflop (excluding blinds/antes).
    - street_initiative:
        - if someone already bet/raised on decision street -> that player (hero/opponent)
        - else falls back to preflop aggressor (hero/opponent)
        - else "none"
    """
    if not action_history or not hero_name:
        return PostflopContext(
            was_hero_preflop_aggressor=None,
            in_position=None,
            street_initiative="none",
            flop_checked_through=None,
        )

    # Normalize street strings
    def st(x: Any) -> str:
        return str(x).lower().strip()

    # Identify hero decision index on decision street (snapshot point)
    decision_idx: int | None = None
    for i, a in enumerate(action_history):
        if st(a.get("street")) != decision_street.value:
            continue
        if str(a.get("actor")) != hero_name:
            continue
        if st(a.get("kind")) in ("fold", "check", "call", "bet", "raise"):
            decision_idx = i

    # 1) Preflop aggressor = last raiser on preflop
    last_pre_raiser: str | None = None
    for a in action_history:
        if st(a.get("street")) != Street.PREFLOP.value:
            continue
        if st(a.get("kind")) == "raise":
            last_pre_raiser = str(a.get("actor"))
    was_hero_preflop_aggressor = (last_pre_raiser == hero_name) if last_pre_raiser is not None else False

    # 2) In-position at the decision street: did someone else act before hero on that street?
    if decision_idx is None:
        in_position: bool | None = None
    else:
        in_position = any(
            st(a.get("street")) == decision_street.value and str(a.get("actor")) != hero_name
            for a in action_history[:decision_idx]
        )

    # 3) Street initiative at decision point
    last_street_aggr: str | None = None
    upto = action_history[:decision_idx] if decision_idx is not None else action_history
    for a in upto:
        if st(a.get("street")) != decision_street.value:
            continue
        if st(a.get("kind")) in ("raise", "bet"):
            last_street_aggr = str(a.get("actor"))
    if last_street_aggr is not None:
        street_initiative: Initiative = "hero" if last_street_aggr == hero_name else "opponent"
    elif last_pre_raiser is not None:
        street_initiative = "hero" if last_pre_raiser == hero_name else "opponent"
    else:
        street_initiative = "none"

    # 4) Flop checked through (no bet/raise on flop)
    flop_actions = [a for a in action_history if st(a.get("street")) == Street.FLOP.value]
    flop_checked_through: bool | None
    if not flop_actions:
        flop_checked_through = None
    else:
        flop_checked_through = not any(st(a.get("kind")) in ("bet", "raise") for a in flop_actions)

    return PostflopContext(
        was_hero_preflop_aggressor=was_hero_preflop_aggressor,
        in_position=in_position,
        street_initiative=street_initiative,
        flop_checked_through=flop_checked_through,
    )


