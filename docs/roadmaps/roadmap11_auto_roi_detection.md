# roadmap11_auto_roi_detection.md — Полностью автоматическое определение ROI зон

Цель: сделать так, чтобы бот сам находил окно и зоны без ручного выделения (template matching + anchors).

## Фаза 1 — Авто-поиск окна по заголовку/процессу
- Расширить bridge/screen_capture.py:
  - Функция auto_find_window() — поиск по части заголовка ("CoinPoker", "Table", "Poker") или процессу
  - Возвращает HWND или None
  - Сохраняет в config/active_window.json
- Тест: запуск → проверка нахождения окна

## Фаза 2 — Сбор и хранение шаблонов (anchors)
- Создать папку templates/anchors/
  - Добавить изображения: logo_coinpoker.png, btn_fold.png, btn_call.png, btn_raise.png, chip_icon.png, table_border.png
  - Добавить в config/anchor_templates.yaml — список шаблонов и их зоны (относительные)

## Фаза 3 — Поиск anchors и расчёт ROI
- Создать bridge/vision/anchor_detector.py:
  - Функция find_anchors(image) — cv2.matchTemplate для каждого шаблона
  - Функция calculate_relative_roi(anchors) — пересчёт зон относительно найденных anchors
  - Пример: board = центр между logo и btn_fold
  - hero_cards = слева/справа от chip_icon
- Тест: на 10 скриншотах → точность нахождения anchors >90%

## Фаза 4 — Интеграция в основной цикл
- В live_rta.py или bot_instance.py:
  - При запуске: auto_find_window() → find_anchors() → calculate_relative_roi()
  - Если anchors не найдены → fallback на относительные % из конфига
  - Каждые 30 сек — повторный поиск (если окно переместили)
- Добавить логирование: "Найден логотип CoinPoker в (x,y), пересчитаны зоны"

## Фаза 5 — Тестирование и улучшение
- Тесты: 20 разных скриншотов CoinPoker → сравнение auto-ROI vs ручной
- Добавить fallback: если auto не нашёл — просить пользователя выделить 2 точки (левый верх + правый низ)
- Цель: точность зон >90% без ручного ввода


