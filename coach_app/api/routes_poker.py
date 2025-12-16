from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from coach_app.coach.explain import explain_from_key_facts
from coach_app.engine.poker.analyze import analyze_poker_state
from coach_app.ingest.hand_history.dispatch import parse_hand_history
from coach_app.schemas.ingest import HandHistoryParseError, ParseReport
from coach_app.schemas.poker import PokerDecision, PokerGameState
from coach_app.state.validate import StateValidationError, validate_poker_state


router = APIRouter()


class PokerAnalyzeRequest(BaseModel):
    hand_history_text: str = Field(..., min_length=1)
    meta: dict[str, Any] | None = None


class PokerAnalyzeResponse(BaseModel):
    decision: PokerDecision
    explanation: str
    parse_report: ParseReport


@router.post("/analyze/poker", response_model=PokerAnalyzeResponse)
def analyze_poker(req: PokerAnalyzeRequest) -> PokerAnalyzeResponse:
    try:
        parsed = parse_hand_history(req.hand_history_text)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=HandHistoryParseError(message="Ошибка парсинга hand history", warnings=[str(e)]).model_dump(),
        )

    state: PokerGameState = parsed.state
    report: ParseReport = parsed.report

    # Required minimal fields for MVP engine
    required = {"hero_hole"}
    missing_required = sorted(required.intersection(set(report.missing_fields)))
    if missing_required:
        raise HTTPException(
            status_code=422,
            detail=HandHistoryParseError(
                message="Не удалось извлечь обязательные поля",
                missing_fields=missing_required,
                warnings=report.warnings,
                parse_report=report,
            ).model_dump(),
        )

    # Validate state consistency
    try:
        validate_poker_state(state)
    except StateValidationError as ve:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Состояние неконсистентно",
                "errors": [e.__dict__ for e in ve.errors],
                "parse_report": report.model_dump(),
            },
        )

    # Engine decision
    decision = analyze_poker_state(state, report)

    # Explanation strictly from Decision.key_facts + decision fields (no external claims)
    explanation = explain_from_key_facts(
        decision_action=decision.action.value,
        sizing=decision.sizing,
        confidence=decision.confidence,
        key_facts=decision.key_facts,
        domain="poker",
    )
    return PokerAnalyzeResponse(decision=decision, explanation=explanation, parse_report=report)
