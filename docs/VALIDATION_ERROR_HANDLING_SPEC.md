# Input Validation and Error Handling Specification
## Multi-Agent Simulation Framework - Error Minimization Strategy

**Version:** 1.0  
**Date:** 2026-02-05  
**Parent Document:** SIMULATION_SPEC.md  
**Purpose:** Comprehensive error prevention, detection, and recovery strategies

---

## Table of Contents

1. [Overview](#1-overview)
2. [Input Validation Strategy](#2-input-validation-strategy)
3. [Component-Level Error Handling](#3-component-level-error-handling)
4. [Unit Test Specifications](#4-unit-test-specifications)
5. [Integration Test Requirements](#5-integration-test-requirements)
6. [Error Recovery Mechanisms](#6-error-recovery-mechanisms)
7. [Monitoring and Alerting](#7-monitoring-and-alerting)

---

## 1. Overview

### 1.1 Error Minimization Principles

1. **Fail Early, Fail Loudly:** Detect errors at input boundaries
2. **Type Safety:** Use Python type hints + mypy validation
3. **Contract-Based Programming:** Validate preconditions/postconditions
4. **Graceful Degradation:** Fallback strategies for non-critical failures
5. **Observable Failures:** Comprehensive logging and metrics

### 1.2 Error Categories

| Category | Severity | Response Strategy |
|----------|----------|-------------------|
| **Input Validation** | Medium | Reject with clear error message |
| **State Inconsistency** | High | Force re-sync from canonical source |
| **Network Failure** | Medium | Retry with exponential backoff |
| **Decision Logic Error** | Critical | Log + fallback to conservative default |
| **Vision Extraction Failure** | Medium | Trigger fallback model chain |
| **Concurrency Conflict** | Low | Resolve via conflict resolution protocol |

---

## 2. Input Validation Strategy

### 2.1 Agent Configuration Validation

**Input:** `AgentProfile`

```python
from pydantic import BaseModel, Field, validator

class AgentProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    variance_model: str = Field(..., regex="^(conservative|aggressive|adaptive)$")
    decision_threshold: float = Field(..., ge=0.0, le=1.0)
    timing_variance_s: tuple[float, float] = Field(...)
    action_randomness: float = Field(..., ge=0.0, le=1.0)
    session_duration_minutes: int = Field(..., ge=1, le=240)
    
    @validator('timing_variance_s')
    def validate_timing_range(cls, v):
        if v[0] < 0 or v[1] < 0:
            raise ValueError("Timing values must be non-negative")
        if v[0] >= v[1]:
            raise ValueError("Min timing must be less than max timing")
        if v[1] > 10.0:
            raise ValueError("Max timing cannot exceed 10 seconds (unrealistic)")
        return v
    
    @validator('session_duration_minutes')
    def validate_session_duration(cls, v):
        if v > 240:
            raise ValueError("Session duration cannot exceed 4 hours (safety limit)")
        return v

# Usage
try:
    profile = AgentProfile(
        name="test_agent",
        variance_model="conservative",
        decision_threshold=0.8,
        timing_variance_s=(0.5, 1.5),
        action_randomness=0.1,
        session_duration_minutes=60
    )
except ValidationError as e:
    logging.error(f"Invalid agent profile: {e}")
    # Return detailed error to user
```

**Validation Rules:**
- ✅ `name`: Alphanumeric + underscores/hyphens, 1-50 chars
- ✅ `variance_model`: Must be one of ["conservative", "aggressive", "adaptive"]
- ✅ `decision_threshold`: Must be in [0.0, 1.0]
- ✅ `timing_variance_s`: Min < Max, both positive, max ≤ 10s
- ✅ `action_randomness`: Must be in [0.0, 1.0]
- ✅ `session_duration_minutes`: Must be in [1, 240] (4 hour limit)

### 2.2 Game State Validation

**Input:** `TableState`

```python
from coach_app.schemas.common import Street
from coach_app.schemas.poker import Position

class TableState(BaseModel):
    table_id: str = Field(..., min_length=1, max_length=100)
    timestamp: float = Field(..., gt=0)
    street: Street
    board: list[str] = Field(..., min_items=0, max_items=5)
    pot_bb: float = Field(..., ge=0.0)
    players: list[PlayerState] = Field(..., min_items=2, max_items=9)
    active_seat: int = Field(..., ge=0, le=8)
    version: int = Field(..., ge=0)
    
    @validator('board')
    def validate_board(cls, v, values):
        """Validate board cards based on street."""
        street = values.get('street')
        
        if street == Street.preflop and len(v) != 0:
            raise ValueError("Preflop must have 0 board cards")
        elif street == Street.flop and len(v) != 3:
            raise ValueError("Flop must have exactly 3 board cards")
        elif street == Street.turn and len(v) != 4:
            raise ValueError("Turn must have exactly 4 board cards")
        elif street == Street.river and len(v) != 5:
            raise ValueError("River must have exactly 5 board cards")
        
        # Validate card format: Rank + Suit (e.g., "Ah", "Ks")
        valid_ranks = "23456789TJQKA"
        valid_suits = "shdc"
        
        for card in v:
            if len(card) != 2:
                raise ValueError(f"Invalid card format: {card}. Must be 2 chars (rank+suit)")
            if card[0] not in valid_ranks:
                raise ValueError(f"Invalid rank: {card[0]}")
            if card[1] not in valid_suits:
                raise ValueError(f"Invalid suit: {card[1]}")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Board contains duplicate cards")
        
        return v
    
    @validator('pot_bb')
    def validate_pot(cls, v):
        if v < 0:
            raise ValueError("Pot cannot be negative")
        if v > 10000:
            raise ValueError("Pot suspiciously large (>10000 BB). Possible error.")
        return v
    
    @validator('active_seat')
    def validate_active_seat(cls, v, values):
        """Active seat must correspond to an actual player."""
        players = values.get('players', [])
        if not any(p.seat == v for p in players):
            raise ValueError(f"Active seat {v} not found in player list")
        return v

class PlayerState(BaseModel):
    seat: int = Field(..., ge=0, le=8)
    name: str = Field(..., min_length=1, max_length=50)
    stack_bb: float = Field(..., ge=0.0)
    position: Position
    hole_cards: list[str] | None = Field(None, min_items=2, max_items=2)
    is_active: bool
    
    @validator('hole_cards')
    def validate_hole_cards(cls, v):
        if v is None:
            return v
        
        if len(v) != 2:
            raise ValueError("Hole cards must be exactly 2 cards")
        
        # Same validation as board cards
        valid_ranks = "23456789TJQKA"
        valid_suits = "shdc"
        
        for card in v:
            if len(card) != 2:
                raise ValueError(f"Invalid card format: {card}")
            if card[0] not in valid_ranks or card[1] not in valid_suits:
                raise ValueError(f"Invalid card: {card}")
        
        if v[0] == v[1]:
            raise ValueError("Hole cards cannot be identical")
        
        return v
```

**Validation Rules:**
- ✅ `table_id`: Non-empty string
- ✅ `timestamp`: Positive float (Unix timestamp)
- ✅ `street`: Valid Street enum
- ✅ `board`: Length matches street (0/3/4/5), valid card format, no duplicates
- ✅ `pot_bb`: Non-negative, sanity check < 10000 BB
- ✅ `players`: 2-9 players (poker standard)
- ✅ `active_seat`: Must match a player's seat
- ✅ `hole_cards`: Exactly 2 cards, valid format, no duplicates

### 2.3 Action Validation

**Input:** `ActionRequest`

```python
class ActionRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    table_id: str = Field(..., min_length=1)
    action: PokerActionType
    sizing_bb: float | None = Field(None, ge=0.0)
    timestamp: float = Field(..., gt=0)
    seat_position: int = Field(..., ge=0, le=8)
    
    @validator('sizing_bb')
    def validate_sizing(cls, v, values):
        """Validate bet/raise sizing."""
        action = values.get('action')
        
        if action in [PokerActionType.bet, PokerActionType.raise_]:
            if v is None:
                raise ValueError(f"{action.value} requires sizing_bb")
            if v <= 0:
                raise ValueError("Sizing must be positive")
        
        if action in [PokerActionType.fold, PokerActionType.check]:
            if v is not None and v != 0:
                raise ValueError(f"{action.value} should not have sizing")
        
        return v
    
    class Config:
        use_enum_values = True

# Usage with context validation
def validate_action_in_context(
    action_request: ActionRequest,
    table_state: TableState
) -> None:
    """Validate action is legal given current table state."""
    
    # Check it's the agent's turn
    if action_request.seat_position != table_state.active_seat:
        raise ValueError(f"Not your turn. Active seat: {table_state.active_seat}")
    
    # Find player state
    player = next(
        (p for p in table_state.players if p.seat == action_request.seat_position),
        None
    )
    
    if not player:
        raise ValueError("Player not found at table")
    
    # Check stack size
    if action_request.sizing_bb and action_request.sizing_bb > player.stack_bb:
        raise ValueError(f"Sizing ({action_request.sizing_bb} BB) exceeds stack ({player.stack_bb} BB)")
    
    # Check action is legal (e.g., can't check if facing bet)
    # ... additional context-based validation
```

### 2.4 Vision Input Validation

**Input:** Screenshot + ROI

```python
import numpy as np

def validate_screenshot(screenshot: np.ndarray) -> None:
    """Validate screenshot image data."""
    
    if not isinstance(screenshot, np.ndarray):
        raise TypeError(f"Screenshot must be numpy array, got {type(screenshot)}")
    
    if screenshot.ndim != 3:
        raise ValueError(f"Screenshot must be 3D (H, W, C), got shape {screenshot.shape}")
    
    height, width, channels = screenshot.shape
    
    if channels not in [3, 4]:  # RGB or RGBA
        raise ValueError(f"Screenshot must have 3 or 4 channels, got {channels}")
    
    if height < 480 or width < 640:
        raise ValueError(f"Screenshot too small: {width}x{height}. Min: 640x480")
    
    if height > 4320 or width > 7680:  # 8K max
        raise ValueError(f"Screenshot too large: {width}x{height}. Max: 7680x4320")
    
    # Check dtype
    if screenshot.dtype not in [np.uint8, np.float32]:
        raise TypeError(f"Screenshot dtype must be uint8 or float32, got {screenshot.dtype}")

def validate_roi(roi: dict, screenshot_shape: tuple) -> None:
    """Validate region of interest bounds."""
    
    required_fields = ["x", "y", "width", "height"]
    for field in required_fields:
        if field not in roi:
            raise ValueError(f"ROI missing required field: {field}")
    
    x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
    img_h, img_w = screenshot_shape[:2]
    
    # Check bounds
    if x < 0 or y < 0:
        raise ValueError(f"ROI coordinates cannot be negative: ({x}, {y})")
    
    if w <= 0 or h <= 0:
        raise ValueError(f"ROI dimensions must be positive: {w}x{h}")
    
    if x + w > img_w or y + h > img_h:
        raise ValueError(
            f"ROI out of bounds: ({x}, {y}, {w}, {h}) exceeds image {img_w}x{img_h}"
        )
    
    # Sanity checks
    if w < 10 or h < 10:
        raise ValueError(f"ROI too small: {w}x{h}. Minimum 10x10 pixels")
    
    if w > img_w * 0.9 or h > img_h * 0.9:
        raise ValueError(f"ROI suspiciously large: {w}x{h} (>90% of image)")
```

---

## 3. Component-Level Error Handling

### 3.1 Central Hub Error Handling

```python
import asyncio
import logging
from typing import Any

class CentralHub:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
        self.error_counts: dict[str, int] = {}
        self.max_errors_per_agent = 10
    
    async def handle_message(self, ws: WebSocket, message: str):
        """Main message handler with comprehensive error handling."""
        
        agent_id = None
        
        try:
            # Parse JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                await self.send_error(ws, "invalid_json", str(e))
                return
            
            # Validate message structure
            if "type" not in data:
                await self.send_error(ws, "missing_field", "Message must have 'type' field")
                return
            
            if "agent_id" not in data:
                await self.send_error(ws, "missing_field", "Message must have 'agent_id' field")
                return
            
            agent_id = data["agent_id"]
            
            # Check error rate
            if self.error_counts.get(agent_id, 0) >= self.max_errors_per_agent:
                await self.send_error(ws, "rate_limit", "Too many errors. Connection blocked.")
                await ws.close()
                return
            
            # Route message
            msg_type = data["type"]
            
            if msg_type == "sync_request":
                await self.handle_sync_request(ws, data)
            elif msg_type == "action_request":
                await self.handle_action_request(ws, data)
            elif msg_type == "subscribe":
                await self.handle_subscribe(ws, data)
            else:
                await self.send_error(ws, "unknown_type", f"Unknown message type: {msg_type}")
        
        except ValidationError as e:
            # Pydantic validation error
            await self.send_error(ws, "validation_error", str(e))
            if agent_id:
                self.error_counts[agent_id] = self.error_counts.get(agent_id, 0) + 1
        
        except StateConflictError as e:
            # Expected error: state mismatch
            await self.send_error(ws, "state_conflict", str(e))
            logging.warning(f"State conflict for {agent_id}: {e}")
        
        except asyncio.TimeoutError:
            # Redis or network timeout
            await self.send_error(ws, "timeout", "Operation timed out")
            logging.error(f"Timeout handling message from {agent_id}")
        
        except Exception as e:
            # Unexpected error
            logging.exception(f"Unexpected error handling message from {agent_id}")
            await self.send_error(ws, "internal_error", "Internal server error")
            
            # Increment error count
            if agent_id:
                self.error_counts[agent_id] = self.error_counts.get(agent_id, 0) + 1
    
    async def send_error(self, ws: WebSocket, error_code: str, message: str):
        """Send formatted error message to client."""
        error_msg = {
            "type": "error",
            "error_code": error_code,
            "message": message,
            "timestamp": time.time()
        }
        
        try:
            await ws.send(json.dumps(error_msg))
        except Exception as e:
            logging.error(f"Failed to send error message: {e}")

class StateConflictError(Exception):
    """Raised when state synchronization fails due to conflicts."""
    pass
```

### 3.2 Decision Engine Error Handling

```python
class DecisionEngine:
    def __init__(self):
        self.fallback_enabled = True
        self.error_metrics = {}
    
    def calculate_decision(
        self,
        state: TableState,
        agent_profile: AgentProfile
    ) -> SimulationDecision:
        """Calculate decision with error handling and fallback."""
        
        try:
            # Validate input state
            self._validate_decision_input(state)
            
            # Primary decision path
            if state.street == Street.preflop:
                decision = self._decide_preflop(state, agent_profile)
            else:
                decision = self._decide_postflop(state, agent_profile)
            
            # Validate output
            self._validate_decision_output(decision, state)
            
            return decision
        
        except ValidationError as e:
            logging.error(f"Validation error in decision engine: {e}")
            self.error_metrics["validation_errors"] = self.error_metrics.get("validation_errors", 0) + 1
            
            if self.fallback_enabled:
                return self._fallback_decision(state, reason=f"validation_error: {e}")
            raise
        
        except ZeroDivisionError as e:
            logging.error(f"Math error in equity calculation: {e}")
            self.error_metrics["math_errors"] = self.error_metrics.get("math_errors", 0) + 1
            
            if self.fallback_enabled:
                return self._fallback_decision(state, reason=f"math_error: {e}")
            raise
        
        except Exception as e:
            logging.exception(f"Unexpected error in decision engine")
            self.error_metrics["unexpected_errors"] = self.error_metrics.get("unexpected_errors", 0) + 1
            
            if self.fallback_enabled:
                return self._fallback_decision(state, reason=f"unexpected_error: {type(e).__name__}")
            raise
    
    def _validate_decision_input(self, state: TableState) -> None:
        """Validate decision input state."""
        
        # Check required fields
        if not state.players:
            raise ValidationError("No players in state")
        
        # Find hero
        hero = next((p for p in state.players if p.hole_cards is not None), None)
        if not hero:
            raise ValidationError("No hero with hole cards found")
        
        # Check hero has cards
        if not hero.hole_cards or len(hero.hole_cards) != 2:
            raise ValidationError(f"Invalid hero hole cards: {hero.hole_cards}")
        
        # Check board matches street
        expected_board_len = {
            Street.preflop: 0,
            Street.flop: 3,
            Street.turn: 4,
            Street.river: 5
        }
        
        if len(state.board) != expected_board_len[state.street]:
            raise ValidationError(
                f"Board length {len(state.board)} doesn't match street {state.street.value}"
            )
    
    def _validate_decision_output(self, decision: SimulationDecision, state: TableState) -> None:
        """Validate decision output."""
        
        # Check confidence is in valid range
        if not 0.0 <= decision.confidence <= 1.0:
            raise ValidationError(f"Invalid confidence: {decision.confidence}")
        
        # Check equity is in valid range
        if not 0.0 <= decision.equity <= 1.0:
            raise ValidationError(f"Invalid equity: {decision.equity}")
        
        # Check sizing for bet/raise
        if decision.action in [PokerActionType.bet, PokerActionType.raise_]:
            if decision.sizing_bb is None or decision.sizing_bb <= 0:
                raise ValidationError(f"Invalid sizing for {decision.action.value}: {decision.sizing_bb}")
            
            # Check sizing doesn't exceed pot by too much
            if decision.sizing_bb > state.pot_bb * 10:
                raise ValidationError(f"Sizing suspiciously large: {decision.sizing_bb} BB (pot: {state.pot_bb} BB)")
    
    def _fallback_decision(self, state: TableState, reason: str) -> SimulationDecision:
        """Return conservative fallback decision when primary logic fails."""
        
        logging.warning(f"Using fallback decision. Reason: {reason}")
        
        # Conservative default: check/fold
        # If facing bet, fold
        # Otherwise, check
        
        # Simplified: just check
        return SimulationDecision(
            action=PokerActionType.check,
            sizing_bb=None,
            confidence=0.3,  # Low confidence for fallback
            equity=0.5,  # Neutral equity
            ev_bb=0.0,
            reasoning={
                "fallback": True,
                "reason": reason,
                "note": "Conservative default due to error in primary decision logic"
            },
            alternatives=[]
        )
```

### 3.3 Vision Adapter Error Handling

```python
class VisionAdapter:
    def __init__(self):
        self.fallback_chain = [
            ("primary_yolo", self._yolo_primary),
            ("secondary_yolo", self._yolo_secondary),
            ("template_matching", self._template_matching),
        ]
        self.min_confidence = 0.6
    
    async def extract_state(
        self,
        screenshot: np.ndarray,
        table_id: str
    ) -> tuple[TableState, float]:
        """Extract state with fallback chain."""
        
        try:
            # Validate input
            validate_screenshot(screenshot)
        except (TypeError, ValueError) as e:
            logging.error(f"Invalid screenshot: {e}")
            raise VisionExtractionError(f"Screenshot validation failed: {e}")
        
        # Try each model in fallback chain
        for model_name, model_func in self.fallback_chain:
            try:
                state, confidence = await model_func(screenshot, table_id)
                
                if confidence >= self.min_confidence:
                    logging.info(f"Vision extraction succeeded with {model_name} (conf: {confidence:.2f})")
                    return state, confidence
                else:
                    logging.warning(
                        f"{model_name} confidence too low ({confidence:.2f}), trying next model..."
                    )
            
            except VisionModelError as e:
                logging.error(f"{model_name} failed: {e}. Trying next model...")
                continue
            
            except Exception as e:
                logging.exception(f"Unexpected error in {model_name}")
                continue
        
        # All models failed
        raise VisionExtractionError(
            f"All vision models failed for table {table_id}. "
            f"Tried: {[name for name, _ in self.fallback_chain]}"
        )
    
    async def _yolo_primary(self, screenshot: np.ndarray, table_id: str) -> tuple[TableState, float]:
        """Primary YOLO-based extraction."""
        
        try:
            # ROI detection
            rois = await self.detect_rois(screenshot, table_id)
            
            if not rois or len(rois) < 3:  # Need at least hero, board, pot
                raise VisionModelError("Insufficient ROIs detected")
            
            # Extract components
            hero_cards, hero_conf = await self._extract_cards(screenshot, rois.get("hero_cards"))
            board, board_conf = await self._extract_cards(screenshot, rois.get("board"))
            pot, pot_conf = await self._extract_number(screenshot, rois.get("pot"))
            
            # Build state
            state = TableState(
                table_id=table_id,
                timestamp=time.time(),
                street=self._infer_street(board),
                board=board,
                pot_bb=pot,
                players=[],  # Simplified
                active_seat=0,
                version=0
            )
            
            # Aggregate confidence
            avg_confidence = (hero_conf + board_conf + pot_conf) / 3
            
            return state, avg_confidence
        
        except Exception as e:
            raise VisionModelError(f"Primary YOLO failed: {e}")

class VisionExtractionError(Exception):
    """Raised when vision extraction fails completely."""
    pass

class VisionModelError(Exception):
    """Raised when a specific vision model fails."""
    pass
```

---

## 4. Unit Test Specifications

### 4.1 Test Coverage Requirements

**Component-Level Coverage Targets:**

| Component | Target Coverage | Critical Paths | Edge Cases |
|-----------|----------------|----------------|------------|
| Range Model v0 | 95% | normalize, merge, contains | Empty ranges, invalid weights |
| Postflop Logic v2 | 90% | hand categorization, line selection | Edge board textures, stack depths |
| Preflop Heuristics | 90% | RFI ranges, 3bet/defend | All positions, stack buckets |
| Central Hub | 85% | State sync, conflict resolution | Network failures, race conditions |
| Decision Engine | 90% | Decision calculation, equity | Invalid states, edge equities |
| Vision Adapter | 75% | ROI detection, extraction | Low quality images, partial occlusion |
| Variance Models | 80% | Timing, action randomness | Statistical properties |
| Orchestrator | 80% | Agent lifecycle, deployment | Health checks, restarts |

### 4.2 Range Model v0 Tests

```python
# tests/unit/test_range_model.py

import pytest
from coach_app.engine.poker.ranges.range import Range

class TestRangeModel:
    """Unit tests for Range Model v0."""
    
    def test_range_initialization(self):
        """Test basic range creation."""
        r = Range(hands={"AA": 1.0, "KK": 0.9, "22": 0.5})
        assert r.hands["AA"] == 1.0
        assert r.hands["KK"] == 0.9
    
    def test_range_normalization(self):
        """Test normalization clamps weights and removes zeros."""
        r = Range(hands={"AA": 1.5, "KK": -0.1, "QQ": 0.0, "JJ": 0.5})
        normalized = r.normalize()
        
        assert normalized.hands["AA"] == 1.0  # Clamped to 1.0
        assert "KK" not in normalized.hands  # Negative removed
        assert "QQ" not in normalized.hands  # Zero removed
        assert normalized.hands["JJ"] == 0.5
    
    def test_range_merge(self):
        """Test range merging adds weights."""
        r1 = Range(hands={"AA": 0.8, "KK": 0.5})
        r2 = Range(hands={"KK": 0.3, "QQ": 0.6})
        merged = r1.merge(r2)
        
        assert merged.hands["AA"] == 0.8
        assert merged.hands["KK"] == 0.8  # 0.5 + 0.3
        assert merged.hands["QQ"] == 0.6
    
    def test_range_merge_clamps_to_one(self):
        """Test merge doesn't exceed 1.0 weight."""
        r1 = Range(hands={"AA": 0.9})
        r2 = Range(hands={"AA": 0.5})
        merged = r1.merge(r2)
        
        assert merged.hands["AA"] == 1.0  # Clamped
    
    def test_range_contains(self):
        """Test hand membership check."""
        r = Range(hands={"AA": 1.0, "KK": 0.5, "22": 0.0})
        normalized = r.normalize()
        
        assert normalized.contains("AA")
        assert normalized.contains("KK")
        assert not normalized.contains("22")  # Zero weight removed
        assert not normalized.contains("AKs")  # Not in range
    
    def test_range_weight(self):
        """Test weight retrieval."""
        r = Range(hands={"AA": 0.8, "KK": 0.5})
        
        assert r.weight("AA") == 0.8
        assert r.weight("KK") == 0.5
        assert r.weight("QQ") == 0.0  # Not in range
    
    def test_range_describe(self):
        """Test human-readable description."""
        r = Range(
            hands={"AA": 1.0, "KK": 0.9, "QQ": 0.8},
            metadata={"position": "BTN", "action": "RFI"}
        )
        desc = r.describe(limit=3)
        
        assert "AA(100%)" in desc
        assert "KK(90%)" in desc
        assert "QQ(80%)" in desc
        assert "position=BTN" in desc
        assert "action=RFI" in desc
    
    def test_empty_range(self):
        """Test empty range handling."""
        r = Range(hands={})
        normalized = r.normalize()
        
        assert len(normalized.hands) == 0
        assert not normalized.contains("AA")
        assert normalized.weight("AA") == 0.0
    
    def test_invalid_weight_types(self):
        """Test that invalid weight types raise errors."""
        with pytest.raises((TypeError, ValueError)):
            Range(hands={"AA": "high"})  # String instead of float
    
    @pytest.mark.parametrize("hand,weight", [
        ("AA", 1.0),
        ("AKs", 0.95),
        ("AKo", 0.85),
        ("72o", 0.0),
    ])
    def test_range_parametrized(self, hand, weight):
        """Parametrized test for various hands."""
        r = Range(hands={hand: weight})
        normalized = r.normalize()
        
        if weight > 0:
            assert normalized.contains(hand)
            assert normalized.weight(hand) == weight
        else:
            assert not normalized.contains(hand)
```

### 4.3 Decision Engine Tests

```python
# tests/unit/test_decision_engine.py

import pytest
from unittest.mock import Mock, patch
from coach_app.engine.poker.analyze import analyze_poker_state
from coach_app.schemas.poker import PokerGameState, PokerActionType

class TestDecisionEngine:
    """Unit tests for Decision Engine."""
    
    def test_preflop_premium_hand(self):
        """Test decision for premium hand (AA) on BTN."""
        state = PokerGameState(
            street="preflop",
            position="BTN",
            hero_hand=["Ah", "As"],
            board=[],
            pot_bb=1.5,
            to_call=0.0,
            effective_stack_bb=100.0,
            action_facing="unopened"
        )
        
        decision = analyze_poker_state(state)
        
        assert decision.action == PokerActionType.raise_
        assert decision.sizing_bb >= 2.5  # Standard RFI
        assert decision.confidence >= 0.9  # High confidence for AA
    
    def test_preflop_weak_hand(self):
        """Test decision for weak hand (72o) in early position."""
        state = PokerGameState(
            street="preflop",
            position="UTG",
            hero_hand=["7h", "2c"],
            board=[],
            pot_bb=1.5,
            to_call=0.0,
            effective_stack_bb=100.0,
            action_facing="unopened"
        )
        
        decision = analyze_poker_state(state)
        
        assert decision.action == PokerActionType.fold
        assert decision.confidence >= 0.85
    
    def test_postflop_top_pair(self):
        """Test decision with top pair top kicker."""
        state = PokerGameState(
            street="flop",
            position="IP",
            hero_hand=["Ah", "Ks"],
            board=["Ad", "7c", "2s"],
            pot_bb=12.0,
            to_call=0.0,
            effective_stack_bb=95.0,
            action_facing="check"
        )
        
        decision = analyze_poker_state(state)
        
        # Should bet for value
        assert decision.action in [PokerActionType.bet, PokerActionType.raise_]
        assert decision.sizing_bb is not None
        assert decision.sizing_bb > 0
        assert decision.confidence >= 0.7
    
    def test_postflop_flush_draw_pot_odds(self):
        """Test pot odds calculation for flush draw."""
        state = PokerGameState(
            street="flop",
            position="OOP",
            hero_hand=["Kh", "Qh"],
            board=["Ah", "7h", "2c"],
            pot_bb=12.0,
            to_call=4.0,  # 4:16 pot odds = 25%
            effective_stack_bb=90.0,
            action_facing="bet"
        )
        
        decision = analyze_poker_state(state)
        
        # Flush draw ~35% equity, pot odds 25% -> should call
        assert decision.action == PokerActionType.call
        assert decision.confidence >= 0.6
    
    def test_invalid_state_missing_cards(self):
        """Test error handling for invalid state."""
        state = PokerGameState(
            street="flop",
            position="BTN",
            hero_hand=[],  # Missing cards
            board=["Ah", "7c", "2s"],
            pot_bb=12.0,
            to_call=0.0,
            effective_stack_bb=100.0,
            action_facing="check"
        )
        
        with pytest.raises(ValidationError):
            analyze_poker_state(state)
    
    def test_fallback_decision_on_error(self):
        """Test fallback decision when primary logic fails."""
        engine = DecisionEngine()
        engine.fallback_enabled = True
        
        # Create intentionally broken state
        state = Mock()
        state.street = None  # This will cause error
        
        decision = engine.calculate_decision(state, AgentProfile())
        
        # Should get fallback decision
        assert decision.action == PokerActionType.check
        assert decision.confidence < 0.5  # Low confidence for fallback
        assert decision.reasoning.get("fallback") == True
    
    @pytest.mark.parametrize("equity,pot_odds,expected", [
        (0.60, 0.25, PokerActionType.call),  # Good pot odds
        (0.20, 0.40, PokerActionType.fold),  # Bad pot odds
        (0.75, 0.20, PokerActionType.raise_),  # Strong hand
    ])
    def test_pot_odds_decisions(self, equity, pot_odds, expected):
        """Parametrized test for pot odds decisions."""
        # Mock equity calculator
        with patch('coach_app.engine.poker.equity.calculate_equity') as mock_equity:
            mock_equity.return_value = equity
            
            state = create_test_state(pot_bb=10.0, to_call=pot_odds * 10.0)
            decision = analyze_poker_state(state)
            
            assert decision.action == expected
```

### 4.4 State Synchronization Tests

```python
# tests/unit/test_state_sync.py

import pytest
from central_hub import CentralHub, StateConflictError
from schemas import TableState

class TestStateSynchronization:
    """Unit tests for state synchronization."""
    
    @pytest.fixture
    def hub(self):
        return CentralHub()
    
    @pytest.fixture
    def canonical_state(self):
        return TableState(
            table_id="test_001",
            timestamp=1000.0,
            street="flop",
            board=["Ah", "7c", "2s"],
            pot_bb=12.0,
            players=[],
            active_seat=0,
            version=42
        )
    
    def test_sync_matching_states(self, hub, canonical_state):
        """Test sync succeeds when states match."""
        agent_state = canonical_state.copy()
        agent_state.version = 42  # Same version
        
        merged = hub.merge_states(canonical_state, agent_state)
        
        assert merged.version == 43  # Incremented
        assert merged.pot_bb == 12.0
        assert merged.board == ["Ah", "7c", "2s"]
    
    def test_sync_conflicting_pot(self, hub, canonical_state):
        """Test conflict detected when pot differs."""
        agent_state = canonical_state.copy()
        agent_state.pot_bb = 15.0  # Different pot
        
        with pytest.raises(StateConflictError) as exc_info:
            hub.merge_states(canonical_state, agent_state)
        
        assert "Pot mismatch" in str(exc_info.value)
    
    def test_sync_conflicting_board(self, hub, canonical_state):
        """Test conflict detected when board differs."""
        agent_state = canonical_state.copy()
        agent_state.board = ["Ah", "7c", "3s"]  # Different river card
        
        with pytest.raises(StateConflictError) as exc_info:
            hub.merge_states(canonical_state, agent_state)
        
        assert "Board mismatch" in str(exc_info.value)
    
    def test_sync_version_mismatch(self, hub, canonical_state):
        """Test conflict on version mismatch."""
        agent_state = canonical_state.copy()
        agent_state.version = 40  # Old version
        
        with pytest.raises(StateConflictError) as exc_info:
            hub.merge_states(canonical_state, agent_state)
        
        assert "Version mismatch" in str(exc_info.value)
    
    def test_sync_preserves_private_data(self, hub, canonical_state):
        """Test merge preserves agent's private hole cards."""
        agent_state = canonical_state.copy()
        agent_state.players = [
            PlayerState(
                seat=0,
                name="Hero",
                stack_bb=100.0,
                position="BTN",
                hole_cards=["Ah", "Ks"],  # Private
                is_active=True
            )
        ]
        
        merged = hub.merge_states(canonical_state, agent_state)
        
        # Private hole cards should be preserved
        hero = next(p for p in merged.players if p.name == "Hero")
        assert hero.hole_cards == ["Ah", "Ks"]
```

### 4.5 Variance Model Tests

```python
# tests/unit/test_variance_models.py

import pytest
import numpy as np
from variance import TimingVariance, apply_action_randomness, ConservativeBehavior

class TestVarianceModels:
    """Unit tests for variance models."""
    
    def test_timing_variance_range(self):
        """Test timing delays are within specified range."""
        profile = AgentProfile(
            name="test",
            timing_variance_s=(0.5, 1.5),
            # ... other fields
        )
        
        timing = TimingVariance(profile)
        
        delays = [timing.get_action_delay("simple") for _ in range(100)]
        
        # All delays should be within bounds (with small buffer for jitter)
        assert all(0.3 <= d <= 2.0 for d in delays)
        
        # Mean should be near midpoint
        assert 0.8 <= np.mean(delays) <= 1.2
    
    def test_timing_complexity_scaling(self):
        """Test complex decisions take longer than trivial ones."""
        profile = AgentProfile(
            name="test",
            timing_variance_s=(0.5, 1.5),
            # ...
        )
        
        timing = TimingVariance(profile)
        
        trivial = [timing.get_action_delay("trivial") for _ in range(100)]
        complex_delays = [timing.get_action_delay("complex") for _ in range(100)]
        
        assert np.mean(complex_delays) > np.mean(trivial) * 1.5
    
    def test_action_randomness_distribution(self):
        """Test action randomness follows specified probability."""
        optimal = PokerActionType.raise_
        alternatives = [PokerActionType.call, PokerActionType.check]
        randomness = 0.15  # 15% suboptimal
        
        actions = [
            apply_action_randomness(optimal, randomness, alternatives)
            for _ in range(1000)
        ]
        
        suboptimal_count = sum(1 for a in actions if a != optimal)
        suboptimal_rate = suboptimal_count / len(actions)
        
        # Should be close to 15% (within 3% tolerance for randomness)
        assert 0.12 <= suboptimal_rate <= 0.18
    
    def test_conservative_behavior_folds_more(self):
        """Test conservative model folds marginal hands."""
        behavior = ConservativeBehavior()
        
        # Marginal call scenario: equity slightly above pot odds
        action = behavior.adjust_action(
            action=PokerActionType.call,
            equity=0.28,  # 28% equity
            pot_odds=0.25  # 25% pot odds (barely profitable)
        )
        
        # Conservative should fold (requires 5% buffer)
        assert action == PokerActionType.fold
    
    def test_aggressive_behavior_calls_wider(self):
        """Test aggressive model calls with worse pot odds."""
        behavior = AggressiveBehavior()
        
        # Marginal fold scenario: equity slightly below pot odds
        action = behavior.adjust_action(
            action=PokerActionType.fold,
            equity=0.28,  # 28% equity
            pot_odds=0.30  # 30% pot odds (slightly -EV)
        )
        
        # Aggressive should call (accepts 5% worse pot odds)
        assert action == PokerActionType.call
    
    @pytest.mark.parametrize("variance_model,expected_aggression", [
        ("conservative", "low"),
        ("aggressive", "high"),
        ("adaptive", "medium"),
    ])
    def test_variance_model_aggression_levels(self, variance_model, expected_aggression):
        """Parametrized test for different variance models."""
        # Test that models have appropriate aggression levels
        # ... implementation
        pass
```

---

## 5. Integration Test Requirements

### 5.1 End-to-End Pipeline Tests

```python
# tests/integration/test_simulation_pipeline.py

import pytest
import asyncio
from orchestrator import SimulationOrchestrator

@pytest.mark.asyncio
@pytest.mark.integration
class TestSimulationPipeline:
    """Integration tests for full simulation pipeline."""
    
    async def test_single_agent_full_cycle(self):
        """Test single agent from launch to action execution."""
        
        # Setup
        orchestrator = SimulationOrchestrator()
        hub = CentralHub()
        await hub.start()
        
        try:
            # Launch agent
            agent_ids = orchestrator.launch_agents(
                count=1,
                profile="research_baseline"
            )
            assert len(agent_ids) == 1
            
            agent_id = agent_ids[0]
            agent = orchestrator.get_agent(agent_id)
            
            # Connect to hub
            await agent.connect_to_hub(hub)
            assert agent.is_connected()
            
            # Provide test screenshot
            test_screenshot = load_test_image("flop_decision.png")
            
            # Extract state via vision
            state, confidence = await agent.vision_adapter.extract_state(
                test_screenshot,
                table_id="test_001"
            )
            
            assert confidence >= 0.7
            assert state.street == "flop"
            assert len(state.board) == 3
            
            # Sync state with hub
            await agent.sync_state(state)
            
            # Get decision
            decision = await agent.decision_engine.calculate_decision(
                state,
                agent.profile
            )
            
            assert decision.action in PokerActionType
            assert decision.confidence >= 0.5
            
            # Apply variance
            final_action = agent.variance_model.adjust_action(
                decision.action,
                decision.equity
            )
            
            # Execute action (mocked)
            await agent.action_executor.execute_action(
                final_action,
                decision.sizing_bb,
                state.ui_elements
            )
            
            # Verify action was broadcast to hub
            await asyncio.sleep(0.1)
            hub_state = await hub.get_state("test_001")
            assert hub_state.version > state.version
        
        finally:
            # Cleanup
            orchestrator.shutdown_gracefully()
            await hub.stop()
    
    async def test_multi_agent_coordination(self):
        """Test 2 agents coordinating at same table."""
        
        orchestrator = SimulationOrchestrator()
        hub = CentralHub()
        await hub.start()
        
        try:
            # Launch 2 agents
            agent_ids = orchestrator.launch_agents(
                count=2,
                profile="research_baseline"
            )
            
            agent1 = orchestrator.get_agent(agent_ids[0])
            agent2 = orchestrator.get_agent(agent_ids[1])
            
            # Both connect to hub
            await agent1.connect_to_hub(hub)
            await agent2.connect_to_hub(hub)
            
            # Both join same table
            table_id = "test_table_001"
            await agent1.join_table(table_id)
            await agent2.join_table(table_id)
            
            # Agent 1 syncs state
            state1 = create_test_state(
                table_id=table_id,
                pot_bb=10.0,
                board=["Ah", "7c", "2s"]
            )
            await agent1.sync_state(state1)
            
            # Agent 2 should receive state update via broadcast
            await asyncio.sleep(0.2)
            state2 = agent2.get_current_state(table_id)
            
            assert state2 is not None
            assert state2.pot_bb == 10.0
            assert state2.board == ["Ah", "7c", "2s"]
            
            # Test conflict resolution
            # Both agents try to act simultaneously
            action1 = ActionRequest(
                agent_id=agent_ids[0],
                table_id=table_id,
                action=PokerActionType.raise_,
                sizing_bb=10.0,
                timestamp=1000.0,
                seat_position=0
            )
            
            action2 = ActionRequest(
                agent_id=agent_ids[1],
                table_id=table_id,
                action=PokerActionType.call,
                sizing_bb=5.0,
                timestamp=1000.05,  # 50ms later
                seat_position=2
            )
            
            # Hub should resolve conflict
            winner = await hub.resolve_action_conflict([action1, action2])
            
            # Earlier timestamp should win
            assert winner.agent_id == agent_ids[0]
        
        finally:
            orchestrator.shutdown_gracefully()
            await hub.stop()
```

### 5.2 Performance Tests

```python
# tests/integration/test_performance.py

import pytest
import time
import asyncio

@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for simulation framework."""
    
    @pytest.mark.asyncio
    async def test_decision_latency(self):
        """Test decision engine latency under load."""
        
        engine = DecisionEngine()
        states = [create_test_state() for _ in range(100)]
        
        start = time.time()
        
        for state in states:
            decision = engine.calculate_decision(state, AgentProfile())
        
        elapsed = time.time() - start
        avg_latency = elapsed / len(states)
        
        # Decision should take < 50ms on average
        assert avg_latency < 0.05
        print(f"Average decision latency: {avg_latency*1000:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_hub_throughput(self):
        """Test hub message throughput."""
        
        hub = CentralHub()
        await hub.start()
        
        try:
            # Simulate 10 agents sending 10 messages each
            num_agents = 10
            messages_per_agent = 10
            
            async def send_messages(agent_id: str):
                ws = await hub.connect_agent(agent_id)
                for i in range(messages_per_agent):
                    message = {
                        "type": "heartbeat",
                        "agent_id": agent_id,
                        "timestamp": time.time()
                    }
                    await ws.send(json.dumps(message))
            
            start = time.time()
            
            await asyncio.gather(*[
                send_messages(f"agent_{i:03d}")
                for i in range(num_agents)
            ])
            
            elapsed = time.time() - start
            total_messages = num_agents * messages_per_agent
            throughput = total_messages / elapsed
            
            # Should handle >100 msg/s
            assert throughput > 100
            print(f"Hub throughput: {throughput:.0f} msg/s")
        
        finally:
            await hub.stop()
    
    @pytest.mark.asyncio
    async def test_vision_extraction_speed(self):
        """Test vision extraction latency."""
        
        adapter = VisionAdapter()
        screenshot = load_test_image("test_table.png")
        
        times = []
        for _ in range(10):
            start = time.time()
            state, confidence = await adapter.extract_state(screenshot, "test_001")
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = np.mean(times)
        
        # Vision extraction should take < 500ms
        assert avg_time < 0.5
        print(f"Average vision extraction time: {avg_time*1000:.0f}ms")
```

---

## 6. Error Recovery Mechanisms

### 6.1 Retry Strategies

```python
import asyncio
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential: bool = True,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                
                except exceptions as e:
                    if attempt == max_retries - 1:
                        # Last attempt, re-raise
                        raise
                    
                    delay = base_delay * (2 ** attempt if exponential else 1)
                    logging.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(NetworkError, TimeoutError))
async def fetch_state_from_hub(table_id: str) -> TableState:
    """Fetch state from hub with automatic retry."""
    return await hub_client.get_state(table_id)
```

### 6.2 Circuit Breaker Pattern

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject immediately
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: float = 60.0,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time >= self.timeout_duration:
                logging.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logging.info("Circuit breaker transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.success_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0
        
        if self.failure_count >= self.failure_threshold:
            logging.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# Usage
hub_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_duration=60.0)

async def get_state_with_circuit_breaker(table_id: str):
    """Get state from hub with circuit breaker protection."""
    return await hub_circuit_breaker.call(hub_client.get_state, table_id)
```

---

## 7. Monitoring and Alerting

### 7.1 Error Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Error counters
validation_errors = Counter(
    "simulation_validation_errors_total",
    "Total validation errors",
    ["component", "error_type"]
)

network_errors = Counter(
    "simulation_network_errors_total",
    "Total network errors",
    ["operation", "error_type"]
)

decision_errors = Counter(
    "simulation_decision_errors_total",
    "Total decision engine errors",
    ["error_type"]
)

vision_errors = Counter(
    "simulation_vision_errors_total",
    "Total vision extraction errors",
    ["model", "error_type"]
)

# Latency histograms
decision_latency = Histogram(
    "simulation_decision_latency_seconds",
    "Decision calculation latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

vision_latency = Histogram(
    "simulation_vision_latency_seconds",
    "Vision extraction latency",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# State gauges
active_agents = Gauge(
    "simulation_active_agents",
    "Number of active agents"
)

hub_connections = Gauge(
    "simulation_hub_connections",
    "Number of WebSocket connections"
)

# Usage in code
try:
    decision = engine.calculate_decision(state, profile)
except ValidationError as e:
    validation_errors.labels(component="decision_engine", error_type="validation").inc()
    raise
```

### 7.2 Alert Rules

```yaml
# alerting_rules.yml

groups:
  - name: simulation_errors
    interval: 30s
    rules:
      - alert: HighValidationErrorRate
        expr: rate(simulation_validation_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High validation error rate"
          description: "Validation errors >6/min for 2 minutes"
      
      - alert: DecisionEngineFailures
        expr: rate(simulation_decision_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Decision engine experiencing failures"
          description: "Decision errors >3/min for 5 minutes"
      
      - alert: HubDisconnections
        expr: rate(simulation_hub_connections[1m]) < -0.5
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Agents disconnecting from hub"
          description: "Connection drop rate >0.5/min"
      
      - alert: VisionExtractionFailures
        expr: rate(simulation_vision_errors_total[5m]) > 0.2
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Vision extraction failing frequently"
          description: "Vision errors >12/min for 3 minutes"
```

---

## Summary

### Key Error Prevention Strategies

1. **Input Validation:** Comprehensive Pydantic models with custom validators
2. **Type Safety:** Python type hints + mypy static analysis
3. **Fallback Chains:** Multiple fallback options for critical operations
4. **Graceful Degradation:** Conservative defaults when primary logic fails
5. **Retry Logic:** Exponential backoff for transient failures
6. **Circuit Breakers:** Prevent cascade failures in external service calls
7. **Comprehensive Testing:** 80-95% coverage targets for all components
8. **Monitoring:** Prometheus metrics + Grafana dashboards + AlertManager

### Error Handling Checklist

- [ ] All input models use Pydantic validation
- [ ] Custom validators for complex constraints
- [ ] Try-except blocks around all external calls
- [ ] Fallback mechanisms for critical paths
- [ ] Logging at appropriate levels (debug, info, warning, error, critical)
- [ ] Metrics exported for all error types
- [ ] Alert rules defined for critical errors
- [ ] Unit tests for error conditions
- [ ] Integration tests for failure scenarios
- [ ] Documentation of error codes and recovery procedures

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-05  
**Status:** Specification Complete

**Educational Use Only:** This specification is for research and educational simulation framework development.
