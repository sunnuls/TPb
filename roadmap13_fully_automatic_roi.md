# roadmap13_fully_automatic_roi.md
Полностью автоматический режим определения окна и ROI зон (с одноразовым обучением)

Цель: После одного раза подготовки шаблонов бот должен полностью самостоятельно:
- находить окно покер-клиента
- находить ключевые элементы (anchors)
- автоматически рассчитывать все ROI зоны
- работать стабильно при перемещении окна, изменении размера и т.д.

## Фаза 1 — Подготовка шаблонов (одноразовое обучение)
- Создать папку `templates/anchors/`
- Добавить 8–10 шаблонов (PNG):
  - logo (логотип рума)
  - btn_fold, btn_call, btn_raise, btn_check
  - chip_icon, pot_icon
  - table_border или corner
- Создать `config/anchor_templates.yaml` — список шаблонов с threshold, типом и относительными смещениями зон

## Фаза 2 — Авто-поиск окна
- Расширить `bridge/screen_capture.py`:
  - auto_find_window() — поиск по заголовку/процессу + визуальный поиск логотипа
  - Сохранение найденного окна в config/active_window.json

## Фаза 3 — Автоматический расчёт всех ROI зон
- Создать `bridge/vision/anchor_detector.py`:
  - find_anchors(image) — поиск всех шаблонов с cv2.matchTemplate + multi-scale
  - calculate_all_roi(anchors, image_shape) — автоматический расчёт зон (hero cards, board, pot, stacks, action buttons и т.д.) относительно найденных anchors
  - Поддержка derived zones (midpoint, bounding_box)

## Фаза 4 — Интеграция в лаунчер и основной цикл бота
- В `launcher/bot_manager.py` и `bot_instance.py`:
  - При запуске бота: auto_find_window() → find_anchors() → calculate_all_roi()
  - Каждые 20–30 секунд — повторный авто-пересчёт (если окно переместили)
  - Fallback: если anchors не найдены → использовать относительные % из конфига

## Фаза 5 — Тестирование и финализация
- Тесты: 30 разных скриншотов (разные румы, разрешения, положения окна)
- Accuracy test: >92% правильного определения зон
- Стабильность: перемещение окна, изменение размера, разные темы

