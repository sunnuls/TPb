from __future__ import annotations

from typing import Any, Mapping

from coach_app.config import settings


def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return str(x)


def explain_from_key_facts(
    decision_action: str,
    sizing: float | None,
    confidence: float,
    key_facts: Mapping[str, Any],
    *,
    domain: str,
    language: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    """
    Build a user-facing explanation WITHOUT inventing facts.

    This function is intentionally template-based and only uses:
    - decision fields (action/sizing/confidence)
    - key_facts computed by the engine
    """
    lang = (language or settings.language).lower()
    if lang != "ru":
        # Minimal fallback; project default is Russian per requirement.
        lang = "ru"

    # Extract optional facts; if absent, we do not fabricate.
    equity = key_facts.get("equity")
    pot_odds = key_facts.get("pot_odds")
    range_summary = key_facts.get("range_summary")
    combos_summary = key_facts.get("combos_summary")
    notes = key_facts.get("notes")

    lines: list[str] = []
    if confidence < 1.0:
        w = warnings or []
        visionish = any(
            ("vision" in str(x).lower()) or ("карты" in str(x).lower()) or ("борд" in str(x).lower())
            for x in w
        )
        if domain == "poker" and visionish:
            lines.append("Анализ основан на видимых картах; ставки и стеки могли быть неизвестны.")
        else:
            lines.append("Анализ основан на частичных данных; некоторые параметры могли быть неизвестны.")
        lines.append("")
    if domain == "poker":
        act = decision_action
        size_txt = f" {sizing:g}" if sizing is not None else ""
        lines.append(f"Рекомендация: **{act}**{size_txt}.")
        lines.append(f"Уверенность: {confidence:.2f}.")

        # 1) Situation summary
        lines.append("")
        lines.append("1) Борд и ситуация")
        for k, label in (
            ("street", "Улица"),
            ("game_type", "Формат"),
            ("effective_stack_bb", "Effective stack (bb)"),
            ("stack_bucket", "Stack bucket"),
            ("stack_class", "Stack class"),
            ("hero_hand", "Рука героя"),
            ("board", "Борд"),
            ("board_texture", "Текстура борда"),
            ("pot", "Банк"),
            ("to_call", "К коллу"),
            ("pot_odds", "Pot odds"),
            ("hand_category", "Категория руки"),
        ):
            if k not in key_facts:
                continue
            v = key_facts.get(k)
            if v is None or v == []:
                continue
            if k == "pot_odds":
                v = _fmt_pct(v)
            lines.append(f"- {label}: {v}")

        # 2) Range vs range
        lines.append("")
        lines.append("2) Инициатива и позиция")
        for k, label in (
            ("preflop_aggressor", "Префлоп агрессор (герой)"),
            ("in_position", "Позиция (IP)"),
            ("street_initiative", "Инициатива на улице"),
            ("flop_checked_through", "Флоп прочекан"),
        ):
            if k not in key_facts:
                continue
            v = key_facts.get(k)
            if v is None:
                continue
            lines.append(f"- {label}: {v}")

        # 3) Why action fits range position
        lines.append("")
        lines.append("3) Как борд влияет на диапазон")
        if key_facts.get("hero_range_name") is not None:
            lines.append(f"- Диапазон героя: {key_facts.get('hero_range_name')}")
        if key_facts.get("opponent_range_name") is not None:
            lines.append(f"- Диапазон оппонента: {key_facts.get('opponent_range_name')}")
        if key_facts.get("range_intersection_note"):
            lines.append(f"- Примечание: {key_facts.get('range_intersection_note')}")
        if key_facts.get("range_position"):
            lines.append(f"- Позиция руки в диапазоне: {key_facts.get('range_position')}")
        if combos_summary:
            lines.append(f"- По комбинаторике/дро: {combos_summary}")
        if range_summary:
            lines.append(f"- Модель диапазонов: {range_summary}")
        if equity is not None:
            lines.append(f"- Equity (оценка): {_fmt_pct(equity)}")

        # 4) Next-street plan
        lines.append("")
        lines.append("4) Выбранная линия и почему")
        if key_facts.get("selected_line") is not None:
            sc = key_facts.get("sizing_category")
            if sc is not None:
                lines.append(f"- Линия: {key_facts.get('selected_line')} ({sc})")
            else:
                lines.append(f"- Линия: {key_facts.get('selected_line')}")
        pf = key_facts.get("pot_fraction")
        if pf is not None:
            try:
                lines.append(f"- Сайзинг: ~{float(pf) * 100:.0f}% банка")
            except Exception:
                lines.append(f"- Сайзинг: pot_fraction={pf}")
        if key_facts.get("recommended_bet_amount") is not None:
            lines.append(f"- Рекомендованный бет (amount): {key_facts.get('recommended_bet_amount')}")
        if key_facts.get("recommended_raise_to") is not None:
            lines.append(f"- Рекомендованный рейз (raise_to): {key_facts.get('recommended_raise_to')}")
        if key_facts.get("rounding_step") is not None:
            lines.append(f"- Округление: шаг {key_facts.get('rounding_step')}")
        if key_facts.get("line_reason") is not None:
            lines.append(f"- Причина: {key_facts.get('line_reason')}")
        if key_facts.get("plan_hint"):
            lines.append(f"- Коротко: {key_facts.get('plan_hint')}")

        lines.append("")
        lines.append("5) План на следующую улицу")
        sp = key_facts.get("street_plan")
        if isinstance(sp, Mapping):
            ip = sp.get("immediate_plan")
            np = sp.get("next_street_plan")
            if ip:
                lines.append(f"- Сейчас: {ip}")
            if np:
                lines.append(f"- Дальше: {np}")
        elif sp:
            lines.append(f"- {sp}")
        if notes:
            if isinstance(notes, list) and notes:
                lines.append("- Заметки: " + "; ".join(map(str, notes)))
            elif isinstance(notes, str):
                lines.append(f"- Заметки: {notes}")

    elif domain == "blackjack":
        lines.append(f"Рекомендация: **{decision_action}**.")
        lines.append(f"Уверенность: {confidence:.2f}.")

        player_hand = key_facts.get("player_hand")
        dealer_upcard = key_facts.get("dealer_upcard")
        hand_type = key_facts.get("player_hand_type") or key_facts.get("hand_type")
        total = key_facts.get("player_total") if key_facts.get("player_total") is not None else key_facts.get("total")
        allowed = key_facts.get("allowed_actions")
        overrides = key_facts.get("rule_overrides_applied")

        # 1) Hand summary
        lines.append("")
        lines.append("1) Сводка руки")
        if player_hand is not None:
            lines.append(f"- Рука: {player_hand}")
        if total is not None:
            lines.append(f"- Тотал: {total}")
        if hand_type is not None:
            lines.append(f"- Тип: {hand_type}")

        # 2) Dealer pressure
        lines.append("")
        lines.append("2) Карта дилера и давление")
        if dealer_upcard is not None:
            lines.append(f"- Апкард дилера: {dealer_upcard}")
            try:
                r = str(dealer_upcard)[0].upper()
                pressure = "высокое" if r in ("9", "T", "J", "Q", "K", "A") else "умеренное"
                lines.append(f"- Давление: {pressure}")
            except Exception:
                pass

        # 3) Recommended action
        lines.append("")
        lines.append("3) Рекомендованное действие")
        ra = key_facts.get("recommended_action")
        if ra is not None:
            lines.append(f"- Действие: {ra}")
        if allowed is not None:
            lines.append(f"- Разрешено: {allowed}")
        if overrides:
            if isinstance(overrides, list) and overrides:
                lines.append(f"- Применённые ограничения/оверрайды: {overrides}")

        # 4) EV reasoning
        lines.append("")
        lines.append("4) Почему альтернативы хуже (EV-логика, обучающая)")
        if key_facts.get("ev_reasoning_summary") is not None:
            lines.append(f"- Итог: {key_facts.get('ev_reasoning_summary')}")
        if key_facts.get("action_ev_loss") is not None:
            lines.append(f"- Потери EV по вариантам: {key_facts.get('action_ev_loss')}")
        if key_facts.get("avoided_mistakes"):
            lines.append(f"- Избегаем ошибок: {key_facts.get('avoided_mistakes')}")

        # 5) Rule of thumb
        lines.append("")
        lines.append("5) Правило-на-пальцах")
        try:
            action = str(decision_action)
            if action == "surrender":
                lines.append("- Если можно сдаться (late surrender), это часто лучший способ избежать крупных потерь EV в тяжёлых спотах.")
            elif action == "split":
                lines.append("- Сплит делаем, когда пара играет лучше как две отдельные руки, чем как один суммарный тотал.")
            elif action == "double":
                lines.append("- Дабл — это агрессивный добор EV: добавляем ставку, когда преимущество уже на нашей стороне.")
            elif action == "stand":
                lines.append("- Стэнд — когда наш тотал уже достаточно сильный и дополнительная карта чаще ухудшит ситуацию.")
            else:
                lines.append("- Хит — когда стоять слишком слабо против апкарда дилера и нужно улучшать руку.")
        except Exception:
            pass

        if notes:
            if isinstance(notes, list) and notes:
                lines.append("- Заметки: " + "; ".join(map(str, notes)))
            elif isinstance(notes, str):
                lines.append(f"- Заметки: {notes}")
    else:
        lines.append("Неизвестный домен объяснения. Передайте domain='poker' или 'blackjack'.")

    # Ensure we do not include any claims beyond data present.
    return "\n".join(lines)


