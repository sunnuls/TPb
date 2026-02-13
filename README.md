# TPb

## AI Poker + Blackjack Coach (Scaffold)

Production-ready Python 3.11+ scaffold for an **AI Poker + Blackjack Coach** with a deterministic engine and a strict “**no hallucinations**” explanation layer.

### Key guarantees

- **No invented facts**: `coach_app/coach/explain.py` generates explanations **only** from `Decision.key_facts` (computed by the engine) and the validated input state.
- **Validation-first**: `coach_app/state/validate.py` rejects inconsistent states (duplicate cards, negative pot, impossible bet sizes, etc.).
- **Separation of concerns**: `ingest/` → `state/` → `engine/` → `coach/` → `api/` (and optional `ui/telegram_bot.py`).

### Documentation

| Guide | Description |
|---|---|
| [`docs/VISION_SETUP.md`](docs/VISION_SETUP.md) | Vision pipeline setup: capture, ROI, OCR, YOLO, humanization |
| [`docs/BOT_PROFILES.md`](docs/BOT_PROFILES.md) | Bot profiles: presets, JSON format, A/B testing |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Troubleshooting: diagnostics, common errors, fixes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture overview |
| [`docs/API.md`](docs/API.md) | Coach API reference (REST endpoints) |
| [`docs/API_HUB_DECISION.md`](docs/API_HUB_DECISION.md) | Hub & Decision engine API (WebSocket + internal) |
| [`docs/POLICY.md`](docs/POLICY.md) | Policy & ethical guidelines |
| [`docs/RANGES.md`](docs/RANGES.md) | Range Model v0 details |
| [`docs/LIVE_RTA.md`](docs/LIVE_RTA.md) | Live RTA setup guide |

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

- **Tesseract OCR (Windows)**:

1) Скачайте и установите Tesseract OCR:

- https://github.com/tesseract-ocr/tesseract

2) Добавьте папку установки Tesseract в `PATH`.

Пример пути (может отличаться):

- `C:\Program Files\Tesseract-OCR`

- **Live (vision dependencies)**:

```bash
pip install -e ".[live]"
```

Опционально (fallback-автоматизация, может требовать доп. зависимостей/права доступа в Windows):

```bash
pip install -e ".[live_fallback]"
```

Примечание (Windows): если `pip install -e ...` падает на шаге `build_editable` (PEP660), используйте обходной путь:

```bash
pip install .
pip install opencv-python pytesseract mss keyboard pyqt5
```

Либо попробуйте compat-режим editable (если поддерживается вашим pip/setuptools):

```bash
pip install -e . --config-settings editable_mode=compat
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

### Live RTA (локальный live-цикл поверх VisionAdapter)

В проект добавлен локальный live-режим `coach_app.rta.live_rta`, который:

- периодически **захватывает экран**
- извлекает состояние через `LiveVisionAdapter`
- валидирует состояние и запускает **детерминированный движок** (Range Model v0 + Postflop Line Logic v2)
- выводит объяснение в `console` / `overlay` / `telegram`

#### Важно про ethics

По умолчанию `--ethical` включён: вывод происходит **только после события post-action**.
Post-action можно зафиксировать:

- по детектору изменений UI (absdiff между кадрами)
- вручную: нажать **Enter** в консоли (hotkey)

#### Quickstart

1) Установите зависимости live-режима:

```bash
pip install -e ".[live]"
```

2) Запуск (можно передать **adapter config** напрямую):

```bash
python -m coach_app.rta.live_rta --config coach_app/configs/adapters/pokerstars_live.yaml --mode console
```

3) Overlay режим (PyQt5):

```bash
python -m coach_app.rta.live_rta --config coach_app/configs/adapters/pokerstars_live.yaml --mode overlay
```

4) Telegram режим (нужны настройки `telegram.bot_token/chat_id`):

```bash
python -m coach_app.rta.live_rta --config coach_app/configs/adapters/pokerstars_live.yaml --mode telegram
```

5) Если вам нужно отключить post-action gating (НЕ рекомендуется):

```bash
python -m coach_app.rta.live_rta --config coach_app/configs/adapters/pokerstars_live.yaml --mode console --no-ethical
```

### HIVE Launcher — Bot Coordination System

> ⚠️ **EDUCATIONAL RESEARCH ONLY** — coordinated bot operation (collusion) is ILLEGAL in real poker.

HIVE Launcher — GUI-приложение для управления пулом ботов с автоматическим vision pipeline, decision engine и action executor.

#### Architecture

```
launcher/
├── main.py                 # Entry point (PyQt6 GUI)
├── bot_manager.py          # Bot pool management (start/stop/monitor)
├── bot_instance.py         # Single bot: Vision → Decision → Action loop
├── bot_settings.py         # Per-bot configuration (BotSettings dataclass)
├── bot_profile_manager.py  # JSON profiles (shark/rock/tag/lag/fish)
├── bot_config_loader.py    # Per-bot config loading + hot-reload
├── ab_testing.py           # A/B profile comparison framework
├── collusion_coordinator.py # HIVE coordination (card sharing)
├── auto_seating.py         # Auto table selection
├── auto_bot_controller.py  # Automated bot lifecycle
├── lobby_scanner.py        # Lobby monitoring
├── structured_logger.py    # JSON structured logging
├── log_storage.py          # SQLite + Elasticsearch log storage
├── telegram_alerts.py      # Telegram alerts (ban/error notifications)
├── config_manager.py       # Room/ROI config management
├── window_capture.py       # Window capture utilities
├── log_handler.py          # GUI log handler (PyQt6 signals)
├── system_tray.py          # System tray icon
├── vision/                 # Vision pipeline modules
│   ├── auto_ui_detector.py       # Automatic UI element detection
│   ├── auto_navigator.py         # Auto-navigation between screens
│   ├── auto_roi_finder.py        # Auto-calibration of ROI zones
│   ├── window_capturer.py        # Win32 API screen capture
│   ├── multi_template_matching.py # Multi-scale template matching + OCR
│   ├── yolo_region_detector.py   # YOLOv8 table region detection
│   ├── lobby_ocr.py              # Lobby screenshot OCR engine
│   ├── lobby_http_parser.py      # HTTP-based lobby data fallback
│   ├── lobby_anti_limit.py       # Rate-limit protection orchestrator
│   ├── mouse_curve_generator.py  # Bézier mouse trajectory generation
│   ├── behavioral_variance.py    # Player behavior profiles (aggressive/passive)
│   └── anti_pattern_executor.py  # Anti-pattern click orchestrator
├── ui/                     # PyQt6 GUI tabs
│   ├── main_window.py
│   ├── dashboard_tab.py
│   ├── bots_control_tab.py
│   ├── accounts_tab.py
│   ├── logs_tab.py
│   └── settings_dialog.py
├── models/                 # Data models (Account, ROIConfig)
├── tests/                  # Unit tests (400+ tests)
└── config/                 # Runtime configuration
    ├── bot_profiles.json   # 5 preset profiles
    ├── accounts.json       # Account credentials
    └── rooms/              # Per-room ROI configs (YAML)
```

#### Launching the GUI

```bash
python -m launcher.main
```

Requires `PyQt6`. The GUI provides tabs for:
- **Dashboard** — overview of all bots, profit, active tables
- **Bot Control** — start/stop individual bots, assign profiles
- **Accounts** — manage poker room accounts and windows
- **Logs** — real-time color-coded log stream
- **Settings** — global and per-bot configuration

#### Launching Live Bot (headless)

To start bots without the GUI, use the auto-bot controller:

```bash
python -c "
from launcher.auto_bot_controller import AutoBotController
controller = AutoBotController()
controller.start()
"
```

#### Command-Line Flags & Configuration

| Parameter | Location | Description |
|---|---|---|
| `preset` | `BotSettings` | Strategy preset: `conservative`, `balanced`, `aggressive`, `godmode`, `custom` |
| `aggression_level` | `BotSettings` | 1–10, controls bet sizing and bluff frequency |
| `equity_threshold` | `BotSettings` | 0.0–1.0, minimum equity to continue (postflop) |
| `max_bet_multiplier` | `BotSettings` | 1.0–10.0, maximum bet size relative to pot |
| `delay_min` / `delay_max` | `BotSettings` | Action delay range (seconds) for humanization |
| `mouse_curve_intensity` | `BotSettings` | 0–10, Bézier curve curvature for mouse movement |
| `max_session_time` | `BotSettings` | Maximum session duration (minutes) |
| `auto_rejoin` | `BotSettings` | Auto-rejoin after disconnect |

#### Bot Profiles (JSON)

Pre-configured profiles in `config/bot_profiles.json`:

| Profile | Style | Aggression | Equity (preflop open) | Description |
|---|---|---|---|---|
| `shark` | Tight-Aggressive | 8/10 | 0.60 | Fast, decisive, high fold equity |
| `rock` | Tight-Passive | 2/10 | 0.78 | Premium hands only, minimal risk |
| `tag` | TAG (balanced) | 6/10 | 0.65 | Solid default play |
| `lag` | Loose-Aggressive | 9/10 | 0.48 | Wide range, lots of pressure |
| `fish` | Loose-Passive | 4/10 | 0.50 | Mimics a weak recreational player |

Assign profiles per bot:

```python
from launcher.bot_config_loader import BotConfigLoader
loader = BotConfigLoader()
loader.assign("bot_1", "shark")
loader.assign("bot_2", "fish", overrides={"aggression_level": 6})
settings = loader.load_for_bot("bot_1")
```

#### ROI Configuration

ROI (Region of Interest) zones define screen areas for card detection, pot, buttons, etc.

**Auto-calibration:**

```python
from launcher.vision import AutoROIFinder
finder = AutoROIFinder()
result = finder.calibrate(screenshot)
# result.zones = {"hero_card_1": (x, y, w, h), "pot": (...), ...}
```

**Manual YAML config** (`config/rooms/pokerstars.yaml`):

```yaml
room: pokerstars
table_size: 6max
zones:
  hero_card_1: {x: 380, y: 420, w: 50, h: 70}
  hero_card_2: {x: 440, y: 420, w: 50, h: 70}
  pot:         {x: 400, y: 150, w: 120, h: 30}
  board:       {x: 280, y: 250, w: 360, h: 70}
  btn_fold:    {x: 350, y: 550, w: 80, h: 30}
  btn_call:    {x: 460, y: 550, w: 80, h: 30}
  btn_raise:   {x: 570, y: 550, w: 80, h: 30}
```

#### Vision Pipeline

The vision system supports three detection methods:

1. **Template Matching** — `MultiTemplateMatcher` with multi-scale search
2. **OCR** — `RobustOCR` with Tesseract + EasyOCR + multi-strategy preprocessing
3. **YOLOv8** — `YOLORegionDetector` for ML-based table region detection

#### Humanization (Anti-Detection)

Mouse movements use Bézier curves with human-like properties:

```python
from launcher.vision import MouseCurveGenerator
gen = MouseCurveGenerator(intensity=5)
path = gen.generate(start=(100, 200), end=(500, 400))
for pt in path.points:
    move_to(pt.x, pt.y)
    sleep(pt.dt)
```

Behavioral profiles add session-long variance:

```python
from launcher.vision import BehaviorSampler, BehaviorProfile
sampler = BehaviorSampler(BehaviorProfile.aggressive())
think_time = sampler.sample_think_time("raise")  # 0.25–1.2s
mouse_cfg = sampler.sample_mouse_config()         # curve, speed, jitter
```

#### Structured Logging

JSON structured logs with context fields:

```python
from launcher.structured_logger import get_structured_logger, setup_structured_logging
setup_structured_logging(log_dir="logs")

log = get_structured_logger("bot.engine", bot_id="abc123")
log.info("Hand started", hand_id=42, table="NL50")
# → {"ts":"...","level":"INFO","logger":"bot.engine","msg":"Hand started","bot_id":"abc123","hand_id":42,"table":"NL50"}
```

Log storage backends:

```python
from launcher.log_storage import SQLiteLogStore, LogRouter
store = SQLiteLogStore("logs/bot_logs.db")
store.query(level="ERROR", contains="ban", limit=50)
```

#### Telegram Alerts

Real-time alerts to Telegram on bans, errors, crashes:

```python
from launcher.telegram_alerts import TelegramSender, AlertManager, AlertRule
sender = TelegramSender(bot_token="123:ABC", chat_id="-100123")
mgr = AlertManager(sender)
mgr.add_rule(AlertRule(name="ban", level="CRITICAL", keywords=["ban"]))
mgr.add_rule(AlertRule(name="errors", level="ERROR", cooldown_s=120))
```

#### Bridge Module

The `bridge/` module connects vision output to action execution:

```
bridge/
├── bridge_main.py          # Main vision → state → action loop
├── state_bridge.py         # Converts vision data to game state
├── action_translator.py    # Translates decisions to UI actions
├── roi_manager.py          # ROI zone management
├── screen_capture.py       # Screen capture (Win32 API)
├── safety.py               # Safety checks and kill switch
├── action/
│   └── real_executor.py    # Mouse/keyboard action execution
└── config/                 # Bridge-specific configs
```

### Dev ergonomics

- **Tests**:

```bash
pytest
```

Run launcher-specific tests:

```bash
pytest launcher/tests/ -v
```

- **API**:

```bash
uvicorn coach_app.api.main:app --reload --port 8000
```

- **Lint** (optional):

```bash
ruff check .
```
