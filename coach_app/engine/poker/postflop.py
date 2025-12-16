from __future__ import annotations

from dataclasses import dataclass

from coach_app.engine.poker.hand_strength import HandCategory, categorize
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
    game_type: str,
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

    # Made hand tiers (simplified)
    # Deterministic action
    if hc.category in strong_made:
        notes.append("Сильная готовая рука: это верх диапазона -> играем на вэлью.")
        plan_hint = "value: ставка/рейз для вэлью и защиты"
        return PostflopPlan(
            action=PokerActionType.bet,
            sizing=0.66 if pot is not None else None,
            confidence=0.7 if pot is not None else 0.5,
            facts={
                "pot_odds": pot_odds,
                "range_position": range_pos,
                "plan_hint": plan_hint,
                "hero_range_name": f"RFI_proxy_{stack_bucket}",
                "opponent_range_name": "postflop_vs_bet" if (to_call or 0) > 0 else "postflop_vs_check",
                "range_intersection_note": "Сильная готовая рука в верхней части диапазона",
                "range_summary": "Range Model v0: постфлоп без трекинга линий; используем proxy по категории руки.",
            },
            notes=notes,
            hand_category=hc,
        )

    if hc.category in medium_made:
        # With pot odds + facing bet -> call small, otherwise check
        if to_call is not None and to_call > 0:
            plan_hint = "bluff-catcher: чек-колл умеренных ставок"
            if pot_odds is None:
                notes.append("Есть колл, но банк/пот-оддсы неизвестны -> консервативно.")
                return PostflopPlan(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=0.35,
                    facts={
                        "pot_odds": None,
                        "range_position": range_pos,
                        "plan_hint": plan_hint,
                        "hero_range_name": f"RFI_proxy_{stack_bucket}",
                        "opponent_range_name": "postflop_bet_range_v0",
                        "range_intersection_note": "Средняя часть диапазона: колл без точных odds = осторожно",
                        "range_summary": "Range Model v0: постфлоп с ограниченными данными.",
                    },
                    notes=notes,
                    hand_category=hc,
                )
            # Pair vs bet: call if cheap
            if is_short_mtt:
                # short stack: меньше коллов/блеф-кэтчей
                if pot_odds <= 0.25:
                    notes.append("MTT <20bb: блеф-кэтч с парой только при очень дешёвой цене.")
                    return PostflopPlan(
                        action=PokerActionType.call,
                        sizing=None,
                        confidence=0.5,
                        facts={
                            "pot_odds": pot_odds,
                            "range_position": range_pos,
                            "plan_hint": plan_hint,
                            "hero_range_name": f"RFI_proxy_{stack_bucket}",
                            "opponent_range_name": "postflop_bet_range_v0",
                            "range_intersection_note": "MTT short: колл только при дешёвой цене",
                            "range_summary": "Range Model v0: short stack снижает блеф-кэтч частоту.",
                        },
                        notes=notes,
                        hand_category=hc,
                    )
                notes.append("MTT <20bb: чаще фолд с маргинальной парой против ставки.")
                return PostflopPlan(
                    action=PokerActionType.fold,
                    sizing=None,
                    confidence=0.6,
                    facts={
                        "pot_odds": pot_odds,
                        "range_position": range_pos,
                        "plan_hint": "fold: защита стека важнее маргинальных коллов",
                        "hero_range_name": f"RFI_proxy_{stack_bucket}",
                        "opponent_range_name": "postflop_bet_range_v0",
                        "range_intersection_note": "MTT short: маргинальные пары чаще уходят в фолд",
                        "range_summary": "Range Model v0: short stack = низкая терпимость к дисперсии.",
                    },
                    notes=notes,
                    hand_category=hc,
                )

            if pot_odds <= 0.33:
                notes.append("Пара против ставки: колл при приемлемых pot odds (эвристика).")
                return PostflopPlan(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=0.55,
                    facts={
                        "pot_odds": pot_odds,
                        "range_position": range_pos,
                        "plan_hint": plan_hint,
                        "hero_range_name": f"RFI_proxy_{stack_bucket}",
                        "opponent_range_name": "postflop_bet_range_v0",
                        "range_intersection_note": "Средняя часть диапазона: колл при приемлемых odds",
                        "range_summary": "Range Model v0: постфлоп — диапазонные роли через категорию руки.",
                    },
                    notes=notes,
                    hand_category=hc,
                )
            notes.append("Пара против дорогой ставки: фолд (эвристика).")
            return PostflopPlan(
                action=PokerActionType.fold,
                sizing=None,
                confidence=0.6,
                facts={
                    "pot_odds": pot_odds,
                    "range_position": range_pos,
                    "plan_hint": "fold: слишком дорого для блеф-кэтча",
                    "hero_range_name": f"RFI_proxy_{stack_bucket}",
                    "opponent_range_name": "postflop_bet_range_v0",
                    "range_intersection_note": "Средняя/низ диапазона: сдаёмся против дорогой ставки",
                    "range_summary": "Range Model v0: постфлоп — без солвера, только объяснимые эвристики.",
                },
                notes=notes,
                hand_category=hc,
            )

        notes.append("Без явного колла: с парой чаще контролируем банк.")
        return PostflopPlan(
            action=PokerActionType.check,
            sizing=None,
            confidence=0.5,
            facts={
                "pot_odds": pot_odds,
                "range_position": range_pos,
                "plan_hint": "control: чек, чтобы реализовать equity и не раздувать банк",
                "hero_range_name": f"RFI_proxy_{stack_bucket}",
                "opponent_range_name": "postflop_vs_check",
                "range_intersection_note": "Средняя часть диапазона: контроль банка",
                "range_summary": "Range Model v0: постфлоп — контроль банка с маргинальной силой.",
            },
            notes=notes,
            hand_category=hc,
        )

    # Draws / air
    est = _draw_equity_heuristic(street, hc)
    if to_call is not None and to_call > 0:
        plan_hint = "semi-bluff/call: решение зависит от цены"
        if pot_odds is None:
            notes.append("Есть колл, но банк/пот-оддсы неизвестны -> фолд по умолчанию.")
            return PostflopPlan(
                action=PokerActionType.fold,
                sizing=None,
                confidence=0.4,
                facts={
                    "pot_odds": None,
                    "estimated_equity": est,
                    "range_position": range_pos,
                    "plan_hint": "fold: нет данных для +EV колла",
                    "hero_range_name": f"RFI_proxy_{stack_bucket}",
                    "opponent_range_name": "postflop_bet_range_v0",
                    "range_intersection_note": "Низ диапазона: без odds не тянем дро",
                    "range_summary": "Range Model v0: нет рандома/солвера; без odds — фолд по умолчанию.",
                },
                notes=notes,
                hand_category=hc,
            )
        if is_short_mtt:
            # short stack: меньше "погони" за дро
            if est is not None and pot_odds is not None and est >= pot_odds and pot_odds <= 0.25:
                notes.append("MTT <20bb: тянем дро только при очень дешёвой цене.")
                return PostflopPlan(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=0.5,
                    facts={
                        "pot_odds": pot_odds,
                        "estimated_equity": est,
                        "range_position": range_pos,
                        "plan_hint": plan_hint,
                        "hero_range_name": f"RFI_proxy_{stack_bucket}",
                        "opponent_range_name": "postflop_bet_range_v0",
                        "range_intersection_note": "MTT short: колл дро только при дешёвой цене",
                        "range_summary": "Range Model v0: short stack снижает частоту коллов на дро.",
                    },
                    notes=notes,
                    hand_category=hc,
                )
            notes.append("MTT <20bb: чаще фолд дро против ставки, чтобы снизить дисперсию.")
            return PostflopPlan(
                action=PokerActionType.fold,
                sizing=None,
                confidence=0.6,
                facts={
                    "pot_odds": pot_odds,
                    "estimated_equity": est,
                    "range_position": range_pos,
                    "plan_hint": "fold: short stack, избегаем маргинальных коллов",
                    "hero_range_name": f"RFI_proxy_{stack_bucket}",
                    "opponent_range_name": "postflop_bet_range_v0",
                    "range_intersection_note": "MTT short: дисциплина важнее тонких коллов",
                    "range_summary": "Range Model v0: short stack = меньше блефов/дро-коллов.",
                },
                notes=notes,
                hand_category=hc,
            )

        if est is not None and est >= pot_odds:
            notes.append("Дро: колл, если оценочная equity >= pot odds (эвристика).")
            return PostflopPlan(
                action=PokerActionType.call,
                sizing=None,
                confidence=0.55,
                facts={
                    "pot_odds": pot_odds,
                    "estimated_equity": est,
                    "range_position": range_pos,
                    "plan_hint": plan_hint,
                    "hero_range_name": f"RFI_proxy_{stack_bucket}",
                    "opponent_range_name": "postflop_bet_range_v0",
                    "range_intersection_note": "Средняя часть диапазона: колл дро при достаточной цене",
                    "range_summary": "Range Model v0: дро-решение по pot odds vs оценочной equity.",
                },
                notes=notes,
                hand_category=hc,
            )
        notes.append("Дро/хайкард: фолд, если pot odds требуют больше equity (эвристика).")
        return PostflopPlan(
            action=PokerActionType.fold,
            sizing=None,
            confidence=0.6,
            facts={
                "pot_odds": pot_odds,
                "estimated_equity": est,
                "range_position": range_pos,
                "plan_hint": "fold: цена слишком высокая для дро",
                "hero_range_name": f"RFI_proxy_{stack_bucket}",
                "opponent_range_name": "postflop_bet_range_v0",
                "range_intersection_note": "Низ/середина диапазона: сдаёмся при плохой цене",
                "range_summary": "Range Model v0: без симуляций — только объяснимые пороги.",
            },
            notes=notes,
            hand_category=hc,
        )

    if is_short_mtt and (hc.is_flush_draw or hc.is_straight_draw):
        notes.append("MTT <20bb: меньше полублефов без фолд-эквити -> чаще чек.")
        plan_hint = "control: чек, реализуем equity"
        return PostflopPlan(
            action=PokerActionType.check,
            sizing=None,
            confidence=0.45,
            facts={
                "pot_odds": pot_odds,
                "estimated_equity": est,
                "range_position": range_pos,
                "plan_hint": plan_hint,
                "hero_range_name": f"RFI_proxy_{stack_bucket}",
                "opponent_range_name": "postflop_vs_check",
                "range_intersection_note": "MTT short: меньше полублефов",
                "range_summary": "Range Model v0: short stack упрощает линии.",
            },
            notes=notes,
            hand_category=hc,
        )

    notes.append("Нет данных о колле/банке -> чек по умолчанию.")
    return PostflopPlan(
        action=PokerActionType.check,
        sizing=None,
        confidence=0.35,
        facts={
            "pot_odds": pot_odds,
            "estimated_equity": est,
            "range_position": range_pos,
            "plan_hint": "neutral: чек (недостаточно данных)",
            "hero_range_name": f"RFI_proxy_{stack_bucket}",
            "opponent_range_name": "postflop_vs_check",
            "range_intersection_note": "Недостаточно фактов -> нейтральная линия",
            "range_summary": "Range Model v0: без данных о ставках — осторожный чек.",
        },
        notes=notes,
        hand_category=hc,
    )


