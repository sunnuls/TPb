from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from coach_app.coach.explain import explain_from_key_facts
from coach_app.engine.blackjack.analyze import analyze_blackjack
from coach_app.engine.blackjack.trainer import evaluate_answer, get_scenario
from coach_app.product.mode import ProductMode
from coach_app.product.policy import enforce_policy
from coach_app.schemas.blackjack import BlackjackAnalyzeRequest, BlackjackDecision, BlackjackState, BlackjackTrainRequest
from coach_app.schemas.meta import Meta
from coach_app.state.validate import StateValidationError, validate_blackjack_state


router = APIRouter()


class BlackjackAnalyzeResponse(BaseModel):
    decision: BlackjackDecision
    explanation: str
    confidence: float


@router.post("/analyze/blackjack", response_model=BlackjackAnalyzeResponse)
def analyze_blackjack_route(req: BlackjackAnalyzeRequest) -> BlackjackAnalyzeResponse:
    meta = req.meta if req.meta is not None else Meta()
    policy = enforce_policy(req.mode, "blackjack", req.model_dump(), meta, 1.0)
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

    state = BlackjackState(
        player_hand=req.player_hand,
        dealer_upcard=req.dealer_upcard,
        allowed_actions=req.allowed_actions,
        split_count=req.split_count,
        hand_doubled=req.hand_doubled,
        running_count=req.running_count,
        true_count=req.true_count,
        rules=req.rules,
        confidence=1.0,
    )

    try:
        validate_blackjack_state(state)
    except StateValidationError as ve:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Состояние неконсистентно",
                "errors": [e.__dict__ for e in ve.errors],
            },
        )

    decision = analyze_blackjack(
        player_hand=state.player_hand,
        dealer_upcard=state.dealer_upcard,
        rules=state.rules,
        allowed_actions=state.allowed_actions,
        split_count=state.split_count,
        hand_doubled=state.hand_doubled,
    )

    explanation = explain_from_key_facts(
        decision_action=decision.action.value,
        sizing=None,
        confidence=decision.confidence,
        key_facts=decision.key_facts,
        domain="blackjack",
        warnings=[],
    )

    return BlackjackAnalyzeResponse(decision=decision, explanation=explanation, confidence=decision.confidence)


class BlackjackTrainResponse(BaseModel):
    scenario_index: int
    scenario: dict
    correct: bool | None
    ev_loss: str | None
    decision: BlackjackDecision
    explanation: str


@router.post("/train/blackjack", response_model=BlackjackTrainResponse)
def train_blackjack_route(req: BlackjackTrainRequest) -> BlackjackTrainResponse:
    meta = req.meta if req.meta is not None else Meta()

    # Deterministic scenarios. If scenario_index is omitted, we return scenario 0.
    if req.mode == "trainer":
        policy = enforce_policy(
            ProductMode.TRAIN,
            "blackjack",
            {"_input_source": "internal_trainer", "state": req.model_dump()},
            meta,
            1.0,
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

        idx, sc = get_scenario(req.scenario_index)
        # If chosen_action not provided, just return scenario for the user.
        if req.chosen_action is None:
            decision = analyze_blackjack(
                player_hand=sc.player_hand,
                dealer_upcard=sc.dealer_upcard,
                rules=sc.rules,
                allowed_actions=sc.allowed_actions,
                split_count=0,
                hand_doubled=False,
            )
            explanation = explain_from_key_facts(
                decision_action=decision.action.value,
                sizing=None,
                confidence=decision.confidence,
                key_facts=decision.key_facts,
                domain="blackjack",
                warnings=[],
            )
            return BlackjackTrainResponse(
                scenario_index=idx,
                scenario={
                    "player_hand": list(sc.player_hand),
                    "dealer_upcard": sc.dealer_upcard,
                    "allowed_actions": [a.value for a in sc.allowed_actions] if sc.allowed_actions else None,
                    "rules": sc.rules.model_dump(),
                },
                correct=None,
                ev_loss=None,
                decision=decision,
                explanation=explanation,
            )

        out = evaluate_answer(scenario_index=req.scenario_index, chosen_action=req.chosen_action)
        decision: BlackjackDecision = out["decision"]
        explanation = explain_from_key_facts(
            decision_action=decision.action.value,
            sizing=None,
            confidence=decision.confidence,
            key_facts=decision.key_facts,
            domain="blackjack",
            warnings=[],
        )
        return BlackjackTrainResponse(
            scenario_index=int(out["scenario_index"]),
            scenario=dict(out["scenario"]),
            correct=bool(out["correct"]),
            ev_loss=out.get("ev_loss"),
            decision=decision,
            explanation=explanation,
        )

    # review mode: reuse analyze endpoint behavior using request payload
    policy = enforce_policy(req.product_mode, "blackjack", req.model_dump(), meta, 1.0)
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

    decision = analyze_blackjack(
        player_hand=list(req.player_hand or []),
        dealer_upcard=str(req.dealer_upcard or ""),
        rules=req.rules,
        allowed_actions=req.allowed_actions,
        split_count=req.split_count,
        hand_doubled=req.hand_doubled,
    )
    explanation = explain_from_key_facts(
        decision_action=decision.action.value,
        sizing=None,
        confidence=decision.confidence,
        key_facts=decision.key_facts,
        domain="blackjack",
        warnings=[],
    )
    return BlackjackTrainResponse(
        scenario_index=0,
        scenario={
            "player_hand": list(req.player_hand),
            "dealer_upcard": req.dealer_upcard,
            "allowed_actions": [a.value for a in req.allowed_actions] if req.allowed_actions else None,
            "rules": req.rules.model_dump(),
        },
        correct=None,
        ev_loss=None,
        decision=decision,
        explanation=explanation,
    )
