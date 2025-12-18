# TPb

## AI Poker + Blackjack Coach (Scaffold)

Production-ready Python 3.11+ scaffold for an **AI Poker + Blackjack Coach** with a deterministic engine and a strict “**no hallucinations**” explanation layer.

### Key guarantees

- **No invented facts**: `coach_app/coach/explain.py` generates explanations **only** from `Decision.key_facts` (computed by the engine) and the validated input state.
- **Validation-first**: `coach_app/state/validate.py` rejects inconsistent states (duplicate cards, negative pot, impossible bet sizes, etc.).
- **Separation of concerns**: `ingest/` → `state/` → `engine/` → `coach/` → `api/` (and optional `ui/telegram_bot.py`).

### Policy & product modes

Policy rules live in `coach_app/product/policy.py`.

- `docs/POLICY.md`

### Range Model v0 (что это и что это НЕ)

В покере используется **Range Model v0** — небольшой набор **детерминированных** префлоп-диапазонов и объяснимых эвристик.

- **Это НЕ солвер**: нет CFR/GTO/Monte Carlo/рандома.
- **Это стабильно и тестируемо**: одинаковый ввод → одинаковый вывод.
- **Cash vs MTT**:
  - Cash: по умолчанию считаем стеки deep, пока effective \(\ge 60bb\)
  - MTT: бакеты `40bb+`, `20–40bb`, `<20bb` (в `<20bb` включается push/fold)

Подробнее: `docs/RANGES.md`

### Postflop Line Logic v2 (что такое “линия”)

В постфлоп-части движка используется **Postflop Line Logic v2** — детерминированный выбор *одной обучающей линии розыгрыша* на флопе/тёрне/ривере.

**Линия** в этом продукте — это не «одно действие», а связка:

- **`selected_line`**: тип линии (что мы хотим делать в целом)
- **`sizing_category`**: категория сайзинга (`small`/`medium`/`large`)
- **`pot_fraction`**: рекомендуемая доля банка (если банк известен)
- **`recommended_bet_amount` / `recommended_raise_to`**: конкретные размеры ставок (если банк известен)
- **`rounding_step`**: шаг округления размеров
- **`line_reason`**: структурированная причина выбора (enum)
- **`street_plan`**: план в виде объекта `{ immediate_plan, next_street_plan }`

Поддерживаемые типы линий (v2):

- `cbet`
- `check`
- `delayed_cbet`
- `probe`
- `check_raise`
- `check_call`
- `bet_fold`
- `bet_call`
- `second_barrel`
- `give_up`
- `turn_probe`
- `turn_check_raise`
- `turn_value`
- `river_value`
- `river_bluff`
- `river_check_call`
- `river_check_fold`

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
      "pot_odds": 0.31,
      "hero_range_name": "RFI_CO",
      "opponent_range_name": "no_action_yet",
      "range_intersection_note": "Часть opening range",
      "range_position": "top",
      "plan_hint": "Открываемся сайзингом ~2.2–2.5bb (v0).",
      "range_summary": "Villain: broadways+suited aces (placeholder)",
      "combos_summary": "You have top pair; villain has many worse pairs + draws",
      "notes": ["Детерминированная эвристика", "Preflop chart placeholder"]
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

### Пример постфлоп-линии (end-to-end)

Допустим, у нас флоп `Ad 7c 2s`, герой был префлоп-агрессором, и мы хотим получить объяснимую рекомендацию.
Тогда в ответе (внутри `decision.key_facts`) появятся постфлоп-факты (пример):

```json
{
  "board_texture": {
    "is_paired": false,
    "is_monotone": false,
    "is_two_tone": false,
    "straight_connectivity": "low",
    "dryness": "dry"
  },
  "preflop_aggressor": true,
  "in_position": true,
  "selected_line": "cbet",
  "sizing_category": "small",
  "pot_fraction": 0.33,
  "recommended_bet_amount": 4.0,
  "recommended_raise_to": null,
  "rounding_step": 1.0,
  "line_reason": "range_advantage_dry",
  "street_plan": {
    "immediate_plan": "Флоп: ставим, потому что верх диапазона может добирать и защищаться.",
    "next_street_plan": "План: продолжаем на бланках; замедляемся на явных доборах/дро-картах."
  }
}
```

А `explanation` будет собран **строго из этих `key_facts`** и будет явно ссылаться на выбранную линию.

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

### Blackjack v1 (Basic Strategy + trainer)

В проекте Blackjack-движок **детерминированный** и объяснимый:

- **Basic Strategy**: табличная стратегия (multi-deck, S17, DAS) с учётом ограничений `allowed_actions` и правил.
- **EV reasoning (didactic)**: обучающая оценка «почему альтернативы хуже» без симуляций и без точных вероятностей.
- **No hallucinations**: объяснение строится **строго** из `decision.key_facts`.

Поддерживаемые правила (`rules`):

- `decks` (по умолчанию 6)
- `dealer_hits_soft_17` (по умолчанию `false` = S17)
- `double_after_split` (по умолчанию `true` = DAS)
- `surrender_allowed` (`none|early|late`, по умолчанию `late`)
- `resplit_aces` (по умолчанию `false`)
- `max_splits` (по умолчанию 3)

#### Пример: /analyze/blackjack

```bash
curl -X POST "http://127.0.0.1:8000/analyze/blackjack" ^
  -H "Content-Type: application/json" ^
  -d "{\"player_hand\":[\"Ah\",\"7d\"],\"dealer_upcard\":\"9c\",\"rules\":{},\"allowed_actions\":[\"hit\",\"stand\",\"double\"]}"
```

#### Пример: /train/blackjack (deterministic scenarios)

1) Получить сценарий:

```bash
curl -X POST "http://127.0.0.1:8000/train/blackjack" ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"trainer\",\"scenario_index\":0}"
```

2) Отправить ответ пользователя:

```bash
curl -X POST "http://127.0.0.1:8000/train/blackjack" ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"trainer\",\"scenario_index\":0,\"chosen_action\":\"hit\"}"
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

### Vision Adapters v1 (screenshot-based, conservative)

В проект добавлен слой **Vision Adapters v1** для анализа **скриншотов** (review/trainer). Это **НЕ** лайв-автоматизация и **НЕ** стриминг.

Что умеет v1:

- **Poker**:
  - извлекает **только видимые карты** (`hero_hole`, `board`) и **улицу** (`street`) по количеству карт на борде
  - всё остальное (банк, стеки, экшены) **не извлекается**
- **Blackjack**:
  - минимальный stub: пытается извлечь `dealer_upcard` и `player_hand` только когда карты видны очень явно

Что v1 НЕ умеет:

- не распознаёт банк/стеки/экшены
- не подменяет hand history и **никогда** не «догадывается» обязательные факты
- не обучает модели, не требует GPU

#### Философия confidence

- Vision возвращает **частичное** состояние и `confidence_map` по полям.
- **Известные факты всегда выигрывают**:
  - если есть hand history/ручной ввод (`base_state`), он **не перезаписывается** vision-данными
  - если есть конфликт — сохраняем базовое значение и добавляем warning
- При `confidence < 1.0` объяснение начинается с **короткого дисклеймера**.

#### API: Poker screenshot analyze

Endpoint:

- `POST /analyze/poker/screenshot`

Alias endpoint (same behavior):

- `POST /analyze/poker/instant_review`

Формат:

- `multipart/form-data`
  - `image`: файл (png/jpg)
  - `payload`: optional JSON-строка
    - `hand_history_text`: optional
    - `meta`: optional

Пример (PowerShell curl):

```bash
curl -X POST "http://127.0.0.1:8000/analyze/poker/screenshot" ^
  -F "image=@C:\\path\\to\\screenshot.png" ^
  -F "payload={\"hand_history_text\":\"PokerStars Hand #123...\"}"
```

Поведение:

- если `hero_hole` не найден и нет HH → вернётся **422** с явным `missing_fields`
- результат содержит:
  - `decision`
  - `explanation` (с дисклеймером при неполной уверенности)
  - `confidence`
  - `warnings`

### Instant Review mode (post-action coaching)

`INSTANT_REVIEW` позволяет отслеживать стол (периодическими кадрами), но **показывать подсказки только после совершения действия**.

Гарантии:

- Сервер возвращает **403** с `detail.code="POLICY_BLOCK"`, если `meta.post_action != true`.
- Клиентский трекер **никогда не печатает** ответы, если действие не зафиксировано (post-action).

#### Quickstart: tools/instant_review_tracker.py (dev frames)

1) Убедитесь, что API запущен:

```bash
uvicorn coach_app.api.main:app --reload --port 8000
```

2) Положите тестовые кадры (png/jpg) в папку:

- `tools/frames/`

3) Запустите трекер:

```bash
python tools/instant_review_tracker.py --config tools/config.yaml
```

4) Чтобы «зафиксировать действие» и получить подсказку, нажмите **Enter** в консоли (hotkey trigger).

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
