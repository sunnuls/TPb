ы
#### 8. Roadmap for Bad Screen Capture (bad_capture.md)

```markdown
# bad_capture.md — Фикс кривого захвата экрана

Цель: сделать захват полным и точным.

## Фаза 1 — Auto-find window
- Расширить screen_capture.py — auto-search by title/class, crop by edges

## Фаза 2 — Full screen fix
- Добавить resize/crop logic to capture entire window

## Фаза 3 — Тесты
- Тест: 10 разных окон → полный захват без обрезки

