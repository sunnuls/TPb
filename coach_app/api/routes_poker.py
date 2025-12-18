from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from coach_app.coach.explain import explain_from_key_facts
from coach_app.engine.poker.analyze import analyze_poker_state
from coach_app.ingest.hand_history.dispatch import parse_hand_history
from coach_app.ingest.vision.base import VisionAdapter
from coach_app.ingest.vision.fusion import merge_partial_state
from coach_app.ingest.vision.generic_adapter import GenericVisionAdapter
from coach_app.product.mode import ProductMode
from coach_app.product.policy import enforce_policy
from coach_app.schemas.ingest import HandHistoryParseError, ParseReport
from coach_app.schemas.meta import Meta
from coach_app.schemas.poker import PokerDecision, PokerGameState
from coach_app.state.validate import StateValidationError, validate_poker_state


router = APIRouter()


class PokerAnalyzeRequest(BaseModel):
    hand_history_text: str = Field(..., min_length=1)
    mode: ProductMode | None = None
    meta: Meta | None = None


class PokerAnalyzeResponse(BaseModel):
    decision: PokerDecision
    explanation: str
    parse_report: ParseReport


class PokerScreenshotPayload(BaseModel):
    hand_history_text: str | None = None
    mode: ProductMode | None = None
    meta: Meta | None = None


class PokerScreenshotAnalyzeResponse(BaseModel):
    decision: PokerDecision
    explanation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


def get_poker_vision_adapter() -> VisionAdapter:
    return GenericVisionAdapter(game="poker")


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

    meta = req.meta if req.meta is not None else Meta()
    policy = enforce_policy(
        req.mode,
        "poker",
        {"state": state, "hand_history_text": req.hand_history_text},
        meta,
        getattr(report, "confidence", None),
    )
    if not policy.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "POLICY_BLOCK",
                "message": policy.message,
                "reason": policy.reason.value,
                "audit_flags": policy.audit_flags,
            },
        )

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
        warnings=report.warnings,
    )
    return PokerAnalyzeResponse(decision=decision, explanation=explanation, parse_report=report)


@router.post("/analyze/poker/screenshot", response_model=PokerScreenshotAnalyzeResponse)
async def analyze_poker_screenshot(
    image: UploadFile = File(...),
    payload: str | None = Form(default=None),
    adapter: VisionAdapter = Depends(get_poker_vision_adapter),
) -> PokerScreenshotAnalyzeResponse:
    payload_obj: PokerScreenshotPayload | None = None
    if payload:
        try:
            payload_obj = PokerScreenshotPayload.model_validate(json.loads(payload))
        except Exception as e:
            raise HTTPException(status_code=422, detail={"message": "Некорректный JSON payload", "error": str(e)})

    hh_text = payload_obj.hand_history_text if payload_obj is not None else None
    mode = payload_obj.mode if payload_obj is not None else None
    meta = payload_obj.meta if payload_obj is not None and payload_obj.meta is not None else Meta()

    base_state: PokerGameState | None = None
    base_report: ParseReport | None = None
    if hh_text:
        try:
            parsed = parse_hand_history(hh_text)
            base_state = parsed.state
            base_report = parsed.report
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=HandHistoryParseError(message="Ошибка парсинга hand history", warnings=[str(e)]).model_dump(),
            )

    img_bytes = await image.read()
    vision = adapter.parse(img_bytes)

    try:
        merged = merge_partial_state(base_state, vision)
    except StateValidationError as ve:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Состояние неконсистентно после merge",
                "errors": [e.__dict__ for e in ve.errors],
                "warnings": list(vision.warnings),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail={"message": "Не удалось объединить состояние", "error": str(e)})

    if not isinstance(merged.merged_state, PokerGameState):
        raise HTTPException(status_code=422, detail={"message": "Ожидалось poker-состояние"})
    state = merged.merged_state

    policy = enforce_policy(
        mode,
        "poker",
        {"state": state, "hand_history_text": hh_text},
        meta,
        float(merged.global_confidence) if merged.global_confidence is not None else None,
    )
    if not policy.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "POLICY_BLOCK",
                "message": policy.message,
                "reason": policy.reason.value,
                "audit_flags": policy.audit_flags,
            },
        )

    if len(state.hero_hole) != 2:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Недостаточно данных для анализа: hero_hand не распознан",
                "missing_fields": ["hero_hole"],
                "warnings": list(merged.warnings),
                "adapter": {"name": vision.adapter_name, "version": vision.adapter_version},
            },
        )

    report: ParseReport
    if base_report is not None:
        report = base_report.model_copy(deep=True)
        report.warnings = list(report.warnings) + list(merged.warnings)
        try:
            report.confidence = float(min(float(report.confidence), float(merged.global_confidence)))
        except Exception:
            pass
        if "hero_hole" in report.missing_fields and len(state.hero_hole) == 2:
            report.missing_fields = [x for x in report.missing_fields if x != "hero_hole"]
        if "board" in report.missing_fields and state.board:
            report.missing_fields = [x for x in report.missing_fields if x != "board"]
        report.parsed = dict(report.parsed)
        report.parsed.update(
            {
                "vision_adapter": {"name": vision.adapter_name, "version": vision.adapter_version},
                "vision_partial": dict(vision.partial_state),
            }
        )
    else:
        missing = ["players", "small_blind", "big_blind", "pot", "to_call", "action_history"]
        report = ParseReport(
            parser=f"VisionAdapter:{vision.adapter_name}",
            room="unknown",
            game_type_detected=state.game_type.value,
            confidence=float(merged.global_confidence),
            missing_fields=missing,
            warnings=list(merged.warnings),
            parsed={
                "hero_hand": [str(c) for c in state.hero_hole],
                "board": [str(c) for c in state.board],
                "street": state.street.value,
            },
        )

    try:
        validate_poker_state(state)
    except StateValidationError as ve:
        raise HTTPException(
            status_code=422,
            detail={"message": "Состояние неконсистентно", "errors": [e.__dict__ for e in ve.errors]},
        )

    decision = analyze_poker_state(state, report)
    response_confidence = float(min(float(decision.confidence), float(merged.global_confidence)))
    explanation = explain_from_key_facts(
        decision_action=decision.action.value,
        sizing=decision.sizing,
        confidence=response_confidence,
        key_facts=decision.key_facts,
        domain="poker",
        warnings=list(merged.warnings),
    )
    return PokerScreenshotAnalyzeResponse(
        decision=decision,
        explanation=explanation,
        confidence=response_confidence,
        warnings=list(merged.warnings),
    )


@router.post("/analyze/poker/instant_review", response_model=PokerScreenshotAnalyzeResponse)
async def analyze_poker_instant_review(
    image: UploadFile = File(...),
    payload: str | None = Form(default=None),
    adapter: VisionAdapter = Depends(get_poker_vision_adapter),
) -> PokerScreenshotAnalyzeResponse:
    return await analyze_poker_screenshot(image=image, payload=payload, adapter=adapter)
