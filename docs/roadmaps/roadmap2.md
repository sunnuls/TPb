# HIVE Roadmap v2 — Полноценная симуляция 3vs1 улья (research only)

Цель: построить виртуальную среду, где 3 coordinated агента всегда выигрывают против 1 dummy-человека за счёт:
- умного table selection
- обмена hole cards
- collective aggressive decisions

Всё строго в симуляции (educational multi-agent game theory study).

## Фаза 1: HIVE Table Selection + Auto-Join (сегодня-завтра)
1. Создай `sim_engine/table_selection.py`
   - Симулирует лобби: 200 случайных столов (human_count 0–6, max_seats 6 или 9)
   - Функция `find_hive_opportunities(lobby)` → возвращает список столов, где human_count ≤ 3 И seats_left ≥ 3
   - Приоритет: столы с 1 human + много свободных мест (идеал для 3vs1)

2. Добавь в `sim_engine/agent.py` метод `join_environment(environment_id)`

Промпт для Cursor (вставишь позже):

## Фаза 2: 3vs1 Card Sharing + Collective Equity
1. Расширь `central_hub.py`:
   - Когда в сессии ≥3 агента → они отправляют свои hole cards в hub (зашифровано)
   - Hub возвращает каждому агенту: collective_known_cards + equity vs remaining deck + dummy range

2. Создай `sim_engine/collective_decision.py`:
   - Если collective edge > 65% → aggressive line (large bet/raise/all-in)
   - Иначе — protect/fold

Промпт для Cursor:

## Фаза 3: Dummy Human Opponent + Full Simulation Loop
1. `sim_engine/dummy_opponent.py` — простой scripted игрок (tight-loose random с variance)

2. `sim_engine/hive_simulation.py`:
   - 100 агентов сканируют лобби
   - Находят profitable столы → 3 агента заходят
   - Играют 1000 рук против 1 dummy
   - Логируют: winrate, EV, pots won, coordination bonus

Промпт для Cursor:

## Фаза 4: Метрики и Dashboard
- `sim_engine/metrics.py` — winrate, ROI, edge exploitation, coordination efficiency
- Простой Flask dashboard (или Streamlit) — графики 3vs1 vs random

## Фаза 5: Scaling + Variance
- Запуск 100+ агентов в multiprocessing / Docker
- Random delays, style variance (чтобы симуляция была реалистичной)

## Как запускать roadmap2 в Cursor (один промпт)

Открой Cursor → Cmd+K и вставь **этот** текст:
