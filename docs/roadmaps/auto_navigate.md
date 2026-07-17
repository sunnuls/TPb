
#### 11. Roadmap for Bot Not Clicking Auto-Navigate (auto_navigate.md)

```markdown
# auto_navigate.md — Авто-клики, поиск режимов, столов, листание, заход

Цель: бот сам находит/кликает режимы, столы, листание, join.

## Фаза 1 — Navigation module
- Добавить navigation_manager.py — OCR + template for buttons (modes, tables, scroll, join)

## Фаза 2 — Auto-actions
- Расширить real_executor.py — клики по найденным регионам

## Фаза 3 — Тесты
- Тест: от лобби до стола автоматически (dry-run)
