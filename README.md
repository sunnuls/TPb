# TPb

## AI Poker + Blackjack Coach (Scaffold)

Production-ready Python 3.11+ scaffold for an **AI Poker + Blackjack Coach** with a deterministic engine and a strict “**no hallucinations**” explanation layer.

### Key guarantees

- **No invented facts**: `coach_app/coach/explain.py` generates explanations **only** from `Decision.key_facts` (computed by the engine) and the validated input state.
- **Validation-first**: `coach_app/state/validate.py` rejects inconsistent states (duplicate cards, negative pot, impossible bet sizes, etc.).
- **Separation of concerns**: `ingest/` → `state/` → `engine/` → `coach/` → `api/` (and optional `ui/telegram_bot.py`).

### Range Model v0 (что это и что это НЕ)

В покере используется **Range Model v0** — небольшой набор **детерминированных** префлоп-диапазонов и объяснимых эвристик.

- **Это НЕ солвер**: нет CFR/GTO/Monte Carlo/рандома.
- **Это стабильно и тестируемо**: одинаковый ввод → одинаковый вывод.
- **Cash vs MTT**:
  - Cash: по умолчанию считаем стеки deep, пока effective \(\ge 60bb\)
  - MTT: бакеты `40bb+`, `20–40bb`, `<20bb` (в `<20bb` включается push/fold)

Подробнее: `docs/RANGES.md`

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
      "game_type": "cash",
      "effective_stack_bb": 100.0,
      "stack_bucket": "cash_deep",
      "stack_class": "deep",
      "equity": 0.54,
      "pot_odds": 0.31,
      "hero_range_name": "RFI_CO",
      "opponent_range_name": "no_action_yet",
      "range_intersection_note": "Часть opening range",
      "range_position": "top",
      "plan_hint": "Открываемся сайзингом ~2.2–2.5bb (v0).",
      "range_summary": "Villain: broadways+suited aces (placeholder)",
      "combos_summary": "You have top pair; villain has many worse pairs + draws",
      "notes": ["Monte Carlo 20k samples", "Preflop chart placeholder"]
    }
  },
  "explanation": "…строго из key_facts + валидированного состояния…",
  "parse_report": {
    "parser": "PokerStarsHandHistoryParser",
    "room": "pokerstars",
    "game_type_detected": "NLHE_6max_cash",
    "confidence": 0.9,
    "missing_fields": [],
    "warnings": [],
    "parsed": { "hero_hand": ["Ah","Ks"], "board": ["Ad","7c","2s"], "to_call": 0.0 }
  }
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

### Dev ergonomics

- **Tests**:

```bash
pytest
```

- **API**:

```bash
uvicorn coach_app.api.main:app --reload --port 8000
```

- **Lint** (optional):

```bash
ruff check .
```
