from __future__ import annotations

from dataclasses import dataclass

from coach_app.engine.poker.ranges.presets import (
    preset_3bet_vs_late,
    preset_bb_defend_vs_btn,
    preset_rfi,
    preset_shove_v0,
)
from coach_app.schemas.poker import PokerActionType, Position


RANKS = "23456789TJQKA"
RANK_TO_I = {r: i for i, r in enumerate(RANKS, start=2)}


def _hand_notation(c1: str, c2: str, suited: bool) -> str:
    # ranks only (e.g. "A", "K")
    r1, r2 = c1, c2
    if RANK_TO_I[r2] > RANK_TO_I[r1]:
        r1, r2 = r2, r1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{'s' if suited else 'o'}"


@dataclass(frozen=True)
class PreflopPlan:
    action: PokerActionType
    sizing_bb: float | None
    confidence: float
    notes: list[str]
    hero_range_name: str | None = None
    opp_range_name: str | None = None
    range_intersection_note: str | None = None
    range_position: str | None = None  # top|middle|bottom
    plan_hint: str | None = None
    range_summary: str | None = None


def recommend_preflop(
    *,
    hero_hand: str | None,
    hero_pos: Position | None,
    has_aggression: bool,
    game_type: str,
    stack_bucket: str,
    effective_stack_bb: float | None,
) -> PreflopPlan:
    """
    Deterministic, minimal preflop heuristic for 6-max.
    Uses simple placeholder ranges; NOT meant to be solver-accurate.
    """
    if hero_hand is None:
        return PreflopPlan(
            action=PokerActionType.check,
            sizing_bb=None,
            confidence=0.15,
            notes=["Preflop: неизвестны карты героя -> даю нейтральную линию (check)"],
            hero_range_name=None,
            opp_range_name=None,
            range_intersection_note=None,
            range_position=None,
            plan_hint="Нужны hole cards для диапазонной логики.",
            range_summary=None,
        )

    pos = hero_pos or Position.CO
    is_mtt = game_type == "NLHE_MTT"
    notes: list[str] = [f"Preflop Range Model v0 for {pos.value} ({'mtt' if is_mtt else 'cash'}; {stack_bucket})."]

    # Helper: map weight->range position
    def tier(w: float) -> str:
        if w >= 0.75:
            return "top"
        if w >= 0.5:
            return "middle"
        return "bottom"

    if not has_aggression:
        # Open spot: RFI or (MTT <20bb) shove/fold
        if is_mtt and stack_bucket == "mtt_lt20":
            shove = preset_shove_v0(pos, stack_bucket=stack_bucket)
            w = shove.weight(hero_hand)
            if w > 0:
                return PreflopPlan(
                    action=PokerActionType.all_in,
                    sizing_bb=effective_stack_bb,
                    confidence=0.7,
                    notes=notes + [f"Short stack: {hero_hand} входит в shove-range."],
                    hero_range_name=shove.metadata.get("name"),
                    opp_range_name="open_unknown",
                    range_intersection_note="Верх/середина пуш-диапазона",
                    range_position=tier(w),
                    plan_hint="Префлоп упрощается до push/fold при <20bb.",
                    range_summary=shove.describe(),
                )
            return PreflopPlan(
                action=PokerActionType.fold,
                sizing_bb=None,
                confidence=0.75,
                notes=notes + [f"Short stack: {hero_hand} вне shove-range -> фолд."],
                hero_range_name=shove.metadata.get("name"),
                opp_range_name="open_unknown",
                range_intersection_note="Вне пуш-диапазона",
                range_position="bottom",
                plan_hint="Сохраняем фишки: пуш только с верхом диапазона (v0).",
                range_summary=shove.describe(),
            )

        hero_rfi = preset_rfi(pos, stack_bucket=stack_bucket)
        w = hero_rfi.weight(hero_hand)
        if w > 0:
            size = 2.2 if pos == Position.BTN else 2.5
            return PreflopPlan(
                action=PokerActionType.raise_,
                sizing_bb=size,
                confidence=0.65,
                notes=notes + [f"RFI: {hero_hand} входит в open-range (вес {w:.2f})."],
                hero_range_name=hero_rfi.metadata.get("name"),
                opp_range_name="no_action_yet",
                range_intersection_note="Часть opening range",
                range_position=tier(w),
                plan_hint="Открываемся сайзингом ~2.2–2.5bb (v0).",
                range_summary=hero_rfi.describe(),
            )
        return PreflopPlan(
            action=PokerActionType.fold,
            sizing_bb=None,
            confidence=0.7,
            notes=notes + [f"RFI: {hero_hand} вне open-range -> фолд."],
            hero_range_name=hero_rfi.metadata.get("name"),
            opp_range_name="no_action_yet",
            range_intersection_note="Вне opening range",
            range_position="bottom",
            plan_hint="Фолд, если рука вне диапазона открытия (v0).",
            range_summary=hero_rfi.describe(),
        )

    # Facing aggression: approximate opener based on hero position (deterministic heuristic)
    if pos in (Position.BB, Position.SB):
        opener = "BTN"
    elif pos == Position.BTN:
        opener = "CO"
    elif pos == Position.CO:
        opener = "HJ"
    else:
        opener = "UTG"

    opp_open_name = f"{opener}_OPEN_v0"
    threebet = preset_3bet_vs_late(stack_bucket=stack_bucket, opener=opener)

    # Short stack MTT: mostly shove/fold; avoid flatting too much.
    if is_mtt and stack_bucket == "mtt_lt20":
        shove = preset_shove_v0(pos, stack_bucket=stack_bucket)
        w = shove.weight(hero_hand)
        if w > 0:
            return PreflopPlan(
                action=PokerActionType.all_in,
                sizing_bb=effective_stack_bb,
                confidence=0.7,
                notes=notes + [f"Short stack vs open: {hero_hand} -> пуш."],
                hero_range_name=shove.metadata.get("name"),
                opp_range_name=opp_open_name,
                range_intersection_note="Top of shove range vs open",
                range_position=tier(w),
                plan_hint="При <20bb против открытия чаще пуш/фолд (v0).",
                range_summary=shove.describe(),
            )
        return PreflopPlan(
            action=PokerActionType.fold,
            sizing_bb=None,
            confidence=0.75,
            notes=notes + [f"Short stack vs open: {hero_hand} вне пуш-диапазона -> фолд."],
            hero_range_name=shove.metadata.get("name"),
            opp_range_name=opp_open_name,
            range_intersection_note="Вне shove range vs open",
            range_position="bottom",
            plan_hint="Не коллим широко коротким стеком (v0).",
            range_summary=shove.describe(),
        )

    # Deep/mid: 3bet / call / fold
    w3 = threebet.weight(hero_hand)
    if w3 > 0:
        size = 7.5 if pos in (Position.SB, Position.BB) else 8.0
        return PreflopPlan(
            action=PokerActionType.raise_,
            sizing_bb=size,
            confidence=0.6,
            notes=notes + [f"Vs open: {hero_hand} входит в 3bet-range (вес {w3:.2f})."],
            hero_range_name=threebet.metadata.get("name"),
            opp_range_name=opp_open_name,
            range_intersection_note="Top of 3bet range",
            range_position=tier(w3),
            plan_hint="3bet для вэлью/инициативы (v0).",
            range_summary=threebet.describe(),
        )

    # Call/defend ranges: special-case BB vs BTN open.
    if pos == Position.BB and opener == "BTN":
        defend = preset_bb_defend_vs_btn(stack_bucket=stack_bucket)
        wd = defend.weight(hero_hand)
        if wd > 0:
            return PreflopPlan(
                action=PokerActionType.call,
                sizing_bb=None,
                confidence=0.55,
                notes=notes + [f"BB defend vs BTN: {hero_hand} входит в defend-call (вес {wd:.2f})."],
                hero_range_name=defend.metadata.get("name"),
                opp_range_name=opp_open_name,
                range_intersection_note="Средняя часть защиты",
                range_position=tier(wd),
                plan_hint="Колл как защита BB против BTN (v0).",
                range_summary=defend.describe(),
            )
        return PreflopPlan(
            action=PokerActionType.fold,
            sizing_bb=None,
            confidence=0.65,
            notes=notes + [f"BB defend vs BTN: {hero_hand} вне защиты -> фолд."],
            hero_range_name=defend.metadata.get("name"),
            opp_range_name=opp_open_name,
            range_intersection_note="Вне defend range",
            range_position="bottom",
            plan_hint="Фолд, если рука вне диапазона защиты (v0).",
            range_summary=defend.describe(),
        )

    # Default: fold if not in 3bet/call presets (v0 conservative)
    return PreflopPlan(
        action=PokerActionType.fold,
        sizing_bb=None,
        confidence=0.65,
        notes=notes + [f"Vs open: {hero_hand} вне 3bet/defend диапазонов -> фолд (v0)."],
        hero_range_name=threebet.metadata.get("name"),
        opp_range_name=opp_open_name,
        range_intersection_note="Вне defend/3bet",
        range_position="bottom",
        plan_hint="Консервативный фолд вне диапазонов защиты (v0).",
        range_summary=threebet.describe(),
    )


def hole_cards_to_notation(rank1: str, rank2: str, suited: bool) -> str:
    return _hand_notation(rank1, rank2, suited)


