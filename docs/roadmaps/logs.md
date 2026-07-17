
#### 6. Roadmap for Logs 6/10 (logs.md)

```markdown
# logs.md — Улучшение логов и мониторинга

Цель: структурированные логи + алерты.

## Фаза 1 — JSON logging
- Добавить structured_logger.py (using logging module)

## Фаза 2 — External tools
- Добавить SQLite or file-based DB for logs

## Фаза 3 — Telegram alerts
- Добавить telegram_sender.py — на бан / ошибки
- Тест: 10 алертов


