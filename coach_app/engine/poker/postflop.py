from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from coach_app.engine.poker.board import classify_board
from coach_app.engine.poker.context import detect_postflop_context
from coach_app.engine.poker.hand_strength import HandCategory, categorize
from coach_app.engine.poker.lines import LineType, select_line
from coach_app.engine.poker.sizing import recommend_sizing
from coach_app.engine.poker.streets import previous_street_action_summary, runout_change
from coach_app.schemas.common import Street
from coach_app.schemas.poker import PokerActionType


@dataclass(frozen=True)
class PostflopPlan:
    action: PokerActionType
    sizing: float | None
    confidence: float
    facts: dict
    notes: list[str]
    hand_category: HandCategory


def _draw_equity_heuristic(street: str, hand_category: HandCategory) -> float | None:
    """
    Very rough, deterministic heuristic (NOT solver accurate).
    Used only when pot_odds exists and we must decide call/fold with a draw.
    """
    if street not in ("flop", "turn", "river"):
        return None
    if street == "river":
        return 0.0
    # flop/turn roughs
    if hand_category.is_flush_draw and hand_category.is_straight_draw == "open_ender":
        return 0.46 if street == "flop" else 0.23
    if hand_category.is_flush_draw:
        return 0.35 if street == "flop" else 0.18
    if hand_category.is_straight_draw == "open_ender":
        return 0.32 if street == "flop" else 0.17
    if hand_category.is_straight_draw == "gutshot":
        return 0.16 if street == "flop" else 0.09
    return None


def recommend_postflop(
    *,
    street: str,
    hero_hole: list,
    board: list,
    pot: float | None,
    to_call: float | None,
    stack_bucket: str,
    stack_class: str | None,
    game_type: str,
    action_history: list[Mapping[str, Any]] | None,
    hero_name: str | None,
) -> PostflopPlan:
    notes: list[str] = []
    hc = categorize(hero_hole, board)

    pot_odds: float | None = None
    if pot is not None and to_call is not None and to_call > 0 and pot >= 0:
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else None

    is_short_mtt = (game_type == "mtt") and (stack_bucket == "mtt_lt20")

    # Range-aware (v0) classification: top/middle/bottom of hero range (proxy by hand category)
    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "trips", "two_pair"}
    medium_made = {"pair"}
    if hc.category in strong_made:
        range_pos = "top"
    elif hc.category in medium_made or hc.is_flush_draw or hc.is_straight_draw:
        range_pos = "middle"
    else:
        range_pos = "bottom"

    plan_hint: str

    try:
        decision_street = Street(street)
    except Exception:
        decision_street = Street.FLOP

    prev_summary = previous_street_action_summary(
        {"street": decision_street, "board": board, "action_history": action_history},
        action_history=action_history,
        hero_name=hero_name,
    )

    ru_change: dict[str, Any] | None = None
    if decision_street == Street.TURN and len(board) >= 4:
        ru_change = runout_change(board_before=board[:3], board_after=board[:4])
    if decision_street == Street.RIVER and len(board) >= 5:
        ru_change = runout_change(board_before=board[:4], board_after=board[:5])

    board_texture = classify_board(board)
    ctx = detect_postflop_context(action_history=action_history, hero_name=hero_name, decision_street=decision_street)
    facing_bet = to_call is not None and to_call > 0

    line = select_line(
        street=street,
        board_texture=board_texture,
        hero_range_position=range_pos,
        hero_hand_category=hc.category,
        preflop_aggressor=ctx.was_hero_preflop_aggressor,
        in_position=ctx.in_position,
        street_initiative=ctx.street_initiative,
        flop_checked_through=ctx.flop_checked_through,
        stack_depth_class=stack_class,
        game_type=game_type,
        facing_bet=facing_bet,
        previous_street_summary=prev_summary,
        runout_change=ru_change,
    )

    sizing_rec = None
    if line.line_type in (
        LineType.cbet,
        LineType.probe,
        LineType.delayed_cbet,
        LineType.bet_call,
        LineType.bet_fold,
        LineType.second_barrel,
        LineType.turn_probe,
        LineType.turn_value,
        LineType.river_value,
        LineType.river_bluff,
    ):
        action = PokerActionType.bet
        sizing_rec = recommend_sizing(
            sizing_category=line.sizing_category,
            street=street,
            board_texture=board_texture,
            pot=pot,
            to_call=to_call,
            action="bet",
        )
        sizing = sizing_rec.recommended_bet_amount
    elif line.line_type in (LineType.check_raise, LineType.turn_check_raise) and facing_bet:
        action = PokerActionType.raise_
        sizing_rec = recommend_sizing(
            sizing_category=line.sizing_category,
            street=street,
            board_texture=board_texture,
            pot=pot,
            to_call=to_call,
            action="raise",
        )
        sizing = sizing_rec.recommended_raise_to
    elif line.line_type in (LineType.check_call, LineType.river_check_call) and facing_bet:
        action = PokerActionType.call
        sizing = None
    elif line.line_type in (LineType.check, LineType.give_up, LineType.river_check_fold) and facing_bet:
        action = PokerActionType.fold
        sizing = None
    elif line.line_type == LineType.give_up:
        action = PokerActionType.check
        sizing = None
    else:
        action = PokerActionType.check
        sizing = None

    base_conf = 0.45
    if range_pos == "top":
        base_conf = 0.65
    elif range_pos == "middle":
        base_conf = 0.55

    plan_hint = ""
    if isinstance(line.street_plan, dict):
        plan_hint = str(line.street_plan.get("immediate_plan") or "")
    elif line.street_plan is not None:
        plan_hint = str(line.street_plan)
    return PostflopPlan(
        action=action,
        sizing=sizing,
        confidence=base_conf,
        facts={
            "pot_odds": pot_odds,
            "range_position": range_pos,
            "plan_hint": plan_hint,
            "hero_range_name": f"RFI_proxy_{stack_bucket}",
            "opponent_range_name": "postflop_vs_bet" if facing_bet else "postflop_vs_check",
            "range_intersection_note": "Postflop Line Logic v1",
            "range_summary": "Range Model v0 + Postflop Line Logic v1 (детерминированные эвристики, без солвера).",
            "board_texture": board_texture.to_dict(),
            "preflop_aggressor": ctx.was_hero_preflop_aggressor,
            "in_position": ctx.in_position,
            "street_initiative": ctx.street_initiative,
            "flop_checked_through": ctx.flop_checked_through,
            "previous_street_summary": prev_summary,
            "runout_change": ru_change,
            "selected_line": line.line_type.value,
            "sizing_category": line.sizing_category,
            "pot_fraction": sizing_rec.pot_fraction if sizing_rec is not None else None,
            "recommended_bet_amount": sizing_rec.recommended_bet_amount if sizing_rec is not None else None,
            "recommended_raise_to": sizing_rec.recommended_raise_to if sizing_rec is not None else None,
            "rounding_step": sizing_rec.rounding_step if sizing_rec is not None else None,
            "line_reason": line.line_reason.value,
            "street_plan": line.street_plan,
        },
        notes=notes,
        hand_category=hc,
    )


