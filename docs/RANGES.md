## Range Model v0

Это **не солвер** и не GTO-чарты. Это небольшой набор **детерминированных пресетов** (читабельные словари), который:

- даёт **стабильные** рекомендации (без рандома),
- позволяет объяснять решение через:
  - выбранный диапазон (`hero_range_name`, `opponent_range_name`)
  - позицию руки внутри диапазона (`range_position`)
  - простую роль руки (value / semi-bluff / bluff-catcher) через `plan_hint`.

### Стековые бакеты

- **Cash**
  - `cash_deep` (по умолчанию, если effective \(\ge 60bb\))
  - `cash_mid` (\(25–60bb\))
  - `cash_short` (\(<25bb\))
- **MTT**
  - `mtt_40plus` (\(\ge 40bb\))
  - `mtt_20_40` (\(20–40bb\))
  - `mtt_lt20` (\(<20bb\), включается push/fold эвристика)

### Что входит в пресеты

- **RFI** по позициям: UTG, HJ, CO, BTN, SB
- **BB defend vs BTN open**
- **3bet vs late open** (CO/BTN)
- **MTT shove v0** для `<20bb` (пуш/фолд)

Источник: `coach_app/engine/poker/ranges/presets.py`

## Range Model v0

### Что это

**Range Model v0** — это маленький, читаемый набор **детерминированных** префлоп-диапазонов (RFI/defend/3bet/shove) + правила, как использовать их в решениях.

- Диапазоны задаются **в коде** как `Dict[str, float]` (никаких солверов, CFR, Monte Carlo).
- Вес \(0..1\) означает частоту включения руки в диапазон (v0: 1.0/0.75/0.5).
- Решение всегда объясняется через `Decision.key_facts`.

### Что это НЕ

- Это **не GTO-чарты** и не попытка “посчитать оптимально”.
- Это **не** симуляции equity.
- Это **не** ICM.

### Где лежит

- `coach_app/engine/poker/ranges/range.py`: класс `Range`
- `coach_app/engine/poker/ranges/presets.py`: пресеты (RFI по позициям, BB defend vs BTN, 3bet vs late, shove v0)

### Стек-бакеты

- Cash:
  - `cash_deep` (>=60bb)
  - `cash_mid` (25–60bb)
  - `cash_short` (<25bb)
- MTT:
  - `mtt_40plus` (>=40bb)
  - `mtt_20_40` (20–40bb)
  - `mtt_lt20` (<20bb) — включается push/fold эвристика


