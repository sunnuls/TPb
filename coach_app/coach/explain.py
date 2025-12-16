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
    if domain == "poker":
        act = decision_action
        size_txt = f" {sizing:g}" if sizing is not None else ""
        lines.append(f"Рекомендация: **{act}**{size_txt}.")
        lines.append(f"Уверенность: {confidence:.2f}.")

        # 1) Situation summary
        lines.append("")
        lines.append("1) Ситуация")
        for k, label in (
            ("game_type", "Формат"),
            ("street", "Улица"),
            ("effective_stack_bb", "Effective stack (bb)"),
            ("stack_bucket", "Stack bucket"),
            ("stack_class", "Stack class"),
            ("hero_hand", "Рука героя"),
            ("board", "Борд"),
            ("pot", "Банк"),
            ("to_call", "К коллу"),
            ("pot_odds", "Pot odds"),
            ("hand_category", "Категория"),
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
        lines.append("2) Диапазоны (Range Model v0)")
        if key_facts.get("hero_range_name") is not None:
            lines.append(f"- Диапазон героя: {key_facts.get('hero_range_name')}")
        if key_facts.get("opponent_range_name") is not None:
            lines.append(f"- Диапазон оппонента: {key_facts.get('opponent_range_name')}")
        if key_facts.get("range_intersection_note"):
            lines.append(f"- Примечание: {key_facts.get('range_intersection_note')}")
        if range_summary:
            lines.append(f"- Кратко: {range_summary}")

        # 3) Why action fits range position
        lines.append("")
        lines.append("3) Почему это действие подходит")
        if key_facts.get("range_position"):
            lines.append(f"- Позиция руки в диапазоне: {key_facts.get('range_position')}")
        if combos_summary:
            lines.append(f"- Основание по структуре рук/дро: {combos_summary}")
        if equity is not None:
            lines.append(f"- Equity (оценка): {_fmt_pct(equity)}")

        # 4) Next-street plan
        lines.append("")
        lines.append("4) План на следующую улицу")
        if key_facts.get("plan_hint"):
            lines.append(f"- Идея: {key_facts.get('plan_hint')}")
        if notes:
            if isinstance(notes, list) and notes:
                lines.append("- Заметки: " + "; ".join(map(str, notes)))
            elif isinstance(notes, str):
                lines.append(f"- Заметки: {notes}")

    elif domain == "blackjack":
        lines.append(f"Рекомендация: **{decision_action}**.")
        lines.append(f"Уверенность: {confidence:.2f}.")
        # For blackjack we expect facts like table/hand_type/total.
        for k in ("table", "hand_type", "total", "dealer_upcard", "player_hand"):
            if k in key_facts:
                lines.append(f"- {k}: {key_facts[k]}")
        if notes:
            if isinstance(notes, list):
                lines.append(f"- Примечания: " + "; ".join(map(str, notes)))
            else:
                lines.append(f"- Примечания: {notes}")

        if len(lines) <= 2:
            lines.append(
                "Недостаточно данных для ревью: нужны рука игрока и апкард дилера (и правила, если отличаются)."
            )
    else:
        lines.append("Неизвестный домен объяснения. Передайте domain='poker' или 'blackjack'.")

    # Ensure we do not include any claims beyond data present.
    return "\n".join(lines)


