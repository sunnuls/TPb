from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping

from coach_app.engine.poker.board import BoardTexture


class LineType(str, Enum):
    cbet = "cbet"
    check = "check"
    delayed_cbet = "delayed_cbet"
    probe = "probe"
    check_raise = "check_raise"
    check_call = "check_call"
    bet_fold = "bet_fold"
    bet_call = "bet_call"
    second_barrel = "second_barrel"
    give_up = "give_up"
    turn_probe = "turn_probe"
    turn_check_raise = "turn_check_raise"
    turn_value = "turn_value"
    river_value = "river_value"
    river_bluff = "river_bluff"
    river_check_call = "river_check_call"
    river_check_fold = "river_check_fold"


SizingCategory = Literal["small", "medium", "large", "unknown"]


class LineReason(str, Enum):
    range_advantage_dry = "range_advantage_dry"
    protection_wet = "protection_wet"
    pot_control_middle = "pot_control_middle"
    bluff_catch = "bluff_catch"
    value_top = "value_top"
    short_stack_simplify = "short_stack_simplify"
    probe_vs_check = "probe_vs_check"
    delayed_cbet_turn = "delayed_cbet_turn"
    check_raise_value = "check_raise_value"
    check_call_bluffcatch = "check_call_bluffcatch"
    value_bet_strong = "value_bet_strong"
    thin_value_bet = "thin_value_bet"
    second_barrel_value = "second_barrel_value"
    second_barrel_pressure = "second_barrel_pressure"
    give_up_bad_runout = "give_up_bad_runout"
    turn_probe_vs_check = "turn_probe_vs_check"
    river_value_thin = "river_value_thin"
    river_bluff_blockers_proxy = "river_bluff_blockers_proxy"
    river_give_up = "river_give_up"
    unknown_default = "unknown_default"


@dataclass(frozen=True)
class LineDecision:
    line_type: LineType
    sizing_category: SizingCategory
    line_reason: LineReason
    street_plan: dict[str, str] | None


def _mk_plan(immediate_plan: str | None, next_street_plan: str | None) -> dict[str, str] | None:
    out: dict[str, str] = {}
    if immediate_plan:
        out["immediate_plan"] = immediate_plan
    if next_street_plan:
        out["next_street_plan"] = next_street_plan
    return out or None


def select_line(
    *,
    street: str,
    board_texture: BoardTexture,
    hero_range_position: str | None,  # top|middle|bottom
    hero_hand_category: str | None,
    preflop_aggressor: bool | None,
    in_position: bool | None,
    street_initiative: str,  # hero|opponent|none
    flop_checked_through: bool | None,
    stack_depth_class: str | None,  # short|mid|deep
    game_type: str,  # cash|mtt
    facing_bet: bool,
    previous_street_summary: Mapping[str, Any] | None = None,
    runout_change: Mapping[str, Any] | None = None,
) -> LineDecision:
    """
    Postflop Line Logic v1 (deterministic).
    This is NOT a solver. It encodes instructive "good reg thinking" with explicit reasons.
    """
    gt = (game_type or "").lower()
    is_mtt_short = (gt == "mtt") and (stack_depth_class == "short")

    rp = hero_range_position or "bottom"
    dry = board_texture.dryness

    # Helper street plan templates (deterministic, derived from known facts)
    def plan_barrel_or_control() -> str:
        if dry == "dry":
            return "План: продолжаем на бланках; замедляемся на явных доборах/дро-картах."
        if dry == "semi-wet":
            return "План: баррелим на улучшениях и бланках; осторожнее на картах, усиливающих дро."
        return "План: чаще играем контроль банка; продолжаем только на улучшениях и хороших бланках."

    def runout_is_scary() -> bool:
        if not runout_change:
            return False
        return any(bool(runout_change.get(k)) for k in ("paired", "flush_intensified", "overcard", "connects"))

    # Facing a bet (call/raise/fold lines)
    if facing_bet:
        # OOP check-raise as value mostly with top range on drier textures
        if street == "river":
            if rp == "top":
                return LineDecision(
                    line_type=LineType.river_check_call,
                    sizing_category="unknown",
                    line_reason=LineReason.check_call_bluffcatch,
                    street_plan=_mk_plan(
                        "Ривер: чаще играем чек-колл с сильной рукой против ставки.",
                        "План: против дальнейшей агрессии оцениваем сайзинг и тайминги; без улучшений не раздуваем.",
                    ),
                )
            return LineDecision(
                line_type=LineType.river_check_fold,
                sizing_category="unknown",
                line_reason=LineReason.river_give_up,
                street_plan=_mk_plan(
                    "Ривер: без сильной руки чаще сдаёмся против ставки.",
                    None,
                ),
            )

        if street == "turn" and in_position is False and rp == "top" and dry != "wet":
            return LineDecision(
                line_type=LineType.turn_check_raise,
                sizing_category="large",
                line_reason=LineReason.check_raise_value,
                street_plan=_mk_plan(
                    "Тёрн OOP: выбираем чек-рейз на вэлью против ставки.",
                    "План: после рейза — добираем на безопасных картах; на опасных ран-аутах контролируем размер банка.",
                ),
            )

        if in_position is False and rp == "top" and dry != "wet":
            return LineDecision(
                line_type=LineType.check_raise,
                sizing_category="large",
                line_reason=LineReason.check_raise_value,
                street_plan=_mk_plan(
                    "Выбираем чек-рейз на вэлью против ставки.",
                    "План: после рейза — добираем на безопасных картах; на опасных ран-аутах контролируем размер банка.",
                ),
            )
        if rp == "top":
            return LineDecision(
                line_type=LineType.check_call,
                sizing_category="medium",
                line_reason=LineReason.value_bet_strong,
                street_plan=_mk_plan(
                    "Продолжаем против ставки (чек-колл) с верхом диапазона.",
                    "План: повышаем агрессию на безопасных картах и замедляемся на опасных ран-аутах.",
                ),
            )
        # Middle = bluff-catcher check/call (tighten in MTT short)
        if rp == "middle" and not is_mtt_short:
            return LineDecision(
                line_type=LineType.check_call,
                sizing_category="medium",
                line_reason=LineReason.check_call_bluffcatch,
                street_plan=_mk_plan(
                    "Защищаемся коллом против умеренных ставок.",
                    "План: сдаёмся против сильного давления на опасных картах.",
                ),
            )
        # MTT short prefers fewer bluff-catches
        if rp == "middle" and is_mtt_short:
            return LineDecision(
                line_type=LineType.check,
                sizing_category="unknown",
                line_reason=LineReason.short_stack_simplify,
                street_plan=_mk_plan(
                    "Short stack: меньше маргинальных коллов.",
                    "План: выбираем более простые линии.",
                ),
            )
        # Bottom: give up more on wet boards
        return LineDecision(
            line_type=LineType.check,
            sizing_category="unknown",
            line_reason=LineReason.pot_control_middle if dry != "dry" else LineReason.unknown_default,
            street_plan=_mk_plan(
                "Без сильной руки чаще сдаёмся против давления.",
                "План: чаще чек-фолд без явных улучшений.",
            ),
        )

    # Not facing a bet: choose betting/checking lines
    if street == "flop":
        if preflop_aggressor:
            # C-bet with top range; middle only on dry boards; bottom mostly check
            if rp == "top":
                size = "small" if dry == "dry" else "medium"
                return LineDecision(
                    line_type=LineType.cbet if hero_hand_category not in ("straight_flush", "quads", "full_house") else LineType.bet_call,
                    sizing_category=size,
                    line_reason=LineReason.range_advantage_dry if dry == "dry" else LineReason.value_bet_strong,
                    street_plan=_mk_plan(
                        "Флоп: ставим, потому что верх диапазона может добирать и защищаться.",
                        plan_barrel_or_control(),
                    ),
                )
            if rp == "middle":
                if dry == "dry" and in_position is True:
                    return LineDecision(
                        line_type=LineType.cbet,
                        sizing_category="small",
                        line_reason=LineReason.range_advantage_dry,
                        street_plan=_mk_plan(
                            "Флоп IP: ставим небольшим сайзом на сухой текстуре.",
                            plan_barrel_or_control(),
                        ),
                    )
                return LineDecision(
                    line_type=LineType.check,
                    sizing_category="unknown",
                    line_reason=LineReason.pot_control_middle if dry != "dry" else LineReason.unknown_default,
                    street_plan=_mk_plan(
                        "Флоп: чаще чек для контроля банка средней рукой.",
                        "План: реализуем equity и избегаем лишних рейз-спотов на плохой текстуре.",
                    ),
                )
            return LineDecision(
                line_type=LineType.check,
                sizing_category="unknown",
                line_reason=LineReason.unknown_default,
                street_plan=_mk_plan(
                    "Флоп: без причины не раздуваем банк.",
                    "План: чаще чек и реализуем equity.",
                ),
            )

        # Not preflop aggressor: probe when checked to you (IP) with top/middle on drier boards.
        if in_position is True and rp in ("top", "middle"):
            size = "small" if dry != "wet" else "medium"
            return LineDecision(
                line_type=LineType.probe,
                sizing_category=size,
                line_reason=LineReason.probe_vs_check,
                street_plan=_mk_plan(
                    "Флоп: используем проб-бет, когда до нас прочекали.",
                    plan_barrel_or_control(),
                ),
            )
        return LineDecision(
            line_type=LineType.check,
            sizing_category="unknown",
            line_reason=LineReason.unknown_default,
            street_plan=_mk_plan("Флоп: чаще чек без сильного преимущества.", None),
        )

    # TURN: delayed c-bet spot
    if street == "turn" and preflop_aggressor and flop_checked_through is True:
        if rp in ("top", "middle") and not is_mtt_short:
            size = "medium" if dry != "dry" else "small"
            return LineDecision(
                line_type=LineType.delayed_cbet,
                sizing_category=size,
                line_reason=LineReason.delayed_cbet_turn,
                street_plan=_mk_plan(
                    "Тёрн: ставим delayed c-bet после прочеканного флопа.",
                    plan_barrel_or_control(),
                ),
            )
        return LineDecision(
            line_type=LineType.check,
            sizing_category="unknown",
            line_reason=LineReason.pot_control_middle if dry != "dry" else LineReason.unknown_default,
            street_plan=_mk_plan(
                "Тёрн: без преимущества — контроль банка.",
                "План: продолжаем только на улучшениях.",
            ),
        )

    if street == "turn" and not facing_bet:
        prev_aggr = bool(previous_street_summary.get("had_aggression")) if previous_street_summary else None
        hero_prev_aggr = previous_street_summary.get("hero_aggressor") if previous_street_summary else None

        if preflop_aggressor and prev_aggr and hero_prev_aggr is True:
            if rp == "top":
                size = "medium" if not runout_is_scary() else "small"
                return LineDecision(
                    line_type=LineType.second_barrel,
                    sizing_category=size,
                    line_reason=LineReason.second_barrel_value,
                    street_plan=_mk_plan(
                        "Тёрн: второй баррель на вэлью с сильной рукой.",
                        "План: на ривере добираем на бланках; на страшных картах чаще контроль.",
                    ),
                )
            if rp == "middle" and not runout_is_scary() and in_position is True and not is_mtt_short:
                return LineDecision(
                    line_type=LineType.second_barrel,
                    sizing_category="small",
                    line_reason=LineReason.second_barrel_pressure,
                    street_plan=_mk_plan(
                        "Тёрн: продолжаем второй баррель как давление на диапазон колла флопа.",
                        "План: на ривере сдаёмся без улучшений против сопротивления.",
                    ),
                )
            return LineDecision(
                line_type=LineType.give_up,
                sizing_category="unknown",
                line_reason=LineReason.give_up_bad_runout,
                street_plan=_mk_plan(
                    "Тёрн: на плохом ран-ауте чаще сдаёмся/контролируем.",
                    "План: реализуем equity через чек.",
                ),
            )

        if not preflop_aggressor and prev_aggr is False and in_position is True and rp in ("top", "middle"):
            size = "small" if dry != "wet" else "medium"
            return LineDecision(
                line_type=LineType.turn_probe,
                sizing_category=size,
                line_reason=LineReason.turn_probe_vs_check,
                street_plan=_mk_plan(
                    "Тёрн: пробуем поставить после пассивного флопа.",
                    "План: на ривере добираем на бланках; сдаёмся на сопротивление.",
                ),
            )

        if rp == "top":
            return LineDecision(
                line_type=LineType.turn_value,
                sizing_category="medium",
                line_reason=LineReason.value_bet_strong,
                street_plan=_mk_plan(
                    "Тёрн: ставим на вэлью.",
                    "План: на ривере выбираем добор или контроль в зависимости от ран-аута.",
                ),
            )
        return LineDecision(
            line_type=LineType.check,
            sizing_category="unknown",
            line_reason=LineReason.pot_control_middle,
            street_plan=_mk_plan("Тёрн: контроль банка.", "План: играем аккуратно на ривере."),
        )

    if street == "river" and not facing_bet:
        prev_aggr = bool(previous_street_summary.get("had_aggression")) if previous_street_summary else None
        hero_prev_aggr = previous_street_summary.get("hero_aggressor") if previous_street_summary else None

        if rp == "top":
            return LineDecision(
                line_type=LineType.river_value,
                sizing_category="medium" if dry != "dry" else "small",
                line_reason=LineReason.value_bet_strong,
                street_plan=_mk_plan("Ривер: добираем вэлью.", None),
            )
        if rp == "middle" and dry == "dry" and in_position is True:
            return LineDecision(
                line_type=LineType.river_value,
                sizing_category="small",
                line_reason=LineReason.river_value_thin,
                street_plan=_mk_plan("Ривер: тонкий добор на сухом борде.", None),
            )
        if rp == "bottom" and in_position is True and prev_aggr is True and hero_prev_aggr is True and runout_is_scary():
            return LineDecision(
                line_type=LineType.river_bluff,
                sizing_category="small" if dry != "wet" else "medium",
                line_reason=LineReason.river_bluff_blockers_proxy,
                street_plan=_mk_plan("Ривер: блеф как давление на capped диапазон оппонента.", None),
            )
        return LineDecision(
            line_type=LineType.give_up,
            sizing_category="unknown",
            line_reason=LineReason.river_give_up,
            street_plan=_mk_plan("Ривер: сдаёмся/чекаем без явного вэлью.", None),
        )

    # Default: value betting when top of range and not facing bet
    if rp == "top":
        return LineDecision(
            line_type=LineType.bet_call,
            sizing_category="medium",
            line_reason=LineReason.value_bet_strong,
            street_plan=_mk_plan(
                "Ставим на вэлью с верхом диапазона.",
                plan_barrel_or_control(),
            ),
        )
    if rp == "middle":
        return LineDecision(
            line_type=LineType.bet_fold if dry == "dry" else LineType.check,
            sizing_category="small" if dry == "dry" else "unknown",
            line_reason=LineReason.thin_value_bet if dry == "dry" else LineReason.pot_control_middle,
            street_plan=_mk_plan(
                "Тонкий добор возможен только на сухой текстуре.",
                "План: иначе чаще контроль банка.",
            ),
        )
    return LineDecision(
        line_type=LineType.check,
        sizing_category="unknown",
        line_reason=LineReason.unknown_default,
        street_plan=_mk_plan("Контроль банка без явного преимущества.", None),
    )
