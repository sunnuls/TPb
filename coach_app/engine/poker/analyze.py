from __future__ import annotations

from coach_app.engine.poker.preflop import hole_cards_to_notation, recommend_preflop
from coach_app.engine.poker.postflop import recommend_postflop
from coach_app.engine.poker.stack import StackInfo, classify_stack, compute_effective_stack_bb, stack_bucket
from coach_app.schemas.common import Street
from coach_app.schemas.ingest import ParseReport
from coach_app.schemas.poker import PokerDecision, PokerGameState


def analyze_poker_state(state: PokerGameState, report: ParseReport) -> PokerDecision:
    """
    MVP deterministic poker engine.
    - Preflop: simple position-based heuristic.
    - Postflop: simplified made-hand / draw heuristic, pot odds when available.

    IMPORTANT: This function must not invent facts; it only computes from state/report.
    """
    hero = next((p for p in state.players if p.is_hero), None)
    hero_pos = hero.position if hero else None
    hero_stack = hero.stack if hero else None
    opp_stacks = [p.stack for p in state.players if not p.is_hero]

    game_family = "mtt" if state.game_type.value == "NLHE_MTT" else "cash"
    eff_bb = compute_effective_stack_bb(hero_stack=hero_stack, opp_stacks=opp_stacks, bb=state.big_blind)
    bucket = stack_bucket(game_family, eff_bb)
    sclass = classify_stack(eff_bb)
    stack_notes: list[str] = []
    if eff_bb is None:
        stack_notes.append("Не удалось вычислить effective_stack_bb (не хватает stack/bb).")
    stack_info = StackInfo(effective_stack_bb=eff_bb, stack_class=sclass, bucket=bucket, notes=stack_notes)

    hero_hand_notation: str | None = None
    if len(state.hero_hole) == 2:
        c1, c2 = state.hero_hole
        hero_hand_notation = hole_cards_to_notation(c1.rank, c2.rank, c1.suit == c2.suit)

    # derive pot/to_call from parse report (HH)
    pot_known = "pot" not in set(report.missing_fields) and state.pot > 0
    pot_val = float(state.pot) if pot_known else None
    to_call = report.parsed.get("to_call", None)
    if isinstance(to_call, (int, float)):
        to_call_val: float | None = float(to_call)
    else:
        to_call_val = None

    has_aggr = state.last_aggressive_action in ("bet", "raise")

    key_facts: dict = {
        "street": state.street.value,
        "game_type": game_family,
        "effective_stack_bb": stack_info.effective_stack_bb,
        "stack_bucket": stack_info.bucket,
        "stack_class": stack_info.stack_class,
        "pot": pot_val,
        "to_call": to_call_val,
        "pot_odds": None,
        "hero_hand": [str(c) for c in state.hero_hole],
        "board": [str(c) for c in state.board],
        "board_texture": None,
        "preflop_aggressor": None,
        "in_position": None,
        "street_initiative": None,
        "flop_checked_through": None,
        "previous_street_summary": None,
        "runout_change": None,
        "selected_line": None,
        "sizing_category": None,
        "pot_fraction": None,
        "recommended_bet_amount": None,
        "recommended_raise_to": None,
        "rounding_step": None,
        "line_reason": None,
        "street_plan": None,
        "hand_category": None,
        "hero_range_name": None,
        "opponent_range_name": None,
        "range_intersection_note": None,
        "range_position": None,
        "plan_hint": None,
        "range_summary": "Диапазоны оппонента: placeholder (MVP без трекинга линий/популяции).",
        "combos_summary": "Комбы: placeholder (MVP, упрощённые категории рук/дро).",
        "notes": list(stack_info.notes),
    }

    if state.street == Street.PREFLOP:
        plan = recommend_preflop(
            hero_hand=hero_hand_notation,
            hero_pos=hero_pos,
            has_aggression=has_aggr,
            game_type=state.game_type.value,
            stack_bucket=stack_info.bucket,
            effective_stack_bb=stack_info.effective_stack_bb,
        )
        key_facts["hand_category"] = "preflop"
        key_facts["notes"] = list(plan.notes)
        key_facts["hero_range_name"] = plan.hero_range_name
        key_facts["opponent_range_name"] = plan.opp_range_name
        key_facts["range_intersection_note"] = plan.range_intersection_note
        key_facts["range_position"] = plan.range_position
        key_facts["plan_hint"] = plan.plan_hint
        if plan.range_summary:
            key_facts["range_summary"] = plan.range_summary
        # preflop combos summary: derived from range position + action
        if plan.range_position:
            key_facts["combos_summary"] = f"Префлоп: позиция руки в диапазоне = {plan.range_position}."
        conf = min(plan.confidence, float(report.confidence))
        return PokerDecision(action=plan.action, sizing=plan.sizing_bb, confidence=conf, key_facts=key_facts)

    # Postflop
    action_history = report.parsed.get("action_history")
    if not isinstance(action_history, list):
        action_history = None
    hero_name = None
    if hero and hero.name:
        hero_name = hero.name
    elif isinstance(report.parsed.get("hero_name"), str):
        hero_name = report.parsed.get("hero_name")

    plan = recommend_postflop(
        street=state.street.value,
        hero_hole=state.hero_hole,
        board=state.board,
        pot=pot_val,
        to_call=to_call_val,
        stack_bucket=stack_info.bucket,
        stack_class=stack_info.stack_class,
        game_type=game_family,
        action_history=action_history,
        hero_name=hero_name,
    )
    key_facts["hand_category"] = plan.hand_category.category
    key_facts["pot_odds"] = plan.facts.get("pot_odds")
    if "estimated_equity" in plan.facts:
        key_facts["estimated_equity"] = plan.facts["estimated_equity"]
    # extra draw facts
    key_facts["flush_draw"] = plan.hand_category.is_flush_draw
    key_facts["straight_draw"] = plan.hand_category.is_straight_draw
    key_facts["notes"] = list(plan.notes)
    key_facts["range_position"] = plan.facts.get("range_position")
    key_facts["plan_hint"] = plan.facts.get("plan_hint")
    key_facts["hero_range_name"] = plan.facts.get("hero_range_name")
    key_facts["opponent_range_name"] = plan.facts.get("opponent_range_name")
    key_facts["range_intersection_note"] = plan.facts.get("range_intersection_note")
    key_facts["board_texture"] = plan.facts.get("board_texture")
    key_facts["preflop_aggressor"] = plan.facts.get("preflop_aggressor")
    key_facts["in_position"] = plan.facts.get("in_position")
    key_facts["street_initiative"] = plan.facts.get("street_initiative")
    key_facts["flop_checked_through"] = plan.facts.get("flop_checked_through")
    key_facts["previous_street_summary"] = plan.facts.get("previous_street_summary")
    key_facts["runout_change"] = plan.facts.get("runout_change")
    key_facts["selected_line"] = plan.facts.get("selected_line")
    key_facts["sizing_category"] = plan.facts.get("sizing_category")
    key_facts["pot_fraction"] = plan.facts.get("pot_fraction")
    key_facts["recommended_bet_amount"] = plan.facts.get("recommended_bet_amount")
    key_facts["recommended_raise_to"] = plan.facts.get("recommended_raise_to")
    key_facts["rounding_step"] = plan.facts.get("rounding_step")
    key_facts["line_reason"] = plan.facts.get("line_reason")
    key_facts["street_plan"] = plan.facts.get("street_plan")
    if plan.facts.get("range_summary"):
        key_facts["range_summary"] = plan.facts["range_summary"]
    # combos summary derived strictly from computed category/draw flags
    draw_bits: list[str] = []
    if plan.hand_category.is_flush_draw:
        draw_bits.append("флеш-дро")
    if plan.hand_category.is_straight_draw:
        draw_bits.append(f"стрит-дро({plan.hand_category.is_straight_draw})")
    if draw_bits:
        key_facts["combos_summary"] = f"Категория: {plan.hand_category.category}; дополнительные ауты: {', '.join(draw_bits)}."
    else:
        key_facts["combos_summary"] = f"Категория: {plan.hand_category.category}."

    # Confidence gating: parser confidence + engine confidence, penalize unknown pot/to_call
    conf = min(plan.confidence, float(report.confidence))
    if pot_val is None:
        conf = min(conf, 0.45)
        key_facts["notes"].append("Банк неизвестен -> pot_odds не рассчитывались.")
    if to_call_val is None:
        conf = min(conf, 0.45)
        key_facts["notes"].append("Сумма к коллу неизвестна -> pot_odds может быть недоступен.")
    return PokerDecision(action=plan.action, sizing=plan.sizing, confidence=conf, key_facts=key_facts)


