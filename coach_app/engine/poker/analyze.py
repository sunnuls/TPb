from __future__ import annotations

from coach_app.engine.poker.preflop import hole_cards_to_notation, recommend_preflop
from coach_app.engine.poker.postflop import recommend_postflop
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
        "pot": pot_val,
        "to_call": to_call_val,
        "pot_odds": None,
        "hero_hand": [str(c) for c in state.hero_hole],
        "board": [str(c) for c in state.board],
        "hand_category": None,
        "range_summary": "Диапазоны оппонента: placeholder (MVP без трекинга линий/популяции).",
        "combos_summary": "Комбы: placeholder (MVP, упрощённые категории рук/дро).",
        "notes": [],
    }

    if state.street == Street.PREFLOP:
        plan = recommend_preflop(
            hero_hand=hero_hand_notation,
            hero_pos=hero_pos,
            has_aggression=has_aggr,
            game_type=state.game_type.value,
        )
        key_facts["hand_category"] = "preflop"
        key_facts["notes"] = list(plan.notes)
        conf = min(plan.confidence, float(report.confidence))
        return PokerDecision(action=plan.action, sizing=plan.sizing_bb, confidence=conf, key_facts=key_facts)

    # Postflop
    plan = recommend_postflop(
        street=state.street.value,
        hero_hole=state.hero_hole,
        board=state.board,
        pot=pot_val,
        to_call=to_call_val,
    )
    key_facts["hand_category"] = plan.hand_category.category
    key_facts["pot_odds"] = plan.facts.get("pot_odds")
    if "estimated_equity" in plan.facts:
        key_facts["estimated_equity"] = plan.facts["estimated_equity"]
    # extra draw facts
    key_facts["flush_draw"] = plan.hand_category.is_flush_draw
    key_facts["straight_draw"] = plan.hand_category.is_straight_draw
    key_facts["notes"] = list(plan.notes)
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


