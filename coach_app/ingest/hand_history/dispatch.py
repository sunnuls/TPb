from __future__ import annotations

from dataclasses import dataclass

from coach_app.ingest.hand_history.generic import GenericHandHistoryParser
from coach_app.ingest.hand_history.pokerstars import PokerStarsHandHistoryParser
from coach_app.schemas.ingest import HandHistoryParseError, ParseReport
from coach_app.schemas.poker import PokerGameState


@dataclass(frozen=True)
class DispatchedParse:
    state: PokerGameState
    report: ParseReport


def _score(report: ParseReport) -> tuple[int, float]:
    """
    Higher is better.
    - fewer missing fields preferred
    - higher confidence preferred
    """
    return (-len(report.missing_fields), report.confidence)


def parse_hand_history(hand_history_text: str) -> DispatchedParse:
    """
    Choose the best parser for the given HH text.
    Strategy:
    - If text strongly looks like PokerStars -> try PokerStars first, then generic.
    - Otherwise try generic first, then PokerStars as fallback.
    """
    text = hand_history_text or ""
    t = text.lower()

    ps = PokerStarsHandHistoryParser()
    gen = GenericHandHistoryParser()

    candidates: list[tuple[PokerGameState, ParseReport]] = []

    looks_ps = ("pokerstars hand" in t) or ("pokerstars" in t and "dealt to" in t)
    parsers = [ps, gen] if looks_ps else [gen, ps]

    for p in parsers:
        try:
            state, report = p.parse(text)
            candidates.append((state, report))
        except Exception as e:
            # Parser crash: treat as very low confidence result.
            report = ParseReport(
                parser=p.__class__.__name__,
                room=getattr(p, "room", "unknown"),
                game_type_detected="unknown",
                confidence=0.0,
                missing_fields=["hand_history_text"],
                warnings=[f"Parser failed: {e!r}"],
                parsed={},
            )
            # We cannot return state on crash; skip.
            continue

    if not candidates:
        raise ValueError("No parsers produced a result")

    best_state, best_report = sorted(candidates, key=lambda x: _score(x[1]), reverse=True)[0]
    return DispatchedParse(state=best_state, report=best_report)


def ensure_parse_ok(report: ParseReport, *, required: list[str]) -> None:
    missing = sorted(set(report.missing_fields).intersection(set(required)))
    if missing:
        raise ValueError(
            HandHistoryParseError(
                message="Не удалось распарсить обязательные поля из hand_history_text",
                missing_fields=missing,
                warnings=report.warnings,
                parse_report=report,
            ).model_dump_json()
        )


