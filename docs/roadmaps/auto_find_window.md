
#### 10. Roadmap for Bad Screen Capture Auto-Find (auto_find_window.md)

```markdown
# auto_find_window.md — Авто-наход окна и crop edges

Цель: бот сам находит окно и зумит по краям.

## Фаза 1 — Auto-search window
- Расширить test_windows_list.py — auto-find by title/keywords

## Фаза 2 — Auto-crop edges
- Добавить edge_detection in screen_capture.py (opencv Canny or Sobel)

## Фаза 3 — Тесты
- Тест: 10 окон → авто-наход + crop
