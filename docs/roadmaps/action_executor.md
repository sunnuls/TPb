#### 3. Roadmap for Action Executor Minimal (action_executor.md)

```markdown
# action_executor.md — Улучшение action executor

Цель: сделать клики надёжными и humanized.

## Фаза 1 — Bezier mouse paths
- Добавить mouse_curve_generator.py — Bezier curves for mouse (using pyautogui)

## Фаза 2 — Behavioral variance
- Расширить humanization_layer.py — стили aggressive / passive random

## Фаза 3 — Anti-pattern
- Добавить random delays + key/mouse variance
- Тест: 100 кликов без pattern (test_api_simulation.py adapt)

