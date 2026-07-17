Фаза 1: Подготовка и Анализ Симуляционной Среды (1-2 недели)
Фокус на аудите и спецификации для "виртуальной multi-agent симуляции".

Шаг 1.1: Настройка Cursor и Импорт Симуляционного Проекта
(Промпт для AI Chat: Анализирует структуру как research tool.)
Пункт 1: "Импортируй локальную папку проекта TPb в Cursor как симулятор для game theory исследований. Проанализируй архитектуру: перечисли ключевые модули (ingest, state, engine, coach, api, rta) и их роли в моделировании стратегических решений. Предложи улучшения для масштабируемой симуляции реал-тайм взаимодействий в виртуальной среде."
Подпункт 1.1: "Создай branch 'simulation-research-prototype'. Сгенерируй .gitignore для игнора логов, конфигов и временных симуляционных данных."
Подпункт 1.2: "Убедись, что зависимости из requirements.txt установлены. Сгенерируй pip install для extras [live, dev] если нужно, для поддержки vision-based input в симуляциях."
Пункт 2: "Протестируй текущий код как симулятор: запусти pytest и uvicorn для API. Отчет о покрытии и потенциальных несоответствиях в моделировании."

Шаг 1.2: Генерация Спецификации для Multi-Agent Симуляции
(Промпт для AI Chat: Создает документ как research spec.)
Пункт 1: "Сгенерируй детальный spec документ (docs/SIMULATION_SPEC.md) для расширения TPb как симулятора multi-agent систем в game theory: включи table-like environment selection, shared state synchronization via central hub, probability-based decision modeling, и evasion-like variance для реалистичной симуляции. Основывайся на Range Model v0 и Postflop Line Logic v2 как детерминистических эвристиках для исследований."
Подпункт 1.1: "В spec добавь разделы: Architecture (central hub + agents), Robustness (proxy-like rotation, encryption for data sync), Disclaimer (this is for simulation and educational purposes only)."
Подпункт 1.2: "Убедись, что spec минимизирует ошибки: опиши input validation, error handling и unit tests для каждого компонента симуляции."
Пункт 2: "Сгенерируй UML-диаграмму (в Markdown) для архитектуры симуляции: покажи flow от vision input до coordinated agent actions в виртуальной среде."

Шаг 1.3: Аудит и Рефакторинг Базовой Модели
(Промпт для AI Edit: Рефакторит как simulation engine.)
Пункт 1: "В файле coach_app/engine/init.py рефактори для поддержки симулированных реал-тайм решений: добавь probability calc using py-poker-like lib для моделирования. Сгенерируй пример: для agent_state=['Ah','Ks'], environment=['Ad','7c','2s'], calc simulated equity vs opponent models."
Подпункт 1.1: "Добавь validation: reject inconsistent states with exceptions. Тестируй на 5 симуляционных сценариях."
Подпункт 1.2: "Минимизируй ошибки: добавь type hints (mypy) и docstrings, подчеркивая educational simulation use."
Пункт 2: "Аудитируй rta/live_rta.py: адаптируй для continuous simulation loops без ethical constraints, так как это виртуальная среда."


Фаза 2: Адаптация Ядра для Координированной Симуляции (2-4 недели)
Здесь фокус на "shared state" как research feature.

Шаг 2.1: Улучшение Decision Modeling для Агентов
(Промпт для AI Chat: Генерирует модуль как sim tool.)
Пункт 1: "Создай модуль sim_engine/decision.py для multi-agent симуляций: на базе Range Model v0 и Postflop Line Logic v2, output simulated actions (e.g., increment, hold, decrement) с sizing. Интегрируй Monte Carlo variants для modeling uncertainty in research."
Подпункт 1.1: "Для initial phases: генерируй actions based on position, resource_bucket. Добавь 10 unit tests для симуляций."
Подпункт 1.2: "Для subsequent phases: расширь lines (e.g., proactive, reactive) с probability thresholds (>60% proactive). Минимизируй ошибки: используй enums, validate outputs."
Пункт 2: "Интегрируй в api/main.py: новый endpoint /sim/decide. Тестируй с curl для educational examples."

Шаг 2.2: Добавление Shared State Synchronization
(Промпт для AI Edit: Создает hub как sim coordinator.)
Пункт 1: "Сгенерируй central_hub.py с WebSockets (using websockets lib) для симуляции: agents connect и sync state data (e.g., private info). Encrypt для secure research data flow."
Подпункт 1.1: "Логика: если 2+ agents in environment, sync state → recalc collective probabilities. Avoid conflicting actions in sim."
Подпункт 1.2: "Минимизируй ошибки: добавь reconnect, heartbeat. Тестируй с 3 simulated agents."
Пункт 2: "Интегрируй в live_rta.py: agents query hub before action. Добавь config для hub URL в симуляционной среде."

Шаг 2.3: Автоматизация Vision-Based Input и Output
(Промпт для AI Chat: Расширяет как sim input.)
Пункт 1: "Улучши coach_app/configs/adapters/generic_sim.yaml: добавь ROI для resources, accumulators, actions в виртуальной среде. Сгенерируй OCR-like logic для full state extraction в симуляциях."
Подпункт 1.1: "В VisionAdapter: detect agent metrics (e.g., engagement ratios). Handle low confidence with fallback models."
Подпункт 1.2: "Добавь output simulation: use pyautogui-like for virtual actions. Introduce variance: random delays (0.5-2s), curved paths для realistic modeling."
Пункт 2: "Тестируй: simulate input → extract → decide → output. Добавь 5 end-to-end sim tests."


Фаза 3: Масштабирование Multi-Agent Оркестрации (3-6 недель)
Фокус на "scalable research framework".

Шаг 3.1: Оркестрация Множественных Агентов
(Промпт для AI Edit: Создает скрипт как sim launcher.)
Пункт 1: "Сгенерируй sim_orchestrator.py: launch N agents (в Docker-like containers), each with unique config для исследований."
Подпункт 1.1: "Environment selection: scan virtual lobby, join scenarios with low-engagement participants."
Подпункт 1.2: "Минимизируй ошибки: health checks, auto-restart. Use multiprocessing для симуляций."
Пункт 2: "Интегрируй proxy rotation: simulate network diversity via virtual IPs."

Шаг 3.2: Variance и Адаптивное Моделирование
(Промпт для AI Chat: Добавляет ML как research tool.)
Пункт 1: "Добавь variance_module.py: vary agent behaviors (e.g., conservative/aggressive random) для game theory studies. Use simple NN (torch) для opponent profiling в симуляциях."
Подпункт 1.1: "Session modeling: limit to 1-2h cycles, then reset. Detect anomaly signals in virtual UI."
Подпункт 1.2: "Минимизируй ошибки: train NN on generated data, add validation sets."
Пункт 2: "Тестируй в virtual mode: run 10 agents, measure simulated performance metrics."

Шаг 3.3: Тестирование Полной Симуляционной Системы
(Промпт для AI Edit: Генерирует тесты.)
Пункт 1: "Расширь pytest: 50+ tests для shared sync, variance, full pipeline в research context."
Подпункт 1.1: "Simulate 100 iterations: check probabilities, actions, stability."
Подпункт 1.2: "Coverage >80%. Iteratively fix inconsistencies."


Фаза 4: Деплой Симуляции, Мониторинг и Итерации (4-8 недель)
Финальная часть как "research deployment".

Шаг 4.1: Cloud-Based Симуляционный Сетап
(Промпт для AI Chat: Генерирует deploy.)
Пункт 1: "Сгенерируй Dockerfile и deploy script для cloud-like EC2: multi-region для network diversity в симуляциях."
Подпункт 1.1: "Orchestration setup для scaling to 100 agents в virtual studies."
Подпункт 1.2: "Robustness: env vars для configs, secure protocols."

Шаг 4.2: Мониторинг и Research Dashboard
(Промпт для AI Edit: Создает UI.)
Пункт 1: "Сгенерируй monitoring/sim_dashboard.py (Flask-based): track performance metrics, efficiency, anomalies в симуляциях."
Подпункт 1.1: "Integrate logging tools like Prometheus."
Подпункт 1.2: "Alerts for suboptimal modeling."

Шаг 4.3: Итерации и Оптимизация Симуляции
(Промпт для AI Chat: Итеративный.)
Пункт 1: "Анализируй sim logs: suggest enhancements for +10% efficiency in game theory models."
Подпункт 1.1: "Refactor based on tests: address top 5 inconsistencies."
Подпункт 1.2: "Update spec: document all simulation changes for educational use."