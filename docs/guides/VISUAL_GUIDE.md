# 📸 Визуальное Руководство - HIVE Launcher

⚠️ **EDUCATIONAL RESEARCH ONLY**

## 🖥️ Интерфейс

### Главное Окно
```
╔═══════════════════════════════════════════════════════════╗
║  HIVE Launcher - Educational Research                    ║
╠═══════════════════════════════════════════════════════════╣
║  ⚠️ EDUCATIONAL RESEARCH ONLY - COLLUSION SYSTEM         ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  [Accounts] [Bots Control] [Dashboard] [Logs]            ║
║  ═════════════════════════════════════════════            ║
║                                                           ║
║  ┌─────────────────────────────────────────────┐         ║
║  │ №  Nickname  Status  Window  ROI  Games Bot │         ║
║  ├─────────────────────────────────────────────┤         ║
║  │ 1  Bot1      READY   PokerOK  ✓    1 games │         ║
║  │ 2  Bot2      READY   PokerOK  ✓    1 games │         ║
║  │ 3  Bot3      READY   PokerOK  ✓    1 games │         ║
║  └─────────────────────────────────────────────┘         ║
║                                                           ║
║  [➕ Add] [✏️ Edit] [❌ Remove]                           ║
║  [🪟 Capture] [📐 ROI] [🎮 Settings]                     ║
║  [🤖 Test Auto-Navigation]                               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

## 🎯 ROI Configuration

### Как Выглядит:
```
╔═══════════════════════════════════════════════════════════╗
║  [Ваш экран - полупрозрачный серый]                      ║
║                                                           ║
║  ┌──────────────────────┐                                ║
║  │ ⬍ ROI CONFIGURATION ⬍│ ← ПЕРЕТАСКИВАЕМАЯ ПАНЕЛЬ!     ║
║  │ (Drag to move)        │                               ║
║  ├──────────────────────┤                                ║
║  │ Draw ROI zones...     │                               ║
║  │ ESC | ENTER | DELETE  │                               ║
║  ├──────────────────────┤                                ║
║  │ Zone: [hero_card_1 ▼] │                               ║
║  │ Zones: 3              │                               ║
║  ├──────────────────────┤                                ║
║  │ [✓ SAVE] [✕ CANCEL]  │                               ║
║  └──────────────────────┘                                ║
║                                                           ║
║     ┌──────┐  ┌──────┐                                   ║
║     │ As Kh│  │ 7c 7d│  ← Выделенные зоны (зеленым)     ║
║     └──────┘  └──────┘                                   ║
║                                                           ║
║           ┌───────┐                                       ║
║           │ $45.50│  ← Pot zone                          ║
║           └───────┘                                       ║
║                                                           ║
║     [FOLD]  [CALL]  [RAISE]  ← Button zones              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

**Как Использовать:**
1. **Перетащить панель**: Зажать заголовок "⬍ ROI CONFIGURATION ⬍"
2. **Рисовать зоны**: Кликнуть ВНЕ панели, зажать, тянуть
3. **Сохранить**: Нажать зеленую кнопку "✓ SAVE ROI"

## 🎮 Game Settings Dialog

```
╔═══════════════════════════════════════════════════════════╗
║  Game Preferences                                        ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  ┌─ Game Types ────────────────────────────────────────┐ ║
║  │ Select games this bot can play:                     │ ║
║  │                                                      │ ║
║  │ ☑ Hold'em        ☑ PLO           ☐ Omaha           │ ║
║  │ ☑ Rush & Cash    ☐ Spin Gold     ☐ Mystery         │ ║
║  │ ☐ Tournament     ☐ Flip&Go       ☐ Battle Royale   │ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║  ┌─ Stake Limits ──────────────────────────────────────┐ ║
║  │ Quick Preset: [Micro Stakes      ▼]                 │ ║
║  │                                                      │ ║
║  │ Min Stake: [$0.10/$0.25    ]                        │ ║
║  │ Max Stake: [$1/$2          ]                        │ ║
║  │                                                      │ ║
║  │ Or select levels:                                   │ ║
║  │ ☑ Micro  ☑ Low  ☐ Medium  ☐ High                   │ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║  ┌─ Table Selection ────────────────────────────────────┐ ║
║  │ Min Players: [1 ▼]                                   │ ║
║  │ Max Players: [3 ▼]                                   │ ║
║  │ Tip: For 3vs1, set Min=1, Max=3                     │ ║
║  │                                                      │ ║
║  │ Table Size: [6 (6-max) ▼]                           │ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║  ┌─ Auto-Join Settings ─────────────────────────────────┐ ║
║  │ ☑ Enable Auto-Join Tables                           │ ║
║  │ Max Tables: [1 ▼]                                    │ ║
║  │ ☑ Avoid tables with only bots                       │ ║
║  │ ☑ Prefer tables with weak players                   │ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║              [Save]  [Cancel]                            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

## 🤖 Bots Control Tab

```
╔═══════════════════════════════════════════════════════════╗
║  🤖 Automated Bot Control                                ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  ┌─ Quick Start ────────────────────────────────────────┐ ║
║  │ Start Single Bot:                                    │ ║
║  │ [Bot1 ▼] [▶️ Start Bot]                              │ ║
║  │                                                      │ ║
║  │ Start Collusion Group (3 bots):                     │ ║
║  │ [Bot1 ▼] [Bot2 ▼] [Bot3 ▼] [🤝 Start Collusion]    │ ║
║  │                                                      │ ║
║  │ ℹ️ Collusion: 3 bots coordinate on same table      │ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║  ┌─ Active Bots ────────────────────────────────────────┐ ║
║  │ Nickname  State    Table      Stack   Uptime Actions│ ║
║  ├──────────────────────────────────────────────────────┤ ║
║  │ Bot1      PLAYING  Table #123 $45.50  5:23  [⏹️ Stop]│ ║
║  │ Bot2      PLAYING  Table #123 $48.20  5:12  [⏹️ Stop]│ ║
║  │ Bot3      PLAYING  Table #123 $52.80  5:01  [⏹️ Stop]│ ║
║  └──────────────────────────────────────────────────────┘ ║
║                                                           ║
║  [⏹️ Stop All Bots]                                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

## 📊 Автоматический Цикл

### Визуализация Процесса:
```
Запуск Бота
    ↓
┌─────────────────────────┐
│  1. НАВИГАЦИЯ           │
│  [Bot1] Захват окна     │
│  [Bot1] OCR → Find      │
│         "Hold'em" button│
│  [Bot1] Click!          │
│  [Bot1] Wait loading... │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  2. ПОИСК СТОЛОВ        │
│  [Bot1] Scan tables     │
│  [Bot1] Filter:         │
│    - $0.25/$0.50        │
│    - 1-3 players        │
│  [Bot1] Scroll...       │
│  [Bot1] Found!          │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  3. ПРИСОЕДИНЕНИЕ       │
│  [Bot1] Click table     │
│  [Bot1] Select seat     │
│  [Bot1] Confirm         │
│  [Bot1] ✅ Seated!      │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  4. ИГРА                │
│  [Bot1] Read cards      │
│  [Bot1] Calculate       │
│  [Bot1] Decide          │
│  [Bot1] Execute         │
│  Loop...                │
└─────────────────────────┘
```

### Коллюзия 3 Ботов:
```
    START COLLUSION
         ↓
    ┌────┴────┐
    │         │
  Bot1      Bot2      Bot3
    │         │         │
    └────┬────┴────┬────┘
         ↓         ↓
    Find Same Table
         ↓
    Join Together
         ↓
    Share Cards Info
         ↓
   ┌─────────────────┐
   │ COORDINATED     │
   │ 3vs1 STRATEGY   │
   │                 │
   │ Collective      │
   │ Equity: 78%     │
   │                 │
   │ → AGGRESS!      │
   └─────────────────┘
```

## 🎨 Цветовая Схема

### Статусы
```
🟢 Green   - READY, SUCCESS, PLAYING
🟡 Yellow  - NAVIGATING, SEARCHING
🔵 Blue    - INFO, SETTINGS
🟣 Purple  - AUTO-NAV, SPECIAL
🟠 Orange  - WARNING, TEST MODE
🔴 Red     - ERROR, STOP
```

### Кнопки
```
[Green]   - Start, Save, Confirm
[Red]     - Stop, Cancel, Remove
[Blue]    - Settings, Configure
[Purple]  - Auto-Navigation, Advanced
[Orange]  - Test Mode, Warning
```

## 📋 Чеклист Перед Запуском

### Для Одного Бота
```
☐ Установлены зависимости (INSTALL_AUTO_NAV.bat)
☐ Аккаунт добавлен
☐ Окно захвачено (🪟 Capture Window)
☐ ROI настроен (📐 Configure ROI)
☐ Game Settings настроены (🎮 Game Settings)
☐ Test Auto-Nav пройден (🤖 Test)
☐ Готов к запуску! (▶️ Start Bot)
```

### Для Коллюзии 3vs1
```
☐ Все вышеперечисленное × 3 аккаунта
☐ Одинаковые game settings для всех
☐ Одинаковые окна (или разные клиенты)
☐ ROI настроен для всех
☐ Готов к запуску! (🤝 Start Collusion)
```

## 🎯 Примеры Результатов

### Test Auto-Navigation Results:
```
╔═══════════════════════════════════════╗
║  Test Complete                        ║
╠═══════════════════════════════════════╣
║                                       ║
║  Auto-Navigation Test Results:       ║
║                                       ║
║  ✅ Captured window: 1920x1080       ║
║  ✅ Detected 45 UI elements          ║
║  ✅ Found 3 game mode buttons        ║
║                                       ║
║  ✅ Target game 'Hold'em' FOUND!     ║
║                                       ║
║  Game modes detected:                ║
║    - Hold'em                         ║
║    - PLO                             ║
║    - Omaha                           ║
║                                       ║
║  📋 Check logs for details.          ║
║                                       ║
║          [OK]                        ║
╚═══════════════════════════════════════╝
```

### Bot Started:
```
╔═══════════════════════════════════════╗
║  Bot Started                          ║
╠═══════════════════════════════════════╣
║                                       ║
║  Bot started for Bot1!                ║
║                                       ║
║  Check Logs tab for details.          ║
║                                       ║
║  Bot will:                            ║
║  1. Navigate to Hold'em               ║
║  2. Find table ($0.25/$0.50)          ║
║  3. Join and play                     ║
║                                       ║
║          [OK]                        ║
╚═══════════════════════════════════════╝
```

### Collusion Started:
```
╔═══════════════════════════════════════╗
║  Collusion Started                    ║
╠═══════════════════════════════════════╣
║                                       ║
║  Collusion group started!             ║
║                                       ║
║  All 3 bots are now searching for     ║
║  suitable table.                      ║
║                                       ║
║  Check Logs tab for detailed          ║
║  progress.                            ║
║                                       ║
║  Bots will coordinate 3vs1 strategy.  ║
║                                       ║
║          [OK]                        ║
╚═══════════════════════════════════════╝
```

## 📝 Типичные Логи

### Успешный Запуск
```
05:12:30 [INFO] AutoBotController initialized
05:12:31 [INFO] Starting bot for Bot1
05:12:31 [INFO] [Bot1] Bot main loop started
05:12:31 [INFO] [Bot1] Navigating to Hold'em
05:12:32 [INFO] Captured window: (0, 0, 1920, 1080)
05:12:32 [INFO] Detected 45 UI elements
05:12:32 [INFO] Found 'Hold'em' button at (100, 50, 120, 40)
05:12:32 [INFO] Clicking 'Hold'em' button
05:12:35 [INFO] [Bot1] Navigation successful
05:12:35 [INFO] [Bot1] Searching for table
05:12:35 [INFO]   Stakes: $0.25/$0.50
05:12:35 [INFO]   Players: 1-3
05:12:37 [INFO] [Bot1] Found table: $0.25/$0.50 (2 players)
05:12:37 [INFO] [Bot1] Joining...
05:12:40 [INFO] [Bot1] Joined table successfully
05:12:40 [INFO] [Bot1] Play loop started
```

### Коллюзия
```
05:15:00 ========================================
05:15:00 STARTING COLLUSION GROUP
05:15:00 Bots: ['Bot1', 'Bot2', 'Bot3']
05:15:00 ========================================
05:15:01 Starting bot 1/3: Bot1
05:15:01 [Bot1] Navigating to Hold'em...
05:15:06 Starting bot 2/3: Bot2
05:15:06 [Bot2] Navigating to Hold'em...
05:15:11 Starting bot 3/3: Bot3
05:15:11 [Bot3] Navigating to Hold'em...
05:15:15 ========================================
05:15:15 COLLUSION GROUP STARTED SUCCESSFULLY
05:15:15 All 3 bots searching for suitable table
05:15:15 ========================================
05:15:20 [Bot1] Found table: $0.50/$1 (1 player)
05:15:22 [Bot2] Found same table
05:15:24 [Bot3] Found same table
05:15:30 ✅ All 3 bots seated
05:15:30 ✅ Collusion active
```

## 🎯 Советы

### Оптимизация
```
✓ Используйте 6-max столы (легче контроль)
✓ Ищите столы с 1 живым игроком
✓ Micro/Low stakes для начала
✓ Один стол на бота (для начала)
```

### Безопасность
```
✓ VPN обязательно
✓ Разные IP для ботов (если возможно)
✓ Естественные delays (0.5-2s)
✓ Не все действия одновременно
```

### Мониторинг
```
✓ Проверять Logs каждые 5 минут
✓ Следить за Dashboard
✓ Vision errors < 5%
✓ Collective edge > 60%
```

## 📚 Дальнейшее Чтение

```
1. START_HERE.md            - Начните отсюда!
2. QUICK_START_AUTO_NAV.md  - 5-минутный старт
3. COMPLETE_GUIDE.md        - Полное руководство
4. VISUAL_GUIDE.md          - Этот файл (визуальное)
5. AUTO_UI_DETECTION.md     - Техническая документация
6. FINAL_SUMMARY.md         - Итоговая сводка
```

---

## 🎉 Система Готова!

```
┌─────────────────────────────────────────┐
│                                         │
│  ✅ HIVE Launcher v0.4.0               │
│  ✅ Full Auto-Collusion System         │
│  ✅ Ready to Use!                      │
│                                         │
│  🚀 Запуск: MENU.bat                   │
│  📖 Документация: START_HERE.md        │
│                                         │
│  ⚠️ Educational Research Only          │
│                                         │
└─────────────────────────────────────────┘
```

**Используйте Ответственно! 🎓**

---

**Version**: 0.4.0  
**Date**: 2026-02-09  
**Status**: ✅ Complete!
