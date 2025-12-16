# TPb

## AI Poker + Blackjack Coach (Scaffold)

Production-ready Python 3.11+ scaffold for an **AI Poker + Blackjack Coach** with a deterministic engine and a strict “**no hallucinations**” explanation layer.

### Key guarantees

- **No invented facts**: `coach_app/coach/explain.py` generates explanations **only** from `Decision.key_facts` (computed by the engine) and the validated input state.
- **Validation-first**: `coach_app/state/validate.py` rejects inconsistent states (duplicate cards, negative pot, impossible bet sizes, etc.).
- **Separation of concerns**: `ingest/` → `state/` → `engine/` → `coach/` → `api/` (and optional `ui/telegram_bot.py`).

### Quickstart

- **Install** (PowerShell):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

- **Run API**:

```bash
uvicorn coach_app.api.main:app --reload --port 8000
```

- **Run tests**:

```bash
pytest
```

### API examples

#### Poker analyze (MVP: Hand History text)

Request:

```bash
curl -X POST "http://127.0.0.1:8000/analyze/poker" ^
  -H "Content-Type: application/json" ^
  -d "{\"hand_history_text\":\"PokerStars Hand #123...\"}"
```

Response (shape):

```json
{
  "decision": {
    "action": "raise",
    "sizing": 2.5,
    "confidence": 0.63,
    "key_facts": {
      "equity": 0.54,
      "pot_odds": 0.31,
      "range_summary": "Villain: broadways+suited aces (placeholder)",
      "combos_summary": "You have top pair; villain has many worse pairs + draws",
      "notes": ["Monte Carlo 20k samples", "Preflop chart placeholder"]
    }
  },
  "explanation": "…strictly derived from key_facts…"
}
```

#### Blackjack analyze

Request:

```bash
curl -X POST "http://127.0.0.1:8000/analyze/blackjack" ^
  -H "Content-Type: application/json" ^
  -d "{\"player_hand\":[\"A\",\"7\"],\"dealer_upcard\":\"9\",\"rules\":{\"decks\":6,\"hit_soft_17\":false,\"das\":true,\"surrender\":true}}"
```

Response (shape):

```json
{
  "decision": {
    "action": "hit",
    "confidence": 0.9,
    "key_facts": { "table": "S17 DAS (default)", "hand_type": "soft", "total": 18 }
  },
  "explanation": "Soft 18 vs 9 is a Hit under the configured rules…"
}
```

### Optional Telegram bot

Install extra:

```bash
pip install -e ".[telegram]"
```

Run (requires env var `TELEGRAM_BOT_TOKEN`):

```bash
python -m coach_app.ui.telegram_bot
```

### Adapter configs (YAML/JSON)

Example configs live in `coach_app/configs/adapters/` and define:

- ROI coordinates (screen regions)
- Anchors (UI markers)
- Adapter type + metadata

The vision layer is stubbed (plugin interface + placeholder adapter) so you can integrate OCR / card recognition later.
