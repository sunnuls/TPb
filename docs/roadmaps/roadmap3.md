# roadmap3_live_bridge_max.md — Максимальная Bridge к Live Client (HCI Research Prototype)

Цель: исследовать возможность извлечения состояния и взаимодействия с внешним desktop-приложением (educational HCI / external application interface research prototype).

Всё строго в dry-run режиме по умолчанию. Реальные действия запрещены без флага --unsafe.

## Фаза 0 – Safety Framework (1–2 дня)
- Создать `bridge/safety.py` — глобальный kill-switch, dry_run флаг, emergency shutdown
- Добавить в main.py аргумент `--bridge-mode --dry-run` (по умолчанию)
- Создать `bridge/config/live_config.yaml` (room name, window title, resolution, ROI presets)

## Фаза 1 – Screen Capture & ROI System (3–5 дней)
1. `bridge/screen_capture.py` — захват конкретного окна по заголовку/процессу
2. `bridge/roi_manager.py` — динамическая загрузка ROI из json (per room + resolution)
3. Тест: каждые 2 сек захват + сохранение скриншота + проверка стабильности

## Фаза 2 – State Extraction Engine (3–4 недели) ← самая важная
1. `bridge/vision/card_extractor.py` — hero cards + board (использовать существующий vision adapter из coach_app)
2. `bridge/vision/numeric_parser.py` — pot, stacks, bets, positions
3. `bridge/vision/metadata.py` — stage, table type, seats
4. `bridge/state_bridge.py` — конвертировать всё в существующий `TableState` из sim_engine/state/

Результат: `get_live_table_state() → TableState` (полностью совместима с collective_decision и central_hub)

## Фаза 3 – Live Lobby & Opportunity Detection (2 недели)
1. `bridge/lobby_scanner.py` — захват и анализ лобби (кол-во игроков, seats left)
2. `bridge/opportunity_detector.py` — точная копия логики из sim_engine/table_selection.py, но на реальных данных
3. Логирование только (dry-run)

## Фаза 4 – External Coordination (1–2 недели)
1. `bridge/external_hub_client.py` — подключение к удалённому хабу (WebSocket + Fernet)
2. `bridge/bot_identification.py` — shared secret + position hash (чтобы 3 экземпляра поняли, что они за одним столом)
3. Интеграция с существующим central_hub

## Фаза 5 – Action Layer (dry-run + simulation) (2–3 недели)
1. `bridge/action_translator.py` — CollectiveDecision → ActionCommand
2. `bridge/action_simulator.py` — **ТОЛЬКО ЛОГИРОВАНИЕ** (что было бы сделано, без кликов)
3. `bridge/humanization_sim.py` — симуляция задержек, mouse paths, variance (без реального ввода)

**Важно:** реальные клики запрещены до явного --unsafe

## Фаза 6 – Monitoring & Safety (2 недели)
1. `bridge/monitoring.py` — детекция изменения UI, подозрительных событий, алерты
2. Авто-shutdown при любых аномалиях
3. Логирование всех решений + скриншотов

## Фаза 7 – Integration & Testing
- Режимы: --dry-run (по умолчанию) → --safe (только fold/check/call) → --unsafe (полный)
- Сравнение winrate симуляции vs live (dry-run)
- Финальный тест: 1000 рук в dry-run режиме

## Стартовый промпт для Cursor (вставляй в Cmd+K)
