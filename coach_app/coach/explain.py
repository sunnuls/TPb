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

        # Show only validated / computed facts if present
        if "street" in key_facts and key_facts.get("street") is not None:
            lines.append(f"- Street: {key_facts['street']}")
        if "hero_hand" in key_facts and key_facts.get("hero_hand"):
            lines.append(f"- Hero: {key_facts['hero_hand']}")
        if "board" in key_facts and key_facts.get("board"):
            lines.append(f"- Board: {key_facts['board']}")
        if "pot" in key_facts and key_facts.get("pot") is not None:
            lines.append(f"- Pot: {key_facts['pot']}")
        if "to_call" in key_facts and key_facts.get("to_call") is not None:
            lines.append(f"- To call: {key_facts['to_call']}")
        if "hand_category" in key_facts and key_facts.get("hand_category"):
            lines.append(f"- Категория руки: {key_facts['hand_category']}")

        if equity is not None:
            lines.append(f"- Equity (оценка): {_fmt_pct(equity)}")
        if pot_odds is not None:
            lines.append(f"- Pot odds (цена колла): {_fmt_pct(pot_odds)}")
        if range_summary:
            lines.append(f"- Диапазоны (кратко): {range_summary}")
        if combos_summary:
            lines.append(f"- Комбы/категории: {combos_summary}")
        if notes:
            if isinstance(notes, list):
                lines.append(f"- Примечания: " + "; ".join(map(str, notes)))
            else:
                lines.append(f"- Примечания: {notes}")

        if len(lines) <= 2:
            lines.append(
                "Недостаточно вычисленных фактов для подробного ревью. "
                "Добавьте стрит/борд/размеры ставок или используйте парсер HH."
            )

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


