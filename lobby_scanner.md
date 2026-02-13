#### Roadmap for Lobby Scanner Weakness (lobby_scanner.md)

```markdown
# lobby_scanner.md — Улучшение live lobby scanner

Цель: стабильный скан лобби без rate-limit.

## Фаза 1 — OCR-улучшения
- Добавить lobby_ocr.py — распознавание игроков/мест

## Фаза 2 — HTTP-фоллбэк
- Если API доступен — добавить lobby_http_parser.py

## Фаза 3 — Anti-limit
- Delay + proxy rotation
- Тест: 100 сканов без ошибок

