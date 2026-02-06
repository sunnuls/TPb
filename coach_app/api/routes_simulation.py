"""
API routes for multi-agent simulation research.

Educational Use Only: These endpoints are designed for game theory research
and educational simulations in controlled virtual environments.

Endpoints:
- POST /sim/decide - Generate decision for simulation agent
- POST /sim/equity - Calculate equity for research scenarios

NOT intended for real-money gambling or production use.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position
from sim_engine.decision import (
    AgentContext,
    LineType,
    SimulatedActionType,
    generate_simulated_decision,
)

router = APIRouter(prefix="/sim", tags=["simulation"])


class OpponentModel(BaseModel):
    """Opponent behavioral model for simulations."""
    name: str = Field(..., min_length=1, max_length=50)
    vpip: float = Field(0.25, ge=0.0, le=1.0, description="Voluntarily put $ in pot %")
    pfr: float = Field(0.20, ge=0.0, le=1.0, description="Preflop raise %")
    aggression_factor: float = Field(2.0, ge=0.0, le=10.0, description="Aggression factor")
    fold_to_cbet: float = Field(0.5, ge=0.0, le=1.0, description="Fold to continuation bet %")


class SimDecideRequest(BaseModel):
    """
    Request for simulation decision endpoint.
    
    Educational Note:
        This request format enables systematic testing of multi-agent
        decision-making algorithms in controlled research environments.
    """
    agent_id: str = Field(..., min_length=1, description="Unique agent identifier")
    agent_state: list[str] = Field(..., min_items=2, max_items=2, description="Agent's hole cards")
    environment: list[str] = Field(..., min_items=0, max_items=5, description="Community cards (board)")
    street: Street = Field(..., description="Current street")
    pot_bb: float = Field(..., ge=0.0, description="Pot size in big blinds")
    to_call_bb: float = Field(0.0, ge=0.0, description="Amount to call in BB")
    
    # Context
    position: Position = Field(..., description="Agent's position")
    resource_bucket: str = Field("medium", pattern="^(low|medium|high)$", description="Resource level")
    opponent_models: list[OpponentModel] = Field(default_factory=list)
    session_state: dict = Field(default_factory=dict)
    
    # Simulation parameters
    use_monte_carlo: bool = Field(True, description="Enable Monte Carlo equity calculation")
    num_simulations: int = Field(1000, ge=10, le=10000, description="Number of MC simulations")
    probability_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Proactive threshold")
    
    @validator('agent_state')
    def validate_cards(cls, v):
        """Validate card format."""
        valid_ranks = "23456789TJQKA"
        valid_suits = "shdc"
        
        for card in v:
            if len(card) != 2:
                raise ValueError(f"Invalid card format: {card}")
            if card[0] not in valid_ranks or card[1] not in valid_suits:
                raise ValueError(f"Invalid card: {card}")
        
        if v[0] == v[1]:
            raise ValueError("Duplicate cards in hand")
        
        return v
    
    @validator('environment')
    def validate_board(cls, v, values):
        """Validate board cards."""
        if 'street' not in values:
            return v
        
        street = values['street']
        expected_lengths = {
            Street.preflop: 0,
            Street.flop: 3,
            Street.turn: 4,
            Street.river: 5
        }
        
        if len(v) != expected_lengths[street]:
            raise ValueError(
                f"Board length {len(v)} doesn't match street {street.value}. "
                f"Expected {expected_lengths[street]}"
            )
        
        # Validate card format
        valid_ranks = "23456789TJQKA"
        valid_suits = "shdc"
        
        for card in v:
            if len(card) != 2:
                raise ValueError(f"Invalid card format: {card}")
            if card[0] not in valid_ranks or card[1] not in valid_suits:
                raise ValueError(f"Invalid card: {card}")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Board contains duplicate cards")
        
        return v
    
    @validator('environment')
    def validate_no_overlap_with_agent_state(cls, v, values):
        """Ensure no card appears in both agent_state and environment."""
        if 'agent_state' not in values:
            return v
        
        agent_cards = set(values['agent_state'])
        board_cards = set(v)
        
        overlap = agent_cards & board_cards
        if overlap:
            raise ValueError(f"Cards appear in both hand and board: {overlap}")
        
        return v


class SimDecideResponse(BaseModel):
    """Response from simulation decision endpoint."""
    agent_id: str
    action: SimulatedActionType
    sizing_bb: float | None
    confidence: float
    equity: float
    line_type: LineType
    reasoning: dict
    
    # Educational metadata
    educational_note: str = Field(
        default="This decision is generated for game theory research and educational "
                "simulations in controlled virtual environments. Not for real-money use."
    )


@router.post("/decide", response_model=SimDecideResponse)
def simulation_decide(req: SimDecideRequest) -> SimDecideResponse:
    """
    Generate decision for multi-agent simulation.
    
    This endpoint provides decision-making capabilities for educational
    simulations of strategic interactions in game theory research.
    
    Educational Use Only:
        This endpoint is designed for controlled virtual environments and
        academic research. All decisions are generated using deterministic
        heuristics (Range Model v0, Postflop Line Logic v2) combined with
        probabilistic modeling (Monte Carlo) for educational purposes.
        
        NOT intended for:
        - Real-money gambling or wagering
        - Production gaming applications
        - Gaining unfair advantage in competitive play
    
    Example:
        ```bash
        curl -X POST "http://localhost:8000/sim/decide" \\
          -H "Content-Type: application/json" \\
          -d '{
            "agent_id": "agent_001",
            "agent_state": ["Ah", "Ks"],
            "environment": ["Ad", "7c", "2s"],
            "street": "flop",
            "pot_bb": 12.0,
            "to_call_bb": 0.0,
            "position": "BTN",
            "resource_bucket": "high"
          }'
        ```
    """
    try:
        # Build context
        opponent_models_dict = {
            model.name: {
                "vpip": model.vpip,
                "pfr": model.pfr,
                "aggression_factor": model.aggression_factor,
                "fold_to_cbet": model.fold_to_cbet
            }
            for model in req.opponent_models
        }
        
        context = AgentContext(
            position=req.position,
            resource_bucket=req.resource_bucket,
            opponent_models=opponent_models_dict,
            session_state=req.session_state
        )
        
        # Generate decision
        decision = generate_simulated_decision(
            agent_state=req.agent_state,
            environment=req.environment,
            street=req.street,
            pot_bb=req.pot_bb,
            to_call_bb=req.to_call_bb,
            context=context,
            use_monte_carlo=req.use_monte_carlo,
            num_simulations=req.num_simulations,
            probability_threshold=req.probability_threshold
        )
        
        return SimDecideResponse(
            agent_id=req.agent_id,
            action=decision.action,
            sizing_bb=decision.sizing,
            confidence=decision.confidence,
            equity=decision.equity,
            line_type=decision.line_type,
            reasoning=decision.reasoning
        )
    
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision generation failed: {str(e)}")


class SimEquityRequest(BaseModel):
    """Request for equity calculation in simulations."""
    hero_hand: list[str] = Field(..., min_items=2, max_items=2)
    villain_hand: list[str] | None = Field(None, min_items=2, max_items=2)
    board: list[str] = Field(..., min_items=0, max_items=5)
    num_simulations: int = Field(1000, ge=10, le=10000)


class SimEquityResponse(BaseModel):
    """Response from equity calculation endpoint."""
    equity: float
    win_count: int
    tie_count: int
    lose_count: int
    total_simulations: int
    confidence: float
    
    educational_note: str = Field(
        default="Educational simulation only. Not for real-money applications."
    )


@router.post("/equity", response_model=SimEquityResponse)
def simulation_equity(req: SimEquityRequest) -> SimEquityResponse:
    """
    Calculate equity for simulation research scenarios.
    
    Educational Use Only:
        Provides Monte Carlo equity calculations for game theory research.
        Uses deterministic heuristics for educational purposes.
    
    Example:
        ```bash
        curl -X POST "http://localhost:8000/sim/equity" \\
          -H "Content-Type: application/json" \\
          -d '{
            "hero_hand": ["Ah", "Kh"],
            "villain_hand": ["Qd", "Jd"],
            "board": ["Kc", "7h", "2s"],
            "num_simulations": 1000
          }'
        ```
    """
    try:
        from coach_app.engine import calculate_equity_vs_specific_hand, calculate_monte_carlo_equity, Range
        
        if req.villain_hand:
            # Specific matchup
            result = calculate_equity_vs_specific_hand(
                hero_hand=req.hero_hand,
                opponent_hand=req.villain_hand,
                board=req.board,
                num_simulations=req.num_simulations
            )
        else:
            # vs generic range
            default_range = Range(hands={
                "AA": 1.0, "KK": 1.0, "QQ": 1.0,
                "AKs": 0.95, "AKo": 0.85
            })
            
            result = calculate_monte_carlo_equity(
                hero_hand=req.hero_hand,
                opponent_range=default_range,
                board=req.board,
                num_simulations=req.num_simulations
            )
        
        return SimEquityResponse(
            equity=result.equity,
            win_count=result.win_count,
            tie_count=result.tie_count,
            lose_count=result.lose_count,
            total_simulations=result.total_simulations,
            confidence=result.confidence
        )
    
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Equity calculation failed: {str(e)}")
