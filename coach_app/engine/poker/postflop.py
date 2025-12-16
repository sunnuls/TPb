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
) -> PostflopPlan:
    notes: list[str] = []
    hc = categorize(hero_hole, board)

    pot_odds: float | None = None
    if pot is not None and to_call is not None and to_call > 0 and pot >= 0:
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else None

    # Made hand tiers (simplified)
    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "trips", "two_pair"}
    medium_made = {"pair"}

    # Deterministic action
    if hc.category in strong_made:
        notes.append("Сильная готовая рука (эвристика): играем агрессивно.")
        return PostflopPlan(
            action=PokerActionType.bet,
            sizing=0.66 if pot is not None else None,
            confidence=0.7 if pot is not None else 0.5,
            facts={"pot_odds": pot_odds},
            notes=notes,
            hand_category=hc,
        )

    if hc.category in medium_made:
        # With pot odds + facing bet -> call small, otherwise check
        if to_call is not None and to_call > 0:
            if pot_odds is None:
                notes.append("Есть колл, но банк/пот-оддсы неизвестны -> консервативно.")
                return PostflopPlan(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=0.35,
                    facts={"pot_odds": None},
                    notes=notes,
                    hand_category=hc,
                )
            # Pair vs bet: call if cheap
            if pot_odds <= 0.33:
                notes.append("Пара против ставки: колл при приемлемых pot odds (эвристика).")
                return PostflopPlan(
                    action=PokerActionType.call,
                    sizing=None,
                    confidence=0.55,
                    facts={"pot_odds": pot_odds},
                    notes=notes,
                    hand_category=hc,
                )
            notes.append("Пара против дорогой ставки: фолд (эвристика).")
            return PostflopPlan(
                action=PokerActionType.fold,
                sizing=None,
                confidence=0.6,
                facts={"pot_odds": pot_odds},
                notes=notes,
                hand_category=hc,
            )

        notes.append("Без явного колла: пара чаще играет чек/контроль банка (эвристика).")
        return PostflopPlan(
            action=PokerActionType.check,
            sizing=None,
            confidence=0.5,
            facts={"pot_odds": pot_odds},
            notes=notes,
            hand_category=hc,
        )

    # Draws / air
    est = _draw_equity_heuristic(street, hc)
    if to_call is not None and to_call > 0:
        if pot_odds is None:
            notes.append("Есть колл, но банк/пот-оддсы неизвестны -> фолд по умолчанию.")
            return PostflopPlan(
                action=PokerActionType.fold,
                sizing=None,
                confidence=0.4,
                facts={"pot_odds": None, "estimated_equity": est},
                notes=notes,
                hand_category=hc,
            )
        if est is not None and est >= pot_odds:
            notes.append("Дро: колл, если оценочная equity >= pot odds (эвристика).")
            return PostflopPlan(
                action=PokerActionType.call,
                sizing=None,
                confidence=0.55,
                facts={"pot_odds": pot_odds, "estimated_equity": est},
                notes=notes,
                hand_category=hc,
            )
        notes.append("Дро/хайкард: фолд, если pot odds требуют больше equity (эвристика).")
        return PostflopPlan(
            action=PokerActionType.fold,
            sizing=None,
            confidence=0.6,
            facts={"pot_odds": pot_odds, "estimated_equity": est},
            notes=notes,
            hand_category=hc,
        )

    notes.append("Нет данных о колле/банке -> чек по умолчанию (эвристика).")
    return PostflopPlan(
        action=PokerActionType.check,
        sizing=None,
        confidence=0.35,
        facts={"pot_odds": pot_odds, "estimated_equity": est},
        notes=notes,
        hand_category=hc,
    )


