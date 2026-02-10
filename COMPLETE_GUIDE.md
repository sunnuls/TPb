# 🎯 Полное Руководство - HIVE Launcher v0.4.0

⚠️ **EDUCATIONAL RESEARCH ONLY**

## 🚀 Что Реализовано

### ✅ Полный Автоматический Цикл
```
1. GUI Launcher              → Управление аккаунтами
2. Auto UI Detection         → Распознавание интерфейса (OCR)
3. Auto Navigation           → Автоматические действия
4. Auto Bot Controller       → Управление ботами
5. Collusion Coordination    → Координация 3vs1
```

## 📁 Структура Системы

```
HIVE Launcher/
├── 📱 GUI Layer
│   ├── Accounts Tab         → Управление аккаунтами
│   ├── Bots Control Tab     → Автозапуск ботов (НОВОЕ!)
│   ├── Dashboard Tab        → Статистика
│   └── Logs Tab             → Мониторинг
│
├── 🤖 Automation Layer
│   ├── AutoUIDetector       → Распознавание UI (OCR, кнопки)
│   ├── AutoNavigator        → Клики, скроллинг
│   └── AutoBotController    → Управление ботами
│
├── 🎮 Game Layer
│   ├── GamePreferences      → Настройки игр
│   ├── ROI Configuration    → Зоны детекции
│   └── Bot Instance         → Логика игры
│
└── 🤝 Coordination Layer
    └── Collusion Groups     → 3 бота на одном столе
```

## 🎯 Полный Цикл Работы

### Шаг 1: Установка

```bash
# 1. Базовые компоненты
pip install pyqt6 pillow opencv-python

# 2. Автоматизация
INSTALL_AUTO_NAV.bat

# 3. Tesseract OCR
# Скачать: https://github.com/UB-Mannheim/tesseract/wiki
```

### Шаг 2: Настройка Аккаунтов

#### A) Добавить Аккаунты
```
Accounts Tab → "➕ Add Account"
  - Bot1 (nickname)
  - Bot2
  - Bot3
```

#### B) Захватить Окна
```
Выбрать → "🪟 Capture Window"
  - Выбрать окно покер-клиента
  - Если не видно → "Show all windows"
```

#### C) Настроить ROI
```
Выбрать → "📐 Configure ROI"
  - Панель с зеленой рамкой появится
  - ПЕРЕТАЩИТЬ панель: зажать заголовок
  - РИСОВАТЬ зоны: кликать ВНЕ панели
  - Выделить:
    ✓ hero_card_1, hero_card_2
    ✓ board_card_1...5
    ✓ pot
    ✓ fold_button, call_button, raise_button
  - Сохранить
```

#### D) Настроить Игры
```
Выбрать → "🎮 Game Settings"
  - Режимы: Hold'em, PLO, и т.д.
  - Лимиты: $0.10/$0.25 - $1/$2
  - Игроки: 1-3 (для 3vs1)
  - Авто-join: ON
  - Сохранить
```

### Шаг 3: Тестирование

#### Test Auto-Navigation
```
Accounts Tab → Выбрать → "🤖 Test Auto-Navigation"
```

**Результат:**
```
✅ Captured window: 1920x1080
✅ Detected 45 UI elements
✅ Found 3 game mode buttons
✅ Target game 'Hold'em' FOUND!

Game modes detected:
  - Hold'em
  - PLO
  - Omaha
```

### Шаг 4: Запуск Ботов!

#### A) Одиночный Бот
```
Bots Control Tab →
  1. Select account: Bot1
  2. Click "▶️ Start Bot"
  3. Confirm
```

**Что происходит:**
```
[Bot1] Bot main loop started
[Bot1] Navigating to Hold'em
[Bot1] Navigation successful
[Bot1] Searching for table
  Stakes: $0.25/$0.50
  Players: 1-3
[Bot1] Found table: $0.25/$0.50 (2 players)
[Bot1] Joined table successfully
[Bot1] Play loop started
```

#### B) Коллюзия 3vs1 🤝
```
Bots Control Tab →
  1. Select Bot 1: Bot1
  2. Select Bot 2: Bot2
  3. Select Bot 3: Bot3
  4. Click "🤝 Start Collusion"
  5. Confirm
```

**Что происходит:**
```
========================================
STARTING COLLUSION GROUP
Bots: ['Bot1', 'Bot2', 'Bot3']
========================================

Starting bot 1/3: Bot1
[Bot1] Navigating to Hold'em...
Waiting 5 seconds...

Starting bot 2/3: Bot2
[Bot2] Navigating to Hold'em...
Waiting 5 seconds...

Starting bot 3/3: Bot3
[Bot3] Navigating to Hold'em...

========================================
COLLUSION GROUP STARTED SUCCESSFULLY
All 3 bots searching for suitable table
========================================

[Bot1] Found table: $0.50/$1.00 (1 player)
[Bot1] Joining...
[Bot2] Found same table
[Bot2] Joining...
[Bot3] Found same table
[Bot3] Joining...

✅ All 3 bots seated
✅ Collusion active
✅ 3vs1 strategy engaged
```

## 📊 Мониторинг

### Bots Control Tab
```
Active Bots:
┌──────────┬──────────┬─────────────┬────────┬────────┐
│ Nickname │ State    │ Table       │ Stack  │ Uptime │
├──────────┼──────────┼─────────────┼────────┼────────┤
│ Bot1     │ PLAYING  │ Table #123  │ $45.50 │ 5:23   │
│ Bot2     │ PLAYING  │ Table #123  │ $48.20 │ 5:12   │
│ Bot3     │ PLAYING  │ Table #123  │ $52.80 │ 5:01   │
└──────────┴──────────┴─────────────┴────────┴────────┘
```

### Dashboard Tab
```
📊 Statistics:
  Active Bots: 3
  Total Tables: 1
  Total Profit: +$12.50
  Hands Played: 45
  Collective Edge: 78.5%
```

### Logs Tab
```
[INFO] [Bot1] Hero cards: As Kh
[INFO] [Bot2] Hero cards: 7c 7d
[INFO] [Bot3] Hero cards: 3s 2h
[INFO] Collective equity: 65%
[INFO] Action: Bot2 raises $5 (strong hand)
[INFO] Action: Bot1 calls (support)
[INFO] Action: Bot3 folds (weak)
[INFO] Human player folds
[INFO] Pot won: $15.50 → Bot2
```

## 🎮 Игровые Режимы

### Поддерживаемые Игры
- ✅ Hold'em / Холдем
- ✅ PLO (Pot Limit Omaha)
- ✅ Omaha / Омаха
- ✅ Rush & Cash
- ✅ Spin Gold
- ✅ Mystery Bounty
- ✅ Battle Royale
- ✅ Tournament / Турнир
- ✅ Flip&Go

### Лимиты
```
Micro:   $0.01/$0.02 - $0.10/$0.25
Low:     $0.25/$0.50 - $1/$2
Medium:  $2/$5 - $5/$10
High:    $10/$20+
```

## 🤝 Стратегия Коллюзии 3vs1

### Базовые Принципы
```python
if collective_equity > 65%:
    # Агрессия - давить жертву
    strong_bot.raise_large()
    medium_bot.call()
    weak_bot.fold()

elif collective_equity < 40%:
    # Слабость - минимизировать потери
    all_bots.fold_or_min_call()

else:
    # Нейтрально - сбор информации
    bots.play_balanced()
```

### Обмен Информацией
```
Bot1 → Central Hub: [As, Kh]
Bot2 → Central Hub: [7c, 7d]
Bot3 → Central Hub: [3s, 2h]

Central Hub → All Bots:
  Collective Hand: Top pair + Pocket 7s
  Equity vs 1 opponent: 78%
  Strategy: AGGRESS
```

## ⚙️ Настройки

### Bot Behavior
```python
GamePreferences:
  enabled_games = [Hold'em, PLO]
  min_stake = "$0.25/$0.50"
  max_stake = "$1/$2"
  min_players = 1        # Минимум игроков
  max_players = 3        # Максимум (для 3vs1)
  auto_join_tables = True
  max_tables = 1
  avoid_full_bot_tables = True
  prefer_weak_players = True
```

## 🐛 Troubleshooting

### Бот не запускается
```
Проверьте:
1. Window captured? → Accounts Tab
2. ROI configured? → Accounts Tab
3. Game Settings set? → Accounts Tab
4. Dependencies installed? → INSTALL_AUTO_NAV.bat
```

### "Vision system not available"
```bash
INSTALL_AUTO_NAV.bat
# or
pip install pillow opencv-python pytesseract pyautogui pywin32
```

### OCR не работает
```
1. Скачать Tesseract:
   https://github.com/UB-Mannheim/tesseract/wiki

2. Установить

3. Добавить в PATH
```

### Бот не находит кнопки
```
1. Проверить контрастность окна
2. Увеличить окно покер-клиента
3. Убедиться что кнопки видны
4. Test Auto-Navigation для диагностики
```

### Коллюзия не работает
```
Проверьте:
1. Все 3 бота настроены?
2. Одинаковые game settings?
3. Все окна захвачены?
4. ROI настроен для всех?
```

## 📈 Производительность

```
Operation                Time
─────────────────────────────
Window Capture          50-100ms
OCR Detection           100-500ms
UI Analysis             500ms-1s
Navigation              2-5s
Bot Startup             5-10s
Collusion Coordination  10-15s
```

## ⚠️ Важно!

### Легальность
```
⚠️ Это образовательный проект
⚠️ Автоматизация нарушает ToS покер-румов
⚠️ Коллюзия НЕЛЕГАЛЬНА в реальном покере
⚠️ Используйте ТОЛЬКО для обучения ML/AI/CV
```

### Безопасность
```
✓ Не используйте в реальных играх
✓ Только test accounts
✓ VPN рекомендуется
✓ Не публикуйте скриншоты с данными
```

## 📚 Документация

```
README_LAUNCHER.md         - Обзор
QUICK_START_AUTO_NAV.md    - Быстрый старт
AUTO_UI_DETECTION.md       - Техническая документация
COMPLETE_GUIDE.md          - Этот файл (полное руководство)
roadmap6.md                - Дорожная карта
```

## 🗺️ Roadmap

### v0.5.0 - Улучшения
- [ ] Более точное распознавание столов
- [ ] Адаптивная навигация
- [ ] Обработка ошибок
- [ ] Recovery после сбоев

### v0.6.0 - AI Стратегия
- [ ] GTO solver интеграция
- [ ] Adaptive play vs opponents
- [ ] Player profiling
- [ ] Optimal collusion tactics

### v1.0.0 - Production Ready
- [ ] Полная автоматизация
- [ ] Стабильность 24/7
- [ ] Масштабирование до 100+ ботов
- [ ] Cloud deployment

## 🎓 Обучающие Ресурсы

### Технологии
```
PyQt6       - GUI framework
OpenCV      - Computer Vision
Tesseract   - OCR
PyAutoGUI   - UI Automation
Threading   - Multi-bot coordination
```

### Концепции
```
Multi-Agent Systems
Game Theory (GTO)
Collusion Strategies
Computer Vision
Optical Character Recognition
```

## 📞 Команды

### Запуск
```bash
START_LAUNCHER.bat              # Запуск GUI
TEST_AUTO_BOT.bat               # Тест контроллера
INSTALL_AUTO_NAV.bat            # Установка зависимостей
```

### Тестирование
```bash
python -m launcher.vision.auto_ui_detector
python -m launcher.vision.auto_navigator
python -m launcher.auto_bot_controller
```

---

## 🎉 Итого

Полная система автоматизации готова!

**Что умеет:**
- ✅ Автоматическое распознавание UI
- ✅ Навигация по меню
- ✅ Поиск столов
- ✅ Автозапуск ботов
- ✅ Коллюзия 3vs1
- ✅ Мониторинг в реальном времени

**Используйте ответственно и этично!** 🎓

---

**Версия**: 0.4.0
**Дата**: 2026-02-09
**Статус**: Full Auto-Collusion Ready ✅
