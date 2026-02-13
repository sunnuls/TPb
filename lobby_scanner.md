
#### 2. Roadmap for Lobby Scanner Weakness (lobby_scanner.md)

```markdown
# lobby_scanner.md — Улучшение live lobby scanner

Цель: стабильный скан лобби без rate-limit, с fallback.

## Фаза 1 — OCR-улучшения
- Расширить live_capture.py и test_real_ocr.py — распознавание игроков/мест в лобби

## Фаза 2 — HTTP fallback
- Добавить lobby_http_parser.py — если API доступно, fallback к HTTP-запросам

## Фаза 3 — Anti-limit и прокси
- Добавить delay + proxy rotation in live_table_scanner.py (if exists)
- Тест: 100 сканов без ошибок (test_with_hand_history.py adapt)

