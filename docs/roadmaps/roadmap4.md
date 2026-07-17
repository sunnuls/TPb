# roadmap4_unsafe_vision.md — Unsafe Mode + Vision Enhancement (HCI Research Prototype – Advanced)

Цель: исследовать возможности unsafe-режима (симуляция реальных действий) и улучшения vision-слоя для различных внешних desktop-приложений.



## Фаза 1 – Unsafe Action Executor (основной рискованный шаг)

1. Создать/расширить `bridge/action/real_executor.py`:
   - Использовать библиотеку для эмуляции ввода (mouse + keyboard)
   - Поддержка кликов по координатам (из ROI) и ввода сумм
   - Реализовать 3 уровня действий:
     - fold / check / call — низкий риск
     - bet / raise фиксированные суммы — средний риск
     - all-in / большие raise — высокий риск

2. Добавить humanization в `bridge/humanization_layer.py`:
   - Случайные задержки перед действием (0.4–3.5 сек)
   - Mouse paths (Bezier curves вместо прямых линий)
   - Вариация стилей (иногда slow-play, иногда агрессия даже без edge)

3. Обновить main.py:
   - Добавить флаги: --unsafe-level (low / medium / high)
   - По умолчанию: dry-run
   - При --unsafe: предупреждение + подтверждение ввода

4. Тесты: dry-run vs simulated actions → сравнение логов

## Фаза 2 – Vision Enhancement & Multi-Room Support (улучшение распознавания)

1. Создать `bridge/vision/training_data_collector.py`:
   - Автоматический сбор скриншотов (каждые 5 сек) + ручная разметка карт/банка/стеков
   - Сохранять в dataset/ (PNG + JSON labels)

2. Добавить fine-tuning карточного детектора:
   - Использовать существующий card_recognizer.py
   - Добавить YOLO-подобный детектор регионов (если уже есть — дообучить)
   - Увеличить точность на 5–10% для разных скинов румов

3. Создать пресеты для 3–5 румов:
   - config/rooms/pokerstars.yaml
   - config/rooms/ignition.yaml
   - config/rooms/ggpoker.yaml
   - Каждый с уникальными ROI и template anchors

4. Тесты: accuracy на 200+ реальных скриншотах (цель ≥96% на картах, ≥92% на числах)

## Фаза 3 – Live Testing Pipeline (контролируемый запуск)

1. Добавить `bridge/live_test_runner.py`:
   - Запуск в play-money руме (PokerStars или аналог)
   - 100 рук в dry-run → анализ расхождений симуляция vs live
   - 50 рук в safe-режиме (только fold/check/call)
   - 10 рук в medium unsafe (bet/raise малыми размерами)

2. Расширить метрики:
   - Сравнение winrate dry-run vs live
   - Ошибки vision (false positive/negative)
   - Latency от скриншота до решения

3. Добавить logging всех unsafe действий + скриншоты

## Фаза 4 – Final Safety & Demo Mode

1. Добавить `bridge/demo_mode.py` — веб-интерфейс (Streamlit/Gradio):
   - Загрузка скриншота → вывод TableState + HIVE-рекомендация
   - Симуляция 3vs1 без реальных действий

2. Улучшить safety:
   - Авто-стоп при >3 ошибках vision подряд
   - Лимит сессии 30 мин
   - Автоматический logout после N рук

3. Документация: README_bridge.md с предупреждениями и инструкцией по безопасному тесту


